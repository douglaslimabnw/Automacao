# CLAUDE.md — instruções para agentes de código

Este repositório é uma **fábrica de vídeos** para YouTube (dark, lore de jogos,
10–15 min). O código é Python puro com ffmpeg; o conteúdo vive em `episodes/`.

## Comandos que importam

```bash
python -m fabrica estado                  # painel: o que está pendente
python -m fabrica fila                    # fila de episódios
python -m fabrica producao --preview      # produz o próximo (autônomo)
python -m fabrica ideias --n 4            # agente propõe próximos episódios
python -m fabrica qc <slug>               # portões de qualidade
python -m unittest discover -s tests      # testes (13+, ~20s)
```

Pipeline manual de um episódio: `roteiro → narrar → imagens → timeline →
render → pacote → preview → publicar`.

## Estrutura

| caminho | o que é |
|---|---|
| `fabrica/roteiro.py` | `roteiro.md` → `plan.json` (divide em planos, injeta ganchos) |
| `fabrica/agente.py` | executor de agentes: claude / codex / api / mock |
| `fabrica/qc.py` | portões de qualidade (duração, clichê, originalidade) |
| `fabrica/showrunner.py` | fila + máquina de estados da produção |
| `fabrica/render.py` | ffmpeg: Ken Burns, grade, legendas, mixagem |
| `fabrica/arte.py` | cenários procedurais (sem banco de imagens) |
| `prompts/*.md` | prompts versionados usados pelo agente |
| `series/<slug>.yaml` | configuração da série (nicho, tom, voz, estética) |
| `series/<slug>-biblia.md` | continuidade: personagens, perguntas abertas |
| `episodes/<slug>/` | um episódio (roteiro, plano, mídia, estado, QC) |

## Regras ao mexer no código

1. **Nada de mídia no Git.** `shots/`, `narracao/`, `build/`, `final.mp4` são
   ignorados; tudo é regenerável. Não remova essas entradas do `.gitignore`.
2. **Tudo precisa funcionar offline.** Testes e `--provedor mock` não podem
   depender de rede. Se adicionar integração, deixe fallback determinístico.
3. **Idempotência por arquivo.** Antes de gastar API/render, verifique se o
   artefato já existe e se o hash do texto não mudou (`narracao/_cache.json`).
4. **Formato do roteiro é contrato.** `# Episódio NN — Título`, `## Cena N — X`,
   `visual: <arquetipo>[, figura]`, `> GANCHO`, `> PROXIMO`. Mudar isso quebra
   `roteiro.py` e os prompts.
5. **Novos arquétipos visuais** entram em `arte.ARQUETIPOS` + `PALETAS` +
   `MAPA_VISUAL` (em `roteiro.py`), nessa ordem.
6. **Não publique sem QC.** `publicar` só depois de `qc` aprovado; o showrunner
   já garante isso, não contorne.

## Ao escrever roteiro (quando pedirem conteúdo)

Use `prompts/roteiro.md` como especificação. Antes de escrever, leia
`series/<serie>-biblia.md` e os dois últimos `episodes/*/roteiro.md` para não
repetir estrutura. Salve em `episodes/<slug>/roteiro.md` e rode
`python -m fabrica qc <slug>` — se reprovar, corrija antes de terminar.

## Ao criar uma série nova

`python -m fabrica serie-nova <slug> --nome ... --nicho ... --premissa ...`
e depois preencha `series/<slug>-biblia.md` (personagens, 8 perguntas abertas,
léxico). A bíblia é o que impede a série de se contradizer no episódio 30.
