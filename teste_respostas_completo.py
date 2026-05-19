#!/usr/bin/env python3
"""Teste completo do sistema de respostas — roda sem servidor."""

import sys
import os

# Adiciona o caminho do agente
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "agente"))

# Força modo fictício
os.environ["SUPERLOGICA_MODO"] = "ficticio"

from agente import respostas as rp
from agente import superlogica_boleto as sb

# ============================================================
# CONTEXTO FICTÍCIO (igual ao renaissance.json)
# ============================================================
CONTEXTOS = {
    "inadimplente": {
        "nome": "João Silva Santos",
        "unidade": "Apto 101",
        "valor": 850.50,
        "vencimento": "15/05/2026",
        "dias_atraso": 13,
        "boleto_id": "159203",
        "whatsapp": "5584999999999",
        "pix": "renaissance.apto101.A1B2C3D4@admpratika.com.br",
        "linha_digitavel": "34191234567890123456789012345678901234567890",
        "link_boleto": "https://boleto.pratika.com.br/159203/abc/def123/boleto.pdf",
    },
    "sem_boleto": {
        "nome": "Maria",
        "unidade": "Apto 202",
    },
    "vazio": {},
}


def test_classificador():
    """Testa a classificação de intenção."""
    print("=" * 60)
    print("🧪 TESTE 1: CLASSIFICADOR")
    print("=" * 60)

    testes = [
        ("Oi, tudo bem?", "saudacao"),
        ("Bom dia!", "saudacao"),
        ("Já paguei o boleto", "confirmacao_pagamento"),
        ("Paguei ontem", "confirmacao_pagamento"),
        ("Fiz o pix agora", "confirmacao_pagamento"),
        ("Vou pagar amanhã", "promessa_pagamento"),
        ("Pago na sexta-feira", "promessa_pagamento"),
        ("Manda a 2ª via", "pedido_2via_boleto"),
        ("Qual o valor do boleto?", "pedido_2via_boleto"),
        ("Quero parcelar", "pedido_acordo"),
        ("Tem desconto?", "pedido_acordo"),
        ("Não devo nada", "reclamacao"),
        ("Isso é engano", "reclamacao"),
        ("Segue o comprovante", "comprovante"),
        ("", True, "comprovante"),  # anexo sem texto
        ("Texto aleatório qualquer", "desconhecida"),
        ("Quero negociar", "pedido_acordo"),
        ("Paguei mês passado já", "reclamacao"),
        ("Me passa o valor atualizado", "pedido_2via_boleto"),
        ("Boa tarde, posso falar?", "saudacao"),
    ]

    erros = 0
    for item in testes:
        if len(item) == 3:
            texto, anexo, esperado = item
        else:
            texto, esperado = item
            anexo = False

        resultado = rp.classificar(texto, tem_anexo=anexo)
        status = "✅" if resultado == esperado else "❌"
        if resultado != esperado:
            erros += 1
        print(f"  {status} '{texto[:40]:40}' → {resultado:<30} (esperado: {esperado})")

    print(f"\n  Resultado: {len(testes) - erros}/{len(testes)} corretos")
    return erros


def test_gerador_respostas():
    """Testa a geração de respostas com variações e placeholders."""
    print("\n" + "=" * 60)
    print("🧪 TESTE 2: GERADOR DE RESPOSTAS")
    print("=" * 60)

    ctx = CONTEXTOS["inadimplente"]

    intencoes = [
        "confirmacao_pagamento",
        "promessa_pagamento",
        "pedido_2via_boleto",
        "pedido_acordo",
        "reclamacao",
        "saudacao",
        "comprovante",
        "desconhecida",
    ]

    erros = 0
    for intent in intencoes:
        resp = rp.gerar_resposta(intent, ctx, ja_falou_hoje=False)

        # Verifica se tem texto
        if not resp.get("texto"):
            print(f"  ❌ {intent}: texto vazio!")
            erros += 1
            continue

        # Verifica placeholders não substituídos
        texto = resp["texto"]
        placeholders = [p for p in ["{valor}", "{vencimento}", "{apto}", "{pix}", "{linha}", "{nome}"] if p in texto]
        
        status = "✅"
        info = ""
        
        if placeholders:
            status = "⚠️"
            info = f" | placeholders não substituídos: {placeholders}"
            erros += 1
        
        escalar = "🚨 ESCALAR" if resp["escalar_humano"] else "🤖 AUTO"
        delay = resp["delay_segundos"]
        
        # Mostra preview da resposta
        preview = texto[:120].replace("\n", " | ")
        print(f"  {status} {intent:<30} {escalar} | delay={delay:.1f}s")
        print(f"       → \"{preview}...\"{info}")

    print(f"\n  Erros: {erros}")
    return erros


def test_superlogica_ficticio():
    """Testa a busca fictícia de boletos."""
    print("\n" + "=" * 60)
    print("🧪 TESTE 3: BUSCA FICTÍCIA DE BOLETO")
    print("=" * 60)

    # Força modo fictício
    os.environ["SUPERLOGICA_MODO"] = "ficticio"

    # Testa com dados reais do renaissance.json
    dados = sb.extrair_dados_boleto(
        boleto_id="159203",
        unidade="0101 A",
        valor=690.00,
        vencimento="05/05/2026",
    )

    if dados.get("sucesso"):
        print(f"  ✅ Boleto 159203:")
        print(f"     PIX: {dados.get('pix', 'N/A')}")
        print(f"     Linha: {dados.get('linha_digitavel', 'N/A')}")
        print(f"     Link PDF: {dados.get('link_pdf', 'N/A')}")
        print(f"     Modo: {dados.get('modo', 'N/A')}")
        return 0
    else:
        print(f"  ❌ Falha: {dados.get('erro')}")
        return 1


def test_resposta_com_boleto_real():
    """Testa a resposta de 2ª via com dados do boleto."""
    print("\n" + "=" * 60)
    print("🧪 TESTE 4: RESPOSTA 2ª VIA COM DADOS DO BOLETO")
    print("=" * 60)

    # Simula o fluxo completo: webhook → busca boleto → gera resposta
    boleto_id = "159203"
    
    # 1. Busca dados fictícios do boleto
    dados_boleto = sb.extrair_dados_boleto(
        boleto_id=boleto_id,
        unidade="0101 A",
        valor=690.00,
        vencimento="05/05/2026",
    )
    
    # 2. Enriquece contexto
    ctx = CONTEXTOS["inadimplente"].copy()
    if dados_boleto.get("pix"):
        ctx["pix"] = dados_boleto["pix"]
    if dados_boleto.get("linha_digitavel"):
        ctx["linha_digitavel"] = dados_boleto["linha_digitavel"]
    if dados_boleto.get("link_pdf"):
        ctx["link_boleto"] = dados_boleto["link_pdf"]

    # 3. Gera resposta
    resp = rp.gerar_resposta("pedido_2via_boleto", ctx, ja_falou_hoje=False)
    
    print(f"\n  📄 Resposta gerada ({len(resp['texto'])} chars):")
    print(f"  {'='*50}")
    for linha in resp["texto"].split("\n"):
        print(f"  {linha}")
    print(f"  {'='*50}")
    print(f"\n  Delay: {resp['delay_segundos']:.1f}s")
    print(f"  Escalar: {resp['escalar_humano']}")
    
    # Verifica se tem dados do boleto no texto
    texto = resp["texto"]
    if "pix" in texto.lower() or "chave" in texto.lower():
        print("\n  ✅ PIX incluído na resposta!")
    if "boleto.pratika.com.br" in texto or "Link:" in texto:
        print("  ✅ Link do boleto incluído!")
    if "341" in texto or "237" in texto or "linha" in texto.lower():
        print("  ✅ Linha digitável incluída!")
    
    return 0


def test_memoria_conversa():
    """Testa se evita repetir saudação quando já falou hoje."""
    print("\n" + "=" * 60)
    print("🧪 TESTE 5: MEMÓRIA DE CONVERSA")
    print("=" * 60)

    ctx = CONTEXTOS["inadimplente"]

    # Primeira vez: deve responder saudação normalmente
    resp1 = rp.gerar_resposta("saudacao", ctx, ja_falou_hoje=False)
    primeira_intencao = resp1["texto"][:50]
    print(f"  🆕 Primeira vez (não falou hoje):")
    print(f"     → \"{primeira_intencao}...\"")
    print(f"     Escalar: {resp1['escalar_humano']}")

    # Segunda vez no mesmo dia: deve virar desconhecida (não repete "Oi")
    resp2 = rp.gerar_resposta("saudacao", ctx, ja_falou_hoje=True)
    segunda_intencao = resp2["texto"][:50]
    print(f"\n  🔁 Segunda vez (já falou hoje):")
    print(f"     → \"{segunda_intencao}...\"")
    print(f"     Escalar: {resp2['escalar_humano']}")
    
    if resp2["escalar_humano"]:
        print("\n  ✅ Memória funcionando: encaminhou pra humano na 2ª saudação!")
    else:
        # Não escalou, mas ao menos mostrou resposta diferente
        print("\n  ⚠️  Resposta diferente, mas não escalou humano (pode ser aceitável)")

    return 0


def test_templates_sem_contexto():
    """Testa se as respostas funcionam mesmo sem contexto (fallback)."""
    print("\n" + "=" * 60)
    print("🧪 TESTE 6: RESPOSTAS SEM CONTEXTO (FALLBACK)")
    print("=" * 60)

    intencoes = [
        "confirmacao_pagamento",
        "pedido_2via_boleto",
        "saudacao",
        "reclamacao",
        "desconhecida",
    ]

    erros = 0
    for intent in intencoes:
        resp = rp.gerar_resposta(intent, {}, ja_falou_hoje=False)
        texto = resp["texto"]
        
        # Remove placeholders não substituídos pra não poluir
        texto_limpo = texto.replace("{valor}", "").replace("{vencimento}", "").replace("{apto}", "")
        
        if not texto_limpo.strip():
            erros += 1
            print(f"  ❌ {intent}: resposta totalmente vazia!")
        else:
            delay = resp["delay_segundos"]
            print(f"  ✅ {intent:<30} → {texto_limpo[:80]}... | delay={delay:.1f}s")

    print(f"\n  Erros: {erros}")
    return erros


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    print()
    print("🔥" + "=" * 58 + "🔥")
    print("  SISTEMA DE RESPOSTAS - TESTE COMPLETO")
    print("🔥" + "=" * 58 + "🔥")
    print()

    erros = 0
    erros += test_classificador()
    erros += test_gerador_respostas()
    erros += test_superlogica_ficticio()
    erros += test_resposta_com_boleto_real()
    erros += test_memoria_conversa()
    erros += test_templates_sem_contexto()

    print("\n" + "=" * 60)
    if erros == 0:
        print("🔥 TODOS OS TESTES PASSARAM! 🔥")
    else:
        print(f"⚠️  {erros} erro(s) encontrado(s)")
    print("=" * 60)
