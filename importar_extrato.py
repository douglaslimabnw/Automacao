#!/usr/bin/env python3
"""
Importador de extrato do Mercado Pago (PDF) -> JSON

Uso:
    pip install pymupdf
    python3 importar_extrato.py extrato.pdf [outro.pdf ...] > transacoes.json

Gera uma lista de transacoes no formato usado pelo app "Bolso em Dia":
    {"id": "...", "data": "2026-09-01", "descricao": "...", "valor": -60.45}

Tudo roda localmente: nenhum dado sai da sua maquina.
"""
import json
import re
import sys

import pymupdf

# Linhas de cabecalho/rodape que aparecem em toda pagina e nao sao transacoes
BOILERPLATE = [
    r"EXTRATO DE CONTA",
    r"DETALHE DOS MOVIMENTOS",
    r"Data\s+Descrição\s+ID da operação\s+Valor\s+Saldo",
    r"^\s*Data\s*$",
    r"^\s*Descrição\s*$",
    r"^\s*ID da operação\s*$",
    r"^\s*Valor\s*$",
    r"^\s*Saldo\s*$",
    r"Saldo final: R\$ -?[\d.,]+",
    r"Saldo inicial: R\$ -?[\d.,]+",
    r"Entradas: R\$ -?[\d.,]+",
    r"Saidas: R\$ -?[\d.,]+",
    r"^\s*\d+/\d+\s*$",                       # numero da pagina "3/10"
    r"Data de geração:.*",
    r"Você tem alguma dúvida\?.*",
    r"Mercado Pago Instituição.*",
    r"nosso SAC, ligue.*",
    r"da ouvidoria, ligue.*",
    r"Encontre nossos canais.*",
    r"Douglas Roberto Nunes de Lima",
    r"CPF/CNPJ:.*",
    r"Agência:.*",
    r"Conta:.*",
    r"Periodo:.*",
    r"De \d{2}-\d{2}-\d{4} al \d{2}-\d{2}-\d{4}",
    r"^\s*54917874435\s*$",
    r"^\s*1\s*$",
]

ROW_RE = re.compile(
    r"(\d{2})-(\d{2})-(\d{4})\s+(.*?)\s+(\d{10,})\s+R\$\s*(-?[\d.]+,\d{2})\s+R\$\s*(-?[\d.]+,\d{2})",
    re.DOTALL,
)


def limpar(texto: str) -> str:
    for padrao in BOILERPLATE:
        texto = re.sub(padrao, " ", texto, flags=re.MULTILINE)
    return texto


def brl(s: str) -> float:
    return float(s.replace(".", "").replace(",", "."))


def extrair(caminho: str):
    doc = pymupdf.open(caminho)
    texto = "\n".join(pagina.get_text() for pagina in doc)
    texto = limpar(texto)

    transacoes = []
    fim_anterior = 0
    for m in ROW_RE.finditer(texto):
        # Texto solto entre a transacao anterior e esta pode ser o comeco
        # da descricao (quando a linha quebra na virada da pagina).
        resto = " ".join(texto[fim_anterior:m.start()].split())
        desc = " ".join(m.group(4).split())
        if resto and not re.fullmatch(r"[\d\s/.-]+", resto):
            desc = f"{resto} {desc}"
        dia, mes, ano = m.group(1), m.group(2), m.group(3)
        transacoes.append({
            "id": m.group(5),
            "data": f"{ano}-{mes}-{dia}",
            "descricao": desc,
            "valor": brl(m.group(6)),
            "saldo": brl(m.group(7)),
        })
        fim_anterior = m.end()
    return transacoes


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    todas = []
    vistas = set()
    for caminho in sys.argv[1:]:
        for t in extrair(caminho):
            chave = (t["id"], t["valor"], t["descricao"][:20])
            if chave not in vistas:
                vistas.add(chave)
                todas.append(t)
    todas.sort(key=lambda t: t["data"])
    print(json.dumps(todas, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
