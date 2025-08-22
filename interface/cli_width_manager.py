"""
CLI Width Manager - Sistema de larguras determinísticas para CLI
Baseado no SimpleWidthManager da GUI, adaptado para terminal ASCII.
"""

import os
import json
from typing import Dict, List, Optional, Any

class CLIWidthManager:
    """
    Gerenciador de larguras para CLI baseado no SimpleWidthManager da GUI.
    
    Implementa o mesmo sistema de larguras fixas determinísticas com crescimento
    proporcional 50/50 para colunas de descrição, adaptado para terminal ASCII.
    """
    
    def __init__(self):
        """Inicializa o gerenciador de larguras CLI."""
        # Larguras fixas idênticas à GUI (convertidas de pixels para caracteres)
        # Conversão aproximada: 1 char ≈ 8px (para fontes monospace)
        self.fixed_widths = {
            '#': 3,                    # GUI: 20px ÷ 8 ≈ 3 chars
            'numero_ssa': 9,           # GUI: 65px ÷ 8 ≈ 9 chars  
            'situacao': 5,             # GUI: 35px ÷ 8 ≈ 5 chars
            'setor_executor': 6,       # GUI: 40px ÷ 8 ≈ 6 chars
            'setor_emissor': 6,        # GUI: 40px ÷ 8 ≈ 6 chars
            'localizacao_codigo': 8,   # GUI: 60px ÷ 8 ≈ 8 chars
            'data_cadastro': 11,       # GUI: 85px ÷ 8 ≈ 11 chars
            'semana_cadastro': 8,      # GUI: 60px ÷ 8 ≈ 8 chars
            'semana_programada': 6,    # GUI: 45px ÷ 8 ≈ 6 chars
            'derivada_de': 9,          # GUI: 65px ÷ 8 ≈ 9 chars
            'solicitante': 25,         # GUI: 160px ÷ 8 ≈ 20 chars (aumentado para 25)
            'descricao_ssa': 56,       # GUI: 450px ÷ 8 ≈ 56 chars (base)
            'descricao_execucao': 44,  # GUI: 350px ÷ 8 ≈ 44 chars (base)
            'grau_prioridade_emissao': 9,      # GUI: 65px ÷ 8 ≈ 9 chars
            'grau_prioridade_planejamento': 9, # GUI: 65px ÷ 8 ≈ 9 chars
        }
        
        # Colunas que podem crescer proporcionalmente (igual à GUI)
        self.expandable_columns = ['descricao_ssa', 'descricao_execucao']
        
        # Carrega configuração unificada
        self.gui_config = self._load_gui_config()
        
    def _load_gui_config(self) -> Dict[str, Any]:
        """Carrega configuração da GUI para unificar sistemas."""
        try:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_path = os.path.join(project_root, 'config', 'gui_main_preferences.json')
            
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    
    def get_column_order(self) -> List[str]:
        """Retorna ordem das colunas baseada na configuração da GUI."""
        gui_order = self.gui_config.get('display_columns', [])
        if gui_order:
            # Adiciona '#' no início se não estiver presente
            return ['#'] + [col for col in gui_order if col != '#']
        
        # Fallback para ordem padrão
        return [
            '#', 'numero_ssa', 'situacao', 'semana_cadastro', 'semana_programada',
            'derivada_de', 'localizacao_codigo', 'data_cadastro', 'descricao_ssa',
            'setor_executor', 'setor_emissor', 'solicitante', 'descricao_execucao'
        ]
    
    def get_display_names(self) -> Dict[str, str]:
        """Retorna mapeamento de nomes de exibição da GUI."""
        return self.gui_config.get('column_display_names', {})
    
    def compute_cli_widths(
        self, 
        df,
        available_width: int,
        column_order: Optional[List[str]] = None
    ) -> Dict[str, int]:
        """
        Calcula larguras determinísticas para CLI usando mesmo algoritmo da GUI.
        
        Args:
            df: DataFrame com os dados
            available_width: Largura disponível no terminal
            column_order: Ordem específica das colunas (opcional)
            
        Returns:
            Dict com larguras calculadas para cada coluna
        """
        if df is None or df.empty:
            return {}
        
        # Usa ordem fornecida ou ordem da configuração
        if column_order is None:
            column_order = self.get_column_order()
        
        # Garante que apenas colunas existentes sejam processadas
        available_columns = ['#'] + [col for col in df.columns if col in column_order]
        columns_to_process = [col for col in column_order if col in available_columns]
        
        # LARGURAS FIXAS DETERMINÍSTICAS (igual à GUI)
        calculated_widths = {}
        expandable_cols = []
        
        for i, col in enumerate(columns_to_process):
            
            if col in self.fixed_widths:
                calculated_widths[col] = self.fixed_widths[col]
                
                # Marca como expansível se aplicável
                if col in self.expandable_columns:
                    expandable_cols.append(col)
            else:
                # Largura padrão para outras colunas
                calculated_widths[col] = 15
                print(f"  -> PADRÃO: 15 chars")
        
        # CÁLCULO DE CRESCIMENTO PROPORCIONAL (algoritmo idêntico à GUI)
        total_fixed = sum(calculated_widths.values())
        separator_space = (len(columns_to_process) * 3)  # Espaço para separadores
        usable_width = max(0, available_width - separator_space)
        available_extra = max(0, usable_width - total_fixed)
        
        if available_extra > 10 and expandable_cols:  # Mínimo de 10 chars extras para expandir
            # Divisão proporcional 50/50 entre descrições (igual à GUI)
            extra_per_col = available_extra // len(expandable_cols)
            remainder = available_extra % len(expandable_cols)
            
            for i, col in enumerate(expandable_cols):
                # Primeira coluna recebe o resto
                extra_bonus = remainder if i == 0 else 0
                total_extra = extra_per_col + extra_bonus
                
                calculated_widths[col] += total_extra
        
        return calculated_widths
        
    def apply_word_wrap(self, text: str, width: int, column_name: str = '') -> List[str]:
        """
        Aplica word wrap ASCII para colunas de texto.
        
        Args:
            text: Texto a ser quebrado
            width: Largura máxima em caracteres
            column_name: Nome da coluna (para decidir se aplica wrap)
            
        Returns:
            Lista de linhas quebradas
        """
        if not text or width <= 0:
            return ['']
        
        text = str(text).strip()
        
        # Aplica word wrap apenas em colunas específicas (igual à GUI)
        wrap_columns = ['descricao_ssa', 'descricao_execucao', 'solicitante']
        
        if column_name not in wrap_columns:
            # Trunca sem word wrap
            if len(text) <= width:
                return [text]
            else:
                return [text[:max(0, width-3)] + '...']
        
        # Word wrap para colunas de descrição
        words = text.split()
        lines = []
        current_line = []
        current_length = 0
        
        for word in words:
            # Se a palavra sozinha é maior que a largura, quebra ela
            if len(word) > width:
                if current_line:
                    lines.append(' '.join(current_line))
                    current_line = []
                    current_length = 0
                
                # Quebra palavra longa
                while len(word) > width:
                    lines.append(word[:width-3] + '...')
                    word = word[width-3:]
                
                if word:
                    current_line = [word]
                    current_length = len(word)
                continue
            
            # Verifica se a palavra cabe na linha atual
            needed_space = len(word) + (1 if current_line else 0)
            
            if current_length + needed_space <= width:
                current_line.append(word)
                current_length += needed_space
            else:
                # Quebra linha
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
                current_length = len(word)
        
        # Adiciona última linha
        if current_line:
            lines.append(' '.join(current_line))
        
        # Garante que pelo menos uma linha existe
        if not lines:
            lines = ['']
        
        return lines
        
    def normalize_ssa_number(self, ssa_value) -> str:
        """
        Normaliza número SSA usando mesmo algoritmo da GUI.
        
        Args:
            ssa_value: Valor do número SSA
            
        Returns:
            Número SSA normalizado
        """
        if not ssa_value or str(ssa_value).strip() in ['', 'nan', 'None', '-']:
            return '-'
        
        s = str(ssa_value).strip()
        
        # Remove caracteres não numéricos
        s = ''.join(filter(str.isdigit, s))
        
        if not s:
            return '-'
        
        # Já com 9 dígitos
        if len(s) == 9:
            return s
        
        # 3-5 dígitos -> prefixa ano corrente 2025
        if len(s) <= 5:
            return f"2025{s.zfill(5)}"
        
        # 7-8 dígitos -> zfill para 9
        return s.zfill(9)
