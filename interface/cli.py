# interface/cli.py
import sys
import logging
import pandas as pd
from typing import Dict

# Importações da estrutura do projeto
from utils.pagination import Paginator
from interface.table_printer import format_dataframe_for_cli
from core.app_logic import filter_dataframe
from exportacao.exporter import export_dataframe
from interface.display import pretty_print_details
from core.config_manager import handle_config_command
from interface.command_handlers import handle_schedule_command

logger = logging.getLogger(__name__)

def start_cli_loop(initial_df: pd.DataFrame, display_map: Dict[str, str], output_dir: str):
    """
    Inicia o loop principal da interface de linha de comando.
    """
    if initial_df.empty:
        print("A base de dados está vazia. Importe dados primeiro.")
        return

    # Banner de boas-vindas com informações da versão
    print("\n" + "="*60)
    print("    CONSULTA RÁPIDA DE SSAS - v2.3")
    print("    Sistema de Gestão de Solicitações de Serviços e Alterações")
    print("="*60)

    # Aplicar otimizações de memória ao DataFrame
    try:
        # Converter tipos para reduzir uso de memória
        df_completo = initial_df.copy()
        
        # Converter colunas de texto para categorias quando houver poucos valores únicos
        for col in df_completo.select_dtypes(include=['object']).columns:
            # Se a coluna tem poucos valores únicos em relação ao total, usar category
            if col not in ['descricao_ssa', 'descricao_execucao']:
                try:
                    unique_count = df_completo[col].nunique()
                    if unique_count > 0 and unique_count < len(df_completo) * 0.5:
                        df_completo[col] = df_completo[col].astype('category')
                except:
                    pass  # Se der erro, mantém o tipo original
                    
        # Converter números para tipos mais eficientes
        for col in df_completo.select_dtypes(include=['int64', 'float64']).columns:
            try:
                if df_completo[col].max() < 32767 and df_completo[col].min() > -32768:
                    df_completo[col] = df_completo[col].astype('int16')
            except:
                pass  # Se der erro, mantém o tipo original
                
        print(f"Base de dados carregada com {len(df_completo):,} registros.")
        
    except Exception as e:
        print(f"Aviso: Não foi possível otimizar o uso de memória: {e}")
        df_completo = initial_df
        print(f"Base de dados carregada com {len(df_completo):,} registros.")
    
    df_filtrado = df_completo.copy()
    
    # Tamanho de página padrão (configurável com o comando -p)
    page_size = 20

    while True:
        paginator = Paginator(df_filtrado, page_size=page_size)
        
        print(f"\nExibindo {len(df_filtrado)} registros de {len(df_completo)} totais.")
        
        if paginator.total_items == 0:
            print("\n" + "-"*60)
            print("  Nenhum resultado encontrado para o filtro atual.")
            print("  Use -r para limpar os filtros e exibir todos os registros.")
            print("-"*60)
        else:
            is_paginating = True
            while is_paginating:
                try:
                    # Mostra primeiro a informação do total de registros e páginas
                    print(f"\n--- Mostrando registros {(paginator.current_page-1)*page_size+1}-{min(paginator.current_page*page_size, paginator.total_items)} de {paginator.total_items} ---")
                    
                    # Obtém e formata a página atual
                    page_df = paginator.get_current_page_data()
                    formatted_table = format_dataframe_for_cli(page_df, display_map)
                    print(formatted_table)
                    
                except Exception as e:
                    logger.error(f"Erro ao formatar tabela: {e}")
                    print("\n" + "!"*60)
                    print("  ERRO AO EXIBIR TABELA COMPLETA")
                    print("  Tentando exibir versão simplificada...")
                    print("!"*60)
                    
                    # Tenta exibir uma versão mais simples da tabela
                    try:
                        # Seleciona apenas as primeiras 3 colunas para exibição simplificada
                        simple_df = page_df.iloc[:, :3].copy()
                        
                        from tabulate import tabulate
                        print(tabulate(simple_df, headers="keys", tablefmt="simple", showindex=False))
                    except Exception as e2:
                        logger.error(f"Erro ao formatar tabela simplificada: {e2}")
                        print(f"  Não foi possível exibir a tabela. {len(page_df)} registros nesta página.")
                
                # Exibe comandos de navegação
                if paginator.total_pages > 1:
                    print("\n" + "-"*60)
                    nav_prompt = f"  Pág {paginator.current_page} de {paginator.total_pages} | "
                    
                    # Adiciona opções de navegação disponíveis com ícones visuais
                    nav_options = []
                    if paginator.current_page > 1:
                        nav_options.append("'p' ← anterior")
                    if paginator.current_page < paginator.total_pages:
                        nav_options.append("'n'/Enter → próxima")
                    nav_options.append("'q' para voltar")
                    nav_options.append("digite número para ir à página")
                    
                    nav_prompt += " | ".join(nav_options)
                    print(nav_prompt)
                    print("-"*60)
                    
                    try:
                        cmd = input("> ").strip().lower()
                    except (EOFError, KeyboardInterrupt):
                        cmd = 'q'
                        
                    # Processamento do comando de navegação
                    if cmd == 'q':
                        is_paginating = False
                    elif cmd == 'p':
                        paginator.prev_page()
                    elif cmd == 'n' or cmd == '':
                        if not paginator.next_page():
                            print("\nFim dos resultados. Pressione Enter para voltar ao menu principal.")
                            try:
                                input()
                            except (EOFError, KeyboardInterrupt):
                                pass
                            is_paginating = False
                    elif cmd.isdigit():
                        # Ir para uma página específica
                        page_num = int(cmd)
                        if 1 <= page_num <= paginator.total_pages:
                            paginator.go_to_page(page_num)
                        else:
                            print(f"Página inválida. Digite um número entre 1 e {paginator.total_pages}.")
                            # Pequena pausa para o usuário ver a mensagem
                            import time
                            time.sleep(1)
                    else:
                        # Tenta avançar por padrão
                        if not paginator.next_page():
                            is_paginating = False
                else:
                    # Apenas uma página, aguarda o usuário confirmar antes de voltar
                    print("\n" + "-"*60)
                    print("  Página única. Pressione Enter para voltar ao menu principal.")
                    print("-"*60)
                    try:
                        input("> ")
                    except (EOFError, KeyboardInterrupt):
                        pass
                    is_paginating = False

        # Prompt de comando principal com formatação melhorada
        prompt = "\n" + "-"*60 + "\n"
        prompt += "> Pesquise por termos separados por vírgula, ou use comandos:\n"
        prompt += "  (-h para ajuda, -q para sair, -r para limpar filtros)\n> "
        
        try:
            user_input = input(prompt).strip()
        except EOFError:
            print("\nEncerrando...")
            break
            
        parts = user_input.split()
        command = parts[0].lower() if parts else ""

        if not command:
            continue
        
        # Comandos de sistema
        if command in ['-q', 'sair', 'exit']:
            print("Encerrando o programa...")
            break
        elif command in ['-h', '-help', 'ajuda']:
            # Menu de ajuda com formatação melhorada
            print("\n" + "="*60)
            print(" COMANDOS DISPONÍVEIS:")
            print("="*60)
            print("  -h, -help, ajuda       : Exibe este menu de ajuda")
            print("  -q, sair, exit         : Encerra o programa")
            print("  -r                     : Limpa filtros e exibe todos os registros")
            print("  -e <nome>              : Exporta resultados atuais para arquivo")
            print("  -p <num>               : Define o tamanho da página (padrão: 20)")
            print("  -c                     : Abre menu de configurações")
            print("  -schedule              : Gerencia exportações agendadas")
            print("  -d <num_linha>         : Exibe detalhes de uma SSA específica")
            print("\nCOMANDOS DE NAVEGAÇÃO (durante paginação):")
            print("  Enter, n               : Próxima página")
            print("  p                      : Página anterior")
            print("  <número>               : Ir para a página específica")
            print("  q                      : Voltar ao menu principal")
            print("\nPESQUISA:")
            print("  Digite termos separados por vírgula para filtrar os registros.")
            print("  Ex: MEL4, pendente     : Busca por registros que contêm 'MEL4' e 'pendente'")
            print("="*60)
        elif command == '-r':
            df_filtrado = df_completo.copy()
            print("Filtro resetado. Todos os registros serão exibidos.")
        elif command == '-e':
            if len(parts) > 1:
                filename = parts[1]
                try:
                    export_dataframe(df_filtrado, filename, output_dir, display_map)
                    print(f"Dados exportados com sucesso para '{filename}' em {output_dir}")
                except Exception as e:
                    print(f"Erro ao exportar: {e}")
                    logger.error(f"Erro na exportação: {e}")
            else:
                print("Uso: -e <nome_base_arquivo>")
                print("Exemplos: -e relatorio (exporta para relatorio.xlsx, relatorio.csv, etc)")
        elif command == '-p':
            # Configuração de tamanho de página
            if len(parts) > 1 and parts[1].isdigit():
                new_size = int(parts[1])
                if 5 <= new_size <= 100:
                    page_size = new_size
                    print(f"Tamanho da página definido para {page_size} registros.")
                else:
                    print("O tamanho da página deve estar entre 5 e 100.")
            else:
                print("Uso: -p <número_de_registros>")
                print(f"O tamanho atual da página é {page_size} registros.")
        elif command == '-c':
            try:
                handle_config_command()
                print("\nConfigurações alteradas. Para ver o efeito, reinicie a busca ou a aplicação.")
            except Exception as e:
                print(f"Erro ao acessar configurações: {e}")
                logger.error(f"Erro no menu de configurações: {e}")
        elif command == '-schedule':
            try:
                handle_schedule_command(parts[1:])
            except Exception as e:
                print(f"Erro ao gerenciar agendamentos: {e}")
                logger.error(f"Erro no schedule: {e}")
        elif command == '-d':
            # Exibe detalhes de uma SSA
            try:
                if len(parts) > 1 and parts[1].isdigit():
                    row_num = int(parts[1]) - 1  # Ajusta para índice base 0
                    if 0 <= row_num < len(paginator._data):
                        row_data = paginator._data.iloc[row_num]
                        pretty_print_details(row_data, display_map)
                    else:
                        print(f"Número de linha inválido. Digite um valor entre 1 e {len(paginator._data)}.")
                else:
                    print("Uso: -d <número_da_linha>")
                    print("Exemplo: -d 3 (exibe detalhes do item número 3 na listagem atual)")
            except Exception as e:
                print(f"Erro ao exibir detalhes: {e}")
                logger.error(f"Erro ao exibir detalhes: {e}")
        else:
            try:
                # Assume que é uma busca
                termos = user_input.split(',')
                print(f"Buscando por: {', '.join(t.strip() for t in termos)}")
                
                # Mede o tempo de execução para melhor feedback ao usuário
                import time
                start_time = time.time()
                
                df_filtrado = filter_dataframe(df_completo, termos)
                
                end_time = time.time()
                exec_time = end_time - start_time
                
                # Feedback sobre o resultado da busca
                if len(df_filtrado) == 0:
                    print("Nenhum resultado encontrado. Tente outros termos ou use -r para limpar os filtros.")
                else:
                    print(f"Encontrados {len(df_filtrado)} registros em {exec_time:.2f} segundos.")
            except Exception as e:
                print(f"Erro ao realizar a busca: {e}")
                logger.error(f"Erro ao filtrar dataframe: {e}")