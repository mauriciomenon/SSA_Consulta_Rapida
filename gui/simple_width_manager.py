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
            'solicitante': 14,
            'grau_prioridade': 4
        }
        
        self.expandable_columns = ['descricao_ssa', 'descricao_execucao', 'solicitante']
    
    def compute_optimal_widths(
        self, 
        df,  # DataFrame
        available_width: int,
        display_mappings=None,
        saved_widths=None
    ):
        """
        Calcula larguras otimizadas para o DataFrame dado.
        """
        display_mappings = display_mappings or {}
        saved_widths = saved_widths or {}
        
        # Lista de colunas (incluindo '#' se presente)
        columns = ['#'] + list(df.columns) if '#' not in df.columns else list(df.columns)
        
        # 1. Calcula larguras mínimas
        widths = {}
        total_min_width = 0
        
        for col in columns:
            # Usa largura salva se disponível
            if col in saved_widths and saved_widths[col] > 0:
                widths[col] = saved_widths[col]
            else:
                # Calcula largura baseada em caracteres
                min_chars = self.min_char_sizes.get(col, 8)
                if col not in self.min_char_sizes:
                    # Para colunas não mapeadas, usa tamanho do header
                    header = display_mappings.get(col, col)
                    min_chars = max(len(header), 8)
                
                # Converte caracteres em pixels (7px por char + 16px margem)
                widths[col] = min_chars * 7 + 16
            
            total_min_width += widths[col]
        
        # 2. Distribui espaço extra
        available_extra = max(0, available_width - total_min_width)
        
        if available_extra > 0:
            # Identifica colunas expandíveis presentes
            expandable_present = [col for col in self.expandable_columns if col in columns]
            
            if expandable_present:
                # Distribui espaço extra entre colunas expandíveis
                if available_extra > 800:  # Tela grande
                    # 70% para descrição_ssa, 30% para outras
                    if 'descricao_ssa' in expandable_present:
                        widths['descricao_ssa'] += int(available_extra * 0.7)
                        remaining_extra = available_extra * 0.3
                        other_expandable = [col for col in expandable_present if col != 'descricao_ssa']
                        if other_expandable:
                            extra_per_col = remaining_extra / len(other_expandable)
                            for col in other_expandable:
                                widths[col] += int(extra_per_col)
                    else:
                        # Distribui igualmente entre expandíveis
                        extra_per_col = available_extra / len(expandable_present)
                        for col in expandable_present:
                            widths[col] += int(extra_per_col)
                else:
                    # Tela menor - distribui proporcionalmente
                    weights = {'descricao_ssa': 0.6, 'descricao_execucao': 0.25, 'solicitante': 0.15}
                    for col in expandable_present:
                        weight = weights.get(col, 0.1)
                        widths[col] += int(available_extra * weight)
        
        # 3. Aplica limites
        for col in widths:
            if col == '#':
                widths[col] = max(30, min(widths[col], 60))
            elif col in self.expandable_columns:
                widths[col] = max(widths[col], 100)
                widths[col] = min(widths[col], 2000)
            else:
                widths[col] = max(widths[col], 50)
        
        return widths


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
