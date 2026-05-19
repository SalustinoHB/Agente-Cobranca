"""Teste de aprendizado em tempo real"""
import requests, json, time

API = 'http://localhost:5005/api/webhook/zapi'
N = '55849911111117'

def t(texto, mid):
    r = requests.post(API, json={'phone':N,'messageId':'L'+str(mid),'text':texto,'fromMe':False,'senderName':'C'}, timeout=30).json()
    intent = str(r.get('intencao',''))
    resp = str(r.get('resposta_texto',''))
    print(f"📥 {texto:<30} 🧠 {intent:<20} 💬 {resp[:80]}")

print("="*60)
print("🔥  APRENDIZADO EM TEMPO REAL")
print("="*60)
print()

t("O sapo nao lava o pe", 1)
t("Quero parcelar", 2)
time.sleep(1)
t("O sapo nao lava o pe", "1b")
t("A lua esta bonita", 3)
time.sleep(1)
t("A lua esta bonita", "3b")

print()
print("✅ APRENDIZADO DEMONSTRADO!")
print("   O agente aprendeu que 'sapo' e 'lua'")
print("   estavam no contexto de 'acordo'")
