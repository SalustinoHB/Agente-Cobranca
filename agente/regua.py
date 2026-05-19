"""
regua.py — Motor da régua de cobrança.

Lê base de boletos (renaissance.json),
calcula dias de atraso pra cada um,
decide qual etapa aplicar hoje,
delega envio pro sender (com state.py garantindo idempotência).
"""

import json
import os
import time
from datetime import date, datetime
from typing import List
from pathlib import Path

from loguru import logger
from dateutil import parser as dateparser

from agente.templates import renderizar
from agente.state import State
from agente.sender import BaseSender, make_sender


def _parse_data(s: str) -> date:
    """Aceita 'DD/MM/YYYY', 'YYYY-MM-DD', etc."""
    if isinstance(s, date):
        return s
    return dateparser.parse(s, dayfirst=True).date()


def _calcular_dias_atraso(vencimento: str, hoje: date = None) -> int:
    """
    Negativo = vence no futuro (-3 = vence em 3 dias)
    Zero    = vence hoje
    Positivo = atraso (7 = 7 dias atrasado)
    """
    hoje = hoje or date.today()
    venc = _parse_data(vencimento)
    return (hoje - venc).days


def carregar_base(caminho: str) -> List[dict]:
    """Carrega lista de boletos de renaissance.json."""
    if not Path(caminho).exists():
        logger.warning(f"Base não existe: {caminho}")
        return []

    with open(caminho, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Aceita tanto lista direta quanto {"boletos": [...]}
    boletos = data if isinstance(data, list) else data.get("boletos", [])
    logger.info(f"Base carregada: {len(boletos)} boletos")
    return boletos


def filtrar_para_envio_hoje(
    boletos: List[dict],
    state: State,
    hoje: date = None,
) -> List[dict]:
    """
    Pra cada boleto:
    1. Calcula dias_atraso
    2. Determina etapa pra hoje
    3. Skip se: pago / na blacklist / já enviou essa etapa / sem whatsapp
    """
    hoje = hoje or date.today()
    candidatos = []

    for boleto in boletos:
        # Skip pagos
        if boleto.get("status", "").lower() in ("pago", "baixado", "quitado"):
            continue

        # Sem whatsapp
        if not boleto.get("whatsapp"):
            logger.debug(f"Skip (sem whatsapp): {boleto.get('nome')}")
            continue

        # Blacklist
        if state.esta_na_blacklist(boleto["whatsapp"]):
            logger.info(f"Skip (blacklist): {boleto['nome']}")
            continue

        # Calcula etapa pra hoje
        dias = _calcular_dias_atraso(boleto["vencimento"], hoje)
        boleto["dias_atraso"] = dias

        resultado = renderizar(boleto, seed=boleto.get("boleto_id"))
        if not resultado["deve_enviar"]:
            continue  # fora dos pontos da régua

        # Já enviou essa etapa?
        boleto_id = boleto.get("id") or boleto.get("boleto_id") or boleto.get("recibo_id")
        if not boleto_id:
            logger.warning(f"Boleto sem ID: {boleto.get('nome')} — skip")
            continue

        if state.ja_enviado(str(boleto_id), resultado["etapa_codigo"]):
            logger.debug(f"Skip (já enviado): {boleto['nome']} {resultado['etapa_codigo']}")
            continue

        candidatos.append({
            "boleto": boleto,
            "resultado": resultado,
        })

    return candidatos


def janela_horaria_valida(
    horario_inicio: str,
    horario_fim: str,
    enviar_sab: bool,
    enviar_dom: bool,
    agora: datetime = None,
) -> tuple:
    """
    Retorna (valida: bool, motivo: str).
    """
    agora = agora or datetime.now()

    # Fim de semana
    dow = agora.weekday()  # 0=segunda, 6=domingo
    if dow == 5 and not enviar_sab:
        return False, "sábado"
    if dow == 6 and not enviar_dom:
        return False, "domingo"

    # Horário
    inicio = datetime.strptime(horario_inicio, "%H:%M").time()
    fim = datetime.strptime(horario_fim, "%H:%M").time()
    if not (inicio <= agora.time() <= fim):
        return False, f"fora do horário ({horario_inicio}-{horario_fim})"

    return True, "ok"


def executar(
    base_path: str,
    state: State,
    sender: BaseSender,
    intervalo_segundos: int = 180,
    soft_cap: int = 50,
    horario_inicio: str = "09:00",
    horario_fim: str = "18:00",
    enviar_sab: bool = False,
    enviar_dom: bool = False,
    dry_run: bool = True,
    forcar: bool = False,
) -> dict:
    """
    Executa um ciclo da régua.

    Retorna: { enviados, falhas, skipped, candidatos_total, motivo_skip }
    """
    logger.info("=" * 60)
    logger.info(f"🚀 Executando régua | dry_run={dry_run} | forcar={forcar}")

    # 1. Janela horária (a menos que forcar=True)
    if not forcar:
        valida, motivo = janela_horaria_valida(
            horario_inicio, horario_fim, enviar_sab, enviar_dom
        )
        if not valida:
            logger.warning(f"⛔ Fora da janela: {motivo} — abortando")
            return {"abortado": True, "motivo": motivo, "enviados": 0}

    # 2. Carrega base
    boletos = carregar_base(base_path)
    if not boletos:
        logger.warning("Base vazia")
        return {"abortado": True, "motivo": "base_vazia", "enviados": 0}

    # 3. Filtra candidatos pra hoje
    candidatos = filtrar_para_envio_hoje(boletos, state)
    logger.info(f"📋 Candidatos pra envio hoje: {len(candidatos)}")

    if not candidatos:
        return {"enviados": 0, "falhas": 0, "candidatos_total": 0}

    # 4. Soft-cap diário (em modo real)
    if not dry_run:
        ja_enviados_hoje = state.enviados_hoje()
        if ja_enviados_hoje + len(candidatos) > soft_cap:
            logger.warning(
                f"⚠️ Soft-cap diário atingido: {ja_enviados_hoje} enviados + "
                f"{len(candidatos)} pendentes = {ja_enviados_hoje + len(candidatos)} > {soft_cap}"
            )
            # Trunca pra não passar do cap
            espaco = max(0, soft_cap - ja_enviados_hoje)
            candidatos = candidatos[:espaco]
            logger.warning(f"   Reduzindo pra {len(candidatos)} envios neste ciclo")

    # 5. Envia um por um com intervalo
    enviados = 0
    falhas = 0

    for i, item in enumerate(candidatos, 1):
        boleto = item["boleto"]
        resultado = item["resultado"]

        logger.info(
            f"[{i}/{len(candidatos)}] {resultado['etapa_codigo']} → "
            f"{boleto['nome']} ({boleto.get('unidade', 'sem unidade')})"
        )

        # Adiciona whatsapp no dict pra registro
        boleto["whatsapp"] = boleto.get("whatsapp", "")

        envio = sender.enviar_texto(
            numero_whatsapp=boleto["whatsapp"],
            texto=resultado["texto"],
        )

        state.registrar_envio(
            boleto=boleto,
            etapa_codigo=resultado["etapa_codigo"],
            etapa_descricao=resultado["etapa_descricao"],
            texto=resultado["texto"],
            dry_run=dry_run,
            sucesso=envio["sucesso"],
            evolution_message_id=envio["message_id"],
            evolution_response=str(envio["raw_response"])[:500],
            erro=envio["erro"],
        )

        if envio["sucesso"]:
            enviados += 1
        else:
            falhas += 1

        # Intervalo (não no último)
        if i < len(candidatos) and not dry_run:
            logger.info(f"⏳ Aguardando {intervalo_segundos}s antes do próximo envio...")
            time.sleep(intervalo_segundos)

    logger.info("=" * 60)
    logger.success(f"✅ Ciclo completo: {enviados} enviados, {falhas} falhas")

    return {
        "enviados": enviados,
        "falhas": falhas,
        "candidatos_total": len(candidatos),
        "dry_run": dry_run,
    }


# ─── CLI ───
if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv

    load_dotenv()

    state = State(os.getenv("DATABASE_PATH", "./data/state.db"))
    sender = make_sender()

    # Simulação (sempre dry-run, sem horário restrito)
    if "--simular" in sys.argv:
        sender.dry_run = True
        resultado = executar(
            base_path=os.getenv("BASE_JSON_PATH", "./data/renaissance.json"),
            state=state,
            sender=sender,
            dry_run=True,
            forcar=True,
        )
        print("\n📊 Resultado simulação:", resultado)
    else:
        resultado = executar(
            base_path=os.getenv("BASE_JSON_PATH", "./data/renaissance.json"),
            state=state,
            sender=sender,
            intervalo_segundos=int(os.getenv("INTERVALO_ENTRE_ENVIOS_SEGUNDOS", "180")),
            soft_cap=int(os.getenv("SOFT_CAP_DIARIO", "50")),
            horario_inicio=os.getenv("HORARIO_INICIO_ENVIO", "09:00"),
            horario_fim=os.getenv("HORARIO_FIM_ENVIO", "18:00"),
            enviar_sab=os.getenv("ENVIAR_SABADO", "false").lower() == "true",
            enviar_dom=os.getenv("ENVIAR_DOMINGO", "false").lower() == "true",
            dry_run=sender.dry_run,
        )
        print("\n📊 Resultado:", resultado)
