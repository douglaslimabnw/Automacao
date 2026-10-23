"""Executor de agentes: roda Claude Code, Codex CLI ou a API direto.

A mesma tarefa (escrever um roteiro, criticar um episódio, gerar ideias) pode
ser executada por qualquer "cérebro" — o resto da fábrica não sabe nem se
importa com qual. Isso evita ficar preso a um fornecedor e permite trocar de
agente sem mexer no pipeline.

Provedores suportados
---------------------
claude   usa o CLI `claude -p` (headless). Aceita --max-budget-usd e
         --allowedTools. Funciona com login OAuth ou ANTHROPIC_API_KEY.
codex    usa `codex exec` (não interativo), com sandbox workspace-write.
api      chama a API da Anthropic direto por HTTP (sem instalar nada).
mock     escritor local determinístico — sem rede, para testes e demo.

Todos recebem um prompt em texto e DEVEM escrever arquivos no repositório
(é mais barato e mais verificável do que devolver 2.000 palavras por stdout).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

from .util import RAIZ, aviso, log, ok


@dataclass
class Resultado:
    ok: bool
    provedor: str
    texto: str = ""
    custo_usd: float | None = None
    duracao_s: float = 0.0
    erro: str = ""
    bruto: dict = field(default_factory=dict)


def provedor_disponivel() -> str | None:
    """Descobre o melhor provedor instalado, na ordem de preferência."""
    if os.environ.get("FABRICA_AGENTE"):
        return os.environ["FABRICA_AGENTE"]
    if shutil.which("claude"):
        return "claude"
    if shutil.which("codex"):
        return "codex"
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "api"
    if os.environ.get("OPENAI_API_KEY"):
        return "codex"
    return None


def _rodar_cmd(cmd: list[str], *, cwd: Path, timeout: int, entrada: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd, cwd=str(cwd), input=entrada, text=True, timeout=timeout,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )


# ------------------------------------------------------------------ claude
def _claude(prompt: str, *, cwd: Path, timeout: int, modelo: str | None,
            orcamento: float | None, turnos: int) -> Resultado:
    cmd = [
        "claude", "-p", prompt,
        "--output-format", "json",
        "--permission-mode", "dontAsk",
        "--allowedTools", "Read,Write,Edit,Glob,Grep,Bash(python -m fabrica:*)",
        "--max-turns", str(turnos),
    ]
    if modelo:
        cmd += ["--model", modelo]
    if orcamento:
        cmd += ["--max-budget-usd", f"{orcamento:.2f}"]
    t0 = time.time()
    try:
        p = _rodar_cmd(cmd, cwd=cwd, timeout=timeout)
    except subprocess.TimeoutExpired:
        return Resultado(False, "claude", erro=f"timeout após {timeout}s", duracao_s=time.time() - t0)
    dur = time.time() - t0
    bruto = {}
    texto = p.stdout
    try:
        bruto = json.loads(p.stdout)
        texto = bruto.get("result", p.stdout)
    except Exception:
        pass
    if p.returncode != 0:
        return Resultado(False, "claude", texto=texto, erro=p.stderr[-1500:], bruto=bruto, duracao_s=dur)
    return Resultado(True, "claude", texto=texto.strip(),
                     custo_usd=bruto.get("total_cost_usd"), duracao_s=dur, bruto=bruto)


# ------------------------------------------------------------------ codex
def _codex(prompt: str, *, cwd: Path, timeout: int, modelo: str | None,
           orcamento: float | None, turnos: int) -> Resultado:
    cmd = ["codex", "exec", "--sandbox", "workspace-write", "--skip-git-repo-check", prompt]
    if modelo:
        cmd += ["--model", modelo]
    t0 = time.time()
    try:
        p = _rodar_cmd(cmd, cwd=cwd, timeout=timeout)
    except subprocess.TimeoutExpired:
        return Resultado(False, "codex", erro=f"timeout após {timeout}s", duracao_s=time.time() - t0)
    dur = time.time() - t0
    if p.returncode != 0:
        return Resultado(False, "codex", texto=p.stdout, erro=p.stderr[-1500:], duracao_s=dur)
    return Resultado(True, "codex", texto=p.stdout.strip(), duracao_s=dur)


# ------------------------------------------------------------------ api
def _api(prompt: str, *, cwd: Path, timeout: int, modelo: str | None,
         orcamento: float | None, turnos: int) -> Resultado:
    import urllib.error
    import urllib.request

    chave = os.environ.get("ANTHROPIC_API_KEY")
    if not chave:
        return Resultado(False, "api", erro="ANTHROPIC_API_KEY ausente")
    corpo = json.dumps({
        "model": modelo or os.environ.get("FABRICA_MODELO", "claude-sonnet-4-6"),
        "max_tokens": 8000,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages", data=corpo,
        headers={"x-api-key": chave, "anthropic-version": "2023-06-01",
                 "content-type": "application/json"},
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            dados = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return Resultado(False, "api", erro=f"HTTP {e.code}: {e.read()[:500]!r}", duracao_s=time.time() - t0)
    except Exception as e:
        return Resultado(False, "api", erro=str(e), duracao_s=time.time() - t0)
    texto = "".join(b.get("text", "") for b in dados.get("content", []))
    uso = dados.get("usage", {})
    # preço aproximado por milhão de tokens (entrada/saída) — ajuste se mudar
    custo = (uso.get("input_tokens", 0) * 3 + uso.get("output_tokens", 0) * 15) / 1_000_000
    return Resultado(True, "api", texto=texto.strip(), custo_usd=round(custo, 4),
                     duracao_s=time.time() - t0, bruto=uso)


def executar(prompt: str, *, provedor: str | None = None, cwd: Path | None = None,
             timeout: int = 1800, modelo: str | None = None,
             orcamento: float | None = None, turnos: int = 40) -> Resultado:
    """Roda o prompt no provedor escolhido (ou no melhor disponível)."""
    nome = provedor or provedor_disponivel() or "mock"
    cwd = Path(cwd or RAIZ)
    log(f"agente[{nome}] executando ({len(prompt)} caracteres de prompt)")
    if nome == "claude":
        r = _claude(prompt, cwd=cwd, timeout=timeout, modelo=modelo,
                    orcamento=orcamento, turnos=turnos)
    elif nome == "codex":
        r = _codex(prompt, cwd=cwd, timeout=timeout, modelo=modelo,
                   orcamento=orcamento, turnos=turnos)
    elif nome == "api":
        r = _api(prompt, cwd=cwd, timeout=timeout, modelo=modelo,
                 orcamento=orcamento, turnos=turnos)
    elif nome == "mock":
        from .escritor import escrever_como_agente
        r = escrever_como_agente(prompt, cwd=cwd)
    else:
        raise SystemExit(f"provedor desconhecido: {nome}")
    if r.ok:
        custo = f" · US$ {r.custo_usd:.3f}" if r.custo_usd else ""
        ok(f"agente[{nome}] concluiu em {r.duracao_s:.0f}s{custo}")
    else:
        aviso(f"agente[{nome}] falhou: {r.erro[:300]}")
    return r


def executar_com_retry(prompt: str, *, tentativas: int = 2, **kwargs) -> Resultado:
    ultimo = None
    for i in range(tentativas):
        ultimo = executar(prompt, **kwargs)
        if ultimo.ok:
            return ultimo
        if i < tentativas - 1:
            aviso(f"tentando de novo ({i+2}/{tentativas}) em {5*(i+1)}s")
            time.sleep(5 * (i + 1))
    return ultimo
