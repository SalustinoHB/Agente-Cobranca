"""
logging_config.py — Configuração centralizada do loguru.

Handlers:
  - stdout (INFO, colorido)
  - arquivo rotativo (DEBUG, 100MB rotação, 30 dias retenção)

Caminho do arquivo:
  1. Tenta /var/log/cobranca/app.log
  2. Se não escreve lá, cai pra ./logs/app.log (relativo ao cwd)

Idempotente: pode ser chamado múltiplas vezes — só monta uma vez.
"""

import os
import sys
from pathlib import Path

from loguru import logger


_SETUP_DONE = False


def _pode_escrever(diretorio: Path) -> bool:
    """True se a pasta existe (ou pode ser criada) e é writeable."""
    try:
        diretorio.mkdir(parents=True, exist_ok=True)
        teste = diretorio / ".write_test"
        teste.touch()
        teste.unlink()
        return True
    except Exception:
        return False


def _resolver_log_path() -> Path:
    """
    Decide onde gravar o log:
      1. LOG_FILE do .env, se setado
      2. /var/log/cobranca/app.log (preferido em produção/Docker)
      3. ./logs/app.log (fallback local)
    """
    env_log = os.getenv("LOG_FILE", "").strip()
    if env_log:
        p = Path(env_log)
        if _pode_escrever(p.parent):
            return p
        # se a pasta do env não escreve, cai no fallback abaixo

    sistema = Path("/var/log/cobranca/app.log")
    if _pode_escrever(sistema.parent):
        return sistema

    local = Path("./logs/app.log").resolve()
    _pode_escrever(local.parent)  # tenta criar; se falhar, loguru reclamará
    return local


def setup_logging(level: str = None, force: bool = False) -> Path:
    """
    Configura loguru com handlers de console + arquivo rotativo.

    Args:
        level: força nível (override de LOG_LEVEL do .env)
        force: reaplica configuração mesmo se já foi feita
    Returns:
        Path do arquivo de log usado
    """
    global _SETUP_DONE
    if _SETUP_DONE and not force:
        return _resolver_log_path()

    log_level = level or os.getenv("LOG_LEVEL", "INFO").upper()
    log_path = _resolver_log_path()

    logger.remove()  # zera handlers default

    # Console (colorido, INFO+ por padrão)
    logger.add(
        sys.stdout,
        level=log_level,
        colorize=True,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
    )

    # Arquivo (DEBUG+ pra ter rastro completo)
    try:
        logger.add(
            str(log_path),
            level="DEBUG",
            rotation="100 MB",
            retention="30 days",
            compression="zip",
            encoding="utf-8",
            enqueue=True,  # safe em multi-thread (APScheduler + FastAPI)
            format=(
                "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
                "{level: <8} | "
                "{name}:{function}:{line} | "
                "{message}"
            ),
        )
        logger.info(f"Logging inicializado | console={log_level} | arquivo={log_path}")
    except Exception as e:
        # Mesmo se o arquivo falhar, o console handler segue funcionando
        logger.warning(f"Falha ao montar handler de arquivo ({log_path}): {e}")

    _SETUP_DONE = True
    return log_path


if __name__ == "__main__":
    path = setup_logging()
    logger.debug("teste debug")
    logger.info(f"Logging OK em: {path}")
    logger.warning("teste warning")
    logger.error("teste error")
