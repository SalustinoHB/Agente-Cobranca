import requests, json, time

API = "http://localhost:5005/api/webhook/zapi"

testes = [
    ("Saudação", "Oi, tudo bem?"),
    ("Já paguei", "Já paguei o boleto"),
    ("Vou pagar", "Vou pagar amanhã"),
    ("2ª via", "Manda a 2ª via do boleto"),
    ("Acordo", "Quero parcelar"),
    ("Reclamação", "Isso é engano"),
    ("Aleatório", "Teste aleatório 123"),
]

for i, (nome, texto) in enumerate(testes, 1):
    r = requests.post(API, json={
        "phone": "5584991627655",
        "messageId": f"TESTE_FINAL_{i}",
        "text": texto,
        "fromMe": False,
        "senderName": "Murilo"
    }, timeout=30)
    d = r.json()
    status = "✅" if d.get("respondido") else "❌"
    intent = d.get("intencao") or "?"
    resp = d.get("resposta_texto") or "(vazia)"
    print(f"{status} {nome:<20} → [{intent}] {resp[:120]}")

print("\n🔥 TODOS OS TESTES CONCLUÍDOS!")
