"""
escalacao.py — Sistema de escalonamento humano.

Quando o bot decide escalar (pedido_acordo, reclamacao, comprovante_invalido,
intent desconhecido), este modulo:

  1. Marca a conversa como escalada no SQLite (via State.marcar_conversa_escalada).
  2. Envia uma notificacao via WhatsApp pro operador (OPERADOR_WHATSAPP no .env).

A notificacao usa o mesmo sender ja configurado (Z-API/Baileys/Dryrun).
Em caso de falha no envio da notificacao, NAO levanta excecao — apenas loga.
A escalacao no banco continua valida e o operador pode ver via dashboard.
"""

from __future__ import annotations

import os
from typing import Optional

from loguru import logger

from agente.sender import make_sender


def _operador_numero() -> Optional[str]:
    """Le OPERADOR_WHATSAPP do .env. Retorna None se nao configurado."""
    n = (os.getenv("OPERADOR_WHATSAPP", "") or "").strip()
    return n or None


def _montar_mensagem(
    telefone: str,
    nome: Optional[str],
    apto: Optional[str],
    motivo: str,
    ultima_mensagem: str,
) -> str:
    """Monta o texto da notificacao pro operador."""
    nome_safe = nome or "(sem nome)"
    apto_safe = apto or "—"
    msg_safe = (ultima_mensagem or "(sem texto)").strip()
    if len(msg_safe) > 500:
        msg_safe = msg_safe[:500] + "..."

    return (
        "🚨 Cobrança Pratika - Escalação\n\n"
        f"Inadimplente: {nome_safe} (apto {apto_safe})\n"
        f"WhatsApp: {telefone}\n"
        f"Motivo: {motivo}\n\n"
        "Última mensagem do cliente:\n"
        f'"{msg_safe}"\n\n'
        f"Por favor, responde diretamente pro {nome_safe}."
    )


def escalar_humano(
    telefone: str,
    nome: Optional[str],
    motivo: str,
    ultima_mensagem: str,
    apto: Optional[str] = None,
    state=None,
) -> dict:
    """
    Escala conversa pra humano:
      - Marca no SQLite (se state for passado)
      - Notifica operador via WhatsApp

    Args:
        telefone: numero do cliente (5584999999999)
        nome: nome do cliente (opcional)
        motivo: descricao curta (ex: "pedido_acordo", "reclamacao",
                "comprovante_invalido", "desconhecida")
        ultima_mensagem: ultima msg recebida do cliente
        apto: unidade/apto (opcional)
        state: instancia de State (opcional; se None, nao marca banco)

    Returns:
        {
            "notificou_operador": bool,
            "operador_message_id": str | None,
            "erro": str | None,
        }
    """
    resultado = {
        "notificou_operador": False,
        "operador_message_id": None,
        "erro": None,
    }

    # 1. Marca conversa no banco
    if state is not None:
        try:
            state.marcar_conversa_escalada(telefone, motivo=motivo)
        except Exception as e:
            logger.exception(f"[escalacao] erro marcando conversa: {e}")
            resultado["erro"] = f"db: {e}"

    # 2. Notifica operador
    operador = _operador_numero()
    if not operador:
        logger.warning("[escalacao] OPERADOR_WHATSAPP nao configurado — sem notificacao")
        resultado["erro"] = (resultado["erro"] or "") + " | sem_operador_configurado"
        return resultado

    texto = _montar_mensagem(telefone, nome, apto, motivo, ultima_mensagem)

    try:
        sender = make_sender()
        envio = sender.enviar_texto(numero_whatsapp=operador, texto=texto)
        resultado["notificou_operador"] = bool(envio.get("sucesso"))
        resultado["operador_message_id"] = envio.get("message_id")
        if not envio.get("sucesso"):
            erro_envio = envio.get("erro", "?")
            logger.error(f"[escalacao] falha notificando operador: {erro_envio}")
            resultado["erro"] = (resultado["erro"] or "") + f" | envio: {erro_envio}"
        else:
            logger.success(
                f"[escalacao] operador {operador} notificado sobre {telefone} "
                f"(motivo={motivo})"
            )
    except Exception as e:
        logger.exception(f"[escalacao] erro enviando notificacao: {e}")
        resultado["erro"] = (resultado["erro"] or "") + f" | exc: {e}"

    return resultado


# ─── Test rapido ───
if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()

    r = escalar_humano(
        telefone="5584999999999",
        nome="João Teste",
        motivo="pedido_acordo",
        ultima_mensagem="Posso parcelar em 3x?",
        apto="0602",
    )
    print(f"Resultado: {r}")
