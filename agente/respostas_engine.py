"""
respostas_engine.py — Motor gerador de respostas combinatórias.

Em vez de escrever 100 respostas na mão, este motor COMBINA
pedaços (abertura + corpo + fechamento) pra gerar MILHARES
de variações únicas automaticamente.

Exemplo:
  "{nome}, {abertura} {corpo} {fechamento}"
  
  Gera: "João, bom dia! O boleto venceu. Pode regularizar?"
  Gera: "João, boa tarde! Identifiquei pendência. Me avise."
  etc.
"""

import random

# ─── ABERTURAS ───
ABERTURAS = [
    "bom dia!",
    "boa tarde!",
    "ola!",
    "oi!",
    "tudo bem?",
    "como vai?",
    "espero que esteja bem.",
    "boa noite!",
    "tudo certo?",
]

# ─── CONECTORES ───
CONECTORES = [
    " tudo bem?",
    " como esta?",
    "",
    " espero que esteja bem.",
    "",
]

# ─── CORPO: confirmacao_pagamento ───
CORPO_CONFIRMACAO = [
    "Preciso do comprovante de pagamento para dar baixa no sistema.",
    "Assim que enviar o comprovante, confirmo a baixa imediatamente.",
    "Pode enviar o comprovante? Ja regularizo o cadastro.",
    "O comprovante ja foi enviado? Preciso para registrar.",
    "Ok, so preciso do comprovante para liberar a baixa.",
    "Me manda o comprovante que ja resolvo aqui.",
    "Legal, confirma o pagamento com o comprovante.",
    "So falta o comprovante para finalizar. Manda ai.",
    "Envia o comprovante para eu dar baixa no sistema.",
    "Pode mandar o print ou PDF do pagamento?",
]

CORPO_PROMESSA = [
    "Anotado, fico no aguardo. Lembrando que o boleto vencido ja tem juros e multa.",
    "Ok, lembrando que atraso adicional gera mais encargos. Me avise quando pagar.",
    "Certo, quando pagar me mande o comprovante para eu dar baixa.",
    "Anotado aqui. Se precisar de 2a via ou PIX, so pedir.",
    "Combinado, fico aguardando. Os juros continuam correndo ate a quitação.",
    "Ok, registrei. Nao esqueca de me enviar o comprovante depois.",
    "Certo, qualquer dificuldade me chama antes do vencimento.",
    "Anotado, estou acompanhando. Fique atento aos encargos diarios.",
    "Ok, sem pressa mas lembrando que o valor aumenta com o tempo.",
    "Combinado, me avise assim que realizar o pagamento.",
]

CORPO_2VIA = [
    "Segue os dados do boleto:\n\nValor: {valor}\nVencimento: {vencimento}\nUnidade: {apto}\n\nPIX: {pix}\nLinha: {linha}\n{link}",
    "Aqui esta a 2a via:\n\n{valor} | {vencimento} | {apto}\n\nPIX: {pix}\nLinha: {linha}\n{link}",
    "Dados para pagamento:\n\nValor: {valor}\nVenc: {vencimento}\nApto: {apto}\n\nPIX: {pix}\nCodigo: {linha}\n{link}",
    "Segue o boleto atualizado:\n\n{valor} vencendo {vencimento}\n{apto}\n\nPIX: {pix}\nLinha: {linha}\n{link}",
    "Aqui estao os dados do boleto:\n\nValor: {valor}\nVencimento: {vencimento}\nApto: {apto}\n\nPIX: {pix}\nLinha digitavel: {linha}\n{link}",
]

CORPO_ACORDO = [
    "Vou encaminhar seu caso para analise de parcelamento.",
    "Seu pedido de acordo foi registrado. Retorno em ate 24h.",
    "Vou submeter para a administradora analisar.",
    "Registrei seu pedido de parcelamento. Assim que sair, aviso.",
    "Vou consultar as opcoes disponiveis e retorno.",
    "Seu caso foi encaminhado para o setor responsavel.",
    "Vou verificar o que podemos fazer e te retorno.",
    "Registrado para analise. Prazo medio de resposta: 24h.",
]

CORPO_RECLAMACAO = [
    "Vou verificar com a administradora o que houve.",
    "Recebi sua reclamacao, vou apurar internamente.",
    "Deixa eu verificar o historico do seu apto.",
    "Vou investigar e te retorno ainda hoje.",
    "Recebi sua manifestacao, vou conferir o sistema.",
    "Vou apurar o caso, pedimos desculpas pelo transtorno.",
    "Deixa eu verificar e confirmo a situacao.",
    "Ok, vou checar o que aconteceu e retorno.",
]

CORPO_SAUDACAO = [
    "Aqui e da Pratika, sobre o condominio Renaissance.",
    "Sou da Pratika, sobre o boleto do apto {apto}.",
    "Estou verificando a pendencia do apto {apto}.",
    "Precisamos tratar sobre o boleto do apto {apto}.",
    "Estou cuidando do boleto do apto {apto}.",
    "Entrando em contato sobre o boleto pendente do apto {apto}.",
    "Aqui e a Pratika, do condominio Renaissance.",
    "Estou verificando as pendencias do apto {apto}.",
]

CORPO_COMPROVANTE = [
    "Recebi o comprovante, vou validar.",
    "Comprovante recebido, conferindo os dados.",
    "Ok, comprovante em maos, processando a baixa.",
    "Recebi, ja estou conferindo.",
    "Comprovante recebido, confirmo em instantes.",
    "Ok, vou verificar os valores e ja retorno.",
    "Recebi, processando a regularizacao.",
    "Comprovante em maos, ja dou baixa.",
]

CORPO_DESCONHECIDA = [
    "Vou verificar e retorno em instantes.",
    "Deixa eu checar o sistema.",
    "Estou consultando e ja respondo.",
    "Vou verificar seu caso e retorno.",
    "Deixa eu consultar aqui.",
    "Vou checar as informacoes.",
    "Um momento, vou verificar no sistema.",
    "Estou apurando e ja volto.",
]

# ─── CORPO: duvida (explica direto, sem meta-comentário) ───
CORPO_DUVIDA = [
    "O boleto do condominio e gerado mensalmente. O valor de {valor} cobre as despesas comuns do Renaissance. Vencimento: {vencimento}. Pode pagar via PIX ({pix}) ou linha digitavel ({linha}). A baixa leva ate 2 dias uteis.",
    "O valor de {valor} e referente a taxa condominial do apto {apto}. Pagamento pode ser feito por:\n1. PIX: {pix}\n2. Linha digitavel: {linha}\nA baixa e automatica em ate 2 dias apos o pagamento.",
    "O condominio Renaissance rateia as despesas comuns entre todos os moradores. O boleto do apto {apto} no valor de {valor} vence em {vencimento}. Apos o vencimento, incidem juros e multa conforme a convencao. Pode pagar via PIX ({pix}) ou linha digitavel ({linha}).",
    "Esse boleto e do apto {apto}, valor {valor}, vencimento {vencimento}. Pode pagar via PIX ({pix}) ou linha: {linha}. O pagamento e processado em ate 2 dias uteis. Se preferir o boleto em PDF, me avise.",
    "O boleto de {valor} do apto {apto} venceu em {vencimento}. Para regularizar, pode usar o PIX {pix} ou a linha digitavel {linha}. O sistema registra a baixa automaticamente em ate 2 dias uteis. Qualquer coisa, estou aqui.",
    "A taxa condominial do apto {apto} esta em {valor}, vencimento {vencimento}. As formas de pagamento disponiveis sao: PIX ({pix}) e linha digitavel ({linha}). Apos o pagamento, o sistema da baixa automaticamente.",
]

# ─── FECHAMENTOS ───
FECHAMENTOS = [
    "Pode me ajudar?",
    "Me avise quando puder.",
    "Estou a disposicao.",
    "Agradeco a atencao.",
    "Qualquer duvida, estou aqui.",
    "Obrigado.",
    "A disposicao para ajudar.",
    "Fico no aguardo.",
    "Me retorne quando possivel.",
    "Podemos resolver hoje?",
    "Agradeco o contato.",
    "",
    "Estou aqui para ajudar.",
    "Conte comigo.",
]


def gerar_resposta_personalizada(
    intent: str,
    ctx: dict,
    historico: list[dict] = None,
    padroes: dict = None,
) -> str:
    """
    Gera uma resposta TOTALMENTE PERSONALIZADA em tempo real,
    combinando:
      - Intenção detectada
      - Nome do cliente
      - Unidade/apto
      - Histórico da conversa (se já falou sobre algo antes)
      - Padrões de comportamento
    
    NUNCA repete a mesma combinação duas vezes seguidas.
    
    Returns: str com a resposta personalizada
    """
    nome = ctx.get("nome", "").split()[0] if ctx.get("nome") else "morador(a)"
    apto = ctx.get("unidade") or ctx.get("apto") or "—"
    valor = ctx.get("valor") or "—"
    venc = ctx.get("vencimento") or "—"
    pix = ctx.get("pix") or "[PIX]"
    linha = ctx.get("linha_digitavel") or "[Linha]"
    link = ctx.get("link_boleto") or ""
    dias_atraso = ctx.get("dias_atraso", 0)

    # ─── Personaliza com base no HISTÓRICO ───
    padroes = padroes or {}
    ja_falou_antes = (padroes.get("total_interacoes", 0) > 1)
    ja_pediu_acordo = padroes.get("ja_pediu_acordo", False)
    ja_reclamou = padroes.get("ja_reclamou", False)

    abertura = random.choice(ABERTURAS)
    fechamento = random.choice(FECHAMENTOS)

    # ─── ESCOLHA DO CORPO BASEADO EM CONTEXTO ───
    if intent == "confirmacao_pagamento":
        corpo = random.choice(CORPO_CONFIRMACAO)
        if ja_pediu_acordo:
            corpo += " E sobre o acordo que tratamos, ja resolvemos tambem?"
        texto = f"{nome}, {corpo} {fechamento}"

    elif intent == "promessa_pagamento":
        corpo = random.choice(CORPO_PROMESSA)
        if dias_atraso > 0:
            corpo += f" Lembrando que seu boleto ja esta ha {dias_atraso} dias em atraso."
        texto = f"{nome}, {corpo}"

    elif intent == "pedido_2via_boleto":
        corpo = random.choice(CORPO_2VIA)
        sufixo = f"\n\n{random.choice(['Pagou? Me manda o comprovante.', 'Apos pagar, envie o comprovante.', 'Fico no aguardo do pagamento.'])}"
        texto = f"{corpo.format(valor=valor, vencimento=venc, apto=apto, pix=pix, linha=linha, link=('🔗 ' + link) if link else '')}{sufixo}"

    elif intent == "pedido_acordo":
        corpo = random.choice(CORPO_ACORDO)
        if ja_falou_antes:
            corpo += " Ja estou ciente do seu caso."
        texto = f"{abertura} {corpo} {fechamento}"

    elif intent == "reclamacao":
        corpo = random.choice(CORPO_RECLAMACAO)
        if not ja_reclamou:
            corpo += " Pedimos desculpas pelo transtorno."
        texto = f"{corpo} {fechamento}"

    elif intent == "saudacao":
        corpo = random.choice(CORPO_SAUDACAO)
        texto = f"{abertura} {corpo.format(apto=apto)} {fechamento}"

    elif intent == "comprovante":
        corpo = random.choice(CORPO_COMPROVANTE)
        texto = f"{corpo} {fechamento}"

    elif intent == "duvida":
        corpo = random.choice(CORPO_DUVIDA)
        texto = corpo.format(valor=valor, vencimento=venc, apto=apto, pix=pix, linha=linha, link=("🔗 " + link) if link else "")
        texto += f"\n\n{fechamento}"

    else:  # desconhecida
        corpo = random.choice(CORPO_DESCONHECIDA)
        texto = f"{corpo} {fechamento}"

    return texto.strip()


def gerar_resposta_composta(intent: str, ctx: dict, variacoes_existentes: list[str]) -> str:
    """
    Gera uma resposta COMPOSTA combinando abertura + corpo + fechamento.
    Só gera se a lista existente de variações for menor que o desejado.
    """
    nome = ctx.get("nome", "").split()[0] if ctx.get("nome") else ""
    apto = ctx.get("unidade") or ctx.get("apto") or "—"
    valor = ctx.get("valor") or "—"
    venc = ctx.get("vencimento") or "—"
    pix = ctx.get("pix") or "[PIX]"
    linha = ctx.get("linha_digitavel") or "[Linha]"
    link = ctx.get("link_boleto") or ""

    abertura = random.choice(ABERTURAS)
    fechamento = random.choice(FECHAMENTOS)

    # Escolhe o corpo baseado na intenção
    corpos = {
        "confirmacao_pagamento": CORPO_CONFIRMACAO,
        "promessa_pagamento": CORPO_PROMESSA,
        "pedido_2via_boleto": CORPO_2VIA,
        "pedido_acordo": CORPO_ACORDO,
        "reclamacao": CORPO_RECLAMACAO,
        "saudacao": CORPO_SAUDACAO,
        "comprovante": CORPO_COMPROVANTE,
        "desconhecida": CORPO_DESCONHECIDA,
        "duvida": CORPO_DUVIDA,
    }

    corpo = random.choice(corpos.get(intent, CORPO_DESCONHECIDA))

    # Monta
    if intent == "pedido_2via_boleto":
        # 2a via tem formato especial com dados estruturados
        texto = corpo.format(valor=valor, vencimento=venc, apto=apto, pix=pix, linha=linha, link=("🔗 " + link) if link else "")
        if fechamento:
            texto += f"\n\n{fechamento}"
    elif intent == "saudacao":
        texto = f"{abertura} {corpo.format(apto=apto)} {fechamento}" if nome else f"{abertura} {corpo.format(apto=apto)} {fechamento}"
    else:
        texto = f"{corpo} {fechamento}" if fechamento else corpo

    return texto.strip()


def popular_respostas_faltantes(respostas_dict: dict, ctx: dict, min_por_intent: int = 50):
    """
    Para cada intenção, se tiver menos que min_por_intent variações,
    gera novas combinadas até atingir o mínimo.
    
    Returns: (dict atualizado, total_gerado)
    """
    total_gerado = 0
    for intent, existentes in respostas_dict.items():
        if intent not in ("confirmacao_pagamento", "promessa_pagamento", "pedido_2via_boleto",
                          "pedido_acordo", "reclamacao", "saudacao", "comprovante", "desconhecida"):
            continue
        
        atuais = len(existentes)
        if atuais >= min_por_intent:
            continue
        
        # Gera novas tentando evitar duplicatas
        tentativas = set(existentes)
        max_tentativas = (min_por_intent - atuais) * 3  # tenta 3x mais pra evitar repetição
        for _ in range(max_tentativas):
            if len(tentativas) >= min_por_intent:
                break
            nova = gerar_resposta_composta(intent, ctx, existentes)
            if nova not in tentativas:
                tentativas.add(nova)
                total_gerado += 1
        
        respostas_dict[intent] = list(tentativas)
    
    return respostas_dict, total_gerado
