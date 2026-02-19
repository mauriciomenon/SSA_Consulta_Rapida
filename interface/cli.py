# ruff: noqa: E402
# interface/cli.py (CLI refatorada – Command Pattern, integrada)
"""
Interface de Linha de Comando (CLI) para interação com o usuário.

Permite pesquisar, filtrar, ordenar, exportar e visualizar detalhes das SSAs.
"""

import os
import sys
import math
import logging
import re
import pandas as pd
from collections import Counter
from typing import Tuple, List, Dict, Any, Optional, Callable, cast

# Adiciona o diretório raiz do projeto ao sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Importações relativas
from armazenamento.database import query_db
from core.app_logic import run_importer_logic, filter_dataframe, parse_search_terms
from core.config_manager import load_settings, handle_config_command, load_display_mappings_integrity
from interface.display import pretty_print_details
from interface.table_printer import pretty_print_df # Versão antiga como fallback
from interface.enhanced_table_printer import EnhancedTablePrinter
from interface.cli_enhancement_manager import enhancement_manager
from utils.version import get_app_version, get_app_version_long

# Configura logger específico para este módulo
logger = logging.getLogger(__name__)
APP_VERSION = get_app_version()
APP_VERSION_LONG = get_app_version_long()


# Rastreador de paginação por DataFrame (id -> estado retornado pelo printer)
CLI_PAGINATION_TRACKER: Dict[int, Dict[str, Any]] = {}
DEFAULT_FILTER_TERMS_CACHE: Dict[str, Any] = {}


def _reset_pagination_state(df: pd.DataFrame) -> None:
    CLI_PAGINATION_TRACKER[id(df)] = {
        'next_page': 0,
        'total_pages': 0,
        'rendered_pages': 0,
        'page_size': 0,
    }


def _update_pagination_state(df: pd.DataFrame, state: Optional[Dict[str, Any]]) -> None:
    if state is None:
        CLI_PAGINATION_TRACKER.pop(id(df), None)
        return
    CLI_PAGINATION_TRACKER[id(df)] = state


def _release_pagination_state(df: pd.DataFrame) -> None:
    CLI_PAGINATION_TRACKER.pop(id(df), None)


def _next_page_for(df: pd.DataFrame) -> int:
    state = CLI_PAGINATION_TRACKER.get(id(df))
    if not state:
        return 0
    next_page = state.get('next_page')
    if next_page is None:
        return int(state.get('total_pages', 0))
    return max(0, int(next_page))

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
            filter_text = ', '.join(str(term) for term in filter_terms if term)
        else:
            filter_text = str(filter_terms)
    else:
        filter_text = ''
    settings['_cli_filter_terms'] = filter_text

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
    except Exception:
        page_size = 20

    total_rows = len(df)
    total_pages = math.ceil(total_rows / page_size) if total_rows else 0
    if total_rows == 0:
        print("Nenhum resultado para exibir.")
        return {
            'next_page': None,
            'total_pages': 0,
            'rendered_pages': 0,
            'page_size': page_size,
        }

    effective_start = max(0, start_page)
    if total_pages and effective_start >= total_pages:
        print("Nenhuma nova página para exibir.")
        return {
            'next_page': None,
            'total_pages': total_pages,
            'rendered_pages': 0,
            'page_size': page_size,
        }

    start_index = effective_start * page_size
    if max_pages is None:
        rows_limit = total_rows - start_index
    else:
        rows_limit = page_size * max_pages
    end_index = start_index + max(0, rows_limit)
    subset = df.iloc[start_index:end_index]

    df_hash = hash(str(df.shape) + str(list(df.columns)) + str(df.iloc[0].values.tobytes() if total_rows > 0 else ''))
    settings_hash = hash(str(sorted(settings.items())))
    display_hash = hash(str(sorted(display_map.items())))
    filter_hash = hash(filter_text)
    page_hash = hash((effective_start, max_pages))
    cache_key = f"{df_hash}:{settings_hash}:{display_hash}:{filter_hash}:{page_hash}"

    if cache_key in cache:
        cached_output, cached_state = cache[cache_key]
        print(cached_output, end='')
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

    print(output, end='')

    rendered_rows = len(subset)
    rendered_pages = math.ceil(rendered_rows / page_size) if rendered_rows else 0
    next_page = effective_start + rendered_pages
    if next_page >= total_pages:
        next_page = None

    state = {
        'next_page': next_page,
        'total_pages': total_pages,
        'rendered_pages': rendered_pages,
        'page_size': page_size,
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

def _apply_default_filters(df: pd.DataFrame, settings: dict) -> pd.DataFrame:
    """Aplica os filtros padrão definidos nas configurações."""
    default_filters = settings.get("default_filters", [])
    if default_filters:
        logger.debug(f"Aplicando filtros padrão: {default_filters}")
    default_mode = (settings.get('user_preferences') or {}).get('filter_mode_default', 'contains')

    # OTIMIZAÇÃO: Cache para parsing de termos padrão
    cache_key = f"{','.join(default_filters)}:{default_mode}"
    if cache_key not in DEFAULT_FILTER_TERMS_CACHE:
        DEFAULT_FILTER_TERMS_CACHE[cache_key] = parse_search_terms(default_filters, default_mode=default_mode)

    parsed = DEFAULT_FILTER_TERMS_CACHE[cache_key]
    return filter_dataframe(df, parsed)

def get_ssa_query(table_name: str = 'ssa_table') -> str:
    """
    Retorna a query customizada para mapear colunas corretamente.
    Usa os nomes de coluna normalizados da tabela atual.
    """
    return f'''
    SELECT
        numero_ssa,
        situacao,
        derivada_de,
        localizacao_codigo,
        descricao_localizacao,
        equipamento,
        semana_cadastro,
        data_cadastro,
        descricao_ssa,
        setor_emissor,
        setor_executor,
        solicitante,
        servico_origem,
        grau_prioridade_emissao,
        grau_prioridade_planejamento,
        execucao_simples,
        responsavel_programacao,
        semana_programada,
        responsavel_execucao,
        descricao_execucao,
        id,
        sistema_origem,
        prazo_limite,
        tempo_disponivel,
        data_limite,
        tempo_excedido,
        desde,
        tempo_total,
        desde_1,
        total_tempo_tpe_planejado,
        total_tempo_tex_planejado,
        total_tempo_tpo_planejado,
        total_horas_programadas,
        execucao_parcial,
        anomalia,
        semana_executada,
        num_reprogramacoes
    FROM {table_name}
    '''

def _get_initial_state(
    db_path: str,
    table_name: str,
    settings: dict
) -> Tuple['pd.DataFrame', List[str]]:
    """
    Carrega o estado inicial do DataFrame e filtros.

    Returns:
        Tuple[pd.DataFrame, List[str]]: DataFrame inicial e lista de termos de filtro.
    """
    logger.debug("Carregando estado inicial...")
    try:
        initial_df = query_db(db_path, '', get_ssa_query(table_name))
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

def _show_initial_help():
    """Exibe help inicial mais detalhado antes do prompt ficar disponivel."""
    help_text = f"""
===============================================================================
CONSULTA RAPIDA de SSAs v{APP_VERSION}

PESQUISA
  - Separe termos por virgula (ex.: ADM, MEL3, 2025)
  - Termos simples procuram em qualquer parte; use =valor para coincidencia exata
  - Prefixos: ^inicio, fim$, =exato, ~regex, !negativo (podem ser combinados)
  - Exemplos: svp, !ste, mel4 -> contem "svp", exclui "STE", contem "mel4"
  - Tambem aceita comparacoes/regex (ex.: mmu2, prazo<=30, ^2025)

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
  x termo              Remover termo do filtro atual (ex.: x mel4)
  l                    Listar filtros ativos

DICAS
  - Filtros ativos aparecem acima do prompt; digite termos como: svp, !ste, mel4
  - Comandos rapidos: m (mais pagina), l (listar filtros), v (voltar), x termo (ex.: x mel4), h (ajuda)
  - Para continuar navegando apos a primeira pagina use m; para exibir tudo, use m z
===============================================================================
"""

    try:
        print(help_text)
    except UnicodeEncodeError as exc:
        logger.error("Erro de codificacao ao exibir texto de ajuda: %s", exc)
        fallback_text = f"""
===============================================================================
CONSULTA RAPIDA de SSAs v{APP_VERSION}

PESQUISA
  - Separe termos por virgula (ex.: ADM, MEL3, 2025)
  - Termos simples procuram em qualquer parte; use =valor para coincidencia exata
  - Prefixos: ^inicio, fim$, =exato, ~regex, !negativo (podem ser combinados)
  - Exemplos: svp, !ste, mel4 -> contem "svp", exclui "STE", contem "mel4"
  - Tambem aceita comparacoes/regex (ex.: mmu2, prazo<=30, ^2025)

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
  x termo              Remover termo do filtro atual (ex.: x mel4)
  l                    Listar filtros ativos

DICAS
  - Filtros ativos aparecem acima do prompt; digite termos como: svp, !ste, mel4
  - Comandos rapidos: m (mais pagina), l (listar filtros), v (voltar), x termo (ex.: x mel4), h (ajuda)
  - Para continuar navegando apos a primeira pagina use m; para exibir tudo, use m z
===============================================================================
"""
        print(fallback_text)
        logger.debug("Texto de ajuda fallback exibido com sucesso")
    else:
        logger.debug("Texto de ajuda exibido com sucesso")

def _handle_quit():
    """Handler para o comando de sair."""
    print("Saindo...")
    sys.exit(0)

def _handle_help():
    """Handler para o comando de ajuda."""
    help_text = f"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                      CONSULTA RÁPIDA DE SSAs v{APP_VERSION} - AJUDA COMPLETA                  ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║ COMANDOS DE PESQUISA E NAVEGAÇÃO                                              ║
║   termos (ex: svp, !ste, mel4) → Aplicam filtros cumulativos                ║
║   d <Nº>        → Mostra detalhes da SSA na linha <Nº> da tabela atual       ║
║   v             → Volta para o filtro anterior (desfaz último filtro)        ║
║   m             → Mostra a próxima página disponível                         ║
║   m z           → Mostra todas as páginas restantes                          ║
║   r             → Reseta todos os filtros e recarrega a base completa        ║
║   h, ?          → Mostra esta ajuda completa                                 ║
║   q, sair, exit → Sai do programa                                            ║
║   paginação     → Após a primeira página utilize m (mais) ou m z (tudo)      ║
║                                                                               ║
║ COMANDOS DE ORGANIZAÇÃO                                                       ║
║   ord <Nº>      → Ordena pela coluna de índice <Nº> (crescente)              ║
║   ordi <Nº>     → Ordena pela coluna de índice <Nº> (decrescente)            ║
║   ordn <nome>   → Ordena pela coluna com este nome (crescente)               ║
║   ordni <nome>  → Ordena pela coluna com este nome (decrescente)             ║
║   cols          → Lista as colunas visíveis com índices e nomes              ║
║                                                                               ║
║ COMANDOS DE FILTROS                                                           ║
║   x [termo]     → Remove termo específico; sem termo equivale a 'v'          ║
║   l, filtros    → Mostra os filtros atualmente aplicados                     ║
║   clear         → Limpa filtros do usuário (mantém filtros padrão)           ║
║   clearall      → Limpa TODOS os filtros (usuário + padrão) desta sessão     ║
║                                                                               ║
║ COMANDOS DE DADOS                                                             ║
║   rescan        → Reimporta arquivos Excel (modo compatibilidade)            ║
║   force-rescan  → Força reimportação completa (recomendado)                  ║
║                                                                               ║
║   +-- DIFERENCA: rescan vs force-rescan -------------------------------------+ ║
║   │ rescan:       Alias histórico, mesmo comportamento                      │ ║
║   │ force-rescan: Nome mais explícito, recomendado                          │ ║
║   │ AMBOS fazem:  Ignora cache, processa todos os arquivos novamente        │ ║
║   +--------------------------------------------------------------------------+ ║
║                                                                               ║
║ COMANDOS DE EXPORTAÇÃO                                                        ║
║   e <nome>      → Exporta resultados atuais para XLSX e CSV                  ║
║                   Exemplo: 'e relatorio_mel' cria relatorio_mel.xlsx         ║
║                                                                               ║
║ COMANDOS DE CONFIGURAÇÃO                                                      ║
║   c             → Abre menu de configurações interativo                      ║
║                                                                               ║
║ MELHORIAS CLI                                                                 ║
║   status-cli    → Status das melhorias implementadas                         ║
║   toggle-debug  → Liga/desliga modo debug do Enhanced Table Printer          ║
║   enhanced-on   → Ativa Enhanced Table Printer                               ║
║   enhanced-off  → Desativa Enhanced Table Printer (volta ao original)        ║
║                                                                               ║
║ PESQUISA AVANÇADA                                                             ║
║   Digite termos separados por vírgula para filtrar resultados:               ║
║   Exemplo: 'ADM, MEL3, 2025' → Situação ADM OU Executor MEL3 OU SSA 2025     ║
║                                                                               ║
║   MODOS AVANÇADOS POR TERMO (case-insensitive):                              ║
║   • contém (padrão): foo          → encontra "foobar", "barfoo"              ║
║   • começa com: ^foo              → encontra "foobar", não "barfoo"          ║
║   • termina com: foo$             → encontra "barfoo", não "foobar"          ║
║   • igual: =foo                   → encontra exatamente "foo"                ║
║   • regex: ~foo.*bar              → busca com expressão regular              ║
║   • negativos: !^adm, !$2025, !=fechado, !~cancel.*                          ║
║                                                                               ║
║ EXEMPLOS PRÁTICOS                                                             ║
║   ADM                    → Situações contendo "ADM"                          ║
║   ^MEL                   → Executores que começam com "MEL"                  ║
║   $2025                  → SSAs que terminam com "2025"                      ║
║   =STE                   → Situação exatamente "STE"                         ║
║   !cancelada             → Exclui SSAs canceladas                            ║
║   ~MEL[0-9]+             → Regex: MEL seguido de números                     ║
║   ADM, !cancelada        → Situação ADM, mas não canceladas                  ║
╚═══════════════════════════════════════════════════════════════════════════════╝

Digite qualquer tecla para continuar..."""

    try:
        print(help_text)
        logger.debug("Texto de ajuda exibido com sucesso")
    except UnicodeEncodeError as e:
        logger.error(f"Erro de codificação ao exibir texto de ajuda: {e}")
        # Fallback sem caracteres especiais
        fallback_text = f"""
================================ CONSULTA RÁPIDA de SSAs v{APP_VERSION} ================================

PESQUISA
  • Separe termos por virgula (ex.: ADM, MEL3, 2025)
  • Termos simples procuram em qualquer parte; use =valor para coincidencia exata
  • Prefixos: ^inicio, fim$, =exato, ~regex, !negativo (podem ser combinados)
  • Exemplos: svp, !ste, mel4 -> contem "svp", exclui "STE", contem "mel4"
  • Tambem aceita comparacoes/regex (ex.: mmu2, prazo<=30, ^2025)

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
  x termo              Remover termo do filtro atual (ex.: x mel4)
  l                    Listar filtros ativos

DICAS
  • Filtros ativos aparecem acima do prompt; digite termos como: svp, !ste, mel4
  • Comandos rapidos: m (mais pagina), l (listar filtros), v (voltar), x termo (ex.: x mel4), h (ajuda)
  • Para continuar navegando apos a primeira pagina use m; para exibir tudo, use m z
===============================================================================================
"""
        print(fallback_text)
        logger.debug("Texto de ajuda fallback exibido com sucesso")
    input()  # Pausa para o usuário ler

def _handle_details(parts: List[str], current_df: 'pd.DataFrame', display_map: dict):
    """Handler para o comando de detalhes."""
    try:
        if len(parts) < 2 or not parts[1].isdigit():
            print("Erro: use d <Nº da linha>. Exemplo: d 5")
            return
        row_index = int(parts[1]) - 1
        if 0 <= row_index < len(current_df):
            pretty_print_details(current_df.iloc[row_index], display_map)
        else:
            print("Erro: Número da linha inválido.")
    except Exception as e:
        print(f"Erro ao exibir detalhes: {e}")

def _show_ssa_details(ssa_series: 'pd.Series', display_map: dict):
    """Mostra detalhes de uma SSA específica."""
    try:
        print(f"\n--- Detalhes da SSA {ssa_series.get('numero_ssa', 'N/A')} ---")
        pretty_print_details(ssa_series, display_map)
    except Exception as e:
        print(f"Erro ao exibir detalhes da SSA: {e}")

def _handle_export(parts: List[str], current_df: 'pd.DataFrame', output_dir: str, display_map: dict):
    """Handler para o comando de exportar."""
    from exportacao import exporter # Import local para manter escopo
    if len(parts) < 2:
        print("Erro: Forneça um nome para os arquivos. Ex: -e meu_relatorio")
        return
    base_filename = parts[1]
    print(f"Iniciando exportação para arquivos com base '{base_filename}'...")
    try:
        exporter.export_dataframe(current_df, base_filename, output_dir, display_map)
        print("Exportação concluída.")
    except Exception as e:
        print(f"Erro durante a exportação: {e}")

def _handle_list_columns(current_df: 'pd.DataFrame', display_map: dict):
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
        if results_stack:
            _reset_pagination_state(results_stack[-1][0])
    else:
        print("Nenhum filtro anterior para restaurar.")

def _handle_reset(db_path: str, table_name: str, results_stack: list, display_map: dict, settings: dict, print_cache: dict):
    """Handler para o comando de resetar."""
    print("...todos os filtros foram zerados e a base completa (ou com filtros padrão) foi recarregada.")
    initial_df_reset, initial_filter_terms_reset = _get_initial_state(db_path, table_name, settings)
    results_stack.clear()
    results_stack.append((initial_df_reset, initial_filter_terms_reset))
    _reset_pagination_state(initial_df_reset)
    # Exibe o novo estado
    _render_single_page(
        results_stack[-1][0],
        display_map,
        settings,
        print_cache,
        initial_filter_terms_reset,
        start_page=0,
    )

def _handle_rescan(db_path: str, table_name: str, results_stack: list, display_map: dict, settings: dict, print_cache: dict):
    """Handler para o comando de reanalisar."""
    print("Forçando reanálise dos relatórios...")
    summary_counts: Counter = Counter()
    other_warnings: List[str] = []

    def _extract_first_number(text: str) -> int:
        match = re.search(r'(\d+)', text)
        return int(match.group(1)) if match else 0

    class _SummaryHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            if record.levelno < logging.WARNING:
                return
            message = record.getMessage()
            if 'registros inválidos' in message and 'Removidos' in message:
                summary_counts['invalid_removed'] += _extract_first_number(message)
            elif 'registros sem número de SSA' in message:
                summary_counts['missing_ssa'] += _extract_first_number(message)
            elif 'registros sem semana de cadastro' in message:
                summary_counts['missing_week'] += _extract_first_number(message)
            else:
                other_warnings.append(message)

    progress_state: Dict[str, Any] = {'displayed': False, 'total': 0, 'last_length': 0}

    def progress_callback(event: str, payload: Dict[str, Any]) -> None:
        if event == 'start':
            progress_state['total'] = payload.get('total', 0) or 0
            progress_state['displayed'] = False
            progress_state['last_length'] = 0
            if progress_state['total']:
                message = f"Forçando reanálise... 0/{progress_state['total']}"
                progress_state['displayed'] = True
                progress_state['last_length'] = len(message)
                sys.stdout.write(message)
                sys.stdout.flush()
        elif event == 'file':
            total = payload.get('total', progress_state.get('total', 0)) or 0
            index = payload.get('index', 0) + 1
            filename = payload.get('filename', '')
            message = f"Processando {index}/{total}: {filename}"
            progress_state['displayed'] = True
            progress_state['last_length'] = len(message)
            sys.stdout.write(f"\r{message}")
            sys.stdout.flush()
        elif event == 'finish':
            progress_state['finished'] = True

    handler = _SummaryHandler()
    handler.setLevel(logging.WARNING)
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)

    try:
        updated = run_importer_logic(force_import=True, progress_callback=progress_callback)
        summary_parts = []
        if summary_counts['invalid_removed']:
            summary_parts.append(f"Inválidos removidos: {summary_counts['invalid_removed']}")
        if summary_counts['missing_ssa']:
            summary_parts.append(f"Sem nº SSA: {summary_counts['missing_ssa']}")
        if summary_counts['missing_week']:
            summary_parts.append(f"Sem semana cadastro: {summary_counts['missing_week']}")
        if other_warnings:
            summary_parts.append(f"Outros avisos: {len(other_warnings)}")

        if summary_parts:
            summary_text = " • ".join(summary_parts)
        else:
            summary_text = "Sem avisos adicionais"

        summary_line = f"Importação concluída. {summary_text}. Logs: logs/app.log"
        if progress_state.get('displayed'):
            padding = ' ' * max(0, progress_state.get('last_length', 0) - len(summary_line))
            sys.stdout.write(f"\r{summary_line}{padding}\n")
        else:
            print(summary_line)

        if updated:
            print("Base de dados atualizada. Recarregando...")
            initial_df_rescan, initial_filter_terms_rescan = _get_initial_state(db_path, table_name, settings)
            results_stack.clear()
            CLI_PAGINATION_TRACKER.clear()
            results_stack.append((initial_df_rescan, initial_filter_terms_rescan))
            _reset_pagination_state(initial_df_rescan)
            print("Dados recarregados.")
            _render_single_page(
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

def _handle_sort(parts: List[str], results_stack: list, display_map: dict, settings: dict, ascending: bool, print_cache: dict):
    """Handler para os comandos de ordenação (-ord, -ordi)."""
    current_df, current_filter_terms = results_stack[-1]
    try:
        if len(parts) < 2 or not parts[1].isdigit():
            print("Erro: use -ord <Nº> ou -ordi <Nº>. Exemplo: -ord 3")
            return
        col_index = int(parts[1])

        # Obter colunas visíveis na ordem em que aparecem na tabela
        # Isso requer sincronização com table_printer, o que é complexo.
        # Uma abordagem mais simples é ordenar pelo índice da coluna no DataFrame original.
        # Para simplificar esta implementação, vamos ordenar pelas colunas do DataFrame atual.
        if 0 <= col_index <= len(current_df.columns):
            col_name = current_df.columns[col_index - 1] # Ajuste para 1-based index do usuário
            sorted_df = current_df.sort_values(by=col_name, ascending=ascending, na_position='last')
            # Empilha o resultado ordenado
            results_stack.append((sorted_df, current_filter_terms))
            _reset_pagination_state(sorted_df)
            print(f"Resultados ordenados por '{col_name}' ({'asc' if ascending else 'desc'}).")
            _render_single_page(
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

def _handle_sort_by_name(parts: List[str], results_stack: list, display_map: dict, settings: dict, ascending: bool, print_cache: dict):
    """Ordena por nome de coluna (interna ou de exibição)."""
    current_df, current_filter_terms = results_stack[-1]
    try:
        if len(parts) < 2:
            print("Erro: use -ordn <nome> ou -ordni <nome>.")
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
            print("Coluna não encontrada. Use -cols para ver as opções.")
            return
        sorted_df = current_df.sort_values(by=col_name, ascending=ascending, na_position='last')
        results_stack.append((sorted_df, current_filter_terms))
        _reset_pagination_state(sorted_df)
        print(f"Resultados ordenados por '{col_name}' ({'asc' if ascending else 'desc'}).")
        _render_single_page(
            sorted_df,
            display_map,
            settings,
            print_cache,
            current_filter_terms,
            start_page=0,
        )
    except Exception as e:
        print(f"Erro ao ordenar por nome: {e}")

def _handle_remove_filter(parts: List[str], results_stack: list, display_map: dict, settings: dict, print_cache: dict):
    """Remove um termo do filtro atual e re-aplica sobre o estado anterior.

    Uso: -x <termo>
    Sem termo: equivale a voltar (-v).
    """
    if len(results_stack) == 0:
        print("Sem estado atual.")
        return
    current_df, current_terms = results_stack[-1]
    # Sem termo -> volta
    if len(parts) < 2:
        _handle_back(results_stack)
        # Exibe topo após voltar, se houver
        if results_stack:
            top_df, top_terms = results_stack[-1]
            _reset_pagination_state(top_df)
            _render_single_page(
                top_df,
                display_map,
                settings,
                print_cache,
                top_terms,
                start_page=0,
            )
        return
    term_to_remove = parts[1].strip()
    if not current_terms:
        print("Nenhum termo de filtro atual para remover.")
        return
    remaining = [t for t in current_terms if t.lower() != term_to_remove.lower()]
    # Base para re-aplicar é o estado anterior, se existir; senão o mesmo current_df
    if len(results_stack) >= 2:
        base_df = results_stack[-2][0]
    else:
        base_df = current_df
    if remaining:
        new_df = filter_dataframe(base_df, remaining)
        results_stack[-1] = (new_df, remaining)
        _reset_pagination_state(new_df)
        print(f"Removido termo '{term_to_remove}'. Filtro atual: {', '.join(remaining)}")
        _render_single_page(
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
            _reset_pagination_state(top_df)
            _render_single_page(
                top_df,
                display_map,
                settings,
                print_cache,
                top_terms,
                start_page=0,
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
    neg = [t for t in terms if t.startswith('!') or t.startswith('-')]
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
    state = CLI_PAGINATION_TRACKER.get(id(current_df)) or {}
    next_page = state.get('next_page')
    total_pages = state.get('total_pages', 0)
    show_all = bool(args and args[0] in {'z', 'tudo', 'all'})
    if next_page is None or not total_pages or next_page >= total_pages:
        print("Nenhuma página adicional disponível.")
        return

    if show_all:
        current_page = next_page
        while current_page is not None and current_page < total_pages:
            state = _render_single_page(
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
            current_page = state.get('next_page')
        return

    _render_single_page(
        current_df,
        display_map,
        settings,
        print_cache,
        current_terms,
        start_page=next_page,
        max_pages=1,
    )


def _handle_clear_filters(results_stack: list, display_map: dict, settings: dict, print_cache: dict):
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
    _render_single_page(
        base_state[0],
        display_map,
        settings,
        print_cache,
        base_state[1],
        start_page=0,
    )

def _handle_clear_all_filters(db_path: str, table_name: str, results_stack: list, display_map: dict, settings: dict, print_cache: dict):
    """Limpa todos os filtros (incluindo padrão) recarregando a base sem aplicar default_filters."""
    if not results_stack:
        print("Sem estado atual.")
        return
    # Clona settings sem default_filters
    fresh_settings = dict(settings or {})
    fresh_settings['default_filters'] = []
    df = query_db(db_path, '', get_ssa_query())
    results_stack.clear()
    results_stack.append((df, []))
    CLI_PAGINATION_TRACKER.clear()
    _reset_pagination_state(df)
    print("Todos os filtros foram limpos para esta sessão.")
    _render_single_page(
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
    'q': _handle_quit,
    'sair': _handle_quit,
    'exit': _handle_quit,
    'quit': _handle_quit,
    'h': _handle_help,
    '?': _handle_help,
    'ajuda': _handle_help,
    'v': _handle_back,
    'voltar': _handle_back,
    'r': _handle_reset,
    'resetar': _handle_reset,
    'rescan': _handle_rescan,
    'c': handle_config_command, # Diretamente do config_manager
    'config': handle_config_command,
    # Comandos das melhorias CLI
    'status-cli': lambda: print(enhancement_manager.get_status_report()),
    'cli-status': lambda: print(enhancement_manager.get_status_report()),
    'toggle-debug': lambda: print(f"[Debug] Debug CLI {'ATIVADO' if enhancement_manager.toggle_debug() else 'DESATIVADO'}"),
    'debug': lambda: print(f"[Debug] Debug CLI {'ATIVADO' if enhancement_manager.toggle_debug() else 'DESATIVADO'}"),
    'enhanced-on': lambda: (enhancement_manager.enable_enhanced_printer(), print("Enhanced Table Printer ATIVADO")),
    'enable-enhanced': lambda: (enhancement_manager.enable_enhanced_printer(), print("Enhanced Table Printer ATIVADO")),
    'enhanced-off': lambda: (enhancement_manager.disable_enhanced_printer(), print("Enhanced Table Printer DESATIVADO")),
    'disable-enhanced': lambda: (enhancement_manager.disable_enhanced_printer(), print("Enhanced Table Printer DESATIVADO")),
}

def start_cli_loop(db_path: str, table_name: str):
    """Inicia o loop principal da interface de linha de comando."""
    logger.debug("Iniciando loop da CLI...")

    # OTIMIZAÇÃO: Cache inicial de configurações
    settings = load_settings()
    display_map = load_display_mappings_integrity()
    output_dir = os.path.join(project_root, 'docs_saida')

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
        'd', 'detalhe', 'e', 'exportar', 'ord', 'ordi', 'ordn', 'ordni',
        'cols', 'x', 'l', 'listar', 'filtros', 'm', 'mais', 'clear', 'clearall'
    ]

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

            print(
                "Comandos: digite termos separados por virgula (ex: svp, !ste, mel4) ou use m (mais pagina), l (listar filtros), v (voltar), x <termo> (ex: x mel4), h (ajuda)."
            )

            prompt_text = f"[{len(current_df)} SSAs] Buscar termos separados por vírgula ou comando: "
            user_input = input(prompt_text).strip()

            if not user_input:
                continue

            # --- NOVA LÓGICA: Comandos de 1 caractere sempre são comandos ---
            if len(user_input) == 1 and user_input.lower() in COMMAND_HANDLERS:
                command = user_input.lower()
                if command in ['v', 'voltar']:
                    _handle_back(results_stack)
                elif command in ['r', 'resetar']:
                    _handle_reset(db_path, table_name, results_stack, display_map, settings, _print_cache)
                elif command in ['rescan']:
                    _handle_rescan(db_path, table_name, results_stack, display_map, settings, _print_cache)
                elif command in ['c', 'config']:
                    # OTIMIZAÇÃO: Sinaliza que configurações mudaram
                    display_map = handle_config_command()
                else:
                    # Handlers simples que não precisam de argumentos específicos do loop
                    simple_handler = cast(Callable[[], Any], COMMAND_HANDLERS[command])
                    simple_handler()
                continue

            parts = user_input.lower().split()
            command = parts[0]

            # --- 1. Tratamento de Comandos Mapeados (palavras completas) ---
            if command in COMMAND_HANDLERS:
                # Chama handlers específicos com argumentos
                if command in ['v', 'voltar']:
                    _handle_back(results_stack)
                elif command in ['r', 'resetar']:
                    _handle_reset(db_path, table_name, results_stack, display_map, settings, _print_cache)
                elif command in ['rescan']:
                    _handle_rescan(db_path, table_name, results_stack, display_map, settings, _print_cache)
                elif command in ['c', 'config']:
                     # OTIMIZAÇÃO: Sinaliza que configurações mudaram
                     handle_config_command()
                     _config_changed = True
                     # Após configurar, força um refresh do estado e exibição
                     settings = load_settings()
                     display_map = load_display_mappings_integrity()
                     # Recarrega o estado inicial com as novas configurações
                     initial_df_after_config, initial_filter_terms_after_config = _get_initial_state(db_path, table_name, settings)
                     results_stack = [(initial_df_after_config, initial_filter_terms_after_config)]
                     CLI_PAGINATION_TRACKER.clear()
                     _reset_pagination_state(initial_df_after_config)
                     _render_single_page(
                         initial_df_after_config,
                         display_map,
                         settings,
                         _print_cache,
                         initial_filter_terms_after_config,
                         start_page=0,
                     )
                else:
                    # Handlers simples que não precisam de argumentos específicos do loop
                    simple_handler = cast(Callable[[], Any], COMMAND_HANDLERS[command])
                    simple_handler()

            # --- 2. Tratamento de Comandos com Lógica Inline ou Argumentos ---
            elif command in INLINE_COMMAND_PREFIXES:
                if command in ['d', 'detalhe']:
                    _handle_details(parts, current_df, display_map)
                elif command in ['e', 'exportar']:
                    _handle_export(parts, current_df, output_dir, display_map)
                elif command in ['ord', 'ordi']:
                    ascending = (command == 'ord')
                    _handle_sort(parts, results_stack, display_map, settings, ascending, _print_cache)
                elif command in ['ordn', 'ordni']:
                    ascending = (command == 'ordn')
                    _handle_sort_by_name(parts, results_stack, display_map, settings, ascending, _print_cache)
                elif command in ['cols']:
                    _handle_list_columns(current_df, display_map)
                elif command in ['x']:
                    _handle_remove_filter(parts, results_stack, display_map, settings, _print_cache)
                elif command in ['clear']:
                    _handle_clear_filters(results_stack, display_map, settings, _print_cache)
                elif command in ['l', 'listar', 'filtros']:
                    _handle_show_filters(results_stack)
                elif command in ['m', 'mais']:
                    _handle_show_more(results_stack, display_map, settings, _print_cache, parts[1:])
                elif command in ['clearall']:
                    _handle_clear_all_filters(db_path, table_name, results_stack, display_map, settings, _print_cache)

            # --- 3. Tratamento como Pesquisa/Busca ou Detalhe direto ---
            else:
                # Se input tem mais de 1 caractere, primeiro verifica se é número SSA direto para detalhes
                if len(user_input) > 1:
                    # Verifica se é um número SSA direto (começa com 2025 ou é numérico)
                    if user_input.strip().isdigit() or user_input.strip().startswith('2025'):
                        ssa_number = user_input.strip()
                        # Procura SSA específica na tabela atual
                        matching_rows = current_df[current_df['numero_ssa'].astype(str).str.contains(ssa_number, na=False)]
                        if not matching_rows.empty:
                            # Mostra detalhes da primeira ocorrência
                            _show_ssa_details(matching_rows.iloc[0], display_map)
                            continue
                        else:
                            print(f"SSA {ssa_number} não encontrada na tabela atual.")
                            continue

                    # Se não é SSA, aplica filtro acumulativo (mais de 1 caractere = filtro)
                    # Aceita separação por vírgulas OU espaços (um ou mais)
                    parts_terms = re.split(r"[\s,]+", user_input)
                    processed_search_terms = [term.strip() for term in parts_terms if term.strip()]
                    normalized_terms: list[str] = []
                    for term in processed_search_terms:
                        lower = term.lower()
                        if lower in {'ou', 'or', 'v'}:
                            normalized_terms.append('OU')
                        elif lower in {'and', 'e', '^'}:
                            normalized_terms.append('E')
                        else:
                            normalized_terms.append(term)
                    processed_search_terms = normalized_terms
                    if processed_search_terms: # Só filtra se houver termos
                        default_mode = (settings.get('user_preferences') or {}).get('filter_mode_default', 'contains')

                        # OTIMIZAÇÃO: Cache para parse_search_terms
                        cache_key = f"{','.join(processed_search_terms)}:{default_mode}"
                        if cache_key not in _parse_cache:
                            _parse_cache[cache_key] = parse_search_terms(processed_search_terms, default_mode=default_mode)
                        parsed_terms = _parse_cache[cache_key]

                        # Aplica filtro acumulativo sobre os dados atuais
                        new_filtered_df = filter_dataframe(current_df, parsed_terms)
                        if new_filtered_df.empty:
                            print("Nenhum resultado encontrado para o filtro. Tente outros termos.")
                        else:
                            # Combina termos atuais com os novos para o filtro acumulativo
                            combined_filter_terms = current_filter_terms + processed_search_terms
                            results_stack.append((new_filtered_df, combined_filter_terms))
                            _reset_pagination_state(new_filtered_df)
                            _render_single_page(
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
