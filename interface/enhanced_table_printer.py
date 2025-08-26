"""
Enhanced Table Printer - Versão melhorada com CLI Width Manager
Integra as soluções da GUI para fornecer renderização consistente na CLI.
"""

import pandas as pd
from tabulate import tabulate
from typing import Dict, List, Optional
import os
import sys
import math
import logging

from interface.cli_width_manager import CLIWidthManager
from utils.formatting import format_dataframe_for_display

logger = logging.getLogger(__name__)

class EnhancedTablePrinter:
    """
    Renderizador de tabelas melhorado para CLI.
    Usa CLIWidthManager para larguras determinísticas e word wrap.
    """
    
    def __init__(self):
        """Inicializa o renderizador melhorado."""
        self.width_manager = CLIWidthManager()
        
    def get_terminal_size(self):
        """Obtém dimensões do terminal."""
        try:
            size = os.get_terminal_size()
            return size.lines, size.columns
        except OSError:
            return 24, 120  # Valores padrão mais generosos
    
    def print_dataframe_enhanced(
        self, 
        df: pd.DataFrame, 
        display_map: Dict[str, str], 
        settings: dict,
        highlight_terms: Optional[List[str]] = None,
        filter_terms: Optional[List[str]] = None
    ):
        """
        Renderiza DataFrame com sistema melhorado.
        
        Args:
            df: DataFrame a ser exibido
            display_map: Mapeamento de nomes de colunas
            settings: Configurações do sistema
            highlight_terms: Termos para destacar (opcional)
        """
        if df.empty:
            print("Nenhum resultado para exibir.")
            return
        
        # Obtém dimensões do terminal
        terminal_height, terminal_width = self.get_terminal_size()
        available_width = max(terminal_width - 5, 80)  # Margem de segurança
        
        # Obtém ordem das colunas da configuração unificada
        column_order = self.width_manager.get_column_order()
        display_names = self.width_manager.get_display_names()
        
        # Filtra colunas que existem no DataFrame
        available_columns = ['#'] + [col for col in df.columns]
        filtered_order = [col for col in column_order if col in available_columns]
        
        # Seleciona colunas baseado na largura disponível
        selected_columns = self._select_columns_smart(
            df, filtered_order, available_width, display_names
        )
        
        if not selected_columns or len(selected_columns) <= 1:
            print("Nenhuma coluna adequada para exibição encontrada.")
            return
        
        # Prepara DataFrame de trabalho
        data_columns = [col for col in selected_columns if col != '#']
        working_df = df[data_columns].copy()
        
        # Aplica formatação base (datas, SSAs, etc.)
        working_df = format_dataframe_for_display(working_df)
        
        # Normaliza números SSA
        if 'numero_ssa' in working_df.columns:
            working_df['numero_ssa'] = working_df['numero_ssa'].apply(
                self.width_manager.normalize_ssa_number
            )
        
        # Calcula larguras usando CLI Width Manager
        widths = self.width_manager.compute_cli_widths(
            working_df, available_width, selected_columns
        )
        
        # Adiciona coluna de índice
        working_df.insert(0, '#', range(1, len(working_df) + 1))
        
        # Aplica word wrap e formatação de células
        formatted_df = self._apply_formatting_and_wrap(working_df, widths, display_names)
        
        # Renderiza com paginação
        self._render_paginated(formatted_df, widths, settings, highlight_terms, filter_terms)
    
    def _select_columns_smart(
        self, 
        df: pd.DataFrame, 
        column_order: List[str], 
        available_width: int,
        display_names: Dict[str, str]
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
        essential_columns = ['#', 'numero_ssa', 'situacao', 'descricao_ssa']
        
        # Colunas prioritárias (ordem de importância)
        priority_columns = [
            'localizacao_codigo', 'setor_executor', 'data_cadastro', 
            'semana_cadastro', 'semana_programada', 'derivada_de',
            'setor_emissor', 'solicitante', 'descricao_execucao'
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
                if estimated_width + col_width + 3 <= available_width * 0.95:  # 95% para margem
                    selected.append(col)
                    estimated_width += col_width + 3
        
        # Adiciona outras colunas se houver espaço abundante
        for col in column_order:
            if col not in selected and col != '#':
                col_width = self.width_manager.fixed_widths.get(col, 15)
                if estimated_width + col_width + 3 <= available_width * 0.9:  # 90% para outras
                    selected.append(col)
                    estimated_width += col_width + 3
        
        return selected
    
    def _apply_formatting_and_wrap(
        self, 
        df: pd.DataFrame, 
        widths: Dict[str, int],
        display_names: Dict[str, str]
    ) -> pd.DataFrame:
        """
        Aplica formatação e word wrap nas células.
        
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
                formatted_df[col] = formatted_df[col].astype(str).apply(
                    lambda x: self._format_cell(x, width, col)
                )
        
        # Renomeia colunas para exibição
        rename_map = {}
        for col in formatted_df.columns:
            if col == '#':
                rename_map[col] = '#'
            else:
                # Usa nomes da configuração unificada
                display_name = display_names.get(col, col)
                # Trunca nome da coluna se necessário
                max_header_width = widths.get(col, 15)
                if len(display_name) > max_header_width:
                    display_name = display_name[:max_header_width-3] + '...'
                rename_map[col] = display_name
        
        formatted_df = formatted_df.rename(columns=rename_map)
        
        return formatted_df
    
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
        if not content or content == 'nan':
            content = '-'
        
        content = str(content).strip()
        
        # Para coluna de índice, aplica padding à direita
        if column_name == '#':
            return content.rjust(width)
        
        # Aplica word wrap ou truncamento
        wrapped_lines = self.width_manager.apply_word_wrap(content, width, column_name)
        
        # Por enquanto, usa apenas a primeira linha (futuro: suporte a múltiplas linhas)
        formatted_content = wrapped_lines[0] if wrapped_lines else ''
        
        # Remove padding fixo para evitar quebras de linha
        return formatted_content.rstrip()[:width]
    
    def _render_paginated(
        self, 
        df: pd.DataFrame, 
        widths: Dict[str, int],
        settings: dict,
        highlight_terms: Optional[List[str]] = None,
        filter_terms: Optional[List[str]] = None
    ):
        """
        Renderiza DataFrame com paginação.
        
        Args:
            df: DataFrame formatado
            widths: Larguras das colunas
            settings: Configurações do sistema
            highlight_terms: Termos para destacar
        """
        terminal_height, _ = self.get_terminal_size()
        page_size = max(1, terminal_height - 8)
        
        # Auto-scroll settings
        auto_scroll = settings.get('user_preferences', {}).get('auto_scroll_to_end', False)
        total_pages = math.ceil(len(df) / page_size) if page_size > 0 else 1
        max_auto_scroll_pages = settings.get('display_settings', {}).get('max_auto_scroll_pages', 3)
        
        if auto_scroll and total_pages > max_auto_scroll_pages:
            auto_scroll = False
        
        # Gera páginas
        pages = []
        for i in range(0, len(df), page_size):
            pages.append(df.iloc[i:i+page_size])
        
        if not pages:
            print("Nenhum dado para exibir após processamento.")
            return
        
        # Loop de exibição
        current_page = 0
        while current_page < len(pages):
            try:
                page_df = pages[current_page]
                
                # Cabeçalho da página (só na primeira página)
                if current_page == 0:
                    print(f"Página {current_page + 1} de {len(pages)}")
                
                # Renderiza tabela
                table_str = tabulate(
                    page_df,
                    headers=page_df.columns,
                    tablefmt='presto',
                    showindex=False,
                    stralign='left',
                    disable_numparse=True
                )
                
                # Aplica destaque se necessário
                if highlight_terms and highlight_terms[0]:  # Só se houver termos
                    table_str = self._apply_highlighting(table_str, highlight_terms)
                
                print(table_str)
                
                current_page += 1
                
                # Controle de paginação
                if current_page < len(pages):
                    if auto_scroll:
                        continue
                    else:
                        remaining = len(pages) - current_page
                        
                        # Monta informação sobre filtros aplicados
                        filter_info = ""
                        if filter_terms:
                            filter_info = f" - Filtros: {', '.join(filter_terms)}"
                        
                        prompt = f"\n-- Mais ({remaining} pág. restante(s)){filter_info} | Enter: continuar, 'f': até o final, 'd <#>': detalhe, '+filtro': adicionar, 'q': sair --"
                        try:
                            user_input = input(prompt).strip().lower()
                        except KeyboardInterrupt:
                            print("\n...exibição interrompida.")
                            break
                        
                        if user_input == 'q':
                            print("\n...exibição interrompida.")
                            break
                        elif user_input == 'f':
                            auto_scroll = True
                        elif user_input.startswith('+'):
                            # Implementação simplificada para adicionar filtro
                            # (retorna comando para processamento externo)
                            print(f"\nPara adicionar filtro '{user_input[1:]}', use o comando principal.")
                            continue
                        elif user_input.startswith('d '):
                            # Implementação simplificada para detalhe
                            print(f"\nPara ver detalhe da linha {user_input[2:]}, use o comando principal.")
                            continue
                        elif user_input == '':
                            continue
                        else:
                            print("Comando inválido.")
                            current_page -= 1
                else:
                    # Última página
                    if not auto_scroll:
                        try:
                            input("\n-- Fim | 'q': sair --")
                        except KeyboardInterrupt:
                            print("\n...exibição interrompida.")
                    break
                    
            except KeyboardInterrupt:
                print("\\n...exibição interrompida.")
                break
            except Exception as e:
                logger.error(f"Erro na renderização: {e}")
                print(f"Erro na exibição: {e}")
                break
    
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
        if os.name == 'nt' or not sys.stdout.isatty() or os.environ.get('NO_COLOR'):
            return table_str
        
        highlighted = table_str
        for term in highlight_terms:
            if term and len(term) > 1:  # Evita termos muito curtos
                pattern = f"({re.escape(term)})"
                replacement = "\\x1b[1m\\1\\x1b[0m"  # Negrito
                highlighted = re.sub(pattern, replacement, highlighted, flags=re.IGNORECASE)
        
        return highlighted


# Instância global para uso direto
enhanced_printer = EnhancedTablePrinter()

def pretty_print_df_enhanced(df: pd.DataFrame, display_map: Dict[str, str], settings: dict, highlight_terms: Optional[List[str]] = None, filter_terms: Optional[List[str]] = None):
    """
    Função de conveniência para usar o renderizador melhorado.
    
    Args:
        df: DataFrame a ser exibido
        display_map: Mapeamento de nomes de colunas
        settings: Configurações do sistema
        highlight_terms: Termos para destacar (opcional)
        filter_terms: Termos de filtro aplicados (opcional)
    """
    enhanced_printer.print_dataframe_enhanced(df, display_map, settings, highlight_terms, filter_terms)


# Função simplificada para formato CLI rápido
def format_dataframe_for_cli_enhanced(
    df: pd.DataFrame,
    display_map: Optional[Dict[str, str]] = None,
    max_width: Optional[int] = None,
    highlight_terms: Optional[List[str]] = None
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
    essential_cols = ['numero_ssa', 'situacao', 'setor_executor', 'descricao_ssa']
    available_cols = [col for col in essential_cols if col in df.columns]
    
    if not available_cols:
        available_cols = list(df.columns)[:4]
    
    work_df = df[available_cols].copy()
    
    # Aplica normalização SSA
    if 'numero_ssa' in work_df.columns:
        work_df['numero_ssa'] = work_df['numero_ssa'].apply(
            temp_printer.width_manager.normalize_ssa_number
        )
    
    # Formata usando nomes de exibição
    display_names = temp_printer.width_manager.get_display_names()
    rename_map = {}
    for col in work_df.columns:
        short_name = display_names.get(col, col)
        # Trunca nomes muito longos
        if len(short_name) > 15:
            short_name = short_name[:12] + '...'
        rename_map[col] = short_name
    
    work_df = work_df.rename(columns=rename_map)
    
    # Renderiza com tabulate
    table_str = tabulate(
        work_df, 
        headers=work_df.columns,
        tablefmt='presto', 
        showindex=False,
        disable_numparse=True
    )
    
    # Aplica destaque se necessário
    if highlight_terms:
        import re
        for term in highlight_terms:
            if term and len(term) > 1:
                if os.name != 'nt' and sys.stdout.isatty() and not os.environ.get('NO_COLOR'):
                    pattern = f"({re.escape(term)})"
                    replacement = "\\x1b[1m\\1\\x1b[0m"
                    table_str = re.sub(pattern, replacement, table_str, flags=re.IGNORECASE)
    
    return table_str
