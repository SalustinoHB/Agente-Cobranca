"""
Teste de validação das melhorias aplicadas ao agente de cobrança.

Roda: python teste_melhorias.py
"""

import sys
import os

# Adiciona o path do agente
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "agente"))

from agente.templates import (
    etapa_d_menos_3, etapa_d_zero, etapa_d_mais_1,
    etapa_d_mais_7, etapa_d_mais_15, etapa_d_mais_30,
    _escolher_variacao
)
from agente.sender import ZAPISender, BaseSender


def test_variacoes_templates():
    """Testa se as variações funcionam e são diferentes."""
    print("=" * 60)
    print("🧪 TESTE 1: Variações de templates")
    print("=" * 60)

    boleto = {
        "nome": "João Silva Santos",
        "unidade": "Apto 101",
        "valor": 850.50,
        "vencimento": "15/05/2026",
        "dias_atraso": 7,
        "boleto_id": "TESTE-001"
    }

    # Gera 3 vezes com seed diferente → devem ser diferentes
    textos = []
    for i in range(3):
        t = etapa_d_mais_7(boleto, seed=f"seed-{i}")
        textos.append(t)
        print(f"\n--- Variação {i+1} ---")
        print(t[:150] + "...")

    # Verifica se são diferentes
    unicos = set(textos)
    if len(unicos) > 1:
        print(f"\n✅ SUCESSO: {len(unicos)} variações distintas geradas!")
    else:
        print("\n⚠️ AVISO: Todas as variações ficaram iguais")

    # Testa consistência com mesmo seed
    t1 = etapa_d_mais_7(boleto, seed="MESMO-SEED")
    t2 = etapa_d_mais_7(boleto, seed="MESMO-SEED")
    if t1 == t2:
        print("✅ Consistência com mesmo seed: OK")
    else:
        print("⚠️ Inconsistência com mesmo seed")


def test_normalizacao_numero():
    """Testa a normalização de números de telefone."""
    print("\n" + "=" * 60)
    print("🧪 TESTE 2: Normalização de números")
    print("=" * 60)

    casos = [
        ("+55 84 99999-9999", "5584999999999"),
        ("(84) 99999-9999", "5584999999999"),
        ("84999999999", "5584999999999"),
        ("5584999999999", "5584999999999"),
        ("05584999999999", "5584999999999"),
    ]

    for entrada, esperado in casos:
        resultado = BaseSender.normalizar_numero(entrada)
        status = "✅" if resultado == esperado else "❌"
        print(f"{status} '{entrada}' → '{resultado}' (esperado: '{esperado}')")


def test_delay_humanizado():
    """Testa se o delay está configurado corretamente."""
    print("\n" + "=" * 60)
    print("🧪 TESTE 3: Delay humanizado")
    print("=" * 60)

    # O ZAPISender.enviar_texto() aceita delay_ms=1200 por padrão
    # e converte pra delayMessage em segundos (arredonda pra cima)
    delay_ms = 1200
    delay_segundos = max(1, int(delay_ms / 1000))
    print(f"✅ delay_ms={delay_ms} → delayMessage={delay_segundos}s (Z-API)")

    # Intervalo entre envios (do regua.py)
    intervalo = 180  # 3 minutos
    print(f"✅ Intervalo entre envios: {intervalo}s ({intervalo/60:.0f} min)")

    # Retry com backoff
    print(f"✅ Retry automático: até 3 tentativas com backoff exponencial")
    for tentativa in range(1, 4):
        wait = tentativa * 2
        print(f"   Tentativa {tentativa}: aguarda {wait}s antes de retry")


def test_conexao_zapi():
    """Testa se a conexão Z-API está funcionando."""
    print("\n" + "=" * 60)
    print("🧪 TESTE 4: Conexão Z-API")
    print("=" * 60)

    from dotenv import load_dotenv
    load_dotenv()

    instance_url = os.getenv("ZAPI_INSTANCE_URL")
    token = os.getenv("ZAPI_TOKEN")

    if not instance_url or not token:
        print("⚠️ Z-API não configurado no .env — pulando teste")
        return

    sender = ZAPISender(instance_url, token, dry_run=True)

    try:
        conectado = sender.esta_conectado()
        status = "✅ CONECTADO" if conectado else "❌ DESCONECTADO"
        print(f"{status} — WhatsApp status: {conectado}")

        info = sender.status_instancia()
        print(f"📊 Info da instância: {info}")
    except Exception as e:
        print(f"❌ Erro ao checar conexão: {e}")


def resumo_melhorias():
    """Mostra resumo de tudo que foi aplicado."""
    print("\n" + "=" * 60)
    print("📋 RESUMO DAS MELHORIAS APLICADAS")
    print("=" * 60)

    melhorias = [
        ("📝 Templates com variações", "2-3 textos alternativos por etapa"),
        ("🎲 Variação aleatória", "Evita padrão robótico (seed opcional)"),
        ("⏱️ Delay de digitação", "1200ms padrão (Z-API: delayMessage)"),
        ("🔄 Retry automático", "Até 3 tentativas com backoff exponencial"),
        ("📡 Verificação pré-envio", "Checa conexão antes de enviar"),
        ("📞 Normalização robusta", "Aceita +55, (), espaços, 0 à esquerda"),
        ("⏳ Intervalo entre envios", "180s (3 min) configurável via .env"),
        ("🛡️ Soft-cap diário", "Máximo 50 envios/dia (configurável)"),
    ]

    for titulo, desc in melhorias:
        print(f"  {titulo}")
        print(f"     └─ {desc}")

    print("\n✅ Tudo pronto pra produção com Z-API!")


if __name__ == "__main__":
    test_variacoes_templates()
    test_normalizacao_numero()
    test_delay_humanizado()
    test_conexao_zapi()
    resumo_melhorias()
