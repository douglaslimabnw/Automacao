"""Motor de roteiro: transforma prosa em um plano de cenas pronto para render.

Fluxo pensado para produção semanal:

    episodes/<slug>/roteiro.md    (você/LLM escreve a prosa, com marcas simples)
              │
              ▼  fabrica roteiro
    episodes/<slug>/plan.json     (cenas, tipos, visuais, ganchos, thumbnails)

Marcas aceitas no roteiro.md (opcionais — o motor completa o que faltar):

    ## Cena 3 — O primeiro sino            → cabeçalho de cena
    > GANCHO                               → marca a cena como gancho de inscrição
    > CTA
    > PROXIMO
    visual: caverna, figura                → cenário/paleta do arquétipo
    duracao: 6                             → força a duração (cena muda)
    [pausa]                                → respiro na narração (removido do TTS)

Regra de ritmo: nenhuma imagem fica mais de `MAX_SEG_POR_SHOT` segundos na
tela. Blocos longos são divididos em planos automáticos.
"""
from __future__ import annotations

import random
import re
from pathlib import Path

from .config import Episodio, carregar_serie
from .timeline import duracao_estimada
from .util import RAIZ, log, salvar_json

MAX_SEG_POR_SHOT = 9.0
PALAVRAS_POR_SHOT = 48

# Palavras-chave -> arquétipo visual
MAPA_VISUAL = {
    "ruina": ["ruína", "ruina", "castelo", "muralha", "torre", "reino", "cidade",
              "fortaleza", "catedral", "vila", "aldeia", "templo"],
    "caverna": ["caverna", "gruta", "túnel", "tunel", "mina", "profundeza", "escuro",
                "pedra", "eco", "abismo subterrâneo"],
    "floresta": ["floresta", "bosque", "árvore", "arvore", "raiz", "selva", "névoa",
                 "nevoa", "musgo", "pântano", "pantano"],
    "abismo": ["abismo", "precipício", "precipicio", "vazio", "queda", "fenda",
               "borda", "garganta", "nada"],
    "trono": ["trono", "rei", "rainha", "coroa", "salão", "salao", "coluna",
              "majestade", "soberano", "deus", "deuses"],
    "campo": ["campo", "planície", "planicie", "deserto", "neve", "gelo", "cinza",
              "planícies", "horizonte"],
}

PALETA_POR_ARQ = {
    "ruina": "abismo", "caverna": "catacumba", "floresta": "floresta",
    "abismo": "abismo", "trono": "trono", "campo": "gelo",
}


def limpar_marcas(texto: str) -> str:
    return re.sub(r"\[[^\]]*\]", "", texto).strip()


def _dividir(texto: str, max_palavras: int = PALAVRAS_POR_SHOT) -> list[str]:
    """Quebra um parágrafo em blocos de ~max_palavras respeitando frases."""
    frases = re.split(r"(?<=[.!?…])\s+", texto.strip())
    blocos, atual = [], ""
    for f in frases:
        if not f:
            continue
        if atual and len((atual + " " + f).split()) > max_palavras:
            blocos.append(atual.strip())
            atual = f
        else:
            atual = (atual + " " + f).strip()
    if atual:
        blocos.append(atual.strip())
    # frase gigante sozinha: quebra por vírgula
    final = []
    for b in blocos:
        if len(b.split()) > max_palavras * 1.8:
            partes = re.split(r"(?<=,)\s+", b)
            meio = len(partes) // 2
            final += [" ".join(partes[:meio]), " ".join(partes[meio:])]
        else:
            final.append(b)
    return [b for b in final if b]


def inferir_arquetipo(texto: str, padrao: str = "abismo") -> str:
    t = (texto or "").lower()
    pontos = {k: sum(t.count(p) for p in v) for k, v in MAPA_VISUAL.items()}
    melhor = max(pontos, key=pontos.get)
    return melhor if pontos[melhor] > 0 else padrao


def ler_roteiro(caminho: Path) -> list[dict]:
    """Lê roteiro.md em uma lista de cenas brutas."""
    if not caminho.exists():
        return []
    cenas, atual = [], None
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^##\s*(?:Cena\s*)?(\d+)?\s*[—\-–:]?\s*(.*)$", linha.strip())
        if linha.strip().startswith("## "):
            if atual:
                cenas.append(atual)
            atual = {
                "titulo": m.group(2).strip() if m else linha.strip("# ").strip(),
                "marca": None,
                "visual": None,
                "duracao": None,
                "texto": [],
            }
            continue
        if atual is None:
            continue
        s = linha.strip()
        if not s:
            if atual["texto"]:
                atual["texto"].append("")
            continue
        low = s.lower()
        if low.startswith(">"):
            conteudo = s.lstrip("> ").strip().upper()
            if any(k in conteudo for k in ("GANCHO", "CTA", "INSCRI", "LIKE")):
                atual["marca"] = "gancho"
            elif "PROXIM" in conteudo:
                atual["marca"] = "proximo"
        elif low.startswith("visual:"):
            atual["visual"] = s.split(":", 1)[1].strip()
        elif low.startswith("duracao:") or low.startswith("duração:"):
            try:
                atual["duracao"] = float(re.findall(r"[\d.]+", s)[0])
            except Exception:
                pass
        else:
            atual["texto"].append(s)
    if atual:
        cenas.append(atual)
    for c in cenas:
        c["texto"] = "\n".join(c["texto"]).strip()
    return cenas


def construir_plan(slug: str, serie: str, titulo: str, numero: int,
                   cenas_brutas: list[dict], *, ganchos: bool = True,
                   semente: int = 777, thumb: str | None = None,
                   meta_alvo: float | None = None, extra: dict | None = None) -> dict:
    extra = extra or {}
    """Expande cenas brutas em plano com IDs, visuais e marcações."""
    rng = random.Random(semente + numero)
    cenas, n = [], 0
    for bruta in cenas_brutas:
        texto = limpar_marcas(bruta["texto"])
        marca = bruta.get("marca")
        vis = bruta.get("visual")
        pedacos = _dividir(texto) if texto else [""]
        for i, pedaco in enumerate(pedacos):
            n += 1
            arq = (vis.split(",")[0].strip().lower() if vis else None)
            arq = arq if arq in PALETA_POR_ARQ else inferir_arquetipo(pedaco or bruta["titulo"])
            # a marca vale só para o plano de abertura (gancho) ou de fecho (próximo)
            marcado = (i == 0) if marca == "gancho" else (i == len(pedacos) - 1)
            tipo = "fala" if pedaco else "broll"
            if marca and marcado:
                tipo = marca
            # "eu" = narrador falando com a câmera -> plano médio do personagem.
            # A cada 3 planos médios, um aberto para o cenário respirar.
            primeira_pessoa = bool(re.search(r"\b(eu|meu|minha|mim)\b", (pedaco or "").lower()))
            if vis and "figura" in vis:
                primeira_pessoa = True
            plano = "aberto"
            if primeira_pessoa:
                plano = "aberto" if (n % 4 == 0) else "medio"
            cena = {
                "id": f"c{n:03d}",
                "tipo": tipo,
                "narracao": pedaco,
                "secao": bruta.get("titulo") or "",
                "visual": arq,
                "paleta": PALETA_POR_ARQ.get(arq, "abismo"),
                "figura": plano != "aberto",
                "plano": plano,
                "movimento": rng.choice(["zoom_in", "pan_esq", "zoom_out", "pan_dir"]),
            }
            if len(pedacos) == 1 and bruta.get("duracao"):
                cena["duracao"] = bruta["duracao"]
            if marcado:
                cena["sfx"] = "impacto" if marca == "gancho" else "riser"
            cenas.append(cena)

    # ---- estrutura editorial: cartão de abertura e fecho
    cartao_abertura = {
        "id": "abertura",
        "tipo": "cartao",
        "secao": "Abertura",
        "narracao": "",
        "visual": cenas[0]["visual"] if cenas else "abismo",
        "duracao": 4.5,
        "cartao": {"tipo": "titulo", "titulo": titulo,
                   "subtitulo": f"Episódio {numero:02d}"},
    }
    if ganchos and not any(c["tipo"] == "gancho" for c in cenas):
        pesos = [max(1, len((c.get("narracao") or "").split())) for c in cenas]
        acumulado, alvo = 0, 0
        for idx, p in enumerate(pesos):
            acumulado += p
            if acumulado >= sum(pesos) * 0.42:
                alvo = idx
                break
        cenas.insert(alvo, {
            "id": "gancho_meio",
            "tipo": "gancho",
            "secao": "Gancho",
            "narracao": "Antes de continuar: se essa história te prendeu, deixa o like. "
                        "É o que mantém o canal vivo.",
            "visual": cenas[alvo]["visual"],
            "duracao": 6.5,
            "legenda": "SE ISSO TE PRENDEU, DEIXA O LIKE",
            "sfx": "impacto",
            "cartao": {"tipo": "cta", "titulo": "DEIXA O LIKE",
                       "subtitulo": "e se inscreve no canal"},
            "transicao": "fade",
        })
    cenas = [cartao_abertura] + cenas

    if ganchos:
        cenas.append({
            "id": "fecho_cta",
            "tipo": "cta",
            "secao": "Encerramento",
            "narracao": "Se você chegou até aqui, você aguenta o que vem depois. "
                        "Se inscreve — o próximo episódio já está escrito.",
            "visual": "trono",
            "duracao": 9.0,
            "cartao": {"tipo": "cta", "titulo": "INSCREVA-SE", "subtitulo": "novo episódio toda semana"},
        })
    # garante IDs únicos
    vistos = set()
    for i, c in enumerate(cenas):
        cid = c["id"]
        while cid in vistos:
            cid = f"{cid}_{i}"
        c["id"] = cid
        vistos.add(cid)

    total = sum(duracao_estimada(c.get("narracao", "")) + (0.45 if c.get("narracao") else 0)
                for c in cenas) + sum(c.get("duracao", 0) for c in cenas if not c.get("narracao"))
    return {
        "slug": slug,
        "serie": serie,
        "episodio": numero,
        "titulo": titulo,
        "duracao_alvo": int(meta_alvo or 780),
        "duracao_estimada": round(total, 1),
        "semente": semente + numero * 31,
        "thumbnail": thumb,
        "sinopse": (extra.get("sinopse") or ""),
        "tags": list(extra.get("tags") or []),
        "cenas": cenas,
    }


def gerar_roteiro(slug: str, *, forcar: bool = False) -> Path:
    """Converte roteiro.md -> plan.json (mantendo ajustes manuais se existirem)."""
    base = RAIZ / "episodes" / slug
    roteiro = base / "roteiro.md"
    if not roteiro.exists():
        raise SystemExit(f"crie o roteiro em {roteiro}")
    cenas = ler_roteiro(roteiro)
    if not cenas:
        raise SystemExit("roteiro.md não tem nenhuma cena (use '## Cena 1 — ...')")

    meta = _ler_meta(roteiro, base)
    plano_existente = base / "plan.json"
    plan = construir_plan(
        slug,
        meta["serie"],
        meta["titulo"],
        meta["numero"],
        cenas,
        ganchos=meta["ganchos"],
        semente=meta["semente"],
        thumb=meta.get("thumb"),
        meta_alvo=meta.get("duracao_alvo"),
        extra=meta,
    )
    if plano_existente.exists() and not forcar:
        antigo = __import__("json").loads(plano_existente.read_text(encoding="utf-8"))
        por_id = {c["id"]: c for c in antigo.get("cenas", [])}
        for c in plan["cenas"]:
            # preserva mídia e ajustes feitos à mão
            if c["id"] in por_id:
                for campo in ("imagem", "clip", "movimento", "paleta", "figura"):
                    if por_id[c["id"]].get(campo):
                        c[campo] = por_id[c["id"]][campo]
    salvar_json(plano_existente, plan)
    log(f"plano gerado: {len(plan['cenas'])} cenas, ~{plan['duracao_estimada']/60:.1f} min")
    return plano_existente


def _ler_meta(roteiro: Path, base: Path) -> dict:
    texto = roteiro.read_text(encoding="utf-8")
    meta = {"serie": "vozes-do-abismo", "titulo": base.name, "numero": 1,
            "ganchos": True, "semente": 777, "thumb": None}
    import json

    cfg = base / "ep.json"
    if cfg.exists():
        meta.update(json.loads(cfg.read_text(encoding="utf-8")))
    m = re.search(r"^#\s*Episódio\s*(\d+)\s*[—\-–:]\s*(.+)$", texto, re.M)
    if m:
        meta["numero"] = int(m.group(1))
        meta["titulo"] = m.group(2).strip()
    else:
        m2 = re.search(r"^#\s*(.+)$", texto, re.M)
        if m2:
            meta["titulo"] = m2.group(1).strip()
    return meta


def resumo(plan: dict) -> str:
    por_tipo: dict[str, int] = {}
    for c in plan["cenas"]:
        por_tipo[c["tipo"]] = por_tipo.get(c["tipo"], 0) + 1
    linhas = [f"{plan['titulo']}  (#{plan['episodio']} · {plan['serie']})",
              f"cenas: {len(plan['cenas'])}  ·  ~{plan['duracao_estimada']/60:.1f} min",
              "tipos: " + ", ".join(f"{k}={v}" for k, v in sorted(por_tipo.items()))]
    return "\n".join(linhas)
