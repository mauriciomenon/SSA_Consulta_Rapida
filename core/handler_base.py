"""
Handler Base - Padronizacao para Handlers CLI
Elimina inconsistencias nas assinaturas dos handlers (1-6 parametros).
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from utils.path_safety import ensure_path_is_allowed
from utils.robust_logging import get_robust_logger

logger = get_robust_logger().get_logger(__name__, "core")


class HandlerContext:
    """
    Contexto padronizado para todos os handlers.
    Centraliza parametros e configuracoes.
    """

    def __init__(
        self,
        config_manager: Any = None,
        cache_manager: Any = None,
        output_format: str = "table",
        max_width: Optional[int] = None,
        show_summary: bool = True,
        debug_mode: bool = False,
        **kwargs,
    ):
        """
        Inicializa contexto do handler.

        Args:
            config_manager: Gerenciador de configuracoes
            cache_manager: Gerenciador de cache
            output_format: Formato de saida ('table', 'json', 'csv')
            max_width: Largura maxima da saida
            show_summary: Se deve mostrar resumo
            debug_mode: Modo de debug ativo
            **kwargs: Parametros adicionais especificos
        """
        self.config_manager = config_manager
        self.cache_manager = cache_manager
        self.output_format = output_format
        self.max_width = max_width
        self.show_summary = show_summary
        self.debug_mode = debug_mode

        # Parametros especificos dos handlers
        self.extra_params = kwargs

        # Estado do processamento
        self.processed_rows = 0
        self.filtered_rows = 0
        self.error_count = 0
        self.warnings: List[str] = []

    def get_param(self, key: str, default: Any = None) -> Any:
        """Recupera parametro especifico."""
        return self.extra_params.get(key, default)

    def set_param(self, key: str, value: Any) -> None:
        """Define parametro especifico."""
        self.extra_params[key] = value

    def add_warning(self, message: str) -> None:
        """Adiciona warning ao contexto."""
        self.warnings.append(message)

    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatisticas do processamento."""
        return {
            "processed_rows": self.processed_rows,
            "filtered_rows": self.filtered_rows,
            "error_count": self.error_count,
            "warnings_count": len(self.warnings),
            "warnings": self.warnings,
        }


class HandlerResult:
    """
    Resultado padronizado dos handlers.
    """

    def __init__(
        self,
        success: bool = True,
        data: Optional[pd.DataFrame] = None,
        message: str = "",
        output_text: str = "",
        stats: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Inicializa resultado do handler.

        Args:
            success: Se operacao foi bem-sucedida
            data: DataFrame resultante (se aplicavel)
            message: Mensagem de status
            output_text: Texto formatado para exibicao
            stats: Estatisticas do processamento
            metadata: Metadados adicionais
        """
        self.success = success
        self.data = data
        self.message = message
        self.output_text = output_text
        self.stats = stats or {}
        self.metadata = metadata or {}

    def has_data(self) -> bool:
        """Verifica se ha dados no resultado."""
        return isinstance(self.data, pd.DataFrame) and not self.data.empty

    def get_row_count(self) -> int:
        """Retorna numero de linhas no resultado."""
        if not isinstance(self.data, pd.DataFrame):
            return 0
        return len(self.data) if not self.data.empty else 0


class HandlerBase(ABC):
    """
    Classe base para todos os handlers CLI.
    Padroniza interface e elimina inconsistencias de assinatura.
    """

    def __init__(self, name: str, description: str = ""):
        """
        Inicializa handler base.

        Args:
            name: Nome do handler
            description: Descricao do handler
        """
        self.name = name
        self.description = description
        self._supported_formats = ["table", "json", "csv"]

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
        Valida contexto antes da execucao.

        Args:
            context: Contexto a validar

        Returns:
            Lista de erros de validacao
        """
        errors = []

        if context.output_format not in self._supported_formats:
            errors.append(
                f"Formato '{context.output_format}' nao suportado. "
                f"Suportados: {', '.join(self._supported_formats)}"
            )

        return errors

    def format_output(self, data: pd.DataFrame, context: HandlerContext) -> str:
        """
        Formata dados para saida.

        Args:
            data: DataFrame a formatar
            context: Contexto com configuracoes

        Returns:
            String formatada
        """
        format_type = context.output_format.lower()

        if format_type == "json":
            if data.empty:
                return "[]"
            json_text = data.to_json(orient="records", indent=2)
            return json_text or "[]"
        elif format_type == "csv":
            return data.to_csv(index=False, lineterminator="\n")
        elif data.empty:
            return "Nenhum resultado encontrado."
        else:  # table (default)
            return self._format_table(data, context)

    def _format_table(self, data: pd.DataFrame, context: HandlerContext) -> str:
        """
        Formata DataFrame como tabela.

        Args:
            data: DataFrame a formatar
            context: Contexto com configuracoes

        Returns:
            Tabela formatada
        """
        cache_key = None
        # Usa cache se disponivel
        if context.cache_manager:
            cache_key = context.cache_manager.get_dataframe_hash(
                data, f"table_{context.max_width}_{context.output_format}"
            )
            cached_output = context.cache_manager.get_cached_output(cache_key)
            if cached_output:
                return cached_output

        # Calcula larguras das colunas
        if context.config_manager and hasattr(context.config_manager, "width_manager"):
            widths = context.config_manager.width_manager.calculate_column_widths(
                data, max_table_width=context.max_width
            )
            formatted_output = self._apply_column_widths(data, widths)
        else:
            # Fallback simples
            formatted_output = str(data.to_string(index=False, max_colwidth=50))

        # Armazena no cache
        if context.cache_manager and cache_key is not None:
            context.cache_manager.cache_output(cache_key, formatted_output)

        return formatted_output

    def _apply_column_widths(self, data: pd.DataFrame, widths: Dict[str, int]) -> str:
        """Aplica larguras especificas as colunas."""
        output_lines = []
        columns = data.columns

        # Cabecalho
        headers = []
        for col in columns:
            width = widths.get(col, 20)
            header = str(col)[:width].ljust(width)
            headers.append(header)
        output_lines.append(" | ".join(headers))

        # Separador
        separators = []
        for col in columns:
            width = widths.get(col, 20)
            separators.append("-" * width)
        output_lines.append(" | ".join(separators))

        # Dados
        for row in data.itertuples(index=False, name=None):
            row_parts = []
            for col, raw_value in zip(columns, row):
                width = widths.get(col, 20)
                value = str(raw_value)[:width].ljust(width)
                row_parts.append(value)
            output_lines.append(" | ".join(row_parts))

        return "\n".join(output_lines)

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
        message: str = "",
        context: Optional[HandlerContext] = None,
        success: bool = True,
        format_output_text: bool = True,
    ) -> HandlerResult:
        """
        Cria resultado padronizado.

        Args:
            data: DataFrame resultante
            message: Mensagem de status
            context: Contexto do handler
            success: Status de sucesso
            format_output_text: Se deve montar output_text para exibicao

        Returns:
            Resultado padronizado
        """
        output_text = ""
        stats = {}

        if context:
            stats = context.get_stats()

        if isinstance(data, pd.DataFrame) and context and format_output_text:
            output_text = self.format_output(data, context)

        return HandlerResult(
            success=success,
            data=data,
            message=message,
            output_text=output_text,
            stats=stats,
            metadata={"handler": self.name},
        )


class FilterHandlerBase(HandlerBase):
    """
    Handler base para operacoes de filtro.
    Especializacao para handlers que filtram dados.
    """

    def __init__(self, name: str, description: str = ""):
        super().__init__(name, description)
        self._filter_cache = {}

    @abstractmethod
    def apply_filters(
        self, data: pd.DataFrame, context: HandlerContext
    ) -> pd.DataFrame:
        """
        Aplica filtros especificos aos dados.

        Args:
            data: DataFrame a filtrar
            context: Contexto com parametros de filtro

        Returns:
            DataFrame filtrado
        """
        pass

    def execute(self, context: HandlerContext) -> HandlerResult:
        """
        Execucao padrao para handlers de filtro.

        Args:
            context: Contexto do handler

        Returns:
            Resultado do filtro
        """
        # Validacao
        validation_errors = self.validate_context(context)
        if validation_errors:
            return self.create_result(
                message=f"Erros de validacao: {'; '.join(validation_errors)}",
                context=context,
                success=False,
            )

        try:
            # Carrega dados base (implementacao especifica deve definir fonte)
            base_data = self._load_base_data(context)
            if not isinstance(base_data, pd.DataFrame):
                raise TypeError(
                    f"{self.name}._load_base_data deve retornar pandas.DataFrame"
                )
            if base_data.empty:
                return self.create_result(
                    data=base_data,
                    message="Nenhum dado base encontrado",
                    context=context,
                )

            context.processed_rows = len(base_data)

            # Aplica filtros
            filtered_data = self.apply_filters(base_data, context)
            if not isinstance(filtered_data, pd.DataFrame):
                raise TypeError(
                    f"{self.name}.apply_filters deve retornar pandas.DataFrame"
                )
            context.filtered_rows = len(filtered_data)

            # Cria resultado
            return self.create_result(
                data=filtered_data,
                message=f"Filtro aplicado: {context.filtered_rows} de {context.processed_rows} registros",
                context=context,
            )

        except Exception as e:
            context.error_count += 1
            logger.exception("Filter handler '%s' failed", self.name)
            return self.create_result(
                message=f"Erro durante filtro: {str(e)}",
                context=context,
                success=False,
            )

    @abstractmethod
    def _load_base_data(self, context: HandlerContext) -> pd.DataFrame:
        """
        Carrega dados base para filtro.
        Implementacao especifica deve definir fonte dos dados.

        Args:
            context: Contexto do handler

        Returns:
            DataFrame com dados base
        """
        pass


class ExportHandlerBase(HandlerBase):
    """
    Handler base para operacoes de exportacao.
    Especializacao para handlers que exportam dados.
    """

    def __init__(self, name: str, description: str = ""):
        super().__init__(name, description)
        self.add_supported_format("xlsx")
        self.add_supported_format("parquet")

    @abstractmethod
    def export_data(
        self, data: pd.DataFrame, output_path: Path, context: HandlerContext
    ) -> bool:
        """
        Exporta dados para arquivo.

        Args:
            data: DataFrame a exportar
            output_path: Caminho do arquivo
            context: Contexto com configuracoes

        Returns:
            True se exportacao foi bem-sucedida
        """
        pass

    def execute(self, context: HandlerContext) -> HandlerResult:
        """
        Execucao padrao para handlers de exportacao.

        Args:
            context: Contexto do handler

        Returns:
            Resultado da exportacao
        """
        try:
            # Carrega dados para exportacao
            export_data = self._load_export_data(context)
            if not isinstance(export_data, pd.DataFrame):
                raise TypeError(
                    f"{self.name}._load_export_data deve retornar pandas.DataFrame"
                )
            context.processed_rows = len(export_data)
            if export_data.empty:
                return self.create_result(
                    data=export_data,
                    message="Nenhum dado para exportar",
                    context=context,
                )

            # Define caminho de saida
            output_path = ensure_path_is_allowed(
                context.get_param("output_path", "output.csv"),
                purpose="handler_export_output",
                base=Path.cwd(),
                must_exist=False,
                expect_directory=False,
            )

            # Executa exportacao
            success = self.export_data(export_data, output_path, context)

            if success:
                result = self.create_result(
                    data=export_data,
                    message=f"Dados exportados para: {output_path}",
                    context=context,
                    format_output_text=False,
                )
                result.metadata["output_path"] = str(output_path)
                return result

            return self.create_result(
                message="Falha na exportacao",
                context=context,
                success=False,
            )

        except Exception as e:
            context.error_count += 1
            logger.exception("Export handler '%s' failed", self.name)
            return self.create_result(
                message=f"Erro durante exportacao: {str(e)}",
                context=context,
                success=False,
            )

    @abstractmethod
    def _load_export_data(self, context: HandlerContext) -> pd.DataFrame:
        """
        Carrega dados para exportacao.
        Implementacao especifica deve definir fonte dos dados.

        Args:
            context: Contexto do handler

        Returns:
            DataFrame com dados para exportar
        """
        pass
