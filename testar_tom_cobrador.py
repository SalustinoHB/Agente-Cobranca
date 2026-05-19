"""Testa o novo tom de cobrador"""
import requests, json, time

API = "http://localhost:5005/api/webhook/zapi"
N = "55849999998888"

def t(texto, mid):
    uid = str(int(time.time() * 1000))[-6:]
    r = requests.post(API, json={"phone":N,"messageId":"COB"+str(mid)+uid,"text":texto,"fromMe":False,"senderName":"C"}, timeout=30).json()
    resp = r.get("resposta_texto")
    if not resp:
        resp = "(vazia - erro: " + str(r.get("erro", "?")) + ")"
    print(f"📥 {texto}")
    print(f"   💬 {resp[:200]}")
    print()
    print(f"   💬 {resp[:200]}")
    print()

print("="*50)
print("🔥 TOM DE COBRADOR")
print("="*50)
print()

t("Oi, tudo bem?", 1)
t("Já paguei o boleto", 2)
t("Vou pagar amanhã", 3)
t("Manda a 2ª via", 4)
t("Quero parcelar", 5)
t("Não devo nada", 6)

print("✅ Tom de cobrador ativo!")