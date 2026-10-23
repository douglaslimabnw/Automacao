# 🐷 Bolso em Dia — meus gastos

Um app **simples**, feito para o celular, para entender e planejar os gastos mensais.

## O que ele faz

- 📄 **Importa o extrato em PDF do Mercado Pago** e organiza tudo sozinho em categorias
  (cartão, supermercado, Farmácia, Pix para pessoas, reserva etc.) — a leitura acontece
  **dentro do próprio celular**, nada é enviado para a internet.
- 🏠 **Início:** quanto entrou, quanto saiu, quanto sobrou, gráfico "para onde foi o
  dinheiro", como o saldo se comportou no mês e observações em linguagem simples
  ("a fatura do cartão levou X% do que entrou", "seu saldo ficou abaixo de R$ 50 em N momentos"...).
- 🧾 **Gastos:** todas as movimentações com busca e filtro. Tocando em um gasto, você
  troca a categoria e o app **aprende** para as próximas vezes. Botão **+** para anotar
  gasto na hora.
- 🎯 **Planejar:** sua renda, contas fixas (com sugestões automáticas do que se repete
  todo mês), limite por categoria e a conta de **quanto dá para gastar por dia** até o fim do mês.
- 📱 Funciona como aplicativo (ícone na tela inicial, abre tela cheia e funciona offline).

## 🔒 Privacidade (importante)

- Os dados ficam **somente no aparelho** (no armazenamento do navegador/app).
- **Nenhum dado financeiro faz parte deste repositório** — PDFs e arquivos de dados
  estão bloqueados no `.gitignore`.
- Por isso, mesmo que o repositório seja público para publicar o app, seus gastos
  **não** estão nele. Use o botão **Backup** na aba "Mais" de vez em quando.

## Publicar para acessar de qualquer lugar (grátis)

Com o GitHub Pages:

1. No GitHub, abra este repositório → **Settings → General** → mude a visibilidade
   para **Public** (o Pages gratuito exige isso; repito: o repositório tem só o código, sem dados).
2. **Settings → Pages** → *Source: Deploy from a branch* → branch `main`, pasta **`/docs`** → Save.
3. Em 1–2 minutos o app estará em `https://SEU-USUARIO.github.io/Automacao/`
4. Abra o endereço no celular e instale:
   - **Android/Chrome:** menu ⋮ → *Instalar app*
   - **iPhone/Safari:** Compartilhar → *Adicionar à Tela de Início*

> Alternativa sem publicar: qualquer hospedagem estática (Netlify, Vercel, Cloudflare Pages)
> apontando para a pasta `docs/` funciona.

## Todo mês (30 segundos)

1. No app do Mercado Pago: **Extrato → escolher o mês → baixar o PDF**.
2. No Bolso em Dia: aba **Mais → Importar extrato novo** → escolher o PDF. Pronto.

## Estrutura

| Arquivo | O que é |
|---|---|
| `docs/index.html` · `docs/app.js` · `docs/style.css` | O aplicativo (HTML/CSS/JS puro, sem compilar nada) |
| `docs/manifest.webmanifest` · `docs/sw.js` | O que permite instalar e usar offline (PWA) |
| `importar_extrato.py` | Versão para computador: converte o PDF do Mercado Pago em JSON (`python3 importar_extrato.py extrato.pdf > transacoes.json`, precisa de `pip install pymupdf`) |

## Como o app decide a categoria (e como corrigir)

Ele reconhece padrões do extrato (fatura do cartão, supermercados, Uber, internet, a
"Reserva por gastos" de R$ 2 etc.) e considera a transferência mensal da outra conta e a
AROM como **renda**. Errou alguma? Toque na movimentação na aba **Gastos** e troque a
categoria — ele aprende aquele nome para sempre. A reserva automática e as transferências
entre suas próprias contas **não** contam como gasto nos gráficos.
