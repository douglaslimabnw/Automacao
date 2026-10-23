"""Trilha e efeitos sonoros procedurais (100% livres de direitos).

A ideia: nenhum banco de músicas, nenhuma assinatura. A trilha de cada
episódio é sintetizada a partir de um "mood" e de uma semente, então dois
episódios nunca soam iguais — e o canal não corre risco de Content ID.
"""
from __future__ import annotations

import math
import struct
import wave
from pathlib import Path

import numpy as np

SR = 48_000

# Frequências base (Lá = 440). Tons menores soam "dark".
ESCALAS = {
    "melancolico": [0, 3, 7, 10],      # menor com sétima
    "tenso": [0, 1, 5, 6],             # cromatismo / trítono
    "epico": [0, 5, 7, 12],            # quintas abertas
    "misterioso": [0, 2, 6, 9],        # ambíguo, quartas
    "funesto": [0, 1, 7, 8],           # meio-tom + quinta
}
NOTAS = {"D": -7, "E": -5, "F": -4, "G": -2, "A": 0, "B": 2, "C": 3}


def _hz(semitons: float, base: float = 55.0) -> float:
    return base * (2 ** (semitons / 12))


def _env_ad(n: int, ataque: float, decaimento: float) -> np.ndarray:
    """Envelope ataque/decaimento exponencial."""
    a = max(1, int(ataque * SR))
    env = np.ones(n)
    env[: min(a, n)] = np.linspace(0, 1, min(a, n))
    tail = np.exp(-np.linspace(0, decaimento, n))
    return env * tail


def _reverb(x: np.ndarray, segundos: float = 3.2, mistura: float = 0.35) -> np.ndarray:
    """Reverb por convolução com uma resposta impulsiva sintética (FFT)."""
    n_ir = int(segundos * SR)
    if n_ir < 16 or x.size == 0:
        return x
    rng = np.random.default_rng(7)
    ir = rng.standard_normal(n_ir) * np.exp(-np.linspace(0, 6.5, n_ir))
    ir[: int(0.012 * SR)] *= np.linspace(0, 1, int(0.012 * SR))  # pré-delay curto
    ir /= np.max(np.abs(ir)) + 1e-9
    n = 1 << int(math.ceil(math.log2(x.size + n_ir)))
    y = np.fft.irfft(np.fft.rfft(x, n) * np.fft.rfft(ir, n), n)[: x.size]
    y /= np.max(np.abs(y)) + 1e-9
    return (1 - mistura) * x / (np.max(np.abs(x)) + 1e-9) + mistura * y


def _fade(x: np.ndarray, entrada: float = 2.0, saida: float = 3.0) -> np.ndarray:
    n = x.size
    a = min(int(entrada * SR), n // 2)
    b = min(int(saida * SR), n // 2)
    if a:
        x[:a] *= np.linspace(0, 1, a)
    if b:
        x[-b:] *= np.linspace(1, 0, b)
    return x


def trilha(duracao: float, mood: str = "melancolico", semente: int = 0,
           intensidade: float = 0.3) -> np.ndarray:
    """Gera uma trilha estéreo float32 de `duracao` segundos."""
    rng = np.random.default_rng(semente)
    n = int(duracao * SR)
    t = np.arange(n) / SR
    escala = ESCALAS.get(mood, ESCALAS["melancolico"])
    tonica = rng.choice(list(NOTAS.values()))
    base = _hz(tonica, 55.0)
    mix = np.zeros(n, dtype=np.float64)

    # 1. Drone: duas vozes levemente desafinadas + quinta, com batimento lento
    for i, intervalo in enumerate(escala[:3]):
        f = _hz(intervalo + 12 * (i % 2))
        det = 1 + rng.uniform(-0.0015, 0.0015)
        amp = 0.30 / (i + 1)
        fase = rng.uniform(0, 6.28)
        mix += amp * np.sin(2 * np.pi * base * f * det * t + fase)
    lfo = 0.55 + 0.45 * np.sin(2 * np.pi * 0.045 * t + rng.uniform(0, 6.28))
    mix *= lfo

    # 2. Pad de ruído filtrado (FFT low-pass) — a "poeira" do ambiente
    ruido = rng.standard_normal(n)
    corte = int(max(80, min(n // 2 - 1, 380 / (SR / 2) * (n // 2))))
    espectro = np.fft.rfft(ruido)
    espectro[corte:] *= np.exp(-np.linspace(0, 8, espectro.size - corte))
    pad = np.fft.irfft(espectro, n)
    pad /= np.max(np.abs(pad)) + 1e-9
    swell = 0.35 + 0.65 * (0.5 + 0.5 * np.sin(2 * np.pi * 0.031 * t - 1.2))
    mix += 0.22 * pad * swell

    # 3. Pulso grave (coração) — a cada 4 tempos bem lentos
    bpm = {"tenso": 64, "epico": 58, "melancolico": 44}.get(mood, 40)
    periodo = 60 / bpm
    k = 0
    while True:
        ini = int(k * periodo * SR)
        if ini >= n:
            break
        dur = int(0.55 * SR)
        seg = min(dur, n - ini)
        tt = np.arange(seg) / SR
        env = np.exp(-tt * 7.5)
        batida = np.sin(2 * np.pi * 42 * tt) * env + 0.35 * np.sin(2 * np.pi * 84 * tt) * env**2
        mix[ini : ini + seg] += 0.5 * batida[:seg]
        k += 1

    # 4. Brilho distante (sino) esporádico, só em moods etéreos
    if mood in ("misterioso", "melancolico"):
        for ini_s in rng.uniform(6, max(7, duracao - 4), size=max(2, int(duracao / 26))):
            ini = int(ini_s * SR)
            dur = int(3.2 * SR)
            seg = min(dur, n - ini)
            if seg <= 0:
                continue
            tt = np.arange(seg) / SR
            f = _hz(rng.choice(escala), 220.0)
            sino = (np.sin(2 * np.pi * f * tt) + 0.4 * np.sin(2 * np.pi * 2.76 * f * tt)) * np.exp(-tt * 2.2)
            mix[ini : ini + seg] += 0.09 * sino

    mix = _fade(mix, entrada=3.0, saida=4.0)
    mix /= np.max(np.abs(mix)) + 1e-9
    mix *= float(np.clip(intensidade, 0.02, 1.0)) * 1.6

    # Estéreo com pequeno atraso/decorrelação
    esq = mix
    dir_ = np.roll(mix, int(0.011 * SR)) * 0.98
    est = np.stack([esq, dir_], axis=1)
    return est.astype(np.float32)


def whoosh(duracao: float = 1.1, semente: int = 1) -> np.ndarray:
    rng = np.random.default_rng(semente)
    n = int(duracao * SR)
    t = np.arange(n) / SR
    env = np.sin(np.pi * np.clip(t / duracao, 0, 1)) ** 2
    ruido = rng.standard_normal(n)
    # varredura de banda feita por FFT por blocos (barato e suficiente)
    saida = np.zeros(n)
    blocos = 8
    tam = n // blocos
    for i in range(blocos):
        a, b = i * tam, (i + 1) * tam if i < blocos - 1 else n
        seg = ruido[a:b]
        esp = np.fft.rfft(seg)
        centro = int((150 + 1800 * (i / blocos)) / (SR / 2) * esp.size)
        ganho = np.exp(-((np.arange(esp.size) - centro) ** 2) / (2 * (esp.size * 0.08) ** 2))
        saida[a:b] = np.fft.irfft(esp * ganho, seg.size)
    saida /= np.max(np.abs(saida)) + 1e-9
    chirp = np.sin(2 * np.pi * (180 + 900 * (t / duracao) ** 2) * t) * 0.25
    return (saida * 0.8 + chirp) * env * 0.5


def impacto(duracao: float = 2.2) -> np.ndarray:
    n = int(duracao * SR)
    t = np.arange(n) / SR
    f = 92 * np.exp(-t * 1.6) + 32
    corpo = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 1.8)
    rng = np.random.default_rng(3)
    estalo = rng.standard_normal(n) * np.exp(-t * 26) * 0.35
    return (corpo + estalo) * 0.7


def riser(duracao: float = 2.6) -> np.ndarray:
    n = int(duracao * SR)
    t = np.arange(n) / SR
    rng = np.random.default_rng(5)
    ruido = rng.standard_normal(n)
    esp = np.fft.rfft(ruido)
    env = np.linspace(0.02, 1, n) ** 2
    tom = np.sin(2 * np.pi * (200 * np.exp(t * 0.55)) * t) * 0.3
    ruido = np.fft.irfft(esp * np.linspace(0.2, 1, esp.size), n)
    ruido /= np.max(np.abs(ruido)) + 1e-9
    return ((ruido * 0.8 + tom) * env * 0.45)


def salvar_wav(caminho: Path | str, audio: np.ndarray, sr: int = SR) -> Path:
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    if audio.ndim == 1:
        audio = np.stack([audio, audio], axis=1)
    pcm = np.clip(audio, -1, 1)
    pcm = (pcm * 32767).astype(np.int16)
    with wave.open(str(caminho), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    return caminho
