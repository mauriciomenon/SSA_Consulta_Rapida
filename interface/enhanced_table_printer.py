"""
Enhanced Table Printer - Versao melhorada com CLI Width Manager
Integra as solucoes da GUI para fornecer renderizacao consistente na CLI.
"""

import builtins
import math
import os
import sys
from typing import Any, Dict, List, Optional

import pandas as pd

try:
    from tabulate import tabulate

    _TABULATE_AVAILABLE = True
except ModuleNotFoundError:  # pragma: no cover - depende do ambiente
    _TABULATE_AVAILABLE = False

    def tabulate(data, headers=(), tablefmt="plain", showindex=False, **kwargs):
        """Fallback simples para ambientes sem `tabulate`."""
        _ = tablefmt
        if hasattr(data, "to_string"):
            try:
                return data.to_string(index=showindex)
            except Exception as exc:  # pragma: no cover
                logger.debug("Fallback tabulate falhou em to_string: %s", exc)

        try:
            rows = list(data)
        except TypeError:
            rows = [data]

        header_list: list[str] = []
        if isinstance(headers, (list, tuple)):
            header_list = [str(h) for h in headers]
        elif headers:
            header_list = [str(headers)]

        column_count = (
            len(header_list)
            if header_list
            else max(
                (len(r) if isinstance(r, (list, tuple)) else 1 for r in rows),
                default=0,
            )
        )

        def _fmt(row) -> str:
            if isinstance(row, (list, tuple)):
                cells = list(row)
            elif hasattr(row, "tolist"):
                cells = list(row.tolist())
            else:
                cells = [row]
            if column_count:
                if len(cells) < column_count:
                    cells.extend([""] * (column_count - len(cells)))
                elif len(cells) > column_count:
                    cells = cells[:column_count]
            return " | ".join(str(c) for c in cells)

        lines: list[str] = []
        if header_list:
            lines.append(" | ".join(header_list))

        if showindex:
            for idx, row in enumerate(rows):
                lines.append(f"{idx} | {_fmt(row)}")
        else:
            for row in rows:
                lines.append(_fmt(row))

        return "\n".join(lines)


from interface.cli_width_manager import CLIWidthManager
from utils.formatting import format_dataframe_for_display
from utils.robust_logging import get_robust_logger

logger = get_robust_logger().get_logger(__name__, "cli")
if not _TABULATE_AVAILABLE:
    logger.warning(
        "tabulate não encontrado; EnhancedTablePrinter usando fallback simples"
    )


_ORIGINAL_INPUT = builtins.input


class EnhancedTablePrinter:
    """
    Renderizador de tabelas melhorado para CLI.
    Usa CLIWidthManager para larguras deterministicas e truncamento conservador.
    """

    def __init__(self):
        """Inicializa o renderizador melhorado."""
        self.width_manager = CLIWidthManager()

    def get_terminal_size(self):
        """Obtem dimensoes do terminal."""
        try:
            size = os.get_terminal_size()
            return size.lines, size.columns
        except OSError:
            return 24, 120  # Valores padrao mais generosos

    def print_dataframe_enhanced(
        self,
        df: pd.DataFrame,
        display_map: Dict[str, str],
        settings: dict,
        highlight_terms: Optional[List[str]] = None,
        filter_terms: Optional[List[str]] = None,
        start_page: int = 0,
        max_pages: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Renderiza DataFrame com sistema melhorado e retorna estado de paginação.

        Args:
            df: DataFrame a ser exibido
            display_map: Mapeamento de nomes de colunas
            settings: Configuracoes do sistema
            highlight_terms: Termos para destacar (opcional)
            filter_terms: termos aplicados (para mensagens auxiliares)
            start_page: pagina inicial (0-based)
            max_pages: limite superior de paginas a renderizar (None = todas)

        Returns:
            Informacoes sobre paginas renderizadas (ex.: proxima pagina disponivel).
        """
        if df.empty:
            print("Nenhum resultado para exibir.")
            return {
                "next_page": None,
                "total_pages": 0,
                "rendered_pages": 0,
                "page_size": 0,
            }

        # Obtem dimensoes do terminal
        terminal_height, terminal_width = self.get_terminal_size()
        available_width = max(terminal_width - 5, 40)  # Margem de seguranca

        # Obtem ordem das colunas da configuracao unificada
        column_order = self.width_manager.get_column_order()
        display_names = self.width_manager.get_display_names()

        # Filtra colunas que existem no DataFrame
        available_columns = ["#"] + [col for col in df.columns]
        filtered_order = [col for col in column_order if col in available_columns]

        # Seleciona colunas baseado na largura disponível
        selected_columns = self._select_columns_smart(
            df, filtered_order, available_width, display_names
        )

        if not selected_columns or len(selected_columns) <= 1:
            print("Nenhuma coluna adequada para exibição encontrada.")
            return {
                "next_page": None,
                "total_pages": 0,
                "rendered_pages": 0,
                "page_size": 0,
            }

        # Prepara DataFrame de trabalho
        data_columns = [col for col in selected_columns if col != "#"]
        working_df = df[data_columns].copy()

        # Calcula larguras usando CLI Width Manager
        widths = self.width_manager.compute_cli_widths(
            working_df, available_width, selected_columns
        )

        # Renderiza com paginação
        return self._render_paginated(
            working_df,
            widths,
            display_names,
            settings,
            highlight_terms,
            filter_terms,
            start_page=start_page,
            max_pages=max_pages,
        )

    def _select_columns_smart(
        self,
        df: pd.DataFrame,
        column_order: List[str],
        available_width: int,
        display_names: Dict[str, str],
    ) -> List[str]:
        """
        Seleciona colunas inteligentemente baseado na largura disponível.

        Args:
            df: DataFrame fonte
            column_order: Ordem preferida das colunas
            available_width: Largura disponível
            display_names: Nomes de exibição

        Returns:
            Lista de colunas selecionadas
        """
        # Colunas essenciais que sempre devem aparecer
        essential_columns = ["#", "numero_ssa", "situacao", "descricao_ssa"]

        # Colunas prioritárias (ordem de importância)
        priority_columns = [
            "localizacao_codigo",
            "setor_executor",
            "data_cadastro",
            "semana_cadastro",
            "semana_programada",
            "derivada_de",
            "setor_emissor",
            "solicitante",
            "descricao_execucao",
        ]

        selected = []
        estimated_width = 0

        # Sempre inclui colunas essenciais
        for col in essential_columns:
            if col in column_order:
                selected.append(col)
                col_width = self.width_manager.fixed_widths.get(col, 15)
                estimated_width += col_width + 3  # +3 para separadores

        # Adiciona colunas prioritárias se couberem
        for col in priority_columns:
            if col in column_order and col not in selected:
                col_width = self.width_manager.fixed_widths.get(col, 15)
                if (
                    estimated_width + col_width + 3 <= available_width * 0.95
                ):  # 95% para margem
                    selected.append(col)
                    estimated_width += col_width + 3

        # Adiciona outras colunas se houver espaço abundante
        for col in column_order:
            if col not in selected and col != "#":
                col_width = self.width_manager.fixed_widths.get(col, 15)
                if (
                    estimated_width + col_width + 3 <= available_width * 0.9
                ):  # 90% para outras
                    selected.append(col)
                    estimated_width += col_width + 3

        return selected

    def _apply_formatting_and_truncation(
        self,
        df: pd.DataFrame,
        widths: Dict[str, int],
        display_names: Dict[str, str],
        *,
        rename_columns: bool = True,
    ) -> pd.DataFrame:
        """
        Aplica formatação e truncamento por limite de palavra nas células.

        Args:
            df: DataFrame a ser formatado
            widths: Larguras calculadas
            display_names: Nomes de exibição

        Returns:
            DataFrame formatado
        """
        formatted_df = df.copy()

        # Aplica formatação coluna por coluna
        for col in formatted_df.columns:
            if col in widths:
                width = widths[col]

                # Aplica word wrap ou truncamento conforme a coluna
                formatted_df[col] = (
                    formatted_df[col]
                    .astype(str)
                    .apply(lambda x: self._format_cell(x, width, col))
                )

        if rename_columns:
            formatted_df = self._rename_columns_for_display(
                formatted_df, widths, display_names
            )

        return formatted_df

    def _rename_columns_for_display(
        self,
        df: pd.DataFrame,
        widths: Dict[str, int],
        display_names: Dict[str, str],
    ) -> pd.DataFrame:
        rename_map = {}
        for col in df.columns:
            if col == "#":
                rename_map[col] = "#"
            else:
                display_name = display_names.get(col, col)
                rename_map[col] = self._truncate_header(
                    display_name,
                    widths.get(col, 15),
                )
        return df.rename(columns=rename_map)

    def _format_cell(self, content: str, width: int, column_name: str) -> str:
        """
        Formata uma célula individual.

        Args:
            content: Conteúdo da célula
            width: Largura disponível
            column_name: Nome da coluna

        Returns:
            Conteúdo formatado
        """
        if not content or content == "nan":
            content = "-"

        content = str(content).strip()

        # Para coluna de índice, aplica padding à direita
        if column_name == "#":
            return content.rjust(width)

        # Aplica truncamento por limite de palavra
        wrapped_lines = self.width_manager.apply_word_wrap(content, width, column_name)

        # A CLI atual mantém apenas uma linha por registro.
        formatted_content = wrapped_lines[0] if wrapped_lines else ""

        # Remove padding fixo para evitar quebras de linha
        return formatted_content.rstrip()[:width]

    def _truncate_header(self, header: str, max_width: int) -> str:
        if max_width <= 0:
            return ""
        if len(header) <= max_width:
            return header
        if max_width <= 3:
            return "." * max_width
        return header[: max_width - 3] + "..."

    def _render_page_table(
        self,
        page_df: pd.DataFrame,
        *,
        include_header: bool,
        highlight_terms: Optional[List[str]],
    ) -> None:
        table_str = tabulate(
            page_df.values.tolist(),
            headers=page_df.columns,
            tablefmt="presto",
            showindex=False,
            stralign="left",
            disable_numparse=True,
        )
        lines = table_str.splitlines()
        if not include_header and lines:
            if len(lines) >= 2 and set(lines[1].strip()) <= {"-", "+", " "}:
                lines = lines[2:]
            else:
                lines = lines[1:]
        output = "\n".join(lines)
        if lines:
            output += "\n"
        if highlight_terms and highlight_terms[0]:
            output = self._apply_highlighting(output, highlight_terms)
        print(output, end="")

    def _handle_last_page_command(
        self,
        command: str,
        *,
        total_pages: int,
        rendered_pages: int,
        page_size: int,
        resume_page: int | None,
    ) -> Dict[str, Any]:
        if command == "qq":
            print("Saindo...")
            return self._build_pagination_state(
                total_pages=total_pages,
                rendered_pages=rendered_pages,
                page_size=page_size,
                exit_requested=True,
            )
        if command == "q":
            print("...exibição interrompida.")
        else:
            print("Fim da exibição.")
        return self._build_pagination_state(
            total_pages=total_pages,
            rendered_pages=rendered_pages,
            page_size=page_size,
            next_page=resume_page,
        )

    def _handle_pagination_command(
        self,
        command: str,
        *,
        filters_text: str,
        total_pages: int,
        rendered_pages: int,
        page_size: int,
        resume_page: int | None,
        current_page: int,
        highlight_terms: Optional[List[str]],
    ) -> tuple[str, Dict[str, Any] | None]:
        if command == "qq":
            print("Saindo...")
            return "return", self._build_pagination_state(
                total_pages=total_pages,
                rendered_pages=rendered_pages,
                page_size=page_size,
                exit_requested=True,
            )
        if not command:
            return "next_page", None
        if command == "q":
            print("...exibição interrompida.")
            return "return", self._build_pagination_state(
                total_pages=total_pages,
                rendered_pages=rendered_pages,
                page_size=page_size,
                next_page=resume_page,
            )
        if command == "z":
            if current_page >= total_pages - 1:
                print("Fim da exibição.")
                return "return", self._build_pagination_state(
                    total_pages=total_pages,
                    rendered_pages=rendered_pages,
                    page_size=page_size,
                    next_page=resume_page,
                )
            return "auto_scroll", None
        if command == "l":
            if filters_text:
                print(f"\nFiltros ativos: {filters_text}")
            else:
                print("\nNenhum filtro aplicado.")
            return "continue", None
        if command.startswith("d "):
            print(
                f"\nPara ver detalhe da linha {command[2:]}, use o comando principal."
            )
            return "continue", None
        if command == "f":
            return "auto_scroll", None
        print("Comando inválido.")
        return "continue", None

    def _render_paginated(
        self,
        df: pd.DataFrame,
        widths: Dict[str, int],
        display_names: Dict[str, str],
        settings: dict,
        highlight_terms: Optional[List[str]] = None,
        filter_terms: Optional[List[str]] = None,
        *,
        start_page: int = 0,
        max_pages: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Renderiza DataFrame com paginação de forma mais enxuta."""
        terminal_height, _ = self.get_terminal_size()
        page_size = max(1, terminal_height - 8)

        auto_scroll = settings.get("user_preferences", {}).get(
            "auto_scroll_to_end", False
        )
        total_pages = math.ceil(len(df) / page_size) if page_size > 0 else 0
        max_auto_scroll_pages = settings.get("display_settings", {}).get(
            "max_auto_scroll_pages", 3
        )
        if auto_scroll and total_pages > max_auto_scroll_pages:
            auto_scroll = False

        if total_pages <= 0:
            print("Nenhum dado para exibir após processamento.")
            return self._build_pagination_state(
                total_pages=0,
                rendered_pages=0,
                page_size=page_size,
            )
        last_index = total_pages - 1
        effective_start = max(0, start_page)
        if effective_start >= total_pages:
            print("Nenhuma nova página para exibir.")
            return self._build_pagination_state(
                total_pages=total_pages,
                rendered_pages=0,
                page_size=page_size,
            )

        filters_text = ""
        if filter_terms:
            if isinstance(filter_terms, (list, tuple)):
                filters_text = ", ".join(filter_terms)
            else:
                filters_text = str(filter_terms)

        env_flag = os.environ.get("SSA_NON_INTERACTIVE", "").strip().lower()
        input_is_patched = builtins.input is not _ORIGINAL_INPUT
        non_interactive = (
            env_flag in {"1", "true", "yes", "on"} and not input_is_patched
        )
        current_page = effective_start
        rendered_pages = 0
        last_counted_page: int | None = None
        prepared_page: tuple[int, pd.DataFrame] | None = None
        while current_page < total_pages:
            resume_page: int | None = None
            try:
                if prepared_page is not None and prepared_page[0] == current_page:
                    page_df = prepared_page[1]
                else:
                    page_df = self._prepare_page_dataframe(
                        df,
                        current_page=current_page,
                        page_size=page_size,
                        widths=widths,
                        display_names=display_names,
                    )
                    prepared_page = (current_page, page_df)
                resume_page = current_page + 1 if current_page < last_index else None
                print(f"Página {current_page + 1} de {total_pages}")
                self._render_page_table(
                    page_df,
                    include_header=True,
                    highlight_terms=highlight_terms,
                )
                page_counted = current_page != last_counted_page
                if page_counted:
                    rendered_pages += 1
                    last_counted_page = current_page
                last = current_page == last_index

                if (
                    page_counted
                    and max_pages is not None
                    and rendered_pages >= max_pages
                ):
                    next_page = current_page + 1 if current_page < last_index else None
                    return self._build_pagination_state(
                        total_pages=total_pages,
                        rendered_pages=rendered_pages,
                        page_size=page_size,
                        next_page=next_page,
                    )
                if auto_scroll or non_interactive:
                    if last:
                        if non_interactive:
                            print("Fim da exibicao.")
                        return self._build_pagination_state(
                            total_pages=total_pages,
                            rendered_pages=rendered_pages,
                            page_size=page_size,
                        )
                    current_page += 1
                    continue
                if last:
                    try:
                        cmd = (
                            "q"
                            if non_interactive
                            else input(
                                "\n-- Fim | Enter fechar exibicao, q=fechar exibicao, qq=sair app -- "
                            )
                            .strip()
                            .lower()
                        )
                    except KeyboardInterrupt:
                        print("\n...exibição interrompida.")
                        return self._build_pagination_state(
                            total_pages=total_pages,
                            rendered_pages=rendered_pages,
                            page_size=page_size,
                            next_page=resume_page,
                        )
                    return self._handle_last_page_command(
                        cmd,
                        total_pages=total_pages,
                        rendered_pages=rendered_pages,
                        page_size=page_size,
                        resume_page=resume_page,
                    )

                remaining = total_pages - current_page - 1
                prefix = f" {remaining} pág. restantes"
                if filters_text:
                    prefix += f" - Filtros: {filters_text}"
                prompt = f"{prefix} | 'z': até o final, 'l': listar filtros, 'd <#>': detalhe, 'q': fechar exibicao, 'qq': sair app: "
                try:
                    sys.stdout.flush()
                    user_input = input(prompt).strip().lower()
                except KeyboardInterrupt:
                    print("\n...exibição interrompida.")
                    return self._build_pagination_state(
                        total_pages=total_pages,
                        rendered_pages=rendered_pages,
                        page_size=page_size,
                        next_page=resume_page,
                    )

                action, state = self._handle_pagination_command(
                    user_input,
                    filters_text=filters_text,
                    total_pages=total_pages,
                    rendered_pages=rendered_pages,
                    page_size=page_size,
                    resume_page=resume_page,
                    current_page=current_page,
                    highlight_terms=highlight_terms,
                )
                if action == "return":
                    return state or self._build_pagination_state(
                        total_pages=total_pages,
                        rendered_pages=rendered_pages,
                        page_size=page_size,
                    )
                if action == "continue":
                    continue
                if action == "next_page":
                    current_page += 1
                    prepared_page = None
                    continue
                if action == "auto_scroll":
                    auto_scroll = True
                    current_page += 1
                    prepared_page = None
                    continue
            except KeyboardInterrupt:
                print("\n...exibição interrompida.")
                return self._build_pagination_state(
                    total_pages=total_pages,
                    rendered_pages=rendered_pages,
                    page_size=page_size,
                    next_page=resume_page,
                )
            except Exception as e:
                logger.error(f"Erro na renderização: {e}")
                print(f"Erro na exibição: {e}")
                return self._build_pagination_state(
                    total_pages=total_pages,
                    rendered_pages=rendered_pages,
                    page_size=page_size,
                )
            current_page += 1

        return self._build_pagination_state(
            total_pages=total_pages,
            rendered_pages=rendered_pages,
            page_size=page_size,
        )

    def _build_pagination_state(
        self,
        *,
        total_pages: int,
        rendered_pages: int,
        page_size: int,
        next_page: int | None = None,
        exit_requested: bool = False,
    ) -> Dict[str, Any]:
        return {
            "next_page": next_page,
            "total_pages": total_pages,
            "rendered_pages": rendered_pages,
            "page_size": page_size,
            "exit_requested": exit_requested,
        }

    def _prepare_page_dataframe(
        self,
        df: pd.DataFrame,
        *,
        current_page: int,
        page_size: int,
        widths: Dict[str, int],
        display_names: Dict[str, str],
    ) -> pd.DataFrame:
        start_index = current_page * page_size
        end_index = start_index + page_size
        page_df = format_dataframe_for_display(df.iloc[start_index:end_index].copy())

        if "numero_ssa" in page_df.columns:
            page_df["numero_ssa"] = page_df["numero_ssa"].apply(
                self.width_manager.normalize_ssa_number
            )

        row_numbers = range(start_index + 1, start_index + len(page_df) + 1)
        if "#" in page_df.columns:
            page_df["#"] = list(row_numbers)
            ordered_columns = ["#"] + [col for col in page_df.columns if col != "#"]
            page_df = page_df[ordered_columns]
        else:
            page_df.insert(0, "#", row_numbers)
        page_df = self._apply_formatting_and_truncation(
            page_df,
            widths,
            display_names,
            rename_columns=False,
        )

        try:
            page_df = self._clamp_widths(page_df, widths)
        except Exception as exc:
            logger.debug("Falha ao limitar larguras da pagina CLI: %s", exc)

        return self._rename_columns_for_display(page_df, widths, display_names)

    def _apply_highlighting(self, table_str: str, highlight_terms: List[str]) -> str:
        """
        Aplica destaque ANSI aos termos especificados.

        Args:
            table_str: String da tabela
            highlight_terms: Termos para destacar

        Returns:
            String com destaque aplicado
        """
        import re

        # Apenas em terminais compatíveis
        if os.name == "nt" or not sys.stdout.isatty() or os.environ.get("NO_COLOR"):
            return table_str

        highlighted = table_str
        for term in highlight_terms:
            if term and len(term) > 1:  # Evita termos muito curtos
                pattern = f"({re.escape(term)})"
                replacement = "\\x1b[1m\\1\\x1b[0m"  # Negrito
                highlighted = re.sub(
                    pattern, replacement, highlighted, flags=re.IGNORECASE
                )

        return highlighted

    # -- Helpers de ordenação/ajuste --
    def _apply_default_order(self, df: pd.DataFrame) -> pd.DataFrame:
        """Aplica ordenação padrão pedida: não-STE primeiro; depois numero_ssa desc."""
        work = df.copy()
        # Marca STE (situação) — valores ausentes tratados como não-STE
        if "situacao" in work.columns:
            is_ste = work["situacao"].astype(str).str.upper().eq("STE")
        else:
            # Se não há coluna, mantém ordem original
            return work

        # Converte número SSA para inteiro para ordenar desc (tolerante)
        ssa_int = None
        if "numero_ssa" in work.columns:
            normalized_ssa = work["numero_ssa"].apply(
                self.width_manager.normalize_ssa_number
            )
            ssa_int = normalized_ssa.apply(lambda s: int(s) if str(s).isdigit() else -1)
        else:
            ssa_int = pd.Series([-1] * len(work), index=work.index)

        work = work.assign(__is_ste=is_ste, __ssa=ssa_int)
        work = work.sort_values(
            by=["__is_ste", "__ssa"],
            ascending=[True, False],
            na_position="last",
        )
        return work.drop(columns=["__is_ste", "__ssa"])

    def _clamp_widths(self, df: pd.DataFrame, widths: Dict[str, int]) -> pd.DataFrame:
        """Garante que cada célula tenha no máximo a largura da coluna (ajuste conservador)."""
        out = df.copy()
        for col in out.columns:
            limit = widths.get(col)
            if not limit or limit <= 0:
                continue

            def _clamp(x):
                s = "" if x is None else str(x)
                if len(s) <= limit:
                    return s
                # Mantém elipse para indicar truncamento, preservando largura
                return (s[: max(0, limit - 1)] + "…") if limit > 1 else s[:limit]

            out[col] = out[col].map(_clamp)
        return out


# Instância global para uso direto
enhanced_printer = EnhancedTablePrinter()


def pretty_print_df_enhanced(
    df: pd.DataFrame,
    display_map: Dict[str, str],
    settings: dict,
    highlight_terms: Optional[List[str]] = None,
    filter_terms: Optional[List[str]] = None,
    *,
    start_page: int = 0,
    max_pages: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Função de conveniência para usar o renderizador melhorado.

    Args:
        df: DataFrame a ser exibido
        display_map: Mapeamento de nomes de colunas
        settings: Configurações do sistema
        highlight_terms: Termos para destacar (opcional)
        filter_terms: Termos de filtro aplicados (opcional)
        start_page: página inicial (0-based)
        max_pages: limite máximo de páginas a renderizar

    Returns:
        Informações de paginação retornadas pelo EnhancedTablePrinter.
    """
    return enhanced_printer.print_dataframe_enhanced(
        df,
        display_map,
        settings,
        highlight_terms,
        filter_terms,
        start_page=start_page,
        max_pages=max_pages,
    )


# Função simplificada para formato CLI rápido
def format_dataframe_for_cli_enhanced(
    df: pd.DataFrame,
    display_map: Optional[Dict[str, str]] = None,
    max_width: Optional[int] = None,
    highlight_terms: Optional[List[str]] = None,
) -> str:
    """
    Versão melhorada da formatação CLI rápida.

    Args:
        df: DataFrame a ser formatado
        display_map: Mapeamento de nomes (opcional)
        max_width: Largura máxima (não usado, mantido para compatibilidade)
        highlight_terms: Termos para destacar

    Returns:
        String formatada da tabela
    """
    if df.empty:
        return "Nenhum resultado encontrado."

    # Cria instância temporária
    temp_printer = EnhancedTablePrinter()

    # Seleciona apenas algumas colunas essenciais para formato rápido
    essential_cols = ["numero_ssa", "situacao", "setor_executor", "descricao_ssa"]
    available_cols = [col for col in essential_cols if col in df.columns]

    if not available_cols:
        available_cols = list(df.columns)[:4]

    work_df = df[available_cols].copy()

    # Aplica normalização SSA
    if "numero_ssa" in work_df.columns:
        work_df["numero_ssa"] = work_df["numero_ssa"].apply(
            temp_printer.width_manager.normalize_ssa_number
        )

    # Formata usando nomes de exibição
    display_names = temp_printer.width_manager.get_display_names()
    rename_map = {}
    for col in work_df.columns:
        short_name = display_names.get(col, col)
        # Trunca nomes muito longos
        if len(short_name) > 15:
            short_name = short_name[:12] + "..."
        rename_map[col] = short_name

    work_df = work_df.rename(columns=rename_map)

    # Renderiza com tabulate
    table_str = tabulate(
        work_df,
        headers=work_df.columns,
        tablefmt="presto",
        showindex=False,
        disable_numparse=True,
    )

    # Aplica destaque se necessário
    if highlight_terms:
        import re

        for term in highlight_terms:
            if term and len(term) > 1:
                if (
                    os.name != "nt"
                    and sys.stdout.isatty()
                    and not os.environ.get("NO_COLOR")
                ):
                    pattern = f"({re.escape(term)})"
                    replacement = "\\x1b[1m\\1\\x1b[0m"
                    table_str = re.sub(
                        pattern, replacement, table_str, flags=re.IGNORECASE
                    )

    return table_str
