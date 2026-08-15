#!/usr/bin/env python3
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

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
        # Fazer backup se banco existir
        if db_path.exists():
            if backup_path.exists():
                logger.error(
                    "ERR Backup ja existe e nao sera sobrescrito: %s", backup_path
                )
                return False
            try:
                with closing(
                    sqlite3.connect(f"{db_path.resolve().as_uri()}?mode=ro", uri=True)
                ) as source_conn:
                    with closing(sqlite3.connect(backup_path)) as backup_conn:
                        source_conn.backup(backup_conn)
                        if backup_conn.execute("PRAGMA quick_check").fetchone() != (
                            "ok",
                        ):
                            raise sqlite3.DatabaseError("backup falhou no quick_check")
            except (OSError, sqlite3.Error):
                backup_path.unlink(missing_ok=True)
                raise
            logger.info("OK Backup criado: %s", backup_path)

        # Limpar tabela
        with closing(sqlite3.connect(db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute(COUNT_SSA_ROWS_SQL)
            count_before = cursor.fetchone()[0]
            logger.info("INFO Registros antes da limpeza: %s", f"{count_before:,}")

            cursor.execute(DELETE_SSA_ROWS_SQL)
            conn.commit()
            cursor.execute("VACUUM")  # Otimizar o banco

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
