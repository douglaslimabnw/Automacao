# 🎨 Identidade visual — "A Cada Dia, Aprender"

> Dia 5 da trilha. Visual dark editorial: sério como fonte de conhecimento, mas com contraste suficiente para vencer o feed.
> Tudo aqui é o padrão-mestre; thumbs e Shorts nunca devem destoar.

## 1. Paleta de cores

| Papel | Cor | Hex | Uso |
|---|---|---|---|
| Fundo profundo | Preto azulado | `#0B0E17` | Fundos de thumb e abertura |
| Fundo secundário | Azul-petróleo escuro | `#141A2E` | Cartões, overlays, banners |
| Cor de marca | Violeta mental | `#7C5CFF` | Logo, detalhes, gráficos, palavras-destaque secundárias |
| Impacto 1 | Amarelo vivo | `#FBBF24` | Palavra-chave de thumb (curiosidade) |
| Impacto 2 | Vermelho alerta | `#EF4444` | Palavra-chave de thumb (tensão/perigo) |
| Texto principal | Branco gelo | `#F5F7FF` | Títulos e legendas |
| Texto secundário | Cinza azulado | `#97A2BD` | Apoios e rodapés |

Regra: cada thumb usa no máximo **2 cores de texto** (branco + uma cor de impacto). Violeta é a assinatura recorrente da marca.

## 2. Tipografia

- **Títulos e thumbs:** Montserrat ExtraBold (alternativa premium: Sora). Fonte condensada, grossa, legível mesmo em tamanho de selo no celular.
- **Corpo e legendas:** Inter Medium/SemiBold (alternativa: Archivo).
- No Canva, buscar exatamente por "Montserrat" e "Inter" — ambas têm licença livre.

## 3. Peças e medidas oficiais

| Peça | Tamanho | Observação |
|---|---|---|
| Foto de perfil / logo | 800 × 800 px | Enxergar bem em 48 px (comentários) |
| Banner do canal | 2560 × 1440 px | Área segura central: **1546 × 423 px** — nada importante fora dela |
| Thumbnail de vídeo | 1280 × 720 px | Template mestre com a fórmula abaixo |
| Shorts | 1080 × 1920 px | Overlay com legenda central e frame final de CTA |
| Marca d'água de inscrição | 150 × 150 px | PNG transparente, só o símbolo |

## 4. Fórmula de thumbnail (validada na pesquisa do Dia 2)

> Fundo escuro texturizado (`#0B0E17`) + 1 elemento visual autoral (ilustração/IA estilizada ou metáfora, sem rosto real)
> + no máximo 3 palavras em Montserrat branca + 1 palavra de impacto em amarelo OU vermelho
> + moldura fina violeta opcional. Nada de foto parada: o elemento sempre recebe zoom/parallax na edição.

Exemplos de composição para as pautas-semente:
- "7 leis da estupidez": metáfora — burro elegante de terno, fundo turquesa escuro, texto "7 LEIS" (branco) + "ESTUPIDEZ" (amarelo).
- "Técnica do FBI": silhueta de agente com ouvido atento, texto "FAÇA AS PESSOAS" (branco) + "FALAREM" (vermelho).

## 5. Checklist de entrega do Dia 5

- [x] Logo 800×800 (símbolo + versão com nome) — gerado em `assets/identidade/logo-800x800.svg`
- [x] Banner 2560×1440 com tudo dentro da área segura (1546×423 px) — gerado em `assets/identidade/banner-2560x1440.svg`
- [x] Marca d'água 150×150 PNG/SVG transparente — gerada em `assets/identidade/marca-dagua-150x150.svg`
- [x] Template de thumb 1280×720 em SVG mestre — gerado em `assets/identidade/template-thumb-1280x720.svg`
- [x] Template de overlay de Shorts 1080×1920 — gerado em `assets/identidade/template-shorts-1080x1920.svg`
- [x] Pasta `assets/identidade` organizada com backup vetorial de todos os ativos
