"""Script de migração incremental para alinhar banco existente ao schema_unified.

Uso:
  python scripts/migracao/migrar_para_unificado.py --db data/ssas.db

Lógica:
  1. Carrega lista de colunas alvo (parse simples do arquivo schema_unified.sql).
  2. Obtém colunas atuais via PRAGMA table_info(ssa_table).
  3. Para cada coluna ausente executa ALTER TABLE ADD COLUMN (tipo TEXT ou INTEGER se nome sugerir numero/semana/contador).
  4. Gera backup automático antes de alterar.
  5. Escreve relatório em logs/migracao_unificado_<timestamp>.log.

Seguro porque:
  - Não remove colunas.
  - Não altera tipos existentes.
  - Apenas adiciona quando ausente.

Limitações:
  - Inferência de tipo é heurística; ajuste manual se necessário.
"""

from __future__ import annotations

import argparse
import re
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path
from typing import List

from armazenamento.identifier_utils import quote_identifier

SCHEMA_PATH = Path("config/schema_unified.sql")
TARGET_TABLE = "ssa_table"

# Heurística básica: nomes que indicam inteiro
INT_HINTS = (
    "semana",
    "numero_",
    "num_",
    "numero_desvios",
    "num_reprogramacoes",
    "num_reprobaciones",
    "id",
)


def infer_type(column_name: str) -> str:
    low = column_name.lower()
    if any(h in low for h in INT_HINTS):
        return "INTEGER"
    return "TEXT"


def parse_target_columns() -> List[str]:
    if not SCHEMA_PATH.exists():
        raise SystemExit(f"Schema unificado não encontrado em {SCHEMA_PATH}")
    content = SCHEMA_PATH.read_text(encoding="utf-8")
    # Extrair bloco CREATE TABLE ssa_table (...)
    m = re.search(
        r"CREATE TABLE IF NOT EXISTS ssa_table \((.*?)\);", content, re.S | re.I
    )
    if not m:
        raise SystemExit(
            "Não foi possível localizar definição de ssa_table no schema_unified.sql"
        )
    block = m.group(1)
    cols = []
    for line in block.splitlines():
        line = line.strip()
        if not line or line.startswith("--"):
            continue
        if line.lower().startswith("id "):
            continue  # ignora PK já existente
        # linha típica: nome_coluna TIPO,
        parts = line.split()
        if not parts:
            continue
        name = parts[0].rstrip(",")
        # evitar duplicar comentários acoplados
        if name.endswith("--"):
            continue
        # ignorar se tem parênteses de constraints (não aplicável aqui)
        cols.append(name)
    return cols


def backup_database(db_path: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    backup_dir = Path("data")
    backup_dir.mkdir(exist_ok=True)
    backup_path = backup_dir / f"ssas.db.backup_before_unified_{ts}"
    try:
        with closing(
            sqlite3.connect(f"{db_path.resolve().as_uri()}?mode=ro", uri=True)
        ) as source_conn:
            with closing(sqlite3.connect(backup_path)) as backup_conn:
                source_conn.backup(backup_conn)
                if backup_conn.execute("PRAGMA quick_check").fetchone() != ("ok",):
                    raise sqlite3.DatabaseError("backup falhou no quick_check")
    except (OSError, sqlite3.Error):
        backup_path.unlink(missing_ok=True)
        raise
    return backup_path


def migrate(db_path: Path) -> None:
    if not db_path.exists():
        raise SystemExit(f"Banco não encontrado: {db_path}")
    target_cols = parse_target_columns()
    quoted_target_table = quote_identifier(TARGET_TABLE)
    with closing(sqlite3.connect(db_path)) as con:
        cur = con.cursor()
        cur.execute(f"PRAGMA table_info({quoted_target_table})")
        existing = [row[1] for row in cur.fetchall()]
        missing = [c for c in target_cols if c not in existing]
        print(
            f"Colunas alvo: {len(target_cols)} | Existentes: {len(existing)} | Ausentes: {len(missing)}"
        )
        if not missing:
            print("Nada a migrar.")
            return
        backup_path = backup_database(db_path)
        print(f"Backup criado: {backup_path}")
        try:
            con.execute("BEGIN")
            for col in missing:
                col_type = infer_type(col)
                quoted_col = quote_identifier(col)
                sql = f"ALTER TABLE {quoted_target_table} ADD COLUMN {quoted_col} {col_type}"
                print("> ", sql)
                cur.execute(sql)
            con.commit()
        except sqlite3.Error:
            con.rollback()
            raise
    print("Migração concluída.")
    # Log
    Path("logs").mkdir(exist_ok=True)
    log_path = (
        Path("logs")
        / f"migracao_unificado_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    )
    with open(log_path, "w", encoding="utf-8") as fh:
        fh.write(f"Missing columns added: {missing}\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="data/ssas.db")
    args = parser.parse_args()
    migrate(Path(args.db))


if __name__ == "__main__":
    main()
