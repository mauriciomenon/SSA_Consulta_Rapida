# interface/cli.py 20250725 160000 (v5.3 - Refatorado, Command Pattern, Integrado)
"""
Interface de Linha de Comando (CLI) para interação com o usuário.

Permite pesquisar, filtrar, ordenar, exportar e visualizar detalhes das SSAs.
"""

import os
import sys
import logging
import pandas as pd
from typing import Tuple, List, Dict, Any

# Adiciona o diretório raiz do projeto ao sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Importações relativas
from armazenamento.database import query_db
from core.app_logic import run_importer_logic, filter_dataframe
from core.config_manager import load_settings, handle_config_command
from interface.display import pretty_print_details
from interface.table_printer import pretty_print_df # Importa a versão revisada

# Configura logger específico para este módulo
logger = logging.getLogger(__name__)
APP_VERSION = "4.0.0"

# --- Funções Auxiliares Refatoradas ---

def _apply_default_filters(df: pd.DataFrame, settings: dict) -> pd.DataFrame:
    """Aplica os filtros padrão definidos nas configurações."""
    import pandas as pd # Import local para evitar problemas de importacao circular
    default_filters = settings.get("default_filters", [])
    if default_filters:
        logger.debug(f"Aplicando filtros padrão: {default_filters}")
        return filter_dataframe(df, default_filters)
    return df

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
        initial_df = query_db(db_path, table_name)
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

def _handle_quit():
    """Handler para o comando de sair."""
    print("Saindo...")
    sys.exit(0)

def _handle_help():
    """Handler para o comando de ajuda."""
    help_text = f"""
--- Ajuda da Consulta Rápida de SSAs v{APP_VERSION} ---
Comandos disponíveis:
  -d <Nº>        : Mostra detalhes da SSA na linha <Nº> da tabela atual.
  -v             : Volta para o filtro anterior.
  -e <nome>      : Exporta os resultados atuais para XLSX e CSV com o <nome> base.
  -r             : Reseta todos os filtros e recarrega a base completa.
  -rescan        : Reimporta todos os arquivos Excel e recarrega os dados.
  -c             : Abre o menu de configurações.
  -ord <Nº>      : Ordena pela coluna de índice <Nº> (crescente).
  -ordi <Nº>     : Ordena pela coluna de índice <Nº> (decrescente).
  -h             : Mostra esta ajuda.
  -q, sair, exit : Sai do programa.
Pesquisa:
  Digite um ou mais termos separados por vírgula para filtrar os resultados.
  Exemplo: 'ADM, MEL3, 2025' filtra por Situação ADM, Executor MEL3 ou Nº SSA 2025.
"""
    print(help_text)

def _handle_details(parts: List[str], current_df: 'pd.DataFrame', display_map: dict):
    """Handler para o comando de detalhes."""
    try:
        if len(parts) < 2 or not parts[1].isdigit():
            print("Erro: use -d <Nº da linha>. Exemplo: -d 5")
            return
        row_index = int(parts[1]) - 1
        if 0 <= row_index < len(current_df):
            pretty_print_details(current_df.iloc[row_index], display_map)
        else:
            print("Erro: Número da linha inválido.")
    except Exception as e:
        print(f"Erro ao exibir detalhes: {e}")

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

def _handle_back(results_stack: list):
    """Handler para o comando de voltar."""
    if len(results_stack) > 1:
        results_stack.pop()
        print("...filtro anterior restaurado.")
    else:
        print("Nenhum filtro anterior para restaurar.")

def _handle_reset(db_path: str, table_name: str, results_stack: list, display_map: dict, settings: dict):
    """Handler para o comando de resetar."""
    print("...todos os filtros foram zerados e a base completa (ou com filtros padrão) foi recarregada.")
    initial_df_reset, initial_filter_terms_reset = _get_initial_state(db_path, table_name, settings)
    results_stack.clear()
    results_stack.append((initial_df_reset, initial_filter_terms_reset))
    # Exibe o novo estado
    pretty_print_df(results_stack[-1][0], display_map, settings)

def _handle_rescan(db_path: str, table_name: str, results_stack: list, display_map: dict, settings: dict):
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
            pretty_print_df(results_stack[-1][0], display_map, settings)
        else:
            print("Nenhuma alteração detectada durante o rescan.")
    except Exception as e:
        print(f"Erro durante o rescan: {e}")

def _handle_sort(parts: List[str], results_stack: list, display_map: dict, settings: dict, ascending: bool):
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
            pretty_print_df(sorted_df, display_map, settings)
        else:
            print("Erro: Índice da coluna inválido.")
    except Exception as e:
        print(f"Erro ao ordenar: {e}")

# --- Loop Principal Refatorado ---

# Mapeamento de comandos para funções
COMMAND_HANDLERS = {
    '-q': _handle_quit,
    'sair': _handle_quit,
    'exit': _handle_quit,
    'quit': _handle_quit,
    '-h': _handle_help,
    'ajuda': _handle_help,
    '-v': _handle_back,
    'voltar': _handle_back,
    '-r': _handle_reset,
    'resetar': _handle_reset,
    '-rescan': _handle_rescan,
    '-c': handle_config_command, # Diretamente do config_manager
    'config': handle_config_command,
}

def start_cli_loop(db_path: str, table_name: str):
    """Inicia o loop principal da interface de linha de comando."""
    logger.debug("Iniciando loop da CLI...")
    
    settings = load_settings()
    display_map = settings.get("display_mappings", {})
    output_dir = os.path.join(project_root, 'docs_saida')
    
    # --- Estado Inicial ---
    initial_df, initial_filter_terms = _get_initial_state(db_path, table_name, settings)
    results_stack = [(initial_df, initial_filter_terms)]

    # --- Exibição Inicial ---
    print(f"\n--- Consulta Rápida de SSAs {APP_VERSION} ---")
    print(f"Base de dados carregada: {len(initial_df)} SSAs.")
    
    if not initial_df.empty:
        # Mostra o estado inicial
        filter_status_at_start_text = ""
        if initial_filter_terms:
            filter_status_at_start_text = f" - Filtro(s) Aplicado(s): {', '.join(initial_filter_terms)}"
        print(f"Filtrando {len(initial_df)} SSAs{filter_status_at_start_text}")
        print("Comandos: -d(etalhes), -v(oltar filtro), -e(xportar), -r(eset), -c(onfigurar), -h(elp), -q(uit)")
        print("Pesquisar (virgulas para multiplos termos):")
        
        logger.debug("Chamando pretty_print_df inicial.")
        pretty_print_df(initial_df, display_map, settings)
    else:
        print("Nenhum dado disponível para exibição.")
        # Mesmo com dados vazios, entra no loop para permitir rescan, etc.
        

    # --- Loop Principal ---
    # Comandos que requerem lógica inline ou handlers não mapeados diretamente
    INLINE_COMMAND_PREFIXES = ['-d', '-detalhe', '-e', '-exportar', '-ord', '-ordi']

    while True:
        try:
            # Recarrega configurações a cada iteração para refletir mudanças
            settings = load_settings() 
            display_map = settings.get("display_mappings", {}) # Atualiza display_map também
            
            current_df, current_filter_terms = results_stack[-1]
            
            print("") # Linha em branco para separação visual
            filter_status_runtime_text = ""
            if current_filter_terms:
                filter_status_runtime_text = f" - Filtro(s) Aplicado(s): {', '.join(current_filter_terms)}"
            
            prompt_text = (
                f"Filtrando {len(current_df)} SSAs{filter_status_runtime_text}\n"
                f"Comandos: -d(etalhes), -v(oltar filtro), -e(xportar), -r(eset), -c(onfigurar), -h(elp), -q(uit)\n"
                f"Pesquisar (virgulas para multiplos termos): "
            )
            user_input = input(prompt_text).strip()
            
            if not user_input:
                continue

            parts = user_input.lower().split()
            command = parts[0]

            # --- 1. Tratamento de Comandos Mapeados ---
            if command in COMMAND_HANDLERS:
                handler = COMMAND_HANDLERS[command]
                # Chama handlers específicos com argumentos
                if command in ['-v', 'voltar']:
                    handler(results_stack)
                elif command in ['-r', 'resetar']:
                    handler(db_path, table_name, results_stack, display_map, settings)
                elif command in ['-rescan']:
                    handler(db_path, table_name, results_stack, display_map, settings)
                elif command in ['-c', 'config']:
                     # O handler de config pode modificar settings
                     handler()
                     # Após configurar, força um refresh do estado e exibição
                     settings = load_settings()
                     display_map = settings.get("display_mappings", {})
                     # Recarrega o estado inicial com as novas configurações
                     initial_df_after_config, initial_filter_terms_after_config = _get_initial_state(db_path, table_name, settings)
                     results_stack = [(initial_df_after_config, initial_filter_terms_after_config)]
                     pretty_print_df(initial_df_after_config, display_map, settings)
                else:
                    # Handlers simples que não precisam de argumentos específicos do loop
                    handler()

            # --- 2. Tratamento de Comandos com Lógica Inline ou Argumentos ---
            elif command in INLINE_COMMAND_PREFIXES:
                if command in ['-d', '-detalhe']:
                    _handle_details(parts, current_df, display_map)
                elif command in ['-e', '-exportar']:
                    _handle_export(parts, current_df, output_dir, display_map)
                elif command in ['-ord', '-ordi']:
                    ascending = (command == '-ord')
                    _handle_sort(parts, results_stack, display_map, settings, ascending)
            
            # --- 3. Tratamento como Pesquisa/Busca ---
            else:
                # Assume que qualquer entrada que não seja um comando conhecido é um termo de busca
                search_terms_input = user_input.split(',')
                processed_search_terms = [term.strip() for term in search_terms_input if term.strip()]
                if processed_search_terms: # Só filtra se houver termos
                    new_filtered_df = filter_dataframe(current_df, processed_search_terms)
                    if new_filtered_df.empty:
                        print("Nenhum resultado encontrado para o filtro. Tente outros termos.")
                    else:
                        results_stack.append((new_filtered_df, processed_search_terms))
                        pretty_print_df(new_filtered_df, display_map, settings)
                else:
                    # Se o usuário digitou algo que não é comando nem termo (só espaços?), apenas continua
                    continue

        except KeyboardInterrupt:
            print("\nOperação interrompida pelo usuário. Saindo...")
            sys.exit(0)
        except Exception as e:
            logger.error(f"Erro inesperado no loop da CLI: {e}", exc_info=True)
            print(f"Ocorreu um erro inesperado: {e}. A aplicação será encerrada.")
            sys.exit(1)
