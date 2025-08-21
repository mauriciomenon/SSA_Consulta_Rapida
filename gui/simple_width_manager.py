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
        print(f"DEBUG SIMPLES: saved_widths recebido: {saved_widths}")
        saved_widths = {}  # FORÇA uso das larguras fixas
        print(f"DEBUG SIMPLES: saved_widths LIMPO - usando larguras fixas")
        
        # LARGURAS FIXAS CONSTANTES - TAMANHO EXATO SEMPRE IGUAL
        fixed_widths = {}
        expandable_cols = []  # Colunas que podem crescer
        
        print(f"DEBUG SIMPLES: Processando {len(columns)} colunas na ordem: {columns}")
        
        for i, col in enumerate(columns):
            print(f"DEBUG SIMPLES: [{i+1}] Processando coluna '{col}'")
            
            if col == '#':
                fixed_widths[col] = 20  # Ajuste v3.0.4: 25px → 20px (-5px)
                print(f"  -> FIXO: 20px")
                
            elif col in saved_widths and saved_widths[col] > 0:
                fixed_widths[col] = saved_widths[col]
                print(f"  -> SALVA: {saved_widths[col]}px")
                
            elif col == 'numero_ssa':
                fixed_widths[col] = 65
                print(f"  -> NUMERO_SSA: 65px")
                
            elif col == 'situacao':
                fixed_widths[col] = 35
                print(f"  -> SITUACAO: 35px")
                
            elif col == 'setor_executor':
                fixed_widths[col] = 40
                print(f"  -> SETOR_EXECUTOR: 40px")
                
            elif col == 'setor_emissor':
                fixed_widths[col] = 40
                print(f"  -> SETOR_EMISSOR: 40px")
                
            elif col == 'localizacao_codigo':
                fixed_widths[col] = 60  # Ajuste v3.0.4: 50px → 60px (+10px)
                print(f"  -> LOCALIZACAO: 60px")
                
            elif col == 'data_cadastro':
                fixed_widths[col] = 85
                print(f"  -> DATA_CADASTRO: 85px")
                
            elif col == 'semana_cadastro':
                fixed_widths[col] = 60  # CORRIGIDO: 55 -> 60px
                print(f"  -> SEMANA_CADASTRO: 60px")
                
            elif col == 'semana_programada':
                fixed_widths[col] = 45
                print(f"  -> SEMANA_PROGRAMADA: 45px")
                
            elif col == 'derivada_de':
                fixed_widths[col] = 65  # CORRIGIDO: 60 -> 65px
                print(f"  -> DERIVADA_DE: 65px")
                
            elif col == 'grau_prioridade_emissao':
                fixed_widths[col] = 65
                print(f"  -> GRAU_PRIO_EMIS: 65px")
                
            elif col == 'grau_prioridade_planejamento':
                fixed_widths[col] = 65
                print(f"  -> GRAU_PRIO_PLAN: 65px")
                
            elif col == 'solicitante':
                fixed_widths[col] = 160
                print(f"  -> SOLICITANTE: 160px")
                
            elif col == 'descricao_ssa':
                fixed_widths[col] = 450  # VOLTOU ao valor solicitado
                expandable_cols.append(col)
                print(f"  -> DESCRICAO_SSA: 450px (base, expansível)")
                
            elif col == 'descricao_execucao':
                fixed_widths[col] = 350  # VOLTOU ao valor solicitado
                expandable_cols.append(col)
                print(f"  -> DESCRICAO_EXEC: 350px (base, expansível)")
                
            else:
                # Outros campos: largura padrão
                fixed_widths[col] = 120
                print(f"  -> OUTROS: 120px")
        
        # CÁLCULO DE CRESCIMENTO PROPORCIONAL MELHORADO
        total_fixed = sum(fixed_widths.values())
        available_extra = max(0, available_width - total_fixed)
        
        print(f"DEBUG CRESCIMENTO: Total fixo: {total_fixed}px, Disponível: {available_width}px")
        print(f"DEBUG CRESCIMENTO: Espaço extra: {available_extra}px")
        
        if available_extra > 0 and expandable_cols:
            # Divisão proporcional do espaço extra com tratamento de resto
            extra_per_col = available_extra // len(expandable_cols)
            remainder = available_extra % len(expandable_cols)
            
            for i, col in enumerate(expandable_cols):
                # Primeira coluna recebe o resto para evitar pixels perdidos
                extra_bonus = remainder if i == 0 else 0
                total_extra = extra_per_col + extra_bonus
                
                fixed_widths[col] += total_extra
                print(f"DEBUG CRESCIMENTO: {col} cresceu para {fixed_widths[col]}px (+{total_extra}px)")
        
        total_final = sum(fixed_widths.values())
        print(f"DEBUG SIMPLES: Total final: {total_final}px, Disponível: {available_width}px")
        
        # Lista larguras finais
        for col, width in sorted(fixed_widths.items()):
            print(f"  FINAL: {col} = {width}px")
        
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
