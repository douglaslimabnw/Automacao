# Prompt para gerar o roteiro da semana

Copie o bloco abaixo, cole em qualquer LLM (ChatGPT, Claude, Gemini…) e troque
só a última linha. O resultado já vem no formato que `python -m fabrica roteiro`
entende — salve como `episodes/<slug>/roteiro.md`.

> Dica: gere 2–3 opções de gancho de abertura e escolha a melhor. Abrir com uma
> frase que só faz sentido no fim é o que segura o espectador nos primeiros 30 s.

---

```
Você é roteirista de um canal de YouTube dark de lore/análise de jogos, em
português do Brasil. Escreve em primeira pessoa, como um personagem que
sobreviveu ao evento que narra e fala diretamente com quem assiste.

SÉRIE: "Vozes do Abismo"
PREMISSA DA SÉRIE: cada episódio é a confissão de um sobrevivente de um reino
chamado Vardhal, onde uma igreja de pedra negra apareceu pronta numa manhã e,
desde então, quem ouve o sino dela não morre — passa a viver uma lembrança
perfeita de uma vida que nunca teve.

VOZ E TOM
- frases curtas, ritmo lento, sem ironia, sem exclamações em excesso
- imagens concretas em vez de adjetivos ("a colher atravessada no prato" e não
  "uma cena triste")
- o narrador confessa; ele não explica o jogo, ele lembra do que viveu
- terror atmosférico, não gore
- uma revelação a cada ~2 minutos; nada de resumo no começo

ESTRUTURA OBRIGATÓRIA (10 a 15 minutos de narração, ~1.700 a 2.100 palavras)
1. Abertura: 2 parágrafos, um gancho que só faz sentido no fim do episódio
2. 4 a 6 blocos temáticos, cada um com um lugar, um detalhe físico e uma
   informação nova sobre o mistério
3. Um diálogo com outro personagem (guardião, criança, rainha, forasteiro…)
   que diga algo que contradiz o narrador
4. Um gancho de inscrição no meio, escrito como parte da história e não como
   propaganda ("Antes de continuar…")
5. Reviravolta: o narrador revela algo que ele escondeu de quem assiste
6. Fecho com chamada para o próximo episódio, citando o que será revelado

FORMATO (siga exatamente)
# Episódio NN — Título

## Cena 1 — Nome do bloco
visual: ruina

<parágrafos>

## Cena 2 — Nome do bloco
visual: caverna, figura

<parágrafos>

> GANCHO

<texto do gancho, 2 a 3 frases>

## Cena 3 — Nome do bloco
visual: trono

<parágrafos, incluindo o diálogo>

## Cena 4 — Fecho
visual: abismo, figura

<parágrafos>

> PROXIMO

<chamada para o próximo episódio, 2 a 3 frases>

REGRAS DE `visual:`
use um destes: ruina | caverna | floresta | abismo | trono | campo
adicione ", figura" quando o narrador estiver falando de si mesmo em cena

NÃO escreva títulos de seção fora desse formato, não use listas, não use
markdown além dos `##`. Sem emojis.

EPISÓDIO A ESCREVER: NN = 02, título provisório "O Segundo Sino".
O que o episódio anterior estabeleceu: a igreja apareceu pronta; o sino apaga
quem ouve; o guardião não tem rosto; a rainha conta casas acesas todas as
noites; o narrador foi salvo por uma mão de criança que ele nunca viu.
O que este episódio revela: o que existe na sala dos sinos que ainda não
tocaram — e por que um deles tem o nome do narrador.
```

---

## Como manter uma série por semanas

Guarde as respostas do LLM em `docs/biblia-da-serie.md` (o que já foi revelado,
quem são os personagens, que perguntas estão abertas). No prompt, cole esse
arquivo na seção "O que o episódio anterior estabeleceu". Isso evita
contradição e faz a série ganhar fôlego — que é o que gera inscrição.

Ordem sugerida de episódios (uma temporada de 8):

1. O Reino que Esqueceu o Sol ✅ *(já escrito em episodes/ep-01…)*
2. O Segundo Sino — a sala dos sinos que não tocaram
3. O Guardião Sem Rosto — quem ele era antes do elmo
4. A Contadora de Janelas — a rainha e os números
5. A Menina do Poço — o irmão que desceu e nunca voltou
6. O Forasteiro Sem Nome — o que acontece com quem chega depois
7. A Cripta — os sinos com nomes de gente viva
8. O Último Sino — quem tocou, e o que acordou

## Checklist de qualidade antes de renderizar

- [ ] os primeiros 30 segundos têm uma frase que dá arrepio
- [ ] existe pelo menos um diálogo que contradiz o narrador
- [ ] tem uma revelação por volta dos 40% e outra nos 90%
- [ ] o gancho de inscrição parece parte da história
- [ ] o fecho promete algo concreto para o próximo episódio
- [ ] `python -m fabrica timeline <slug>` mostra 10–15 min sem avisos
