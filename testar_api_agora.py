#!/usr/bin/env python3
"""Testa o webhook local — executa: python testar_api_agora.py"""

import requests
import json
from datetime import datetime

URL = "http://localhost:5005/api/webhook/zapi"

def testar(nome, texto):
    print(f"\n🧪 {nome}")
    payload = {
        "phone": "5584991627655",
        "messageId": f"TST_{datetime.now().strftime('%H%M%S%f')}",
        "text": texto,
        "fromMe": False,
        "senderName": "Murilo"
    }
    r = requests.post(URL, json=payload, timeout=30)
    data = r.json()
    
    intent = data.get("intencao", "?")
    resposta = data.get("resposta_texto", "") or "(sem resposta)"
    print(f"   📥 \"{texto}\"")
    print(f"   🤖 Intenção: {intent}")
    print(f"   💬 Resposta: {resposta[:200]}")
    print(f"   📡 Status HTTP: {r.status_code}")
    return data

print("=" * 60)
print("🔥 TESTE DO WEBHOOK LOCAL 🔥")
print("=" * 60)

# Teste 1: Saudação
testar("Saudação", "Oi, tudo bem?")

# Teste 2: Pedido de 2ª via
testar("Pedido 2ª via", "Manda a 2ª via do boleto")

# Teste 3: Já paguei
testar("Confirmação pagamento", "Já paguei o boleto hoje")

# Teste 4: Promessa
testar("Promessa pagamento", "Vou pagar amanhã")

# Teste 5: Acordo
testar("Pedido acordo", "Quero parcelar")

# Teste 6: Reclamação
testar("Reclamação", "Isso é engano, não devo nada")

# Teste 7: Desconhecida
testar("Mensagem aleatória", "Blablabla teste 123")

print("\n" + "=" * 60)
print("✅ TODOS OS TESTES CONCLUÍDOS!")
print("=" * 60)
