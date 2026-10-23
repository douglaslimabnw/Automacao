"""Renderizador: transforma a timeline + imagens em um MP4 pronto para o YouTube.

Cadeia de vídeo por cena:
  imagem -> upscale -> Ken Burns (zoompan) -> grão -> color grade frio ->
  vinheta -> micro-tremor de câmera -> clipe .mp4

Depois: crossfades (xfade), cartões, legendas queimadas, mixagem de áudio
(narração + trilha procedural + SFX com ducking) e normalização para -14 LUFS.
"""
from __future__ import annotations

import math
import shutil
from pathlib import Path

import numpy as np

from . import audio_gen, subtitles
from .timeline import ordem_visual
from .util import ffmpeg, log, ok, run, tempo

MOVIMENTOS = ("zoom_in", "zoom_out", "pan_esq", "pan_dir", "zoom_in_lento")


def _kenburns(mov: str, frames: int, estilo: dict) -> str:
    z = float(estilo.get("zoom", 0.06))
    n = max(frames, 2)
    if mov == "zoom_out":
        zexpr = f"{1 + z:.4f}-{z:.4f}*on/{n}"
        x, y = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    elif mov in ("pan_esq", "pan_dir"):
        zexpr = f"{1 + z * 0.6:.4f}"
        direcao = "(on/{n})" if mov == "pan_dir" else f"(1-on/{n})"
        x = f"(iw-iw/zoom)*{direcao}"
        y = "ih/2-(ih/zoom/2)"
    else:  # zoom in
        velocidade = 0.5 if mov == "zoom_in_lento" else 1.0
        zexpr = f"1+{z * velocidade:.4f}*on/{n}"
        x, y = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    return (
        f"zoompan=z='{zexpr}':x='{x}':y='{y}':d={n}:s=WxH:fps=FPS"
    )


def _filtros_video(estilo: dict, frames: int, mov: str, largura: int, altura: int,
                   fps: int) -> str:
    z = float(estilo.get("zoom", 0.06))
    kb = _kenburns(mov, frames, estilo).replace("WxH", f"{largura}x{altura}").replace("FPS", str(fps))
    gr = float(estilo.get("grao", 6))
    trem = float(estilo.get("tremor", 0.35))
    w2, h2 = largura - 10, altura - 10
    partes = [
        # margem extra para o crop/tremor não mostrar borda
        f"scale={int(largura*2)}:{int(altura*2)}:force_original_aspect_ratio=increase:flags=lanczos",
        f"crop={int(largura*2)}:{int(altura*2)}",
        kb,
        f"eq=contrast={estilo.get('contraste', 1.08)}:brightness={estilo.get('brilho', -0.03)}:"
        f"saturation={estilo.get('saturacao', 0.86)}:gamma=0.98",
        "colorbalance=rs=-0.03:gs=0.01:bs=0.06:rm=-0.01:bm=0.03:rh=0.03:bh=-0.02",
        "unsharp=5:5:0.55:5:5:0.0",
    ]
    if trem > 0:
        partes.append(
            f"crop={w2}:{h2}:"
            f"'{5 + trem*6*math.sin(0.9):.2f}+{trem*5:.2f}*sin(2*PI*t*0.73)'"
            f":'{5 + trem*4*math.cos(0.8):.2f}+{trem*5:.2f}*cos(2*PI*t*0.61)'"
        )
        partes.append(f"scale={largura}:{altura}")
    if float(estilo.get("vinheta", 0.55)) > 0:
        # ângulo maior = vinheta mais sutil; 5.0 ~ cantos a ~70% do centro
        partes.append(f"vignette=angle=PI/{5.4 - float(estilo.get('vinheta', 0.55)) * 0.9:.2f}:mode=forward")
    if gr > 0:
        partes.append(f"noise=alls={gr}:allf=t+u")
    partes += ["format=yuv420p", f"fps={fps}"]
    return ",".join(partes)


def _render_cena(ep, ev: dict, estilo: dict, saida: Path, cfg_video: dict) -> Path:
    largura, altura = cfg_video["largura"], cfg_video["altura"]
    fps = cfg_video["fps"]
    frames = max(2, int(round(ev["duracao"] * fps)))
    filtros = _filtros_video(estilo, frames, ev.get("movimento", "zoom_in"), largura, altura, fps)

    imagem = ep.caminho_relativo(ev.get("imagem"))
    clipe = ep.caminho_relativo(ev.get("clip"))

    if clipe and Path(clipe).exists():
        cmd = [
            ffmpeg(), "-y", "-stream_loop", "-1", "-i", str(clipe),
            "-t", f"{ev['duracao']:.3f}",
            "-vf", (
                f"scale={largura}:{altura}:force_original_aspect_ratio=increase:flags=lanczos,"
                f"crop={largura}:{altura},"
                f"eq=contrast={estilo.get('contraste', 1.08)}:saturation={estilo.get('saturacao', 0.86)}:"
                f"brightness={estilo.get('brilho', -0.03)},"
                f"vignette=angle=PI/5,noise=alls={int(estilo.get('grao', 6))}:allf=t+u,"
                f"fps={fps},format=yuv420p"
            ),
        ]
    elif imagem and Path(imagem).exists():
        cmd = [
            ffmpeg(), "-y", "-i", str(imagem),
            "-vf", filtros, "-frames:v", str(frames), "-r", str(fps),
        ]
    else:
        raise FileNotFoundError(f"cena {ev['id']} sem imagem/clipe")

    cmd += [
        "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "17",
        "-pix_fmt", "yuv420p", "-g", str(fps * 2), str(saida),
    ]
    run(cmd)
    return saida


def _concatenar(clipes: list[Path], duracoes: list[float], transicoes: list[float],
                saida: Path, cfg_video: dict, ass: Path | None, fonte_dir: Path) -> Path:
    """Concatena com xfade e (opcionalmente) queima legendas em uma única passada."""
    if len(clipes) == 1:
        shutil.copy(clipes[0], saida)
        return saida
    entradas: list[str] = []
    for c in clipes:
        entradas += ["-i", str(c)]

    partes, atual = [], "[0:v]"
    acumulado = duracoes[0]
    for i in range(1, len(clipes)):
        tr = max(0.05, transicoes[i - 1])
        offset = acumulado - tr
        tipo = "fade"
        marca = f"[x{i}]"
        partes.append(
            f"{atual}[{i}:v]xfade=transition={tipo}:duration={tr:.3f}:offset={offset:.3f}{marca}"
        )
        atual = marca
        acumulado = acumulado + duracoes[i] - tr
    ultimo = atual
    if ass and ass.exists():
        partes.append(
            f"{ultimo}ass=filename='{ass}':fontsdir='{fonte_dir}'[vout]"
        )
        ultimo = "[vout]"

    cmd = [ffmpeg(), "-y", *entradas, "-filter_complex", ";".join(partes),
           "-map", ultimo,
           "-c:v", "libx264", "-preset", cfg_video.get("preset", "medium"),
           "-crf", str(cfg_video.get("crf", 20)), "-pix_fmt", "yuv420p",
           "-r", str(cfg_video["fps"]), "-g", str(cfg_video["fps"] * 2),
           "-movflags", "+faststart", str(saida)]
    run(cmd)
    return saida


def _montar_audio(ep, tl: dict, cfg: dict, saida: Path) -> Path:
    """Narração + trilha procedural + SFX, com ducking e loudness de YouTube."""
    total = tl["total"]
    base = ep.build
    musica = ep.base / "trilha" / "bed.wav"
    mood = cfg["trilha"].get("mood", "melancolico")
    if cfg["trilha"].get("modo") == "procedural":
        if not musica.exists():
            log(f"sintetizando trilha ({mood})")
            audio_gen.salvar_wav(
                musica,
                audio_gen.trilha(total + 1.0, mood=mood,
                                 semente=int(cfg["estilo"].get("semente_base", 777)) + int(ep.plan.get("episodio", 1)),
                                 intensidade=float(cfg["trilha"].get("intensidade", 0.3))),
            )
    elif cfg["trilha"].get("modo") == "arquivo" and musica.exists():
        pass
    else:
        musica = None

    entradas: list[str] = []
    filtros: list[str] = []
    vozes: list[str] = []
    idx = 0

    # 1. narração
    for ev in tl["eventos"]:
        if not ev.get("audio"):
            continue
        p = ep.base / ev["audio"]
        entradas += ["-i", str(p)]
        ms = int(round(ev["inicio"] * 1000))
        etiqueta = f"[n{idx}]"
        filtros.append(
            f"[{idx}:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,"
            f"adelay={ms}|{ms},volume=1.0{etiqueta}"
        )
        vozes.append(etiqueta)
        idx += 1

    if vozes:
        if len(vozes) == 1:
            filtros.append(f"{vozes[0]}alimiter=limit=0.95[voz]")
        else:
            filtros.append(
                f"{''.join(vozes)}amix=inputs={len(vozes)}:normalize=0:dropout_transition=0,"
                f"alimiter=limit=0.95[voz]"
            )
        voz_rotulo = "[voz]"
    else:
        voz_rotulo = None

    # 2. trilha (com ducking pela voz, via sidechain)
    musica_rotulo = None
    if musica and Path(musica).exists():
        entradas += ["-i", str(musica)]
        m_idx = idx
        idx += 1
        base_mus = (f"[{m_idx}:a]aresample=48000,"
                    f"aformat=sample_fmts=fltp:channel_layouts=stereo,volume=1.0")
        if voz_rotulo:
            # um rótulo de filtro só pode ser consumido uma vez -> asplit
            filtros.append(f"{voz_rotulo}asplit=2[vozmix][vozsc]")
            voz_rotulo = "[vozmix]"
            filtros.append(
                f"{base_mus}[mus];"
                f"[mus][vozsc]sidechaincompress=threshold=0.045:ratio=9:attack=12:"
                f"release=340:makeup=1[musd]"
            )
        else:
            filtros.append(f"{base_mus}[musd]")
        musica_rotulo = "[musd]"

    # 3. SFX nas transições e nos ganchos
    sfx_rotulos = []
    for ev in tl["eventos"]:
        if ev["tipo"] in ("gancho",) or ev.get("sfx") == "impacto":
            tipo, pos, dur = "impacto", max(0.0, ev["inicio"] - 0.15), 2.2
        elif ev["tipo"] in ("cartao", "cta"):
            tipo, pos, dur = "riser", max(0.0, ev["inicio"] - 1.2), 2.6
        else:
            continue
        gerador = audio_gen.impacto if tipo == "impacto" else audio_gen.riser
        arq = base / f"sfx_{ev['id']}.wav"
        if not arq.exists():
            audio_gen.salvar_wav(arq, gerador(dur) * 0.55)
        entradas += ["-i", str(arq)]
        ms = int(pos * 1000)
        filtros.append(
            f"[{idx}:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,"
            f"adelay={ms}|{ms}[s{idx}]"
        )
        sfx_rotulos.append(f"[s{idx}]")
        idx += 1

    mix_final = []
    if voz_rotulo:
        mix_final.append(voz_rotulo)
    if musica_rotulo:
        mix_final.append(musica_rotulo)
    mix_final += sfx_rotulos

    if not mix_final:
        raise RuntimeError("nenhum áudio para mixar (sem narração, trilha ou sfx)")

    if len(mix_final) == 1:
        filtros.append(f"{mix_final[0]}apad=whole_dur={total:.3f}[mix]")
    else:
        filtros.append(
            f"{''.join(mix_final)}amix=inputs={len(mix_final)}:normalize=0:dropout_transition=0,"
            f"apad=whole_dur={total:.3f}[mix]"
        )
    alvo = float(cfg["video"].get("loudness", -14))
    filtros.append(
        f"[mix]loudnorm=I={alvo}:TP=-1.5:LRA=11:print_format=summary,"
        f"aresample=48000,atrim=0:{total:.3f}[aout]"
    )

    cmd = [ffmpeg(), "-y", *entradas, "-filter_complex", ";".join(filtros),
           "-map", "[aout]", "-c:a", "aac", "-b:a", cfg["video"].get("audio_bitrate", "192k"),
           "-ar", "48000", str(saida)]
    run(cmd)
    return saida


def renderizar(ep, tl: dict | None = None, *, preview: bool = False) -> Path:
    """Renderiza o episódio completo -> episodes/<slug>/final.mp4"""
    from .timeline import montar

    ep.garantir_pastas()
    cfg = ep.config
    cv = cfg["video"]
    estilo = cfg["estilo"]
    if preview:
        cv = {**cv, "largura": 1280, "altura": 720, "preset": "veryfast", "crf": 23}
    tl = tl or montar(ep)

    # 1. clipes por cena
    clipes, duracoes, transicoes = [], [], []
    total_estimado = sum(e["duracao"] for e in tl["eventos"])
    log(f"renderizando {len(tl['eventos'])} cenas ({tempo(total_estimado)})")
    for ev in tl["eventos"]:
        destino = ep.build / f"cena_{ev['id']}.mp4"
        if not destino.exists() or preview:
            _render_cena(ep, ev, estilo, destino, cv)
            print(f"    · {ev['id']} {ev['duracao']:5.1f}s  {ev['tipo']}", flush=True)
        clipes.append(destino)
        duracoes.append(ev["duracao"])
        transicoes.append(float(estilo.get("transicao", 0.7)) if ev["tipo"] != "cartao" else 0.9)
    ok("cenas renderizadas")

    # 2. legendas
    lista_cues = subtitles.cues(tl)
    srt = subtitles.escrever_srt(ep.base / "legendas.srt", lista_cues)
    ass = None
    modo = str(estilo.get("legendas", "burn")).lower()
    if modo == "burn":
        ass = subtitles.escrever_ass(
            ep.build / "legendas.ass", lista_cues,
            fonte=Path(estilo.get("fonte_legenda", "assets/brand/fonts/BebasNeue.ttf")),
            largura=cv["largura"], altura=cv["altura"],
            tamanho=int(56 * cv["largura"] / 1920),
        )
    ok(f"legendas: {len(lista_cues)} blocos ({modo})")

    # 3. vídeo com crossfades + legendas
    video = ep.build / "video.mp4"
    _concatenar(clipes, duracoes, transicoes, video, cv, ass,
                Path(cfg["estilo"].get("fonte_legenda", "assets/brand/fonts")).parent)
    ok("vídeo concatenado")

    # 4. áudio
    audio = _montar_audio(ep, tl, cfg, ep.build / "audio.m4a")
    ok("áudio mixado")

    # 5. mux final
    cmd = [ffmpeg(), "-y", "-i", str(video), "-i", str(audio),
           "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "copy",
           "-shortest", "-movflags", "+faststart", str(ep.saida)]
    run(cmd)
    ok(f"final: {ep.saida} ({ep.saida.stat().st_size/1e6:.1f} MB)")
    return ep.saida
