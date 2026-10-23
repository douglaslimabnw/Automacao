"""Legendas: SRT (para o YouTube) e ASS estilizado (para queimar no vídeo)."""
from __future__ import annotations

import re
from pathlib import Path

from .util import RAIZ, tempo

F_LEGENDA = RAIZ / "assets/brand/fonts/BebasNeue.ttf"
MAX_CHARS = 42
MAX_PALAVRAS = 7


def _limpar(texto: str) -> str:
    texto = re.sub(r"\[[^\]]*\]", "", texto)  # remove marcações tipo [pausa]
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def _quebrar(texto: str) -> list[str]:
    """Divide a fala em blocos curtos, respeitando pontuação."""
    frases = re.split(r"(?<=[.!?…—:])\s+", texto)
    blocos: list[str] = []
    for frase in frases:
        palavras = frase.split()
        atual: list[str] = []
        for p in palavras:
            candidato = " ".join(atual + [p])
            if atual and (len(candidato) > MAX_CHARS or len(atual) >= MAX_PALAVRAS):
                blocos.append(" ".join(atual))
                atual = [p]
            else:
                atual.append(p)
        if atual:
            blocos.append(" ".join(atual))
    return [b for b in blocos if b.strip()]


def cues(timeline: dict) -> list[dict]:
    """Converte a timeline em cues de legenda com tempos proporcionais ao texto."""
    saida = []
    for ev in timeline["eventos"]:
        texto = _limpar(ev.get("narracao", ""))
        if ev.get("legenda"):
            saida.append(
                {
                    "inicio": ev["inicio"],
                    "fim": ev["fim"],
                    "texto": ev["legenda"],
                }
            )
            continue
        if not texto:
            continue
        blocos = _quebrar(texto)
        total_chars = sum(len(b) for b in blocos) or 1
        margem = 0.16
        dur = max(0.6, ev["duracao"] - margem * 2)
        t = ev["inicio"] + margem
        for b in blocos:
            # tempo proporcional ao texto, com piso para leitura confortável
            d = max(0.9, dur * len(b) / total_chars)
            saida.append({"inicio": round(t, 3), "fim": round(t + d, 3), "texto": b})
            t += d
    return saida


def escrever_srt(caminho: Path | str, lista: list[dict]) -> Path:
    caminho = Path(caminho)
    linhas = []
    for i, c in enumerate(lista, 1):
        linhas.append(f"{i}\n{tempo(c['inicio']).replace('.', ',')} --> "
                      f"{tempo(c['fim']).replace('.', ',')}\n{c['texto']}\n")
    caminho.write_text("\n".join(linhas), encoding="utf-8")
    return caminho


# O libass procura a fonte pelo nome da FAMÍLIA, não pelo nome do arquivo.
FAMILIAS = {"BebasNeue": "Bebas Neue", "Cinzel": "Cinzel", "DejaVuSans": "DejaVu Sans"}


def escrever_ass(caminho: Path | str, lista: list[dict], fonte: Path = F_LEGENDA,
                 tamanho: int = 54, largura: int = 1920, altura: int = 1080,
                 cor: str = "&H00EDE7DE", destaque: bool = True,
                 familia: str | None = None) -> Path:
    """Gera um .ass com fade suave e contorno — legenda discreta, estilo 'lore'."""
    caminho = Path(caminho)
    nome = familia or FAMILIAS.get(Path(fonte).stem, "Bebas Neue")
    cabecalho = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {largura}
PlayResY: {altura}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Lore,{nome},{tamanho},{cor},&H000000FF,&H00140E08,&H96000000,0,0,0,0,100,100,1.2,0,1,2.4,0.8,2,180,180,66,1
Style: Destaque,{nome},{int(tamanho*1.15)},&H00DCB47C,&H000000FF,&H00140E08,&H96000000,0,0,0,0,100,100,1.6,0,1,2.6,0.8,2,180,180,120,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    linhas = [cabecalho]
    for c in lista:
        ini = _ass_tempo(c["inicio"])
        fim = _ass_tempo(c["fim"])
        estilo = "Destaque" if c.get("destaque") else "Lore"
        texto = c["texto"].replace("\n", r"\N")
        efeito = r"{\fad(160,160)}" if destaque else r"{\fad(120,140)}"
        linhas.append(f"Dialogue: 0,{ini},{fim},{estilo},,0,0,0,,{efeito}{texto}")
    caminho.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    return caminho


def _ass_tempo(seg: float) -> str:
    h = int(seg // 3600)
    m = int((seg % 3600) // 60)
    s = seg % 60
    return f"{h:d}:{m:02d}:{s:05.2f}"
