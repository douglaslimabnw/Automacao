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

- Por padrão, os dados ficam **somente no aparelho** (no armazenamento do navegador/app).
  Só vão para a nuvem se você ativar a **Família sincronizada** (abaixo) — e mesmo assim
  ficam numa tabela do seu próprio Supabase, legível apenas por quem tem a chave-secreta
  da família (o link do convite).
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

## Família sincronizada 💑 (automático, sem enviar arquivo)

Na aba **Mais → Família sincronizada**:

1. No seu celular: **🔗 Criar nossa família e convidar** → digo seu nome → ele cria uma
   chave-secreta, envia seus dados para a nuvem e prepara o convite.
2. Envie o **convite (link)** pelo WhatsApp **só para sua esposa/família** — o link é a
   "chave da casa": quem o tiver vê e pode lançar gastos.
3. Ela toca no link (abre o app), confirma o nome dela — e já vê **tudo igual**: meses,
   gráficos, insights e planos.

A partir daí, atualização é automática: lançou num celular, aparece no outro em até ~1
minuto (ou na hora em **🔄 Sincronizar agora**). Gastos digitados à mão mostram quem
lançou (✍️ nome). Sem internet, tudo fica salvo no aparelho e sobe quando conectar.

### Sem sincronizar (modo "foto")

No mesmo card: **📤 Enviar arquivo dos meus dados** manda um arquivo pelo WhatsApp;
a pessoa usa **Mais → Restaurar backup** e vê tudo naquela data. Também há o
**📝 resumo do mês em texto** pronto para colar no WhatsApp.

### Para quem mexe na parte técnica

A nuvem é o projeto Supabase gratuito **appfinanceiro** (São Paulo). A tabela
`public.Bolso_sync` guarda uma linha por família (`payload` JSON + `versao` para não
sobrescrever edição simultânea). A regra de segurança (RLS) só libera a linha para quem
apresenta a chave da família no cabeçalho `x-Bolso-key`; sem a chave, nada é legível.
O SQL exato está em `supabase/migration-bolso-sync.sql`. A chave que aparece no código do
app é a **pública** do projeto — sozinha, ela não lê dado nenhum.

## E vale / adiantamento, como lanço? 💵

Vale **não é dinheiro novo**: é um pedaço do salário que chega antes (e depois é
descontado — no próximo pagamento entra menos). São **dois lançamentos separados**:

1. **O vale entrando:**
   - Se caí na conta do Mercado Pago (Pix da empresa), Ele já aparece quando você
     importa o PDF. Confira/mude a categoria para **💵 Vale / adiantamento** (um toque —
     o app aprende o nome da empresa para as próximas).
   - Se recebeu em dinheiro ou em outra conta: botão **+** → **💰 Receber** → valor →
     descrição ex.: *"Vale da fIrma"* → categoria **Vale / adiantamento**.
2. **A conta que você pagou** continua sendo um gasto normal:
   - Internet/luz/telefone → categoria **📄 Contas**; fatura → **💳 Cartão**.
   - Pagou pelo Mercado Pago? Já vem no extrato. Pagou por fora? **+** → **💸 Gastar**.

> Exemplo: vale de R$ 200, internet de R$ 102. Você lança *Receber R$ 200 (Vale)* e
> *Gastar R$ 102 (Contas)*. Sobraram R$ 98 do vale — mas no dia do pagamento o salário
> vem **R$ 200 menor**. O app mostra esse lembrete nas observações do mês.

## Todo mês (30 segundos)

1. No app do Mercado Pago: **Extrato → escolher o mês → baixar o PDF**.
2. No Bolso em Dia: aba **Mais → Importar extrato novo** → escolher o PDF. Pronto.

## Estrutura

| Arquivo | O que é |
|---|---|
| `docs/index.html` · `docs/app.js` · `docs/style.css` | O aplicativo (HTML/CSS/JS puro, sem compilar nada) |
| `docs/manifest.webmanifest` · `docs/sw.js` | O que permite instalar e usar offline (PWA) |
| `importar_extrato.py` | Versão para computador: converte o PDF do Mercado Pago em JSON (`python3 importar_extrato.py extrato.pdf > transacoes.json`, precisa de `pip install pymupdf`) |
| `supabase/migration-bolso-sync.sql` | SQL que cria a tabela da Família sincronizada (aplicado no projeto appfinanceiro) |

## Como o app decide a categoria (e como corrigir)

Ele reconhece padrões do extrato (fatura do cartão, supermercados, Uber, internet, a
"Reserva por gastos" de R$ 2 etc.) e considera a transferência mensal vinda da outra conta
como **renda**. O nome do titular (para reconhecer transferências entre contas próprias)
é aprendido do cabeçalho do próprio PDF. Errou alguma? Toque na movimentação e troque a
categoria — ele aprende aquele nome para sempre. A reserva automática e as transferências
entre suas próprias contas **não** contam como gasto nos gráficos.
