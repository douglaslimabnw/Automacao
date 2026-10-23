"""Voz: narração por cena, com cache e provedores plugáveis.

Provedores:
  edge        Microsoft Edge TTS (grátis, precisa de internet)  -> padrão
  elevenlabs  API paga, voz clonada                             (ELEVENLABS_API_KEY)
  openai      API paga, tts-1/tts-1-hd                          (OPENAI_API_KEY)
  arquivo     você coloca manualmente narracao/<id>.mp3
  silencio    só para testar o pipeline (sem áudio falado)

Cada fala é gravada em episodes/<slug>/narracao/<id>.mp3, então re-renderizar
não gasta cota nem tempo. Mude o texto -> hash muda -> regrava só aquela cena.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import time
from pathlib import Path

from .util import aviso, duracao, log, ok

CACHE = "narracao/_cache.json"


def _hash(texto: str, cfg: dict) -> str:
    base = json.dumps([texto, cfg.get("provedor"), cfg.get("voz"), cfg.get("velocidade"), cfg.get("tom")],
                      ensure_ascii=False)
    return hashlib.sha1(base.encode()).hexdigest()[:16]


def _edge(texto: str, destino: Path, cfg: dict) -> None:
    try:
        import edge_tts
    except ImportError:
        raise SystemExit("instale: pip install edge-tts")
    async def _run():
        com = edge_tts.Communicate(
            texto,
            cfg.get("voz", "pt-BR-AntonioNeural"),
            rate=str(cfg.get("velocidade", "-8%")),
            pitch=str(cfg.get("tom", "-4Hz")),
        )
        await com.save(str(destino))
    ultimo = None
    for tentativa in range(3):
        try:
            asyncio.run(_run())
            if destino.exists() and destino.stat().st_size > 1200:
                return
            raise RuntimeError("arquivo vazio")
        except Exception as e:  # rede instável
            ultimo = e
            time.sleep(2 + tentativa * 3)
    raise RuntimeError(f"edge-tts falhou: {ultimo}")


def _elevenlabs(texto: str, destino: Path, cfg: dict) -> None:
    import urllib.request

    chave = os.environ.get("ELEVENLABS_API_KEY")
    if not chave:
        raise SystemExit("defina ELEVENLABS_API_KEY")
    voz = cfg.get("voz_id") or cfg.get("voz", "")
    corpo = json.dumps({
        "text": texto,
        "model_id": cfg.get("modelo", "eleven_multilingual_v2"),
        "voice_settings": {"stability": 0.45, "similarity_boost": 0.8, "style": 0.35},
    }).encode()
    req = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voz}",
        data=corpo,
        headers={"xi-api-key": chave, "Content-Type": "application/json",
                 "Accept": "audio/mpeg"},
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        destino.write_bytes(r.read())


def _openai(texto: str, destino: Path, cfg: dict) -> None:
    import urllib.request

    chave = os.environ.get("OPENAI_API_KEY")
    if not chave:
        raise SystemExit("defina OPENAI_API_KEY")
    corpo = json.dumps({
        "model": cfg.get("modelo", "tts-1-hd"),
        "voice": cfg.get("voz", "onyx"),
        "input": texto,
        "speed": float(cfg.get("speed", 0.95)),
        "response_format": "mp3",
    }).encode()
    req = urllib.request.Request(
        "https://api.openai.com/v1/audio/speech", data=corpo,
        headers={"Authorization": f"Bearer {chave}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=180) as r:
        destino.write_bytes(r.read())


def _silencio(texto: str, destino: Path, cfg: dict) -> None:
    """Placeholder para testes: gera um tom baixo com a duração estimada."""
    from . import audio_gen
    from .timeline import duracao_estimada
    import numpy as np

    seg = max(0.6, duracao_estimada(texto))
    n = int(seg * 48000)
    t = np.arange(n) / 48000
    tom = 0.02 * np.sin(2 * np.pi * 110 * t) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.7 * t))
    audio_gen.salvar_wav(destino.with_suffix(".wav"), tom)
    # converte para mp3 para manter o mesmo formato
    from .util import ffmpeg, run
    run([ffmpeg(), "-y", "-i", str(destino.with_suffix(".wav")), str(destino)])
    destino.with_suffix(".wav").unlink(missing_ok=True)


PROVEDORES = {"edge": _edge, "elevenlabs": _elevenlabs, "openai": _openai,
              "silencio": _silencio}


def narrar(ep, *, forcar: bool = False, provedor: str | None = None,
           apenas: list[str] | None = None) -> dict:
    """Gera a narração de todas as cenas que têm texto."""
    ep.garantir_pastas()
    cfg = dict(ep.config.get("voz", {}))
    if provedor:
        cfg["provedor"] = provedor
    nome = cfg.get("provedor", "edge")
    if nome not in PROVEDORES:
        raise SystemExit(f"provedor de voz desconhecido: {nome}. Opções: {list(PROVEDORES)}")
    if nome == "arquivo":
        log("provedor 'arquivo': coloque os mp3 em narracao/<id>.mp3")
        return {}

    cache_path = ep.narracao / "_cache.json"
    cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    geradas, puladas = 0, 0
    info = {}
    for cena in ep.cenas:
        texto = (cena.get("narracao") or "").strip()
        if not texto or (apenas and cena["id"] not in apenas):
            continue
        destino = ep.narracao / f"{cena['id']}.mp3"
        h = _hash(texto, cfg)
        if destino.exists() and cache.get(cena["id"]) == h and not forcar:
            puladas += 1
        else:
            log(f"narrando {cena['id']} ({len(texto.split())} palavras)")
            try:
                PROVEDORES[nome](texto, destino, cfg)
            except Exception as e:
                aviso(f"falhou {cena['id']}: {e}")
                raise
            cache[cena["id"]] = h
            geradas += 1
        if destino.exists():
            info[cena["id"]] = round(duracao(destino), 2)
    cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=1))
    total = sum(info.values())
    ok(f"narração: {geradas} novas, {puladas} em cache · {total/60:.1f} min de fala")
    return info


def custo_estimado(ep, preco_por_mil_caracteres: float = 0.0) -> str:
    chars = sum(len(c.get("narracao", "")) for c in ep.cenas)
    minutos = sum(duracao_estimada(c.get("narracao", "")) for c in ep.cenas) / 60
    linhas = [f"{chars} caracteres · ~{minutos:.1f} min de fala"]
    if preco_por_mil_caracteres:
        linhas.append(f"custo estimado: US$ {chars/1000*preco_por_mil_caracteres:.2f}")
    return "  ".join(linhas)


def listar_vozes(filtro: str = "pt-BR") -> list[str]:
    try:
        import edge_tts
    except ImportError:
        return []
    vozes = asyncio.run(edge_tts.list_voices())
    return [v["ShortName"] for v in vozes if filtro in v["ShortName"]]
