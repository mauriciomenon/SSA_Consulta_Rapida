import pandas as pd
import json
import os
import sys
from datetime import datetime

# --- Public API expected by tests ---
def get_terminal_size(default_lines: int = 25, default_cols: int = 120):
    """Return (lines, cols) for the current terminal, with safe fallbacks."""
    try:
        size = os.get_terminal_size()
        # Some environments may not provide lines; assume a safe default
        return (default_lines, size.columns)
    except Exception:
        return (default_lines, default_cols)


def _estimate_column_width(series: pd.Series, display_name: str) -> int:
    """
    Rough width estimate for a column based on values and display header.
    Caps width to a reasonable maximum for CLI.
    """
    max_width = 70
    try:
        header_len = len(str(display_name))
        # Sample up to 200 values to avoid heavy scans
        sample = series.dropna().astype(str).head(200)
        if sample.empty:
            return min(max(header_len, 8), max_width)
        avg_len = int(sample.str.len().mean())
        p95_len = int(sample.str.len().quantile(0.95))
        # Prefer a robust high percentile but keep within limits
        est = max(header_len, min(max(avg_len, p95_len), max_width))
        # Minimum width for some known columns
        if display_name in ("Nº SSA", "numero_ssa", "No"):
            est = max(est, 9)
        if display_name in ("Executor", "setor_executor", "Exec"):
            est = max(est, 8)
        # Keep status and week compact
        if display_name.lower().startswith("stat") or display_name.lower().startswith("situa"):
            est = max(len(str(display_name)), 8)
        if display_name.lower().startswith("sem"):
            est = max(len(str(display_name)), 8)
        return min(est, max_width)
    except Exception:
        return min(max(len(str(display_name)), 8), max_width)


def _select_columns_for_width(df: pd.DataFrame, display_map: dict, terminal_width: int,
                              essential_cols: list, priority_order: list) -> list:
    """
    Choose a subset of columns that fit within terminal_width, always including '#'.
    essential_cols are included first, then priority_order, then other columns.
    """
    # Prepare columns and estimate widths including header mapping
    cols = list(df.columns)
    # Ensure row counter presence if caller added it
    selected = []
    used_width = 0
    padding_per_col = 2  # spacing between columns
    max_total = max(terminal_width - 4, 20)

    def display_name(cname):
        # Prefer provided display_map (already merged with short labels), fallback to col name
        return display_map.get(cname, cname) if isinstance(display_map, dict) else cname

    def can_fit(col):
        nonlocal used_width
        w = _estimate_column_width(df[col] if col in df.columns else pd.Series([], dtype=str), display_name(col))
        needed = (padding_per_col if selected else 0) + w
        return used_width + needed <= max_total, needed

    # Always include '#' (row counter) as first column
    selected.append('#')
    used_width += 4

    # Include essentials
    for col in essential_cols:
        if col in cols and col not in selected:
            ok, inc = can_fit(col)
            if ok:
                selected.append(col)
                used_width += inc

    # Include prioritized columns (provided) with alias resolution
    alias_map = {
        'localizacao': ['localizacao', 'descricao_localizacao', 'localizacao_codigo'],
        'emitida_em': ['emitida_em', 'data_cadastro'],
        'numero_ssa': ['numero_ssa', 'Nº SSA', 'numero_ssa_original'],
        'situacao': ['situacao', 'status'],
        'setor_executor': ['setor_executor', 'executor'],
        'setor_emissor': ['setor_emissor', 'emissor'],
    }
    for key in priority_order:
        candidates = alias_map.get(key, [key])
        chosen = next((c for c in candidates if c in cols and c not in selected), None)
        if chosen:
            ok, inc = can_fit(chosen)
            if ok:
                selected.append(chosen)
                used_width += inc

    # Fill with other columns until we run out of space
    for col in cols:
        if col not in selected:
            ok, inc = can_fit(col)
            if ok:
                selected.append(col)
                used_width += inc

    # Guarantee at least one data column alongside '#'
    if selected == ['#'] and cols:
        first_data = next((c for c in cols if c != '#'), None)
        if first_data:
            selected.append(first_data)

    return selected


def paginate_dataframe(df: pd.DataFrame, page_size: int):
    """Yield DataFrame slices of size page_size."""
    if df is None or df.empty or page_size <= 0:
        return
    total = len(df)
    for start in range(0, total, page_size):
        yield df.iloc[start:start + page_size]


def pretty_print_df(df: pd.DataFrame, display_map: dict, settings: dict):
    """
    Simple pager that prints a DataFrame honoring display_map and terminal size.
    Prints page headers like "Página X de Y" and a closing line "...exibição interrompida.".
    """
    if df is None or df.empty:
        print("Nenhum resultado para exibir.")
        return

    # Apply display mapping for headers only; keep data as-is
    df_display = df.copy()
    if display_map:
        df_display = df_display.rename(columns=display_map)

    lines, cols = get_terminal_size()
    # Reserve some lines for header/footer; keep a small, deterministic page size for tests
    page_size = max(5, lines - 5)

    pages = list(paginate_dataframe(df_display, page_size))
    total_pages = len(pages)
    current = 1

    for page in pages:
        print(f"Página {current} de {total_pages}")
        # Print a minimal table view
        try:
            print(page.to_string(index=False))
        except Exception:
            # Fallback: print first 3 columns only
            print(page.iloc[:, :3].to_string(index=False))

        # After showing a page, ask user if they want to continue
        try:
            user_in = input("Pressione Enter para continuar ou 'q' para sair: ").strip().lower()
        except Exception:
            user_in = ''
        if user_in == 'q':
            print("...exibição interrompida.")
            return
        current += 1

    # Finished all pages
    print("...exibição interrompida.")

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
    
    # Formatação de data - remover horário (mais abrangente: qualquer coluna com 'data' ou 'emit')
    name_l = column_name.lower()
    if ('data' in name_l) or ('emit' in name_l):
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
    if ('sem' in name_l):
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
            ssa_str = str(value).strip()
            # Remove espaços e zeros à esquerda
            ssa_str = ssa_str.lstrip('0')
            # Se for um número simples, adiciona o ano
            if ssa_str.isdigit() and len(ssa_str) <= 5:
                return f"2025{ssa_str.zfill(5)}"  # Ano atual + número com 5 dígitos
            # Se for um número de 9 dígitos, retorna como está
            if ssa_str.isdigit() and len(ssa_str) == 9:
                return ssa_str
            # Se for menor que 9, preenche à esquerda
            if ssa_str.isdigit() and len(ssa_str) < 9:
                return ssa_str.zfill(9)
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

def format_dataframe_for_cli(df, display_map=None, max_rows=None, highlight_terms=None, max_width=None):
    """
    Formata um DataFrame para exibição no CLI com seleção inteligente de colunas
    respeitando prioridades e largura do terminal. Evita exibir 'nan'/'NaT'.
    """
    if df.empty:
        return "\nNenhum registro para exibir.\n"

    try:
        # Load priorities and short labels from config
        config_path = os.path.join(os.path.dirname(__file__), '../config/column_priority.json')
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            priority_order_cfg = config.get('priority_order', [])
            short_labels_cfg = config.get('short_labels', {})
        except Exception:
            priority_order_cfg = []
            short_labels_cfg = {}

        # Tamanho do terminal com fallback e override por max_width (útil para testes)
        if isinstance(max_width, int) and max_width > 0:
            terminal_width = max_width
        else:
            try:
                terminal_width = os.get_terminal_size().columns
            except Exception:
                terminal_width = 120

        # Limita linhas para performance
        if max_rows is None:
            max_rows = min(len(df), 200)
        df_display = df.head(max_rows).copy()

        # Garante coluna '#' (contador de linhas)
        if '#' not in df_display.columns:
            df_display.insert(0, '#', range(1, len(df_display) + 1))

        # Pré-formata campos antes de renomear cabeçalhos (independente de labels)
        try:
            if 'numero_ssa' in df_display.columns:
                df_display['numero_ssa'] = df_display['numero_ssa'].apply(lambda v: format_cell_data(v, 'numero_ssa'))
            if 'semana_programada' in df_display.columns:
                df_display['semana_programada'] = df_display['semana_programada'].apply(lambda v: format_cell_data(v, 'semana_programada'))
            if 'semana_cadastro' in df_display.columns:
                df_display['semana_cadastro'] = df_display['semana_cadastro'].apply(lambda v: format_cell_data(v, 'semana_cadastro'))
            if 'data_cadastro' in df_display.columns:
                df_display['data_cadastro'] = df_display['data_cadastro'].apply(lambda v: format_cell_data(v, 'data_cadastro'))
            if 'emitida_em' in df_display.columns:
                df_display['emitida_em'] = df_display['emitida_em'].apply(lambda v: format_cell_data(v, 'emitida_em'))
        except Exception:
            pass

        # Não renomeia colunas para preservar chaves canônicas; só usaremos labels na renderização

        # Seleção de colunas por prioridade respeitando largura do terminal
        essential_cols = ['numero_ssa', 'setor_executor', 'localizacao', 'descricao_ssa', 'emitida_em', 'semana_programada', 'situacao']
        priority_order = priority_order_cfg

        selected_columns = _select_columns_for_width(
            df_display,
            short_labels_cfg or (display_map if isinstance(display_map, dict) else {}),
            terminal_width,
            essential_cols,
            priority_order
        )

        # Assegura que '#' está sempre na primeira posição
        if '#' in selected_columns:
            selected_columns = ['#'] + [c for c in selected_columns if c != '#']
        else:
            selected_columns.insert(0, '#')

        # Alocação de larguras: dar mais espaço para descrição/localização
        min_col_width = 6
        max_col_width = 50
        sep_space = (len(selected_columns) - 1) * 3
        content_space = max(terminal_width - sep_space, 20)

        base_widths = []
        weights = []
        for col in selected_columns:
            if col == '#':
                est = 4
                w = 0.8
            else:
                est = _estimate_column_width(df_display[col], col)
                cl = str(col).lower()
                if 'desc' in cl:
                    w = 2.5
                    est = max(est, 24)
                elif 'loc' in cl:
                    w = 1.6
                    est = max(est, 14)
                elif 'exec' in cl or 'emi' in cl:
                    w = 1.3
                    est = max(est, 10)
                elif 'ssa' in cl or 'nº' in cl or 'numero' in cl:
                    w = 1.2
                    est = max(est, 12)
                elif 'situa' in cl or 'stat' in cl:
                    w = 1.1
                    est = max(est, 10)
                elif 'data' in cl or 'emit' in cl or 'semana' in cl:
                    w = 1.0
                    est = max(est, 10)
                else:
                    w = 1.0
                    est = max(est, min_col_width)

            base_widths.append(max(min(est, max_col_width), min_col_width))
            weights.append(w)

        # Converte em alocação ponderada que caiba em content_space
        min_total = sum(base_widths)
        if min_total > content_space:
            scale = max(content_space / min_total, 0.5)
            widths = [max(int(wd * scale), min_col_width if c != '#' else 4) for wd, c in zip(base_widths, selected_columns)]
        else:
            extra = content_space - min_total
            total_weight = sum(weights) if sum(weights) > 0 else 1.0
            widths = [bw + int(extra * (wt / total_weight)) for bw, wt in zip(base_widths, weights)]

        total_with_sep = sum(widths) + sep_space
        while total_with_sep > terminal_width and len(widths) > 0:
            for i in range(len(widths) - 1, -1, -1):
                if total_with_sep <= terminal_width:
                    break
                if selected_columns[i] == '#':
                    continue
                if widths[i] > min_col_width:
                    widths[i] -= 1
                    total_with_sep -= 1

        df_display = df_display[selected_columns]

        # Enforce fixed widths for known short labels to keep output predictable
        fixed_label_widths = {
            'Exec': 6,
            'Emi': 6,
            'Sem Prog': 8,
            'Stat': 5,
        }
        # Build resolved labels for selected columns
        resolved_labels = []
        for col in df_display.columns:
            resolved_labels.append(short_labels_cfg.get(col, display_map.get(col, col) if isinstance(display_map, dict) else col))
        # Apply fixed widths where applicable
        for i, lab in enumerate(resolved_labels):
            if isinstance(lab, str) and lab in fixed_label_widths:
                widths[i] = fixed_label_widths[lab]

        for i, col in enumerate(df_display.columns):
            max_width = widths[i] if i < len(widths) else 15
            df_display[col] = df_display[col].apply(lambda x: smart_truncate(x, max_width, col))

        result = []
        headers = []
        # Construir cabeçalhos usando short_labels (ou display_map) sem alterar as chaves de dados
        for i, col in enumerate(df_display.columns):
            width = widths[i] if i < len(widths) else 15
            label = resolved_labels[i] if i < len(resolved_labels) else (short_labels_cfg.get(col, display_map.get(col, col) if isinstance(display_map, dict) else col))
            headers.append(f"{str(label):<{width}}")
        header_line = " | ".join(headers)
        result.append(header_line)
        result.append("-" * len(header_line))

        for _, row in df_display.iterrows():
            cells = []
            for i, val in enumerate(row):
                width = widths[i] if i < len(widths) else 15
                cells.append(f"{str(val):<{width}}")
            result.append(" | ".join(cells))

        total_cols = len(df.columns) + (0 if '#' in df.columns else 1)
        shown_cols = len(selected_columns)
        if shown_cols < total_cols:
            result.append("")
            result.append(f"Exibindo {shown_cols} de {total_cols} colunas (terminal: {terminal_width} chars)")

        # Optional highlight of search terms (applied only to data lines)
        if highlight_terms:
            try:
                def _supports_ansi() -> bool:
                    # Honor NO_COLOR and custom SSA_NO_COLOR
                    if os.environ.get('NO_COLOR') or os.environ.get('SSA_NO_COLOR'):
                        return False
                    try:
                        if not sys.stdout.isatty():
                            return False
                    except Exception:
                        return False
                    if os.name != 'nt':
                        return True
                    # Windows: detect modern terminals
                    env = os.environ
                    if env.get('WT_SESSION') or env.get('TERM_PROGRAM') or env.get('ANSICON') or env.get('ConEmuANSI') == 'ON':
                        return True
                    term = env.get('TERM', '')
                    if term.startswith('xterm') or term.startswith('vt'):
                        return True
                    try:
                        ver = sys.getwindowsversion()
                        return getattr(ver, 'major', 0) >= 10
                    except Exception:
                        return False

                if _supports_ansi():
                    ansi_on = "\033[1m"
                    ansi_off = "\033[0m"
                    # Prepare lowercased terms, skip negatives (starting with '!' or '-')
                    terms = [t.lower() for t in highlight_terms if isinstance(t, str) and t and not t.strip().startswith(('!', '-'))]
                    if terms:
                        for idx in range(2, len(result)):
                            line_lower = result[idx].lower()
                            new_line = result[idx]
                            for t in terms:
                                if t in line_lower:
                                    # Replace plain occurrences with bold; do a simple case-insensitive approach
                                    out = []
                                    src = result[idx]
                                    low = line_lower
                                    start = 0
                                    tl = len(t)
                                    while True:
                                        pos = low.find(t, start)
                                        if pos == -1:
                                            out.append(src[start:])
                                            break
                                        out.append(src[start:pos])
                                        out.append(ansi_on + src[pos:pos+tl] + ansi_off)
                                        start = pos + tl
                                    new_line = ''.join(out)
                                    line_lower = new_line.lower()
                                    result[idx] = new_line
                # else: no ANSI support, keep plain text
            except Exception:
                pass
        return "\n".join(result)

    except Exception as e:
        try:
            simple_df = df.head(10).iloc[:, :3].copy()
            result = []
            headers = [f"{str(col)[:15]:15}" for col in simple_df.columns]
            result.append(" | ".join(headers))
            result.append("-" * (len(headers) * 18))
            for _, row in simple_df.iterrows():
                cells = [f"{(str(val) if pd.notna(val) else '')[:15]:15}" for val in row]
                result.append(" | ".join(cells))
            result.append(f"\n[ERRO] Formatação simplificada: {str(e)[:80]}")
            return "\n".join(result)
        except Exception:
            return f"📊 {len(df)} registros | {len(df.columns)} colunas | Erro de formatação"

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
