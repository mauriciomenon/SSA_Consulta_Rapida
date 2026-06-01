# ruff: noqa: E402
# interface/cli.py (CLI refatorada – Command Pattern, integrada)
"""
Interface de Linha de Comando (CLI) para interação com o usuário.

Permite pesquisar, filtrar, ordenar, exportar e visualizar detalhes das SSAs.
"""

import hashlib
import logging
import math
import os
import re
import sys
import textwrap
import unicodedata
from collections import Counter
from typing import Any, Callable, Dict, List, Optional, Tuple, cast

import pandas as pd

# Adiciona o diretório raiz do projeto ao sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Importações relativas
from armazenamento.database import get_ssa_query, query_db
from core.app_logic import filter_dataframe, parse_search_terms, run_importer_logic
from core.config_manager import (
    load_display_mappings_integrity,
    load_settings,
)
from interface.config_command import handle_config_command
from interface.cli_enhancement_manager import enhancement_manager
from interface.display import pretty_print_details
from interface.enhanced_table_printer import EnhancedTablePrinter
from interface.table_printer import pretty_print_df  # Versão antiga como fallback
from shared.numero_ssa import normalize_strict as normalize_numero_ssa_strict
from utils.path_safety import PathSafetyError, ensure_path_is_allowed
from utils.robust_logging import get_robust_logger
from utils.version import get_app_version, get_app_version_long

# Configura logger específico para este módulo
logger = get_robust_logger().get_logger(__name__, "cli")
APP_VERSION = get_app_version()
APP_VERSION_LONG = get_app_version_long()


# Rastreador de paginação por DataFrame (id -> estado retornado pelo printer)
CLI_PAGINATION_TRACKER: Dict[int, Dict[str, Any]] = {}
DEFAULT_FILTER_TERMS_CACHE: Dict[str, Any] = {}
RAW_ANSI_ESCAPE = "\x1b"


class _CLIPaginationTrackerManager:
    def __init__(self, store: Dict[int, Dict[str, Any]]) -> None:
        self._store = store
        self._prune_tick = 0
        self._next_key = 1

    def key_for(self, df: pd.DataFrame, *, create: bool = True) -> int | None:
        attrs = getattr(df, "attrs", None)
        if isinstance(attrs, dict):
            existing = attrs.get("_cli_pagination_key")
            if isinstance(existing, int):
                return existing
            if create:
                key = self._next_key
                self._next_key += 1
                attrs["_cli_pagination_key"] = key
                return key
        return id(df) if create else None

    def reset(self, df: pd.DataFrame) -> None:
        key = self.key_for(df)
        if key is None:
            return
        self._store[key] = {
            "next_page": 0,
            "total_pages": 0,
            "rendered_pages": 0,
            "page_size": 0,
        }

    def update(self, df: pd.DataFrame, state: Optional[Dict[str, Any]]) -> None:
        key = self.key_for(df)
        if key is None:
            return
        if state is None:
            self._store.pop(key, None)
            return
        self._store[key] = state

    def release(self, df: pd.DataFrame) -> None:
        key = self.key_for(df, create=False)
        if key is not None:
            self._store.pop(key, None)

    def prune_for_stack(self, results_stack: list, *, force: bool = False) -> None:
        active_ids = {
            key
            for entry in results_stack
            if entry
            for key in [self.key_for(entry[0], create=False)]
            if key is not None
        }
        # Hot-path guard: skip full scan when tracker is near active stack size.
        if not force and len(self._store) <= len(active_ids) + 4:
            return
        # Amortize pruning to avoid repeated full scans on interactive commands.
        self._prune_tick = (self._prune_tick + 1) % 4
        if not force and self._prune_tick != 0 and len(self._store) <= 512:
            return
        for state_key in list(self._store.keys()):
            if state_key not in active_ids:
                self._store.pop(state_key, None)

    def next_page_for(self, df: pd.DataFrame) -> int:
        state = self.state_for(df)
        if not state:
            return 0
        next_page = state.get("next_page")
        if next_page is None:
            return 0
        return max(0, int(next_page))

    def state_for(self, df: pd.DataFrame) -> Dict[str, Any]:
        key = self.key_for(df, create=False)
        if key is None:
            return {}
        return self._store.get(key) or {}


_PAGINATION_TRACKER_MANAGER = _CLIPaginationTrackerManager(CLI_PAGINATION_TRACKER)


def _reset_pagination_state(df: pd.DataFrame) -> None:
    _PAGINATION_TRACKER_MANAGER.reset(df)


def _update_pagination_state(df: pd.DataFrame, state: Optional[Dict[str, Any]]) -> None:
    _PAGINATION_TRACKER_MANAGER.update(df, state)


def _release_pagination_state(df: pd.DataFrame) -> None:
    _PAGINATION_TRACKER_MANAGER.release(df)


def _prune_pagination_tracker_for_stack(
    results_stack: list, *, force: bool = False
) -> None:
    _PAGINATION_TRACKER_MANAGER.prune_for_stack(results_stack, force=force)


def _next_page_for(df: pd.DataFrame) -> int:
    return _PAGINATION_TRACKER_MANAGER.next_page_for(df)


def _pagination_state_key_for_df(df: pd.DataFrame) -> int | None:
    return _PAGINATION_TRACKER_MANAGER.key_for(df, create=False)


def _last_rendered_page_for(df: pd.DataFrame) -> int:
    state = _PAGINATION_TRACKER_MANAGER.state_for(df)
    total_pages = max(0, int(state.get("total_pages", 0)))
    rendered_pages = max(0, int(state.get("rendered_pages", 0)))
    if rendered_pages == 0:
        return 0
    next_page = state.get("next_page")
    if next_page is None:
        return max(0, total_pages - rendered_pages)
    return max(0, int(next_page) - rendered_pages)


# --- Funções Auxiliares Refatoradas ---


def _cached_pretty_print_df(
    df: pd.DataFrame,
    display_map: dict,
    settings: dict,
    cache: dict,
    filter_terms=None,
    *,
    start_page: int = 0,
    max_pages: Optional[int] = None,
):
    """
    Versão com cache do pretty_print_df para evitar reprocessamento de dados inalterados.
    Usa enhanced table printer quando habilitado via enhancement manager.
    """
    settings = settings.copy() if settings else {}
    if filter_terms:
        if isinstance(filter_terms, (list, tuple)):
            filter_text = ", ".join(str(term) for term in filter_terms if term)
        else:
            filter_text = str(filter_terms)
    else:
        filter_text = ""
    settings["_cli_filter_terms"] = filter_text

    # Usa enhanced table printer se habilitado
    if enhancement_manager.is_enhanced_printer_enabled():
        try:
            # Usa o Enhanced Table Printer
            printer = EnhancedTablePrinter()
            return printer.print_dataframe_enhanced(
                df,
                display_map,
                settings,
                filter_terms=filter_terms,
                start_page=start_page,
                max_pages=max_pages,
            )

        except Exception as e:
            logger.warning(f"Enhanced printer falhou, usando fallback: {e}")

    # Fallback para versão original
    helper_printer = EnhancedTablePrinter()
    try:
        page_size = max(1, helper_printer.get_terminal_size()[0] - 8)
    except (AttributeError, OSError, TypeError, ValueError):
        page_size = 20

    total_rows = len(df)
    total_pages = math.ceil(total_rows / page_size) if total_rows else 0
    if total_rows == 0:
        print("Nenhum resultado para exibir.")
        return {
            "next_page": None,
            "total_pages": 0,
            "rendered_pages": 0,
            "page_size": page_size,
        }

    effective_start = max(0, start_page)
    if total_pages and effective_start >= total_pages:
        print("Nenhuma nova página para exibir.")
        return {
            "next_page": None,
            "total_pages": total_pages,
            "rendered_pages": 0,
            "page_size": page_size,
        }

    start_index = effective_start * page_size
    if max_pages is None:
        rows_limit = total_rows - start_index
    else:
        rows_limit = page_size * max_pages
    end_index = start_index + max(0, rows_limit)
    subset = df.iloc[start_index:end_index]

    subset_hasher = hashlib.blake2b(digest_size=16)
    subset_hasher.update(str(df.shape).encode("utf-8"))
    subset_hasher.update(str(total_rows).encode("utf-8"))
    subset_hasher.update(str(total_pages).encode("utf-8"))
    subset_hasher.update(str(list(df.columns)).encode("utf-8"))
    if not subset.empty:
        subset_hash_values = tuple(
            int(value)
            for value in pd.util.hash_pandas_object(subset, index=True).tolist()
        )
        subset_hasher.update(str(subset_hash_values).encode("utf-8"))
    df_hash = subset_hasher.hexdigest()
    settings_hash = hash(str(sorted(settings.items())))
    display_hash = hash(str(sorted(display_map.items())))
    filter_hash = hash(filter_text)
    page_hash = hash((effective_start, max_pages))
    cache_key = f"{df_hash}:{settings_hash}:{display_hash}:{filter_hash}:{page_hash}"

    if cache_key in cache:
        cached_output, cached_state = cache[cache_key]
        print(cached_output, end="")
        return cached_state

    import io
    import sys

    old_stdout = sys.stdout
    sys.stdout = captured_output = io.StringIO()
    try:
        pretty_print_df(subset, display_map, settings)
        output = captured_output.getvalue()
    finally:
        sys.stdout = old_stdout

    print(output, end="")

    rendered_rows = len(subset)
    rendered_pages = math.ceil(rendered_rows / page_size) if rendered_rows else 0
    next_page = effective_start + rendered_pages
    if next_page >= total_pages:
        next_page = None

    state = {
        "next_page": next_page,
        "total_pages": total_pages,
        "rendered_pages": rendered_pages,
        "page_size": page_size,
    }

    if len(cache) > 20:
        cache.clear()
    cache[cache_key] = (output, state)

    return state


def _render_single_page(
    df: pd.DataFrame,
    display_map: dict,
    settings: dict,
    cache: dict,
    filter_terms: Optional[List[str]],
    *,
    start_page: Optional[int] = None,
    max_pages: Optional[int] = 1,
) -> Optional[Dict[str, Any]]:
    page_start = _next_page_for(df) if start_page is None else max(0, start_page)
    state = _cached_pretty_print_df(
        df,
        display_map,
        settings,
        cache,
        filter_terms,
        start_page=page_start,
        max_pages=max_pages,
    )
    _update_pagination_state(df, state)
    return state


def _exit_if_requested(state: Optional[Dict[str, Any]]) -> None:
    if state and state.get("exit_requested"):
        _handle_quit()


def _render_cli_page(
    df: pd.DataFrame,
    display_map: dict,
    settings: dict,
    cache: dict,
    filter_terms: Optional[List[str]],
    *,
    start_page: Optional[int] = None,
    max_pages: Optional[int] = 1,
) -> Optional[Dict[str, Any]]:
    state = _render_single_page(
        df,
        display_map,
        settings,
        cache,
        filter_terms,
        start_page=start_page,
        max_pages=max_pages,
    )
    _exit_if_requested(state)
    return state


def _apply_default_filters(df: pd.DataFrame, settings: dict) -> pd.DataFrame:
    """Aplica os filtros padrão definidos nas configurações."""
    default_filters = settings.get("default_filters", [])
    if default_filters:
        logger.debug(f"Aplicando filtros padrão: {default_filters}")
    default_mode = (settings.get("user_preferences") or {}).get(
        "filter_mode_default", "contains"
    )

    # OTIMIZAÇÃO: Cache para parsing de termos padrão
    cache_key = f"{','.join(default_filters)}:{default_mode}"
    if cache_key not in DEFAULT_FILTER_TERMS_CACHE:
        DEFAULT_FILTER_TERMS_CACHE[cache_key] = parse_search_terms(
            default_filters, default_mode=default_mode
        )

    parsed = DEFAULT_FILTER_TERMS_CACHE[cache_key]
    return filter_dataframe(df, parsed)


def _get_initial_state(
    db_path: str, table_name: str, settings: dict
) -> Tuple["pd.DataFrame", List[str]]:
    """
    Carrega o estado inicial do DataFrame e filtros.

    Returns:
        Tuple[pd.DataFrame, List[str]]: DataFrame inicial e lista de termos de filtro.
    """
    logger.debug("Carregando estado inicial...")
    try:
        initial_df = query_db(db_path, "", get_ssa_query(table_name))
        initial_df = _apply_default_filters(initial_df, settings)
        default_filter_terms = settings.get("default_filters", [])
        logger.debug("Estado inicial carregado.")
        return initial_df, default_filter_terms
    except Exception as e:
        logger.error(f"Erro ao carregar estado inicial: {e}")
        # Em caso de erro, retorna um DataFrame vazio
        import pandas as pd

        return pd.DataFrame(), []


# --- Handlers de Comandos ---


def _wrap_cli_help_text(text: str, *, width: int) -> str:
    wrapped_lines: list[str] = []
    for raw_line in text.strip("\n").splitlines():
        if not raw_line:
            wrapped_lines.append("")
            continue
        stripped = raw_line.strip()
        if len(raw_line) <= width or (stripped and len(set(stripped)) == 1):
            wrapped_lines.append(raw_line)
            continue
        indent = raw_line[: len(raw_line) - len(raw_line.lstrip())]
        wrapped_lines.append(
            textwrap.fill(
                stripped,
                width=width,
                initial_indent=indent,
                subsequent_indent=indent,
                break_long_words=False,
                break_on_hyphens=False,
            )
        )
    return "\n".join(wrapped_lines) + "\n"


def _build_cli_plain_help_text(
    *,
    bullet: str = "-",
    line_char: str = "=",
    detailed: bool = False,
) -> str:
    line = line_char * 79
    body = f"""
{line}
CONSULTA RAPIDA de SSAs v{APP_VERSION}

PESQUISA
  {bullet} Separe termos por virgula (ex.: ADM, MEL3, 2025)
  {bullet} Termos simples procuram em qualquer parte; use =valor para coincidencia exata
  {bullet} Prefixos: ^inicio, fim$, =exato, ~regex, !negativo (podem ser combinados)
  {bullet} Exemplos: svp, !ste, mel4 -> contem "svp", exclui "STE", contem "mel4"
  {bullet} Tambem aceita comparacoes/regex (ex.: mmu2, prazo<=30, ^2025)

COMANDOS PRINCIPAIS
  h ou ?    Ajuda completa
  q         Sair da aplicacao
  d #       Mostrar detalhe da linha (use o numero exibido na primeira coluna)
  v         Desfazer o ultimo filtro aplicado
  m         Mostrar a proxima pagina de resultados
  m z       Mostrar todas as paginas restantes
  r         Limpar filtros ativos (mantem dados carregados)
  rescan    Reimportar todos os arquivos Excel
  e nome    Exportar resultado (ex.: e relatorio -> relatorio.csv/.xlsx)
  c         Abrir menu de configuracoes

ORGANIZACAO
  ord / ordi  #        Ordenar coluna pelo indice mostrado em cols (crescente / decrescente)
  ordn / ordni nome    Ordenar coluna pelo nome exato (crescente / decrescente)
  cols                 Listar colunas exibidas e respectivos indices
  x <termo>            Remover termo do filtro atual (ex.: x mel4)
  l                    Listar filtros ativos

DICAS
  {bullet} Filtros ativos aparecem acima do prompt; digite termos como: svp, !ste, mel4
  {bullet} Busca: termos por virgula; !termo exclui
  {bullet} Comandos: d # detalhe, v voltar, x <termo> remover, m mais, l listar, h ajuda
  {bullet} Para continuar navegando apos a primeira pagina use m; para exibir tudo, use m z
"""

    if not detailed:
        return _wrap_cli_help_text(f"{body}{line}\n", width=len(line))

    return _wrap_cli_help_text(
        f"""{body}
COMANDOS DE FILTROS
  clear       Limpa filtros do usuario e volta ao estado base
  clearall    Limpa todos os filtros da sessao atual

COMANDOS DE DADOS
  rescan          Reimporta arquivos Excel
  force-rescan    Alias explicito para rescan

COMANDOS DE MELHORIAS CLI
  status-cli      Mostra status das melhorias implementadas
  toggle-debug    Liga/desliga debug do Enhanced Table Printer
  enhanced-on     Ativa Enhanced Table Printer
  enhanced-off    Desativa Enhanced Table Printer

PESQUISA AVANCADA
  {bullet} Mantem o mesmo contrato da busca inicial: termos separados por virgula e cumulativos
  {bullet} OU/OR/AND/E/v continuam literais na busca
  {bullet} Modos por termo: foo, ^foo, foo$, =foo, ~regex, !foo
  {bullet} Exemplos: svp, !ste, mel4 | ^MEL | =STE | ~MEL[0-9]+
{line}

Pressione Enter para continuar...
""",
        width=len(line),
    )


def _build_cli_prompt_hint_lines() -> tuple[str, str]:
    """Retorna as duas linhas curtas de orientacao do prompt principal."""
    return (
        "Busca: termos por virgula; !termo exclui.",
        "Cmds: d # detalhe | v voltar | x <termo> remover | m | l | h | q.",
    )


def _show_initial_help():
    """Exibe help inicial mais detalhado antes do prompt ficar disponivel."""
    help_text = _build_cli_plain_help_text()

    try:
        print(help_text)
    except UnicodeEncodeError as exc:
        logger.error("Erro de codificacao ao exibir texto de ajuda: %s", exc)
        fallback_text = _build_cli_plain_help_text()
        print(fallback_text)
        logger.debug("Texto de ajuda fallback exibido com sucesso")
    else:
        logger.debug("Texto de ajuda exibido com sucesso")


def _is_cli_non_interactive() -> bool:
    env_flag = os.environ.get("SSA_NON_INTERACTIVE", "").strip().lower()
    if env_flag not in ("", "0", "false", "no"):
        return True
    try:
        return not bool(sys.stdin is not None and sys.stdin.isatty())
    except (AttributeError, OSError, TypeError, ValueError):
        return True


def _to_ascii_cli_text(text: str) -> str:
    text = text.replace("•", "-")
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return ascii_text


def _print_cli_status_report() -> None:
    report = enhancement_manager.get_status_report()
    print(_to_ascii_cli_text(report))


def _toggle_cli_debug_command() -> None:
    enabled = enhancement_manager.toggle_debug()
    print(f"Debug CLI {'ativado' if enabled else 'desativado'}")


def _set_enhanced_cli_enabled(enabled: bool) -> None:
    if enabled:
        enhancement_manager.enable_enhanced_printer()
        print("Enhanced Table Printer ativado")
    else:
        enhancement_manager.disable_enhanced_printer()
        print("Enhanced Table Printer desativado")


def _handle_quit():
    """Handler para o comando de sair."""
    print("Saindo...")
    sys.exit(0)


def _handle_help():
    """Handler para o comando de ajuda."""
    help_text = _build_cli_plain_help_text(detailed=True)

    try:
        print(help_text)
        logger.debug("Texto de ajuda exibido com sucesso")
    except UnicodeEncodeError as e:
        logger.error(f"Erro de codificação ao exibir texto de ajuda: {e}")
        fallback_text = _build_cli_plain_help_text(
            bullet="*",
            line_char="=",
            detailed=True,
        )
        print(fallback_text)
        logger.debug("Texto de ajuda fallback exibido com sucesso")
    if not _is_cli_non_interactive():
        input()  # Pausa para o usuario ler


def _handle_details(parts: List[str], current_df: "pd.DataFrame", display_map: dict):
    """Handler para o comando de detalhes."""
    try:
        if len(parts) < 2 or not parts[1].isdigit():
            print("Erro: use d #. Exemplo: d 5")
            return
        row_index = int(parts[1]) - 1
        if 0 <= row_index < len(current_df):
            pretty_print_details(current_df.iloc[row_index], display_map)
        else:
            print("Erro: Número da linha inválido.")
    except Exception as e:
        print(f"Erro ao exibir detalhes: {e}")


def _show_ssa_details(ssa_series: "pd.Series", display_map: dict):
    """Mostra detalhes de uma SSA específica."""
    try:
        print(f"\n--- Detalhes da SSA {ssa_series.get('numero_ssa', 'N/A')} ---")
        pretty_print_details(ssa_series, display_map)
    except Exception as e:
        print(f"Erro ao exibir detalhes da SSA: {e}")


def _handle_export(
    parts: List[str], current_df: "pd.DataFrame", output_dir: str, display_map: dict
):
    """Handler para o comando de exportar."""
    from exportacao import exporter  # Import local para manter escopo

    if len(parts) < 2:
        print("Erro: Forneca um nome para os arquivos. Ex: e meu_relatorio")
        return
    base_filename = parts[1].strip()
    if not base_filename or base_filename != os.path.basename(base_filename):
        print("Erro: nome de exportacao invalido.")
        return
    if not re.fullmatch(r"[A-Za-z0-9._-]+", base_filename):
        print(
            "Erro: use apenas letras, numeros, ponto, underscore e hifen no nome do arquivo."
        )
        return
    print(f"Iniciando exportação para arquivos com base '{base_filename}'...")
    try:
        ensure_path_is_allowed(
            output_dir, purpose="diretorio de exportacao", expect_directory=True
        )
        exporter.export_dataframe(current_df, base_filename, output_dir, display_map)
        print("Exportação concluída.")
    except PathSafetyError as e:
        print(f"Erro durante a exportação: {e}")
    except Exception as e:
        print(f"Erro durante a exportação: {e}")


def _handle_list_columns(current_df: "pd.DataFrame", display_map: dict):
    """Lista colunas atuais com índices (1-based) e nomes de exibição."""
    if current_df is None or current_df.empty:
        print("Sem dados.")
        return
    print("\nColunas disponíveis:")
    for idx, col in enumerate(current_df.columns, start=1):
        display = display_map.get(col, col)
        print(f"  {idx:>2}: {col}  ->  {display}")


def _handle_back(results_stack: list):
    """Handler para o comando de voltar."""
    if len(results_stack) > 1:
        popped_df, _ = results_stack.pop()
        _release_pagination_state(popped_df)
        print("...filtro anterior restaurado.")
        _prune_pagination_tracker_for_stack(results_stack)
    else:
        print("Nenhum filtro anterior para restaurar.")


def _handle_reset(
    db_path: str,
    table_name: str,
    results_stack: list,
    display_map: dict,
    settings: dict,
    print_cache: dict,
):
    """Handler para o comando de resetar."""
    print(
        "...todos os filtros foram zerados e a base completa (ou com filtros padrão) foi recarregada."
    )
    initial_df_reset, initial_filter_terms_reset = _get_initial_state(
        db_path, table_name, settings
    )
    results_stack.clear()
    CLI_PAGINATION_TRACKER.clear()
    results_stack.append((initial_df_reset, initial_filter_terms_reset))
    _reset_pagination_state(initial_df_reset)
    # Exibe o novo estado
    _render_cli_page(
        results_stack[-1][0],
        display_map,
        settings,
        print_cache,
        initial_filter_terms_reset,
        start_page=0,
    )


def _handle_rescan(
    db_path: str,
    table_name: str,
    results_stack: list,
    display_map: dict,
    settings: dict,
    print_cache: dict,
):
    """Handler para o comando de reanalisar."""
    if _is_cli_non_interactive():
        print(
            "Rescan indisponivel em sessao non-interactive. Execute manualmente na CLI interativa."
        )
        return

    print("Forçando reanálise dos relatórios...")
    summary_counts: Counter = Counter()
    other_warnings: List[str] = []

    def _extract_first_number(text: str) -> int:
        match = re.search(r"(\d+)", text)
        return int(match.group(1)) if match else 0

    class _SummaryHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            if record.levelno < logging.WARNING:
                return
            message = record.getMessage()
            if "registros inválidos" in message and "Removidos" in message:
                summary_counts["invalid_removed"] += _extract_first_number(message)
            elif "registros sem número de SSA" in message:
                summary_counts["missing_ssa"] += _extract_first_number(message)
            elif "registros sem semana de cadastro" in message:
                summary_counts["missing_week"] += _extract_first_number(message)
            else:
                other_warnings.append(message)

    progress_state: Dict[str, Any] = {"displayed": False, "total": 0, "last_length": 0}

    def progress_callback(event: str, payload: Dict[str, Any]) -> None:
        if event == "start":
            progress_state["total"] = payload.get("total", 0) or 0
            progress_state["displayed"] = False
            progress_state["last_length"] = 0
            if progress_state["total"]:
                message = f"Forçando reanálise... 0/{progress_state['total']}"
                progress_state["displayed"] = True
                progress_state["last_length"] = len(message)
                sys.stdout.write(message)
                sys.stdout.flush()
        elif event == "file":
            total = payload.get("total", progress_state.get("total", 0)) or 0
            index = payload.get("index", 0) + 1
            filename = payload.get("filename", "")
            message = f"Processando {index}/{total}: {filename}"
            progress_state["displayed"] = True
            progress_state["last_length"] = len(message)
            sys.stdout.write(f"\r{message}")
            sys.stdout.flush()
        elif event == "finish":
            progress_state["finished"] = True

    handler = _SummaryHandler()
    handler.setLevel(logging.WARNING)
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)

    try:
        updated = run_importer_logic(
            force_import=True, progress_callback=progress_callback
        )
        summary_parts = []
        if summary_counts["invalid_removed"]:
            summary_parts.append(
                f"Inválidos removidos: {summary_counts['invalid_removed']}"
            )
        if summary_counts["missing_ssa"]:
            summary_parts.append(f"Sem nº SSA: {summary_counts['missing_ssa']}")
        if summary_counts["missing_week"]:
            summary_parts.append(
                f"Sem semana cadastro: {summary_counts['missing_week']}"
            )
        if other_warnings:
            summary_parts.append(f"Outros avisos: {len(other_warnings)}")

        if summary_parts:
            summary_text = " • ".join(summary_parts)
        else:
            summary_text = "Sem avisos adicionais"

        summary_line = f"Importação concluída. {summary_text}. Logs: logs/app.log"
        if progress_state.get("displayed"):
            padding = " " * max(
                0, progress_state.get("last_length", 0) - len(summary_line)
            )
            sys.stdout.write(f"\r{summary_line}{padding}\n")
        else:
            print(summary_line)

        if updated:
            print("Base de dados atualizada. Recarregando...")
            initial_df_rescan, initial_filter_terms_rescan = _get_initial_state(
                db_path, table_name, settings
            )
            results_stack.clear()
            CLI_PAGINATION_TRACKER.clear()
            results_stack.append((initial_df_rescan, initial_filter_terms_rescan))
            _reset_pagination_state(initial_df_rescan)
            print("Dados recarregados.")
            _render_cli_page(
                results_stack[-1][0],
                display_map,
                settings,
                print_cache,
                initial_filter_terms_rescan,
                start_page=0,
            )
        else:
            print("Nenhuma alteração detectada durante o rescan.")
    except Exception as e:
        print(f"Erro durante o rescan: {e}")
    finally:
        root_logger.removeHandler(handler)


def _handle_sort(
    parts: List[str],
    results_stack: list,
    display_map: dict,
    settings: dict,
    ascending: bool,
    print_cache: dict,
):
    """Handler para os comandos de ordenacao (ord, ordi)."""
    current_df, current_filter_terms = results_stack[-1]
    try:
        if len(parts) < 2 or not parts[1].isdigit():
            print("Erro: use ord # ou ordi #. Exemplo: ord 3")
            return
        col_index = int(parts[1])

        # Obter colunas visíveis na ordem em que aparecem na tabela
        # Isso requer sincronização com table_printer, o que é complexo.
        # Uma abordagem mais simples é ordenar pelo índice da coluna no DataFrame original.
        # Para simplificar esta implementação, vamos ordenar pelas colunas do DataFrame atual.
        if 1 <= col_index <= len(current_df.columns):
            col_name = current_df.columns[
                col_index - 1
            ]  # Ajuste para 1-based index do usuário
            sorted_df = current_df.sort_values(
                by=col_name, ascending=ascending, na_position="last"
            )
            # Empilha o resultado ordenado
            results_stack.append((sorted_df, current_filter_terms))
            _reset_pagination_state(sorted_df)
            print(
                f"Resultados ordenados por '{col_name}' ({'asc' if ascending else 'desc'})."
            )
            _render_cli_page(
                sorted_df,
                display_map,
                settings,
                print_cache,
                current_filter_terms,
                start_page=0,
            )
        else:
            print("Erro: Índice da coluna inválido.")
    except Exception as e:
        print(f"Erro ao ordenar: {e}")


def _handle_sort_by_name(
    parts: List[str],
    results_stack: list,
    display_map: dict,
    settings: dict,
    ascending: bool,
    print_cache: dict,
):
    """Ordena por nome de coluna (interna ou de exibição)."""
    current_df, current_filter_terms = results_stack[-1]
    try:
        if len(parts) < 2:
            print("Erro: use ordn <nome> ou ordni <nome>.")
            return
        name = parts[1]
        # Mapeia display->interno
        inverse_map = {v.lower(): k for k, v in display_map.items()}
        # Tenta casar interno direto
        if name in current_df.columns:
            col_name = name
        else:
            # Tenta casar display insensitive
            col_name = inverse_map.get(name.lower())
        if not col_name or col_name not in current_df.columns:
            print("Coluna nao encontrada. Use cols para ver as opcoes.")
            return
        sorted_df = current_df.sort_values(
            by=col_name, ascending=ascending, na_position="last"
        )
        results_stack.append((sorted_df, current_filter_terms))
        _reset_pagination_state(sorted_df)
        print(
            f"Resultados ordenados por '{col_name}' ({'asc' if ascending else 'desc'})."
        )
        _render_cli_page(
            sorted_df,
            display_map,
            settings,
            print_cache,
            current_filter_terms,
            start_page=0,
        )
    except Exception as e:
        print(f"Erro ao ordenar por nome: {e}")


def _handle_remove_filter(
    parts: List[str],
    results_stack: list,
    display_map: dict,
    settings: dict,
    print_cache: dict,
):
    """Remove um termo do filtro atual e re-aplica sobre o estado anterior.

    Uso: x <termo>
    Sem termo: mostra mensagem de uso.
    """
    if len(results_stack) == 0:
        print("Sem estado atual.")
        return
    current_df, current_terms = results_stack[-1]
    if len(parts) < 2:
        print("Erro: use x <termo>. Exemplo: x mel4")
        return
    term_to_remove = parts[1].strip()
    if not current_terms:
        print("Nenhum termo de filtro atual para remover.")
        return
    remaining = [t for t in current_terms if t.lower() != term_to_remove.lower()]
    # Otimizacao: remocao LIFO pode reaplicar do estado anterior (menor).
    # Para remocao fora de ordem, reaplica da base para nao manter filtro removido.
    remove_key = term_to_remove.lower()
    is_lifo_remove = bool(current_terms) and (
        current_terms[-1].lower() == remove_key
        and all(t.lower() != remove_key for t in current_terms[:-1])
    )
    if is_lifo_remove and len(results_stack) >= 2:
        base_df = results_stack[-2][0]
    else:
        base_df = results_stack[0][0] if results_stack else current_df
    if remaining:
        new_df = filter_dataframe(base_df, remaining)
        results_stack[-1] = (new_df, remaining)
        _reset_pagination_state(new_df)
        _prune_pagination_tracker_for_stack(results_stack, force=True)
        print(
            f"Removido termo '{term_to_remove}'. Filtro atual: {', '.join(remaining)}"
        )
        _render_cli_page(
            new_df,
            display_map,
            settings,
            print_cache,
            remaining,
            start_page=0,
        )
    else:
        # Sem termos restantes, volta ao estado anterior
        _handle_back(results_stack)
        if results_stack:
            top_df, top_terms = results_stack[-1]
            _prune_pagination_tracker_for_stack(results_stack, force=True)
            _render_cli_page(
                top_df,
                display_map,
                settings,
                print_cache,
                top_terms,
                start_page=_last_rendered_page_for(top_df),
            )


def _handle_show_filters(results_stack: list):
    """Exibe os filtros atualmente aplicados."""
    if not results_stack:
        print("Sem estado atual.")
        return
    terms = results_stack[-1][1] or []
    if not terms:
        print("Nenhum filtro aplicado.")
        return
    neg = [t for t in terms if t.startswith("!") or t.startswith("-")]
    pos = [t for t in terms if t not in neg]
    print("Filtros atuais:")
    if pos:
        print("  + ", ", ".join(pos))
    if neg:
        print("  - ", ", ".join(neg))


def _handle_show_more(
    results_stack: list,
    display_map: dict,
    settings: dict,
    print_cache: dict,
    args: List[str],
) -> None:
    """Exibe a próxima página de resultados utilizando o estado atual."""
    if not results_stack:
        print("Sem estado atual.")
        return
    current_df, current_terms = results_stack[-1]
    state = _PAGINATION_TRACKER_MANAGER.state_for(current_df)
    next_page = state.get("next_page")
    total_pages = state.get("total_pages", 0)
    show_all = bool(args and args[0] in {"z", "tudo", "all"})
    if show_all and _is_cli_non_interactive():
        print(
            "Comando 'm z' indisponivel em sessao non-interactive. Use 'm' na CLI interativa."
        )
        return
    if next_page is None or not total_pages or next_page >= total_pages:
        print("Nenhuma página adicional disponível.")
        return

    if show_all:
        current_page = next_page
        while current_page is not None and current_page < total_pages:
            state = _render_cli_page(
                current_df,
                display_map,
                settings,
                print_cache,
                current_terms,
                start_page=current_page,
                max_pages=1,
            )
            if not state:
                break
            current_page = state.get("next_page")
        return

    _render_cli_page(
        current_df,
        display_map,
        settings,
        print_cache,
        current_terms,
        start_page=next_page,
        max_pages=1,
    )


def _handle_clear_filters(
    results_stack: list, display_map: dict, settings: dict, print_cache: dict
):
    """Limpa filtros do usuário voltando ao estado base (mantém filtros padrão)."""
    if not results_stack:
        print("Sem estado atual.")
        return
    base_state = results_stack[0]
    results_stack.clear()
    results_stack.append(base_state)
    CLI_PAGINATION_TRACKER.clear()
    _reset_pagination_state(base_state[0])
    print("Filtros do usuário limpos. Voltando ao estado base.")
    _render_cli_page(
        base_state[0],
        display_map,
        settings,
        print_cache,
        base_state[1],
        start_page=0,
    )


def _handle_clear_all_filters(
    db_path: str,
    table_name: str,
    results_stack: list,
    display_map: dict,
    settings: dict,
    print_cache: dict,
):
    """Limpa todos os filtros (incluindo padrão) recarregando a base sem aplicar default_filters."""
    if not results_stack:
        print("Sem estado atual.")
        return
    # Clona settings sem default_filters
    fresh_settings = dict(settings or {})
    fresh_settings["default_filters"] = []
    df = query_db(db_path, "", get_ssa_query(table_name))
    results_stack.clear()
    results_stack.append((df, []))
    CLI_PAGINATION_TRACKER.clear()
    _reset_pagination_state(df)
    print("Todos os filtros foram limpos para esta sessão.")
    _render_cli_page(
        df,
        display_map,
        fresh_settings,
        print_cache,
        [],
        start_page=0,
    )


# --- Loop Principal Refatorado ---

# Mapeamento de comandos para funções
COMMAND_HANDLERS = {
    "q": _handle_quit,
    "qq": _handle_quit,
    "sair": _handle_quit,
    "exit": _handle_quit,
    "quit": _handle_quit,
    "h": _handle_help,
    "?": _handle_help,
    "ajuda": _handle_help,
    "v": _handle_back,
    "voltar": _handle_back,
    "r": _handle_reset,
    "resetar": _handle_reset,
    "rescan": _handle_rescan,
    "force-rescan": _handle_rescan,
    "c": handle_config_command,  # Diretamente do config_manager
    "config": handle_config_command,
    # Comandos das melhorias CLI
    "status-cli": _print_cli_status_report,
    "cli-status": _print_cli_status_report,
    "toggle-debug": _toggle_cli_debug_command,
    "debug": _toggle_cli_debug_command,
    "enhanced-on": lambda: _set_enhanced_cli_enabled(True),
    "enable-enhanced": lambda: _set_enhanced_cli_enabled(True),
    "enhanced-off": lambda: _set_enhanced_cli_enabled(False),
    "disable-enhanced": lambda: _set_enhanced_cli_enabled(False),
}


def start_cli_loop(db_path: str, table_name: str):
    """Inicia o loop principal da interface de linha de comando."""
    logger.debug("Iniciando loop da CLI...")

    # OTIMIZAÇÃO: Cache inicial de configurações
    settings = load_settings()
    display_map = load_display_mappings_integrity()
    output_dir = os.path.join(project_root, "docs_saida")

    # Flags para controle de cache
    _config_changed = False
    _parse_cache = {}  # Cache para parse_search_terms
    _print_cache = {}  # Cache para pretty_print_df

    # --- Estado Inicial ---
    initial_df, initial_filter_terms = _get_initial_state(db_path, table_name, settings)
    results_stack = [(initial_df, initial_filter_terms)]
    _reset_pagination_state(initial_df)

    # --- Exibição Inicial (com help detalhado) ---
    print("")

    # Exibe help inicial detalhado
    _show_initial_help()

    if not initial_df.empty:
        total_ssas = len(initial_df)
        print(f"\nDADOS CARREGADOS: {total_ssas:,} SSAs disponíveis para consulta")
        print("-" * 80)
        print(f"[{total_ssas} SSAs] Digite seus termos de busca ou comando:")
    else:
        print("\nNenhum dado disponível para exibição.")
        print("Dica: Digite 'rescan' para reimportar os dados ou 'h' para ajuda.")
        print("-" * 80)
        print("[0 SSAs] Digite comando:")
        # Mesmo com dados vazios, entra no loop para permitir rescan, etc.

    # --- Loop Principal ---
    # Comandos que requerem lógica inline ou handlers não mapeados diretamente
    INLINE_COMMAND_PREFIXES = [
        "d",
        "detalhe",
        "e",
        "exportar",
        "ord",
        "ordi",
        "ordn",
        "ordni",
        "cols",
        "x",
        "l",
        "listar",
        "filtros",
        "m",
        "mais",
        "clear",
        "clearall",
    ]

    def _refresh_after_config_change() -> None:
        nonlocal settings, display_map, results_stack, _config_changed
        previous_default_filters = list(settings.get("default_filters") or [])
        handle_config_command()
        _config_changed = True
        settings = load_settings()
        display_map = load_display_mappings_integrity()
        current_default_filters = list(settings.get("default_filters") or [])
        if not results_stack:
            return

        # Recarrega base apenas quando filtros padrao mudam; evita custo desnecessario.
        if current_default_filters != previous_default_filters:
            previous_base_terms = list(results_stack[0][1] or [])
            previous_current_terms = list(results_stack[-1][1] or [])
            preserved_user_terms: list[str] = []
            base_len = len(previous_base_terms)
            if (
                base_len <= len(previous_current_terms)
                and previous_current_terms[:base_len] == previous_base_terms
            ):
                preserved_user_terms = previous_current_terms[base_len:]
            refreshed_base_df, refreshed_base_terms = _get_initial_state(
                db_path, table_name, settings
            )
            if preserved_user_terms:
                refreshed_df = filter_dataframe(refreshed_base_df, preserved_user_terms)
                refreshed_terms = refreshed_base_terms + preserved_user_terms
            else:
                refreshed_df = refreshed_base_df
                refreshed_terms = refreshed_base_terms
            results_stack = [(refreshed_df, refreshed_terms)]
        else:
            refreshed_df, refreshed_terms = results_stack[-1]

        CLI_PAGINATION_TRACKER.clear()
        _reset_pagination_state(refreshed_df)
        _render_cli_page(
            refreshed_df,
            display_map,
            settings,
            _print_cache,
            refreshed_terms,
            start_page=0,
        )

    def _run_registered_command(command: str) -> None:
        if command in ["v", "voltar"]:
            _handle_back(results_stack)
            if results_stack:
                top_df, top_terms = results_stack[-1]
                _render_cli_page(
                    top_df,
                    display_map,
                    settings,
                    _print_cache,
                    top_terms,
                    start_page=_last_rendered_page_for(top_df),
                )
            return
        if command in ["r", "resetar"]:
            _handle_reset(
                db_path, table_name, results_stack, display_map, settings, _print_cache
            )
            return
        if command in ["rescan", "force-rescan"]:
            _handle_rescan(
                db_path, table_name, results_stack, display_map, settings, _print_cache
            )
            return
        if command in ["c", "config"]:
            _refresh_after_config_change()
            return
        simple_handler = cast(Callable[[], Any], COMMAND_HANDLERS[command])
        simple_handler()

    while True:
        try:
            # OTIMIZAÇÃO: Só recarrega configurações quando necessário
            if _config_changed:
                settings = load_settings()
                display_map = load_display_mappings_integrity()
                _config_changed = False

            current_df, current_filter_terms = results_stack[-1]

            print("")  # Linha em branco para separação visual

            if current_filter_terms:
                print(f"Filtros ativos: {', '.join(current_filter_terms)}")
            else:
                print("Filtros ativos: (nenhum)")

            prompt_hint_line, prompt_help_line = _build_cli_prompt_hint_lines()
            print(prompt_hint_line)
            print(prompt_help_line)

            prompt_text = (
                f"[{len(current_df)} SSAs] Buscar termos por virgula ou comando: "
            )
            raw_user_input = input(prompt_text)
            if RAW_ANSI_ESCAPE in raw_user_input:
                print(
                    "Entrada ignorada: tecla de direcao nao foi processada pelo "
                    "terminal. Digite o filtro novamente."
                )
                continue
            user_input = raw_user_input.strip()

            if not user_input:
                continue

            # --- NOVA LÓGICA: Comandos de 1 caractere sempre são comandos ---
            if len(user_input) == 1 and user_input.lower() in COMMAND_HANDLERS:
                command = user_input.lower()
                _run_registered_command(command)
                continue

            parts = user_input.lower().split()
            command = parts[0]

            # --- 1. Tratamento de Comandos Mapeados (palavras completas) ---
            if command in COMMAND_HANDLERS:
                _run_registered_command(command)

            # --- 2. Tratamento de Comandos com Lógica Inline ou Argumentos ---
            elif command in INLINE_COMMAND_PREFIXES:
                if command in ["d", "detalhe"]:
                    _handle_details(parts, current_df, display_map)
                elif command in ["e", "exportar"]:
                    _handle_export(parts, current_df, output_dir, display_map)
                elif command in ["ord", "ordi"]:
                    ascending = command == "ord"
                    _handle_sort(
                        parts,
                        results_stack,
                        display_map,
                        settings,
                        ascending,
                        _print_cache,
                    )
                elif command in ["ordn", "ordni"]:
                    ascending = command == "ordn"
                    _handle_sort_by_name(
                        parts,
                        results_stack,
                        display_map,
                        settings,
                        ascending,
                        _print_cache,
                    )
                elif command in ["cols"]:
                    _handle_list_columns(current_df, display_map)
                elif command in ["x"]:
                    _handle_remove_filter(
                        parts, results_stack, display_map, settings, _print_cache
                    )
                elif command in ["clear"]:
                    _handle_clear_filters(
                        results_stack, display_map, settings, _print_cache
                    )
                elif command in ["l", "listar", "filtros"]:
                    _handle_show_filters(results_stack)
                elif command in ["m", "mais"]:
                    _handle_show_more(
                        results_stack, display_map, settings, _print_cache, parts[1:]
                    )
                elif command in ["clearall"]:
                    _handle_clear_all_filters(
                        db_path,
                        table_name,
                        results_stack,
                        display_map,
                        settings,
                        _print_cache,
                    )

            # --- 3. Tratamento como Pesquisa/Busca ou Detalhe direto ---
            else:
                # Se input tem mais de 1 caractere, primeiro verifica se é número SSA direto para detalhes
                if len(user_input) > 1:
                    ssa_number = user_input.strip()
                    normalized_ssa = normalize_numero_ssa_strict(ssa_number)
                    if (
                        normalized_ssa
                        and ssa_number.isdigit()
                        and len(ssa_number) == len(normalized_ssa)
                    ):
                        if "numero_ssa" in current_df.columns:
                            numero_series = current_df["numero_ssa"].astype(str)
                            # Procura SSA específica na tabela atual
                            match_mask = numero_series.eq(normalized_ssa)
                            matching_rows = current_df[match_mask]
                            if not matching_rows.empty:
                                # Mostra detalhes da primeira ocorrência
                                _show_ssa_details(matching_rows.iloc[0], display_map)
                                continue
                            print(f"SSA {ssa_number} não encontrada na tabela atual.")
                            continue

                    # Se não é SSA, aplica filtro acumulativo conforme o contrato atual:
                    # termos separados por virgula, sem reinterpretar operadores como OU/E.
                    processed_search_terms = [
                        term.strip() for term in user_input.split(",") if term.strip()
                    ]
                    if processed_search_terms:  # Só filtra se houver termos
                        default_mode = (settings.get("user_preferences") or {}).get(
                            "filter_mode_default", "contains"
                        )

                        # OTIMIZAÇÃO: Cache para parse_search_terms
                        cache_key = f"{','.join(processed_search_terms)}:{default_mode}"
                        if cache_key not in _parse_cache:
                            _parse_cache[cache_key] = parse_search_terms(
                                processed_search_terms, default_mode=default_mode
                            )
                        parsed_terms = _parse_cache[cache_key]

                        # Aplica filtro acumulativo sobre os dados atuais
                        new_filtered_df = filter_dataframe(current_df, parsed_terms)
                        if new_filtered_df.empty:
                            print(
                                "Nenhum resultado encontrado para o filtro. Tente outros termos."
                            )
                        else:
                            # Combina termos atuais com os novos para o filtro acumulativo
                            combined_filter_terms = (
                                current_filter_terms + processed_search_terms
                            )
                            results_stack.append(
                                (new_filtered_df, combined_filter_terms)
                            )
                            _reset_pagination_state(new_filtered_df)
                            _render_cli_page(
                                new_filtered_df,
                                display_map,
                                settings,
                                _print_cache,
                                combined_filter_terms,
                                start_page=0,
                            )
                    else:
                        # Se o usuário digitou algo que não é comando nem termo (só espaços?), apenas continua
                        continue
                else:
                    # Input de 1 caractere que não é comando mapeado - ignora
                    print("Comando inválido.")

        except KeyboardInterrupt:
            print("\nOperação interrompida pelo usuário. Saindo...")
            sys.exit(0)
        except Exception as e:
            logger.error(f"Erro inesperado no loop da CLI: {e}", exc_info=True)
            print(f"Ocorreu um erro inesperado: {e}. A aplicação será encerrada.")
            sys.exit(1)
