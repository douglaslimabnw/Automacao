# Estética: como deixar o vídeo com cara de canal grande

O vídeo sai com: preto profundo, uma cor de luz (âmbar ou lua fria), névoa em
três camadas, grão de filme, crossfades de 0,7 s, legendas em Bebas Neue e
trilha de drone. Isso é o "padrão da casa" — o que faz alguém reconhecer o
canal pelo polegar.

## O que cada controle faz

| controle | efeito | valores que funcionam |
|---|---|---|
| `grao` | granulação de filme | 4–8 (acima de 12 parece VHS) |
| `vinheta` | escurece as bordas | 0.25–0.45 |
| `contraste` | soca os pretos | 1.05–1.15 |
| `saturacao` | dessatura a cor | 0.80–0.90 |
| `zoom` | intensidade do Ken Burns | 0.05–0.09 |
| `tremor` | micro-handheld | 0.2–0.5 (acima disso enjoa) |
| `transicao` | duração do crossfade | 0.6–1.0 |
| `intensidade` (trilha) | volume da trilha | 0.2–0.35 |
| `legendas` | `burn` / `srt` / `off` | burn para Shorts e mobile |

## Ritmo de corte

O motor divide blocos longos em planos de ~48 palavras, com piso de 2 s e teto
de 11 s. Para vídeos de lore, o alvo é:

- plano médio do personagem falando: 4–8 s
- plano aberto do cenário: 3–6 s
- nenhuma imagem parada por mais de 11 s

Se `python -m fabrica timeline <slug>` mostrar muitos planos de 11 s, o roteiro
tem parágrafos longos: divida em frases curtas com ponto final (é o que o
corte usa como fronteira natural).

## Substituir arte procedural por material real

O maior salto de qualidade não é o filtro — é o material. Ordem de impacto:

1. **Gameplay do próprio jogo** (o mais autêntico): 15–20 min gravados, sem HUD,
   cortados em clipes de 6–10 s. O render aplica o grade dark em cima.
2. **Screenshots em 4K** do jogo (mapa, item, cenário) — bom para "provas".
3. **Arte gerada por IA** para os momentos que o jogo não mostra (o guardião, a
   rainha). Gere em 16:9, style "cinematic concept art, dark fantasy", e salve
   em `episodes/<slug>/imagens/<id>.png`.
4. **Arte procedural** (fallback automático) para preencher tudo que faltar.

Basta nomear o arquivo com o id da cena (`c004.jpg`) e ele entra no lugar da
arte automática, sem mexer no código.

### Como achar os ids

```bash
python -m fabrica timeline <slug>     # lista id, tipo, início e duração
```

## Cartões e vinheta de marca

- abertura: título em Cinzel + "Episódio NN" sobre o cenário escurecido (4,5 s)
- gancho de meio: cartão "DEIXA O LIKE" + impacto sonoro
- fecho: cartão "INSCREVA-SE · novo episódio toda semana"

Troque os textos em `fabrica/roteiro.py` (`construir_plan`) — é o único lugar
onde a copy dos cartões aparece.

## Thumbnail

`python -m fabrica imagens <slug> --linha2 "40 anos sem sol"` gera a thumbnail
1280×720: base com gradiente escuro à esquerda, título em Cinzel e subtítulo em
Bebas Neue. Para escolher a cena:

```bash
python -m fabrica imagens <slug> --cena c012 --linha2 "o sino tocou 30 vezes"
```

Regra prática: 3–5 palavras grandes. O título completo fica na descrição.
