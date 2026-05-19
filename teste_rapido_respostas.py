"""
Teste RÁPIDO do classificador e gerador de respostas.
Roda sem servidor web — testa a lógica pura.

Uso: python3 teste_rapido_respostas.py
(ou: python teste_rapido_respostas.py)
"""

import sys
import os

# Adiciona o caminho do agente
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "agente"))

from agente import respostas as respostas_v2

# Frases de teste
testes = [
    "Oi, tudo bem?",
    "Já paguei o boleto",
    "Vou pagar amanhã",
    "Pode mandar a 2ª via?",
    "Tem como parcelar?",
    "Não devo nada, isso é engano",
    "Bom dia!",
    "Quero fazer um acordo",
    "Mandei o comprovante",
    "Quanto é o boleto?",
]

contexto_fake = {
    "nome": "João Silva",
    "unidade": "Apto 101",
    "valor": 850.50,
    "vencimento": "15/05/2026",
    "dias_atraso": 7,
    "pix_chave": "chave-pix-renaissance",
    "link_boleto": "https://boleto.renaissance.com/123",
}

print("=" * 60)
print("🧪 TESTE RÁPIDO - Classificador de Respostas")
print("=" * 60)

for i, frase in enumerate(testes, 1):
    intent = respostas_v2.classificar(frase)
    resposta = respostas_v2.gerar_resposta(intent, contexto_fake, ja_falou_hoje=False)
    
    print(f"\n[{i}] {frase}")
    print(f"    ├─ Intenção: {intent}")
    print(f"    ├─ Resposta: {resposta['texto'][:100]}...")
    print(f"    └─ Escalar: {'SIM' if resposta['escalar_humano'] else 'NÃO'} | Delay: {resposta['delay_segundos']}s")

print()
print("=" * 60)
print("✅ Teste concluído!")
print("=" * 60)
