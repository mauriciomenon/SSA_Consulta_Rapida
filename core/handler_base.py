"""
Handler Base - Padronização para Handlers CLI
Elimina inconsistências nas assinaturas dos handlers (1-6 parâmetros).
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
import pandas as pd
from pathlib import Path


class HandlerContext:
    """
    Contexto padronizado para todos os handlers.
    Centraliza parâmetros e configurações.
    """

    def __init__(
        self,
        config_manager: Any = None,
        cache_manager: Any = None,
        output_format: str = 'table',
        max_width: Optional[int] = None,
        show_summary: bool = True,
        debug_mode: bool = False,
        **kwargs
    ):
        """
        Inicializa contexto do handler.

        Args:
            config_manager: Gerenciador de configurações
            cache_manager: Gerenciador de cache
            output_format: Formato de saída ('table', 'json', 'csv')
            max_width: Largura máxima da saída
            show_summary: Se deve mostrar resumo
            debug_mode: Modo de debug ativo
            **kwargs: Parâmetros adicionais específicos
        """
        self.config_manager = config_manager
        self.cache_manager = cache_manager
        self.output_format = output_format
        self.max_width = max_width
        self.show_summary = show_summary
        self.debug_mode = debug_mode

        # Parâmetros específicos dos handlers
        self.extra_params = kwargs

        # Estado do processamento
        self.processed_rows = 0
        self.filtered_rows = 0
        self.error_count = 0
        self.warnings: List[str] = []

    def get_param(self, key: str, default: Any = None) -> Any:
        """Recupera parâmetro específico."""
        return self.extra_params.get(key, default)

    def set_param(self, key: str, value: Any) -> None:
        """Define parâmetro específico."""
        self.extra_params[key] = value

    def add_warning(self, message: str) -> None:
        """Adiciona warning ao contexto."""
        self.warnings.append(message)

    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do processamento."""
        return {
            'processed_rows': self.processed_rows,
            'filtered_rows': self.filtered_rows,
            'error_count': self.error_count,
            'warnings_count': len(self.warnings),
            'warnings': self.warnings
        }


class HandlerResult:
    """
    Resultado padronizado dos handlers.
    """

    def __init__(
        self,
        success: bool = True,
        data: Optional[pd.DataFrame] = None,
        message: str = '',
        output_text: str = '',
        stats: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Inicializa resultado do handler.

        Args:
            success: Se operação foi bem-sucedida
            data: DataFrame resultante (se aplicável)
            message: Mensagem de status
            output_text: Texto formatado para exibição
            stats: Estatísticas do processamento
            metadata: Metadados adicionais
        """
        self.success = success
        self.data = data
        self.message = message
        self.output_text = output_text
        self.stats = stats or {}
        self.metadata = metadata or {}

    def has_data(self) -> bool:
        """Verifica se há dados no resultado."""
        return self.data is not None and not self.data.empty

    def get_row_count(self) -> int:
        """Retorna número de linhas no resultado."""
        return len(self.data) if self.has_data() else 0


class HandlerBase(ABC):
    """
    Classe base para todos os handlers CLI.
    Padroniza interface e elimina inconsistências de assinatura.
    """

    def __init__(self, name: str, description: str = ''):
        """
        Inicializa handler base.

        Args:
            name: Nome do handler
            description: Descrição do handler
        """
        self.name = name
        self.description = description
        self._supported_formats = ['table', 'json', 'csv']

    @abstractmethod
    def execute(self, context: HandlerContext) -> HandlerResult:
        """
        Executa processamento do handler.

        Args:
            context: Contexto padronizado

        Returns:
            Resultado padronizado
        """
        pass

    def validate_context(self, context: HandlerContext) -> List[str]:
        """
        Valida contexto antes da execução.

        Args:
            context: Contexto a validar

        Returns:
            Lista de erros de validação
        """
        errors = []

        if context.output_format not in self._supported_formats:
            errors.append(
                f"Formato '{context.output_format}' não suportado. "
                f"Suportados: {', '.join(self._supported_formats)}"
            )

        return errors

    def format_output(
        self,
        data: pd.DataFrame,
        context: HandlerContext
    ) -> str:
        """
        Formata dados para saída.

        Args:
            data: DataFrame a formatar
            context: Contexto com configurações

        Returns:
            String formatada
        """
        if data.empty:
            return "Nenhum resultado encontrado."

        format_type = context.output_format.lower()

        if format_type == 'json':
            return data.to_json(orient='records', indent=2)
        elif format_type == 'csv':
            return data.to_csv(index=False)
        else:  # table (default)
            return self._format_table(data, context)

    def _format_table(self, data: pd.DataFrame, context: HandlerContext) -> str:
        """
        Formata DataFrame como tabela.

        Args:
            data: DataFrame a formatar
            context: Contexto com configurações

        Returns:
            Tabela formatada
        """
        # Usa cache se disponível
        if context.cache_manager:
            cache_key = context.cache_manager.get_dataframe_hash(
                data,
                f"table_{context.max_width}_{context.output_format}"
            )
            cached_output = context.cache_manager.get_cached_output(cache_key)
            if cached_output:
                return cached_output

        # Calcula larguras das colunas
        if context.config_manager and hasattr(context.config_manager, 'width_manager'):
            widths = context.config_manager.width_manager.calculate_column_widths(
                data,
                max_table_width=context.max_width
            )
            formatted_output = self._apply_column_widths(data, widths)
        else:
            # Fallback simples
            formatted_output = str(data.to_string(index=False, max_colwidth=50))

        # Armazena no cache
        if context.cache_manager and 'cache_key' in locals():
            context.cache_manager.cache_output(cache_key, formatted_output)

        return formatted_output

    def _apply_column_widths(
        self,
        data: pd.DataFrame,
        widths: Dict[str, int]
    ) -> str:
        """Aplica larguras específicas às colunas."""
        output_lines = []

        # Cabeçalho
        headers = []
        for col in data.columns:
            width = widths.get(col, 20)
            header = str(col)[:width].ljust(width)
            headers.append(header)
        output_lines.append(' | '.join(headers))

        # Separador
        separators = []
        for col in data.columns:
            width = widths.get(col, 20)
            separators.append('-' * width)
        output_lines.append(' | '.join(separators))

        # Dados
        for _, row in data.iterrows():
            row_parts = []
            for col in data.columns:
                width = widths.get(col, 20)
                value = str(row[col])[:width].ljust(width)
                row_parts.append(value)
            output_lines.append(' | '.join(row_parts))

        return '\n'.join(output_lines)

    def get_supported_formats(self) -> List[str]:
        """Retorna formatos suportados pelo handler."""
        return self._supported_formats.copy()

    def add_supported_format(self, format_name: str) -> None:
        """Adiciona formato suportado."""
        if format_name not in self._supported_formats:
            self._supported_formats.append(format_name)

    def create_result(
        self,
        data: Optional[pd.DataFrame] = None,
        message: str = '',
        context: Optional[HandlerContext] = None,
        success: bool = True
    ) -> HandlerResult:
        """
        Cria resultado padronizado.

        Args:
            data: DataFrame resultante
            message: Mensagem de status
            context: Contexto do handler
            success: Status de sucesso

        Returns:
            Resultado padronizado
        """
        output_text = ''
        stats = {}

        if data is not None and not data.empty and context:
            output_text = self.format_output(data, context)
            stats = context.get_stats()

        return HandlerResult(
            success=success,
            data=data,
            message=message,
            output_text=output_text,
            stats=stats,
            metadata={'handler': self.name}
        )


class FilterHandlerBase(HandlerBase):
    """
    Handler base para operações de filtro.
    Especialização para handlers que filtram dados.
    """

    def __init__(self, name: str, description: str = ''):
        super().__init__(name, description)
        self._filter_cache = {}

    @abstractmethod
    def apply_filters(
        self,
        data: pd.DataFrame,
        context: HandlerContext
    ) -> pd.DataFrame:
        """
        Aplica filtros específicos aos dados.

        Args:
            data: DataFrame a filtrar
            context: Contexto com parâmetros de filtro

        Returns:
            DataFrame filtrado
        """
        pass

    def execute(self, context: HandlerContext) -> HandlerResult:
        """
        Execução padrão para handlers de filtro.

        Args:
            context: Contexto do handler

        Returns:
            Resultado do filtro
        """
        # Validação
        validation_errors = self.validate_context(context)
        if validation_errors:
            return HandlerResult(
                success=False,
                message=f"Erros de validação: {'; '.join(validation_errors)}"
            )

        try:
            # Carrega dados base (implementação específica deve definir fonte)
            base_data = self._load_base_data(context)
            if base_data.empty:
                return HandlerResult(
                    success=True,
                    data=base_data,
                    message="Nenhum dado base encontrado"
                )

            context.processed_rows = len(base_data)

            # Aplica filtros
            filtered_data = self.apply_filters(base_data, context)
            context.filtered_rows = len(filtered_data)

            # Cria resultado
            return self.create_result(
                data=filtered_data,
                message=f"Filtro aplicado: {context.filtered_rows} de {context.processed_rows} registros",
                context=context
            )

        except Exception as e:
            context.error_count += 1
            return HandlerResult(
                success=False,
                message=f"Erro durante filtro: {str(e)}"
            )

    @abstractmethod
    def _load_base_data(self, context: HandlerContext) -> pd.DataFrame:
        """
        Carrega dados base para filtro.
        Implementação específica deve definir fonte dos dados.

        Args:
            context: Contexto do handler

        Returns:
            DataFrame com dados base
        """
        pass


class ExportHandlerBase(HandlerBase):
    """
    Handler base para operações de exportação.
    Especialização para handlers que exportam dados.
    """

    def __init__(self, name: str, description: str = ''):
        super().__init__(name, description)
        self.add_supported_format('xlsx')
        self.add_supported_format('parquet')

    @abstractmethod
    def export_data(
        self,
        data: pd.DataFrame,
        output_path: Path,
        context: HandlerContext
    ) -> bool:
        """
        Exporta dados para arquivo.

        Args:
            data: DataFrame a exportar
            output_path: Caminho do arquivo
            context: Contexto com configurações

        Returns:
            True se exportação foi bem-sucedida
        """
        pass

    def execute(self, context: HandlerContext) -> HandlerResult:
        """
        Execução padrão para handlers de exportação.

        Args:
            context: Contexto do handler

        Returns:
            Resultado da exportação
        """
        try:
            # Carrega dados para exportação
            export_data = self._load_export_data(context)
            if export_data.empty:
                return HandlerResult(
                    success=True,
                    message="Nenhum dado para exportar"
                )

            # Define caminho de saída
            output_path = Path(context.get_param('output_path', 'output.csv'))

            # Executa exportação
            success = self.export_data(export_data, output_path, context)

            if success:
                return HandlerResult(
                    success=True,
                    data=export_data,
                    message=f"Dados exportados para: {output_path}",
                    metadata={'output_path': str(output_path)}
                )
            else:
                return HandlerResult(
                    success=False,
                    message="Falha na exportação"
                )

        except Exception as e:
            return HandlerResult(
                success=False,
                message=f"Erro durante exportação: {str(e)}"
            )

    @abstractmethod
    def _load_export_data(self, context: HandlerContext) -> pd.DataFrame:
        """
        Carrega dados para exportação.
        Implementação específica deve definir fonte dos dados.

        Args:
            context: Contexto do handler

        Returns:
            DataFrame com dados para exportar
        """
        pass
