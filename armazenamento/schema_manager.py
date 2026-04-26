"""Schema manager for dynamic column addition."""

import sqlite3

import pandas as pd

from utils.robust_logging import get_robust_logger

from .database_upsert_logic import infer_sql_type
from .identifier_utils import is_valid_identifier, quote_identifier

logger = get_robust_logger().get_logger(__name__, "core")

def ensure_columns_exist(
    conn: sqlite3.Connection, table_name: str, df: pd.DataFrame
) -> None:
    """
    Ensure all DataFrame columns exist in the table.

    Adds missing columns dynamically with appropriate types.
    If table doesn't exist yet, does nothing (will be created by to_sql).

    Args:
        conn: Database connection
        table_name: Name of table
        df: DataFrame with columns to check
    """
    cursor = conn.cursor()

    # Check if table exists
    if not is_valid_identifier(table_name):
        raise ValueError(f"Invalid SQL identifier for table: {table_name}")
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    )
    if not cursor.fetchone():
        # Table doesn't exist yet, will be created by to_sql
        return

    # Get existing columns
    quoted_table_name = quote_identifier(table_name)
    cursor.execute(f"PRAGMA table_info({quoted_table_name})")
    existing_cols = {row[1] for row in cursor.fetchall()}

    # Find missing columns
    df_cols = set(df.columns)
    missing_cols = df_cols - existing_cols

    if not missing_cols:
        return

    savepoint_name = "schema_manager_ensure_columns"
    savepoint_active = False
    try:
        conn.execute(f"SAVEPOINT {savepoint_name}")
        savepoint_active = True
        # Add missing columns
        for col in missing_cols:
            if not is_valid_identifier(col):
                raise ValueError(f"Invalid SQL identifier for column: {col}")

            sql_type = infer_sql_type(df[col])

            quoted_col = quote_identifier(col)
            try:
                cursor.execute(
                    f"ALTER TABLE {quoted_table_name} ADD COLUMN {quoted_col} {sql_type}"
                )
                logger.info(f"[OK] Coluna adicionada: {col} ({sql_type})")
            except sqlite3.OperationalError as e:
                if "duplicate column name" not in str(e).lower():
                    logger.error(f"[ERRO] Falha ao adicionar coluna {col}: {e}")
                    raise
        conn.execute(f"RELEASE SAVEPOINT {savepoint_name}")
        savepoint_active = False
    except (sqlite3.Error, ValueError):
        if savepoint_active:
            conn.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name}")
            conn.execute(f"RELEASE SAVEPOINT {savepoint_name}")
        raise
