"""Publicação no YouTube: upload, agendamento e metadados.

Autenticação (uma vez, na sua máquina):
    1. Google Cloud Console -> ative a YouTube Data API v3
    2. Crie credenciais OAuth do tipo "App para computador"
    3. Salve o JSON em ~/.config/fabrica/client_secret.json
    4. Rode: python -m fabrica auth

O token fica em ~/.config/fabrica/token.json. No GitHub Actions, o conteúdo do
token vai em um secret (YOUTUBE_TOKEN_JSON) — veja docs/AGENDAMENTO.md.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .util import aviso, log, ok

SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube"]
CONFIG = Path(os.environ.get("FABRICA_CONFIG", Path.home() / ".config" / "fabrica"))
TOKEN = CONFIG / "token.json"
SECRET = CONFIG / "client_secret.json"


def _servico():
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
    except ImportError:
        raise SystemExit("instale: pip install google-api-python-client google-auth-oauthlib")

    creds = None
    if TOKEN.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN), SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        TOKEN.write_text(creds.to_json())
    if not creds or not creds.valid:
        raise SystemExit("sem autenticação. rode: python -m fabrica auth")
    return build("youtube", "v3", credentials=creds)


def autorizar() -> None:
    """Abre o navegador para o consentimento OAuth e salva o token."""
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        raise SystemExit("instale: pip install google-auth-oauthlib")
    if not SECRET.exists():
        raise SystemExit(f"coloque o client_secret.json em {SECRET}")
    flow = InstalledAppFlow.from_client_secrets_file(str(SECRET), SCOPES)
    creds = flow.run_local_server(port=0)
    CONFIG.mkdir(parents=True, exist_ok=True)
    TOKEN.write_text(creds.to_json())
    ok(f"token salvo em {TOKEN}")


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.0Z")


def proxima_data(quando_: str = "sexta", hora: str = "18:00",
                 fuso: str = "America/Sao_Paulo") -> datetime:
    """Próxima ocorrência do dia da semana informado, no fuso do canal."""
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo(fuso)
    except Exception:
        tz = timezone(timedelta(hours=-3))
    dias = {"segunda": 0, "terca": 1, "terça": 1, "quarta": 2, "quinta": 3,
            "sexta": 4, "sabado": 5, "sábado": 5, "domingo": 6}
    alvo = dias.get(str(quando_).lower(), 4)
    h, m = [int(x) for x in hora.split(":")]
    agora = datetime.now(tz)
    delta = (alvo - agora.weekday()) % 7
    cand = agora.replace(hour=h, minute=m, second=0, microsecond=0) + timedelta(days=delta)
    if cand <= agora:
        cand += timedelta(days=7)
    return cand


def capitulos(ep) -> list[str]:
    """Capítulos no formato do YouTube a partir das seções do roteiro.

    Regras da plataforma: o primeiro tem de ser 00:00 e são necessários ao
    menos 3 capítulos, cada um com 10 s ou mais.
    """
    try:
        from .timeline import montar
        tl = montar(ep)
    except Exception:
        return []
    saida: list[tuple[float, str]] = []
    atual = None
    for ev in tl["eventos"]:
        secao = (ev.get("secao") or "").strip()
        if not secao or secao == atual:
            continue
        if ev["tipo"] == "cartao" and not saida:
            saida.append((0.0, "Abertura"))
            atual = secao
            continue
        if ev["inicio"] < 10:
            atual = secao
            continue
        saida.append((ev["inicio"], secao))
        atual = secao
    if not saida:
        return []
    if saida[0][0] > 0:
        saida.insert(0, (0.0, "Abertura"))
    if len(saida) < 3:
        return []
    return [f"{int(t // 60):02d}:{int(t % 60):02d} {nome}" for t, nome in saida]


def metadados(ep, quando: datetime | None = None) -> dict:
    """Monta o corpo da requisição (título, descrição, tags, categoria)."""
    cfg = ep.config["publicacao"]
    titulo = ep.plan.get("titulo", ep.slug)
    serie = ep.config.get("serie", {}).get("nome", ep.plan.get("serie", ""))
    numero = ep.plan.get("episodio", 1)
    tags = list(cfg.get("tags_base", [])) + list(ep.plan.get("tags", []))
    caps = ep.plan.get("capitulos") or capitulos(ep)
    if caps:
        ep.plan["capitulos"] = caps
        ep.salvar_plan()
    descricao = ep.plan.get("descricao")
    if not descricao:
        sinopse = (ep.plan.get("sinopse") or "").strip()
        partes = [
            titulo,
            "",
            f"Episódio {numero:02d} da série {serie}.",
            "",
            *(["Neste episódio:", sinopse, ""] if sinopse else []),
            "CAPÍTULOS",
            *caps,
            "",
            "Se essa história te prendeu, deixa o like e se inscreve — "
            "um episódio novo toda semana, no mesmo horário.",
            "",
            " ".join(f"#{t.replace(' ', '')}" for t in tags[:5]),
        ]
        descricao = "\n".join(p for p in partes if p is not None)
    corpo = {
        "snippet": {
            "title": titulo[:100],
            "description": descricao[:4900],
            "tags": [t[:30] for t in tags][:30],
            "categoryId": str(cfg.get("categoria", 20)),
            "defaultLanguage": "pt-BR",
            "defaultAudioLanguage": "pt-BR",
        },
        "status": {
            "privacyStatus": "private",
            "selfDeclaredMadeForKids": False,
            "license": "youtube",
            "embeddable": True,
        },
    }
    if quando:
        corpo["status"]["privacyStatus"] = "private"
        corpo["status"]["publishAt"] = _iso(quando)
    return corpo


def enviar(ep, *, quando: datetime | None = None, agendado: bool = False,
           dry_run: bool = False) -> dict | None:
    """Sobe o vídeo (e a thumbnail). Use dry_run para conferir metadados."""
    if not ep.saida.exists():
        raise SystemExit(f"renderize antes: {ep.saida}")
    cfg_pub = ep.config["publicacao"]
    quando = quando or proxima_data(
        quando_=cfg_pub.get("dia_semana", "sexta"),
        hora=cfg_pub.get("hora", "18:00"),
        fuso=cfg_pub.get("fuso", "America/Sao_Paulo"),
    )
    corpo = metadados(ep, quando if agendado else None)
    if dry_run:
        print(json.dumps(corpo, ensure_ascii=False, indent=2))
        return corpo

    from googleapiclient.http import MediaFileUpload

    yt = _servico()
    midia = MediaFileUpload(str(ep.saida), chunksize=8 * 1024 * 1024, resumable=True,
                            mimetype="video/mp4")
    pedido = yt.videos().insert(part="snippet,status", body=corpo, media_body=midia)
    resposta = None
    while resposta is None:
        status, resposta = pedido.next_chunk()
        if status:
            log(f"upload {int(status.progress()*100)}%")
    vid = resposta["id"]
    thumb = ep.base / (ep.plan.get("thumbnail") or "thumbnail.jpg")
    if thumb.exists():
        try:
            yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(str(thumb))).execute()
        except Exception as e:
            aviso(f"thumbnail não enviada (canal verificado?): {e}")
    ok(f"vídeo enviado: https://youtu.be/{vid}"
       + (f" · agendado para {quando:%d/%m %H:%M}" if agendado else ""))
    hist = ep.base / "publicacao.json"
    hist.write_text(json.dumps({"video_id": vid, "agendado_para": _iso(quando) if agendado else None,
                                "enviado_em": datetime.now(timezone.utc).isoformat()},
                               ensure_ascii=False, indent=2))
    return resposta
