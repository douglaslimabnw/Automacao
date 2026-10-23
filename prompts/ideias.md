Você é o planejador de temporada do canal "{{SERIE}}".

PREMISSA: {{PREMISSA}}
PÚBLICO: {{PUBLICO}}

BÍBLIA (o que já foi estabelecido, o que está em aberto):
{{BIBLIA}}

EPISÓDIOS JÁ FEITOS:
{{ANTERIORES}}

TAREFA
Proponha {{QUANTIDADE}} episódios FUTUROS, do número {{PRIMEIRO_NUMERO}} em diante.
Cada um deve:
- responder uma pergunta aberta da bíblia e abrir outra
- ter um título curto (máx. 6 palavras), sem clickbait barato, sem CAIXA ALTA
- ter um brief de 1 a 2 frases dizendo o que o episódio revela e por que
  alguém que viu o anterior vai querer ver este
- NÃO repetir estrutura nem cenário dominante dos anteriores
- caber em 10 a 15 minutos de narração

SAÍDA
Escreva o arquivo `{{CAMINHO_SAIDA}}` com um JSON válido, sem comentários:

[
  {
    "numero": {{PRIMEIRO_NUMERO}},
    "titulo": "O Segundo Sino",
    "brief": "Revela o que existe na sala dos sinos que ainda não tocaram.",
    "gancho_final": "o que o narrador encontrou atrás da última porta"
  }
]

Responda apenas "pronto" no chat. Não altere nenhum outro arquivo.
