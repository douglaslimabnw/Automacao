# AGENTS.md

Instruções para qualquer agente de código (Codex, Cursor, OpenClaw, Aider…).
O conteúdo canônico está em [`CLAUDE.md`](CLAUDE.md) — leia antes de agir.

Resumo executivo:

- **Objetivo do repo:** produzir e publicar 1 vídeo dark de 10–15 min por semana
  no YouTube, com o mínimo de intervenção humana.
- **Comando de ouro:** `python -m fabrica producao --preview` (produz o próximo
  episódio da fila; `--publicar` envia agendado).
- **Nunca** comite mídia (`*.mp4`, `narracao/`, `shots/`, `build/`).
- **Nunca** publique sem `python -m fabrica qc <slug>` aprovado.
- **Sempre** rode `python -m unittest discover -s tests` depois de mexer no código.
- **Texto no formato de** `prompts/roteiro.md` — é um contrato lido pelo parser.
- **Contexto de continuidade:** `series/*-biblia.md`. Leia antes de escrever.

Modos não interativos equivalentes:

```bash
claude -p "leia CLAUDE.md e produza o proximo episodio da fila" --allowedTools "Read,Edit,Bash(python -m fabrica:*)"
codex exec --sandbox workspace-write "leia AGENTS.md e produza o proximo episodio da fila"
```
