# interface/display.py 20250725 174500 (v10.12 - Tratamento de Erros Aprimorado)
import pandas as pd
from typing import Dict, Any
import sys
import logging

logger = logging.getLogger(__name__)

# Importa a funcao de impressao de tabela do novo modulo
# (Assumindo que table_printer.py esteja em interface/table_printer.py)
# from interface.table_printer import pretty_print_df 

def pretty_print_details(series: Any, display_map: Dict[str, str]):
    """
    Imprime os detalhes de uma única linha (SSA) de forma legível e formatada.
    
    Args:
        series (Any): Uma linha do DataFrame (pd.Series) ou um dicionário.
        display_map (Dict[str, str]): Mapeamento de nomes internos para nomes de exibição.
    """
    # --- Tratamento de Erros ---
    if not isinstance(display_map, dict):
        logger.error("Erro em pretty_print_details: display_map deve ser um dicionário.")
        print("Erro: Configuração de exibição inválida.")
        return

    # Tenta converter para Series se for um dicionário
    if isinstance(series, dict):
        try:
            series = pd.Series(series)
        except Exception as e:
            logger.error(f"Erro ao converter dict para Series: {e}")
            print("Erro: Dados da SSA inválidos.")
            return
    elif not isinstance(series, pd.Series):
        logger.error(f"Erro em pretty_print_details: 'series' deve ser pd.Series ou dict, recebido {type(series)}.")
        print("Erro: Formato de dados da SSA inválido.")
        return

    # --- Impressão ---
    try:
        import textwrap
        import os
        from tabulate import tabulate
        
        # Obtém largura do terminal
        try:
            terminal_width = os.get_terminal_size().columns
        except OSError:
            terminal_width = 80
        
        # Ajusta a largura de exibição
        width = min(terminal_width - 4, 120)  # Evita linhas muito longas
        separator_line = "="*width
        
        # Cabeçalho
        print("\n" + separator_line)
        ssa_number = series.get('numero_ssa', 'N/A')
        titulo = f" DETALHES DA SSA: {ssa_number}"
        print(titulo)
        print(separator_line)
        
        # Define a ordem de exibição dos campos (mais importantes primeiro)
        priority_fields = [
            'numero_ssa', 'situacao', 'setor_executor', 'data_cadastro',
            'semana_programada', 'setor_emissor', 'descricao_ssa',
            'descricao_execucao'
        ]
        
        # Primeiro exibe os campos prioritários na ordem definida
        displayed_fields = set()
        for key in priority_fields:
            if key in series:
                display_name = display_map.get(key, key)
                value = series[key]
                
                # Trata valores NA/NaN/nulos de forma mais robusta
                if pd.isna(value) or value is None or (isinstance(value, str) and value.strip().lower() in ['none', 'nan', '']):
                    display_value = '-'
                else:
                    display_value = str(value)
                
                # Para campos descritivos, usa wrapping para texto longo
                if key in ['descricao_ssa', 'descricao_execucao']:
                    print(f"\n{display_name}:")
                    print("-" * width)
                    wrapped = textwrap.wrap(display_value, width=width-4)
                    for line in wrapped:
                        print(f"  {line}")
                    print("-" * width)
                else:
                    print(f"{display_name+':':<25} {display_value}")
                
                displayed_fields.add(key)
        
        # Exibe todos os outros campos não prioritários
        if len(series) > len(displayed_fields):
            print("\nInformações Adicionais:")
            print("-" * width)
            
            # Cria uma tabela para os outros campos
            other_fields = []
            for key, value in series.items():
                if key not in displayed_fields:
                    display_name = display_map.get(key, key)
                    
                    if pd.isna(value) or value is None or (isinstance(value, str) and value.strip().lower() in ['none', 'nan', '']):
                        display_value = '-'
                    else:
                        display_value = str(value)
                        
                    other_fields.append([display_name, display_value])
            
            if other_fields:
                print(tabulate(other_fields, tablefmt="simple"))
            
        print(separator_line)
    except Exception as e:
        logger.error(f"Erro inesperado em pretty_print_details: {e}")
        print(f"Erro: Falha ao exibir os detalhes da SSA: {str(e)}")
