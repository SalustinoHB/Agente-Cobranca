"""
respostas_auto.py — Classificação de intenção + geração de resposta automática.

Abordagem híbrida:
  1. Regras por regex/keyword (rápido, determinístico, cobre 80% dos casos).
  2. Fallback opcional via LLM (Claude) — gated por env USE_LLM_FALLBACK=true.
     Por enquanto o stub `_consultar_claude()` retorna None (não chama API real).

Intenções suportadas:
  - ja_paguei              → responde auto (agradece, vai conferir)
  - promessa_pagamento     → responde auto (combina, aguarda)
  - pede_valor             → responde auto (manda valor, se houver contexto)
  - pede_pix               → responde auto (placeholder)
  - pede_2via              → responde auto (vai mandar 2ª via)
  - questiona_cobranca     → ESCALA humano (não responde auto)
  - negociacao             → ESCALA humano
  - fora_topico            → ignora (default)
  - indefinido             → ESCALA humano

Tom: amigável, profissional, PT-BR, primeira pessoa, no máximo 1 emoji por mensagem.
"""

from __future__ import annotations

import os
import re
import unicodedata
from typing import Optional

from loguru import logger


# ============================================================
# Util
# ============================================================
def _normalize(texto: str) -> str:
    """
    Lower + remove acentos + espaços extras.
    Mantém pontuação básica pra os patterns funcionarem.
    """
    if not texto:
        return ""
    t = unicodedata.normalize("NFKD", texto)
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = t.lower().strip()
    t = re.sub(r"\s+", " ", t)
    return t


# ============================================================
# Regras (ordem importa — primeira que casa vence)
# ============================================================
# Cada regra: (intencao, lista_de_padroes_regex). Padrões já normalizados.
# Ordenadas por prioridade — questiona_cobranca antes de ja_paguei pra
# pegar variantes do tipo "ja paguei isso ano passado".
REGRAS = [
    # ── ESCALAR PARA HUMANO (vem primeiro pra ter prioridade) ──
    (
        "questiona_cobranca",
        [
            r"\babsurdo\b",
            r"\berrado\b",
            r"\bnao devo\b",
            r"\bnao deve\b",
            r"\bja paguei (isso |essa |esse )?(ano passado|mes passado|faz tempo|ha (muito )?tempo)\b",
            r"\bdiscordo\b",
            r"\bcobranca indevida\b",
            r"\bcobrar (de )?novo\b",
            r"\bnao reconheco\b",
            r"\bisso (esta )?errado\b",
        ],
    ),
    (
        "negociacao",
        [
            r"\bacordo\b",
            r"\bparcelar\b",
            r"\bparcelamento\b",
            r"\bdesconto\b",
            r"\bnegociar\b",
            r"\bnegociacao\b",
            r"\bdividir em\b",
            r"\bem (\d+) vezes?\b",
        ],
    ),
    # ── JA PAGUEI ──
    (
        "ja_paguei",
        [
            r"\bja paguei\b",
            r"\bpaguei (ja|hoje|ontem|agora|sim)\b",
            r"\bpaguei$\b",
            r"^\s*paguei\b",
            r"\bcomprovante\b",
            r"\bja (esta|ta) pago\b",
            r"\besta pago\b",
            r"^\s*pago\s*$",
            r"\bquitei\b",
            r"\btransferi\b",
            r"\bfiz o pix\b",
            r"\bfiz pix\b",
        ],
    ),
    # ── PROMESSA DE PAGAMENTO ──
    (
        "promessa_pagamento",
        [
            r"\bvou pagar\b",
            r"\bpago (amanha|sexta|segunda|terca|quarta|quinta|sabado|domingo|dia)\b",
            r"\bpago (essa |na |a )?(semana|sexta|segunda|terca|quarta|quinta)\b",
            r"\bpago ate\b",
            r"\bate (sexta|segunda|amanha|terca|quarta|quinta|sabado|domingo|sexta-feira)\b",
            r"\bsemana que vem\b",
            r"\bproxima semana\b",
            r"\bpago no (dia|proximo)\b",
            r"\bdia (\d+)\b",
            r"\bdepois do dia (\d+)\b",
            r"\bso (consigo |posso |dia |no )?\d+\b",
            r"\bpago dia (\d+)\b",
        ],
    ),
    # ── PEDE 2 VIA / BOLETO ──
    (
        "pede_2via",
        [
            r"\b2 ?via\b",
            r"\bsegunda via\b",
            r"\b2a via\b",
            r"\bmanda (o )?boleto\b",
            r"\benviar (o )?boleto\b",
            r"\bme (manda |envia )(o )?boleto\b",
            r"\blinha digitavel\b",
            r"\bcodigo de barras\b",
            r"\bboleto atualizado\b",
            r"\bnovo boleto\b",
        ],
    ),
    # ── PEDE PIX ──
    (
        "pede_pix",
        [
            r"\bpix\b",
            r"\bchave pix\b",
            r"\bqr ?code\b",
            r"\bcomo (eu )?pago\b",
            r"\bcomo posso pagar\b",
            r"\bcomo faco pra pagar\b",
            r"\bcomo faco pra quitar\b",
        ],
    ),
    # ── PEDE VALOR ──
    (
        "pede_valor",
        [
            r"\bqual (o )?valor\b",
            r"\bquanto (e|fica|deu|esta|ta)\b",
            r"\bquanto custa\b",
            r"\bqual (o )?total\b",
            r"\bvalor (atualizado|total|certo)\b",
            r"\bme (passa|fala|diz) o valor\b",
        ],
    ),
]


# ============================================================
# Textos de resposta
# ============================================================
RESPOSTAS = {
    "ja_paguei": (
        "Oi! Obrigado por avisar 🙂\n\n"
        "Vou verificar no sistema da Pratika e te confirmo em breve. "
        "Se tiver o comprovante, pode me mandar aqui que adianta o processo."
    ),
    "promessa_pagamento": (
        "Combinado! Aguardo o pagamento. "
        "Qualquer coisa me avise por aqui."
    ),
    "pede_pix": (
        "Vou te mandar o PIX, um momento."
    ),
    "pede_2via": (
        "Vou te mandar a 2ª via do boleto atualizado. Um momento."
    ),
    # pede_valor é montada dinamicamente com base no contexto
}


def _resposta_pede_valor(contexto: Optional[dict]) -> Optional[str]:
    """Monta a resposta com o valor do boleto (precisa de contexto)."""
    if not contexto:
        return (
            "Vou conferir o valor atualizado no sistema e já te retorno. "
            "Um momento."
        )

    valor = contexto.get("valor")
    venc = contexto.get("vencimento")
    dias = contexto.get("dias_atraso")

    try:
        valor_str = f"R$ {float(valor):.2f}".replace(".", ",") if valor else None
    except Exception:
        valor_str = str(valor) if valor else None

    if valor_str and venc:
        msg = (
            f"O valor atualizado é {valor_str}, com vencimento em {venc}."
        )
        if dias and int(dias) > 0:
            msg += f" Está com {dias} dias de atraso."
        msg += "\n\nQualquer dúvida, me avisa por aqui."
        return msg

    if valor_str:
        return f"O valor é {valor_str}. Qualquer dúvida, me avisa por aqui."

    return "Vou conferir o valor atualizado no sistema e já te retorno. Um momento."


# ============================================================
# LLM fallback (stub)
# ============================================================
def _consultar_claude(phone: str, texto: str, contexto: Optional[dict] = None) -> Optional[dict]:
    """
    Stub do fallback via Claude. Por enquanto retorna None (não chama API real).

    Quando implementado, deve retornar dict no mesmo formato de classificar_e_responder
    ou None se o LLM também não soube classificar.
    """
    logger.debug(f"_consultar_claude (stub) chamado pra {phone}: {texto[:50]!r}")
    return None


# ============================================================
# Função principal
# ============================================================
def classificar_e_responder(
    phone: str,
    texto: str,
    contexto_inadimplente: Optional[dict] = None,
) -> dict:
    """
    Classifica intenção e gera resposta automática.

    Args:
        phone: número do remetente (5584999999999)
        texto: texto recebido pelo WhatsApp
        contexto_inadimplente: dict opcional com dados do boleto/inadimplente
                               { "valor": float, "vencimento": str,
                                 "dias_atraso": int, "nome": str, ... }

    Returns:
        {
            "intencao": str,            # "ja_paguei" | "promessa_pagamento" | ...
            "resposta_texto": str|None, # texto a enviar, None se nao responder
            "acao": str,                # "responder_auto"|"escalar_humano"|"ignorar"
            "confianca": float,         # 0.0 - 1.0
            "log_extra": dict,          # info extra de debug
        }
    """
    log_extra: dict = {"phone": phone, "texto_original": texto}

    if not texto or not texto.strip():
        return {
            "intencao": "fora_topico",
            "resposta_texto": None,
            "acao": "ignorar",
            "confianca": 1.0,
            "log_extra": {**log_extra, "motivo": "texto_vazio"},
        }

    texto_norm = _normalize(texto)
    log_extra["texto_normalizado"] = texto_norm

    # ── Match nas regras ──
    intencao_detectada: Optional[str] = None
    padrao_match: Optional[str] = None
    for intencao, patterns in REGRAS:
        for p in patterns:
            if re.search(p, texto_norm):
                intencao_detectada = intencao
                padrao_match = p
                break
        if intencao_detectada:
            break

    if intencao_detectada:
        log_extra["padrao_match"] = padrao_match
        log_extra["fonte"] = "regra"
        return _construir_resultado(
            intencao_detectada,
            contexto_inadimplente,
            confianca=0.85,
            log_extra=log_extra,
        )

    # ── Fallback LLM (se habilitado) ──
    use_llm = os.getenv("USE_LLM_FALLBACK", "false").lower() == "true"
    if use_llm:
        log_extra["llm_consultado"] = True
        resp_llm = _consultar_claude(phone, texto, contexto_inadimplente)
        if resp_llm:
            resp_llm.setdefault("log_extra", {}).update(log_extra)
            resp_llm["log_extra"]["fonte"] = "llm"
            return resp_llm

    # ── Indefinido: escala humano ──
    log_extra["fonte"] = "fallback_indefinido"
    return {
        "intencao": "indefinido",
        "resposta_texto": None,
        "acao": "escalar_humano",
        "confianca": 0.0,
        "log_extra": log_extra,
    }


def _construir_resultado(
    intencao: str,
    contexto: Optional[dict],
    confianca: float,
    log_extra: dict,
) -> dict:
    """Monta o dict de retorno a partir da intenção detectada."""

    # Casos que escalam pra humano (não responde auto)
    if intencao in ("questiona_cobranca", "negociacao"):
        return {
            "intencao": intencao,
            "resposta_texto": None,
            "acao": "escalar_humano",
            "confianca": confianca,
            "log_extra": log_extra,
        }

    # Casos com resposta automática
    if intencao == "pede_valor":
        resposta = _resposta_pede_valor(contexto)
    else:
        resposta = RESPOSTAS.get(intencao)

    if not resposta:
        # Detectou intenção mas não tem template — escala
        return {
            "intencao": intencao,
            "resposta_texto": None,
            "acao": "escalar_humano",
            "confianca": confianca * 0.5,
            "log_extra": {**log_extra, "motivo": "sem_template"},
        }

    return {
        "intencao": intencao,
        "resposta_texto": resposta,
        "acao": "responder_auto",
        "confianca": confianca,
        "log_extra": log_extra,
    }


# ─── Test rápido ───
if __name__ == "__main__":
    exemplos = [
        "ja paguei",
        "vou pagar amanha",
        "qual o valor?",
        "manda o pix",
        "me manda a 2 via",
        "isso esta errado, nao devo",
        "quero parcelar",
        "blabla qualquer coisa",
    ]
    for ex in exemplos:
        r = classificar_e_responder("5584999999999", ex)
        print(f"\n>>> {ex!r}")
        print(f"   intencao: {r['intencao']}")
        print(f"   acao:     {r['acao']}")
        print(f"   resposta: {r['resposta_texto']}")
