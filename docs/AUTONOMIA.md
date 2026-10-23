# Deixar rodando sem você

Objetivo: **você escolhe o nicho e os parâmetros uma vez; toda semana sai um
episódio sem você tocar em nada.** Este documento mostra as quatro formas de
chegar lá, o que cada uma custa, e onde ficam os guardrails.

---

## O princípio: separar "cérebro" de "músculo"

O erro mais comum em automação de vídeo é tentar fazer o agente de IA renderizar
vídeo. Ele é péssimo nisso, é caro e é lento.

```
┌─────────────────────────────┐        ┌──────────────────────────────┐
│  CÉREBRO (agente de IA)     │        │  MÚSCULO (máquina, sem IA)   │
│  Claude Code / Codex / API  │  →     │  fabrica: TTS, arte, ffmpeg  │
│  escreve e critica texto    │        │  render, upload, agendamento │
│  ~US$ 0,05 por episódio     │        │  R$ 0, determinístico        │
└─────────────────────────────┘        └──────────────────────────────┘
```

O agente decide **o que** dizer (roteiro, títulos, correções). A fábrica faz
**o trabalho pesado** (voz, imagens, corte, mixagem, upload) sem gastar token.
Isso torna o custo por episódio praticamente zero e o resultado reprodutível.

---

## As quatro formas de rodar

| | Onde roda | Precisa do PC ligado? | Custo | Melhor para |
|---|---|---|---|---|
| **A. GitHub Actions** | nuvem do GitHub | não | grátis (repo privado: minutos inclusos) | base recomendada |
| **B. Claude Routines** | nuvem da Anthropic | não | assinatura Pro/Max | pensar/roteirizar de madrugada |
| **C. VPS / PC de casa + cron** | sua máquina | ligado (ou VPS 24h) | R$ 20–40/mês de VPS | render pesado, 4K, muitos episódios |
| **D. OpenClaw / agente pessoal** | sua máquina | ligado | modelo que você já paga | aprovar por WhatsApp e receber status |

**A combinação que eu recomendo:** A como espinha dorsal (produz e publica
toda sexta) + B para o trabalho criativo (todo domingo o agente escreve o
roteiro e as ideias da semana) + D se você quiser aprovar por mensagem.

---

## A. GitHub Actions (recomendado)

Você já tem `.github/workflows/semanal.yml`. Ele roda toda sexta às 15h de
Brasília, pega o próximo item da fila e faz tudo.

```bash
# 1. autorize o YouTube uma vez, na sua máquina
python -m fabrica auth

# 2. guarde o token como secret
gh secret set YOUTUBE_TOKEN_JSON < ~/.config/fabrica/token.json

# 3. dê um cérebro ao workflow (escolha um)
gh secret set ANTHROPIC_API_KEY --body "sk-ant-..."   # Claude (recomendado p/ texto)
gh secret set OPENAI_API_KEY    --body "sk-..."       # Codex

# 4. encha a fila de roteiros para as próximas semanas
python -m fabrica ideias --n 8
git add fila.json && git commit -m "fila: 8 episódios" && git push

# 5. teste agora, sem esperar sexta
gh workflow run semanal
```

O workflow:

1. `roteiro` — se o episódio ainda não tem `roteiro.md`, chama o agente
   (`claude -p` ou `codex exec`) com a bíblia + brief + episódios anteriores;
2. `QC` — roda os portões de qualidade; se reprovar, o agente recebe a lista de
   problemas e corrige (até 2 vezes); se ainda falhar, o episódio vai para
   `precisa_revisao` e **não publica**;
3. `narrar` → `imagens` → `render` → `pacote`;
4. `publicar --agendar` — sobe como `private` com `publishAt` na sexta 18h.

O GitHub hospeda o runner (2 vCPU no plano free), então seu computador fica
livre. Um episódio de 12 min leva 25–45 min de render, bem dentro do limite de
6h por job.

> **Se você já tem um PC forte e quer renderizar em 1080p+ rápido:** instale um
> *self-hosted runner* (`Settings → Actions → Runners → New self-hosted runner`)
> e troque `runs-on: ubuntu-latest` por `runs-on: self-hosted` no workflow.
> O GitHub continua agendando; o trabalho pesado roda na sua máquina.

## B. Claude Routines (o cérebro na nuvem)

Claude Code tem *scheduled tasks* (antes chamadas de "routines") que rodam na
nuvem da Anthropic — **com o seu notebook fechado**. É o jeito mais próximo de
"deixa rodando enquanto faço outras coisas" para a parte criativa.

```bash
# dentro de uma sessão do Claude Code, no repo:
/schedule every sunday at 9am, read fila.json and docs/PROMPT-ROTEIRO.md,
write episodes/<slug>/roteiro.md for the next two queued episodes following
prompts/roteiro.md exactly, then open a PR with the new scripts.
```

Ou pela web: `claude.ai/code/routines` → *New task* → repositório + prompt +
frequência (mínimo 1 hora entre execuções; semanal é o caso).

Boas práticas que fazem diferença:

- peça **PR, não commit direto** — você revisa o roteiro da semana em 5 min e
  o workflow de produção só roda depois do merge;
- use um prompt que **referencia os arquivos do repo** (`prompts/roteiro.md`,
  `series/<serie>-biblia.md`) em vez de repetir as regras no prompt: quando
  você ajusta o tom, ajusta em um lugar só;
- routines consomem sua cota de assinatura e têm limite diário de execuções —
  confira em `claude.ai/settings/usage` antes de agendar horário.

Alternativa dentro do Claude Code, sem nuvem: `/loop 1h "verifique a fila e
produza o próximo episódio"` (roda enquanto a sessão estiver aberta). Ótimo
para uma tarde de produção, ruim para produção contínua.

## C. VPS ou PC de casa com cron

Mais controle, custo mensal, nenhuma dependência de terceiros para agendar.

```bash
# na VPS (Ubuntu 24.04, 4 vCPU, 8 GB é suficiente)
git clone https://github.com/SEU_USUARIO/Automacao && cd Automacao
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
python -m fabrica auth        # uma vez, com navegador (use túnel SSH)

crontab -e
# toda sexta 15:05 — produz e agenda
5 15 * * 5 cd /home/voce/Automacao && .venv/bin/python -m fabrica diario >> ~/fabrica.log 2>&1
# todo domingo 8h — repõe a fila
0 8 * * 0 cd /home/voce/Automacao && .venv/bin/python -m fabrica ideias --n 4 >> ~/fabrica.log 2>&1
```

Vantagens: o token OAuth do YouTube fica na sua máquina (não em secret de
terceiros), render sem limite de minutos, e você pode subir para 4K trocando
duas linhas no YAML.

## D. OpenClaw (o "funcionário digital" que te avisa)

OpenClaw é um gateway self-hosted que conecta seus apps de mensagem a um agente
e tem **cron embutido** (`~/.openclaw/cron/`, sobrevive a restart) e
**heartbeat** (acorda sozinho e lê um `HEARTBEAT.md`). Serve como concierge da
fábrica: ele não renderiza, ele *manda a fábrica rodar* e te conta o resultado
no WhatsApp.

```bash
# 1. cron do OpenClaw disparando a produção (sexta 15h, fuso de SP)
openclaw cron add --name fabrica-semanal --cron "0 15 * * 5" \
  --tz America/Sao_Paulo \
  --prompt "Rode 'python -m fabrica producao --publicar' no repo ~/Automacao. \
            Se o QC reprovar, me mande no WhatsApp o relatório de qc.md e não publique."

# 2. conferência diária no heartbeat
cat >> ~/Automacao/HEARTBEAT.md <<'EOF'
- Se episodes/*/final.mp4 de sexta ainda não existe, avise.
- Se algum episódio estiver com status precisa_revisao, mande o link do qc.md.
EOF
```

O mesmo padrão funciona com Telegram, Discord ou Slack. É a diferença entre
"automação" e "automação que dá para confiar": você fica sabendo sem abrir nada.

---

## Os guardrails (o que impede a automação de fazer besteira)

Automação sem freio é como publicar sem revisar. A fábrica tem cinco freios:

| freio | como usar |
|---|---|
| **portões de QC** | `fabrica qc <slug>` — reprovou, não publica. Rode `fabrica qc --escopo video` antes de liberar |
| **trava de emergência** | `touch PAUSAR` na raiz: a próxima execução para e não faz nada |
| **teto de gasto** | `export FABRICA_ORCAMENTO_MAX=1.50` — passou disso, o episódio não é publicado |
| **publicar como privado** | o vídeo sobe `private` + `publishAt`; se algo estiver errado, dá tempo de desagendar |
| **fila com estado** | nada é refeito à toa: cada etapa fica em `episodes/<slug>/estado.json` |

### Escada de intervenção — escolha onde você quer estar

| nível | o que acontece | quanto tempo seu por semana |
|---|---|---|
| **0 — piloto automático** | agente escreve, QC aprova, publica sozinho | 0 min |
| **1 — aprovação por mensagem** | agente escreve, você recebe o roteiro, responde "ok" | 5 min |
| **2 — revisão de PR** | agente abre PR com o roteiro, produção só após merge | 15 min |
| **3 — revisão de vídeo** | tudo automático, você assiste antes do `publishAt` | 30 min |

Comece no nível 2 por 3–4 semanas. Quando você confiar no QC, desça para 1 e
depois 0. Canal novo não tem histórico para se proteger: um episódio ruim nos
primeiros meses custa caro.

---

## Quanto custa de verdade

Por episódio de 12 min:

| item | custo | observação |
|---|---|---|
| roteiro (Claude/Codex via CLI ou API) | US$ 0,03–0,10 | ~2.000 palavras + 1 rodada de crítica |
| ideias/temporada (a cada ~2 meses) | US$ 0,02 | um lote de 8 títulos |
| voz (Edge TTS) | R$ 0,00 | grátis, precisa de internet |
| arte + trilha + render | R$ 0,00 | roda na máquina/runner |
| publicação (YouTube API) | R$ 0,00 | cota diária gratuita: 10.000 unidades; um upload custa ~1.600 |
| **total** | **~US$ 0,05/episódio** | ~R$ 0,30 |

Se você quiser voz clonada: ElevenLabs ~US$ 0,18/min de áudio → ~US$ 2,20 por
episódio de 12 min. Ainda é o item mais caro — e o que mais muda a percepção de
qualidade do canal.

---

## Checklist de "está rodando sozinho de verdade"

- [ ] `fila.json` tem **mínimo 4 episódios** com `status: todo`
- [ ] o workflow já rodou uma vez com sucesso (`gh run list`)
- [ ] o token do YouTube está renovando (o refresh salva sozinho; confira após 30 dias)
- [ ] você recebeu pelo menos uma notificação de sucesso e uma de falha (teste `FABRICA_WEBHOOK`)
- [ ] `PAUSAR` existe no seu manual de emergência (sabe criar em 2 segundos)
- [ ] `PAINEL.md` é atualizado a cada execução e você olha 1x por semana
- [ ] os 3 últimos vídeos passaram no QC de originalidade (o YouTube pune canal repetitivo — ver `docs/PESQUISA-2026.md`)

---

## Se algo quebrar (as 5 falhas reais)

| sintoma | causa | conserto |
|---|---|---|
| `edge-tts falhou: Cannot connect` | TTS bloqueado/offline na máquina | tente `--voz openai` ou `elevenlabs`; no CI, verifique saída de rede |
| `QC reprovou duração` | agente escreveu curto | o laço de correção já tenta; se insistir, aumente `PALAVRAS_ALVO` em `prompts/roteiro.md` |
| `upload 403 quotaExceeded` | cota diária do YouTube | espere o reset (meia-noite no Pacífico) ou peça aumento no Cloud Console |
| `thumbnail não enviada` | canal não verificado | verifique o canal; a thumbnail é opcional para publicar |
| render travou / sem espaço | build acumulado | `make limpar` (apaga `build/`, `shots/`, `narracao/` — tudo regenerável) |
