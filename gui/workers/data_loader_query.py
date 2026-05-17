"""SQL query fragments for the data loader."""

from __future__ import annotations

import re

SQL_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def build_default_ui_order_clause(sort_spec: tuple[dict, ...]) -> str:
    clause_parts = []
    for rule in sort_spec:
        raw_column = str(rule["column"])
        if not SQL_IDENTIFIER_RE.fullmatch(raw_column):
            raise ValueError(f"Coluna de ordenacao default invalida: {raw_column}")
        column = raw_column.replace('"', '""')
        direction = "ASC" if bool(rule["ascending"]) else "DESC"
        if rule["kind"] == "status_last":
            last_value = str(rule["last_value"]).replace("'", "''")
            clause_parts.append(
                f'CASE WHEN UPPER(CAST("{column}" AS TEXT)) = '
                f"'{last_value}' THEN 1 ELSE 0 END {direction}"
            )
        elif rule["kind"] == "sqlite_integer_prefix":
            clause_parts.append(f'CAST("{column}" AS INTEGER) {direction}')
        else:
            raise ValueError(f"Regra de ordenacao default desconhecida: {rule}")
    return ", ".join(clause_parts)
