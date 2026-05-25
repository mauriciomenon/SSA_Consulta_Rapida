"""
 Simple Width Manager - Versao simplificada para integracao imediata
Elimina codigo frankenstein com implementacao funcional minima.
"""

import logging

import pandas as pd

from gui.gui_config import DEFAULT_COLUMN_WIDTHS

logger = logging.getLogger(__name__)


class SimpleWidthManager:
    """
    Gerenciador simples de larguras de colunas.
    Substitui as multiplas estrategias conflitantes por uma implementacao limpa.
    """

    def __init__(self):
        """Inicializa o gerenciador simples."""
        self.min_char_sizes = {
            "#": 3,
            "numero_ssa": 8,
            "localizacao_codigo": 7,
            "situacao": 4,
            "descricao_ssa": 25,
            "data_cadastro": 9,
            "setor_emissor": 5,
            "setor_executor": 5,
            "derivada_de": 8,
            "semana_programada": 6,
            "descricao_execucao": 20,
            "semana_cadastro": 7,
            "solicitante": 18,  # Aumentado para acomodar "MAURICIO MENON"
            "grau_prioridade_emissao": 4,
            "grau_prioridade_planejamento": 4,
        }
        self.base_pixel_widths = dict(DEFAULT_COLUMN_WIDTHS)
        self.base_pixel_widths.setdefault("#", 24)

        self.expandable_columns = [
            "descricao_ssa",
            "descricao_execucao",
            "solicitante",
            "responsavel_execucao",
        ]
        self.max_pixel_widths = {
            "descricao_ssa": 620,
            "descricao_execucao": 560,
            "solicitante": 320,
            "responsavel_execucao": 280,
            "numero_ssa": 120,
            "localizacao_codigo": 120,
            "situacao": 80,
            "setor_emissor": 95,
            "setor_executor": 95,
            "derivada_de": 135,
            "data_cadastro": 120,
            "data_arquivo_origem": 190,
            "data_planilha": 120,
            "semana_cadastro": 95,
            "semana_programada": 105,
            "semana_executada": 105,
            "grau_prioridade": 105,
            "grau_prioridade_emissao": 130,
            "grau_prioridade_planejamento": 135,
            "total_de_reprogramacoes": 140,
            "execucao_parcial": 110,
        }

    def compute_optimal_widths(
        self,
        df,  # DataFrame
        available_width: int,
        column_order=None,
    ):
        """
        ALGORITMO SIMPLES E FUNCIONAL - BASE DETERMINISTICA COM CRESCIMENTO

        Baseline de larguras fixas para colunas estaticas + crescimento proporcional
        para colunas expansivas definidas em self.expandable_columns.
        Nao aplica overrides externos para manter resultado deterministico.

        Args:
            column_order: Lista explicita da ordem correta das colunas (inclui '#')
        """
        if df is None or df.empty:
            return {}

        # Usa a ordem explicita fornecida, ou fallback para colunas ordenadas deterministicamente
        if column_order:
            columns = column_order
        else:
            # Lista de colunas ordenada deterministicamente
            df_columns = sorted(df.columns.tolist())
            columns = (
                ["#"] + df_columns
                if "#" not in df_columns
                else sorted(df.columns.tolist())
            )

        # Baseline canonico: parte sempre dos widths persistidos em gui_config.py.
        # O crescimento automatico acontece apenas por cima desse baseline.
        fixed_widths = {}
        expandable_cols = []  # Colunas que podem crescer

        for col in columns:
            fixed_widths[col] = int(
                self.base_pixel_widths.get(col, 24 if col == "#" else 120)
            )
            if col in self.expandable_columns:
                expandable_cols.append(col)

        # CALCULO DE CRESCIMENTO PROPORCIONAL MELHORADO
        total_fixed = sum(fixed_widths.values())
        available_extra = max(0, available_width - total_fixed)

        if available_extra > 0 and expandable_cols:
            # Divisao proporcional do espaco extra com tratamento de resto
            extra_per_col = available_extra // len(expandable_cols)
            remainder = available_extra % len(expandable_cols)

            for i, col in enumerate(expandable_cols):
                # Primeira coluna recebe o resto para evitar pixels perdidos
                extra_bonus = remainder if i == 0 else 0
                total_extra = extra_per_col + extra_bonus

                fixed_widths[col] += total_extra

        for col, width in list(fixed_widths.items()):
            max_px = int(self.max_pixel_widths.get(col, 1000))
            min_px = 24 if col == "#" else 30
            fixed_widths[col] = max(min_px, min(int(width), max_px))

        return fixed_widths

    def capture_current_column_widths(
        self, table_widget, current_columns
    ) -> dict[str, int]:
        captured: dict[str, int] = {}
        if table_widget is None:
            return captured
        for idx, col_name in enumerate(list(current_columns or [])):
            if not isinstance(col_name, str) or not col_name:
                continue
            try:
                width = int(table_widget.columnWidth(idx))
            except Exception as exc:
                logger.debug(
                    "Falha ao capturar largura da coluna '%s' (index=%s): %s",
                    col_name,
                    idx,
                    exc,
                )
                width = 0
            if width > 0:
                captured[col_name] = width
        return captured

    def has_user_column_width(
        self, col_name: str, saved_widths: dict | None = None
    ) -> bool:
        return isinstance(saved_widths, dict) and col_name in saved_widths

    def user_column_widths(
        self, saved_widths: dict | None = None, preference_widths: dict | None = None
    ) -> dict:
        widths: dict = {}
        if isinstance(preference_widths, dict):
            widths.update(preference_widths)
        if isinstance(saved_widths, dict):
            widths.update(saved_widths)
        return widths

    def max_pixel_width_for(self, col_name: str, saved_widths: dict | None = None) -> int:
        if self.has_user_column_width(col_name, saved_widths):
            return 1000
        return int(self.max_pixel_widths.get(col_name, 1000))

    def clamp_pixel_width(
        self, col_name: str, width: int, min_px: int, saved_widths: dict | None = None
    ) -> int:
        max_px = self.max_pixel_width_for(col_name, saved_widths)
        return max(int(min_px), min(int(width), max_px))

    def restore_column_widths(
        self,
        table_widget,
        current_columns,
        widths: dict[str, int],
        *,
        saved_widths: dict | None = None,
        gui_widths: dict | None = None,
    ) -> dict[str, int]:
        applied: dict[str, int] = {}
        if table_widget is None or not isinstance(widths, dict):
            return applied
        current_cols = list(current_columns or [])
        for col_name, width in widths.items():
            if col_name not in current_cols:
                continue
            idx = current_cols.index(col_name)
            col_max = self.max_pixel_width_for(col_name, saved_widths)
            try:
                width_int = int(width)
            except Exception as exc:
                logger.debug(
                    "Falha ao converter largura para coluna '%s': %s",
                    col_name,
                    exc,
                )
                continue
            min_px = 24 if col_name == "#" else 30
            safe_width = max(min_px, min(width_int, col_max))
            try:
                table_widget.setColumnWidth(idx, safe_width)
            except Exception as exc:
                logger.debug(
                    "Falha ao restaurar largura da coluna '%s' (index=%s): %s",
                    col_name,
                    idx,
                    exc,
                )
                continue
            applied[col_name] = safe_width
            if isinstance(saved_widths, dict):
                saved_widths[col_name] = safe_width
            if isinstance(gui_widths, dict):
                gui_widths[col_name] = safe_width
        return applied

    def compute_streamlit_width_buckets(
        self,
        df,
        available_width: int,
        column_order=None,
    ):
        """Return deterministic streamlit width buckets per column."""
        if df is None or df.empty:
            return {}

        widths = self.compute_optimal_widths(
            df,
            available_width=available_width,
            column_order=column_order,
        )
        buckets = {}
        for col in column_order or list(df.columns):
            pixel_width = int(widths.get(col, 120))
            # Keep proportional-priority columns expanded whenever possible.
            if col in {"descricao_ssa", "descricao_execucao"}:
                pixel_width = max(pixel_width, 260)
            if pixel_width <= 90:
                buckets[col] = "small"
            elif pixel_width <= 220:
                buckets[col] = "medium"
            else:
                buckets[col] = "large"
        return buckets

    def compute_best_fit_width(
        self,
        series,
        header_text: str,
        col_name: str,
        measure_text,
        baseline_px: int | None = None,
        sample_limit: int = 800,
    ) -> int:
        """Compute deterministic best-fit width with anti-outlier guard."""
        normalized_header = str(header_text or col_name or "").strip()
        if normalized_header.startswith("[f] "):
            normalized_header = normalized_header[4:]
        header_px = int(measure_text(normalized_header)) + 28

        if col_name == "#":
            return max(26, min(int(header_px), 90))

        if series is None:
            return max(40, min(int(header_px), 420))

        try:
            sample_series = pd.Series(series).dropna().astype(str)
        except Exception:
            sample_series = pd.Series(dtype="string")
        if len(sample_series) == 0:
            return max(40, min(int(header_px), 420))

        if len(sample_series) > int(sample_limit):
            sample_series = sample_series.sample(n=int(sample_limit), random_state=0)

        normalized = sample_series.map(
            lambda value: value.replace("\n", " ").replace("\r", " ").strip()
        )
        measure_cache: dict[str, int] = {}

        def _measure_cached(value: str) -> int:
            cached = measure_cache.get(value)
            if cached is None:
                cached = int(measure_text(value))
                measure_cache[value] = cached
            return cached

        widths_px = normalized.map(_measure_cached)
        widths_px = widths_px[widths_px > 0]

        if len(widths_px) == 0:
            target_px = int(header_px)
        else:
            median_px = int(widths_px.median())
            p85_px = int(widths_px.quantile(0.85))
            p92_px = int(widths_px.quantile(0.92))
            outlier_guard_px = max(int(header_px), int(median_px * 2.4))
            target_px = max(int(header_px), median_px, p85_px)
            target_px = min(target_px, p92_px, outlier_guard_px)

        final_px = int(target_px) + 26

        baseline_value = int(baseline_px or 0)
        if baseline_value > 0:
            # Keep close to real Qt auto-fit behavior and avoid width explosions.
            baseline_cap = int(max(int(header_px) + 24, baseline_value * 1.35 + 12))
            baseline_floor = int(max(int(header_px), baseline_value + 6))
            final_px = min(final_px, baseline_cap)
            final_px = max(final_px, baseline_floor)

        max_px = int(self.max_pixel_widths.get(col_name, 420))
        return max(40, min(max(int(header_px), int(final_px)), max_px))


class SimpleCacheManager:
    """Cache manager simples para evitar problemas de importacao."""

    def __init__(self):
        self._formatted_cache = {}
        self._named_caches = {}

    def get_cached_formatted_df(self, df_hash):
        """Retorna DataFrame formatado do cache."""
        return self._formatted_cache.get(df_hash)

    def cache_formatted_df(self, df_hash, formatted_df):
        """Armazena DataFrame formatado no cache."""
        if df_hash not in self._formatted_cache and len(self._formatted_cache) >= 5:
            # Remove entrada mais antiga antes de inserir a nova.
            oldest_key = next(iter(self._formatted_cache))
            del self._formatted_cache[oldest_key]
        self._formatted_cache[df_hash] = formatted_df

    def get_cached_value(self, cache_name, cache_key):
        """Retorna valor de cache nomeado."""
        cache = self._named_caches.get(cache_name)
        if not isinstance(cache, dict):
            return None
        return cache.get(cache_key)

    def cache_value(self, cache_name, cache_key, value, max_entries=5):
        """Armazena valor em cache nomeado com limite simples."""
        cache = self._named_caches.setdefault(cache_name, {})
        max_entries = max(1, int(max_entries or 1))
        if cache_key not in cache and len(cache) >= max_entries:
            oldest_key = next(iter(cache))
            del cache[oldest_key]
        cache[cache_key] = value
