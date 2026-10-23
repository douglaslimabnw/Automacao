"""Configuração da fábrica: séries, canal e caminhos."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .util import RAIZ, aviso, ler_json, salvar_json

try:
    import yaml
except Exception:  # pragma: no cover
    yaml = None


PADRAO = {
    "video": {
        "largura": 1920,
        "altura": 1080,
        "fps": 24,
        "codec": "libx264",
        "preset": "medium",
        "crf": 20,
        "audio_bitrate": "192k",
        "loudness": -14.0,  # LUFS — padrão do YouTube
    },
    "estilo": {
        "semente_base": 777,
        "paleta": "teal frio nas sombras, âmbar quente nos pontos de luz",
        "grao": 6,
        "vinheta": 0.55,
        "contraste": 1.08,
        "saturacao": 0.86,
        "brilho": -0.03,
        "zoom": 0.06,  # amplitude do Ken Burns (6%)
        "tremor": 0.35,  # micro-handheld
        "transicao": 0.7,
        "legendas": "burn",  # burn | srt | off
        "fonte_titulo": "assets/brand/fonts/Cinzel.ttf",
        "fonte_legenda": "assets/brand/fonts/BebasNeue.ttf",
    },
    "voz": {
        "provedor": "edge",  # edge | elevenlabs | openai | manual
        "voz": "pt-BR-AntonioNeural",
        "velocidade": "-8%",
        "tom": "-4Hz",
        "pausa_entre_cenas": 0.45,
    },
    "trilha": {
        "modo": "procedural",  # procedural | arquivo | mute
        "mood": "melancolico",
        "intensidade": 0.30,
        "duck": 0.16,  # quanto a trilha abaixa sob a voz
    },
    "publicacao": {
        "categoria": 20,  # Gaming
        "privacidade_inicial": "private",
        "dia_semana": "sexta",
        "hora": "18:00",
        "fuso": "America/Sao_Paulo",
        "tags_base": ["lore", "dark souls", "jogos", "análise"],
    },
}


def _merge(a: dict, b: dict) -> dict:
    out = dict(a)
    for k, v in (b or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def carregar_serie(nome: str) -> dict:
    caminho = RAIZ / "series" / f"{nome}.yaml"
    if not caminho.exists():
        raise SystemExit(f"série não encontrada: {caminho}")
    dados = yaml.safe_load(caminho.read_text(encoding="utf-8")) if yaml else {}
    return _merge(PADRAO, dados or {})


def carregar_episodio(slug: str) -> dict:
    caminho = RAIZ / "episodes" / slug / "plan.json"
    if not caminho.exists():
        raise SystemExit(f"episódio não encontrado: {caminho}")
    return ler_json(caminho)


@dataclass
class Episodio:
    """Um episódio = uma pasta em episodes/<slug>/."""

    slug: str
    base: Path = field(default_factory=Path)
    plan: dict = field(default_factory=dict)

    def __post_init__(self):
        self.base = RAIZ / "episodes" / self.slug
        if not self.plan:
            plano = self.base / "plan.json"
            if plano.exists():
                self.plan = ler_json(plano)
            else:
                # episódio recém-criado pela fila: ainda não tem plano
                meta = self.base / "ep.json"
                dados = ler_json(meta) if meta.exists() else {}
                self.plan = {
                    "slug": self.slug,
                    "serie": dados.get("serie", "vozes-do-abismo"),
                    "titulo": dados.get("titulo", self.slug),
                    "episodio": dados.get("numero", 1),
                    "semente": dados.get("semente", 777),
                    "sinopse": dados.get("sinopse", ""),
                    "cenas": [],
                }
        self.config = carregar_serie(self.plan.get("serie", "vozes-do-abismo"))

    # ---- caminhos -------------------------------------------------------
    @property
    def shots(self) -> Path:
        return self.base / "shots"

    @property
    def narracao(self) -> Path:
        return self.base / "narracao"

    @property
    def build(self) -> Path:
        return self.base / "build"

    @property
    def saida(self) -> Path:
        return self.base / "final.mp4"

    @property
    def cenas(self) -> list[dict]:
        return self.plan.get("cenas", [])

    def garantir_pastas(self) -> None:
        for p in (self.shots, self.narracao, self.build, self.base / "trilha"):
            p.mkdir(parents=True, exist_ok=True)

    def salvar_plan(self) -> None:
        salvar_json(self.base / "plan.json", self.plan)

    def caminho_relativo(self, valor: str | None) -> Path | None:
        if not valor:
            return None
        p = Path(valor)
        return p if p.is_absolute() else self.base / p
