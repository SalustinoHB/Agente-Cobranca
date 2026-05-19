"""
respostas.py — Classificacao de intencao + gerador de respostas.

VERSAO 3.0 — Tom de cobranca profissional, firme e direto.

Intencoes:
    - confirmacao_pagamento   ("paguei", "ja paguei", "transferi", "pago")
    - promessa_pagamento      ("vou pagar", "pago amanha", "pago dia X")
    - pedido_2via_boleto      ("manda o boleto", "qual o valor", "linha digitavel")
    - pedido_acordo           ("posso parcelar", "tem desconto", "quero negociar")
    - reclamacao              ("nao devo", "ja paguei mes passado", "esse boleto nao e meu")
    - saudacao                ("oi", "bom dia", "boa tarde", "tudo bem")
    - comprovante             quando vem imagem/documento
    - desconhecida            fallback

Tom do cobrador:
  - Educado mas firme
  - Lembra da obrigacao do pagamento
  - Menciona consequencias (juros, protesto, negativacao) quando necessario
  - Profissional, sem exageros
  - Direto ao ponto
"""

from __future__ import annotations

import os
import re
import random
import time
import unicodedata
from typing import Optional


# ============================================================
# Util
# ============================================================
def _normalize(texto: str) -> str:
    """Lower + sem acentos + espacos normalizados."""
    if not texto:
        return ""
    t = unicodedata.normalize("NFKD", texto)
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = t.lower().strip()
    t = re.sub(r"\s+", " ", t)
    return t


def _formatar_valor(valor) -> str:
    """float -> 'R$ 1.234,56'."""
    if valor is None:
        return "—"
    if isinstance(valor, str):
        return valor
    try:
        return f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return str(valor)


def _escolher_variacao(variacoes: list[str]) -> str:
    """Escolhe uma resposta aleatoria da lista."""
    return random.choice(variacoes)


def _delay_natural() -> float:
    """Retorna segundos de delay (3-8s) simulando digitacao humana."""
    return random.uniform(3.0, 8.0)


# ============================================================
# Banco de respostas — TOM DE COBRADOR
# ============================================================

RESPOSTAS = {
    "confirmacao_pagamento": [
        "Ok. Preciso do comprovante de pagamento para dar baixa no sistema. Pode enviar o print ou PDF por aqui?",
        "Entendi. Assim que enviar o comprovante, confirmo a baixa. Pode mandar agora?",
        "Perfeito. Envia o comprovante aqui no chat que ja regularizo o cadastro.",
        "Certo. Manda o comprovante que eu ja libero a baixa e atualizo o sistema.",
        "O comprovante ja foi enviado? Assim que receber, confirmo a baixa imediatamente.",
        "Ok, so preciso do comprovante para registrar. Me envia quando puder.",
        "Entendi. Pode encaminhar o comprovante por aqui mesmo? Ja resolvo.",
        "Perfeito. Me manda o comprovante que ja dou baixa no sistema.",
        "Legal, manda o comprovante para eu confirmar e liberar.",
        "So preciso do comprovante para finalizar. Manda ai.",
        "Ok, comprovante pendente. Me envia que ja resolvo.",
        "Pode mandar o comprovante agora? Ja confirmo pra voce.",
    ],
    "promessa_pagamento": [
        "Anotado. Fico no aguardo do pagamento. Lembrando que o boleto vencido ja esta com juros e multa — quanto mais cedo pagar, menor o valor.",
        "Ok. Nao esqueca que o valor original e {valor}. Qualquer atraso adicional incide em novos encargos. Me avise quando pagar.",
        "Certo. Acompanho aqui. Quando fizer o pagamento, me mande o comprovante para eu dar baixa.",
        "Anotado. Se precisar do link do boleto ou PIX, so pedir. Estou a disposicao.",
        "Ok, combinado. Fico no aguardo. Me avise assim que pagar.",
        "Anotado aqui. So lembre que os juros continuam correndo ate a quitação.",
        "Certo, espero seu pagamento. Qualquer dificuldade, me chama antes do vencimento.",
        "Ok. Vou deixar registrado. Me mande o comprovante quando pagar.",
        "Combinado. Nao esqueca de me enviar o comprovante apos o pagamento.",
        "Anotado. Acompanho seu caso. Fique atento aos encargos diarios.",
        "Ok, sem problema. Quando puder pagar, me avise que acompanho.",
        "Certo. Lembrando que posso ajudar com 2a via ou PIX se precisar.",
    ],
    "pedido_2via_boleto": [
        "Segue os dados do boleto:\n\nValor: {valor}\nVencimento original: {vencimento}\nApto: {apto}\n\nPIX: {pix}\nLinha digitavel: {linha}\n{link}\n\nApos o pagamento, me envie o comprovante para confirmar a baixa.",
        "Aqui esta a 2a via atualizada:\n\nValor: {valor}\nVencimento: {vencimento}\nApto: {apto}\n\nPIX: {pix}\nLinha digitavel: {linha}\n{link}\n\nPagou? Me manda o comprovante que ja libero.",
        "Dados do boleto:\n\nValor: {valor}\nVencimento: {vencimento}\nUnidade: {apto}\n\nChave PIX: {pix}\nLinha: {linha}\n{link}\n\nAguardando pagamento. Qualquer duvida, estou aqui.",
        "Segue o boleto atualizado:\n\nValor: {valor}\nVencimento: {vencimento}\nUnidade: {apto}\n\nPIX: {pix}\nLinha: {linha}\n{link}\n\nMe avise quando pagar.",
        "Aqui estao os dados:\n\nValor: {valor}\nVencimento: {vencimento}\nApto: {apto}\n\nPIX: {pix}\nLinha: {linha}\n{link}\n\nQualquer duvida, estou a disposicao.",
        "Segue a 2a via:\n\n{valor} | {vencimento} | {apto}\nPIX: {pix}\nLinha: {linha}\n{link}\n\nApos o pagamento, envie o comprovante.",
        "Dados para pagamento:\n\nValor: {valor}\nVenc: {vencimento}\nApto: {apto}\n\nPIX: {pix}\nCodigo: {linha}\n{link}\n\nAguardamos a regularizacao.",
        "Segue o boleto:\n\n{valor} vencendo {vencimento}\nUnidade: {apto}\n\nPIX: {pix}\nLinha: {linha}\n{link}\n\nFico no aguardo do pagamento.",
    ],
    "pedido_acordo": [
        "Entendi. Vou encaminhar seu caso para o setor responsavel analisar parcelamento. Te retorno com as opcoes disponiveis em ate 24h uteis.",
        "Seu pedido de acordo foi registrado. Vou passar para analise. Assim que tiver retorno, entro em contato.",
        "Certo. Vou submeter seu cenario para a administradora. Eles analisam e eu volto com a resposta. Prazo medio: 24h.",
        "Entendi. Vou registrar seu pedido de parcelamento para analise. Retorno em breve.",
        "Ok, vou levar seu caso para avaliacao de acordo. Te mantenho informado.",
        "Seu pedido foi registrado. A analise leva ate 24h uteis. Assim que sair, aviso.",
        "Certo. Vou consultar a administradora sobre as opcoes. Retorno assim que possivel.",
        "Entendi seu pedido. Vou encaminhar para o setor competente. Aguarde retorno.",
    ],
    "reclamacao": [
        "Entendo. Vou verificar com a administradora o que houve e te dou um retorno ainda hoje. Pedimos desculpas se houve algum equivoco.",
        "Ok, recebi sua reclamacao. Vou apurar internamente e te retorno assim que tiver uma posicao oficial.",
        "Entendi. Deixa eu verificar o historico do seu apto e confirmo a situacao. Prometo retorno rapido.",
        "Lamento pelo ocorrido. Vou investigar e te retorno em ate 24h.",
        "Recebi sua manifestacao. Vou verificar com a administradora e volto com uma resposta.",
        "Entendo seu ponto. Deixa eu conferir o sistema e confirmo o que houve.",
        "Vou apurar o caso internamente. Assim que tiver a resposta, entro em contato.",
        "Ok, vou verificar o que aconteceu. Pedimos desculpas por qualquer transtorno.",
    ],
    "saudacao": [
        "{nome}, bom dia! Aqui e da Pratika, administradora do Renaissance. Estou entrando em contato sobre o boleto do apto {apto} que esta pendente. Como posso ajudar?",
        "Ola {nome}! Sou da Pratika, sobre o condominio do apto {apto}. Precisamos regularizar a situacao do boleto. Pode me ajudar?",
        "Bom dia {nome}! Pratika Administradora. Estou verificando a pendencia do apto {apto}. Podemos resolver hoje?",
        "Ola {nome}, tudo bem? Aqui e da Pratika, sobre o condominio Renaissance. Precisamos tratar sobre o boleto do apto {apto}.",
        "Oi {nome}, bom dia! Pratika na linha. Estou cuidando do boleto do apto {apto}. Podemos conversar?",
        "Boa tarde {nome}! Aqui e da Pratika. Estou entrando em contato sobre o boleto pendente do apto {apto}.",
        "Ola {nome}! Tudo bem? Aqui e a Pratika, do condominio Renaissance. Precisamos resolver a situacao do apto {apto}.",
        "Oi {nome}! Pratika Administradora. Estou verificando as pendencias do apto {apto}. Podemos acertar hoje?",
    ],
    "comprovante": [
        "Recebi o comprovante. Vou validar e ja confirmo a baixa no sistema.",
        "Ok, comprovante recebido. Estou conferindo os dados e ja retorno.",
        "Comprovante recebido com sucesso. Vou processar e confirmo em instantes.",
        "Perfeito, comprovante recebido. Ja estou conferindo.",
        "Recebi. Vou verificar os valores e confirmo a baixa.",
        "Ok, recebi o comprovante. Deixa eu conferir e ja te confirmo.",
        "Comprovante em maos. Vou processar a baixa e ja retorno.",
        "Recebi o comprovante. Em instantes confirmo a regularizacao.",
    ],
    "desconhecida": [
        "Recebi sua mensagem. Vou verificar aqui e te retorno em instantes.",
        "Entendi. Deixa eu checar o sistema e ja volto com uma resposta.",
        "Ok. Estou consultando aqui e ja te respondo.",
        "Vou verificar seu caso e retorno rapidinho.",
        "Deixa eu consultar aqui e ja te dou uma posicao.",
        "Recebi. Vou verificar as informacoes e ja retorno.",
        "Ok, vou checar e volto ja com uma resposta.",
        "Um momento, vou consultar o sistema e ja te respondo.",
    ],
    "duvida": [
        "O boleto do condominio e gerado mensalmente. O valor de {valor} cobre as despesas comuns do Renaissance. Vencimento: {vencimento}. Pode pagar via PIX ({pix}) ou linha digitavel ({linha}). A baixa leva ate 2 dias uteis.",
        "O valor de {valor} e referente a taxa condominial do apto {apto}. Pagamento pode ser feito por:\n1. PIX: {pix}\n2. Linha digitavel: {linha}\nA baixa e automatica em ate 2 dias apos o pagamento.",
        "O condominio Renaissance rateia as despesas comuns entre todos os moradores. O boleto do apto {apto} no valor de {valor} vence em {vencimento}. Apos o vencimento, incidem juros e multa conforme a convencao. Pode pagar via PIX ({pix}) ou linha digitavel ({linha}).",
        "Esse boleto e do apto {apto}, valor {valor}, vencimento {vencimento}. Pode pagar via PIX ({pix}) ou linha: {linha}. O pagamento e processado em ate 2 dias uteis.",
        "A taxa condominial do apto {apto} esta em {valor}, vencimento {vencimento}. As formas de pagamento disponiveis sao: PIX ({pix}) e linha digitavel ({linha}). Apos o pagamento, o sistema da baixa automaticamente.",
    ],
}

# ============================================================
# Regras de classificacao (ordem importa)
# ============================================================
# Reclamacao vem ANTES de confirmacao_pagamento pra pegar variantes tipo
# "ja paguei isso mes passado".
REGRAS = [
    (
        "duvida",
        [
            r"\bnao entendi\b",
            r"\bnao entendo\b",
            r"\bnao compreendi\b",
            r"\bnao sei\b",
            r"\bcomo funciona\b",
            r"\bme explica\b",
            r"\bexplica (melhor|direito|como)\b",
            r"\bpode explicar\b",
            r"\bgostaria de saber\b",
            r"\bqueria entender\b",
            r"\btem como explicar\b",
            r"\bnao ficou claro\b",
            r"\besclarecer\b",
            r"\bestou em duvida\b",
            r"\bqual a diferenca\b",
            r"\bme tira uma duvida\b",
            r"\bduvida\b",
            r"\bnao faco ideia\b",
            r"\bcomo assim\b",
            r"\bo que significa\b",
            r"\bo que e\b",
            r"\bnao to entendendo\b",
            r"\bsou leigo\b",
            r"\bprimeira vez\b",
        ],
    ),
    (
        "reclamacao",
        [
            r"\bnao devo\b",
            r"\bnao deve\b",
            r"\babsurdo\b",
            r"\b(ja )?paguei (isso |essa |esse )?(ano passado|mes passado|faz tempo|ha (muito )?tempo)\b",
            r"\b(ja )?paguei .{0,10}(ano passado|mes passado)\b",
            r"\besse boleto nao e meu\b",
            r"\bnao e meu\b",
            r"\bnao reconheco\b",
            r"\bisso (esta |ta )?(errado|engano)\b",
            r"\bdiscordo\b",
            r"\bcobranca indevida\b",
            r"\b(esta|ta) errado\b",
            r"\bengano\b",
        ],
    ),
    (
        "pedido_acordo",
        [
            r"\bacordo\b",
            r"\bparcelar\b",
            r"\bparcelamento\b",
            r"\bposso parcelar\b",
            r"\bdesconto\b",
            r"\btem desconto\b",
            r"\bnegociar\b",
            r"\bnegociacao\b",
            r"\bdividir em\b",
            r"\bem (\d+) vezes?\b",
            r"\bcomo faco\b",
        ],
    ),
    (
        "comprovante",
        [
            r"\bcomprovante\b",
            r"\bsegue\b",
            r"\bai esta\b",
            r"\bai vai\b",
            r"\baqui esta\b",
        ],
    ),
    (
        "confirmacao_pagamento",
        [
            r"\bja paguei\b",
            r"\bpaguei (ja|hoje|ontem|agora|sim)\b",
            r"^\s*paguei\b",
            r"^\s*pago\s*$",
            r"\besta pago\b",
            r"\b(ja )?(esta|ta) pago\b",
            r"\bquitei\b",
            r"\btransferi\b",
            r"\bfiz o pix\b",
            r"\bfiz pix\b",
        ],
    ),
    (
        "promessa_pagamento",
        [
            r"\bvou pagar\b",
            r"\bpago amanha\b",
            r"\bpago (na |a )?(segunda|terca|quarta|quinta|sexta|sabado|domingo)",
            r"\bpago dia (\d+)\b",
            r"\bpago no dia (\d+)\b",
            r"\bate (sexta|segunda|amanha|terca|quarta|quinta|sabado|domingo)\b",
            r"\bsemana que vem\b",
            r"\bproxima semana\b",
            r"\bdepois do dia (\d+)\b",
            r"\bso (consigo |posso )?(no )?dia \d+\b",
        ],
    ),
    (
        "pedido_2via_boleto",
        [
            r"\b2 ?via\b",
            r"\bsegunda via\b",
            r"\b2a via\b",
            r"\bmanda (o )?boleto\b",
            r"\benviar (o )?boleto\b",
            r"\bme (manda |envia )(o )?boleto\b",
            r"\blinha digitavel\b",
            r"\bcodigo de barras\b",
            r"\bcodigo pix\b",
            r"\bboleto atualizado\b",
            r"\bnovo boleto\b",
            r"\bqual (o )?valor\b",
            r"\bquanto (e|fica|deu|esta|ta)\b",
            r"\bvalor (atualizado|total)\b",
            r"\bpreciso da 2via\b",
            r"\bme passa o valor\b",
            r"\bchave pix\b",
            r"\bqr ?code\b",
        ],
    ),
    (
        "saudacao",
        [
            r"^\s*oi\s*[!?\.]?\s*$",
            r"^\s*ola\s*[!?\.]?\s*$",
            r"^\s*bom dia\b",
            r"^\s*boa tarde\b",
            r"^\s*boa noite\b",
            r"^\s*tudo bem\b",
            r"^\s*opa\b",
            r"^\s*e ai\b",
            r"^\s*oi,?\s+tudo\s+bem",
            r"^\s*oi,?\s+td\s+bem",
            r"^\s*ola,?\s+tudo\s+bem",
            r"^\s*fala\s+(ai|ae|comigo)",
        ],
    ),
]


# ============================================================
# Funcao publica: classificar
# ============================================================
def classificar(texto: str, tem_anexo: bool = False) -> str:
    """
    Classifica intencao da mensagem.

    Args:
        texto: texto recebido (pode estar vazio se a msg for so anexo)
        tem_anexo: True se veio imagem/documento (forca intent=comprovante)

    Returns:
        Um dos codigos: confirmacao_pagamento | promessa_pagamento |
        pedido_2via_boleto | pedido_acordo | reclamacao | saudacao |
        comprovante | desconhecida
    """
    # Anexo = quase certo que e comprovante (cliente mandando print/pdf)
    if tem_anexo:
        return "comprovante"

    if not texto or not texto.strip():
        return "desconhecida"

    texto_norm = _normalize(texto)

    for intent, patterns in REGRAS:
        for p in patterns:
            if re.search(p, texto_norm):
                return intent

    return "desconhecida"


# ============================================================
# Gerador de resposta HUMANIZADA
# ============================================================
def gerar_resposta(intent: str, contexto_boleto: Optional[dict], ja_falou_hoje: bool = False) -> dict:
    """
    Gera resposta a partir do intent classificado — VERSAO HUMANA.

    Args:
        intent: codigo do intent (saida de classificar)
        contexto_boleto: dict com dados do boleto/inadimplente
        ja_falou_hoje: True se ja enviou mensagem pra esse numero hoje

    Returns:
        {
            "texto": str,
            "escalar_humano": bool,
            "tipo_escalacao": str | None,
            "delay_segundos": float,  # delay simulando digitacao humana
        }
    """
    ctx = contexto_boleto or {}
    apto = ctx.get("unidade") or ctx.get("apto") or "—"
    valor_str = _formatar_valor(ctx.get("valor"))
    venc = ctx.get("vencimento") or "—"
    nome = ctx.get("nome", "").split()[0] if ctx.get("nome") else ""

    # Saudacao: se ja falou hoje, nao repete "Oi" toda hora
    if intent == "saudacao" and ja_falou_hoje:
        intent = "desconhecida"  # transforma em resposta generica amigavel

    # Escolhe variacao aleatoria
    variacoes = RESPOSTAS.get(intent, RESPOSTAS["desconhecida"])
    texto_base = _escolher_variacao(variacoes)

    # Substitui placeholders com dados REAIS do boleto (se disponíveis)
    # Prioridade: contexto > env vars (PIX_CONDOMINIO/LINHA_DIGITAVEL são fallback)
    pix = (
        ctx.get("pix")
        or ctx.get("pix_chave")
        or os.getenv("PIX_CONDOMINIO", "")
    ).strip() or "[PIX - consulte o boleto]"
    
    linha = (
        ctx.get("linha_digitavel")
        or ctx.get("codigo_barras")
        or os.getenv("LINHA_DIGITAVEL_CONDOMINIO", "")
    ).strip() or "[Linha digitavel - consulte o boleto]"
    
    link_boleto = ctx.get("link_boleto") or ctx.get("link_boleto_pdf") or ""

    texto = texto_base.format(
        valor=valor_str,
        vencimento=venc,
        apto=apto,
        pix=pix,
        linha=linha,
        link=("🔗 Link: " + link_boleto + "\n") if link_boleto else "",
        nome=nome or "",
    )

    # Delay natural simulando digitacao
    delay = _delay_natural()

    # Configuracoes de escalacao por intent
    ESCALACAO = {
        "confirmacao_pagamento": (False, None),
        "promessa_pagamento": (False, None),
        "pedido_2via_boleto": (False, None),
        "pedido_acordo": (True, "acordo"),
        "reclamacao": (True, "reclamacao"),
        "saudacao": (False, None),
        "comprovante": (False, None),
        "desconhecida": (True, "desconhecida"),
        "duvida": (False, None),  # ← dúvida NÃO escala, EXPLICA
    }

    escalar, tipo = ESCALACAO.get(intent, (True, "desconhecida"))

    return {
        "texto": texto,
        "escalar_humano": escalar,
        "tipo_escalacao": tipo,
        "delay_segundos": delay,
    }


# ─── Test rapido ───
if __name__ == "__main__":
    exemplos = [
        ("ja paguei", False),
        ("paguei agora", False),
        ("vou pagar amanha", False),
        ("pago dia 20", False),
        ("manda o boleto", False),
        ("qual o valor", False),
        ("linha digitavel", False),
        ("posso parcelar?", False),
        ("tem desconto?", False),
        ("nao devo nada", False),
        ("ja paguei mes passado", False),
        ("esse boleto nao e meu", False),
        ("oi", False),
        ("bom dia", False),
        ("segue", True),
        ("", True),
        ("blabla aleatorio", False),
    ]
    for texto, anexo in exemplos:
        intent = classificar(texto, tem_anexo=anexo)
        resp = gerar_resposta(intent, {"unidade": "0602", "valor": 850.5, "vencimento": "15/05/2026"})
        print(f"\n>>> {texto!r:35} anexo={anexo}")
        print(f"   intent: {intent}")
        print(f"   escalar: {resp['escalar_humano']} ({resp['tipo_escalacao']})")
        print(f"   texto:\n{resp['texto']}")
