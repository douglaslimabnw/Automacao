"""Timeline: durações, offsets, ganchos e validação do plano do episódio."""
from __future__ import annotations

import random
from pathlib import Path

from .util import aviso, duracao, log, tempo

# Pausa natural entre falas (segundos)
RESPIRO = 0.45
# Duração mínima/máxima de uma cena só com imagem (b-roll)
BROLL_MIN, BROLL_MAX = 2.5, 7.0
# Nenhum plano fica menos que isso na tela (frases curtas precisam respirar)
CENA_MIN, CENA_MAX = 2.0, 11.0
# Palavras por segundo aproximadas da narração PT-BR em ritmo "dark"
WPS = 2.25


def duracao_estimada(texto: str) -> float:
    """Estimativa usada antes do TTS existir (roteiro/planejamento)."""
    palavras = len((texto or "").split())
    if not palavras:
        return 0.0
    pausas = (texto.count(".") + texto.count("!") + texto.count("?")) * 0.25
    pausas += texto.count("—") * 0.15
    return round(palavras / WPS + pausas, 2)


def montar(ep) -> dict:
    """Resolve a duração real de cada cena e os offsets da timeline.

    Regra: se a cena tem narração (texto), a duração vem do áudio gravado
    (narracao/<id>.*). Sem áudio, usa a estimativa por palavras. Cenas mudas
    usam `duracao` do plano ou o padrão de 4s.
    """
    log("montando timeline")
    eventos = []
    t = 0.0
    total_narrado = 0.0
    for cena in ep.cenas:
        cid = cena["id"]
        audio = None
        for ext in (".mp3", ".wav", ".m4a", ".opus", ".flac"):
            p = ep.narracao / f"{cid}{ext}"
            if p.exists():
                audio = p
                break
        if audio:
            dur = duracao(audio) + RESPIRO
        elif cena.get("narracao"):
            dur = duracao_estimada(cena["narracao"]) + RESPIRO
        else:
            dur = float(cena.get("duracao") or 4.0)

        if not cena.get("narracao"):
            dur = max(BROLL_MIN, min(BROLL_MAX, dur))

        dur = round(max(CENA_MIN, min(CENA_MAX, dur)), 3)
        eventos.append(
            {
                "id": cid,
                "tipo": cena.get("tipo", "broll"),
                "inicio": round(t, 3),
                "duracao": dur,
                "fim": round(t + dur, 3),
                "audio": str(audio.relative_to(ep.base)) if audio else None,
                "narracao": cena.get("narracao", ""),
                "secao": cena.get("secao", ""),
                "visual": cena.get("visual", ""),
                "imagem": cena.get("imagem"),
                "clip": cena.get("clip"),
                "legenda": cena.get("legenda"),
                "transicao": cena.get("transicao", "fade"),
            }
        )
        if cena.get("narracao"):
            total_narrado += dur
        t += dur
    tl = {
        "episodio": ep.plan.get("slug"),
        "titulo": ep.plan.get("titulo"),
        "total": round(t, 3),
        "narrado": round(total_narrado, 3),
        "eventos": eventos,
    }
    return tl


def validar(ep) -> list[str]:
    """Checagens de sanidade do roteiro. Devolve lista de avisos."""
    problemas = []
    if not ep.cenas:
        problemas.append("nenhuma cena no plano")
    ids = [c.get("id") for c in ep.cenas]
    if len(set(ids)) != len(ids):
        problemas.append("ids de cena duplicados")
    imagens = [c.get("imagem") for c in ep.cenas if c.get("imagem")]
    for img in imagens:
        if not (ep.base / img).exists():
            problemas.append(f"imagem ausente: {img}")
    clips = [c.get("clip") for c in ep.cenas if c.get("clip")]
    for cl in clips:
        if not (ep.base / cl).exists():
            problemas.append(f"clipe ausente: {cl}")
    total = sum(
        duracao(ep.narracao / f"{c['id']}.mp3")
        if (ep.narracao / f"{c['id']}.mp3").exists()
        else duracao_estimada(c.get("narracao", ""))
        for c in ep.cenas
    )
    alvo = float(ep.plan.get("duracao_alvo", 0) or 0)
    if alvo and total < alvo * 0.6:
        problemas.append(
            f"roteiro tem ~{total/60:.1f} min, bem abaixo do alvo de {alvo/60:.1f} min"
        )
    if alvo and total > alvo * 1.35:
        problemas.append(
            f"roteiro tem ~{total/60:.1f} min, bem acima do alvo de {alvo/60:.1f} min"
        )
    return problemas


def diagnostico(tl: dict) -> str:
    linhas = [
        f"Episódio: {tl['titulo']}",
        f"Duração total: {tempo(tl['total'])} ({tl['total']/60:.1f} min)",
        f"Narração: {tempo(tl['narrado'])} ({min(999, tl['narrado']/max(tl['total'],1)*100):.0f}% do vídeo)",
        "",
        f"{'#':>2}  {'id':<6}{'tipo':<10}{'início':>9}{'dur':>7}  fala",
    ]
    for i, e in enumerate(tl["eventos"], 1):
        falado = (e["narracao"][:48] + "…") if len(e["narracao"]) > 48 else e["narracao"]
        linhas.append(
            f"{i:>2}  {e['id']:<6}{e['tipo']:<10}{tempo(e['inicio'])[3:]:>9}{e['duracao']:>7.1f}  {falado}"
        )
    return "\n".join(linhas)


def ordem_visual(cenas: list[dict], semente: int = 0) -> list[dict]:
    """Distribui variações de movimento (zoom in/out, pan) sem repetir em sequência."""
    rng = random.Random(semente or 42)
    movimentos = ["zoom_in", "pan_esq", "zoom_out", "pan_dir", "zoom_in_lento"]
    saida, anterior = [], None
    for c in cenas:
        opcoes = [m for m in movimentos if m != anterior]
        mov = c.get("movimento") or rng.choice(opcoes)
        anterior = mov
        saida.append({**c, "movimento": mov})
    return saida
