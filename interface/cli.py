# interface/cli.py 20250725 160000 (v5.3 - Refatorado, Command Pattern, Integrado)
"""
Interface de Linha de Comando (CLI) para interação com o usuário.

Permite pesquisar, filtrar, ordenar, exportar e visualizar detalhes das SSAs.
"""

import os
import sys
import logging
import re
import pandas as pd
from typing import Tuple, List, Dict, Any

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

# --- Funções Auxiliares Refatoradas ---

def _cached_pretty_print_df(df: pd.DataFrame, display_map: dict, settings: dict, cache: dict, filter_terms=None):
    """
    Versão com cache do pretty_print_df para evitar reprocessamento de dados inalterados.
    Usa enhanced table printer quando habilitado via enhancement manager.
    """
    # Gera hash baseado no DataFrame e configurações
    df_hash = hash(str(df.shape) + str(list(df.columns)) + str(df.iloc[0].values.tobytes() if len(df) > 0 else ''))
    settings_hash = hash(str(sorted(settings.items())) if settings else '')
    display_hash = hash(str(sorted(display_map.items())))
    
    cache_key = f"{df_hash}:{settings_hash}:{display_hash}"
    
    # Se está em cache, apenas imprime (reutiliza saída capturada)
    if cache_key in cache:
        print(cache[cache_key])
        return
    
    # Usa enhanced table printer se habilitado
    if enhancement_manager.is_enhanced_printer_enabled():
        try:
            # Usa o Enhanced Table Printer
            printer = EnhancedTablePrinter()
            printer.print_dataframe_enhanced(df, display_map, settings, filter_terms=filter_terms)
            
            # Para manter compatibilidade com cache, salva uma entrada simples
            if len(cache) > 20:  # Limita a 20 entradas
                cache.clear()
            cache[cache_key] = "rendered_enhanced"  # Placeholder para cache
            return
            
        except Exception as e:
            logger.warning(f"Enhanced printer falhou, usando fallback: {e}")
    
    # Fallback para versão original
    import io
    import sys
    old_stdout = sys.stdout
    sys.stdout = captured_output = io.StringIO()
    
    try:
        pretty_print_df(df, display_map, settings)
        output = captured_output.getvalue()
        
        # Salva no cache (limita tamanho do cache para evitar memory leak)
        if len(cache) > 20:  # Limita a 20 entradas
            cache.clear()
        cache[cache_key] = output
        
        # Restaura stdout e imprime
        sys.stdout = old_stdout
        print(output, end='')
            
    finally:
        sys.stdout = old_stdout

def _apply_default_filters(df: pd.DataFrame, settings: dict) -> pd.DataFrame:
    """Aplica os filtros padrão definidos nas configurações."""
    import pandas as pd # Import local para evitar problemas de importacao circular
    default_filters = settings.get("default_filters", [])
    if default_filters:
        logger.debug(f"Aplicando filtros padrão: {default_filters}")
    default_mode = (settings.get('user_preferences') or {}).get('filter_mode_default', 'contains')
    
    # OTIMIZAÇÃO: Cache para parsing de termos padrão
    cache_key = f"{','.join(default_filters)}:{default_mode}"
    if not hasattr(_apply_default_filters, '_cache'):
        _apply_default_filters._cache = {}
    
    if cache_key not in _apply_default_filters._cache:
        _apply_default_filters._cache[cache_key] = parse_search_terms(default_filters, default_mode=default_mode)
    
    parsed = _apply_default_filters._cache[cache_key]
    return filter_dataframe(df, parsed)

def get_ssa_query() -> str:
    """
    Retorna a query customizada para mapear colunas corretamente.
    Usa os nomes de coluna normalizados da tabela atual.
    """
    return '''
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
    FROM ssas
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
        initial_df = query_db(db_path, '', get_ssa_query())
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
    """Exibe help inicial mais detalhado antes do prompt ficar disponível."""
    help_text = f"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    CONSULTA RÁPIDA DE SSAs v{APP_VERSION} - GUIA RÁPIDO                     ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║ PESQUISA                                                                      ║
║   • Digite termos separados por vírgula: ADM, MEL3, 2025                     ║
║   • Modos avançados: ^início, fim$, =exato, ~regex, !negativo               ║
║                                                                               ║
║ COMANDOS PRINCIPAIS                                                           ║
║   h ou ?      → Ajuda completa        q         → Sair                       ║
║   d <#>       → Detalhes da linha     v         → Voltar filtro              ║
║   r           → Reset completo        rescan    → Reimportar dados           ║
║   e <nome>    → Exportar resultados   c         → Configurações              ║
║                                                                               ║
║ ORGANIZAÇÃO                                                                   ║
║   ord <#>     → Ordenar crescente     ordi <#>  → Ordenar decrescente        ║
║   ordn <nome> → Ordenar por nome      cols     → Listar colunas              ║
║   x [termo]   → Remover filtro        f        → Ver filtros ativos          ║
║                                                                               ║
║ DICAS                                                                         ║
║   • Digite 'h' para help completo com exemplos                               ║
║   • Use 'd <número>' para ver detalhes de uma linha específica               ║
║   • Combine filtros para busca mais precisa                                  ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""
    print(help_text)

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
║   d <Nº>        → Mostra detalhes da SSA na linha <Nº> da tabela atual       ║
║   v             → Volta para o filtro anterior (desfaz último filtro)        ║
║   r             → Reseta todos os filtros e recarrega a base completa        ║
║   h, ?          → Mostra esta ajuda completa                                 ║
║   q, sair, exit → Sai do programa                                            ║
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
║   f, filtros    → Mostra os filtros atualmente aplicados                     ║
║   clear         → Limpa filtros do usuário (mantém filtros padrão)           ║
║   clearall      → Limpa TODOS os filtros (usuário + padrão) desta sessão     ║
║                                                                               ║
║ COMANDOS DE DADOS                                                             ║
║   rescan        → Reimporta arquivos Excel (modo compatibilidade)            ║
║   force-rescan  → Força reimportação completa (recomendado)                  ║
║                                                                               ║
║   ┌─ DIFERENÇA: rescan vs force-rescan ─────────────────────────────────────┐ ║
║   │ rescan:       Alias histórico, mesmo comportamento                      │ ║
║   │ force-rescan: Nome mais explícito, recomendado                          │ ║
║   │ AMBOS fazem:  Ignora cache, processa todos os arquivos novamente        │ ║
║   └─────────────────────────────────────────────────────────────────────────┘ ║
║                                                                               ║
║ COMANDOS DE EXPORTAÇÃO                                                        ║
║   e <nome>      → Exporta resultados atuais para XLSX e CSV                  ║
║                   Exemplo: 'e relatorio_mel' cria relatorio_mel.xlsx         ║
║                                                                               ║
║ COMANDOS DE CONFIGURAÇÃO                                                      ║
║   c             → Abre menu de configurações interativo                      ║
║                                                                               ║
║ MELHORIAS CLI (v3.0.5+)                                                      ║
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
    
    print(help_text)
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
        results_stack.pop()
        print("...filtro anterior restaurado.")
    else:
        print("Nenhum filtro anterior para restaurar.")

def _handle_reset(db_path: str, table_name: str, results_stack: list, display_map: dict, settings: dict, print_cache: dict):
    """Handler para o comando de resetar."""
    print("...todos os filtros foram zerados e a base completa (ou com filtros padrão) foi recarregada.")
    initial_df_reset, initial_filter_terms_reset = _get_initial_state(db_path, table_name, settings)
    results_stack.clear()
    results_stack.append((initial_df_reset, initial_filter_terms_reset))
    # Exibe o novo estado
    _cached_pretty_print_df(results_stack[-1][0], display_map, settings, print_cache, initial_filter_terms_reset)

def _handle_rescan(db_path: str, table_name: str, results_stack: list, display_map: dict, settings: dict, print_cache: dict):
    """Handler para o comando de reanalisar."""
    print("Forçando reanálise dos relatórios...")
    try:
        if run_importer_logic(force_import=True):
            print("Base de dados atualizada. Recarregando...")
            initial_df_rescan, initial_filter_terms_rescan = _get_initial_state(db_path, table_name, settings)
            results_stack.clear()
            results_stack.append((initial_df_rescan, initial_filter_terms_rescan))
            print("Dados recarregados.")
            # Chama a exibição após rescan
            _cached_pretty_print_df(results_stack[-1][0], display_map, settings, print_cache, None)
        else:
            print("Nenhuma alteração detectada durante o rescan.")
    except Exception as e:
        print(f"Erro durante o rescan: {e}")

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
            print(f"Resultados ordenados por '{col_name}' ({'asc' if ascending else 'desc'}).")
            _cached_pretty_print_df(sorted_df, display_map, settings, print_cache, None)
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
        print(f"Resultados ordenados por '{col_name}' ({'asc' if ascending else 'desc'}).")
        _cached_pretty_print_df(sorted_df, display_map, settings, print_cache, None)
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
            _cached_pretty_print_df(results_stack[-1][0], display_map, settings, print_cache, None)
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
        print(f"Removido termo '{term_to_remove}'. Filtro atual: {', '.join(remaining)}")
        _cached_pretty_print_df(new_df, display_map, settings, print_cache, None)
    else:
        # Sem termos restantes, volta ao estado anterior
        _handle_back(results_stack)
        if results_stack:
            _cached_pretty_print_df(results_stack[-1][0], display_map, settings, print_cache, None)

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

def _handle_clear_filters(results_stack: list, display_map: dict, settings: dict, print_cache: dict):
    """Limpa filtros do usuário voltando ao estado base (mantém filtros padrão)."""
    if not results_stack:
        print("Sem estado atual.")
        return
    base_state = results_stack[0]
    results_stack.clear()
    results_stack.append(base_state)
    print("Filtros do usuário limpos. Voltando ao estado base.")
    _cached_pretty_print_df(base_state[0], display_map, settings, print_cache, None)

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
    print("Todos os filtros foram limpos para esta sessão.")
    _cached_pretty_print_df(df, display_map, fresh_settings, print_cache, None)

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
    'toggle-debug': lambda: print(f"🔧 Debug CLI {'ATIVADO' if enhancement_manager.toggle_debug() else 'DESATIVADO'}"),
    'debug': lambda: print(f"🔧 Debug CLI {'ATIVADO' if enhancement_manager.toggle_debug() else 'DESATIVADO'}"),
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

    # --- Exibição Inicial (com help detalhado) ---
    print("Pesquisa Rápida de SSAs 3.0.5")
    print("")
    
    # Exibe help inicial detalhado
    _show_initial_help()
    
    if not initial_df.empty:
        total_ssas = len(initial_df)
        print(f"\nDADOS CARREGADOS: {total_ssas:,} SSAs disponíveis para consulta")
        print("" + "─" * 80)
        print(f"[{total_ssas} SSAs] Digite seus termos de busca ou comando:")
    else:
        print("\nNenhum dado disponível para exibição.")
        print("Dica: Digite 'rescan' para reimportar os dados ou 'h' para ajuda.")
        print("" + "─" * 80)
        print("[0 SSAs] Digite comando:")
        # Mesmo com dados vazios, entra no loop para permitir rescan, etc.
        

    # --- Loop Principal ---
    # Comandos que requerem lógica inline ou handlers não mapeados diretamente
    INLINE_COMMAND_PREFIXES = ['d', 'detalhe', 'e', 'exportar', 'ord', 'ordi', 'ordn', 'ordni', 'cols', 'x', 'f', 'filtros', 'clear', 'clearall']

    while True:
        try:
            # OTIMIZAÇÃO: Só recarrega configurações quando necessário
            if _config_changed:
                settings = load_settings() 
                display_map = load_display_mappings_integrity()
                _config_changed = False
            
            current_df, current_filter_terms = results_stack[-1]
            
            print("") # Linha em branco para separação visual
            filter_status_runtime_text = ""
            if current_filter_terms:
                filter_status_runtime_text = f" - Filtro(s) Aplicado(s): {', '.join(current_filter_terms)}"
            
            prompt_text = (
                f"[{len(current_df)} SSAs{filter_status_runtime_text}] Buscar termos separados por vírgula ou comando: "
            )
            user_input = input(prompt_text).strip()
            
            if not user_input:
                continue

            # --- NOVA LÓGICA: Comandos de 1 caractere sempre são comandos ---
            if len(user_input) == 1 and user_input.lower() in COMMAND_HANDLERS:
                command = user_input.lower()
                handler = COMMAND_HANDLERS[command]
                if command in ['v', 'voltar']:
                    handler(results_stack)
                elif command in ['r', 'resetar']:
                    handler(db_path, table_name, results_stack, display_map, settings, _print_cache)
                elif command in ['c', 'config']:
                    # OTIMIZAÇÃO: Sinaliza que configurações mudaram
                    display_map = handle_config_command()
                else:
                    # Handlers simples que não precisam de argumentos específicos do loop
                    handler()
                continue

            parts = user_input.lower().split()
            command = parts[0]

            # --- 1. Tratamento de Comandos Mapeados (palavras completas) ---
            if command in COMMAND_HANDLERS:
                handler = COMMAND_HANDLERS[command]
                # Chama handlers específicos com argumentos
                if command in ['v', 'voltar']:
                    handler(results_stack)
                elif command in ['r', 'resetar']:
                    handler(db_path, table_name, results_stack, display_map, settings, _print_cache)
                elif command in ['rescan']:
                    handler(db_path, table_name, results_stack, display_map, settings, _print_cache)
                elif command in ['c', 'config']:
                     # OTIMIZAÇÃO: Sinaliza que configurações mudaram
                     handler()
                     _config_changed = True
                     # Após configurar, força um refresh do estado e exibição
                     settings = load_settings()
                     display_map = load_display_mappings_integrity()
                     # Recarrega o estado inicial com as novas configurações
                     initial_df_after_config, initial_filter_terms_after_config = _get_initial_state(db_path, table_name, settings)
                     results_stack = [(initial_df_after_config, initial_filter_terms_after_config)]
                     _cached_pretty_print_df(initial_df_after_config, display_map, settings, _print_cache, None)
                else:
                    # Handlers simples que não precisam de argumentos específicos do loop
                    handler()

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
                elif command in ['f', 'filtros']:
                    _handle_show_filters(results_stack)
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
                            _cached_pretty_print_df(new_filtered_df, display_map, settings, _print_cache, combined_filter_terms)
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
