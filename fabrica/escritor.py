"""Escritor local — o "provedor mock".

Existe por três motivos:
1. rodar a fábrica inteira sem chave de API (testes, demo, CI sem custo);
2. servir de rede de segurança: se o agente falhar 3x, o episódio ainda sai;
3. dar um exemplo concreto de formato para o agente imitar.

Não é IA: é um preenchedor de estrutura com material do enunciado. A qualidade
fica abaixo do que Claude/Codex entregam — o valor está na continuidade.
"""
from __future__ import annotations

import random
import re
from pathlib import Path

from .agente import Resultado


def _extrair(prompt: str, chave: str, padrao: str = r"(.+)") -> str:
    m = re.search(rf"{chave}\s*[:=]\s*{padrao}", prompt, re.I)
    return m.group(1).strip() if m else ""


def _paragrafos(tema: str, titulo: str, rng: random.Random) -> list[tuple[str, str]]:
    """Seções de exemplo, com cenário sugerido, ligadas ao tema do episódio."""
    obs = [
        ("Abertura", "abismo",
         f"{titulo} não começa onde você imagina. Começa no dia em que eu parei de "
         f"contar os dias. Se você está ouvindo isso, é porque alguém precisava ouvir."),
        ("O primeiro sinal", "ruina",
         f"Eu vi {tema} pela primeira vez com os olhos de quem ainda acreditava em "
         f"finais felizes. O lugar estava de pé. As pessoas não."),
        ("O que ficou para trás", "caverna",
         f"Há detalhes que ninguém conta sobre {tema}: o cheiro, o som do metal, a forma "
         f"como a luz se recusa a entrar. Eu lembro de todos, um por um."),
        ("A voz de outro", "trono",
         f"— Você não deveria ter vindo — ele disse.\n"
         f"— Eu precisava saber.\n"
         f"— Saber não devolve ninguém.\n"
         f"Ele estava certo. Eu não voltei diferente por saber. Voltei porque sabia."),
        ("A revelação", "abismo",
         f"Foi ali que eu entendi: {tema} não é um lugar. É uma decisão que alguém tomou "
         f"e que todos nós continuamos tomando, todas as manhãs, sem perceber."),
        ("O que resta", "floresta",
         f"Se você chegou até aqui, você já sabe o que eu vou dizer. Ainda assim, "
         f"precisa ouvir de mim: não existe volta. Existe continuar."),
    ]
    rng.shuffle(obs[1:4])
    return obs


def escrever_como_agente(prompt: str, *, cwd: Path) -> Resultado:
    """Preenche o roteiro no caminho pedido pelo prompt."""
    destino = None
    m = re.search(r"(episodes/[A-Za-z0-9._\-]+/roteiro\.md)", prompt)
    if m:
        destino = Path(cwd) / m.group(1)

    titulo = (_extrair(prompt, r"T[ÍI]TULO") or "O que sobrou").strip('"')
    tema = (_extrair(prompt, "TEMA") or "a queda do reino").strip('"')
    numero_m = (re.search(r"N[ÚU]MERO\s*[:=]\s*(\d+)", prompt, re.I)
                or re.search(r"Episódio\s*(\d+)", prompt))
    numero = int(numero_m.group(1)) if numero_m else 1

    rng = random.Random(numero * 7 + len(titulo))
    linhas = [f"# Episódio {numero:02d} — {titulo}", ""]
    secoes = _paragrafos(tema, titulo, rng)
    for i, (nome, visual, texto) in enumerate(secoes, 1):
        linhas += [f"## Cena {i} — {nome}", f"visual: {visual}", ""]
        linhas += [p.strip() for p in texto.split("\n") if p.strip()]
        linhas.append("")
        if i == 3:
            linhas += [
                "> GANCHO",
                "",
                "Antes de continuar: se essa história te prendeu, deixa o like e se "
                "inscreve. É isso que faz o próximo episódio existir.",
                "",
            ]
    linhas += [
        "> PROXIMO",
        "",
        "Semana que vem eu conto o que encontrei depois da última porta. Se você quer "
        "estar lá, se inscreve e ativa o sininho.",
        "",
    ]
    texto_final = "\n".join(linhas)

    if destino:
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(texto_final, encoding="utf-8")
        return Resultado(True, "mock", texto=f"escrito {destino}", custo_usd=0.0)
    return Resultado(True, "mock", texto=texto_final, custo_usd=0.0)
