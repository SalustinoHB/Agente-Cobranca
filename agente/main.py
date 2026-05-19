"""
main.py — Orquestrador. Entry point do agente em produção.

Roda como serviço Docker. APScheduler agenda:
  - 07:00 → scraper (atualiza base)
  - 08:00 → régua (envia mensagens do dia)
  - 18:30 → relatório diário

Argumentos CLI:
  python -m agente.main                # modo serviço (loop com scheduler)
  python -m agente.main --once         # roda 1 ciclo da régua e sai
  python -m agente.main --dry-run      # força DRY-RUN no ciclo
  python -m agente.main --scraper      # roda só scraper

Comandos CLI avançados:
  python -m agente.main --relatorio    # mostra relatório completo
  python -m agente.main --status       # verificação rápida
  python -m agente.main --enviar-teste <numero> # testa envio
  python -m agente.main --blacklist [list|add|remove] <numero> # gerencia blacklist
"""

import os
import sys
import signal
from datetime import datetime

from loguru import logger
from dotenv import load_dotenv
from apscheduler.schedulers.blocking import BlockingScheduler

from agente.state import State
from agente.sender import make_sender
from agente.logging_config import setup_logging
from agente.backup import backup_state
from agente import regua, scraper


# ─── Setup ───

load_dotenv()


def configurar_logs():
    """Wrapper retro-compatível — delega pra agente.logging_config."""
    setup_logging()


def criar_dependencias():
    state = State(os.getenv("DATABASE_PATH", "/data/state.db"))
    sender = make_sender()
    return state, sender


# ─── Jobs ───

def job_scraper():
    logger.info("⏰ [07:00] Job scraper iniciado")
    try:
        url = os.getenv("SUPERLOGICA_URL", "https://admin109865.superlogica.net")
        cookies = os.getenv("COOKIES_PATH", "/data/superlogica_cookies.json")
        condominio_id = int(os.getenv("SUPERLOGICA_CONDOMINIO_ID", "14"))
        lote = os.getenv("SUPERLOGICA_LOTE_MES", "auto")
        base_out = os.getenv("BASE_JSON_PATH", "/data/renaissance.json")
        contatos = "/data/contatos.json"

        state, _ = criar_dependencias()
        run_id = state.registrar_scraper_inicio()

        boletos = scraper.coletar_boletos(url, cookies, condominio_id, lote, headless=True)
        boletos = scraper.cruzar_com_contatos(boletos, contatos)
        scraper.salvar_base(boletos, base_out)

        state.registrar_scraper_fim(run_id, sucesso=True, boletos=len(boletos))
        logger.success(f"✅ Scraper OK: {len(boletos)} boletos atualizados")

    except Exception as e:
        logger.exception(f"❌ Job scraper falhou: {e}")


def job_regua():
    logger.info("⏰ [08:00] Job régua iniciado")
    try:
        state, sender = criar_dependencias()
        resultado = regua.executar(
            base_path=os.getenv("BASE_JSON_PATH", "/data/renaissance.json"),
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
        logger.success(f"✅ Régua OK: {resultado}")

    except Exception as e:
        logger.exception(f"❌ Job régua falhou: {e}")


def job_backup():
    """Job diário 23h: backup do state.db com retenção 30 dias."""
    logger.info("⏰ [23:00] Job backup iniciado")
    try:
        db_path = os.getenv("DATABASE_PATH", "/data/state.db")
        backup_dir = os.getenv("BACKUP_DIR", "/data/backups")
        backup_state(db_path, backup_dir, manter_ultimos=30)
    except Exception as e:
        logger.exception(f"❌ Job backup falhou: {e}")


def job_relatorio_diario():
    logger.info("⏰ [18:30] Job relatório diário")
    try:
        state, _ = criar_dependencias()
        resumo = state.resumo_diario()
        recentes = state.envios_recentes(limit=50)

        logger.info("=" * 60)
        logger.info(f"📊 RESUMO DO DIA — {datetime.now().strftime('%d/%m/%Y')}")
        logger.info(f"   Enviados (real):  {resumo.get('enviados') or 0}")
        logger.info(f"   Falhas:           {resumo.get('falhas') or 0}")
        logger.info(f"   DRY-RUN:          {resumo.get('dry_run') or 0}")
        logger.info("=" * 60)

        # TODO: enviar pra Murilo via email/whatsapp

    except Exception as e:
        logger.exception(f"❌ Job relatório falhou: {e}")


# ═══════════════════════════════════════════════════════════════
# CLI AVANÇADO (inspirado em agente_natal/main.py)
# ═══════════════════════════════════════════════════════════════

def _box(title: str, lines: list[str], width: int = 58) -> str:
    """Desenha caixa ASCII estilizada."""
    BOX_H = "─"
    BOX_V = "│"
    BOX_TL = "┌"
    BOX_TR = "┐"
    BOX_BL = "└"
    BOX_BR = "┘"
    BOX_L = "├"
    BOX_R = "┤"
    out = []
    out.append(f"{BOX_TL}{BOX_H * (width - 2)}{BOX_TR}")
    out.append(f"{BOX_V} {title:<{width - 4}} {BOX_V}")
    out.append(f"{BOX_L}{BOX_H * (width - 2)}{BOX_R}")
    for line in lines:
        text = line[:width - 4]
        out.append(f"{BOX_V} {text:<{width - 4}} {BOX_V}")
    out.append(f"{BOX_BL}{BOX_H * (width - 2)}{BOX_BR}")
    return "\n".join(out)


def _sep(char: str = "═", width: int = 60) -> str:
    return char * width


def cmd_relatorio():
    """Mostra relatório completo no terminal."""
    state, sender = criar_dependencias()

    print(_sep())
    print("  📊 RELATÓRIO DO AGENTE DE COBRANÇA — RENAISSANCE")
    print(_sep())

    # Status Z-API
    print()
    zapi_lines = []
    try:
        conectado = sender.esta_conectado()
        status = "🟢 CONECTADO" if conectado else "🔴 DESCONECTADO"
        zapi_lines.append(f"WhatsApp: {status}")
        try:
            info = sender.status_instancia()
            zapi_lines.append(f"Número: {info.get('number', 'N/A')}")
        except:
            pass
    except Exception as e:
        zapi_lines.append(f"Erro: {e}")

    print(_box("📡 CONEXÃO", zapi_lines))

    # Estatísticas
    print()
    db_lines = []
    try:
        db_lines.append(f"Total envios: {state.total_envios()}")
        db_lines.append(f"Envios hoje: {state.enviados_hoje()}")
        db_lines.append(f"Blacklist: {state.total_blacklist()}")
    except Exception as e:
        db_lines.append(f"Erro: {e}")

    print(_box("📁 BANCO DE DADOS", db_lines))

    # Base
    print()
    base_lines = []
    try:
        base_path = os.getenv("BASE_JSON_PATH", "/data/renaissance.json")
        boletos = regua.carregar_base(base_path)
        inadimplentes = [b for b in boletos if b.get("status", "").lower() not in ("pago", "baixado", "quitado")]
        com_whatsapp = [b for b in inadimplentes if b.get("whatsapp")]
        sem_whatsapp = [b for b in inadimplentes if not b.get("whatsapp")]
        atrasados = [b for b in inadimplentes if b.get("dias_atraso", 0) > 0]

        base_lines.append(f"Total boletos: {len(boletos)}")
        base_lines.append(f"Inadimplentes: {len(inadimplentes)}")
        base_lines.append(f"  → Com WhatsApp: {len(com_whatsapp)}")
        base_lines.append(f"  → Sem WhatsApp: {len(sem_whatsapp)}")
        base_lines.append(f"  → Em atraso: {len(atrasados)}")

        if atrasados:
            top5 = sorted(atrasados, key=lambda x: x.get("dias_atraso", 0), reverse=True)[:5]
            base_lines.append("")
            base_lines.append("TOP 5 ATRASOS:")
            for b in top5:
                dias = b.get("dias_atraso", 0)
                nome = b.get("nome", "N/A")[:20]
                unid = b.get("unidade", "N/A")
                base_lines.append(f"  {dias:3d} dias — {nome} ({unid})")

    except Exception as e:
        base_lines.append(f"Erro: {e}")

    print(_box("📋 BASE DE BOLETOS", base_lines))
    print()
    print(_sep("─"))
    print("  Use --once pra rodar a régua")
    print("  Use --enviar-teste <numero> pra testar")
    print(_sep("─"))


def cmd_status():
    """Verificação rápida."""
    print(_sep())
    print("  🔍 STATUS DO SISTEMA")
    print(_sep())

    checks = []
    checks.append((".env Z-API", bool(os.getenv("ZAPI_INSTANCE_URL") and os.getenv("ZAPI_TOKEN"))))
    checks.append(("Base boletos", os.path.exists(os.getenv("BASE_JSON_PATH", "/data/renaissance.json"))))
    checks.append(("Banco SQLite", os.path.exists(os.getenv("DATABASE_PATH", "/data/state.db"))))
    try:
        _, sender = criar_dependencias()
        checks.append(("Z-API conectado", sender.esta_conectado()))
    except:
        checks.append(("Z-API conectado", False))

    for label, ok in checks:
        icon = "✅" if ok else "❌"
        print(f"  {icon} {label:<25} {'OK' if ok else 'FALHA'}")
    print(_sep("─"))


def cmd_enviar_teste(numero: str, texto: str):
    """Envia mensagem de teste."""
    print(_sep())
    print("  📤 TESTE DE ENVIO")
    print(_sep())

    _, sender = criar_dependencias()
    numero_norm = sender.normalizar_numero(numero)
    print(f"Número: {numero} → {numero_norm}")
    print(f"Backend: {sender.nome_backend}")
    print(f"Dry-run: {'SIM' if sender.dry_run else 'NÃO'}")
    print()

    if not sender.dry_run:
        confirm = input("Enviar DE VERDADE? [s/N]: ").strip().lower()
        if confirm not in ("s", "sim"):
            print("❌ Cancelado")
            return

    resultado = sender.enviar_texto(numero, texto, delay_ms=1500)
    if resultado["sucesso"]:
        print(f"✅ Enviado! ID: {resultado['message_id']}")
    else:
        print(f"❌ Falha: {resultado['erro']}")


def cmd_blacklist(action: str, numero: str = None):
    """Gerencia blacklist."""
    state, _ = criar_dependencias()
    print(_sep())
    print("  🚫 BLACKLIST")
    print(_sep())

    if action == "list":
        nums = state.listar_blacklist()
        print(f"Total: {len(nums)}")
        for n in nums:
            print(f"  → {n}")
    elif action in ("add", "+") and numero:
        state.adicionar_blacklist(numero, "Manual CLI")
        print(f"✅ Adicionado: {numero}")
    elif action in ("remove", "rm", "-") and numero:
        state.remover_blacklist(numero)
        print(f"✅ Removido: {numero}")
    else:
        print("Uso: --blacklist [list|add|remove] <numero>")


# ─── Service ───

def rodar_servico():
    # Logs centralizados (idempotente)
    setup_logging()
    logger.info("🚀 Iniciando agente em modo serviço")

    estado_inicial = "DRY-RUN" if os.getenv("ENVIAR_DE_VERDADE", "false").lower() != "true" else "ENVIO REAL"
    logger.warning(f"🚦 ESTADO: {estado_inicial}")

    tz = os.getenv("TZ", "America/Fortaleza")
    sched = BlockingScheduler(timezone=tz)

    sched.add_job(job_scraper, "cron", hour=7, minute=0, id="scraper",
                  misfire_grace_time=900)
    sched.add_job(job_regua, "cron", hour=8, minute=0, id="regua",
                  misfire_grace_time=900)
    sched.add_job(job_relatorio_diario, "cron", hour=18, minute=30, id="relatorio",
                  misfire_grace_time=900)
    sched.add_job(job_backup, "cron", hour=23, minute=0, id="backup",
                  misfire_grace_time=3600)

    logger.info("Jobs agendados:")
    for job in sched.get_jobs():
        logger.info(f"   {job.id}: {job.trigger}")

    # Graceful shutdown
    def shutdown(sig, frame):
        logger.warning(f"Sinal recebido ({sig}), parando scheduler...")
        sched.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    sched.start()


# ─── CLI ───

if __name__ == "__main__":
    setup_logging()

    # ─── Comandos rápidos (não iniciam scheduler) ───
    if "--relatorio" in sys.argv:
        cmd_relatorio()

    elif "--status" in sys.argv:
        cmd_status()

    elif "--enviar-teste" in sys.argv:
        idx = sys.argv.index("--enviar-teste")
        numero = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else input("Número: ")
        texto = sys.argv[idx + 2] if idx + 2 < len(sys.argv) else input("Texto: ")
        cmd_enviar_teste(numero, texto)

    elif "--blacklist" in sys.argv:
        idx = sys.argv.index("--blacklist")
        action = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else "list"
        numero = sys.argv[idx + 2] if idx + 2 < len(sys.argv) else None
        cmd_blacklist(action, numero)

    elif "--scraper" in sys.argv:
        job_scraper()

    elif "--once" in sys.argv:
        force_dry = "--dry-run" in sys.argv
        state, sender = criar_dependencias()
        if force_dry:
            sender.dry_run = True
        resultado = regua.executar(
            base_path=os.getenv("BASE_JSON_PATH", "/data/renaissance.json"),
            state=state,
            sender=sender,
            forcar=True,
            dry_run=sender.dry_run,
        )
        logger.info(f"Resultado: {resultado}")

    else:
        rodar_servico()
