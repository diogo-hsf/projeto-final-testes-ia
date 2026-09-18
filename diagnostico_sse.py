"""Despeja o stream SSE bruto de UMA pergunta.

Serviu para responder uma questão que decidiu a análise de F-01: o servidor
manda um evento de dados ou vários? Se fossem vários, o envelope JSON que
aparece no campo `message` seria bug do nosso cliente, que pegaria só o
primeiro pedaço. O resultado de 18/09 foi **um único** evento `data:` com
`message`, conforme o formato documentado no guia — ou seja, o defeito é do
sistema, não da suíte.

Gasta 1 chamada. Uso:

    $env:AURA_USUARIO = "grupo03"
    $env:AURA_SENHA = "..."
    python diagnostico_sse.py
"""
import json
import os

import requests

BASE = "https://assistente-financeiro-testes.onrender.com"
TIMEOUT = 180
PERGUNTA = ("Moro em São Paulo capital e tenho renda de R$ 3.500. "
            "Quais critérios vão avaliar no meu pedido?")

r = requests.post(
    f"{BASE}/auth/login",
    json={"username": os.environ["AURA_USUARIO"], "password": os.environ["AURA_SENHA"]},
    timeout=TIMEOUT,
)
r.raise_for_status()
token = r.json()["access_token"]

r = requests.post(
    f"{BASE}/chat",
    json={"message": PERGUNTA, "history": []},
    headers={"Authorization": f"Bearer {token}"},
    stream=True,
    timeout=TIMEOUT,
)
r.raise_for_status()

print("=" * 70)
print("LINHAS BRUTAS DO STREAM")
print("=" * 70)

eventos = com_message = 0
for n, linha in enumerate(r.iter_lines(decode_unicode=True), 1):
    if linha is None:
        continue
    print(f"[linha {n:03d}] len={len(linha):5d} | {linha[:160]}")
    if not linha.startswith("data:"):
        continue
    eventos += 1
    try:
        dados = json.loads(linha[5:].strip())
    except json.JSONDecodeError as erro:
        print(f"           ^^ JSON inválido: {erro}")
        continue
    if "message" in dados:
        com_message += 1
        print(f"           ^^ tem 'message', len={len(dados['message'])}, "
              f"chaves={sorted(dados)}")

print("=" * 70)
print(f"eventos 'data:' = {eventos} | eventos com 'message' = {com_message}")
print("=" * 70)
