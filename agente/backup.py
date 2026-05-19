"""
backup.py — Backup do SQLite com retenção.

Cópia simples do arquivo com sufixo timestamp. Não para o serviço.
Mantém os últimos N backups (default 30); remove os mais antigos.

Uso via APScheduler diário em main.py:
    sched.add_job(lambda: backup_state(DB_PATH, BACKUP_DIR), 'cron', hour=23)

Também executável standalone:
    python -m agente.backup
"""

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from loguru import logger


def backup_state(
    db_path: str,
    backup_dir: str,
    manter_ultimos: int = 30,
) -> Optional[Path]:
    """
    Faz backup do arquivo SQLite.

    Args:
        db_path: caminho do .db (ex: /data/state.db)
        backup_dir: pasta destino (criada se não existir)
        manter_ultimos: quantos backups manter (default 30)

    Returns:
        Path do backup criado, ou None se falhou.
    """
    src = Path(db_path)
    dst_dir = Path(backup_dir)

    if not src.exists():
        logger.warning(f"backup_state: DB não existe ({src}) — pulando")
        return None

    try:
        dst_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.error(f"backup_state: não consegui criar {dst_dir}: {e}")
        return None

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome = f"{src.stem}_{ts}{src.suffix}"
    dst = dst_dir / nome

    try:
        shutil.copy2(src, dst)
        size_kb = dst.stat().st_size / 1024
        logger.success(f"Backup OK: {dst} ({size_kb:.1f} KB)")
    except Exception as e:
        logger.exception(f"backup_state: falha copiando {src} -> {dst}: {e}")
        return None

    # Retenção
    try:
        _limpar_antigos(dst_dir, src.stem, manter_ultimos)
    except Exception as e:
        logger.warning(f"backup_state: erro na limpeza de antigos: {e}")

    return dst


def _limpar_antigos(diretorio: Path, prefixo: str, manter: int) -> List[Path]:
    """Remove os backups além dos `manter` mais recentes."""
    # Lista backups com o prefixo (state_*.db)
    candidatos = sorted(
        [p for p in diretorio.glob(f"{prefixo}_*.db") if p.is_file()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    removidos = []
    for antigo in candidatos[manter:]:
        try:
            antigo.unlink()
            removidos.append(antigo)
            logger.info(f"Backup antigo removido: {antigo.name}")
        except Exception as e:
            logger.warning(f"Não consegui remover {antigo}: {e}")

    return removidos


def listar_backups(backup_dir: str, prefixo: str = "state") -> List[dict]:
    """Lista backups disponíveis (pra inspeção/CLI)."""
    p = Path(backup_dir)
    if not p.exists():
        return []
    backups = []
    for f in sorted(p.glob(f"{prefixo}_*.db"), key=lambda x: x.stat().st_mtime, reverse=True):
        backups.append({
            "arquivo": f.name,
            "tamanho_kb": round(f.stat().st_size / 1024, 1),
            "criado_em": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
        })
    return backups


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    db = os.getenv("DATABASE_PATH", "./data/state.db")
    bk = os.getenv("BACKUP_DIR", "./data/backups")
    print(f"DB: {db}")
    print(f"Backup dir: {bk}")
    resultado = backup_state(db, bk)
    print(f"Resultado: {resultado}")
    print("\nBackups existentes:")
    for b in listar_backups(bk):
        print(f"  {b['arquivo']:40} {b['tamanho_kb']:>8} KB   {b['criado_em']}")
