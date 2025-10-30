"""
# ==============================================================================
# SUPERSEDED FILE - DELETE CANDIDATE
# ==============================================================================
# Status: Superseded by simple_width_manager.py
# Created: Unknown
# Last modified: 2025-10-29T12:15:00 (marked as superseded)
# Recommendation: DELETE - gui_ssa.py uses simple_width_manager.py instead
#
# Width Manager - Sistema Unificado de Gerenciamento de Larguras
# Elimina as estratégias conflitantes de largura da GUI.
#
# NOTA: Este arquivo não é mais usado. Use simple_width_manager.py
"""

from typing import Dict, List, Optional, Tuple, Any

# Importação lazy do pandas para evitar travamento na inicialização
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    pd = None


class WidthManager:
    """
    Gerenciador unificado de larguras de colunas.
    Substitui as múltiplas estratégias conflitantes por uma implementação limpa.
    """

    def __init__(self, default_widths: Optional[Dict[str, int]] = None):
        """
        Inicializa o gerenciador de larguras.

        Args:
            default_widths: Larguras padrão por coluna (opcional)
        """
        # Cache unificado
        self._computed_widths: Dict[str, Dict[str, int]] = {}
        self._dataframe_hashes: Dict[str, str] = {}

        # Configurações base
        self.default_widths = default_widths or {}
        self.min_char_sizes = {
            'numero_ssa': 8,
            'localizacao_codigo': 8,
            'setor_executor': 8,
            'setor_emissor': 8,
            'situacao': 8,
            'solicitante': 18,  # Acomoda "MAURICIO MENON"
            'data_cadastro': 12,
            'semana_programada': 8,
            'semana_executada': 8,
            'descricao_ssa': 25,
            'descricao_execucao': 20,
            'derivada_de': 10,
            'observacoes': 15
        }

        # Colunas expandíveis
        self.expandable_columns = [
            'descricao_ssa', 'descricao_execucao', 'observacoes',
            'solicitante', 'derivada_de'
        ]

    def compute_optimal_widths(
        self,
        df: Any,  # pd.DataFrame quando pandas disponível
        available_width: int,
        display_mappings: Optional[Dict[str, str]] = None,
        saved_widths: Optional[Dict[str, int]] = None
    ) -> Dict[str, int]:
        """
        Calcula larguras otimizadas para o DataFrame dado.

        Args:
            df: DataFrame para calcular larguras
            available_width: Largura total disponível
            display_mappings: Mapeamentos de exibição (opcional)
            saved_widths: Larguras salvas pelo usuário (opcional)

        Returns:
            Dict com larguras por coluna
        """
        if not PANDAS_AVAILABLE:
            # Fallback quando pandas não está disponível
            return {col: 100 for col in getattr(df, 'columns', ['col1', 'col2'])}

        # Gera hash único do DataFrame
        df_hash = self._generate_df_hash(df, available_width)

        # Verifica cache
        if df_hash in self._computed_widths:
            return self._computed_widths[df_hash].copy()

        # Calcula larguras
        widths = self._calculate_widths(df, available_width, display_mappings, saved_widths)

        # Armazena no cache
        self._computed_widths[df_hash] = widths.copy()

        # Limita tamanho do cache
        if len(self._computed_widths) > 10:
            # Remove entrada mais antiga
            oldest_key = next(iter(self._computed_widths))
            del self._computed_widths[oldest_key]

        return widths

    def _generate_df_hash(self, df: Any, available_width: int) -> str:
        """Gera hash único para o DataFrame e largura disponível."""
        try:
            return f"{len(df)}x{len(df.columns)}_{available_width}_{hash(tuple(df.columns))}"
        except:
            return f"fallback_{available_width}"

    def _calculate_widths(
        self,
        df: Any,  # pd.DataFrame
        available_width: int,
        display_mappings: Optional[Dict[str, str]] = None,
        saved_widths: Optional[Dict[str, int]] = None
    ) -> Dict[str, int]:
        """Executa o cálculo real das larguras."""

        display_mappings = display_mappings or {}
        saved_widths = saved_widths or {}
        widths = {}

        # 1. Calcula larguras mínimas
        total_min_width = 0
        for col in df.columns:
            if col == '#':
                min_width = 40
            else:
                # Largura baseada no cabeçalho
                header_text = display_mappings.get(col, col)
                header_width = len(header_text) * 8 + 20  # 8px por char + padding

                # Largura baseada no conteúdo mínimo
                content_min = self.min_char_sizes.get(col, 10) * 8 + 20

                # Usa o maior entre header e conteúdo mínimo
                min_width = max(header_width, content_min)

            widths[col] = min_width
            total_min_width += min_width

        # 2. Distribui espaço extra
        extra_space = max(0, available_width - total_min_width)
        if extra_space > 0:
            self._distribute_extra_space(df, widths, extra_space)

        return widths

    def _distribute_extra_space(
        self,
        df: pd.DataFrame,
        widths: Dict[str, int],
        extra_space: int
    ) -> None:
        """Distribui espaço extra de forma inteligente."""

        # Identifica colunas expandíveis presentes
        expandable_present = [
            col for col in self.expandable_columns
            if col in df.columns
        ]

        if expandable_present:
            # Distribui por prioridade
            if extra_space > 800:  # Tela grande
                self._distribute_large_screen(widths, expandable_present, extra_space)
            else:
                self._distribute_normal_screen(widths, expandable_present, extra_space)
        else:
            # Distribui igualmente entre todas (exceto #)
            non_index_cols = [col for col in df.columns if col != '#']
            if non_index_cols:
                extra_per_col = extra_space // len(non_index_cols)
                for col in non_index_cols:
                    widths[col] += extra_per_col

    def _distribute_large_screen(
        self,
        widths: Dict[str, int],
        expandable_cols: List[str],
        extra_space: int
    ) -> None:
        """Distribui espaço para telas grandes."""

        # Prioridades para tela grande
        priorities = {
            'descricao_ssa': 0.4,
            'descricao_execucao': 0.25,
            'solicitante': 0.15,
            'observacoes': 0.1,
            'derivada_de': 0.1
        }

        for col in expandable_cols:
            priority = priorities.get(col, 0.05)
            additional = int(extra_space * priority)
            widths[col] += additional

    def _distribute_normal_screen(
        self,
        widths: Dict[str, int],
        expandable_cols: List[str],
        extra_space: int
    ) -> None:
        """Distribui espaço para telas normais."""

        # Prioridades para tela normal
        priorities = {
            'descricao_ssa': 0.6,
            'descricao_execucao': 0.3,
            'solicitante': 0.05,
            'observacoes': 0.03,
            'derivada_de': 0.02
        }

        for col in expandable_cols:
            priority = priorities.get(col, 0.01)
            additional = int(extra_space * priority)
            widths[col] += additional

    def invalidate_cache(self) -> None:
        """Limpa todo o cache de larguras."""
        self._computed_widths.clear()
        self._dataframe_hashes.clear()

    def get_cache_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do cache."""
        return {
            'cached_computations': len(self._computed_widths),
            'cache_keys': list(self._computed_widths.keys()),
            'memory_usage_estimate': len(str(self._computed_widths))
        }

    def set_min_width(self, column: str, min_width_chars: int) -> None:
        """Define largura mínima para uma coluna específica."""
        self.min_char_sizes[column] = min_width_chars
        # Invalida cache pois os parâmetros mudaram
        self.invalidate_cache()

    def add_expandable_column(self, column: str) -> None:
        """Adiciona coluna à lista de expandíveis."""
        if column not in self.expandable_columns:
            self.expandable_columns.append(column)
            self.invalidate_cache()

    def remove_expandable_column(self, column: str) -> None:
        """Remove coluna da lista de expandíveis."""
        if column in self.expandable_columns:
            self.expandable_columns.remove(column)
            self.invalidate_cache()
