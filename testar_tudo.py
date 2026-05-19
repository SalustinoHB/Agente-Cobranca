#!/usr/bin/env python3
"""Testa todas as intenções do webhook local - python testar_tudo.py"""

import requests
import json

API = "http://localhost:5005/api/webhook/zapi"

testes = [
    ("👋 Saudação", "Oi, tudo bem?"),
    ("💰 Já paguei", "Já paguei o boleto hoje"),
    ("📅 Vou pagar", "Vou pagar amanhã"),
    ("📄 2ª via", "Manda a 2ª via do boleto"),
    ("🤝 Acordo", "Quero parcelar"),
    ("😠 Reclamação", "Isso é engano, não devo nada"),
    ("❓ Aleatório", "Teste aleatório 123"),
]

for nome, texto in testes:
    r = requests.post(API, json={
        "phone": "5584991627655",
        "messageId": f"T_{texto[:8].replace(' ','_')}",
        "text": texto,
        "fromMe": False,
        "senderName": "Murilo"
    }, timeout=30)
    d = r.json()
    status = "✅" if d.get("respondido") else "❌"
    intent = str(d.get("intencao", "?") or "?")
    resp = str(d.get("resposta_texto", "") or "(vazia)")
    print(f"{status} {nome:<20} intent={intent:<25} → {resp[:120]}")

print("\n🔥 TODOS OS TESTES CONCLUÍDOS!")
