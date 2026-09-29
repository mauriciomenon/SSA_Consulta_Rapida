# utils/enhanced_importer.py
"""
Sistema aprimorado de importação que lida com diferentes formatos AMS
e adiciona campos apenas se não existirem.
"""

import logging
from typing import Optional

import pandas as pd

from extracao.extractor import open_validated_excel_source

logger = logging.getLogger(__name__)


class EnhancedAMSImporter:
    """Importador aprimorado para diferentes formatos de relatórios AMS."""

    def __init__(self):
        self.known_formats = {
            "format_a": {
                "indicators": ["Todas as SSAs", "Número da SSA"],
                "priority": 1,
            },
            "format_b": {"indicators": ["Em Execução", "Nº SSA"], "priority": 2},
            "format_c": {"indicators": ["Pendentes", "SSA"], "priority": 3},
        }

    def detect_format(self, df: pd.DataFrame) -> str:
        """Detecta o formato do arquivo baseado em colunas e conteúdo."""
        if df.empty:
            return "unknown"

        columns = [str(col) for col in df.columns.tolist()]

        for format_name, format_info in self.known_formats.items():
            raw_indicators = format_info.get("indicators", [])
            if not isinstance(raw_indicators, list):
                continue
            indicators = [
                str(indicator).strip()
                for indicator in raw_indicators
                if str(indicator).strip()
            ]
            if not indicators:
                continue
            required_matches = max(1, (len(indicators) + 1) // 2)
            matches = sum(
                1
                for indicator in indicators
                if any(indicator in col for col in columns)
            )

            if matches >= required_matches:  # Pelo menos metade dos indicadores
                logger.info(f"Formato detectado: {format_name}")
                return format_name

        logger.warning("Formato não reconhecido, usando padrão")
        return "unknown"

    def safe_column_addition(
        self, existing_df: pd.DataFrame, new_df: pd.DataFrame
    ) -> pd.DataFrame:
        """Adiciona colunas de new_df apenas se não existirem em existing_df."""
        if existing_df.empty:
            return new_df.copy()

        result_df = existing_df.copy()

        for col in new_df.columns:
            if col not in result_df.columns:
                result_df[col] = None
                logger.info(f"Nova coluna adicionada: {col}")

        return result_df

    def import_with_format_detection(self, file_path: str) -> Optional[pd.DataFrame]:
        """Importa arquivo com detecção automática de formato."""
        try:
            with open_validated_excel_source(file_path) as source_stream:
                df = pd.read_excel(source_stream)
            format_type = self.detect_format(df)

            # Aplicar transformações específicas do formato se necessário
            if format_type != "unknown":
                df = self._apply_format_transformations(df, format_type)

            return df

        except Exception as e:
            logger.error(f"Erro ao importar {file_path}: {e}")
            return None

    def _apply_format_transformations(
        self, df: pd.DataFrame, format_type: str
    ) -> pd.DataFrame:
        """Aplica transformações específicas baseadas no formato detectado."""
        # Implementar transformações específicas conforme necessário
        return df
