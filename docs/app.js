/* ════════════════════════════════════════════════════════════════
   Bolso em Dia — entenda e planeje seus gastos.
   100% no seu aparelho: os dados ficam no localStorage deste celular.
   ════════════════════════════════════════════════════════════════ */
"use strict";

/* ---------- categorias ---------- */
const CATS = {
  cartao:        { nome: "Cartão de crédito",      emoji: "💳", cor: "#8e44ad" },
  bancos:        { nome: "Banco / parcelas",        emoji: "🏦", cor: "#7f8c8d" },
  mercado:       { nome: "Supermercado",            emoji: "🛒", cor: "#27ae60" },
  comida:        { nome: "Alimentação",             emoji: "🍽️", cor: "#e67e22" },
  farmacia:      { nome: "Farmácia / saúde",        emoji: "💊", cor: "#e84393" },
  transporte:    { nome: "Transporte",              emoji: "🚗", cor: "#2980b9" },
  contas:        { nome: "Contas (internet, tel.)", emoji: "📄", cor: "#16a085" },
  compras:       { nome: "Compras",                 emoji: "🛍️", cor: "#d35400" },
  vestuario:     { nome: "Roupas",                  emoji: "👕", cor: "#9b59b6" },
  lazer:         { nome: "Lazer",                   emoji: "🎉", cor: "#f39c12" },
  pessoas:       { nome: "Pix p/ pessoas",          emoji: "👥", cor: "#c0392b" },
  reserva:       { nome: "Reserva (guardado)",      emoji: "🐷", cor: "#0e9f6e" },
  transferencia: { nome: "p/ minha outra conta",    emoji: "🔁", cor: "#95a5a6" },
  outros:        { nome: "Outros",                  emoji: "📦", cor: "#b2bec3" },
  renda:         { nome: "Renda / salário",         emoji: "💼", cor: "#0e9f6e" },
  pix_recebido:  { nome: "Pix recebido",            emoji: "🤝", cor: "#2ecc71" },
  rendimentos:   { nome: "Rendimentos",             emoji: "📈", cor: "#1abc9c" },
};
const CATS_SAIDA = ["mercado","comida","cartao","contas","transporte","farmacia","compras","vestuario","lazer","bancos","pessoas","reserva","transferencia","outros"];
const CATS_ENTRADA = ["renda","pix_recebido","rendimentos","reserva","transferencia","outros"];

/* ---------- utilidades ---------- */
const $ = (s) => document.querySelector(s);
const fmt = (v) => (v ?? 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
const semAcento = (s) => (s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toUpperCase();
const mesDe = (dataISO) => dataISO.slice(0, 7); // "2026-09-01" -> "2026-09"
const nomeMes = (m) => { const [a, mm] = m.split("-").map(Number);
  return new Date(a, mm - 1, 1).toLocaleDateString("pt-BR", { month: "long", year: "numeric" }); };
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;" }[c]));

/** Extrai o "nome" de uma descrição do extrato (sem "Pix enviado", "Pagamento..." etc.) */
function extrairNome(desc) {
  if (/fatura.*cartão/i.test(desc || "")) return "Fatura do cartão de crédito";
  return (desc || "")
    .replace(/^(Pagamento com QR Pix|Pagamento com Pix|Pagamento com código QR|Pagamento|Pix enviado|Pix recebido|Transferência (enviada|recebida)|Reembolso de transferência enviada)\s+/i, "")
    .replace(/\s+\d{11}$/, "") // CPF grudado no fim de alguns nomes
    .trim();
}

/* ---------- categorização automática ---------- */
function categorizar(desc, valor) {
  const d = semAcento(desc);
  if (d.includes("minhas economias".toUpperCase())) return "reserva";
  if (/UBER|99 TECNOLOGIA/.test(d)) return "transporte";
  if (d.includes("RENDIMENTOS")) return "rendimentos";
  if (d.includes("FATURA") && d.includes("cartao".toUpperCase())) return "cartao";
  const meuNome = d.includes("DOUGLAS ROBERTO NUNES DE LIMA");
  if (valor > 0) {
    if (d.startsWith("TRANSFERENCIA RECEBIDA") || d.includes("AROM SOLUCOES")) return "renda";
    if (d.includes("REEMBOLSO")) return "rendimentos";
    if (meuNome) return "transferencia";
    return "pix_recebido";
  }
  if (meuNome) return "transferencia";
  if (/SANTANDER|NU PAGAMENTOS|LEBI MARQUES/.test(d)) return "bancos";
  if (/SUPERMERCADO|SUPERALVO|MUFFATO|MERCADO MOOR|MERCEARIA|MERCADINHO|PAGAMENTO DIA\b/.test(d)) return "mercado";
  if (/BUFFET|ALIMENTOS|IFood|IFOOD|Rappi|RESTAURANTE|LANCHONETE|PIZZA/.test(d)) return "comida";
  if (/FARMACIA|PANVEL|NISSEI|CLAMED|DROGARIA|DROGASIL|RAIA/.test(d)) return "farmacia";
  if (/GIGA MAIS|FIBRA|CORREIOS CELULAR|TABELIONATO|NETFLIX|SPOTIFY|COPEL|SANEPAR|CLARO|VIVO|TIM\b/.test(d)) return "contas";
  if (/CONFECCOES|RENNER|C&A|RIACHUELO/.test(d)) return "vestuario";
  if (/MERCADO LIBRE|TUNA PAGAMENTOS|PAGSEGURO|PAGHIPER|BOM NEGOCIO|COSMETICOS|PRESENTES|CONSTRUCAO|AMAZON|SHOPEE|SHEIN|ALIEXPRESS/.test(d)) return "compras";
  if (/FUTSAL|CINEMA|INGRESSO/.test(d)) return "lazer";
  if (d.startsWith("PIX ENVIADO")) return "pessoas";
  return "outros";
}

/* ---------- estado (salvo só neste aparelho) ---------- */
const salvar = (chave, valor) => localStorage.setItem("Bolso." + chave, JSON.stringify(valor));
const ler = (chave, padrao) => { try { return JSON.parse(localStorage.getItem("Bolso." + chave)) ?? padrao; } catch { return padrao; } };

let transacoes = ler("tx", []);          // [{id,data,descricao,valor,saldo?,categoria,origem}]
let metas = ler("metas", {});            // {cat: limiteMensal}
let fixas = ler("fixas", []);            // [{nome,valor,dia}]
let regras = ler("regras", {});          // {nome normalizado: categoria} — aprendido com você
let cfg = ler("cfg", { renda: 0 });
let mesSel = ler("mesSel", null);
let filtroCat = "todas", termoBusca = "";
let sync = ler("sync", null);            // {chave, meuNome, versao, ultimaSync} — família sincronizada
let excluidas = ler("excluidas", []);    // [{chave, em}] transações apagadas (p/ apagar no outro celular também)
let aplicandoRemoto = false, sincronizando = false, temPendencia = false, timerEnvio = null, ultimoErroSync = "";

function salvarTudo() {
  salvar("tx", transacoes); salvar("metas", metas); salvar("fixas", fixas); salvar("regras", regras);
  salvar("cfg", cfg); salvar("excluidas", excluidas); if (mesSel) salvar("mesSel", mesSel);
  if (sync && !aplicandoRemoto) agendarEnvio();
}

function catDe(t) {
  const chave = semAcento(extrairNome(t.descricao));
  return regras[chave] || t.categoria || categorizar(t.descricao, t.valor);
}

/* ---------- agregações ---------- */
function mesesDisponiveis() {
  const s = new Set(transacoes.map((t) => mesDe(t.data)));
  const agora = new Date();
  s.add(`${agora.getFullYear()}-${String(agora.getMonth() + 1).padStart(2, "0")}`);
  return [...s].sort();
}
function doMes(mes) { return transacoes.filter((t) => mesDe(t.data) === mes); }
/** "gasto de verdade": não conta reserva (é dinheiro guardado) nem transferência entre contas próprias */
const ehGasto = (t) => t.valor < 0 && !["reserva", "transferencia"].includes(catDe(t));
const ehRenda = (t) => t.valor > 0 && catDe(t) !== "transferencia" && catDe(t) !== "reserva";

function somarCats(lista, predicado) {
  const mapa = {};
  for (const t of lista) {
    if (!predicado(t)) continue;
    const c = catDe(t);
    mapa[c] = mapa[c] || { total: 0, n: 0 };
    mapa[c].total += t.valor; mapa[c].n++;
  }
  return mapa;
}

/** Detecta gastos que se repetem (mesmo nome em 2+ meses ou 2+ vezes com mesmo valor) */
function detectarRecorrentes() {
  const porNome = {};
  for (const t of transacoes) {
    if (t.valor >= 0 || ["reserva", "rendimentos", "transferencia", "cartao"].includes(catDe(t))) continue;
    const nome = extrairNome(t.descricao);
    const chave = semAcento(nome);
    (porNome[chave] = porNome[chave] || { nome, meses: new Set(), valores: [], dias: [] });
    porNome[chave].meses.add(mesDe(t.data));
    porNome[chave].valores.push(Math.abs(t.valor));
    porNome[chave].dias.push(Number(t.data.slice(8)));
  }
  return Object.values(porNome)
    .filter((r) => r.meses.size >= 2 || r.valores.length >= 3)
    .map((r) => ({
      nome: r.nome,
      valor: Math.round((r.valores.reduce((a, b) => a + b, 0) / r.valores.length) * 100) / 100,
      dia: r.dias.sort((a, b) => a - b)[Math.floor(r.dias.length / 2)],
      vezes: r.valores.length,
    }))
    .sort((a, b) => b.valor - a.valor);
}

/* ---------- insights em português simples ---------- */
function gerarInsights(mes, mesAnterior) {
  const dicas = [];
  const tx = doMes(mes);
  const entrou = tx.filter((t) => t.valor > 0).reduce((s, t) => s + t.valor, 0);
  const saiu = tx.filter(ehGasto).reduce((s, t) => s + Math.abs(t.valor), 0);
  const porCat = somarCats(tx, ehGasto);

  if (porCat.cartao && entrou > 0) {
    const pct = Math.round((Math.abs(porCat.cartao.total) / entrou) * 100);
    dicas.push(`💳 A fatura do cartão levou <strong>${fmt(Math.abs(porCat.cartao.total))}</strong> — <strong>${pct}% de tudo que entrou</strong> no mês.` +
      (pct >= 50 ? " Quando o cartão passa da metade da renda, o mês inteiro fica apertado. Vale olhar o que está dentro dessa fatura." : ""));
  }
  const guardadoBruto = tx.filter((t) => catDe(t) === "reserva" && t.valor < 0).reduce((s, t) => s + Math.abs(t.valor), 0);
  const retiradoReserva = tx.filter((t) => catDe(t) === "reserva" && t.valor > 0).reduce((s, t) => s + t.valor, 0);
  const nReservas = tx.filter((t) => catDe(t) === "reserva" && t.valor < 0).length;
  if (nReservas > 0) dicas.push(`🐷 Você guardou <strong>${fmt(guardadoBruto)}</strong> sem perceber (${nReservas} reservinhas automáticas)${retiradoReserva ? ` e retirou ${fmt(retiradoReserva)} de volta` : ""}. Esse hábito é ouro — continue!`);
  const pixPessoas = tx.filter((t) => ehRenda(t) && catDe(t) === "pix_recebido").reduce((s, t) => s + t.valor, 0);
  if (pixPessoas > 0 && entrou > 0)
    dicas.push(`🤝 <strong>${fmt(pixPessoas)}</strong> entraram por Pix de pessoas (${Math.round((pixPessoas / entrou) * 100)}% das entradas). Sem isso, o mês fecharia em <strong>${fmt(entrou - pixPessoas - saiu)}</strong>. Bom saber para planejar o próximo.`);
  const comSaldo = tx.filter((t) => typeof t.saldo === "number");
  if (comSaldo.length > 5) {
    const apertados = comSaldo.filter((t) => t.saldo < 50).length;
    const menor = Math.min(...comSaldo.map((t) => t.saldo));
    if (menor < 50) dicas.push(`📉 Em <strong>${apertados} momentos</strong> do mês seu saldo ficou abaixo de R$ 50 (menor: ${fmt(menor)}). Separar as contas fixas logo que o dinheiro entra ajuda a não zerar.`);
  }
  const formiga = tx.filter((t) => ehGasto(t) && Math.abs(t.valor) <= 20);
  if (formiga.length >= 5)
    dicas.push(`🐜 Foram <strong>${formiga.length} gastos pequenos</strong> (até R$ 20) somando <strong>${fmt(formiga.reduce((s, t) => s + Math.abs(t.valor), 0))}</strong>. Sozinhos parecem nada, juntos pesam.`);
  if (mesAnterior) {
    const ant = somarCats(doMes(mesAnterior), ehGasto);
    let pior = null;
    for (const [c, v] of Object.entries(porCat)) {
      const antes = Math.abs(ant[c]?.total || 0), agora = Math.abs(v.total);
      if (antes > 50 && agora > antes * 1.3 && (!pior || agora - antes > pior.diff)) pior = { c, antes, agora, diff: agora - antes };
    }
    if (pior) dicas.push(`📊 <strong>${CATS[pior.c].nome}</strong> subiu bastante: de ${fmt(pior.antes)} para <strong>${fmt(pior.agora)}</strong> (+${fmt(pior.diff)} vs. mês anterior).`);
    else if (saiu > 0) {
      const saiuAnt = doMes(mesAnterior).filter(ehGasto).reduce((s, t) => s + Math.abs(t.valor), 0);
      if (saiuAnt > 0) {
        const d = Math.round(((saiu - saiuAnt) / saiuAnt) * 100);
        dicas.push(d <= 0
          ? `👏 Você gastou <strong>${Math.abs(d)}% a menos</strong> que no mês anterior (${fmt(saiu)} contra ${fmt(saiuAnt)}). Continue assim!`
          : `📊 No total, os gastos ficaram <strong>${d}% maiores</strong> que no mês anterior (${fmt(saiu)} contra ${fmt(saiuAnt)}).`);
      }
    }
  }
  const rec = detectarRecorrentes().filter((r) => r.valor >= 80 && !fixas.some((f) => semAcento(f.nome) === semAcento(r.nome)));
  if (rec.length) dicas.push(`📌 <strong>${esc(rec[0].nome)}</strong> (${fmt(rec[0].valor)}) aparece todo mês. Veja na aba <em>Planejar</em> para transformar em conta fixa — assim você já conta com ele no orçamento.`);
  if (!dicas.length) dicas.push("Quando houver mais movimentações, eu destaco aqui os pontos mais importantes do mês. 🙂");
  return dicas;
}

/* ---------- desenhos (gráficos) ---------- */
function desenharRosca(canvas, porCat) {
  const ctx = canvas.getContext("2d");
  const itens = Object.entries(porCat).map(([c, v]) => ({ c, valor: Math.abs(v.total) })).filter((i) => i.valor > 0).sort((a, b) => b.valor - a.valor);
  const total = itens.reduce((s, i) => s + i.valor, 0);
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  if (!total) return itens;
  let ang = -Math.PI / 2;
  const cx = canvas.width / 2, cy = canvas.height / 2, r = Math.min(cx, cy) - 6;
  for (const i of itens) {
    const fatia = (i.valor / total) * Math.PI * 2;
    ctx.beginPath(); ctx.moveTo(cx, cy); ctx.arc(cx, cy, r, ang, ang + fatia); ctx.closePath();
    ctx.fillStyle = CATS[i.c].cor; ctx.fill();
    ang += fatia;
  }
  ctx.globalCompositeOperation = "destination-out";
  ctx.beginPath(); ctx.arc(cx, cy, r * 0.55, 0, Math.PI * 2); ctx.fill();
  ctx.globalCompositeOperation = "source-over";
  return itens;
}

function desenharSaldo(canvas, tx) {
  const comSaldo = tx.filter((t) => typeof t.saldo === "number").sort((a, b) => a.data.localeCompare(b.data));
  const card = $("#cardSaldo");
  if (comSaldo.length < 3) { card.style.display = "none"; return; }
  card.style.display = "";
  canvas.width = canvas.clientWidth * devicePixelRatio || 600;
  canvas.height = 120 * devicePixelRatio;
  const ctx = canvas.getContext("2d");
  const W = canvas.width, H = canvas.height, pad = 8 * devicePixelRatio;
  const max = Math.max(...comSaldo.map((t) => t.saldo)), min = Math.min(0, ...comSaldo.map((t) => t.saldo));
  const X = (i) => pad + (i / (comSaldo.length - 1)) * (W - 2 * pad);
  const Y = (v) => H - pad - ((v - min) / ((max - min) || 1)) * (H - 2 * pad);
  ctx.strokeStyle = "#e05252"; ctx.setLineDash([5, 5]); ctx.lineWidth = devicePixelRatio;
  ctx.beginPath(); ctx.moveTo(pad, Y(50)); ctx.lineTo(W - pad, Y(50)); ctx.stroke(); ctx.setLineDash([]);
  const grad = ctx.createLinearGradient(0, 0, 0, H);
  grad.addColorStop(0, "rgba(14,159,110,.45)"); grad.addColorStop(1, "rgba(14,159,110,.02)");
  ctx.beginPath(); comSaldo.forEach((t, i) => i ? ctx.lineTo(X(i), Y(t.saldo)) : ctx.moveTo(X(i), Y(t.saldo)));
  ctx.strokeStyle = "#0e9f6e"; ctx.lineWidth = 2 * devicePixelRatio; ctx.stroke();
  ctx.lineTo(X(comSaldo.length - 1), H - pad); ctx.lineTo(X(0), H - pad); ctx.closePath();
  ctx.fillStyle = grad; ctx.fill();
  const menor = Math.min(...comSaldo.map((t) => t.saldo));
  $("#saldoFrase").textContent = `Maior saldo: ${fmt(max)} · menor: ${fmt(menor)} · linha tracejada = R$ 50 (zona de aperto)`;
}

/* ---------- telas ---------- */
function toast(msg) {
  document.querySelector(".toast")?.remove();
  const el = document.createElement("div"); el.className = "toast"; el.innerHTML = msg;
  document.body.appendChild(el); setTimeout(() => el.remove(), 4200);
}

function txHTML(t) {
  const c = catDe(t);
  const sinal = t.valor < 0 ? "−" : "+";
  return `<div class="tx" data-id="${esc(t._uid)}">
    <div class="emoji">${CATS[c].emoji}</div>
    <div class="meio"><div class="desc">${esc(extrairNome(t.descricao) || t.descricao)}</div>
    <div class="sub">${CATS[c].nome} · ${t.data.slice(8)}/${t.data.slice(5, 7)}${t.por ? " · ✍️ " + esc(t.por) : ""}</div></div>
    <div class="valor ${t.valor < 0 ? "vermelho" : "verde"}">${sinal} ${fmt(Math.abs(t.valor))}</div></div>`;
}

function renderInicio() {
  const tx = doMes(mesSel);
  $("#semDados").hidden = transacoes.length > 0;
  $("#resumoWrap").style.display = transacoes.length ? "" : "none";
  // Cartões = totais brutos, iguais ao extrato (para conferir com o PDF).
  // Nos gráficos de categorias, reserva e transferências entre contas próprias ficam de fora.
  const entrou = tx.filter((t) => t.valor > 0).reduce((s, t) => s + t.valor, 0);
  const saiu = tx.filter((t) => t.valor < 0).reduce((s, t) => s + Math.abs(t.valor), 0);
  $("#rEntrou").textContent = fmt(entrou);
  $("#rSaiu").textContent = fmt(saiu);
  const sobrou = entrou - saiu;
  const el = $("#rSobrou"); el.textContent = fmt(sobrou); el.className = sobrou >= 0 ? "verde" : "vermelho";
  $("#resumoFrase").textContent = entrou === 0 && saiu === 0
    ? "Nenhuma movimentação neste mês ainda."
    : sobrou >= 0
      ? `Em ${nomeMes(mesSel)}, no total, sobrou dinheiro na conta. 🎉`
      : `Em ${nomeMes(mesSel)} saiu ${fmt(Math.abs(sobrou))} a mais do que entrou. Veja abaixo onde apertou.`;

  const porCat = somarCats(tx, ehGasto);
  const meses = mesesDisponiveis();
  const mesAnt = meses[meses.indexOf(mesSel) - 1];
  const ant = mesAnt ? somarCats(doMes(mesAnt), ehGasto) : {};
  const itens = desenharRosca($("#graficoRosca"), porCat);
  const total = itens.reduce((s, i) => s + i.valor, 0) || 1;
  $("#legendaRosca").innerHTML = itens.slice(0, 6).map((i) =>
    `<div><span class="bolinha" style="background:${CATS[i.c].cor}"></span>${CATS[i.c].emoji} ${CATS[i.c].nome} — <strong>${Math.round((i.valor / total) * 100)}%</strong></div>`).join("");
  $("#listaCategorias").innerHTML = itens.map((i) => {
    const antes = Math.abs(ant[i.c]?.total || 0);
    const delta = antes > 0 ? `<span class="delta">${i.valor > antes ? "▲" : "▼"} ${fmt(Math.abs(i.valor - antes))} vs mês passado</span>` : "";
    return `<div class="cat-linha"><div class="cat-topo"><span>${CATS[i.c].emoji} ${CATS[i.c].nome}${delta}</span><strong>${fmt(i.valor)}</strong></div>
      <div class="barra"><i style="width:${Math.max(3, (i.valor / total) * 100)}%;background:${CATS[i.c].cor}"></i></div></div>`;
  }).join("") || `<p class="vazio">Sem gastos neste mês.</p>`;

  desenharSaldo($("#graficoSaldo"), tx);
  $("#listaInsights").innerHTML = gerarInsights(mesSel, mesAnt).map((d) => `<li>${d}</li>`).join("");
  const top = tx.filter(ehGasto).sort((a, b) => a.valor - b.valor).slice(0, 5);
  $("#topGastos").innerHTML = top.map(txHTML).join("") || `<p class="vazio">—</p>`;
}

function renderGastos() {
  const catsUsadas = ["todas", ...new Set(doMes(mesSel).map(catDe))];
  $("#chipsCategorias").innerHTML = catsUsadas.map((c) =>
    `<button class="chip ${filtroCat === c ? "ativo" : ""}" data-chip="${c}">${c === "todas" ? "Todas" : CATS[c].emoji + " " + CATS[c].nome}</button>`).join("");
  let lista = doMes(mesSel).slice().sort((a, b) => b.data.localeCompare(a.data) || String(b.id).localeCompare(String(a.id)));
  if (filtroCat !== "todas") lista = lista.filter((t) => catDe(t) === filtroCat);
  if (termoBusca) lista = lista.filter((t) => semAcento(t.descricao).includes(semAcento(termoBusca)));
  if (!lista.length) { $("#listaTransacoes").innerHTML = `<p class="vazio">Nada por aqui neste mês. 🙌</p>`; return; }
  let html = "", diaAtual = "";
  for (const t of lista) {
    if (t.data !== diaAtual) {
      diaAtual = t.data;
      const [a, m, d] = t.data.split("-").map(Number);
      html += `<div class="dia-titulo">${new Date(a, m - 1, d).toLocaleDateString("pt-BR", { weekday: "long", day: "numeric", month: "long" })}</div>`;
    }
    html += txHTML(t);
  }
  $("#listaTransacoes").innerHTML = html;
}

function rendaSugerida() {
  const meses = mesesDisponiveis().filter((m) => doMes(m).some((t) => ehRenda(t) && catDe(t) === "renda"));
  if (!meses.length) return 0;
  const soma = meses.reduce((s, m) => s + doMes(m).filter((t) => catDe(t) === "renda").reduce((a, t) => a + t.valor, 0), 0);
  return Math.round(soma / meses.length);
}

function renderPlanejar() {
  if (!cfg.renda) { cfg.renda = rendaSugerida(); }
  $("#inputRenda").value = cfg.renda || "";
  const totalFixas = fixas.reduce((s, f) => s + Number(f.valor || 0), 0);
  $("#totalFixas").textContent = fmt(totalFixas);
  $("#listaFixas").innerHTML = fixas.map((f, i) =>
    `<div class="fixa"><div><strong>${esc(f.nome)}</strong><small>${f.dia ? "todo dia " + f.dia : "todo mês"}</small></div>
     <div><strong>${fmt(Number(f.valor))}</strong> <button class="x" data-del-fixa="${i}" aria-label="Remover">✕</button></div></div>`).join("")
    || `<p class="vazio">Nenhuma conta fixa ainda. Adicione abaixo ou aceite uma sugestão. 👇</p>`;

  const sugs = detectarRecorrentes().filter((r) => !fixas.some((f) => semAcento(f.nome) === semAcento(r.nome))).slice(0, 4);
  $("#sugestoesFixas").innerHTML = sugs.map((r, i) =>
    `<div class="sugestao">🔎 Notei que <strong>${esc(r.nome)}</strong> (${fmt(r.valor)}, por volta do dia ${r.dia}) se repete (${r.vezes}×). É uma conta fixa?
     <br><button class="btn primario" data-add-sug="${i}">Sim, adicionar</button></div>`).join("");
  $("#sugestoesFixas").dataset.json = JSON.stringify(sugs);

  // pode gastar por dia (mês atual real)
  const hoje = new Date();
  const mesAtualReal = `${hoje.getFullYear()}-${String(hoje.getMonth() + 1).padStart(2, "0")}`;
  const txMes = doMes(mesAtualReal);
  const jaGastou = txMes.filter(ehGasto).reduce((s, t) => s + Math.abs(t.valor), 0);
  const ultimoDia = new Date(hoje.getFullYear(), hoje.getMonth() + 1, 0).getDate();
  const diasRestantes = Math.max(1, ultimoDia - hoje.getDate() + 1);
  const entrouEsteMes = txMes.filter((t) => t.valor > 0).reduce((s, t) => s + t.valor, 0);
  const base = Math.max(cfg.renda || 0, entrouEsteMes); // se já entrou mais que a renda típica, uso o que entrou
  const livre = base - jaGastou;
  $("#podeGastar").innerHTML = !cfg.renda
    ? `<span class="nota">Preencha sua renda para eu calcular quanto dá para gastar por dia.</span>`
    : livre > 0
      ? `Neste mês já gastou <strong>${fmt(jaGastou)}</strong>. Contando com o que já entrou (${fmt(base)}), ainda dá para gastar<span class="grande-num">${fmt(livre / diasRestantes)} por dia</span>até o fim do mês sem ficar no vermelho${totalFixas ? ` — lembre das contas fixas (${fmt(totalFixas)})` : ""}.`
      : `⚠️ Neste mês já gastou <strong>${fmt(jaGastou)}</strong>, acima dos ${fmt(base)} que entraram. Segure os gastos variáveis até a próxima entrada.`;

  if (cfg.renda) {
    const r = cfg.renda;
    $("#regra503020").innerHTML =
      `<div style="flex:5;background:#0e9f6e">Essencial<br>${fmt(r * .5)}</div>
       <div style="flex:3;background:#e6a817">Lazer/desejos<br>${fmt(r * .3)}</div>
       <div style="flex:2;background:#2980b9">Guardar<br>${fmt(r * .2)}</div>`;
    $("#regra503020").title = "Sugestão simples 50/30/20";
  }

  // metas
  const porCat = somarCats(doMes(mesSel), ehGasto);
  const catsComAlgo = [...new Set([...CATS_SAIDA.filter((c) => porCat[c] || metas[c])])];
  $("#listaMetas").innerHTML = catsComAlgo.map((c) => {
    const gasto = Math.abs(porCat[c]?.total || 0);
    const limite = Number(metas[c] || 0);
    const pct = limite ? Math.min(100, (gasto / limite) * 100) : 0;
    const classe = limite && gasto > limite ? "estourou" : limite && gasto > limite * 0.8 ? "alerta" : "";
    return `<div class="meta-linha"><div class="meta-topo"><span>${CATS[c].emoji} ${CATS[c].nome}</span>
      <span>${fmt(gasto)} de <button class="meta-valor" data-meta="${c}">${limite ? fmt(limite) : "definir limite"}</button></span></div>
      ${limite ? `<div class="barra"><i class="${classe}" style="width:${pct}%"></i></div>` : ""}</div>`;
  }).join("");
}

function renderBannerEspelho() {
  const b = $("#bannerEspelho");
  if (!cfg.espelhoEm) { b.hidden = true; return; }
  const quando = new Date(cfg.espelhoEm).toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
  b.hidden = false;
  b.innerHTML = `👀 Você está vendo os dados compartilhados em <strong>${quando}</strong>. Para atualizar, Peça um novo envio (é rapidinho). <button class="btn texto" id="btnSairEspelho">Estou no meu próprio app</button>`;
  b.querySelector("#btnSairEspelho").onclick = () => { delete cfg.espelhoEm; salvarTudo(); renderBannerEspelho(); };
}

function render() {
  $("#mesAtual").textContent = nomeMes(mesSel);
  renderBannerEspelho();
  renderSync();
  renderInicio(); renderGastos(); renderPlanejar();
}

/* ---------- interações ---------- */
document.querySelector(".bottom-nav").addEventListener("click", (e) => {
  const b = e.target.closest("[data-aba]"); if (!b) return;
  document.querySelectorAll(".bottom-nav button").forEach((x) => x.classList.toggle("ativa", x === b));
  document.querySelectorAll(".aba").forEach((x) => x.classList.toggle("ativa", x.id === "aba-" + b.dataset.aba));
  window.scrollTo({ top: 0 });
});
function irParaAba(nome) { document.querySelector(`[data-aba="${nome}"]`).click(); }

function mudarMes(dir) {
  const meses = mesesDisponiveis();
  const i = meses.indexOf(mesSel);
  const novo = meses[i + dir];
  if (novo) { mesSel = novo; salvarTudo(); render(); }
}
$("#mesAnt").onclick = () => mudarMes(-1);
$("#mesProx").onclick = () => mudarMes(1);
$("#busca").addEventListener("input", (e) => { termoBusca = e.target.value; renderGastos(); });
$("#chipsCategorias").addEventListener("click", (e) => {
  const b = e.target.closest("[data-chip]"); if (!b) return;
  filtroCat = b.dataset.chip; renderGastos();
});

/* Sheet (ficha da transação / adicionar) */
function abrirSheet(html) { $("#sheetConteudo").innerHTML = html; $("#fundoSheet").hidden = false; $("#sheet").hidden = false; }
function fecharSheet() { $("#fundoSheet").hidden = true; $("#sheet").hidden = true; }
$("#fundoSheet").onclick = fecharSheet;

document.addEventListener("click", (e) => {
  const el = e.target.closest(".tx[data-id]");
  if (el) { const t = transacoes.find((x) => x._uid === el.dataset.id); if (t) abrirFicha(t); }
  const imp = e.target.closest("[data-importar]");
  if (imp) $("#inputPdf").click();
});

function gradeCatsHTML(selecionada, tipo) {
  const lista = tipo === "entrada" ? CATS_ENTRADA : CATS_SAIDA;
  return `<div class="grade-cats">${lista.map((c) =>
    `<button type="button" data-cat-escolha="${c}" class="${c === selecionada ? "sel" : ""}">${CATS[c].emoji}<br>${CATS[c].nome}</button>`).join("")}</div>`;
}

function abrirFicha(t) {
  const nome = extrairNome(t.descricao) || t.descricao;
  abrirSheet(`
    <h3>${esc(nome)}</h3>
    <p class="nota">${t.data.split("-").reverse().join("/")} · <strong class="${t.valor < 0 ? "vermelho" : "verde"}">${fmt(t.valor)}</strong></p>
    <p>Está na categoria certa? Se trocar, eu aprendo e já acerto da próxima vez. 🧠</p>
    ${gradeCatsHTML(catDe(t), t.valor > 0 ? "entrada" : "saida")}
    <div style="margin-top:16px; display:flex; gap:8px; flex-wrap:wrap">
      <button class="btn primario" id="fichaOk" style="flex:1">Pronto</button>
      <button class="btn perigo" id="fichaExcluir">Excluir</button>
    </div>`);
  $("#sheetConteudo").querySelectorAll("[data-cat-escolha]").forEach((b) => b.onclick = () => {
    document.querySelectorAll("[data-cat-escolha]").forEach((x) => x.classList.toggle("sel", x === b));
    regras[semAcento(nome)] = b.dataset.catEscolha;
    t.categoria = b.dataset.catEscolha; t.editadoEm = Date.now();
    salvarTudo(); render();
    toast(`✅ Categorizei “${esc(nome)}” como <strong>${CATS[b.dataset.catEscolha].nome}</strong> (e vou lembrar nas próximas).`);
  });
  $("#fichaOk").onclick = fecharSheet;
  $("#fichaExcluir").onclick = () => {
    if (confirm("Excluir esta movimentação?")) {
      transacoes = transacoes.filter((x) => x !== t); excluidas.push({ chave: chaveTx(t), em: Date.now() }); salvarTudo(); fecharSheet(); render(); toast("Movimentação excluída.");
    }
  };
}

function abrirAdicionar() {
  const hoje = new Date().toISOString().slice(0, 10);
  let tipo = "saida", catSel = "mercado";
  abrirSheet(`
    <h3>Adicionar movimentação</h3>
    <div class="tipo-toggle">
      <button type="button" id="tipoSaida" class="sel-saida">💸 Gastar</button>
      <button type="button" id="tipoEntrada">💰 Receber</button>
    </div>
    <label>Quanto? (R$)</label><input type="number" id="novoValor" inputmode="decimal" min="0" step="0.01" placeholder="0,00">
    <label>O que é?</label><input type="text" id="novaDesc" placeholder="Ex.: Padaria, Salário, Pix da mãe...">
    <label>Quando?</label><input type="date" id="novaData" value="${hoje}">
    <label>Categoria</label><div id="gradeNova">${gradeCatsHTML(catSel, "saida")}</div>
    <button class="btn primario grande" id="btnSalvarNovo" style="margin-top:16px">Salvar</button>`);
  const ligarGrade = () => $("#gradeNova").querySelectorAll("[data-cat-escolha]").forEach((b) => b.onclick = () => {
    catSel = b.dataset.catEscolha;
    $("#gradeNova").querySelectorAll("[data-cat-escolha]").forEach((x) => x.classList.toggle("sel", x === b));
  });
  ligarGrade();
  const setTipo = (tp) => {
    tipo = tp; catSel = tp === "entrada" ? "renda" : "mercado";
    $("#tipoSaida").className = tp === "saida" ? "sel-saida" : "";
    $("#tipoEntrada").className = tp === "entrada" ? "sel-entrada" : "";
    $("#gradeNova").innerHTML = gradeCatsHTML(catSel, tp); ligarGrade();
  };
  $("#tipoSaida").onclick = () => setTipo("saida");
  $("#tipoEntrada").onclick = () => setTipo("entrada");
  $("#btnSalvarNovo").onclick = () => {
    const v = parseFloat($("#novoValor").value);
    const desc = $("#novaDesc").value.trim();
    if (!v || v <= 0 || !desc) { toast("Preencha o valor e o que é 🙂"); return; }
    transacoes.push({
      id: "manual-" + Date.now(), _uid: "u" + Date.now() + Math.random().toString(36).slice(2, 7),
      data: $("#novaData").value || hoje, descricao: desc,
      valor: tipo === "saida" ? -v : v, categoria: catSel, origem: "manual", editadoEm: Date.now(), ...(sync?.meuNome ? { por: sync.meuNome } : {}),
    });
    mesSel = mesDe($("#novaData").value || hoje);
    salvarTudo(); fecharSheet(); render(); toast("✅ Salvo!");
  };
}
$("#fab").onclick = abrirAdicionar;
$("#btnManualVazio").onclick = abrirAdicionar;

/* Planejar: eventos */
$("#btnSalvarRenda").onclick = () => {
  cfg.renda = parseFloat($("#inputRenda").value) || 0; salvarTudo(); renderPlanejar(); toast("✅ Renda salva: " + fmt(cfg.renda) + "/mês");
};
$("#formFixa").addEventListener("submit", (e) => {
  e.preventDefault();
  const f = new FormData(e.target);
  fixas.push({ nome: String(f.get("nome")), valor: parseFloat(f.get("valor")) || 0, dia: parseInt(f.get("dia")) || null });
  e.target.reset(); salvarTudo(); renderPlanejar(); toast("📌 Conta fixa adicionada!");
});
$("#aba-planejar").addEventListener("click", (e) => {
  const del = e.target.closest("[data-del-fixa]");
  if (del) { fixas.splice(Number(del.dataset.delFixa), 1); salvarTudo(); renderPlanejar(); }
  const sug = e.target.closest("[data-add-sug]");
  if (sug) {
    const sugs = JSON.parse($("#sugestoesFixas").dataset.json || "[]");
    const r = sugs[Number(sug.dataset.addSug)];
    if (r) { fixas.push({ nome: r.nome, valor: r.valor, dia: r.dia }); salvarTudo(); renderPlanejar(); toast("📌 Adicionado às contas fixas!"); }
  }
  const meta = e.target.closest("[data-meta]");
  if (meta) {
    const c = meta.dataset.meta;
    const atual = metas[c] || "";
    const resp = prompt(`Limite mensal para ${CATS[c].emoji} ${CATS[c].nome} (R$). Deixe vazio para remover:`, atual);
    if (resp === null) return;
    const v = parseFloat(String(resp).replace(",", "."));
    if (v > 0) metas[c] = v; else delete metas[c];
    salvarTudo(); renderPlanejar();
  }
});

/* Backup / compartilhar */
function montarBackup() {
  return JSON.stringify({ app: "Bolso em Dia", versao: 1, exportadoEm: new Date().toISOString(), transacoes, metas, fixas, regras, cfg }, null, 1);
}
function baixarBackup(aviso) {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([montarBackup()], { type: "application/json" }));
  a.download = "backup-bolso-em-dia.json"; a.click(); URL.revokeObjectURL(a.href);
  toast(aviso || "⬇️ Arquivo baixado. Envie pelo WhatsApp e ela usa em Mais → Restaurar backup.");
}
$("#btnExportar").onclick = () => baixarBackup("⬇️ Backup baixado. Guarde em lugar seguro!");
$("#btnCompartilharDados").onclick = async () => {
  const arquivo = new File([montarBackup()], "backup-bolso-em-dia.json", { type: "application/json" });
  if (navigator.canShare?.({ files: [arquivo] })) {
    try { await navigator.share({ files: [arquivo], title: "Bolso em Dia — nossos gastos" }); } catch { /* cancelou o envio */ }
    return;
  }
  baixarBackup();
};
$("#btnCompartilharLink").onclick = async () => {
  const url = location.origin + location.pathname;
  if (navigator.share) {
    try { await navigator.share({ title: "Bolso em Dia — nossos gastos", text: "Abre este link e instala o app dos nossos gastos 🐷", url }); } catch { /* cancelou */ }
    return;
  }
  try { await navigator.clipboard.writeText(url); toast("🔗 Link copiado! Cole no WhatsApp dela."); }
  catch { toast("Copie o endereço da barra do navegador e envie para ela."); }
};
$("#btnCompartilharResumo").onclick = async () => {
  const tx = doMes(mesSel);
  const entrou = tx.filter((t) => t.valor > 0).reduce((sm, t) => sm + t.valor, 0);
  const saiu = tx.filter((t) => t.valor < 0).reduce((sm, t) => sm + Math.abs(t.valor), 0);
  const top = Object.entries(somarCats(tx, ehGasto))
    .map(([c, v]) => ({ c, valor: Math.abs(v.total) })).sort((a, b) => b.valor - a.valor).slice(0, 4);
  const texto = [
    `🐷 *Bolso em Dia — ${nomeMes(mesSel)}*`,
    `💰 Entrou: ${fmt(entrou)}`,
    `💸 Saiu: ${fmt(saiu)}`,
    entrou - saiu >= 0 ? `🎉 Sobrou: ${fmt(entrou - saiu)}` : `🔴 Faltou: ${fmt(Math.abs(entrou - saiu))}`,
    ``, `Maiores gastos:`,
    ...top.map((i) => `${CATS[i.c].emoji} ${CATS[i.c].nome}: ${fmt(i.valor)}`),
  ].join("\n");
  if (navigator.share) {
    try { await navigator.share({ title: "Resumo do mês", text: texto }); } catch { /* cancelou */ }
    return;
  }
  window.open("https://wa.me/?text=" + encodeURIComponent(texto), "_blank");
};
$("#btnImportarBackup").onclick = () => $("#inputBackup").click();
$("#inputBackup").addEventListener("change", async (e) => {
  try {
    const dados = JSON.parse(await e.target.files[0].text());
    if (!Array.isArray(dados.transacoes)) throw new Error("formato");
    transacoes = dados.transacoes; metas = dados.metas || {}; fixas = dados.fixas || [];
    regras = dados.regras || {}; cfg = dados.cfg || { renda: 0 };
    cfg.espelhoEm = dados.exportadoEm || new Date().toISOString(); // modo "vendo dados de outra pessoa"
    preparar(); salvarTudo(); render(); irParaAba("inicio");
    toast("✅ Pronto! Agora você está vendo os mesmos dados.");
  } catch { toast("⚠️ Não consegui ler esse arquivo de backup."); }
  e.target.value = "";
});
$("#btnApagarTudo").onclick = () => {
  if (confirm("Tem certeza? Isso apaga TODAS as transações deste aparelho (faça backup antes!).") && confirm("Confirma mesmo?")) {
    ["tx", "metas", "fixas", "regras", "cfg", "mesSel", "seedOk"].forEach((c) => localStorage.removeItem("Bolso." + c));
    location.reload();
  }
};

/* ---------- importar PDF do Mercado Pago (lido no próprio aparelho) ---------- */
let pdfjsOK = null;
function carregarPdfJs() {
  if (pdfjsOK) return pdfjsOK;
  pdfjsOK = new Promise((resolve, reject) => {
    const s = document.createElement("script");
    s.src = "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js";
    s.onload = () => { window.pdfjsLib.GlobalWorkerOptions.workerSrc = "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js"; resolve(); };
    s.onerror = () => reject(new Error("sem internet para carregar o leitor de PDF"));
    document.head.appendChild(s);
  });
  return pdfjsOK;
}

function parsearTextoExtrato(textoBruto) {
  let texto = textoBruto;
  const boilerplate = [
    /EXTRATO DE CONTA/g, /DETALHE DOS MOVIMENTOS/g, /Data\s+Descrição\s+ID da operação\s+Valor\s+Saldo/g,
    /Saldo final: R\$ -?[\d.,]+/g, /Saldo inicial: R\$ -?[\d.,]+/g, /Entradas: R\$ -?[\d.,]+/g, /Saidas: R\$ -?[\d.,]+/g,
    /\b\d+\/\d+\b/g, /Data de geração:[^\n]*/g, /Você tem alguma dúvida\?[\s\S]*?mercadopago\.com\.br/g,
    /CPF\/CNPJ:[^\n]*/g, /Agência:[^\n]*/g, /Conta:[^\n]*/g, /Periodo:[^\n]*/g, /De \d{2}-\d{2}-\d{4} al \d{2}-\d{2}-\d{4}/g,
  ];
  for (const b of boilerplate) texto = texto.replace(b, " ");
  const brl = (s) => parseFloat(s.replace(/\./g, "").replace(",", "."));
  const re = /(\d{2})-(\d{2})-(\d{4})\s+([\s\S]*?)\s+(\d{10,})\s+R\$\s*(-?[\d.]+,\d{2})\s+R\$\s*(-?[\d.]+,\d{2})/g;
  const achadas = [];
  let m, fimAnterior = 0;
  while ((m = re.exec(texto)) !== null) {
    const resto = texto.slice(fimAnterior, m.index).replace(/\s+/g, " ").trim();
    let desc = m[4].replace(/\s+/g, " ").trim();
    if (resto && !/^[\d\s/.-]+$/.test(resto) && resto.length < 80) desc = resto + " " + desc;
    achadas.push({ id: m[5], data: `${m[3]}-${m[2]}-${m[1]}`, descricao: desc, valor: brl(m[6]), saldo: brl(m[7]) });
    fimAnterior = re.lastIndex;
  }
  return achadas;
}

$("#inputPdf").addEventListener("change", async (e) => {
  const arquivos = [...e.target.files];
  if (!arquivos.length) return;
  const st = $("#statusImport");
  st.textContent = "Lendo o PDF no seu aparelho…";
  try {
    await carregarPdfJs();
    let novas = 0, total = 0;
    const chaves = new Set(transacoes.map((t) => `${t.id}|${t.valor}|${(t.descricao || "").slice(0, 20)}`));
    for (const arq of arquivos) {
      const pdf = await window.pdfjsLib.getDocument({ data: await arq.arrayBuffer() }).promise;
      let texto = "";
      for (let p = 1; p <= pdf.numPages; p++) {
        const conteudo = await (await pdf.getPage(p)).getTextContent();
        texto += conteudo.items.map((i) => i.str + (i.hasEOL ? "\n" : " ")).join("") + "\n";
      }
      const achadas = parsearTextoExtrato(texto);
      total += achadas.length;
      for (const t of achadas) {
        const chave = `${t.id}|${t.valor}|${t.descricao.slice(0, 20)}`;
        if (chaves.has(chave)) continue;
        chaves.add(chave);
        t.categoria = categorizar(t.descricao, t.valor); t.origem = "pdf";
        transacoes.push(t); novas++;
      }
    }
    if (!total) { st.textContent = "⚠️ Não encontrei transações nesse PDF. Confira se é o extrato de conta do Mercado Pago."; return; }
    delete cfg.espelhoEm; // quem importa o proprio extrato e o "dono" dos dados
    preparar(); salvarTudo(); render(); irParaAba("inicio");
    st.textContent = "";
    toast(`🎉 Pronto! <strong>${novas} transações novas</strong> importadas${novas < total ? ` (${total - novas} já existiam)` : ""}.`);
  } catch (err) {
    console.error(err);
    st.textContent = "⚠️ Não consegui ler o PDF (" + err.message + "). Dica: a importação precisa de internet só na primeira vez.";
  } finally { e.target.value = ""; }
});


/* ═══════════ FAMÍLIA SINCRONIZADA (nuvem Supabase, opcional) ═══════════
   Modelo simples e honesto: a "chave da família" é um segredo aleatório e
   comprido que Vai no link do convite. Quem tem a chave, acessa — por isso
   o convite deve ser enviado só para a família. No banco, nenhuma linha é
   legível sem apresentar a chave (regra de segurança confere o cabeçalho).
   A chave pública abaixo pode aparecer no código: ela sozinha não lê nada. */
const SUPABASE_URL = "https://srpzthggplnacmpgewcp.supabase.co";
const SUPABASE_CHAVE_PUBLICA = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNycHp0aGdncGxuYWNtcGdld2NwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTIwMjM2NjcsImV4cCI6MjEwNzU5OTY2N30.e7mVm8Y9fzNd_Pg44Bb4pieWApJjh2P8J2V5td7aFsU";

function chaveTx(t) { return `${t.id}|${t.valor}|${t.data}|${semAcento(extrairNome(t.descricao))}`; }
function payloadAtual() { return { transacoes, metas, fixas, regras, renda: cfg.renda || 0, excluidas }; }
function assinaturaEstado(pl) {
  const chaves = (pl.transacoes || []).map((t) => chaveTx(t) + (t.editadoEm || "")).sort().join(";");
  return chaves + "#" + JSON.stringify(pl.metas || {}) + "#" + JSON.stringify(pl.fixas || []) + "#" + JSON.stringify(pl.regras || {}) + "#" + (pl.renda || 0);
}

async function apiSync(metodo, caminho, corpo) {
  const r = await fetch(SUPABASE_URL + "/rest/v1/Bolso_sync" + caminho, {
    method: metodo,
    headers: {
      apikey: SUPABASE_CHAVE_PUBLICA,
      Authorization: "Bearer " + SUPABASE_CHAVE_PUBLICA,
      "Content-Type": "application/json",
      "x-Bolso-key": sync.chave,
      ...(metodo === "GET" ? {} : { Prefer: "return=representation" }),
    },
    body: corpo ? JSON.stringify(corpo) : undefined,
  });
  if (!r.ok) throw new Error("HTTP " + r.status);
  return r.status === 204 ? null : r.json().catch(() => null);
}

/** Junta o que veio da nuvem com o que está neste aparelho (sem duplicar, sem perder). */
function mesclarComRemoto(remoto) {
  const assinaturaAntes = assinaturaEstado(payloadAtual());
  const mapa = new Map(transacoes.map((t) => [chaveTx(t), t]));
  for (const t of remoto.transacoes || []) {
    const k = chaveTx(t);
    const local = mapa.get(k);
    if (!local || (t.editadoEm || 0) > (local.editadoEm || 0)) mapa.set(k, t);
  }
  const lapides = new Map(excluidas.map((e) => [e.chave, e.em]));
  for (const e of remoto.excluidas || []) lapides.set(e.chave, Math.max(lapides.get(e.chave) || 0, e.em));
  excluidas = [...lapides.entries()].map(([chave, em]) => ({ chave, em }));
  // some o que foi apagado em qualquer celular (lápide), a não ser que tenha sido editado depois da exclusão
  transacoes = [...mapa.values()].filter((t) => { const k = chaveTx(t); return !lapides.has(k) || (t.editadoEm || 0) > lapides.get(k); });
  metas = { ...metas, ...(remoto.metas || {}) };
  regras = { ...regras, ...(remoto.regras || {}) };
  const nomesFixas = new Set(fixas.map((f) => semAcento(f.nome)));
  for (const f of remoto.fixas || []) if (!nomesFixas.has(semAcento(f.nome))) fixas.push(f);
  if (Number(remoto.renda) > 0) cfg.renda = Number(remoto.renda);
  delete cfg.espelhoEm;
  preparar();
  return assinaturaEstado(payloadAtual()) !== assinaturaAntes;
}

function agendarEnvio() {
  temPendencia = true; renderSync();
  clearTimeout(timerEnvio);
  timerEnvio = setTimeout(() => sincronizar("auto"), 4000);
}

async function sincronizar(motivo) {
  if (!sync || sincronizando || navigator.onLine === false) return;
  sincronizando = true; renderSync();
  try {
    const linhas = await apiSync("GET", `?household_key=eq.${encodeURIComponent(sync.chave)}&select=payload,versao,atualizado_por`);
    const remoto = linhas?.[0] || null;
    let mudouAqui = false;
    if (remoto && remoto.versao !== sync.versao) {
      mudouAqui = mesclarComRemoto(remoto.payload || {});
      sync.versao = remoto.versao;
      if (mudouAqui && motivo !== "criar" && motivo !== "entrar") toast(`🔄 Chegaram novidades${remoto.atualizado_por ? " de <strong>" + esc(remoto.atualizado_por) + "</strong>" : ""}!`);
    }
    const precisoEnviar = !remoto || assinaturaEstado(payloadAtual()) !== assinaturaEstado(remoto.payload || {});
    if (precisoEnviar) {
      const corpo = { household_key: sync.chave, payload: payloadAtual(), versao: (remoto?.versao || 0) + 1, atualizado_por: sync.meuNome || "", updated_at: new Date().toISOString() };
      if (!remoto) {
        const criadas = await apiSync("POST", "", corpo);
        sync.versao = criadas?.[0]?.versao || 1;
      } else {
        const atualizadas = await apiSync("PATCH", `?household_key=eq.${encodeURIComponent(sync.chave)}&versao=eq.${remoto.versao}`, corpo);
        if (!atualizadas?.length) { sincronizando = false; return sincronizar(motivo); } // outro celular enviou junto: junta e tenta de novo
        sync.versao = atualizadas[0].versao;
      }
    }
    temPendencia = false; ultimoErroSync = "";
    sync.ultimaSync = Date.now();
    salvar("sync", sync);
    aplicandoRemoto = true; salvarTudo(); aplicandoRemoto = false;
    render();
    if (motivo === "manual") toast("✅ Tudo sincronizado com a família!");
  } catch (e) {
    ultimoErroSync = e.message || "sem internet";
    renderSync();
    if (motivo === "manual" || motivo === "criar" || motivo === "entrar") toast("⚠️ Não consegui sincronizar agora (" + esc(ultimoErroSync) + "). Confira a internet e tente 🔄.");
  } finally {
    sincronizando = false; renderSync();
  }
}

function renderSync() {
  const dot = $("#btnSyncTopo"), desc = $("#syncDesconectado"), conn = $("#syncConectado"), txt = $("#syncStatusTexto");
  if (!dot || !desc || !conn) return;
  if (!sync) { dot.hidden = true; desc.hidden = false; conn.hidden = true; return; }
  dot.hidden = false; desc.hidden = true; conn.hidden = false;
  const estado = ultimoErroSync ? "erro" : sincronizando ? "pensando" : "";
  dot.className = "sync-topo " + estado;
  dot.textContent = ultimoErroSync ? "☁️⚠️ família" : sincronizando ? "☁️… família" : "☁️ família ✓";
  const quando = sync.ultimaSync ? new Date(sync.ultimaSync).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" }) : "ainda não";
  txt.innerHTML = ultimoErroSync
    ? `⚠️ Sem sincronizar (${esc(ultimoErroSync)}). Seus lançamentos ficam salvos aqui e sobem quando a internet voltar.`
    : `☁️ Conectado como <strong>${esc(sync.meuNome || "você")}</strong> · última sincronização às ${quando}${temPendencia ? " · <em>enviando…</em>" : ""}`;
}

function gerarChaveFamilia() {
  const b = new Uint8Array(24); crypto.getRandomValues(b);
  return [...b].map((x) => x.toString(16).padStart(2, "0")).join("");
}
function extrairChaveConvite(texto) {
  const m = String(texto || "").match(/#familia=([A-Za-z0-9]{20,})/) || String(texto || "").trim().match(/^([a-f0-9]{40,})$/i);
  return m ? m[1] : null;
}
async function enviarConvite() {
  const link = location.origin + location.pathname + "#familia=" + sync.chave;
  const texto = "Oi! 💑 Com este link você entra no nosso app de gastos (Bolso em Dia) e vê tudo atualizado comigo. É segredo nosso, não repasse. 🐷";
  if (navigator.share) {
    try { await navigator.share({ title: "Bolso em Dia — nossa família", text: texto + "\n" + link }); return; } catch { return; }
  }
  try { await navigator.clipboard.writeText(texto + "\n" + link); toast("💌 Convite copiado! Cole no WhatsApp <strong>só dela</strong>."); }
  catch { prompt("Copie o convite e envie só para sua família:", texto + "\n" + link); }
}

function abrirCriarFamilia() {
  abrirSheet(`
    <h3>🔗 Criar nossa família</h3>
    <p>Vou criar uma chave-secreta e enviar seus dados atuais para a nuvem da família. Depois basta mandar o convite para sua esposa.</p>
    <label>Como você quer aparecer nos lançamentos?</label>
    <input type="text" id="syncNome" placeholder="Ex.: Douglas" value="${esc(sync?.meuNome || "Douglas")}">
    <button class="btn primario grande" id="btnConfirmarCriar" style="margin-top:14px">Criar e preparar convite</button>
    <button class="btn texto" id="btnCancelarSync">Cancelar</button>`);
  $("#btnCancelarSync").onclick = fecharSheet;
  $("#btnConfirmarCriar").onclick = async () => {
    const nome = $("#syncNome").value.trim() || "Eu";
    fecharSheet();
    sync = { chave: gerarChaveFamilia(), meuNome: nome, versao: 0 };
    salvar("sync", sync); delete cfg.espelhoEm; renderSync();
    toast("☁️ Criando a família e enviando seus dados…");
    await sincronizar("criar");
    if (!ultimoErroSync) { toast("🎉 Família criada! Agora envie o convite."); enviarConvite(); }
  };
}

function abrirEntrarFamilia(chavePre) {
  abrirSheet(`
    <h3>🔑 Entrar na família</h3>
    <p>${chavePre ? "Você abriu um convite! 🎉" : "Cole o convite que você recebeu."} Vou Baixar os dados da família para este celular (e juntar com o que já houver aqui, sem apagar nada).</p>
    ${chavePre ? "" : `<label>Convite (link ou código)</label><input type="text" id="syncConvite" placeholder="Cole aqui o link do convite">`}
    <label>Como você quer aparecer nos lançamentos?</label>
    <input type="text" id="syncNomeEntrar" placeholder="Seu primeiro nome">
    <button class="btn primario grande" id="btnConfirmarEntrar" style="margin-top:14px">Entrar e sincronizar</button>
    <button class="btn texto" id="btnCancelarEntrar">Agora não</button>`);
  $("#btnCancelarEntrar").onclick = fecharSheet;
  $("#btnConfirmarEntrar").onclick = async () => {
    const chave = chavePre || extrairChaveConvite($("#syncConvite")?.value);
    const nome = $("#syncNomeEntrar").value.trim() || "Família";
    if (!chave) { toast("⚠️ Não reconheci esse convite. Confira se colou o link inteiro."); return; }
    fecharSheet();
    sync = { chave, meuNome: nome, versao: 0 };
    salvar("sync", sync); delete cfg.espelhoEm; renderSync();
    toast("☁️ Baixando os dados da família…");
    await sincronizar("entrar");
    if (!ultimoErroSync) { irParaAba("inicio"); toast(`🎉 Pronto, ${esc(nome)}! Você está vendo os gastos da família, atualizados.`); }
  };
}

$("#btnCriarFamilia").onclick = abrirCriarFamilia;
$("#btnEntrarFamilia").onclick = () => abrirEntrarFamilia(null);
$("#btnConvidar").onclick = enviarConvite;
$("#btnSincronizarAgora").onclick = () => sincronizar("manual");
$("#btnSyncTopo").onclick = () => sincronizar("manual");
$("#btnDesconectarSync").onclick = () => {
  if (confirm("Desconectar ESTE aparelho da família? Os dados continuam aqui e na nuvem, só param de atualizar sozinhos.")) {
    sync = null; localStorage.removeItem("Bolso.sync"); temPendencia = false; renderSync();
    toast("Desconectado. Seus dados continuam neste celular.");
  }
};
setInterval(() => { if (sync && document.visibilityState === "visible") sincronizar("poll"); }, 60000);
document.addEventListener("visibilitychange", () => { if (sync && document.visibilityState === "visible") sincronizar("poll"); });
window.addEventListener("online", () => { if (sync) sincronizar("poll"); });

/* ---------- início ---------- */
function preparar() {
  transacoes.forEach((t, i) => { t._uid = t._uid || "u" + i + "-" + String(t.id); t.categoria = t.categoria || categorizar(t.descricao, t.valor); });
  transacoes.sort((a, b) => a.data.localeCompare(b.data));
  const meses = mesesDisponiveis();
  if (!mesSel || !meses.includes(mesSel)) {
    // mês mais recente COM dados (ou o atual)
    mesSel = [...new Set(transacoes.map((t) => mesDe(t.data)))].sort().pop() || meses[meses.length - 1];
  }
}

async function iniciar() {
  preparar();
  // Na prévia/demonstração pode existir um arquivo local com os dados já importados.
  // Ele NUNCA Vai para internet/GitHub (está no .gitignore) — o uso normal é importar o PDF aqui no aparelho.
  if (!transacoes.length && !localStorage.getItem("Bolso.seedOk")) {
    try {
      const r = await fetch("dados-pessoais.json", { cache: "no-store" });
      if (r.ok) {
        const dados = await r.json();
        if (Array.isArray(dados) && dados.length) {
          transacoes = dados; preparar(); salvarTudo();
          setTimeout(() => toast("👋 Importei seus extratos de <strong>setembro e outubro</strong> para você já começar vendo tudo!"), 600);
        }
      }
    } catch { /* sem seed: tela de boas-vindas com o botão de importar */ }
    localStorage.setItem("Bolso.seedOk", "1");
  }
  salvarTudo();
  render();
  const chaveConvite = extrairChaveConvite(location.hash);
  if (location.hash) history.replaceState(null, "", location.pathname + location.search); // tira a chave da barra de endereço
  if (chaveConvite && sync?.chave !== chaveConvite) setTimeout(() => abrirEntrarFamilia(chaveConvite), 500);
  else if (sync) sincronizar("inicio");
  navigator.serviceWorker?.register("sw.js").catch(() => {});
}

iniciar();
