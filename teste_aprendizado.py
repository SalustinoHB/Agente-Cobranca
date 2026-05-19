"""Teste de aprendizado em tempo real"""
import requests, json, time

API = 'http://localhost:5005/api/webhook/zapi'
NUM = '5584991627655'

def enviar(texto, msg_id):
    r = requests.post(API, json={
        'phone': NUM,
        'messageId': 'APR_' + str(msg_id),
        'text': texto,
        'fromMe': False,
        'senderName': 'Murilo'
    }, timeout=30)
    d = r.json()
    intent = d.get('intencao','?')
    resp = str(d.get('resposta_texto',''))[:130]
    print(f'📥 "{texto}"')
    print(f'   🧠 Intenção: {intent}')
    print(f'   💬 Resposta: {resp}')
    print()
    return d

print('=' * 55)
print('🔥  TESTE DE APRENDIZADO EM TEMPO REAL')
print('=' * 55)
print()

print('--- [1] Mensagem aleatória (não entende) ---')
enviar('O sapo não lava o pé', 1)

print('--- [2] Mensagem que entende ---')
enviar('Quero parcelar minha dívida', 2)

print('--- [3] Mesma frase aleatória de NOVO (aprendeu!) ---')
time.sleep(1)
enviar('O sapo não lava o pé', '1b')

print('--- [4] Mensagem NOVA aleatória ---')
enviar('A lua está bonita hoje', 3)

print('--- [5] Repete a NOVA ---')
time.sleep(1)
enviar('A lua está bonita hoje', '3b')

print('✅ APRENDIZADO DEMONSTRADO!')
