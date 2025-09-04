"""
Simple Width Manager - Versão simplificada para integração imediata
Elimina código frankenstein com implementação funcional mínima.
"""

class SimpleWidthManager:
    """
    Gerenciador simples de larguras de colunas.
    Substitui as múltiplas estratégias conflitantes por uma implementação limpa.
    """
    
    def __init__(self):
        """Inicializa o gerenciador simples."""
        self.min_char_sizes = {
            '#': 3,
            'numero_ssa': 8,
            'localizacao_codigo': 7,
            'situacao': 4,
            'descricao_ssa': 25,
            'data_cadastro': 9,
            'setor_emissor': 5,
            'setor_executor': 5,
            'derivada_de': 8,
            'semana_programada': 6,
            'descricao_execucao': 20,
            'semana_cadastro': 7,
            'solicitante': 18,  # Aumentado para acomodar "MAURICIO MENON"
            'grau_prioridade_emissao': 4,
            'grau_prioridade_planejamento': 4
        }
        
        self.expandable_columns = ['descricao_ssa', 'descricao_execucao', 'solicitante']
    
    def compute_optimal_widths(
        self, 
        df,  # DataFrame
        available_width: int,
        display_mappings=None,
        saved_widths=None,
        column_order=None
    ):
        """
        ALGORITMO SIMPLES E FUNCIONAL - LARGURAS FIXAS DETERMINÍSTICAS COM CRESCIMENTO
        
        Larguras fixas para colunas estáticas + crescimento proporcional para descrições.
        Divisão 50/50 entre descricao_ssa e descricao_execucao para espaço extra.
        
        Args:
            column_order: Lista explícita da ordem correta das colunas (inclui '#')
        """
        display_mappings = display_mappings or {}
        saved_widths = saved_widths or {}
        
        if df is None or df.empty:
            return {}
        
        # Usa a ordem explícita fornecida, ou fallback para colunas ordenadas deterministicamente
        if column_order:
            columns = column_order
        else:
            # Lista de colunas ordenada deterministicamente
            df_columns = sorted(df.columns.tolist())
            columns = ['#'] + df_columns if '#' not in df_columns else sorted(df.columns.tolist())
        
        # IMPORTANTE: Para forçar larguras fixas, ignora saved_widths temporariamente
        saved_widths = {}  # FORÇA uso das larguras fixas
        
        # LARGURAS FIXAS CONSTANTES - TAMANHO EXATO SEMPRE IGUAL
        fixed_widths = {}
        expandable_cols = []  # Colunas que podem crescer
        
        for i, col in enumerate(columns):
            
            if col == '#':
                fixed_widths[col] = 20  # Ajuste v3.0.4: 25px → 20px (-5px)
                
            elif col in saved_widths and saved_widths[col] > 0:
                fixed_widths[col] = saved_widths[col]
                
            elif col == 'numero_ssa':
                fixed_widths[col] = 70  # +5 px leve
                
            elif col == 'situacao':
                fixed_widths[col] = 40  # +5 px leve
                
            elif col == 'setor_executor':
                fixed_widths[col] = 45  # +5 px leve
                
            elif col == 'setor_emissor':
                fixed_widths[col] = 45  # +5 px leve
                
            elif col == 'localizacao_codigo':
                fixed_widths[col] = 65  # +5 px leve
                
            elif col == 'data_cadastro':
                fixed_widths[col] = 95  # +10 px leve
                
            elif col == 'semana_cadastro':
                fixed_widths[col] = 65  # +5 px leve
                
            elif col == 'semana_programada':
                fixed_widths[col] = 50  # +5 px leve
                
            elif col == 'derivada_de':
                fixed_widths[col] = 70  # +5 px leve
                
            elif col == 'grau_prioridade_emissao':
                fixed_widths[col] = 70  # +5 px leve
                
            elif col == 'grau_prioridade_planejamento':
                fixed_widths[col] = 70  # +5 px leve
                
            elif col == 'solicitante':
                fixed_widths[col] = 170  # +10 px leve
                
            elif col == 'descricao_ssa':
                fixed_widths[col] = 470  # +20 px leve
                expandable_cols.append(col)
                
            elif col == 'descricao_execucao':
                fixed_widths[col] = 370  # +20 px leve
                expandable_cols.append(col)
                
            else:
                # Outros campos: largura padrão
                fixed_widths[col] = 120
        
        # CÁLCULO DE CRESCIMENTO PROPORCIONAL MELHORADO
        total_fixed = sum(fixed_widths.values())
        available_extra = max(0, available_width - total_fixed)
        
        if available_extra > 0 and expandable_cols:
            # Divisão proporcional do espaço extra com tratamento de resto
            extra_per_col = available_extra // len(expandable_cols)
            remainder = available_extra % len(expandable_cols)
            
            for i, col in enumerate(expandable_cols):
                # Primeira coluna recebe o resto para evitar pixels perdidos
                extra_bonus = remainder if i == 0 else 0
                total_extra = extra_per_col + extra_bonus
                
                fixed_widths[col] += total_extra
        
        return fixed_widths


class SimpleCacheManager:
    """Cache manager simples para evitar problemas de importação."""
    
    def __init__(self):
        self._formatted_cache = {}
    
    def get_cached_formatted_df(self, df_hash):
        """Retorna DataFrame formatado do cache."""
        return self._formatted_cache.get(df_hash)
    
    def cache_formatted_df(self, df_hash, formatted_df):
        """Armazena DataFrame formatado no cache."""
        self._formatted_cache[df_hash] = formatted_df
        
        # Limita tamanho do cache
        if len(self._formatted_cache) > 5:
            # Remove entrada mais antiga
            oldest_key = next(iter(self._formatted_cache))
            del self._formatted_cache[oldest_key]
