"""Folha de contato e página de revisão do episódio (para conferir sem abrir editor)."""
from __future__ import annotations

from pathlib import Path

from PIL import Image

from .util import ffmpeg, log, ok, run, tempo


def extrair(caminho_video: Path, destino_dir: Path, quantidade: int = 12,
            largura: int = 640) -> list[Path]:
    """Extrai N quadros distribuídos ao longo do vídeo."""
    from .util import duracao

    total = duracao(caminho_video)
    destino_dir.mkdir(parents=True, exist_ok=True)
    saidas = []
    for i in range(quantidade):
        t = total * (i + 0.5) / quantidade
        p = destino_dir / f"frame_{i:02d}.jpg"
        run([ffmpeg(), "-y", "-loglevel", "error", "-ss", f"{t:.2f}",
             "-i", str(caminho_video), "-frames:v", "1",
             "-vf", f"scale={largura}:-2", str(p)], check=False)
        if p.exists():
            saidas.append(p)
    return saidas


def folha_contato(quadros: list[Path], saida: Path, colunas: int = 3) -> Path:
    if not quadros:
        raise SystemExit("nenhum quadro extraído")
    with Image.open(quadros[0]) as primeira:
        w, h = primeira.size
    linhas = (len(quadros) + colunas - 1) // colunas
    margem = 8
    folha = Image.new("RGB", (colunas * w + margem * (colunas + 1),
                              linhas * h + margem * (linhas + 1)), (10, 10, 12))
    for i, q in enumerate(quadros):
        with Image.open(q) as im:
            folha.paste(im.convert("RGB"),
                        (margem + (i % colunas) * (w + margem),
                         margem + (i // colunas) * (h + margem)))
    folha.save(saida, quality=90)
    return saida


def pagina_revisao(ep, quantidade: int = 12) -> Path:
    """Gera build/revisao.html com vídeo, folha de contato e tabela da timeline."""
    from .timeline import montar

    quadros = extrair(ep.saida, ep.build / "frames", quantidade)
    folha = folha_contato(quadros, ep.build / "folha_de_contato.jpg", colunas=3)
    tl = montar(ep)
    linhas = "\n".join(
        f"<tr><td>{i+1}</td><td><code>{e['id']}</code></td><td>{e['tipo']}</td>"
        f"<td>{tempo(e['inicio'])}</td><td>{e['duracao']:.1f}s</td>"
        f"<td>{e['narracao'][:90]}</td></tr>"
        for i, e in enumerate(tl["eventos"])
    )
    thumb = ep.base / (ep.plan.get("thumbnail") or "thumbnail.jpg")
    html = f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<title>{ep.plan.get('titulo')} — revisão</title>
<style>
 :root {{ color-scheme: dark; }}
 body {{ background:#0b0b0d; color:#e7e2d8; font:16px/1.5 system-ui,sans-serif;
        margin:0; padding:32px; }}
 h1 {{ font-family:Georgia,serif; font-weight:400; letter-spacing:.02em; }}
 h2 {{ font-size:14px; text-transform:uppercase; letter-spacing:.14em;
      color:#b99a6b; margin-top:36px; }}
 video, img {{ max-width:100%; border-radius:10px; border:1px solid #26242a; }}
 .grid {{ display:grid; grid-template-columns: 2fr 1fr; gap:24px; align-items:start; }}
 table {{ width:100%; border-collapse:collapse; font-size:14px; }}
 td, th {{ border-bottom:1px solid #1e1c22; padding:6px 8px; text-align:left;
          vertical-align:top; }}
 th {{ color:#9d968a; font-weight:500; }}
 code {{ color:#d8b47c; }}
 .meta {{ color:#8d867a; font-size:14px; }}
</style></head><body>
<h1>{ep.plan.get('titulo')}</h1>
<p class="meta">#{ep.plan.get('episodio')} · {ep.plan.get('serie')} ·
 {tl['total']/60:.1f} min · {len(tl['eventos'])} cenas</p>
<h2>Vídeo</h2>
<video src="../final.mp4" controls preload="metadata" poster="../{ep.plan.get('thumbnail') or 'thumbnail.jpg'}"></video>
<div class="grid">
  <div><h2>Folha de contato</h2><img src="folha_de_contato.jpg" alt="quadros do vídeo"></div>
  <div><h2>Thumbnail</h2><img src="../{ep.plan.get('thumbnail') or 'thumbnail.jpg'}" alt="thumbnail"></div>
</div>
<h2>Timeline</h2>
<table><thead><tr><th>#</th><th>id</th><th>tipo</th><th>início</th><th>dur</th>
<th>fala</th></tr></thead><tbody>
{linhas}
</tbody></table>
</body></html>"""
    saida = ep.build / "revisao.html"
    saida.write_text(html, encoding="utf-8")
    log(f"folha de contato: {folha.name}")
    return saida
