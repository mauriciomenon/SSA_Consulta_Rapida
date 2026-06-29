#!/usr/bin/env python3
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

from utils.robust_logging import get_robust_logger

TABLE_NAME = "ssa_table"
logger = get_robust_logger().get_logger(__name__, "maintenance")


def limpar_banco():
    """Limpa completamente o banco de dados"""
    db_path = Path("data/ssas.db")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = Path("data") / f"ssas_backup_antes_limpeza_final_{timestamp}.db"

    try:
        # Fazer backup se banco existir
        if db_path.exists():
            if backup_path.exists():
                logger.error("ERR Backup ja existe e nao sera sobrescrito: %s", backup_path)
                return False
            shutil.copy2(db_path, backup_path)
            logger.info("OK Backup criado: %s", backup_path)

        # Limpar tabela
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}")
            count_before = cursor.fetchone()[0]
            logger.info("INFO Registros antes da limpeza: %s", f"{count_before:,}")

            cursor.execute(f"DELETE FROM {TABLE_NAME}")
            conn.commit()
            cursor.execute("VACUUM")  # Otimizar o banco

            cursor.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}")
            count_after = cursor.fetchone()[0]
            logger.info("INFO Registros apos limpeza: %s", f"{count_after:,}")
            logger.info("OK Banco limpo com sucesso!")

    except Exception as e:
        logger.error("ERR Erro ao limpar banco: %s", e)
        return False

    return True


if __name__ == "__main__":
    limpar_banco()
