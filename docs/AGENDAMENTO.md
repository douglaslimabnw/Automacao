# Agendar 1 vídeo por semana

Duas formas. As duas fazem a mesma coisa: na sexta, o vídeo sobe como
`private` com `publishAt` = sexta 18h (America/Sao_Paulo). O YouTube publica
sozinho.

---

## A) GitHub Actions (não depende do seu computador)

O workflow já está em `.github/workflows/semanal.yml`.

### 1. Autorize o YouTube uma única vez, na sua máquina

```bash
python -m pip install google-api-python-client google-auth-oauthlib
python -m fabrica auth          # abre o navegador, salva ~/.config/fabrica/token.json
```

No Google Cloud Console: crie um projeto → ative **YouTube Data API v3** →
credenciais → **OAuth client ID** → tipo *Desktop app* → baixe o JSON como
`~/.config/fabrica/client_secret.json`.

### 2. Coloque o token no secret do repositório

```bash
gh secret set YOUTUBE_TOKEN_JSON < ~/.config/fabrica/token.json
```

Se for usar voz paga (opcional):

```bash
gh secret set ELEVENLABS_API_KEY --body "sua-chave"
```

### 3. Pronto

Toda sexta às 15h (Brasília) o job pega o **próximo episódio pendente** da fila
(pasta em `episodes/` sem `final.mp4`), narra, gera imagens, renderiza, faz o
upload e agenda. Se não houver episódio pendente, ele não faz nada — então basta
garantir que o roteiro da semana seguinte exista no repositório.

Rodar na mão quando quiser:

```bash
gh workflow run semanal
```

> Renders longos: o runner do GitHub tem 2 vCPU. 10 min de vídeo levam ~30-50
> min, bem dentro do limite de 6 h. Se quiser mais rápido, use
> `render --preview` para testar e deixe o render final para o job semanal.

---

## B) cron no seu computador

```cron
# toda sexta 15:00 — produz e agenda o episódio pendente
0 15 * * 5 cd /home/você/Automacao && .venv/bin/python -m fabrica diario >> ~/fabrica.log 2>&1
```

Como o agendamento (`publishAt`) exige o vídeo já enviado, o ideal é deixar
**dois episódios prontos** na fila: um para a semana atual, outro de reserva.
A fábrica sempre processa o primeiro sem `final.mp4`.

---

## Checagem de metadados sem enviar

```bash
python -m fabrica publicar ep-01-o-reino-que-esqueceu-o-sol --agendar --dry-run
```

Imprime o JSON exato que iria para a API: título (≤100 caracteres), descrição
com capítulos, tags, categoria 20 (Gaming), `publishAt`.

## Ritmo recomendado (o que faz o canal crescer)

| dia | tarefa | tempo |
|---|---|---|
| segunda | gerar roteiro com o prompt de `docs/PROMPT-ROTEIRO.md` e revisar | 30 min |
| terça | `roteiro` + `narrar` + `imagens` (ajustar cenas que não ficaram boas) | 20 min |
| quarta | `render` (rodar de madrugada) + conferir o vídeo inteiro | 30 min |
| quinta | thumbnail (2–3 variações), descrição, `publicar --dry-run` | 20 min |
| sexta 18h | vídeo publicado automaticamente | 0 min |

Sempre deixe o roteiro do **próximo** episódio escrito antes de publicar o da
semana. É o único hábito que separa "canal que para no terceiro vídeo" de
"canal com 50 episódios".
