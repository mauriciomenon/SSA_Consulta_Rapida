# gui/workers/data_loader_worker.py
# Worker thread for loading data from database asynchronously

import logging
import re
import sqlite3
import pandas as pd
from PyQt6.QtCore import QThread, pyqtSignal
from armazenamento.database import query_db

logger = logging.getLogger(__name__)


class DataLoaderWorker(QThread):
    """Thread para carregar dados do banco com suporte seguro a paginação."""
    data_loaded = pyqtSignal(pd.DataFrame)
    error_occurred = pyqtSignal(str)

    _ALLOWED_ORDER_COLUMNS = {
        'numero_ssa', 'situacao', 'data_cadastro', 'semana_cadastro',
        'semana_programada', 'semana_executada', 'setor_emissor', 'setor_executor',
        'descricao_ssa', 'localizacao_codigo', 'equipamento', 'solicitante',
        'grau_prioridade_emissao', 'grau_prioridade_planejamento', 'derivada_de',
    }
    _IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

    def __init__(self, db_path, table_name, limit=None, offset=0, order_by=None):
        super().__init__()
        self.db_path = db_path
        self.table_name = table_name
        self.limit = limit
        self.offset = offset
        self.order_by = order_by

    def _sanitize_identifier(self, value: str) -> str:
        text = str(value or "").strip()
        if not text:
            return ""
        if not self._IDENTIFIER_RE.match(text):
            return ""
        return text

    def _resolve_target_table(self) -> str:
        requested = self._sanitize_identifier(self.table_name)
        candidates = []
        if requested:
            candidates.append(requested)
        if "ssa_table" not in candidates:
            candidates.append("ssa_table")

        try:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type IN ('table','view')"
                ).fetchall()
                existing = {str(row[0]) for row in rows if row and row[0]}
            for candidate in candidates:
                if candidate in existing:
                    return candidate
        except Exception as exc:
            logger.debug("Falha ao resolver tabela alvo do DataLoaderWorker: %s", exc)

        return candidates[0] if candidates else "ssa_table"

    def _normalize_order_by(self, order_by: str | None) -> str | None:
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
                raise ValueError(f"ORDER BY inválido: {part}")
            col = self._sanitize_identifier(col).lower()
            if col not in self._ALLOWED_ORDER_COLUMNS:
                raise ValueError(f"Coluna ORDER BY não permitida: {col}")
            if direction not in {"ASC", "DESC"}:
                raise ValueError(f"Direção ORDER BY inválida: {direction}")
            normalized_parts.append(f"{col} {direction}")
        return ", ".join(normalized_parts)

    def run(self):
        try:
            target_table = self._resolve_target_table()
            query = f"SELECT * FROM {target_table}"

            order_clause = self._normalize_order_by(self.order_by)
            if order_clause:
                query += f" ORDER BY {order_clause}"

            if self.limit is not None:
                limit_int = int(self.limit)
                if limit_int < 0:
                    raise ValueError("LIMIT não pode ser negativo")
                query += f" LIMIT {limit_int}"

            offset_int = int(self.offset or 0)
            if offset_int < 0:
                raise ValueError("OFFSET não pode ser negativo")
            if offset_int > 0:
                # SQLite exige LIMIT antes de OFFSET.
                if self.limit is None:
                    query += " LIMIT -1"
                query += f" OFFSET {offset_int}"

            df = query_db(self.db_path, '', query)
            if not df.empty:
                self.data_loaded.emit(df)
            else:
                self.error_occurred.emit("Falha ao carregar dados do banco.")
        except Exception as e:
            self.error_occurred.emit(f"Erro ao carregar dados: {e}")
