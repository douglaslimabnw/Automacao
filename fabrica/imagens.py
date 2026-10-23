"""Imagens por cena.

Para cada cena o renderizador precisa de UMA imagem. A fábrica resolve na
seguinte ordem:

  1. `imagem` do plano (screenshot do jogo, arte de IA, foto) — tem prioridade
  2. `clip` do plano (gameplay em vídeo) — vira cena em movimento
  3. arte procedural gerada aqui (shots/<id>.jpg)

Assim você pode começar 100% automático e ir substituindo cena a cena por
material real do jogo sem mexer em nada além de um campo no plan.json.
"""
from __future__ import annotations

from pathlib import Path

from . import arte
from .util import log, ok

# pastas onde você pode largar material próprio (shots/ é arte automática)
PASTAS_MANUAIS = ("imagens", "assets", "material")


def _procurar_manual(ep, cena_id: str) -> Path | None:
    """Aceita shots/<id>.png|jpg|jpeg já colocados à mão pelo usuário."""
    for pasta in PASTAS_MANUAIS:
        for ext in (".png", ".jpg", ".jpeg", ".webp"):
            p = ep.base / pasta / f"{cena_id}{ext}"
            if p.exists() and p.stat().st_size > 5000:
                return p
    return None


def planejar_imagens(ep, *, largura: int = 1920, altura: int = 1080,
                     forcar: bool = False) -> dict:
    """Garante uma imagem para cada cena. Devolve o mapa id -> caminho."""
    ep.garantir_pastas()
    mapa = {}
    geradas = 0
    semente_base = int(ep.plan.get("semente") or ep.config["estilo"].get("semente_base", 777))

    for i, cena in enumerate(ep.cenas):
        cid = cena["id"]
        # "shots/..." é arte automática (regenerável); qualquer outro caminho
        # é material do usuário e tem prioridade absoluta.
        auto = str(cena.get("imagem") or "").replace("\\", "/").startswith("shots/")
        manual = None if auto else (ep.caminho_relativo(cena.get("imagem")) if cena.get("imagem") else None)
        if cena.get("clip") and ep.caminho_relativo(cena["clip"]).exists():
            mapa[cid] = ep.caminho_relativo(cena["clip"])
            continue
        if manual and manual.exists():
            mapa[cid] = manual
            continue
        achado = None if (auto and not forcar) else _procurar_manual(ep, cid)
        if achado:
            mapa[cid] = achado
            cena["imagem"] = str(achado.relative_to(ep.base))
            continue

        destino = ep.shots / f"{cid}.jpg"
        if destino.exists() and not forcar:
            mapa[cid] = destino
            cena.setdefault("imagem", str(destino.relative_to(ep.base)))
            continue

        cartao = cena.get("cartao")
        if cartao:
            if cartao.get("tipo") == "titulo":
                arte.cartao_titulo(cartao.get("titulo", ""), cartao.get("subtitulo", ""),
                                   destino, semente=semente_base + i, largura=largura,
                                   altura=altura, paleta=cena.get("paleta"),
                                   arquetipo=cena.get("visual") or "ruina")
            else:
                arte.cartao_cta(cartao.get("titulo", ""), cartao.get("subtitulo", ""),
                                destino, semente=semente_base + i, largura=largura,
                                altura=altura, paleta=cena.get("paleta"),
                                arquetipo=cena.get("visual") or "trono")
        else:
            arq = cena.get("visual") or "abismo"
            # plano médio (personagem grande, "falando com a câmera")
            plano = cena.get("plano") or ("medio" if cena.get("figura") else "aberto")
            arr = arte.compor(
                arq,
                semente_base + i * 17,
                largura=largura,
                altura=altura,
                paleta=cena.get("paleta"),
                figura=plano != "aberto",
                escala_figura={"medio": 0.52, "close": 0.80, "aberto": None}.get(plano),
                figura_x=0.5 if plano == "close" else None,
                desfoque_profundo=1.8 if plano == "close" else 1.0,
            )
            from PIL import Image
            import numpy as _np
            # máscara de gradiente: a esquerda fica mais escura (ar para texto),
            # a direita preserva o cenário. Dá cara de "plano de cinema".
            W = arr.shape[1]
            grad = _np.linspace(0.55, 1.0, W, dtype=_np.float32)[None, :, None]
            arr = (arr.astype(_np.float32) * grad).clip(0, 255).astype(_np.uint8)
            Image.fromarray(arr).save(destino, quality=94)
        mapa[cid] = destino
        cena["imagem"] = str(destino.relative_to(ep.base))
        geradas += 1

    ep.salvar_plan()
    ok(f"imagens: {geradas} geradas, {len(mapa)-geradas} reaproveitadas/manuais")
    return mapa


def gerar_thumbnail(ep, cena_id: str | None = None, *, titulo: str | None = None,
                    linha2: str = "") -> Path:
    """Thumbnail 1280x720 a partir de uma cena (ou da primeira cena de impacto)."""
    candidatas = [c for c in ep.cenas if c.get("imagem")]
    if not candidatas:
        raise SystemExit("gere as imagens antes da thumbnail")
    escolhida = next((c for c in candidatas if c["id"] == cena_id), None)
    if escolhida is None:
        escolhida = max(candidatas, key=lambda c: (c["tipo"] in ("fala", "gancho"),
                                                   len(c.get("narracao", ""))))
    base = ep.caminho_relativo(escolhida["imagem"])
    saida = ep.base / "thumbnail.jpg"
    arte.thumbnail(base, titulo or ep.plan["titulo"], saida, linha2=linha2)
    ep.plan["thumbnail"] = str(saida.relative_to(ep.base))
    ep.salvar_plan()
    ok(f"thumbnail: {saida}")
    return saida
