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
    filtros_aplicados = []  # Lista para rastrear filtros aplicados sequencialmente
    mostrar_resultados = False  # Controla se deve exibir resultados
    
    # Tamanho de página padrão (configurável com o comando -p)
    page_size = 20
    rolagem_continua = True  # Por padrão, exibe resultados continuamente

    while True:
        # Status só exibido quando há filtros aplicados
        if filtros_aplicados:
            print(f"\nExibindo {len(df_filtrado)} registros de {len(df_completo)} totais.")
            print(f"Filtros aplicados: {' → '.join(filtros_aplicados)}")
        
        # Só exibe resultados se há filtros aplicados ou se foi solicitado explicitamente
        if mostrar_resultados and (filtros_aplicados or len(df_filtrado) < len(df_completo)):
            if len(df_filtrado) == 0:
                print("\n" + "-"*60)
                print("  Nenhum resultado encontrado para o filtro atual.")
                print("  Use -r para limpar os filtros e exibir todos os registros.")
                print("-"*60)
            elif rolagem_continua:
                # Modo rolagem contínua - com limite inteligente para performance
                try:
                    # Limite para performance - mais de 100 registros pergunta primeiro
                    if len(df_filtrado) > 100:
                        print(f"\n⚠️  Encontrados {len(df_filtrado)} registros.")
                        print("Exibir todos pode demorar. Opções:")
                        print("  1 - Primeiros 50 registros (rápido)")
                        print("  2 - Primeiros 100 registros (médio)")
                        print("  3 - Todos os registros (pode demorar)")
                        print("  4 - Modo paginação")
                        try:
                            choice = input("Escolha (1/2/3/4): ").strip()
                            if choice == "1":
                                display_count = 50
                            elif choice == "2":
                                display_count = 100
                            elif choice == "4":
                                # Muda para paginação temporariamente
                                paginator = Paginator(df_filtrado, page_size=page_size)
                                is_paginating = True
                                while is_paginating:
                                    try:
                                        print(f"\n--- Mostrando registros {(paginator.current_page-1)*page_size+1}-{min(paginator.current_page*page_size, paginator.total_items)} de {paginator.total_items} ---")
                                        page_df = paginator.get_current_page_data()
                                        # Adiciona numeração de linha
                                        page_df_with_num = page_df.copy()
                                        page_df_with_num.insert(0, '#', range((paginator.current_page-1)*page_size + 1, (paginator.current_page-1)*page_size + len(page_df) + 1))
                                        formatted_table = format_dataframe_for_cli(page_df_with_num, display_map)
                                        print(formatted_table)
                                        
                                        if paginator.total_pages > 1:
                                            print(f"\n⏪ Pág {paginator.current_page} de {paginator.total_pages} | n=próxima | p=anterior | q=voltar | número=ir página")
                                            cmd = input("> ").strip().lower()
                                            if cmd == 'q':
                                                is_paginating = False
                                            elif cmd == 'p':
                                                paginator.prev_page()
                                            elif cmd == 'n' or cmd == '':
                                                if not paginator.next_page():
                                                    print("Fim dos resultados.")
                                                    is_paginating = False
                                            elif cmd.isdigit():
                                                page_num = int(cmd)
                                                if 1 <= page_num <= paginator.total_pages:
                                                    paginator.go_to_page(page_num)
                                                else:
                                                    print(f"Página inválida. Digite um número entre 1 e {paginator.total_pages}.")
                                        else:
                                            is_paginating = False
                                    except Exception as e:
                                        print(f"Erro na paginação: {e}")
                                        is_paginating = False
                                continue  # Pula o resto da exibição contínua
                            else:
                                display_count = len(df_filtrado)  # Todos
                        except (EOFError, KeyboardInterrupt):
                            display_count = 50  # Default para 50
                    else:
                        display_count = len(df_filtrado)
                    
                    # Exibe quantidade limitada com numeração
                    df_to_show = df_filtrado.head(display_count).copy()
                    # Adiciona coluna de numeração
                    df_to_show.insert(0, '#', range(1, len(df_to_show) + 1))
                    
                    print(f"\n--- Exibindo {len(df_to_show)} de {len(df_filtrado)} registros ---")
                    formatted_table = format_dataframe_for_cli(df_to_show, display_map)
                    print(formatted_table)
                    
                    if len(df_filtrado) > display_count:
                        print(f"--- Mostrando {display_count} de {len(df_filtrado)} registros (use paginação para ver todos) ---")
                    else:
                        print(f"--- Fim dos resultados ({len(df_filtrado)} registros) ---")
                        
                except Exception as e:
                    logger.error(f"Erro ao formatar tabela: {e}")
                    print(f"\nErro ao exibir tabela completa. {len(df_filtrado)} registros encontrados.")
            else:
                # Modo paginação (apenas se solicitado)
                paginator = Paginator(df_filtrado, page_size=page_size)
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

        # Reset da flag após exibir resultados
        mostrar_resultados = False

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
            print("  -r                     : Limpa TODOS os filtros e exibe todos os registros")
            print("  -s                     : Alterna entre rolagem contínua e paginação")
            print("                         Contínua: exibe até 100 registros de uma vez (performance)")
            print("                         Paginação: navega página por página (todos os registros)")
            print("  -e <nome>              : Exporta resultados atuais para arquivo")
            print("  -p <num>               : Define o tamanho da página (padrão: 20)")
            print("  -c                     : Abre menu de configurações")
            print("  -schedule              : Gerencia exportações agendadas")
            print("  -d <num_linha_ou_ssa>  : Exibe detalhes de uma SSA específica")
            print("\nCOMANDOS DE NAVEGAÇÃO (durante paginação):")
            print("  Enter, n               : Próxima página")
            print("  p                      : Página anterior")
            print("  <número>               : Ir para a página específica")
            print("  q                      : Voltar ao menu principal")
            print("\nPESQUISA SEQUENCIAL:")
            print("  Digite termos separados por vírgula para filtrar os registros.")
            print("  Os filtros são aplicados SEQUENCIALMENTE na seleção atual.")
            print("  Ex: MEL4, pendente     : Primeiro filtra por 'MEL4', depois por 'pendente'")
            print("  Use -r para limpar todos os filtros e voltar ao conjunto completo.")
            print("="*60)
        elif command == '-r':
            df_filtrado = df_completo.copy()
            filtros_aplicados = []  # Limpa os filtros aplicados
            mostrar_resultados = True  # Ativa exibição para mostrar todos os registros
            print("Filtros resetados. Todos os registros serão exibidos.")
        elif command == '-s':
            rolagem_continua = not rolagem_continua
            modo = "CONTÍNUA" if rolagem_continua else "PAGINAÇÃO"
            print(f"Modo de exibição alterado para: {modo}")
            print("Rolagem contínua: exibe todos os resultados de uma vez")
            print("Paginação: divide resultados em páginas navegáveis")
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
                if len(parts) > 1:
                    param = parts[1].strip()
                    
                    # Verifica se é um número de linha ou número de SSA
                    if param.isdigit():
                        if len(param) == 9:  # Número de SSA (9 dígitos)
                            # Busca por número da SSA
                            ssa_matches = df_filtrado[df_filtrado['numero_ssa'].astype(str) == param]
                            if not ssa_matches.empty:
                                row_data = ssa_matches.iloc[0]
                                print(f"\n--- DETALHES DA SSA {param} ---")
                                pretty_print_details(row_data, display_map)
                            else:
                                print(f"SSA {param} não encontrada nos resultados atuais.")
                                # Verifica se existe no conjunto completo
                                ssa_complete = df_completo[df_completo['numero_ssa'].astype(str) == param]
                                if not ssa_complete.empty:
                                    print("(Esta SSA existe na base completa mas foi filtrada)")
                        else:
                            # Número de linha na listagem atual
                            row_num = int(param) - 1  # Ajusta para índice base 0
                            if 0 <= row_num < len(df_filtrado):
                                row_data = df_filtrado.iloc[row_num]
                                ssa_num = row_data.get('numero_ssa', 'N/A')
                                print(f"\n--- DETALHES DA SSA {ssa_num} (linha {param}) ---")
                                pretty_print_details(row_data, display_map)
                            else:
                                print(f"Número de linha inválido. Digite um valor entre 1 e {len(df_filtrado)}.")
                    else:
                        print("O parâmetro deve ser um número (linha da listagem ou número da SSA de 9 dígitos).")
                else:
                    print("Uso: -d <número_da_linha_ou_número_da_ssa>")
                    print("Exemplos:")
                    print("  -d 3         : Exibe detalhes do item número 3 na listagem atual")
                    print("  -d 202500001 : Exibe detalhes da SSA 202500001")
            except Exception as e:
                print(f"Erro ao exibir detalhes: {e}")
                logger.error(f"Erro ao exibir detalhes: {e}")
        else:
            # Verifica se o input é um número de SSA (9 dígitos)
            if user_input.isdigit() and len(user_input) == 9:
                # Trata como comando de exibir detalhes
                try:
                    ssa_matches = df_filtrado[df_filtrado['numero_ssa'].astype(str) == user_input]
                    if not ssa_matches.empty:
                        row_data = ssa_matches.iloc[0]
                        print(f"\n--- DETALHES DA SSA {user_input} ---")
                        pretty_print_details(row_data, display_map)
                        continue
                    else:
                        print(f"SSA {user_input} não encontrada nos resultados atuais.")
                        # Verifica se existe no conjunto completo
                        ssa_complete = df_completo[df_completo['numero_ssa'].astype(str) == user_input]
                        if not ssa_complete.empty:
                            print("(Esta SSA existe na base completa mas foi filtrada)")
                            row_data = ssa_complete.iloc[0]
                            print(f"\n--- DETALHES DA SSA {user_input} (da base completa) ---")
                            pretty_print_details(row_data, display_map)
                        continue
                except Exception as e:
                    print(f"Erro ao buscar SSA {user_input}: {e}")
                    continue
            
            # Verifica se pode ser um comando digitado acidentalmente
            potential_commands = ['-q', '-h', '-r', '-e', '-p', '-c', '-schedule', '-d']
            
            # Se parece com um comando (começa com '-' ou é muito curto), pede confirmação
            if (user_input.startswith('-') and user_input not in potential_commands) or len(user_input.strip()) == 1:
                print(f"'{user_input}' parece ser um comando, mas não é reconhecido.")
                print("Você quis dizer:")
                print("  -q  : Sair do programa")
                print("  -r  : Limpar filtros") 
                print("  -h  : Mostrar ajuda")
                try:
                    confirm = input("Deseja executar uma busca mesmo assim? (s/N): ").strip().lower()
                    if confirm not in ['s', 'sim', 'y', 'yes']:
                        print("Busca cancelada.")
                        continue
                except (EOFError, KeyboardInterrupt):
                    print("\nBusca cancelada.")
                    continue
            
            try:
                # Assume que é uma busca
                termos = user_input.split(',')
                termos_limpos = [t.strip() for t in termos if t.strip()]
                
                if not termos_limpos:
                    print("Nenhum termo de busca válido fornecido.")
                    continue
                
                print(f"Aplicando filtro: {', '.join(termos_limpos)}")
                
                # Mede o tempo de execução para melhor feedback ao usuário
                import time
                start_time = time.time()
                
                # Aplica filtro sequencial na seleção atual, não no conjunto completo
                df_filtrado = filter_dataframe(df_filtrado, termos_limpos)
                
                end_time = time.time()
                exec_time = end_time - start_time
                
                # Adiciona filtro à lista de filtros aplicados
                filtros_aplicados.append(', '.join(termos_limpos))
                mostrar_resultados = True  # Ativa exibição dos resultados filtrados
                
                # Feedback sobre o resultado da busca
                if len(df_filtrado) == 0:
                    print("Nenhum resultado encontrado. Tente outros termos ou use -r para limpar os filtros.")
                else:
                    print(f"Encontrados {len(df_filtrado)} registros em {exec_time:.2f} segundos.")
                    if len(filtros_aplicados) > 1:
                        print(f"Filtros aplicados sequencialmente: {' → '.join(filtros_aplicados)}")
            except Exception as e:
                print(f"Erro ao realizar a busca: {e}")
                logger.error(f"Erro ao filtrar dataframe: {e}")