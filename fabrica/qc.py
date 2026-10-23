"""Portões de qualidade (QC).

Um canal automatizado morre de dois jeitos: entrega lixo sem perceber, ou é
marcado como conteúdo inautêntico por produzir sempre a mesma coisa. Este
módulo ataca os dois.

As checagens são determinísticas e explicáveis — nada de "o modelo disse que
está bom". Cada item tem severidade:

  bloqueia  impede publicar (o showrunner tenta corrigir e, se não der, para)
  aviso     publica, mas te avisa no relatório
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from .timeline import duracao_estimada
from .util import RAIZ, duracao, ffmpeg, info, ler_json, run, salvar_json

# Frases que denunciam texto genérico de LLM (o "sotaque" que o YouTube penaliza)
CLICHES = [
    "em conclusão", "em suma", "vamos explorar", "vamos mergulhar", "mergulhe",
    "desvende", "é importante notar", "vale ressaltar", "no mundo de hoje",
    "nos dias de hoje", "não é apenas", "não apenas", "de forma intrigante",
    "prepare-se para", "sem mais delongas", "repleto de", "cenário fascinante",
    "uma jornada", "te convido", "convido você", "vamos descobrir juntos",
    "como você pode imaginar", "certamente", "em resumo",
]

LIMITES = {
    "min_min": 8.0,
    "max_min": 18.0,
    "alvo_min": 13.0,
    "frase_max_palavras": 26,
    "cliche_max": 3,
    "similaridade_max": 0.16,
    "cenas_min": 8,
}


@dataclass
class Item:
    nome: str
    ok: bool
    detalhe: str = ""
    severidade: str = "aviso"  # bloqueia | aviso

    def __str__(self) -> str:
        marca = "✔" if self.ok else ("✖" if self.severidade == "bloqueia" else "!")
        return f"{marca} {self.nome}: {self.detalhe}"


@dataclass
class Relatorio:
    escopo: str
    itens: list[Item] = field(default_factory=list)

    @property
    def aprovado(self) -> bool:
        return all(i.ok for i in self.itens if i.severidade == "bloqueia")

    @property
    def bloqueios(self) -> list[Item]:
        return [i for i in self.itens if not i.ok and i.severidade == "bloqueia"]

    @property
    def avisos(self) -> list[Item]:
        return [i for i in self.itens if not i.ok and i.severidade == "aviso"]

    def adicionar(self, nome: str, ok: bool, detalhe: str = "", severidade: str = "aviso"):
        self.itens.append(Item(nome, ok, detalhe, severidade))
        return self

    def texto(self) -> str:
        linhas = [f"{'APROVADO' if self.aprovado else 'REPROVADO'} — QC de {self.escopo}"]
        linhas += [f"  {i}" for i in self.itens]
        return "\n".join(linhas)

    def para_json(self) -> dict:
        return {
            "escopo": self.escopo,
            "aprovado": self.aprovado,
            "itens": [i.__dict__ for i in self.itens],
        }

    def feedback_para_agente(self) -> str:
        """Texto que volta ao agente pedindo correção."""
        problemas = [i for i in self.itens if not i.ok]
        return "\n".join(f"- {i.nome}: {i.detalhe}" for i in problemas)


# ------------------------------------------------------------------ roteiro
def _frases(texto: str) -> list[str]:
    return [f.strip() for f in re.split(r"(?<=[.!?…])\s+", texto) if f.strip()]


def _ngramas(texto: str, n: int = 5) -> set[str]:
    palavras = re.findall(r"\b[a-záàâãéêíóôõúç]{2,}\b", texto.lower())
    return {" ".join(palavras[i:i + n]) for i in range(max(0, len(palavras) - n + 1))}


def similaridade(ep, outros_roteiros: list[Path]) -> tuple[float, str]:
    """Jaccard de 5-gramas entre este roteiro e os anteriores."""
    atual = _ngramas(ep.plan.get("texto_completo", "") or _texto_das_cenas(ep))
    if not atual or not outros_roteiros:
        return 0.0, "sem comparação"
    pior, nome = 0.0, ""
    for p in outros_roteiros:
        outro = _ngramas(p.read_text(encoding="utf-8"))
        if not outro:
            continue
        inter = len(atual & outro)
        uniao = len(atual | outro) or 1
        j = inter / uniao
        if j > pior:
            pior, nome = j, p.name
    return round(pior, 3), nome


def _texto_das_cenas(ep) -> str:
    return "\n".join(c.get("narracao", "") for c in ep.cenas)


def avaliar_roteiro(ep, anteriores: list[Path] | None = None) -> Relatorio:
    rel = Relatorio(f"roteiro · {ep.slug}")
    cenas = ep.cenas
    faladas = [c for c in cenas if (c.get("narracao") or "").strip()]
    texto = _texto_das_cenas(ep)
    palavras = len(texto.split())
    minutos = duracao_estimada(texto) / 60

    rel.adicionar("duração estimada", LIMITES["min_min"] <= minutos <= LIMITES["max_min"],
                  f"{minutos:.1f} min (alvo {LIMITES['alvo_min']:.0f}, faixa "
                  f"{LIMITES['min_min']:.0f}–{LIMITES['max_min']:.0f})", "bloqueia")
    rel.adicionar("volume de roteiro", palavras >= 1200,
                  f"{palavras} palavras (mínimo 1.200)", "bloqueia")
    rel.adicionar("cenas faladas", len(faladas) >= LIMITES["cenas_min"],
                  f"{len(faladas)} cenas com narração", "bloqueia")

    # abertura: precisa ser curta e afiada
    primeira = next((c for c in faladas if c["tipo"] not in ("cartao", "cta")), None)
    if primeira:
        n = len(primeira["narracao"].split())
        rel.adicionar("abertura curta", n <= 70, f"{n} palavras na primeira cena", "aviso")
        frase1 = _frases(primeira["narracao"])[0] if _frases(primeira["narracao"]) else ""
        rel.adicionar("gancho na primeira frase", 3 <= len(frase1.split()) <= 24,
                      f'"{frase1[:70]}"', "aviso")

    # diálogo com outro personagem
    dialogos = len(re.findall(r"^\s*—", texto, re.M)) + len(
        re.findall(r"\b(disse|perguntou|respondeu|sussurrou)\b", texto, re.I))
    rel.adicionar("diálogo/contradição", dialogos >= 2,
                  f"{dialogos} marcas de fala", "aviso")

    tipos = [c["tipo"] for c in cenas]
    rel.adicionar("gancho de inscrição", "gancho" in tipos,
                  "cena marcada como gancho", "bloqueia")
    rel.adicionar("chamada para o próximo", any(t in tipos for t in ("proximo", "cta")),
                  "fecho com CTA/próximo", "bloqueia")

    # ritmo de frase
    frases = _frases(texto)
    media = (sum(len(f.split()) for f in frases) / len(frases)) if frases else 0
    rel.adicionar("frases curtas", media <= LIMITES["frase_max_palavras"],
                  f"média de {media:.1f} palavras/frase", "aviso")

    # sotaque de IA
    achados = [c for c in CLICHES if c in texto.lower()]
    rel.adicionar("sem clichês de IA", len(achados) <= LIMITES["cliche_max"],
                  f"{len(achados)} encontrados: {', '.join(achados[:5]) or 'nenhum'}", "aviso")

    # variedade visual
    visuais = [c.get("visual") for c in cenas if c.get("visual") and c.get("tipo") != "cartao"]
    if visuais:
        distintos = len(set(visuais))
        dominante = max(visuais.count(v) for v in set(visuais)) / len(visuais)
        rel.adicionar("variedade de cenários", distintos >= 3 and dominante <= 0.6,
                      f"{distintos} cenários, {dominante*100:.0f}% no mais usado", "aviso")

    # originalidade contra episódios anteriores (defesa do "inauthentic content")
    sim, nome = similaridade(ep, anteriores or [])
    rel.adicionar("originalidade vs. episódios anteriores", sim <= LIMITES["similaridade_max"],
                  f"similaridade {sim:.2f}" + (f" com {nome}" if nome else ""), "aviso")
    return rel


def avaliar_video(ep) -> Relatorio:
    rel = Relatorio(f"vídeo · {ep.slug}")
    if not ep.saida.exists():
        return rel.adicionar("arquivo final", False, "final.mp4 não existe", "bloqueia")

    meta = info(ep.saida)
    dur_min = (meta.get("duracao") or 0) / 60
    rel.adicionar("duração", LIMITES["min_min"] <= dur_min <= LIMITES["max_min"],
                  f"{dur_min:.1f} min", "bloqueia")
    rel.adicionar("faixa de áudio", bool(meta.get("audio")), "stream de áudio presente", "bloqueia")
    resolucao = meta.get("video") or (0, 0)
    rel.adicionar("resolução", min(resolucao) >= 720,
                  f"{resolucao[0]}x{resolucao[1]}", "bloqueia")

    srt = ep.base / "legendas.srt"
    cues = len(re.findall(r"^\d+$", srt.read_text(encoding="utf-8"), re.M)) if srt.exists() else 0
    rel.adicionar("legendas", cues >= 60, f"{cues} blocos em legendas.srt", "aviso")

    thumb = ep.base / (ep.plan.get("thumbnail") or "thumbnail.jpg")
    if thumb.exists():
        from PIL import Image
        with Image.open(thumb) as im:
            rel.adicionar("thumbnail", im.size == (1280, 720), f"{im.size[0]}x{im.size[1]}", "aviso")
    else:
        rel.adicionar("thumbnail", False, "não gerada", "aviso")

    # loudness real (média do arquivo) — o YouTube normaliza, mas muito baixo
    # faz o vídeo parecer "amador" no celular
    p = run([ffmpeg(), "-hide_banner", "-i", str(ep.saida), "-af", "volumedetect",
             "-f", "null", "-"], check=False)
    m = re.search(r"mean_volume:\s*(-?[\d.]+) dB", p.stderr)
    if m:
        media_db = float(m.group(1))
        rel.adicionar("loudness", -26 <= media_db <= -10,
                      f"média {media_db:.1f} dB", "aviso")
    return rel


# ------------------------------------------------------------------ saída
def anteriores_de(ep, limite: int = 6) -> list[Path]:
    arquivos = sorted((RAIZ / "episodes").glob("*/roteiro.md"))
    return [p for p in arquivos if p.parent != ep.base][-limite:]


def rodar(ep, *, escopo: str = "tudo") -> Relatorio:
    if escopo == "roteiro":
        rel = avaliar_roteiro(ep, anteriores_de(ep))
    elif escopo == "video":
        rel = avaliar_video(ep)
    else:
        rel = Relatorio(f"completo · {ep.slug}")
        r1 = avaliar_roteiro(ep, anteriores_de(ep))
        r2 = avaliar_video(ep)
        rel.itens = r1.itens + r2.itens
        rel.escopo = f"completo · {ep.slug}"
    salvar_json(ep.base / "qc.json", rel.para_json())
    (ep.base / "qc.md").write_text(
        f"# QC — {ep.plan.get('titulo', ep.slug)}\n\n```\n{rel.texto()}\n```\n",
        encoding="utf-8",
    )
    return rel
