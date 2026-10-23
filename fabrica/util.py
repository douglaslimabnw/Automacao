"""Utilitários: localização do ffmpeg, execução de comandos e sonda de mídia.

Não dependemos de ffprobe (a build estática do ffmpeg usada aqui não o traz),
então a duração é lida do stderr do próprio ffmpeg.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

# Permite apontar a fábrica para outra árvore de episódios (útil em testes/CI)
RAIZ = Path(os.environ.get("FABRICA_RAIZ") or Path(__file__).resolve().parent.parent)

_ffmpeg_cache: str | None = None


def ffmpeg() -> str:
    """Descobre o binário do ffmpeg.

    Ordem: variável FFMPEG -> PATH -> binário embutido do pacote imageio-ffmpeg.
    """
    global _ffmpeg_cache
    if _ffmpeg_cache:
        return _ffmpeg_cache
    candidatos = []
    if os.environ.get("FFMPEG"):
        candidatos.append(os.environ["FFMPEG"])
    if shutil.which("ffmpeg"):
        candidatos.append(shutil.which("ffmpeg"))
    try:  # fallback: wheel do imageio-ffmpeg (traz um ffmpeg estático completo)
        import imageio_ffmpeg

        candidatos.append(imageio_ffmpeg.get_ffmpeg_exe())
    except Exception:
        pass
    for c in candidatos:
        if c and Path(c).exists():
            _ffmpeg_cache = c
            return c
    raise RuntimeError(
        "ffmpeg não encontrado. Instale o ffmpeg ou rode: pip install imageio-ffmpeg"
    )


def run(cmd: list[str], *, quiet: bool = True, check: bool = True) -> subprocess.CompletedProcess:
    """Executa um comando, capturando stderr (é onde o ffmpeg fala)."""
    if not quiet:
        print(" ".join(str(c) for c in cmd)[:400])
    p = subprocess.run(
        [str(c) for c in cmd],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if check and p.returncode != 0:
        raise RuntimeError(
            f"comando falhou ({p.returncode}): {' '.join(str(c) for c in cmd)[:300]}\n"
            f"{p.stderr[-3000:]}"
        )
    return p


def duracao(caminho: Path | str) -> float:
    """Duração em segundos de qualquer mídia, via stderr do ffmpeg."""
    p = run([ffmpeg(), "-hide_banner", "-i", str(caminho)], check=False)
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", p.stderr)
    if not m:
        raise RuntimeError(f"não consegui ler a duração de {caminho}")
    h, mi, s = m.groups()
    return int(h) * 3600 + int(mi) * 60 + float(s)


def tem_audio(caminho: Path | str) -> bool:
    p = run([ffmpeg(), "-hide_banner", "-i", str(caminho)], check=False)
    return "Audio:" in p.stderr


def info(caminho: Path | str) -> dict:
    """Metadados básicos: duração, streams de vídeo/áudio, resolução."""
    p = run([ffmpeg(), "-hide_banner", "-i", str(caminho)], check=False)
    out = {"duracao": None, "video": None, "audio": False}
    try:
        out["duracao"] = duracao(caminho)
    except Exception:
        pass
    m = re.search(r"Video:.*?(\d{2,5})x(\d{2,5})", p.stderr)
    if m:
        out["video"] = (int(m.group(1)), int(m.group(2)))
    out["audio"] = "Audio:" in p.stderr
    return out


def ler_json(caminho: Path | str) -> dict:
    return json.loads(Path(caminho).read_text(encoding="utf-8"))


def salvar_json(caminho: Path | str, dados) -> None:
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")


def log(msg: str) -> None:
    print(f"\033[36m▸\033[0m {msg}", file=sys.stderr, flush=True)


def ok(msg: str) -> None:
    print(f"\033[32m✔\033[0m {msg}", file=sys.stderr, flush=True)


def aviso(msg: str) -> None:
    print(f"\033[33m!\033[0m {msg}", file=sys.stderr, flush=True)


def tempo(seg: float) -> str:
    """Segundos -> 00:00:00.000 (formato SRT/ffmpeg)."""
    ms = int(round(seg * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"
