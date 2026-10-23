"""Linha de comando da fábrica.

    python -m fabrica novo --slug ep-02 --titulo "O Segundo Sino"
    python -m fabrica roteiro ep-02
    python -m fabrica narrar ep-02
    python -m fabrica imagens ep-02
    python -m fabrica timeline ep-02
    python -m fabrica render ep-02
    python -m fabrica pacote ep-02          # metadados + thumbnail + srt
    python -m fabrica publicar ep-02 --agendar
    python -m fabrica diario                # roda o próximo episódio da fila
"""
from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path

from . import arte, imagens, publicar, render, roteiro, timeline, voz
from .config import Episodio, carregar_serie
from .util import RAIZ, aviso, ler_json, log, ok, salvar_json, tempo


def _ep(slug: str) -> Episodio:
    ep = Episodio(slug)
    ep.garantir_pastas()
    return ep


# ------------------------------------------------------------------ comandos
def cmd_novo(args) -> None:
    base = RAIZ / "episodes" / args.slug
    if base.exists() and not args.forcar:
        raise SystemExit(f"{base} já existe (use --forcar)")
    base.mkdir(parents=True, exist_ok=True)
    serie = carregar_serie(args.serie)
    slug = args.serie
    ep_cfg = {
        "serie": slug,
        "titulo": args.titulo,
        "numero": args.numero,
        "ganchos": True,
        "semente": args.semente,
    }
    salvar_json(base / "ep.json", ep_cfg)
    (base / "roteiro.md").write_text(
        f"# Episódio {args.numero:02d} — {args.titulo}\n\n"
        "## Cena 1 — Abertura\n\n"
        f"<abra com um gancho: uma frase que só faz sentido no fim.>\n\n"
        "## Cena 2 — O mundo\n\n"
        "visual: caverna\n\n"
        "<descreva o cenário e o que o personagem vê.>\n\n"
        "> GANCHO\n\n"
        "Antes de continuar: se essa história te prendeu, deixa o like.\n\n"
        "## Cena 3 — O confronto\n\n"
        "<diálogo com outro personagem, revelação, reviravolta.>\n\n"
        "## Cena 4 — O fecho\n\n"
        "> PROXIMO\n\n"
        "<chamada para o próximo episódio.>\n",
        encoding="utf-8",
    )
    ok(f"episódio criado: {base}")
    print(f"   edite {base/'roteiro.md'} e rode: python -m fabrica roteiro {args.slug}")


def cmd_roteiro(args) -> None:
    caminho = roteiro.gerar_roteiro(args.slug, forcar=args.forcar)
    plan = ler_json(caminho)
    print(roteiro.resumo(plan))
    problemas = timeline.validar(_ep(args.slug))
    for p in problemas:
        aviso(p)


def cmd_narrar(args) -> None:
    ep = _ep(args.slug)
    if args.vozes:
        for v in voz.listar_vozes(args.vozes):
            print(v)
        return
    print("custo:", voz.custo_estimado(ep))
    voz.narrar(ep, forcar=args.forcar, provedor=args.provedor,
               apenas=args.apenas.split(",") if args.apenas else None)


def cmd_imagens(args) -> None:
    ep = _ep(args.slug)
    cv = ep.config["video"]
    imagens.planejar_imagens(ep, largura=cv["largura"], altura=cv["altura"], forcar=args.forcar)
    if not args.sem_thumb:
        imagens.gerar_thumbnail(ep, args.cena, linha2=args.linha2)


def cmd_timeline(args) -> None:
    ep = _ep(args.slug)
    for p in timeline.validar(ep):
        aviso(p)
    tl = timeline.montar(ep)
    salvar_json(ep.build / "timeline.json", tl)
    print(timeline.diagnostico(tl))
    # capítulos automáticos para a descrição do YouTube
    caps = [{"t": tempo(ev["inicio"])[:7], "id": ev["id"], "tipo": ev["tipo"]}
            for ev in tl["eventos"] if ev["tipo"] in ("cartao", "gancho", "cta", "proximo")]
    if caps:
        ep.plan["capitulos"] = [f"{c['t']} {c['id']}" for c in caps]
        ep.salvar_plan()


def cmd_render(args) -> None:
    ep = _ep(args.slug)
    if args.forcar_imagens:
        cv = ep.config["video"]
        imagens.planejar_imagens(ep, largura=cv["largura"], altura=cv["altura"], forcar=True)
    tl = timeline.montar(ep)
    if args.limite:
        tl["eventos"] = tl["eventos"][: args.limite]
        tl["total"] = tl["eventos"][-1]["fim"]
    salvar_json(ep.build / "timeline.json", tl)
    print(timeline.diagnostico(tl))
    render.renderizar(ep, tl, preview=args.preview)


def cmd_pacote(args) -> None:
    """Gera tudo que não é vídeo: thumbnail, srt, metadados, checklist."""
    ep = _ep(args.slug)
    if not any(c.get("imagem") for c in ep.cenas):
        imagens.planejar_imagens(ep, largura=ep.config["video"]["largura"],
                                 altura=ep.config["video"]["altura"])
    imagens.gerar_thumbnail(ep, args.cena, linha2=args.linha2)
    tl = timeline.montar(ep)
    from . import subtitles
    subtitles.escrever_srt(ep.base / "legendas.srt", subtitles.cues(tl))
    meta = publicar.metadados(ep)
    salvar_json(ep.base / "publicacao_meta.json", meta)
    ok(f"pacote pronto em {ep.base} (legendas.srt, thumbnail.jpg, publicacao_meta.json)")


def cmd_publicar(args) -> None:
    ep = _ep(args.slug)
    quando = datetime.fromisoformat(args.quando) if args.quando else None
    publicar.enviar(ep, quando=quando, agendado=args.agendar, dry_run=args.dry_run)


def cmd_auth(args) -> None:
    publicar.autorizar()


def cmd_serie(args) -> None:
    cfg = carregar_serie(args.nome)
    print(json.dumps(cfg, ensure_ascii=False, indent=2))


def cmd_arte(args) -> None:
    """Testa a arte procedural sem criar episódio."""
    saida = Path(args.saida)
    arte.gerar(args.arquetipo, args.semente, saida, largura=args.largura,
               altura=args.altura, paleta=args.paleta, figura=args.figura)
    ok(str(saida))


def cmd_diario(args) -> None:
    """Pipeline completo do próximo episódio pendente (para o cron semanal)."""
    fila = sorted((RAIZ / "episodes").glob("*/ep.json"))
    if not fila:
        raise SystemExit("nenhum episódio na fila")
    pendente = None
    for cfg_path in fila:
        slug = cfg_path.parent.name
        if not (cfg_path.parent / "final.mp4").exists():
            pendente = slug
            break
    if pendente is None and not args.repetir:
        ok("nada pendente — tudo já renderizado")
        return
    slug = pendente or fila[0].parent.name
    log(f"produzindo {slug}")
    roteiro.gerar_roteiro(slug)
    ep = _ep(slug)
    voz.narrar(ep)
    imagens.planejar_imagens(ep, largura=ep.config["video"]["largura"],
                             altura=ep.config["video"]["altura"])
    imagens.gerar_thumbnail(ep)
    timeline.montar(ep)
    render.renderizar(ep)
    publicar.enviar(ep, agendado=True, dry_run=args.dry_run)


# ------------------------------------------------------------------ parser
def montar_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="fabrica", description="Fábrica de vídeos dark para YouTube")
    sub = p.add_subparsers(dest="cmd", required=True)

    n = sub.add_parser("novo", help="cria a pasta e o esqueleto do roteiro")
    n.add_argument("slug")
    n.add_argument("--titulo", default="Novo episódio")
    n.add_argument("--numero", type=int, default=1)
    n.add_argument("--serie", default="vozes-do-abismo")
    n.add_argument("--semente", type=int, default=777)
    n.add_argument("--forcar", action="store_true")
    n.set_defaults(func=cmd_novo)

    r = sub.add_parser("roteiro", help="roteiro.md -> plan.json")
    r.add_argument("slug")
    r.add_argument("--forcar", action="store_true", help="descarta ajustes manuais")
    r.set_defaults(func=cmd_roteiro)

    v = sub.add_parser("narrar", help="gera a narração (TTS) por cena")
    v.add_argument("slug")
    v.add_argument("--provedor", choices=list(voz.PROVEDORES))
    v.add_argument("--forcar", action="store_true")
    v.add_argument("--apenas", help="ids separados por vírgula")
    v.add_argument("--vozes", help="lista vozes que contenham este filtro (ex: pt-BR)")
    v.set_defaults(func=cmd_narrar)

    i = sub.add_parser("imagens", help="gera/reaproveita a imagem de cada cena")
    i.add_argument("slug")
    i.add_argument("--cena", help="id da cena para a thumbnail")
    i.add_argument("--linha2", default="", help="segunda linha da thumbnail")
    i.add_argument("--forcar", action="store_true")
    i.add_argument("--sem-thumb", action="store_true")
    i.set_defaults(func=cmd_imagens)

    t = sub.add_parser("timeline", help="mostra durações e offsets")
    t.add_argument("slug")
    t.set_defaults(func=cmd_timeline)

    rd = sub.add_parser("render", help="renderiza o MP4 final")
    rd.add_argument("slug")
    rd.add_argument("--preview", action="store_true", help="720p, mais rápido")
    rd.add_argument("--limite", type=int, help="renderiza só as N primeiras cenas")
    rd.add_argument("--forcar-imagens", action="store_true")
    rd.set_defaults(func=cmd_render)

    pc = sub.add_parser("pacote", help="thumbnail + srt + metadados")
    pc.add_argument("slug")
    pc.add_argument("--cena")
    pc.add_argument("--linha2", default="")
    pc.set_defaults(func=cmd_pacote)

    pb = sub.add_parser("publicar", help="envia para o YouTube")
    pb.add_argument("slug")
    pb.add_argument("--agendar", action="store_true", help="agenda para o próximo slot")
    pb.add_argument("--quando", help="ISO, ex: 2026-10-30T18:00:00-03:00")
    pb.add_argument("--dry-run", action="store_true")
    pb.set_defaults(func=cmd_publicar)

    a = sub.add_parser("auth", help="autoriza o acesso ao YouTube (OAuth)")
    a.set_defaults(func=cmd_auth)

    s = sub.add_parser("serie", help="mostra a configuração efetiva de uma série")
    s.add_argument("nome", nargs="?", default="vozes-do-abismo")
    s.set_defaults(func=cmd_serie)

    ar = sub.add_parser("arte", help="gera uma arte procedural de teste")
    ar.add_argument("arquetipo")
    ar.add_argument("saida")
    ar.add_argument("--semente", type=int, default=1)
    ar.add_argument("--largura", type=int, default=1920)
    ar.add_argument("--altura", type=int, default=1080)
    ar.add_argument("--paleta")
    ar.add_argument("--figura", action="store_true")
    ar.set_defaults(func=cmd_arte)

    pv = sub.add_parser("preview", help="página de revisão com quadros e timeline")
    pv.add_argument("slug")
    pv.add_argument("--frames", type=int, default=12)
    pv.set_defaults(func=cmd_preview)

    d = sub.add_parser("diario", help="produz e agenda o próximo episódio pendente")
    d.add_argument("--repetir", action="store_true")
    d.add_argument("--dry-run", action="store_true")
    d.set_defaults(func=cmd_diario)
    return p


def main(argv: list[str] | None = None) -> None:
    args = montar_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()


def cmd_preview(args) -> None:
    """Monta uma página de revisão (vídeo + folha de contato + timeline)."""
    from . import frames

    ep = _ep(args.slug)
    if not ep.saida.exists():
        raise SystemExit(f"renderize antes: {ep.saida}")
    pagina = frames.pagina_revisao(ep, quantidade=args.frames)
    ok(f"página: {pagina}")
    print(f"   abra com: python -m http.server -d {ep.base} 8000")
