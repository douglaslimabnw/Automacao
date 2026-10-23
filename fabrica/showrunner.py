"""Showrunner: a camada que roda sem você.

Fluxo de uma execução:

    fila.json  →  episódio  →  agente escreve  →  QC  →  voz  →  arte  →
    render  →  QC do vídeo  →  pacote  →  agendado no YouTube  →  relatório

Cada etapa grava seu estado em episodes/<slug>/estado.json. Se algo falha, a
próxima execução retoma de onde parou (idempotência por arquivo: se
narracao/c001.mp3 existe e não mudou, não regrava).

É isso que permite deixar rodando em cron, GitHub Actions, Claude Routines ou
OpenClaw: sempre que o processo acorda, ele avança o que falta.
"""
from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

from . import agente, imagens, publicar, qc, render, roteiro, timeline, voz
from .config import Episodio, carregar_serie
from .util import RAIZ, aviso, ler_json, log, ok, salvar_json

# caminhos resolvidos em tempo de chamada (testes apontam RAIZ para outro lugar)
def _fila_path() -> Path:
    return RAIZ / "fila.json"


def _prompts_dir() -> Path:
    return RAIZ / "prompts"


# ------------------------------------------------------------------ fila
def carregar_fila() -> dict:
    p = _fila_path()
    if p.exists():
        return ler_json(p)
    return {"serie": "vozes-do-abismo", "itens": []}


def salvar_fila(fila: dict) -> None:
    salvar_json(_fila_path(), fila)


def enfileirar(itens: list[dict], *, serie: str | None = None) -> dict:
    fila = carregar_fila()
    if serie:
        fila["serie"] = serie
    existentes = {i["numero"] for i in fila["itens"]}
    proximo = max(existentes, default=0) + 1
    for item in itens:
        if not item.get("numero"):
            item["numero"] = proximo
            proximo += 1
        if item["numero"] in existentes:
            continue
        item.setdefault("slug", slugificar(item.get("titulo", f"episodio-{item['numero']}"), item["numero"]))
        item.setdefault("status", "todo")
        item.setdefault("serie", fila.get("serie"))
        item.setdefault("criado_em", datetime.now(timezone.utc).isoformat(timespec="seconds"))
        fila["itens"].append(item)
        existentes.add(item["numero"])
    fila["itens"].sort(key=lambda i: i["numero"])
    salvar_fila(fila)
    return fila


def slugificar(titulo: str, numero: int) -> str:
    from unicodedata import normalize

    base = normalize("NFKD", titulo).encode("ascii", "ignore").decode()
    base = re.sub(r"[^a-zA-Z0-9]+", "-", base).strip("-").lower()[:48]
    return f"ep-{numero:02d}-{base or 'episodio'}"


def proximo_pendente(serie: str | None = None) -> dict | None:
    fila = carregar_fila()
    for item in fila["itens"]:
        if item.get("status") in ("todo", "erro", "precisa_revisao"):
            if serie and item.get("serie") != serie:
                continue
            # já existe e está pronto? então pula
            final = RAIZ / "episodes" / item["slug"] / "final.mp4"
            if final.exists() and item.get("status") == "todo":
                item["status"] = "pronto"
                salvar_fila(fila)
                continue
            return item
    return None


def marcar(item: dict, status: str, **extra) -> None:
    fila = carregar_fila()
    for i in fila["itens"]:
        if i["numero"] == item["numero"]:
            i["status"] = status
            i.update(extra)
    salvar_fila(fila)


# ------------------------------------------------------------------ prompts
def montar_prompt(nome: str, **valores) -> str:
    caminho = _prompts_dir() / f"{nome}.md"
    if not caminho.exists():
        raise SystemExit(f"prompt ausente: {caminho}")
    texto = caminho.read_text(encoding="utf-8")
    for k, v in valores.items():
        texto = texto.replace("{{" + k.upper() + "}}", str(v))
    # placeholders não preenchidos viram texto vazio (evita vazar {{X}} ao modelo)
    return re.sub(r"\{\{[A-Z_]+\}\}", "", texto)


def _biblia(serie: str) -> str:
    for nome in (f"{serie}-biblia.md", "BIBLIA.md"):
        p = RAIZ / "series" / nome
        if p.exists():
            return p.read_text(encoding="utf-8")
    p = RAIZ / "docs" / "BIBLIA.md"
    return p.read_text(encoding="utf-8") if p.exists() else ""


def _resumo_anteriores(limite: int = 4) -> str:
    linhas = []
    for p in sorted((RAIZ / "episodes").glob("*/roteiro.md"))[-limite:]:
        txt = p.read_text(encoding="utf-8")
        titulo = re.search(r"^#\s*(.+)$", txt, re.M)
        sinopse = re.search(r"^##\s*Cena 1.*?\n+(.+?)$", txt, re.M | re.S)
        linhas.append(f"- {titulo.group(1) if titulo else p.parent.name}")
    return "\n".join(linhas) or "- (nenhum episódio anterior)"


# ------------------------------------------------------------------ ideias
# modelos sem marca de gênero — funcionam com qualquer léxico
MODELOS_TITULO = [
    "Ninguém Volta de {lugar}", "Depois de {lugar}", "{lugar} Não Existe Mais",
    "O Que Restou de {lugar}", "A História de {coisa}", "{coisa}: o que ninguém contou",
    "{n} Vezes em {lugar}",
]


def ideias_locais(serie: str, n: int, base: int = 2) -> list[dict]:
    """Banco de reserva: títulos e briefs montados a partir do léxico da série.

    O léxico vem de `serie.lexico` no YAML — é o parâmetro que faz o gerador
    local falar a língua do seu nicho em vez de genérico.
    """
    rng = __import__("random").Random(int(time.time()) // 86400 + base)
    try:
        cfg = carregar_serie(serie)
    except SystemExit:
        cfg = {}
    lex = (cfg.get("serie") or {}).get("lexico") or {}
    coisas = lex.get("coisas") or ["Sino", "Guardião", "Rainha", "Poço", "Cripta",
                                   "Forasteiro", "Muralha", "Fogo"]
    acoes = lex.get("acoes") or ["Ninguém Escutou", "Ainda Toca", "Não Tinha Nome",
                                 "Engoliu o Reino"]
    lugares = lex.get("lugares") or ["Vardhal", "Campanário", "Catacumba",
                                     "Torre Leste", "Portão de Cinzas"]
    saida = []
    for i in range(n):
        modelo = rng.choice(MODELOS_TITULO)
        titulo = modelo.format(coisa=rng.choice(coisas), acao=rng.choice(acoes),
                               lugar=rng.choice(lugares), n=rng.choice([7, 12, 30]))
        saida.append({
            "numero": base + i,
            "titulo": titulo,
            "brief": f"Episódio sobre {titulo.lower()}, revelando um detalhe novo do "
                     f"mistério do sino e aprofundando um personagem já apresentado.",
            "gancho_final": "prometer o que existe atrás da próxima porta",
        })
    return saida


def gerar_ideias(serie: str, n: int = 6, *, provedor: str | None = None,
                 orcamento: float | None = 1.0) -> list[dict]:
    """Pede ao agente um lote de episódios e enfileira (com fallback local)."""
    cfg = carregar_serie(serie)
    fila = carregar_fila()
    base = max([i["numero"] for i in fila["itens"]], default=0) + 1
    prompt = montar_prompt(
        "ideias",
        serie=cfg.get("serie", {}).get("nome", serie),
        premissa=cfg.get("serie", {}).get("premissa", ""),
        publico=cfg.get("serie", {}).get("publico", ""),
        biblia=_biblia(serie),
        anteriores=_resumo_anteriores(),
        quantidade=n,
        primeiro_numero=base,
        caminho_saida="episodes/_ideias.json",
    )
    r = agente.executar(prompt, provedor=provedor, orcamento=orcamento, turnos=15)
    sugestoes = []
    saida = RAIZ / "episodes" / "_ideias.json"
    if r.ok and saida.exists():
        try:
            sugestoes = ler_json(saida) if isinstance(ler_json(saida), list) else ler_json(saida).get("itens", [])
        except Exception:
            sugestoes = []
        saida.unlink(missing_ok=True)
    if not sugestoes:
        aviso("agente não entregou ideias válidas — usando banco local")
        sugestoes = ideias_locais(serie, n, base)
    for i, s in enumerate(sugestoes[:n]):
        s["numero"] = base + i
    fila = enfileirar(sugestoes[:n], serie=serie)
    ok(f"fila: {len(fila['itens'])} itens (novos: {len(sugestoes[:n])})")
    return sugestoes[:n]


# ------------------------------------------------------------------ estado
def _estado_path(ep_base: Path) -> Path:
    return ep_base / "estado.json"


def ler_estado(ep_base: Path) -> dict:
    p = _estado_path(ep_base)
    if p.exists():
        return ler_json(p)
    return {"estagios": {}, "custos": []}


def gravar_estagio(ep_base: Path, nome: str, ok_: bool, detalhe: str = "",
                   segundos: float = 0.0, custo: float | None = None) -> dict:
    est = ler_estado(ep_base)
    est["estagios"][nome] = {
        "ok": ok_,
        "em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "detalhe": detalhe[:500],
        "segundos": round(segundos, 1),
    }
    if custo:
        est.setdefault("custos", []).append({"etapa": nome, "usd": round(custo, 4)})
    est["custo_total_usd"] = round(sum(c["usd"] for c in est.get("custos", [])), 4)
    salvar_json(_estado_path(ep_base), est)
    return est


# ------------------------------------------------------------------ notificação
def notificar(mensagem: str) -> None:
    """Avisa por webhook (Discord/Slack/Telegram-via-bot/URL própria)."""
    url = os.environ.get("FABRICA_WEBHOOK")
    if not url:
        log(f"[notificação] {mensagem[:200]}")
        return
    import urllib.request

    corpo = json.dumps({"text": mensagem, "content": mensagem}).encode()
    req = urllib.request.Request(url, data=corpo,
                                 headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=15).read()
    except Exception as e:
        aviso(f"webhook falhou: {e}")


# ------------------------------------------------------------------ produção
def preparar_episodio(item: dict) -> Episodio:
    base = RAIZ / "episodes" / item["slug"]
    base.mkdir(parents=True, exist_ok=True)
    ep_json = base / "ep.json"
    if not ep_json.exists():
        salvar_json(ep_json, {
            "serie": item.get("serie", carregar_fila().get("serie")),
            "titulo": item["titulo"],
            "numero": item["numero"],
            "ganchos": True,
            "semente": 777 + item["numero"] * 13,
            "sinopse": item.get("brief", ""),
            "brief": item.get("brief", ""),
            "gancho_final": item.get("gancho_final", ""),
        })
    ep = Episodio(item["slug"])
    ep.garantir_pastas()
    return ep


def _escrever_roteiro(ep: Episodio, item: dict, provedor: str | None,
                      tentativas: int = 2) -> tuple[bool, float]:
    if (ep.base / "roteiro.md").exists() and (ep.base / "roteiro.md").stat().st_size > 2000:
        log("roteiro já existe — reaproveitando")
        return True, 0.0
    serie = ep.plan.get("serie") or item.get("serie", "vozes-do-abismo")
    cfg = carregar_serie(serie)
    prompt = montar_prompt(
        "roteiro",
        serie=cfg.get("serie", {}).get("nome", serie),
        premissa=cfg.get("serie", {}).get("premissa", ""),
        publico=cfg.get("serie", {}).get("publico", ""),
        biblia=_biblia(serie),
        anteriores=_resumo_anteriores(),
        numero=item["numero"],
        titulo=item["titulo"],
        brief=item.get("brief", ""),
        gancho_final=item.get("gancho_final", ""),
        tema=item.get("brief") or item["titulo"],
        caminho_saida=f"episodes/{ep.slug}/roteiro.md",
        palavras_alvo=1900,
    )
    custo = 0.0
    for i in range(tentativas):
        r = agente.executar(prompt, provedor=provedor, orcamento=2.0, turnos=30)
        custo += r.custo_usd or 0.0
        if (ep.base / "roteiro.md").exists() and (ep.base / "roteiro.md").stat().st_size > 1500:
            return True, custo
        aviso(f"tentativa {i+1}: agente não escreveu o roteiro ({r.erro[:200]})")
    return False, custo


def _corrigir_roteiro(ep: Episodio, rel: qc.Relatorio, item: dict,
                      provedor: str | None, tentativa: int) -> tuple[bool, float]:
    prompt = montar_prompt(
        "critica",
        serie=ep.plan.get("serie", ""),
        problemas=rel.feedback_para_agente(),
        caminho=f"episodes/{ep.slug}/roteiro.md",
        numero=item["numero"],
        titulo=item["titulo"],
        biblia=_biblia(ep.plan.get("serie", "")),
    )
    r = agente.executar(prompt, provedor=provedor, orcamento=1.5, turnos=25)
    return r.ok, (r.custo_usd or 0.0)


def produzir(*, serie: str | None = None, publicar_: bool = False,
             sem_render: bool = False, provedor: str | None = None,
             ignorar_qc: bool = False, tentativas_qc: int = 2,
             preview: bool = False, voz_provedor: str | None = None) -> dict:
    """Produz o próximo episódio da fila. Devolve um resumo."""
    # trava de emergência: crie o arquivo PAUSAR na raiz e nada roda
    if (RAIZ / "PAUSAR").exists():
        aviso("PAUSAR encontrado na raiz — produção interrompida")
        return {"status": "pausado"}

    item = proximo_pendente(serie)
    if not item:
        ok("fila vazia — nada a produzir")
        return {"status": "vazio"}

    log(f"produzindo #{item['numero']} · {item['titulo']}")
    ep = preparar_episodio(item)
    marcar(item, "produzindo")
    inicio = time.time()
    resumo = {"slug": ep.slug, "numero": item["numero"], "status": "ok", "etapas": {}}

    # 1. roteiro (agente) ------------------------------------------------
    t0 = time.time()
    if not (ep.base / "roteiro.md").exists() or (ep.base / "roteiro.md").stat().st_size < 1500:
        ok_rot, custo = _escrever_roteiro(ep, item, provedor)
        gravar_estagio(ep.base, "roteiro", ok_rot, custo=custo, segundos=time.time() - t0)
        resumo["etapas"]["roteiro"] = ok_rot
        if not ok_rot:
            marcar(item, "erro", erro="agente não gerou roteiro")
            notificar(f"❌ #{item['numero']} falhou na escrita do roteiro")
            return {**resumo, "status": "erro_roteiro"}

    roteiro.gerar_roteiro(ep.slug, forcar=False)
    ep = Episodio(ep.slug)

    # 2. QC do roteiro (com laço de correção) ----------------------------
    for tent in range(tentativas_qc + 1):
        rel = qc.rodar(ep, escopo="roteiro")
        resumo["etapas"][f"qc_roteiro_{tent}"] = rel.aprovado
        if rel.aprovado or ignorar_qc:
            break
        if tent >= tentativas_qc:
            aviso("QC reprovou o roteiro; marcando para revisão humana")
            marcar(item, "precisa_revisao", qc=rel.texto()[:1500])
            notificar(f"⚠️ #{item['numero']} precisa de revisão:\n{rel.feedback_para_agente()[:400]}")
            return {**resumo, "status": "precisa_revisao", "qc": rel.para_json()}
        log(f"QC reprovou — pedindo correção ({tent+1}/{tentativas_qc})")
        corrigiu, custo = _corrigir_roteiro(ep, rel, item, provedor, tent)
        gravar_estagio(ep.base, f"correcao_{tent+1}", corrigiu, custo=custo)
        roteiro.gerar_roteiro(ep.slug, forcar=True)
        ep = Episodio(ep.slug)

    # 3. voz -------------------------------------------------------------
    t0 = time.time()
    try:
        voz.narrar(ep, provedor=voz_provedor)
        gravar_estagio(ep.base, "narracao", True, segundos=time.time() - t0)
        resumo["etapas"]["narracao"] = True
    except Exception as e:
        gravar_estagio(ep.base, "narracao", False, detalhe=str(e))
        marcar(item, "erro", erro=f"narração: {e}")
        notificar(f"❌ #{item['numero']} falhou na narração: {e}")
        return {**resumo, "status": "erro_narracao"}

    # 4. imagens + thumbnail ---------------------------------------------
    t0 = time.time()
    cv = ep.config["video"]
    larg, alt = (960, 540) if preview else (cv["largura"], cv["altura"])
    imagens.planejar_imagens(ep, largura=larg, altura=alt)
    imagens.gerar_thumbnail(ep, linha2=(item.get("thumb_linha") or ""))
    gravar_estagio(ep.base, "imagens", True, segundos=time.time() - t0)
    resumo["etapas"]["imagens"] = True

    # 5. render ----------------------------------------------------------
    if not sem_render:
        t0 = time.time()
        try:
            render.renderizar(ep, preview=preview)
            gravar_estagio(ep.base, "render", True, segundos=time.time() - t0)
            resumo["etapas"]["render"] = True
        except Exception as e:
            gravar_estagio(ep.base, "render", False, detalhe=str(e))
            marcar(item, "erro", erro=f"render: {e}")
            notificar(f"❌ #{item['numero']} falhou no render: {e}")
            return {**resumo, "status": "erro_render"}

    # 6. pacote + QC do vídeo -------------------------------------------
    from . import subtitles
    tl = timeline.montar(ep)
    subtitles.escrever_srt(ep.base / "legendas.srt", subtitles.cues(tl))
    salvar_json(ep.base / "publicacao_meta.json", publicar.metadados(ep))
    if not sem_render:
        rel_video = qc.rodar(ep, escopo="video")
        resumo["etapas"]["qc_video"] = rel_video.aprovado
        if not rel_video.aprovado and not ignorar_qc:
            marcar(item, "precisa_revisao", qc=rel_video.texto()[:1500])
            notificar(f"⚠️ #{item['numero']} reprovado no QC de vídeo")
            return {**resumo, "status": "precisa_revisao_video", "qc": rel_video.para_json()}

    # 7. publicação ------------------------------------------------------
    if publicar_:
        try:
            publicar.enviar(ep, agendado=True)
            gravar_estagio(ep.base, "publicacao", True)
            resumo["etapas"]["publicacao"] = True
        except Exception as e:
            gravar_estagio(ep.base, "publicacao", False, detalhe=str(e))
            aviso(f"publicação falhou: {e}")
            resumo["etapas"]["publicacao"] = False

    est = ler_estado(ep.base)
    resumo["custo_usd"] = est.get("custo_total_usd", 0)
    teto = float(os.environ.get("FABRICA_ORCAMENTO_MAX", "0") or 0)
    if teto and resumo["custo_usd"] > teto:
        aviso(f"custo US$ {resumo['custo_usd']:.2f} passou do teto US$ {teto:.2f} — "
              f"episódio fica em revisão e não será publicado")
        publicar_ = False
    resumo["minutos"] = round((time.time() - inicio) / 60, 1)
    marcar(item, "publicado" if publicar_ else "pronto",
           slug=ep.slug, concluido_em=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    _relatorio(ep, resumo, est)
    notificar(
        f"✅ Episódio #{item['numero']} pronto: {item['titulo']}\n"
        f"{resumo['minutos']} min · US$ {resumo['custo_usd']:.2f} · {ep.slug}"
    )
    return resumo


def _relatorio(ep: Episodio, resumo: dict, est: dict) -> Path:
    linhas = [f"# Relatório — {ep.plan.get('titulo', ep.slug)}", ""]
    linhas.append(f"- slug: `{ep.slug}`")
    linhas.append(f"- status: **{resumo.get('status')}**")
    linhas.append(f"- tempo de produção: {resumo.get('minutos', 0)} min")
    linhas.append(f"- custo de agente: US$ {resumo.get('custo_usd', 0):.2f}")
    linhas.append("")
    linhas.append("## Estágios")
    for nome, dado in est.get("estagios", {}).items():
        marca = "✔" if dado.get("ok") else "✖"
        linhas.append(f"- {marca} {nome} — {dado.get('segundos', 0):.0f}s "
                      f"({dado.get('em', '')})" + (f" · {dado['detalhe']}" if dado.get("detalhe") else ""))
    qc_file = ep.base / "qc.md"
    if qc_file.exists():
        linhas += ["", "## QC", "", qc_file.read_text(encoding="utf-8")]
    saida = ep.base / "RELATORIO.md"
    saida.write_text("\n".join(linhas), encoding="utf-8")
    return saida


# ------------------------------------------------------------------ dashboard
def estado_geral() -> dict:
    fila = carregar_fila()
    linhas = []
    total_custo = 0.0
    for item in fila["itens"]:
        base = RAIZ / "episodes" / item["slug"]
        est = ler_estado(base) if base.exists() else {"estagios": {}}
        total_custo += est.get("custo_total_usd", 0) or 0
        linhas.append({
            "numero": item["numero"],
            "titulo": item["titulo"],
            "slug": item["slug"],
            "status": item.get("status"),
            "estagios": {k: v.get("ok") for k, v in est.get("estagios", {}).items()},
            "final": (base / "final.mp4").exists(),
            "custo_usd": est.get("custo_total_usd", 0),
        })
    return {"itens": linhas, "custo_total_usd": round(total_custo, 2)}


def escrever_dashboard() -> Path:
    dados = estado_geral()
    linhas = ["# Painel da fábrica", "",
              f"Custo acumulado de agentes: **US$ {dados['custo_total_usd']:.2f}**", "",
              "| # | episódio | status | vídeo | US$ | estágios |",
              "|---|---|---|---|---|---|"]
    for i in dados["itens"]:
        est = " ".join(f"{'✔' if v else '·'}{k}" for k, v in i["estagios"].items())
        linhas.append(
            f"| {i['numero']} | {i['titulo']} | `{i['status']}` | "
            f"{'✔' if i['final'] else '—'} | {i['custo_usd']:.2f} | {est} |"
        )
    saida = RAIZ / "PAINEL.md"
    saida.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    return saida
