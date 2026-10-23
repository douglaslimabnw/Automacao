# O que mudou em 2026 (e o que isso muda aqui)

Pesquisa feita em outubro de 2026 para decidir a arquitetura da fábrica. Cada
seção diz **o fato**, **a fonte** e **o que eu fiz com ele** neste repositório.

---

## 1. Agentes de código agora rodam sozinhos (headless)

**Fato.** Claude Code e Codex CLI têm modos não interativos que transformam o
agente em um comando de shell:

- `claude -p "tarefa"` com `--output-format json`, `--max-turns`,
  `--max-budget-usd`, `--allowedTools`, `--permission-mode dontAsk` e `--bare`
  (que ignora hooks/MCP/CLAUDE.md para o resultado ser igual em qualquer
  máquina). [2](https://agentscamp.com/guides/advanced/claude-code-ci-github-actions)
  [3](https://code.claude.com/docs/en/headless) [5](https://likeone.ai/blog/claude-code-headless-mode-guide-2026/)
- `codex exec "tarefa"` com `--sandbox workspace-write`, `--json`, `-o arquivo`,
  `--output-schema` e `--ephemeral`. [2](https://developers.openai.com/codex/noninteractive)
  [5](https://codex.danielvaughan.com/2026/04/18/codex-cli-headless-batch-mode-automation/)
- Existem *actions* oficiais para os dois (`anthropics/claude-code-action@v1`,
  `openai/codex-action@v1`), que gerenciam a chave por proxy em vez de expor o
  secret no ambiente do job. [1](https://hidekazu-konishi.com/entry/claude_code_cicd_and_headless_automation.html)
  [6](https://developers.openai.com/codex/github-action)

**O que fiz.** `fabrica/agente.py` fala com os três (claude, codex, API direta)
pelo mesmo contrato: *recebe um prompt, o agente escreve arquivos no repo*.
Nada no pipeline sabe qual cérebro está atendendo — trocar é uma variável de
ambiente (`FABRICA_AGENTE=codex`).

**Detalhe que quase todo mundo erra:** em automação não se pede "texto de
2.000 palavras no stdout". Pede-se *"salve no arquivo X"*. É mais barato, não
estoura limite de saída e a validação é trivial (o arquivo existe? passa no QC?).

## 2. Agendamento saiu do cron do seu PC

**Fato.** O Claude Code ganhou *scheduled tasks* (as antigas "routines") que
rodam na nuvem da Anthropic: gatilho por horário, por API (HTTP POST com bearer
token) ou por evento do GitHub, com o **computador desligado**. Intervalo
mínimo de 1 hora, e o consumo entra na cota da assinatura.
[1](https://code.claude.com/docs/en/routines) [3](https://code.claude.com/docs/en/scheduled-tasks)
[11](https://www.builder.io/blog/claude-code-routines)

Para tarefas só locais existem ainda `/loop` (dentro da sessão) e as tarefas
agendadas do Desktop (exigem a máquina ligada).
[16](https://wmedia.es/en/tips/claude-code-schedule-vs-loop-vs-cron)

**O que fiz.** `docs/AUTONOMIA.md` separa as quatro rotas (GitHub Actions,
Routines, VPS/cron, OpenClaw) com setup de cada uma. A regra que adotei: **o
agente pensa na nuvem, o render acontece na máquina** — porque sessão de nuvem
não tem ffmpeg nem 40 minutos de CPU sobrando.

## 3. OpenClaw virou "funcionário digital" com cron próprio

**Fato.** OpenClaw (ex-Clawdbot/Moltbot) é um gateway self-hosted que conecta
WhatsApp/Telegram/Slack/Discord a agentes, com **cron embutido e persistente**
(`openclaw cron add --cron "0 15 * * 5" --tz America/Sao_Paulo`), **heartbeat**
que acorda o agente e lê um `HEARTBEAT.md`, e entrega do resultado no canal de
mensagem que você escolher. [5](https://docs2.openclaw.ai/cli/cron)
[2](https://geekyants.com/blog/openclawai-your-personal-ai-that-actually-does-things)
[9](https://milvusio.medium.com/openclaw-formerly-clawdbot-moltbot-explained-a-complete-guide-to-the-autonomous-ai-agent-9209659c2b8b)

**O que fiz.** É a rota D em `docs/AUTONOMIA.md`: o OpenClaw não renderiza, ele
*dispara* `fabrica producao` e te avisa. A fábrica já aceita
`FABRICA_WEBHOOK` para mandar o status sozinha, então funciona com ou sem ele.

## 4. A regra que pode matar o canal: conteúdo inautêntico

**Fato.** Este é o risco real de automação de YouTube hoje.

- Em 15/07/2025 o YouTube renomeou a política de "conteúdo repetitivo" para
  **"inauthentic content"**; em 16/07/2026 detalhou três categorias que não
  podem monetizar: produção genérica/baseada em template, conteúdo manipulador
  e personas sintéticas dando conselho em temas sensíveis.
  [1](https://www.layer3labs.io/guides/youtube-ai-content-policy)
  [11](https://deeporax.com/blog/youtube-inauthentic-content-policy-2026)
- Em janeiro de 2026 o YouTube encerrou **16 canais** que somavam ~4,7 bilhões
  de views e 35 milhões de inscritos, por produção em massa — não por usar IA.
  [5](https://miraflow.ai/blog/youtube-monetization-ai-content-2026-allowed-demonetized)
  [10](https://lenspov.com/articles/youtube-ai-content-demonetization-2026)
- **Usar IA não é o gatilho.** O gatilho é não acrescentar ponto de vista,
  repetir o mesmo template e não ter voz própria.
  [18](https://finance.yahoo.com/news/youtube-clarifies-changes-monetization-rules-194232823.html)
- Divulgação ("altered or synthetic content") só é obrigatória quando o
  conteúdo é **realista** e poderia enganar; roteiro com IA, thumbnail e TTS
  genérico normalmente não exigem. Desde 27/05/2026 o YouTube aplica o rótulo
  sozinho quando detecta IA fotorrealista não declarada.
  [2](https://faceless.my/youtube/youtube-inauthentic-content-policy-faceless-ai-2026/)
  [3](https://milx.app/en/trends/does-ai-impact-youtube-monetization-what-youtube-has-to-say)

**O que fiz.** `fabrica/qc.py` trata isso como requisito de engenharia, não como
conselho:

- **similaridade de 5-gramas** contra todos os episódios anteriores (bloqueia
  quando o texto começa a se repetir);
- **detector de clichê de LLM** ("em conclusão", "mergulhe", "não é apenas"...);
- **variedade visual** — se 60% das cenas usam o mesmo cenário, reprova;
- **ritmo e diálogo** — média de frase e presença de contradição dramática.

Nada disso garante originalidade, mas pega o sintoma exato que o algoritmo
penaliza: episódios que são o mesmo episódio com outro título.

**Consequência editorial:** a série tem bíblia, personagens recorrentes e
perguntas abertas (`series/*-biblia.md`). Isso é o oposto de "gerar 30 vídeos
sobre 30 jogos diferentes a partir de um template" — e é o que dá para defender
se o canal for revisado.

## 5. Pipelines de "faceless" amadureceram — e convergiram

**Fato.** Os guias de 2026 convergem no mesmo desenho: fila → roteiro (LLM) →
TTS → imagens/vídeo → montagem com ffmpeg → legenda → upload agendado, com uma
planilha ou fila como fonte da verdade e **algum ponto de revisão humana**.
[1](https://www.genaiunplugged.com/courses/n8n/lessons/build-your-first-faceless-youtube-automation-with-n8n/)
[5](https://dev.to/nils44344/how-i-built-a-free-self-hosted-pipeline-that-auto-generates-faceless-youtube-shorts-3je4)
[17](https://github.com/Karthikvarmamkv/faceless-youtube-automation)

Duas lições que aparecem em quase todos:

1. **ffmpeg no próprio runner**, não em serviço de terceiro (Shotstack/Creatomate
   custam por render e amarram o formato);
2. **QC humano em algum lugar** — os canais que sobrevivem revisam algo.
   [21](https://www.reddit.com/r/n8n/comments/1ri9047/built_my_own_youtube_automation_with/)
   [24](https://www.overseeros.com/blog/faceless-youtube-automation)

**O que fiz.** Mantive o ffmpeg local e troquei "revisão humana no meio" por
**portões automáticos + escada de intervenção** (`docs/AUTONOMIA.md`): você
escolhe se revisa o roteiro (nível 2), o vídeo (nível 3) ou nada (nível 0).

## 6. Detalhes técnicos que economizam horas

- **Chave de API não vai em `env` de job** que roda código do repositório —
  use as *actions* oficiais, que fazem proxy da credencial.
  [2](https://developers.openai.com/codex/noninteractive)
- **`--bare` no Claude em CI** evita que hooks/CLAUDE.md de outra pessoa mudem
  o resultado. [28](https://www.stephane-robert.info/docs/developper/autres-outils/claude-code/headless-ci-claude-code/)
- **`--max-turns` e `--max-budget-usd` são circuit breakers** — sem eles, um
  laço de correção pode virar US$ 20 de madrugada.
  [10](https://popularaitools.ai/blog/claude-code-workflow-patterns-agentic-guide-2026)
- **Cota do YouTube:** 10.000 unidades/dia; um upload custa ~1.600, então dá
  para ~6 uploads/dia no mesmo projeto. Agendar é de graça depois de subir.
  [2](https://dev.to/samchenreviews/how-to-make-faceless-youtube-shorts-with-ai-1o3k)
- **Idempotência por arquivo** (se o mp3 da cena existe e o hash do texto não
  mudou, não regrava) é o que permite retomar de qualquer ponto — é o mesmo
  princípio de *durable execution* que orquestradores como Temporal vendem.

---

## O que eu deliberadamente NÃO usei (e por quê)

| tentação | por que não |
|---|---|
| n8n/Make como orquestrador | mais uma conta, mais um runtime para quebrar; o repo já é a fonte da verdade |
| Shotstack/Creatomate para montar | custo por render e formato engessado; ffmpeg local dá mais controle estético |
| vídeo gerado por IA (Kling/Veo) para todas as cenas | caro (US$ 0,30–1,50 por clipe) e visualmente inconsistente entre cenas; a arte procedural + gameplay real fica coerente |
| 30 vídeos por semana | é exatamente o padrão que o YouTube está punindo desde janeiro de 2026 |
| TTS "premium" desde o dia 1 | Edge TTS é grátis e suficiente; clone de voz só quando o canal tiver identidade |
