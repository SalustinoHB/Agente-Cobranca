"""
conversa_memoria.py — Memória de conversa + aprendizado contextual.

Funcionalidades:
  1. Rastreia histórico completo de intenções por telefone
  2. Detecta padrões: "cliente sempre pede acordo", "já falou sobre X"
  3. Escalação SILENCIOSA: quando não entende, responde educadamente
     e notifica operador SEM o cliente saber
  4. Aprendizado: se o cliente repetir a mesma intenção 2+ vezes,
     prioriza essa intenção na classificação
"""

import os
import json
from datetime import datetime, date
from typing import Optional

from loguru import logger


# Máximo de mensagens no histórico por conversa
MAX_HISTORICO = 20


def extrair_historico(state, telefone: str) -> list[dict]:
    """
    Retorna o histórico de mensagens de um telefone.
    Últimas N mensagens ordenadas da mais antiga pra mais recente.
    """
    try:
        from agente.state import State
        msgs = state.conversas_recentes(limit=MAX_HISTORICO)
        return [m for m in msgs if m.get("phone", "")[-11:] == telefone[-11:]]
    except Exception as e:
        logger.warning(f"[memoria] erro extraindo historico: {e}")
        return []


def detectar_padroes(historico: list[dict]) -> dict:
    """
    Analisa o histórico da conversa e extrai padrões.

    Returns:
        {
            "intencoes_repetidas": list[str],  # intenções que aparecem 2+ vezes
            "ja_pediu_acordo": bool,
            "ja_reclamou": bool,
            "total_interacoes": int,
            "ultima_intencao": str | None,
        }
    """
    if not historico:
        return {
            "intencoes_repetidas": [],
            "ja_pediu_acordo": False,
            "ja_reclamou": False,
            "total_interacoes": 0,
            "ultima_intencao": None,
        }

    intencoes = [m.get("intencao") for m in historico if m.get("intencao")]
    from collections import Counter
    contagem = Counter(intencoes)
    
    return {
        "intencoes_repetidas": [k for k, v in contagem.items() if v >= 2],
        "ja_pediu_acordo": any("acordo" in (i or "") for i in intencoes),
        "ja_reclamou": any("reclamacao" in (i or "") for i in intencoes),
        "total_interacoes": len(historico),
        "ultima_intencao": intencoes[-1] if intencoes else None,
    }


def ajustar_classificacao_por_contexto(
    intent_original: str,
    padroes: dict,
) -> str:
    """
    Ajusta a classificação baseada no histórico.

    Regras:
    - Só ajusta se a intenção original for "desconhecida"
    - Se cliente já pediu acordo antes → vira "pedido_acordo"  
    - Se cliente já reclamou antes → vira "reclamacao"
    - NUNCA modifica intenções que já foram identificadas
    """
    if intent_original != "desconhecida":
        return intent_original

    # Só ajusta se tiver histórico relevante
    if padroes.get("total_interacoes") < 2:
        return intent_original

    # Se já pediu acordo antes, provavelmente é sobre isso
    if padroes.get("ja_pediu_acordo"):
        return "pedido_acordo"
    
    # Se já reclamou antes
    if padroes.get("ja_reclamou"):
        return "reclamacao"

    return intent_original


def gerar_resposta_sem_alerta(intent_original: str) -> str:
    """
    Gera uma resposta educada que não alerta o cliente sobre a escalação.
    Usada quando a IA não entendeu mas quer evitar constrangimento.
    """
    respostas = [
        "Entendi! Vou verificar aqui e te retorno em instantes, ok?",
        "Recebi sua mensagem! Deixa eu dar uma olhada e ja te respondo.",
        "Obrigado pelo contato! Vou checar as informações e volto já.",
        "Certo! Deixa eu consultar aqui rapidinho e te dou um retorno.",
    ]
    import random
    return random.choice(respostas)


class ConversaMemory:
    """
    Gerenciador de memória de conversa.
    Mantém estado em memória + SQLite para consulta rápida.
    """

    def __init__(self, state):
        self.state = state
        self._cache = {}  # telefone -> dict de padrões

    def get_contexto(self, telefone: str) -> dict:
        """
        Retorna contexto completo enriquecido para uma conversa.
        """
        if telefone in self._cache:
            return self._cache[telefone]

        historico = extrair_historico(self.state, telefone)
        padroes = detectar_padroes(historico)
        
        contexto = {
            "telefone": telefone,
            "historico": historico,
            "padroes": padroes,
        }
        self._cache[telefone] = contexto
        return contexto

    def invalidar_cache(self, telefone: str):
        """Limpa cache quando mensagem nova chega."""
        self._cache.pop(telefone, None)


# Factory
_default_memory = None

def get_memory(state=None) -> ConversaMemory:
    """Singleton da memória de conversa."""
    global _default_memory
    if _default_memory is None and state is not None:
        _default_memory = ConversaMemory(state)
    return _default_memory
