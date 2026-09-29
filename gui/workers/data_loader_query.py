"""SQL query fragments for the data loader."""

from __future__ import annotations

import re

from armazenamento.identifier_utils import is_valid_identifier

SQL_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
SQLITE_OFFSET_WITHOUT_LIMIT = 9223372036854775807
DERIVADAS_SUMMARY_TABLE = "ssa_derivada_summary"
DERIVADAS_COUNT_COLUMN = "qtd_derivadas"
DEFAULT_SELECT_COLUMNS = (
    "numero_ssa",
    "situacao",
    "data_cadastro",
    "semana_cadastro",
    "semana_programada",
    "semana_executada",
    "setor_emissor",
    "setor_executor",
    "descricao_ssa",
    "localizacao_codigo",
    "equipamento",
    "solicitante",
    "grau_prioridade_emissao",
    "grau_prioridade_planejamento",
    "derivada_de",
)
ALLOWED_ORDER_COLUMNS = set(DEFAULT_SELECT_COLUMNS)


def sanitize_identifier(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if not is_valid_identifier(text):
        return ""
    return text


def quote_identifier(value: str) -> str:
    identifier = str(value or "").replace('"', '""')
    return f'"{identifier}"'


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


def normalize_order_by(order_by: str | None) -> str | None:
    if not order_by:
        return None
    normalized_parts = []
    parts = [part.strip() for part in str(order_by).split(",") if part.strip()]
    if not parts:
        return None
    for part in parts:
        tokens = part.split()
        if len(tokens) == 1:
            col, direction = tokens[0], "ASC"
        elif len(tokens) == 2:
            col, direction = tokens[0], tokens[1].upper()
        else:
            raise ValueError(f"ORDER BY invalido: {part}")
        col = sanitize_identifier(col).lower()
        if col not in ALLOWED_ORDER_COLUMNS:
            raise ValueError(f"Coluna ORDER BY nao permitida: {col}")
        if direction not in {"ASC", "DESC"}:
            raise ValueError(f"Direcao ORDER BY invalida: {direction}")
        normalized_parts.append(f"{quote_identifier(col)} {direction}")
    return ", ".join(normalized_parts)


def build_select_projection(
    select_columns: tuple[str, ...] | None,
    *,
    source_alias: str | None = None,
) -> str:
    columns = select_columns or DEFAULT_SELECT_COLUMNS
    normalized_columns = []
    seen = set()
    for raw_column in columns:
        column = sanitize_identifier(raw_column)
        if not column:
            raise ValueError(f"Coluna SELECT invalida: {raw_column}")
        if column in seen:
            continue
        quoted_column = quote_identifier(column)
        if source_alias:
            quoted_column = f"{quote_identifier(source_alias)}.{quoted_column}"
        normalized_columns.append(quoted_column)
        seen.add(column)
    if not normalized_columns:
        raise ValueError("Consulta SELECT sem colunas validas")
    return ", ".join(normalized_columns)


def build_select_query(
    *,
    target_table: str,
    select_columns: tuple[str, ...] | None = None,
    order_by: str | None,
    limit: int | None,
    offset: int | None,
    default_sort_spec: tuple[dict, ...],
    include_derivadas_count: bool = False,
    derivadas_summary_available: bool = False,
) -> tuple[str, bool]:
    if not sanitize_identifier(target_table):
        raise ValueError("Tabela alvo invalida para DataLoaderWorker")
    use_derivadas_summary = include_derivadas_count and derivadas_summary_available
    source_alias = "ssa_source" if use_derivadas_summary else None
    projection = build_select_projection(select_columns, source_alias=source_alias)
    if include_derivadas_count:
        if use_derivadas_summary:
            projection += (
                ', COALESCE("derivadas_summary"."descendants_count", 0) '
                f"AS {quote_identifier(DERIVADAS_COUNT_COLUMN)}"
            )
        else:
            projection += f", 0 AS {quote_identifier(DERIVADAS_COUNT_COLUMN)}"

    query = f"SELECT {projection} FROM {quote_identifier(target_table)}"  # nosec B608
    if source_alias is not None:
        query += (
            f" AS {quote_identifier(source_alias)} "
            f"LEFT JOIN {quote_identifier(DERIVADAS_SUMMARY_TABLE)} "
            f"AS {quote_identifier('derivadas_summary')} "
            f"ON {quote_identifier('derivadas_summary')}.{quote_identifier('ssa')} = "
            f"CAST({quote_identifier(source_alias)}."
            f"{quote_identifier('numero_ssa')} AS TEXT)"
        )
    already_sorted_for_ui = False

    order_clause = normalize_order_by(order_by)
    if order_clause:
        query += f" ORDER BY {order_clause}"
    else:
        query += f" ORDER BY {build_default_ui_order_clause(default_sort_spec)}"
        already_sorted_for_ui = True

    if limit is not None:
        limit_int = int(limit)
        if limit_int < 0:
            raise ValueError("LIMIT nao pode ser negativo")
        query += f" LIMIT {limit_int}"

    offset_int = int(offset or 0)
    if offset_int < 0:
        raise ValueError("OFFSET nao pode ser negativo")
    if offset_int > 0:
        if limit is None:
            query += f" LIMIT {SQLITE_OFFSET_WITHOUT_LIMIT}"
        query += f" OFFSET {offset_int}"

    return query, already_sorted_for_ui
