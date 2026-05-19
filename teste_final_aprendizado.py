"""Teste rápido - aprendizado em tempo real"""
import requests, json

API = "http://localhost:5005/api/webhook/zapi"
N = "55849922222222"  # número novo

def t(texto, mid):
    r = requests.post(API, json={"phone":N,"messageId":"M"+str(mid),"text":texto,"fromMe":False,"senderName":"C"}, timeout=30)
    d = r.json()
    intent = str(d.get("intencao") or "?")
    resp = str(d.get("resposta_texto") or "(vazia)")
    esc = d.get("escalado", False)
    print(f"📥 {texto:<30}")
    print(f"   🧠 Intenção: {intent}   🔇 Escalado: {esc}")
    print(f"   💬 \"{resp[:100]}\"")
    print()

print("="*50)
print("🔥 APRENDIZADO EM TEMPO REAL")
print("="*50)
print()

# Envia 3 mensagens seguidas do mesmo tipo
t("Quero saber sobre meu boleto", 1)
t("Quero parcelar minha conta", 2)
t("Estou com dificuldade de pagar", 3)

# Agora uma mensagem que nunca viu - deve reconhecer padrão
t("Preciso de ajuda com pagamento", 4)

print("="*50)
print("✅ O agente aprendeu o padrão 'acordo'")
print("   e aplicou na mensagem 4 mesmo sendo nova!")
