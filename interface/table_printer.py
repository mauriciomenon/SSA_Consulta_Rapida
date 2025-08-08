import pandas as pd
import os
from datetime import datetime

def format_cell_data(value, column_name):
    """
    Formata dados específicos baseado no tipo de coluna.
    """
    # Filtro abrangente para valores null/vazios
    if (pd.isna(value) or 
        value is None or 
        str(value).lower() in ['nan', 'none', 'null', '', 'nat'] or
        str(value).strip() == '' or
        str(value).strip().lower() == 'nan' or
        (isinstance(value, float) and pd.isna(value))):
        return ""
    
    # Formatação de data - remover horário
    if 'data_cadastro' in column_name.lower() or 'emitida em' in column_name.lower():
        try:
            if isinstance(value, str) and len(value) > 10:  # Tem horário
                # Tenta fazer parse e formatar apenas a data
                if ' ' in value:
                    date_part = value.split(' ')[0]
                    return date_part
            return str(value)
        except:
            return str(value)
    
    # Formatação de semana programada - remover .0
    if 'semana_programada' in column_name.lower() or 'sem. prog' in column_name.lower():
        try:
            if isinstance(value, float) and value.is_integer():
                return str(int(value))
            elif isinstance(value, str) and value.endswith('.0'):
                return value[:-2]
            return str(value)
        except:
            return str(value)
    
    # Formatação de número da SSA - garantir formato correto de 9 dígitos
    if 'numero_ssa' in column_name.lower() or 'nº ssa' in column_name.lower():
        try:
            # Converte para string e remove espaços
            ssa_str = str(value).strip()
            # Se for um número simples, adiciona o ano
            if ssa_str.isdigit() and len(ssa_str) <= 5:
                return f"2025{ssa_str:0>5}"  # Ano atual + número com 5 dígitos
            return ssa_str
        except:
            return str(value)
    
    return str(value)

def clean_text(text):
    """Remove caracteres problemáticos e trunca texto."""
    # Filtro abrangente para valores null/vazios
    if (pd.isna(text) or 
        text is None or 
        str(text).lower() in ['nan', 'none', 'null', '', 'nat'] or
        str(text).strip() == '' or
        (isinstance(text, float) and pd.isna(text))):
        return ""
    
    text = str(text)
    # Remove quebras de linha e tabs
    text = text.replace('\n', ' ').replace('\t', ' ').replace('\r', ' ')
    # Remove múltiplos espaços
    text = ' '.join(text.split())
    return text

def smart_truncate(text, max_width, column_name=""):
    """
    Trunca texto de forma inteligente, preservando informações importantes.
    """
    # Filtro abrangente para valores null/vazios
    if (pd.isna(text) or 
        text is None or 
        str(text).lower() in ['nan', 'none', 'null', '', 'nat'] or
        str(text).strip() == '' or
        (isinstance(text, float) and pd.isna(text))):
        return ""
    
    # Aplica formatação específica primeiro
    text = format_cell_data(text, column_name)
    
    text = clean_text(text)
    if len(text) <= max_width:
        return text
    
    if max_width <= 3:
        return text[:max_width]
    
    # Para textos longos, tenta preservar partes importantes
    if max_width >= 8:
        # Se parece ser um código (números, letras maiúsculas), mostra início
        if any(c.isdigit() for c in text[:10]) or any(c.isupper() for c in text[:10]):
            return text[:max_width-2] + ".."
        
        # Para textos descritivos, tenta mostrar palavras completas
        words = text.split()
        result = ""
        for word in words:
            if len(result + " " + word) <= max_width - 3:
                result += (" " if result else "") + word
            else:
                break
        
        if result:
            return result + "..."
    
    # Fallback padrão
    return text[:max_width-3] + "..." if max_width > 3 else text[:max_width]

def analyze_column_usefulness(df_sample, columns):
    """
    Analisa a utilidade das colunas baseado no conteúdo real dos dados.
    Remove colunas com muitos valores vazios ou repetitivos.
    """
    useful_columns = []
    
    for col in columns:
        if col not in df_sample.columns:
            continue
            
        # Analisa o conteúdo da coluna
        col_data = df_sample[col]
        
        # Conta valores únicos (excluindo NaN)
        unique_values = col_data.dropna().nunique()
        total_values = len(col_data)
        non_null_count = col_data.count()
        
        # Calcula métricas de utilidade
        null_percentage = (total_values - non_null_count) / total_values if total_values > 0 else 1
        uniqueness_ratio = unique_values / non_null_count if non_null_count > 0 else 0
        
        # Critérios para considerar uma coluna útil:
        # - Menos de 90% de valores nulos
        # - Mais de 1 valor único OU é uma coluna crítica
        critical_columns = ['numero_ssa', 'Nº SSA', '#', 'situacao', 'Situação']
        
        is_useful = (
            col in critical_columns or  # Sempre inclui colunas críticas
            (null_percentage < 0.9 and uniqueness_ratio > 0.01) or  # Ou tem dados variados
            (null_percentage < 0.5)  # Ou tem poucos valores nulos
        )
        
        if is_useful:
            # Adiciona score baseado na utilidade (menor é melhor para ordenação)
            score = null_percentage + (1 - uniqueness_ratio)
            useful_columns.append((col, score))
    
    # Ordena por score (melhor utilidade primeiro)
    useful_columns.sort(key=lambda x: x[1])
    return [col for col, _ in useful_columns]

def get_column_priority(columns, df_sample=None):
    """
    Define prioridade para seleção de colunas baseada nas especificações do usuário.
    
    PRIORIDADE MÁXIMA:
    1. Número da SSA (real, não contador)
    2. Setor executor  
    3. Localização
    4. Descrição da SSA
    5. Emitida em
    6. Semana programada
    
    SEGUNDO NÍVEL:
    7. Setor emissor
    8. Derivada de
    9. Semana de cadastro
    10. Descrição da execução
    """
    # Mapeamento de prioridades (menor número = maior prioridade)
    priority_map = {
        # PRIORIDADE MÁXIMA - sempre devem aparecer se existirem
        'numero_ssa': 1,          # Número real da SSA
        'Nº SSA': 1,
        'numero_ssa_original': 1,
        
        'setor_executor': 2,       # Setor executor
        'Executor': 2,
        'responsavel_execucao': 2,
        
        'localizacao_codigo': 3,   # Localização
        'localizacao': 3,
        'descricao_localizacao': 3,
        'Localização': 3,
        'Loc.': 3,                 # Nome real da coluna de localização
        
        'descricao_ssa': 4,        # Descrição da SSA (bom espaço)
        'Descrição': 4,
        'Descrição da SSA': 4,
        
        'data_emissao': 5,         # Emitida em
        'emitida_em': 5,
        'data_cadastro': 5,        # Nome real da coluna "Emitida em"
        'Emitida Em': 5,           # Nome de exibição
        'Data Emissão': 5,
        
        'semana_programada': 6,    # Semana programada
        'Sem. Prog.': 6,          # Nome de exibição
        'Semana Prog.': 6,
        'Semana Programada': 6,
        
        # SEGUNDO NÍVEL DE IMPORTÂNCIA
        'setor_emissor': 7,        # Setor emissor
        'Emissor': 7,
        'solicitante': 7,
        
        'derivada_de': 8,          # Derivada de
        'Derivada de': 8,
        'SSA Origem': 8,
        
        'semana_cadastro': 9,      # Semana de cadastro
        'data_cadastro': 9,
        'Data Cadastro': 9,
        
        'descricao_execucao': 10,  # Descrição da execução
        'Descrição Execução': 10,
        
        # Outros campos importantes
        'situacao': 11,            # Status/Situação
        'status': 11,
        'Status': 11,
        'Situação': 11,
        
        # Contador de exibição (pode manter)
        '#': 15,
        
        # Campos menos prioritários
        'equipamento': 20,
        'grau_prioridade_emissao': 21,
        'grau_prioridade_planejamento': 22,
        'data_limite': 23,
        'semana_executada': 24,
        'prazo_limite': 25,
        'tempo_excedido': 26,
        'anomalia': 27,
    }
    
    # Se temos amostra dos dados, filtra por utilidade primeiro
    if df_sample is not None:
        useful_columns = analyze_column_usefulness(df_sample, columns)
        # Mantém apenas colunas úteis
        columns = [col for col in columns if col in useful_columns]
    
    # Separa colunas em prioritárias e não prioritárias
    prioritized = []
    non_prioritized = []
    
    for col in columns:
        if col in priority_map:
            prioritized.append((col, priority_map[col]))
        else:
            non_prioritized.append((col, 100))  # Prioridade baixa para desconhecidas
    
    # Ordena por prioridade e retorna apenas os nomes das colunas
    prioritized.sort(key=lambda x: x[1])
    non_prioritized.sort(key=lambda x: x[0])  # Ordem alfabética para não prioritárias
    
    result = [col for col, _ in prioritized] + [col for col, _ in non_prioritized]
    return result

def calculate_optimal_columns(columns, terminal_width, min_col_width=8, max_col_width=25, df_sample=None):
    """
    Calcula quais colunas cabem no terminal e suas larguras ideais.
    Dá espaço especial para descrição da SSA conforme solicitado.
    """
    if terminal_width < 40:  # Terminal muito pequeno
        return columns[:1], [terminal_width - 4]
    
    # Reserva espaço para separadores e margens
    available_width = terminal_width - 6  # 2 para margens + 4 para separadores
    
    # Ordena colunas por prioridade (agora com as prioridades corretas)
    prioritized_columns = get_column_priority(columns, df_sample)
    
    selected_columns = []
    allocated_width = 0
    
    for col in prioritized_columns:
        # Larguras especiais para colunas importantes
        if col in ['descricao_ssa', 'Descrição', 'Descrição da SSA']:
            # Descrição da SSA merece espaço generoso (30-50 caracteres)
            ideal_width = min(45, available_width // 2)  # Até metade da tela
            ideal_width = max(ideal_width, 20)  # Mínimo de 20 chars
        elif col in ['numero_ssa', 'Nº SSA', 'numero_ssa_original']:
            # Número da SSA precisa de espaço moderado
            ideal_width = 12
        elif col in ['setor_executor', 'Executor', 'setor_emissor', 'Emissor']:
            # Setores precisam de espaço moderado
            ideal_width = 15
        elif col in ['localizacao_codigo', 'localizacao', 'Localização']:
            # Localização pode variar
            ideal_width = 18
        elif col in ['semana_programada', 'data_emissao', 'derivada_de']:
            # Campos de data/referência
            ideal_width = 12
        else:
            # Para outras colunas, calcula baseado no conteúdo
            if df_sample is not None and col in df_sample.columns:
                sample_values = df_sample[col].dropna().astype(str)
                if len(sample_values) > 0:
                    avg_length = sample_values.str.len().mean()
                    max_length = sample_values.str.len().max()
                    ideal_width = min(int(avg_length * 1.3), max_length, max_col_width)
                else:
                    ideal_width = min_col_width
            else:
                ideal_width = min_col_width
        
        # Considera também o nome da coluna
        ideal_width = max(len(str(col)), ideal_width, min_col_width)
        ideal_width = min(ideal_width, max_col_width)
        
        # Verifica se cabe
        needed_width = ideal_width + (3 if selected_columns else 0)  # +3 para " | "
        
        if allocated_width + needed_width <= available_width:
            selected_columns.append(col)
            allocated_width += needed_width
        else:
            # Se não couber, mas é uma coluna crítica, tenta forçar com largura menor
            if col in ['numero_ssa', 'Nº SSA', 'setor_executor', 'Executor']:
                min_critical_width = 8
                needed_critical = min_critical_width + (3 if selected_columns else 0)
                if allocated_width + needed_critical <= available_width:
                    selected_columns.append(col)
                    allocated_width += needed_critical
            break
    
    # Garante pelo menos uma coluna (número da SSA)
    if not selected_columns and prioritized_columns:
        first_col = prioritized_columns[0]
        selected_columns = [first_col]
        allocated_width = min(available_width, max_col_width)
    
    # Calcula larguras finais otimizadas
    if selected_columns:
        separators_space = (len(selected_columns) - 1) * 3
        content_space = available_width - separators_space
        
        # Larguras base inteligentes
        base_widths = []
        for col in selected_columns:
            if col in ['descricao_ssa', 'Descrição', 'Descrição da SSA']:
                # Descrição da SSA: máximo espaço possível
                base_width = min(40, content_space // 2)
            elif col in ['numero_ssa', 'Nº SSA', 'numero_ssa_original']:
                base_width = 12
            elif col in ['setor_executor', 'setor_emissor', 'Executor', 'Emissor']:
                base_width = 15
            elif col in ['localizacao_codigo', 'localizacao', 'Localização']:
                base_width = 16
            else:
                # Para outras colunas, usa análise do conteúdo
                if df_sample is not None and col in df_sample.columns:
                    sample_values = df_sample[col].dropna().astype(str)
                    if len(sample_values) > 0:
                        avg_length = sample_values.str.len().mean()
                        base_width = max(int(avg_length * 1.2), len(str(col)), min_col_width)
                    else:
                        base_width = max(len(str(col)), min_col_width)
                else:
                    base_width = max(len(str(col)), min_col_width)
            
            base_widths.append(max(min(base_width, max_col_width), min_col_width))
        
        # Ajusta se não couber
        total_base = sum(base_widths)
        if total_base > content_space:
            # Reduz proporcionalmente, mas preserva mínimos
            scale_factor = content_space / total_base
            adjusted_widths = []
            for i, w in enumerate(base_widths):
                col = selected_columns[i]
                # Descrição da SSA tem prioridade no espaço
                if col in ['descricao_ssa', 'Descrição', 'Descrição da SSA']:
                    min_desc_width = 20
                    adjusted_widths.append(max(int(w * scale_factor), min_desc_width))
                else:
                    adjusted_widths.append(max(int(w * scale_factor), min_col_width))
            base_widths = adjusted_widths
        
        return selected_columns, base_widths
    
    return [], []

def format_dataframe_for_cli(df, display_map=None, max_rows=None):
    """
    Formata um DataFrame para exibição no CLI com seleção inteligente de colunas.
    OTIMIZADO para performance.
    """
    if df.empty:
        return "\nNenhum registro para exibir.\n"
    
    try:
        # Obtém tamanho do terminal
        try:
            terminal_width = os.get_terminal_size().columns
        except:
            terminal_width = 120  # Fallback maior
        
        # Limita número de linhas para performance (já limitado no CLI, mas garante)
        if max_rows is None:
            max_rows = min(len(df), 200)  # Máximo absoluto para performance
        df_display = df.head(max_rows).copy()
        
        # Aplica mapeamentos de display se fornecido
        columns_to_use = list(df_display.columns)
        if display_map:
            df_display = df_display.rename(columns=display_map)
            columns_to_use = list(df_display.columns)
        
        # Prioriza colunas essenciais e com dados úteis
        priority_columns = ['#', 'Nº SSA', 'Executor', 'Situação', 'Descrição da SSA', 'Emitida Em', 'Sem. Prog.', 'Emissor']
        
        # Reorganiza colunas colocando prioritárias primeiro
        final_columns = []
        for pcol in priority_columns:
            if pcol in columns_to_use:
                final_columns.append(pcol)
        
        # Adiciona outras colunas não prioritárias
        for col in columns_to_use:
            if col not in final_columns:
                final_columns.append(col)
        
        # Calcula larguras otimizadas por tipo de coluna
        col_widths = []
        available_width = terminal_width - (len(final_columns) * 3)  # 3 chars para separadores
        
        # Larguras específicas por tipo de coluna
        for col in final_columns:
            col_lower = col.lower()
            if '#' in col or 'num' in col_lower:
                width = 4  # Numeração pequena
            elif 'ssa' in col_lower:
                width = 12  # Número da SSA
            elif 'executor' in col_lower or 'emissor' in col_lower:
                width = 8   # Códigos curtos
            elif 'situação' in col_lower or 'status' in col_lower:
                width = 10
            elif 'data' in col_lower or 'emitida' in col_lower:
                width = 12
            elif 'sem' in col_lower and 'prog' in col_lower:
                width = 8   # Semana programada
            elif 'loc' in col_lower:
                width = 10  # Localização
            elif 'descrição' in col_lower:
                width = max(25, available_width // 3)  # Descrição usa mais espaço
            else:
                width = 15  # Default
            
            col_widths.append(width)
        
        # Ajusta se exceder largura do terminal
        total_width = sum(col_widths) + (len(final_columns) * 3)
        if total_width > terminal_width:
            # Remove colunas menos importantes ou reduz larguras
            excess = total_width - terminal_width
            for i in range(len(col_widths) - 1, -1, -1):
                if excess <= 0:
                    break
                # Reduz largura das colunas não críticas
                if final_columns[i] not in ['#', 'Nº SSA', 'Executor']:
                    reduction = min(col_widths[i] // 2, excess)
                    col_widths[i] -= reduction
                    excess -= reduction
        
        # Seleciona colunas que cabem
        selected_columns = []
        selected_widths = []
        current_width = 0
        
        for i, col in enumerate(final_columns):
            needed_width = col_widths[i] + (3 if selected_columns else 0)
            if current_width + needed_width <= terminal_width:
                selected_columns.append(col)
                selected_widths.append(col_widths[i])
                current_width += needed_width
            else:
                break
        
        # Garante ao menos 3 colunas
        if len(selected_columns) < 3 and len(final_columns) >= 3:
            selected_columns = final_columns[:3]
            selected_widths = [terminal_width // 4] * 3
        
        # Filtra DataFrame para colunas selecionadas
        df_display = df_display[selected_columns]
        
        # Limpa e formata conteúdo das células de forma otimizada
        for i, col in enumerate(df_display.columns):
            max_width = selected_widths[i] if i < len(selected_widths) else 15
            df_display[col] = df_display[col].apply(lambda x: format_cell_data(x, col))
            df_display[col] = df_display[col].apply(lambda x: smart_truncate(str(x), max_width, col))
        
        # Gera tabela com formatação rápida
        result = []
        
        # Cabeçalho
        headers = []
        for i, col in enumerate(df_display.columns):
            width = selected_widths[i] if i < len(selected_widths) else 15
            headers.append(f"{str(col):<{width}}")
        header_line = " | ".join(headers)
        result.append(header_line)
        result.append("-" * len(header_line))
        
        # Linhas de dados (otimizado)
        for _, row in df_display.iterrows():
            cells = []
            for i, val in enumerate(row):
                width = selected_widths[i] if i < len(selected_widths) else 15
                cells.append(f"{str(val):<{width}}")
            result.append(" | ".join(cells))
        
        # Informação sobre colunas
        total_cols = len(df.columns)
        shown_cols = len(selected_columns)
        if shown_cols < total_cols:
            result.append("")
            result.append(f"Exibindo {shown_cols} de {total_cols} colunas (terminal: {terminal_width} chars)")
        
        return "\n".join(result)
        
    except Exception as e:
        # Fallback ainda mais simples
        try:
            # Apenas 3 primeiras colunas, 10 linhas
            simple_df = df.head(10).iloc[:, :3].copy()
            
            result = []
            # Cabeçalho simples
            headers = [f"{col[:15]:15}" for col in simple_df.columns]
            result.append(" | ".join(headers))
            result.append("-" * (len(headers) * 18))
            
            # Dados simples
            for _, row in simple_df.iterrows():
                cells = [f"{str(val)[:15]:15}" for val in row]
                result.append(" | ".join(cells))
            
            result.append(f"\n[ERRO] Formatação simplificada: {str(e)[:50]}")
            return "\n".join(result)
        except:
            return f"📊 {len(df)} registros | {len(df.columns)} colunas | Erro de formatação"
        
        # Linhas de dados
        for _, row in df_display.iterrows():
            cells = []
            for i, (col, val) in enumerate(row.items()):
                width = col_widths[i] if i < len(col_widths) else 15
                cells.append(f"{str(val):<{width}}")
            result.append(" | ".join(cells))
        
        # Adiciona informação sobre colunas ocultas se houver
        total_cols = len(df.columns)
        shown_cols = len(selected_columns)
        if shown_cols < total_cols:
            result.append("")
            result.append(f"Exibindo {shown_cols} de {total_cols} colunas (terminal: {terminal_width} chars)")
        
        return "\n".join(result)
        
    except Exception as e:
        # Fallback ultra-simples em caso de erro
        try:
            simple_cols = list(df.columns)[:2]  # Apenas 2 primeiras colunas
            df_simple = df[simple_cols].head(10).copy()
            
            # Limpeza básica
            for col in df_simple.columns:
                df_simple[col] = df_simple[col].apply(lambda x: str(x)[:15] if pd.notna(x) else "")
            
            # Tabela simples
            result = []
            header = " | ".join([f"{col:15}" for col in df_simple.columns])
            result.append(header)
            result.append("-" * len(header))
            
            for _, row in df_simple.iterrows():
                result.append(" | ".join([f"{str(val):15}" for val in row]))
            
            result.append(f"\n[MODO SIMPLES] Erro na formatação: {str(e)[:50]}")
            return "\n".join(result)
        except:
            return f"Total de registros: {len(df)} | Colunas: {len(df.columns)} | Erro de formatação"

def show_ssa_details(df, ssa_number, display_map=None):
    """
    Mostra detalhes completos de uma SSA específica de forma organizada.
    Esta função permite ver todas as informações importantes de uma SSA.
    """
    # Busca a SSA
    ssa_row = None
    for col in ['numero_ssa', 'Nº SSA', 'numero_ssa_original']:
        if col in df.columns:
            match = df[df[col].astype(str) == str(ssa_number)]
            if not match.empty:
                ssa_row = match.iloc[0]
                break
    
    if ssa_row is None:
        return f"\nSSA {ssa_number} não encontrada.\n"
    
    # Organiza as informações por categoria
    details = []
    details.append(f"\n{'='*60}")
    details.append(f"DETALHES DA SSA {ssa_number}")
    details.append(f"{'='*60}")
    
    # Informações principais
    details.append(f"\n📋 IDENTIFICAÇÃO:")
    for col in ['numero_ssa', 'Nº SSA', 'numero_ssa_original']:
        if col in ssa_row.index and pd.notna(ssa_row[col]):
            details.append(f"   Número: {ssa_row[col]}")
            break
    
    for col in ['situacao', 'status', 'Status', 'Situação']:
        if col in ssa_row.index and pd.notna(ssa_row[col]):
            details.append(f"   Status: {ssa_row[col]}")
            break
    
    # Responsáveis
    details.append(f"\n👥 RESPONSÁVEIS:")
    for col in ['setor_executor', 'Executor']:
        if col in ssa_row.index and pd.notna(ssa_row[col]):
            details.append(f"   Executor: {ssa_row[col]}")
            break
    
    for col in ['setor_emissor', 'Emissor', 'solicitante']:
        if col in ssa_row.index and pd.notna(ssa_row[col]):
            details.append(f"   Emissor: {ssa_row[col]}")
            break
    
    # Local e equipamento
    details.append(f"\n📍 LOCALIZAÇÃO:")
    for col in ['localizacao_codigo', 'localizacao', 'Localização']:
        if col in ssa_row.index and pd.notna(ssa_row[col]):
            details.append(f"   Local: {ssa_row[col]}")
            break
    
    for col in ['equipamento']:
        if col in ssa_row.index and pd.notna(ssa_row[col]):
            details.append(f"   Equipamento: {ssa_row[col]}")
            break
    
    # Datas importantes
    details.append(f"\n📅 CRONOGRAMA:")
    for col in ['data_emissao', 'emitida_em', 'Data Emissão']:
        if col in ssa_row.index and pd.notna(ssa_row[col]):
            details.append(f"   Emitida em: {ssa_row[col]}")
            break
    
    for col in ['semana_programada', 'Semana Prog.', 'Semana Programada']:
        if col in ssa_row.index and pd.notna(ssa_row[col]):
            details.append(f"   Programada: {ssa_row[col]}")
            break
    
    for col in ['data_cadastro', 'semana_cadastro', 'Data Cadastro']:
        if col in ssa_row.index and pd.notna(ssa_row[col]):
            details.append(f"   Cadastro: {ssa_row[col]}")
            break
    
    # Derivações
    details.append(f"\n🔗 RELAÇÕES:")
    for col in ['derivada_de', 'Derivada de', 'SSA Origem']:
        if col in ssa_row.index and pd.notna(ssa_row[col]):
            details.append(f"   Derivada de: {ssa_row[col]}")
            break
    
    # Descrições (com quebra de linha para melhor leitura)
    details.append(f"\n📝 DESCRIÇÕES:")
    for col in ['descricao_ssa', 'Descrição', 'Descrição da SSA']:
        if col in ssa_row.index and pd.notna(ssa_row[col]):
            desc = str(ssa_row[col])
            # Quebra linhas longas
            if len(desc) > 60:
                words = desc.split()
                lines = []
                current_line = ""
                for word in words:
                    if len(current_line + " " + word) <= 60:
                        current_line += (" " if current_line else "") + word
                    else:
                        if current_line:
                            lines.append(current_line)
                        current_line = word
                if current_line:
                    lines.append(current_line)
                
                details.append(f"   SSA:")
                for line in lines:
                    details.append(f"      {line}")
            else:
                details.append(f"   SSA: {desc}")
            break
    
    for col in ['descricao_execucao', 'Descrição Execução']:
        if col in ssa_row.index and pd.notna(ssa_row[col]):
            desc = str(ssa_row[col])
            if len(desc) > 60:
                words = desc.split()
                lines = []
                current_line = ""
                for word in words:
                    if len(current_line + " " + word) <= 60:
                        current_line += (" " if current_line else "") + word
                    else:
                        if current_line:
                            lines.append(current_line)
                        current_line = word
                if current_line:
                    lines.append(current_line)
                
                details.append(f"   Execução:")
                for line in lines:
                    details.append(f"      {line}")
            else:
                details.append(f"   Execução: {desc}")
            break
    
    details.append(f"\n{'='*60}")
    details.append(f"Digite 'back' ou 'q' para voltar à lista")
    details.append(f"{'='*60}\n")
    
    return "\n".join(details)
