"""
Teste local do webhook — simula payload do Z-API.

Roda: python teste_webhook_local.py
"""

import requests
import json
from datetime import datetime

# URL do webhook (local ou AWS)
WEBHOOK_URL = "http://localhost:5000/api/webhook/zapi"
# WEBHOOK_URL = "http://15.228.231.24:5000/api/webhook/zapi"  # AWS

# Payload simulado do Z-API (quando alguém envia mensagem)
payload = {
    "phone": "5584991627655",
    "messageId": "TESTE_" + datetime.now().strftime("%H%M%S"),
    "text": "Oi, já paguei o boleto",
    "fromMe": False,
    "isGroup": False,
    "senderName": "Murilo",
    "timestamp": int(datetime.now().timestamp() * 1000),
}

print("=" * 60)
print("🧪 TESTE DE WEBHOOK — Simulando mensagem recebida do Z-API")
print("=" * 60)
print(f"\nURL: {WEBHOOK_URL}")
print(f"Payload:")
print(json.dumps(payload, indent=2, ensure_ascii=False))

try:
    response = requests.post(
        WEBHOOK_URL,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=30,
    )
    print(f"\n📡 Resposta: HTTP {response.status_code}")
    try:
        data = response.json()
        print(json.dumps(data, indent=2, ensure_ascii=False))
    except:
        print(response.text[:500])
except Exception as e:
    print(f"\n❌ Erro: {e}")
    print("\n💡 Dica: Certifique-se de que a API está rodando:")
    print("   uvicorn agente.api:app --host 0.0.0.0 --port 5000")
