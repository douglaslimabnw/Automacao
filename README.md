# Automação — fábrica de vídeos dark para YouTube

Pipeline local (e gratuito) que transforma **um roteiro em texto** em um vídeo
dark de 10–15 min pronto para o YouTube: narração, imagens, trilha, legendas,
thumbnail, metadados e agendamento — um episódio por semana, no automático.

```
roteiro.md  →  plan.json  →  narração (TTS)  →  imagens  →  render (ffmpeg)  →  YouTube
   texto        cenas          voz grave         cenários      MP4 1080p        agendado
```

Sem banco de imagens, sem música com direitos, sem editor de vídeo. Tudo gerado
por código: cenários são desenhados proceduralmente, a trilha é sintetizada e a
voz vem de TTS. Você pode substituir qualquer peça por material real do jogo
(screenshot, gameplay) apenas apontando o caminho no plano.

---

## 1. Instalação (2 minutos)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

`imageio-ffmpeg` traz um ffmpeg estático completo — não precisa instalar nada
no sistema. (Se já tiver ffmpeg no PATH, ele é usado.)

Narração grátis via Microsoft Edge TTS (precisa de internet):

```bash
python -m fabrica narrar --vozes pt-BR      # lista as vozes disponíveis
```

## 2. Primeiro vídeo

```bash
python -m fabrica novo ep-02 --titulo "O Segundo Sino" --numero 2
# edite episodes/ep-02/roteiro.md

python -m fabrica roteiro ep-02      # texto -> cenas (mostra a duração estimada)
python -m fabrica narrar  ep-02      # gera a voz de cada cena
python -m fabrica imagens ep-02      # gera cenários + thumbnail
python -m fabrica timeline ep-02     # confere ritmo, ganchos e durações
python -m fabrica render  ep-02      # MP4 final em episodes/ep-02/final.mp4
python -m fabrica pacote  ep-02      # legendas.srt, thumbnail.jpg, metadados
python -m fabrica publicar ep-02 --agendar --dry-run   # confere sem enviar
python -m fabrica publicar ep-02 --agendar             # sobe agendado
python -m fabrica preview ep-02      # página HTML de revisão (vídeo + quadros)
```

Atalhos com `make` (no macOS/Linux):

```bash
make episodio SLUG=ep-02-o-segundo-sino   # pipeline completo
make preview  SLUG=ep-02-o-segundo-sino   # revisão no navegador
make testes
```

Ou tudo de uma vez, no próximo episódio pendente da fila:

```bash
python -m fabrica diario
```

## 3. Como o roteiro funciona

`episodes/<slug>/roteiro.md` é prosa normal, com marcas simples:

```markdown
# Episódio 02 — O Segundo Sino

## Cena 1 — Debaixo do campanário
visual: caverna, figura

Eu desci os degraus contando. Na décima segunda, o sino tocou sozinho.

> GANCHO

Se isso te prendeu, deixa o like — é o que mantém esse canal respirando.

## Cena 2 — A sala dos sinos
visual: trono

<texto...>
```

| marca | efeito |
|---|---|
| `## Cena N — Título` | nova cena (obrigatório para separar blocos) |
| `visual: caverna, figura` | força o cenário (`ruina`, `caverna`, `floresta`, `abismo`, `trono`, `campo`) |
| `> GANCHO` | a cena vira gancho de like/inscrição (com cartão e SFX) |
| `> PROXIMO` | a cena vira chamada para o próximo vídeo |
| `duracao: 6` | duração fixa para cena sem narração |

Regras aplicadas automaticamente:

- blocos longos são **divididos em planos** (~48 palavras por shot, nenhuma
  imagem fica mais de 11 s na tela);
- frases na primeira pessoa (`eu`, `meu`, `minha`) viram **plano médio do
  personagem falando com a câmera**; a cada 4 planos, um plano aberto do cenário;
- o cenário de cada cena é **inferido do texto** (palavras como "igreja",
  "sino", "trono") se você não indicar `visual:`;
- um gancho de meio de vídeo é inserido no **meio do tempo** (não no meio da
  contagem de cenas) se o roteiro não tiver um;
- cartão de abertura com título e fecho com CTA são adicionados nas pontas.

Para escrever o roteiro da semana, use o prompt pronto em
**[docs/PROMPT-ROTEIRO.md](docs/PROMPT-ROTEIRO.md)** (basta colar em qualquer
LLM e pedir o episódio seguinte).

## 4. O que é gerado em cada pasta

```
episodes/ep-01-o-reino-que-esqueceu-o-sol/
├── roteiro.md          ← você escreve (ou o LLM escreve)
├── ep.json             ← série, número, título, semente
├── plan.json           ← cenas resolvidas (editável à mão)
├── narracao/           ← <id>.mp3 + cache (só regrava o que mudou)
├── shots/              ← arte procedural por cena (regenerável)
├── imagens/            ← SEU material (screenshot do jogo) tem prioridade
├── build/              ← cenas individuais, legendas.ass, audio.m4a
├── final.mp4           ← o vídeo
├── legendas.srt        ← para o YouTube
└── thumbnail.jpg       ← 1280×720
```

**Nada de mídia pesada entra no Git** (veja `.gitignore`): o que é versionado é
o roteiro e o plano — o resto é reproduzível em minutos.

## 5. Usar footage real do jogo (recomendado para o melhor resultado)

A arte procedural é um piso de qualidade — bonita, coerente e livre de
direitos, mas não é gameplay. Para os vídeos realmente performarem:

1. Grave 15–20 min de gameplay do jogo (OBS, 1080p, sem HUD se possível).
2. Coloque cortes em `episodes/<slug>/imagens/` com o **nome do id da cena**
   (`c004.jpg`) — ou aponte no `plan.json`:
   ```json
   { "id": "c004", "imagem": "imagens/igreja.png" }
   ```
3. Para movimento, use `"clip": "imagens/c004.mp4"` (o clipe é repetido/ajustado
   à duração da fala).
4. Rode `python -m fabrica render <slug> --forcar-imagens`.

O render aplica o mesmo color grade dark, grão, vinheta e Ken Burns em cima do
seu material — então tudo fica com a mesma cara.

## 6. Custo e tempo

| etapa | tempo (10 min de vídeo) | custo |
|---|---|---|
| roteiro (LLM) | 2 min | ~US$ 0,05 |
| narração (Edge TTS) | 3–5 min | R$ 0 |
| imagens (procedurais) | ~1,5 min | R$ 0 |
| render 1080p | 20–40 min (notebook) | R$ 0 |
| trilha + SFX | sintetizados no render | R$ 0 (sem Content ID) |

Alternativas de voz pagas já suportadas: `--provedor elevenlabs` (voz clonada,
`ELEVENLABS_API_KEY`) e `--provedor openai` (`OPENAI_API_KEY`). Para uma voz
única e proprietária do canal, clone a sua no ElevenLabs e troque a config em
`series/vozes-do-abismo.yaml`.

## 7. Agendamento semanal

Duas opções prontas em **[docs/AGENDAMENTO.md](docs/AGENDAMENTO.md)**:

- **GitHub Actions** (`.github/workflows/semanal.yml`): toda sexta, 15h, roda o
  episódio pendente e agenda no YouTube para 18h.
- **cron local**: `0 15 * * 5 cd ~/Automacao && .venv/bin/python -m fabrica diario`

O vídeo sobe como `private` com `publishAt` — o YouTube publica sozinho no
horário definido.

## 8. Ajustes de estética

Tudo em `series/vozes-do-abismo.yaml`:

```yaml
estilo:
  grao: 6            # granulação de filme (0 = limpo)
  vinheta: 0.35      # escurecimento das bordas
  contraste: 1.08
  saturacao: 0.85
  zoom: 0.07         # intensidade do Ken Burns
  tremor: 0.30       # micro-handheld
  transicao: 0.7     # crossfade entre planos
  legendas: burn     # burn (no vídeo) | srt (só arquivo) | off

voz:
  velocidade: "-8%"  # mais lento = mais "dark"
  tom: "-4Hz"
```

Teste uma arte isolada sem criar episódio:

```bash
python -m fabrica arte caverna /tmp/teste.jpg --figura --largura 1920 --altura 1080
```

## 9. Testes

```bash
python -m unittest discover -s tests -v
```

Checam: parsing do roteiro, divisão em planos, durações da timeline, legendas
(SRT/ASS), mixagem/geração de áudio e um render de 2 segundos de ponta a ponta.

## 10. Estrutura do código

```
fabrica/
├── cli.py         comandos (novo, roteiro, narrar, imagens, timeline, render, ...)
├── roteiro.py     roteiro.md -> plan.json (divisão em planos, ganchos, visuais)
├── voz.py         TTS por cena com cache (edge | elevenlabs | openai | arquivo)
├── arte.py        cenários, cartões e thumbnail procedurais (Pillow + numpy)
├── imagens.py     resolve a mídia de cada cena (sua ou gerada)
├── timeline.py    durações reais, offsets, validação
├── subtitles.py   SRT + ASS estilizado
├── audio_gen.py   trilha e SFX sintetizados (sem direitos, sem Content ID)
├── render.py      Ken Burns, grade, grão, crossfades, mixagem -14 LUFS, MP4
└── publicar.py    upload, agendamento e metadados do YouTube
```

Licenças das fontes: Cinzel e Bebas Neue (SIL Open Font License) em
`assets/brand/fonts/`.
