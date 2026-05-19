import requests, json

r = requests.post("http://localhost:5005/api/webhook/zapi", json={
    "phone": "5584991627655",
    "messageId": "TESTE1",
    "text": "Oi, tudo bem?",
    "fromMe": False,
    "senderName": "Murilo"
}, timeout=30)

print(json.dumps(r.json(), indent=2, ensure_ascii=False, default=str))
