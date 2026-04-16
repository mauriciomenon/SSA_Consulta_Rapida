"""Schema manager for dynamic column addition."""

import logging
import sqlite3

import pandas as pd

from .identifier_utils import is_valid_identifier, quote_identifier

logger = logging.getLogger(__name__)

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

    # Add missing columns
    for col in missing_cols:
        if not is_valid_identifier(col):
            raise ValueError(f"Invalid SQL identifier for column: {col}")

        # Infer type from DataFrame
        dtype = df[col].dtype

        if pd.api.types.is_integer_dtype(dtype):
            sql_type = "INTEGER"
        elif pd.api.types.is_float_dtype(dtype):
            sql_type = "REAL"
        elif pd.api.types.is_bool_dtype(dtype):
            sql_type = "INTEGER"
        elif pd.api.types.is_datetime64_any_dtype(dtype):
            sql_type = "TEXT"
        else:
            sql_type = "TEXT"

        try:
            quoted_col = quote_identifier(col)
            cursor.execute(
                f"ALTER TABLE {quoted_table_name} ADD COLUMN {quoted_col} {sql_type}"
            )
            logger.info(f"[OK] Coluna adicionada: {col} ({sql_type})")
        except sqlite3.OperationalError as e:
            if "duplicate column name" not in str(e).lower():
                logger.error(f"[ERRO] Falha ao adicionar coluna {col}: {e}")
                raise

    conn.commit()
