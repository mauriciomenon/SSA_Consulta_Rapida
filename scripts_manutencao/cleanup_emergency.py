import shutil
import sqlite3
from datetime import datetime

from utils.robust_logging import get_robust_logger

logger = get_robust_logger().get_logger(__name__, "maintenance")


def _run_cleanup_transaction(
    conn: sqlite3.Connection,
) -> tuple[int, int, int, int, int]:
    cursor = conn.cursor()
    conn.execute("BEGIN IMMEDIATE")

    try:
        # 1. Verificar estado atual
        cursor.execute("SELECT COUNT(*) FROM ssas")
        total_before = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(DISTINCT numero_ssa) FROM ssas WHERE numero_ssa IS NOT NULL AND numero_ssa != ''"
        )
        unique_ssas = cursor.fetchone()[0]

        logger.info("INFO ESTADO ATUAL:")
        logger.info("   Total de registros: %s", f"{total_before:,}")
        logger.info("   SSAs unicas: %s", f"{unique_ssas:,}")
        logger.info("   Duplicatas: %s", f"{total_before - unique_ssas:,}")

        # 2. Criar tabela temporaria com dados unicos
        logger.info("FIX INICIANDO LIMPEZA...")
        cursor.execute("""
        CREATE TABLE ssas_clean AS
        SELECT * FROM ssas
        WHERE id IN (
            SELECT MIN(id)
            FROM ssas
            WHERE numero_ssa IS NOT NULL AND numero_ssa != ''
            GROUP BY numero_ssa
        )
        """)

        # 3. Adicionar registros sem numero de SSA (mas validos)
        cursor.execute("""
        INSERT INTO ssas_clean
        SELECT * FROM ssas
        WHERE (numero_ssa IS NULL OR numero_ssa = '')
        AND (descricao_ssa IS NOT NULL AND descricao_ssa != '')
        AND id NOT IN (SELECT id FROM ssas_clean)
        """)

        # 4. Verificar resultado
        cursor.execute("SELECT COUNT(*) FROM ssas_clean")
        total_clean = cursor.fetchone()[0]
        if total_before > 0 and total_clean <= 0:
            raise RuntimeError(
                "Tabela ssas_clean vazia; abortando operacao destrutiva."
            )

        logger.info("   OK Tabela limpa criada: %s registros", f"{total_clean:,}")
        logger.info("   Removidos: %s duplicatas", f"{total_before - total_clean:,}")

        # 5. Substituir tabela original
        cursor.execute("DROP TABLE ssas")
        cursor.execute("ALTER TABLE ssas_clean RENAME TO ssas")

        # 6. Recriar indices
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_numero_ssa ON ssas(numero_ssa)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_situacao ON ssas(situacao)")

        # 7. Verificar resultado final
        cursor.execute("SELECT COUNT(*) FROM ssas")
        total_after = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(*) FROM ssas WHERE numero_ssa IS NULL OR numero_ssa = ''"
        )
        empty_ssa = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(*) FROM ssas WHERE semana_cadastro IS NULL OR semana_cadastro = '' OR semana_cadastro = '-'"
        )
        empty_week = cursor.fetchone()[0]

        conn.commit()
        return total_before, total_after, total_clean, empty_ssa, empty_week
    except Exception:
        conn.rollback()
        logger.exception("Falha durante limpeza emergencial. Operacao revertida.")
        raise


def _fetch_remaining_dupes() -> list[tuple[str, int]]:
    conn = sqlite3.connect("data/ssas.db")
    try:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT numero_ssa, COUNT(*) as count
        FROM ssas
        WHERE numero_ssa IS NOT NULL AND numero_ssa != ''
        GROUP BY numero_ssa
        HAVING COUNT(*) > 1
        LIMIT 5
        """)
        return cursor.fetchall()
    finally:
        conn.close()


def emergency_cleanup():
    """Limpeza emergencial para remover duplicatas massivas"""

    logger.info("LIMPEZA EMERGENCIAL DO BANCO DE DADOS")
    logger.info("=" * 60)

    # Backup adicional de segurança
    backup_name = (
        f"data/ssas_emergency_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    )
    shutil.copy2("data/ssas.db", backup_name)
    logger.info("OK Backup criado: %s", backup_name)

    conn = sqlite3.connect("data/ssas.db")
    try:
        total_before, total_after, _total_clean, empty_ssa, empty_week = (
            _run_cleanup_transaction(conn)
        )
    finally:
        conn.close()

    logger.info("OK LIMPEZA CONCLUIDA:")
    logger.info("   Registros antes: %s", f"{total_before:,}")
    logger.info("   Registros depois: %s", f"{total_after:,}")
    logger.info("   Removidos: %s", f"{total_before - total_after:,}")
    logger.info("   SSAs sem numero: %s", f"{empty_ssa:,}")
    logger.info("   SSAs sem semana: %s", f"{empty_week:,}")

    # 8. Verificar integridade
    remaining_dupes = _fetch_remaining_dupes()
    if remaining_dupes:
        logger.warning("WARN AINDA EXISTEM DUPLICATAS:")
        for ssa, count in remaining_dupes:
            logger.warning("   SSA %s: %s copias", ssa, count)
    else:
        logger.info("OK NENHUMA DUPLICATA RESTANTE")

    return total_before, total_after


if __name__ == "__main__":
    before, after = emergency_cleanup()
    logger.info("=" * 60)
    logger.info(
        "DONE EMERGENCIA RESOLVIDA: %s duplicatas removidas!", f"{before - after:,}"
    )
    logger.info(
        "FIX Proximo passo: Corrigir o codigo de importacao para evitar futuras duplicatas."
    )
