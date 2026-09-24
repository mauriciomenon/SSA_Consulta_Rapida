#!/usr/bin/env python3
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

from armazenamento.database_integrity import create_sqlite_backup
from armazenamento.database_lock import database_writer_lock
from utils.robust_logging import get_robust_logger

COUNT_SSA_ROWS_SQL = "SELECT COUNT(*) FROM ssa_table"
DELETE_SSA_ROWS_SQL = "DELETE FROM ssa_table"
logger = get_robust_logger().get_logger(__name__, "maintenance")


def limpar_banco():
    """Limpa completamente o banco de dados"""
    db_path = Path("data/ssas.db")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    backup_path = Path("data") / f"ssas_backup_antes_limpeza_final_{timestamp}.db"

    try:
        with database_writer_lock(str(db_path)):
            if not db_path.exists():
                raise FileNotFoundError(f"Banco nao encontrado: {db_path}")
            if backup_path.exists():
                logger.error(
                    "ERR Backup ja existe e nao sera sobrescrito: %s", backup_path
                )
                return False
            create_sqlite_backup(db_path, backup_path)
            logger.info("OK Backup criado: %s", backup_path)

            with closing(sqlite3.connect(db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute(COUNT_SSA_ROWS_SQL)
                count_before = cursor.fetchone()[0]
                logger.info("INFO Registros antes da limpeza: %s", f"{count_before:,}")

                cursor.execute(DELETE_SSA_ROWS_SQL)
                conn.commit()
                logger.info("INFO Remocao confirmada: %s registros", f"{count_before:,}")
                try:
                    cursor.execute("VACUUM")
                except sqlite3.Error as exc:
                    logger.warning(
                        "Registros removidos; otimizacao VACUUM pendente: %s", exc
                    )
                    return True

                cursor.execute(COUNT_SSA_ROWS_SQL)
                count_after = cursor.fetchone()[0]
                logger.info("INFO Registros apos limpeza: %s", f"{count_after:,}")
                logger.info("OK Banco limpo com sucesso!")

    except Exception as e:
        logger.error("ERR Erro ao limpar banco: %s", e)
        return False

    return True


if __name__ == "__main__":
    limpar_banco()
