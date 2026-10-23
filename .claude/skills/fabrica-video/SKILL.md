---
name: fabrica-video
description: Produz um episódio completo da fábrica de vídeos dark (roteiro, voz, imagens, render, QC, publicação). Use quando pedirem para criar, revisar ou publicar um episódio deste repositório.
---

# Skill: fabrica-video

Você opera a fábrica de vídeos. O objetivo é entregar **um episódio pronto para
publicar**, respeitando o formato e os portões de qualidade.

## Passo a passo

1. **Contexto** — leia, nesta ordem:
   - `series/<serie>-biblia.md` (ou `docs/BIBLIA.md`)
   - os dois `episodes/*/roteiro.md` mais recentes
   - `prompts/roteiro.md` (especificação exata do formato)

2. **Fila** — `python -m fabrica estado`. Se a fila estiver vazia:
   `python -m fabrica ideias --n 4`.

3. **Roteiro** — se o episódio não tem `roteiro.md`, escreva seguindo
   `prompts/roteiro.md`. Salve em `episodes/<slug>/roteiro.md`.
   Regras: 8–12 blocos, ~1.900 palavras, diálogo que contradiz o narrador,
   gancho de inscrição dentro da ficção, fecho prometendo o próximo.

4. **Validar** — `python -m fabrica roteiro <slug>` e depois
   `python -m fabrica qc <slug>`. Se reprovar:
   - duração curta → acrescente blocos com substância (lugar novo, detalhe
     físico, informação nova); nunca encha linguiça;
   - clichê → troque por imagem concreta;
   - similaridade alta → mude a estrutura da revelação e os cenários;
   - repita até `APROVADO`.

5. **Mídia e render** —
   `python -m fabrica producao --serie <serie> --preview` (rápido) e depois
   `python -m fabrica render <slug>` (final 1080p).

6. **Entrega** — `python -m fabrica pacote <slug>`, `qc --escopo video`, e só
   então `python -m fabrica publicar <slug> --agendar --dry-run` para conferir.
   Publicar de verdade só se o usuário pedir explicitamente.

## Restrições

- não invente novos campos no `plan.json` sem registrar em `fabrica/roteiro.py`;
- não altere `.gitignore` para incluir mídia;
- não publique sem QC aprovado e sem confirmação explícita;
- se um comando falhar duas vezes, pare e reporte o erro com o log relevante.
