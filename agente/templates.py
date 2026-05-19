"""
Templates das 6 etapas da régua de cobrança Renaissance.

Cada template recebe um dict `boleto` com chaves:
    nome, unidade, valor, vencimento, dias_atraso, link_boleto, pix_chave

E retorna o texto pronto pra enviar via WhatsApp.

Estilo: cordial, direto, sem emojis exagerados, tom Pratika.

NOVO: Templates com variações humanizadas — evita que o mesmo morador
receba sempre a mesma mensagem quando houver novo ciclo.
"""

import random
from datetime import datetime


# ============================================================
# VARIAÇÕES POR ETAPA
# ============================================================
# Cada etapa tem 2-3 textos alternativos — escolhido aleatoriamente.
# Isso evita que o morador perceba que é um robô enviando sempre igual.

ETAPA_D_MENOS_3 = [
    """Prezado(a) {nome},

Aviso: o boleto do condomínio Renaissance ({unidade}) vence em 3 dias, em {venc}, valor de {valor}.

Evite juros e multa — quite ate o vencimento.

Qualquer duvida, estou a disposicao.

Pratika Administradora""",

    """{nome}, bom dia!

Lembrete: o boleto do Renaissance ({unidade}) vence em {venc}. Valor: {valor}.

Nao deixe para a ultima hora. Qualquer problema, me avise.

Atenciosamente,
Pratika""",

    """Olá {nome}, tudo bem?

O boleto do condomínio ({unidade}) vence dia {venc}. Valor: {valor}.

Se precisar de 2a via ou tiver alguma duvida, me chama.

Pratika Administradora""",

    """{nome}, informo que o boleto do Renaissance ({unidade}) vence em 3 dias: {venc}, valor {valor}.

Programe-se para evitar contratempos.

Atenciosamente,
Pratika""",

    """Prezado(a) {nome},

Faltam 3 dias para o vencimento do boleto do condomínio ({unidade}). Valor: {valor}.

Qualquer duvida, estou a disposicao.

Pratika Administradora""",
]

ETAPA_D_ZERO = [
    """Bom dia {nome},

O boleto do Renaissance ({unidade}) vence HOJE, no valor de {valor}.

Por favor, quite ate o final do dia para evitar encargos.

Pratika Administradora""",

    """{nome}, o boleto do condomínio vence hoje. Valor: {valor}.

Se precisar da 2a via, me avise. Nao deixe vencer.

Atenciosamente,
Pratika""",

    """Oi {nome}, o boleto do Renaissance ({unidade}) vence hoje! Valor: {valor}.

A regularizacao ainda hoje evita juros e multa.

Pratika""",

    """{nome}, prazo final hoje para o boleto do condomínio ({unidade}). Valor: {valor}.

Evite encargos desnecessarios — quite ate o fim do dia.

Atenciosamente,
Pratika""",
]

ETAPA_D_MAIS_1 = [
    """Bom dia {nome},

Verifiquei que o boleto do Renaissance ({unidade}) com vencimento em {venc} ainda consta em aberto. Valor: {valor}.

Se ja pagou, desconsidere — a baixa pode levar ate 2 dias uteis. Caso contrario, regularize para evitar juros.

Pratika Administradora""",

    """{nome}, identificamos que o boleto do condomínio ({unidade}) venceu em {venc} e esta pendente no valor de {valor}.

A regularização rapida evita cobranca de multa e juros. Me avise se precisar de auxilio.

Pratika""",

    """Oi {nome}, o boleto do Renaissance ({unidade}) venceu ontem e ainda esta em aberto. Valor: {valor}.

A baixa pode demorar 1-2 dias se ja pagou. Se nao, regularize o quanto antes.

Pratika Administradora""",

    """{nome}, nota do sistema: boleto do condominio ({unidade}) vencido em {venc}. Valor: {valor}.

Evite acumulo de encargos. Me avise se precisar de ajuda.

Pratika""",
]

ETAPA_D_MAIS_7 = [
    """{nome},

O boleto do Renaissance ({unidade}) esta com {dias} dias de atraso (vencimento {venc}, valor original {valor}).

A partir de agora ja estao incidindo juros e multa conforme a convencao do condominio. Quanto antes regularizar, menor o valor.

Se precisar de 2a via atualizada ou negociar, me avise.

Pratika Administradora""",

    """{nome}, tudo bem?

O boleto do condominio ({unidade}) ja esta com {dias} dias em atraso. Valor original: {valor}.

Os encargos ja estao correndo. Sugiro regularizar o quanto antes para evitar que o valor aumente ainda mais.

A disposicao,
Pratika""",

    """{nome}, ja sao {dias} dias de atraso no boleto do condominio ({unidade}). Valor: {valor}.

Procure regularizar para evitar que a situacao se complique. Estou a disposicao.

Pratika Administradora""",

    """Prezado(a) {nome}, o boleto do Renaissance ({unidade}) esta ha {dias} dias vencido. Valor inicial: {valor}.

Os encargos ja estao sendo aplicados. Regularize para nao perder o controle do valor.

Pratika""",
]

ETAPA_D_MAIS_15 = [
    """{nome},

O boleto do Renaissance ({unidade}) ja esta com {dias} dias de atraso (vencimento {venc}, valor {valor}).

Gostaria de entender se ha alguma dificuldade. Podemos conversar sobre parcelamento ou acordo para evitar o protesto do nome.

Me retorne, por favor.

Pratika Administradora""",

    """Bom dia {nome},

Sao {dias} dias de atraso no boleto do condominio ({unidade}). Valor atualizado com encargos: {valor}.

Precisamos resolver essa situacao. Se nao houver retorno, o caso seguira para protesto em cartorio e restricao de CPF/CNPJ.

Me ligue ou responda para negociarmos.

Atenciosamente,
Pratika""",

    """{nome}, estou preocupado com a situacao do boleto do condominio ({unidade}). Ja sao {dias} dias em atraso, valor de {valor}.

Podemos buscar uma solucao juntos? Me responda para evitar medidas legais.

Pratika""",

    """Prezado(a) {nome}, o debito do Renaissance ({unidade}) ja soma {dias} dias. Valor: {valor}.

Sugiro regularizar ou negociar o quanto antes para evitar protesto.

A disposicao,
Pratika Administradora""",
]

ETAPA_D_MAIS_30 = [
    """{nome},

O boleto do Renaissance ({unidade}) esta com {dias} dias em atraso (vencimento {venc}). Valor: {valor}.

Esta e a ultima notificacao antes do envio para protesto e inclusao nos orgaos de credito (SPC/Serasa).

Para evitar, entre em contato urgente para negociacao. Temos opcoes de parcelamento.

Pratika Administradora""",

    """{nome}, preciso da sua atencao.

O debito do condominio ({unidade}) ja soma {dias} dias de atraso e o valor acumulado e de {valor}.

Se nao houver regularizacao em 5 dias uteis, o caso sera encaminhado ao juridico, com custas processuais adicionais.

Nao deixe para depois. Me responda aqui ou indique o melhor horario para eu ligar.

Pratika""",

    """{nome}, comunicado importante: o boleto do Renaissance ({unidade}) esta ha {dias} dias em atraso. Valor: {valor}.

Esta e a ultima tentativa amigavel. Apos isso, o caso segue para protesto.

Entre em contato urgente para negociarmos.

Pratika Administradora""",

    """Prezado(a) {nome}, o debito do condominio ({unidade}) ja atingiu {dias} dias. Valor atual: {valor}.

Para evitar negativacao e custas judiciais, procure regularizar nos proximos dias.

Estou a disposicao para negociar.

Pratika""",
]


# ============================================================
# HELPERS
# ============================================================

def _formatar_valor(valor) -> str:
    """Converte float pra 'R$ 1.234,56'."""
    if isinstance(valor, str):
        return valor
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _primeiro_nome(nome_completo: str) -> str:
    """'João Silva Santos' -> 'João'."""
    if not nome_completo:
        return "morador(a)"
    return nome_completo.strip().split()[0].title()


def _escolher_variacao(variacoes: list[str], seed: str = None) -> str:
    """
    Escolhe uma variação aleatória.
    Se seed for informado (ex: id do boleto), garante consistência
    pra mesma unidade no mesmo ciclo.
    """
    if seed:
        # Determinístico baseado no seed
        idx = abs(hash(seed)) % len(variacoes)
        return variacoes[idx]
    return random.choice(variacoes)


def _montar_kwargs(boleto: dict) -> dict:
    """Prepara os argumentos pros templates."""
    return {
        "nome": _primeiro_nome(boleto.get("nome", "")),
        "unidade": boleto.get("unidade", ""),
        "valor": _formatar_valor(boleto.get("valor", 0)),
        "venc": boleto.get("vencimento", ""),
        "dias": boleto.get("dias_atraso", 0),
        "link_boleto": boleto.get("link_boleto", ""),
        "pix": boleto.get("pix_chave", ""),
    }


# ============================================================
# ETAPAS PÚBLICAS
# ============================================================

def etapa_d_menos_3(boleto: dict, seed: str = None) -> str:
    """Lembrete pré-vencimento (3 dias antes)."""
    kwargs = _montar_kwargs(boleto)
    template = _escolher_variacao(ETAPA_D_MENOS_3, seed=seed)
    return template.format(**kwargs)


def etapa_d_zero(boleto: dict, seed: str = None) -> str:
    """Vence hoje."""
    kwargs = _montar_kwargs(boleto)
    template = _escolher_variacao(ETAPA_D_ZERO, seed=seed)
    return template.format(**kwargs)


def etapa_d_mais_1(boleto: dict, seed: str = None) -> str:
    """1 dia em atraso."""
    kwargs = _montar_kwargs(boleto)
    template = _escolher_variacao(ETAPA_D_MAIS_1, seed=seed)
    return template.format(**kwargs)


def etapa_d_mais_7(boleto: dict, seed: str = None) -> str:
    """1 semana em atraso."""
    kwargs = _montar_kwargs(boleto)
    template = _escolher_variacao(ETAPA_D_MAIS_7, seed=seed)
    return template.format(**kwargs)


def etapa_d_mais_15(boleto: dict, seed: str = None) -> str:
    """15 dias em atraso."""
    kwargs = _montar_kwargs(boleto)
    template = _escolher_variacao(ETAPA_D_MAIS_15, seed=seed)
    return template.format(**kwargs)


def etapa_d_mais_30(boleto: dict, seed: str = None) -> str:
    """30+ dias em atraso."""
    kwargs = _montar_kwargs(boleto)
    template = _escolher_variacao(ETAPA_D_MAIS_30, seed=seed)
    return template.format(**kwargs)


# ============================================================
# MAPA: dias_atraso -> template
# ============================================================

TEMPLATES = {
    -3: ("D-3", "Lembrete pré-vencimento", etapa_d_menos_3),
    0:  ("D-0", "Vence hoje", etapa_d_zero),
    1:  ("D+1", "1 dia atraso", etapa_d_mais_1),
    7:  ("D+7", "1 semana atraso", etapa_d_mais_7),
    15: ("D+15", "2 semanas atraso", etapa_d_mais_15),
    30: ("D+30", "1 mês atraso", etapa_d_mais_30),
}


def determinar_etapa(dias_atraso: int):
    """
    Retorna (codigo, descricao, funcao) da etapa exata pro dia.
    Se não bate com nenhum dos 6 pontos, retorna None.

    Política: só dispara nos pontos exatos. Sem "ganchos" entre.
    Se o agente perdeu o D-3 do boleto, espera D-0.
    """
    return TEMPLATES.get(dias_atraso)


def renderizar(boleto: dict, seed: str = None) -> dict:
    """
    Renderiza a mensagem pro boleto, se hoje for um dos pontos da régua.

    seed: opcional — se passado, usa hash(seed) pra escolher variação
    deterministicamente (útil pra testes ou manter consistência).

    Retorna:
        {
            "deve_enviar": bool,
            "etapa_codigo": "D+7" ou None,
            "etapa_descricao": ...,
            "texto": ...,
            "boleto": boleto
        }
    """
    dias = boleto["dias_atraso"]
    etapa = determinar_etapa(dias)

    if not etapa:
        return {
            "deve_enviar": False,
            "etapa_codigo": None,
            "etapa_descricao": f"Dia {dias} fora da régua",
            "texto": None,
            "boleto": boleto,
        }
