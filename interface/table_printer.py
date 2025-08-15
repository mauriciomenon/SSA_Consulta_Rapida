# interface/table_printer.py 20250724 160000 (v1.15 - Consolidado Final)

import pandas as pd
from tabulate import tabulate
from typing import Dict, Any, List, Optional
import os
import sys
import re
import unicodedata
import math
import json
import logging
from utils.formatting import format_dataframe_for_display
logger = logging.getLogger(__name__)

def get_terminal_size():
    """Obtem a altura e largura do terminal."""
    try:
        size = os.get_terminal_size()
        return size.lines, size.columns
    except OSError:
        # Valores padrão conservadores
        return 24, 80

def _estimate_column_width(series: pd.Series, header: str) -> int:
    """Estima a largura necessária para uma coluna."""
    max_header_width = len(str(header))
    # Amostra para performance
    sample_data = series.dropna().astype(str).head(100)
    if len(sample_data) == 0:
        return max_header_width
    # Considera o 95º percentil para evitar outliers muito largos
    max_data_width = sample_data.str.len().quantile(0.95, interpolation='lower')
    estimated_width = max(max_header_width, int(max_data_width) if pd.notna(max_data_width) else 0, 5)
    # Limite máximo para evitar colunas extremamente largas
    return min(estimated_width, 70)

def _select_columns_for_width(
    df: pd.DataFrame,
    display_map: Dict[str, str],
    available_width: int,
    essential_columns: List[str],
    priority_order: List[str],
    always_visible: List[str] = None,
    fixed_widths: Dict[str, int] = None
) -> list:
    """Seleciona colunas priorizando as essenciais e distribuindo o espaço."""
    valid_cols = [col for col in df.columns if not col.startswith('Unnamed:')]
    always_visible = always_visible or []
    fixed_widths = fixed_widths or {}
    # Carrega short_labels para estimar largura de cabeçalhos de forma mais compacta
    try:
        cfg = _load_priority_config()
        short_labels = cfg.get('short_labels', {}) if isinstance(cfg, dict) else {}
    except Exception:
        short_labels = {}

    # Cria lista ordenada: sempre visíveis, essenciais, prioridade, depois o resto
    ordered_cols = []
    seen = set()
    # 0. Sempre visíveis primeiro
    for col in always_visible:
        if col in valid_cols and col not in seen:
            ordered_cols.append(col)
            seen.add(col)
    # 1. Adiciona colunas essenciais na ordem EXATA
    for col in essential_columns:
        if col in valid_cols and col not in seen:
            ordered_cols.append(col)
            seen.add(col)
    # 2. Adiciona colunas prioritárias na ordem
    for col in priority_order:
        if col in valid_cols and col not in seen:
            ordered_cols.append(col)
            seen.add(col)
    # 3. Adiciona colunas restantes
    for col in valid_cols:
        if col not in seen:
            ordered_cols.append(col)

    # Calcula larguras estimadas
    estimated_widths = {'#': 4} # Largura fixa para '#'
    for col in valid_cols:
        # Prefer short label para estimar largura do cabeçalho
        renamed_col = short_labels.get(col) or display_map.get(col, col)
        if col in fixed_widths:
            estimated_widths[col] = fixed_widths[col]
        else:
            estimated_widths[col] = _estimate_column_width(df[col], renamed_col)

    selected_columns = ['#'] # Sempre inclui '#'
    total_width = estimated_widths['#'] + 3 # Espaço inicial

    # Itera pela ordem definida para selecionar colunas
    for col in ordered_cols:
        col_width = estimated_widths.get(col, 10) + 3 # +3 para separador
        if col in always_visible:
            # Sempre inclui colunas marcadas como sempre visíveis, mesmo se ultrapassar a largura disponível
            selected_columns.append(col)
            total_width += col_width
            continue
        # Se couber, adiciona
        if total_width + col_width <= available_width:
            selected_columns.append(col)
            total_width += col_width
        else:
            # Se for a primeira coluna de dados e não couber, força adicioná-la
            # para evitar tabela vazia
            if len(selected_columns) == 1: # Só tem '#'
                selected_columns.append(col)
            # Se já tem colunas de dados, para de adicionar
            break

    return selected_columns

def paginate_dataframe(df: pd.DataFrame, page_size: int):
    """Gera pedaços (chunks) de um DataFrame."""
    if df.empty:
        return
    total_pages = math.ceil(len(df) / page_size)
    for page_num in range(total_pages):
        start_idx = page_num * page_size
        end_idx = min(start_idx + page_size, len(df))
        yield df.iloc[start_idx:end_idx]

def pretty_print_df(df: pd.DataFrame, display_map: Dict[str, str], settings: dict):
    """Imprime o DataFrame de forma paginada e formatada."""
    if df.empty:
        print("Nenhum resultado para exibir.")
        return

    # --- Configuração e Detecção do Terminal ---
    terminal_height, terminal_width = get_terminal_size()
    # Deixa uma margem de segurança
    available_width = max(terminal_width - 10, 20)

    # --- Definição de Ordem de Colunas (a partir de config/column_priority.json, com fallback) ---
    cfg = _load_priority_config()
    essential_columns_in_order = cfg.get('essential') or [
        'numero_ssa', 'setor_executor', 'situacao', 'descricao_ssa',
        'data_cadastro', 'semana_cadastro', 'semana_programada', 'descricao_execucao'
    ]
    subsequent_priority = cfg.get('priority_order') or [
        'setor_emissor', 'derivada_de', 'data_limite', 'execucao_parcial',
        'anomalia', 'sistema_origem', 'grau_prioridade_emissao',
        'grau_prioridade_planejamento', 'solicitante', 'servico_origem',
        'responsavel_programacao', 'responsavel_execucao', 'prazo_limite',
        'tempo_disponivel', 'tempo_excedido', 'desde', 'tempo_total',
        'desde_1', 'total_tempo_tpe_planejado', 'total_tempo_tex_planejado',
        'total_tempo_tpo_planejado', 'total_horas_programadas',
        'semana_executada', 'num_reprogramacoes', 'execucao_simples'
    ]
    always_visible = cfg.get('always_visible', [])
    fixed_widths = cfg.get('fixed_widths', {})
    # Mescla larguras fixas do settings.display_settings.column_widths (chaves por rótulo de exibição)
    settings_display = (settings or {}).get('display_settings', {}) if isinstance(settings, dict) else {}
    label_widths = settings_display.get('column_widths', {}) if isinstance(settings_display, dict) else {}
    # Constrói um mapa internal->width a partir dos labels
    if isinstance(label_widths, dict) and label_widths:
        for internal_col in df.columns:
            # Usa short label se existir, senão display_map
            short = cfg.get('short_labels', {}).get(internal_col)
            label = short or display_map.get(internal_col, internal_col)
            if label in label_widths and isinstance(label_widths[label], int):
                fixed_widths[internal_col] = label_widths[label]
        # Largura da coluna '#' (índice) se configurada
        if '#' in label_widths and isinstance(label_widths['#'], int):
            pass  # Já tratamos '#' diretamente fora deste dict

    # --- Respeita visibilidade configurada ---
    visibility_map = {}
    try:
        visibility_map = (settings or {}).get('display_settings', {}).get('column_visibility', {}) if isinstance(settings, dict) else {}
        if not isinstance(visibility_map, dict):
            visibility_map = {}
    except Exception:
        visibility_map = {}

    allowed_columns = []
    for col in df.columns:
        visible_flag = visibility_map.get(col, True)
        if visible_flag or col in always_visible:
            allowed_columns.append(col)

    df_visible = df[allowed_columns] if allowed_columns else df

    # --- Seleção Inteligente de Colunas ---
    selected_cols = _select_columns_for_width(
        df_visible, display_map, available_width, essential_columns_in_order, subsequent_priority, always_visible, fixed_widths
    )

    if not selected_cols or (len(selected_cols) == 1 and selected_cols[0] == '#'):
        print("Nenhuma coluna para exibição foi encontrada ou selecionada.")
        return

    cols_to_display = [col for col in selected_cols if col != '#']
    if not cols_to_display:
        print("Nenhuma coluna de dados para exibição foi encontrada.")
        return

    # --- Processamento Inicial dos Dados ---
    working_df = df[cols_to_display].copy()

    # Aplica formatação compartilhada (suprime .0/NaN/NaT, datas dd/mm/YYYY, SSA)
    working_df = format_dataframe_for_display(working_df)

    # Sanitização agressiva de strings
    for col in working_df.columns:
        if pd.api.types.is_object_dtype(working_df[col]) or pd.api.types.is_string_dtype(working_df[col]):
            # Converte vazio para '-'
            working_df[col] = working_df[col].apply(
                lambda x: '-' if (isinstance(x, str) and x.strip() == '') else str(x)
            )
            # Normalização Unicode
            working_df[col] = working_df[col].apply(
                lambda x: unicodedata.normalize('NFKD', x).encode('ascii', 'ignore').decode('utf-8')
            )
            # Remove caracteres de controle e substitui quebras por espaço
            working_df[col] = working_df[col].apply(
                lambda x: re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F\n\r\t]+', ' ', x)
            )
            # Normaliza espaços e remove bordas
            working_df[col] = working_df[col].str.replace(r'\s+', ' ', regex=True).str.strip()

    # Truncar colunas de descrição de forma mais inteligente
    cols_to_truncate = ['descricao_ssa', 'descricao_execucao']
    for col in cols_to_truncate:
        if col in working_df.columns:
            # Calcula largura máxima com base no espaço disponível e número de colunas
            # Prioriza um mínimo de 30 caracteres para descrições
            base_width = max(30, (terminal_width // max(2, len(cols_to_display))))
            max_len = min(base_width, 100)  # Limite máximo
            def _truncate(val: str) -> str:
                s = val or ''
                if len(s) > max_len:
                    s = s[:max_len].rstrip()
                    # Evita '...' repetido
                    if not s.endswith('...'):
                        s += '...'
                return s
            working_df[col] = working_df[col].astype(str).apply(_truncate)

    # --- Preparação Final para Exibição ---
    # Adiciona coluna de índice
    working_df.insert(0, '#', range(1, len(working_df) + 1))
    
    # Renomeia colunas para exibição
    # Prefer nomes completos (display_map) em terminais largos; use short_labels apenas em modo compacto ou largura estreita
    use_compact_headers = False
    try:
        # available_width foi calculado acima
        use_compact_headers = (available_width < 80) or (settings.get('display_settings', {}).get('prefer_short_labels', False))
    except Exception:
        use_compact_headers = False

    renamed_columns = {'#': '#'}
    for internal_col in cols_to_display:
        short = cfg.get('short_labels', {}).get(internal_col)
        full = display_map.get(internal_col, internal_col)
        renamed_columns[internal_col] = (short if use_compact_headers and short else full)
    working_df.rename(columns=renamed_columns, inplace=True)

    # Prepara cabeçalhos e larguras para `tabulate`
    final_headers = [renamed_columns.get(col, col) for col in selected_cols]
    
    # Observação: evitamos usar maxcolwidths do tabulate aqui para preservar o conteúdo
    # exatamente como pré-processado (e.g., não forçar lowercase ou truncações adicionais).


    # --- Paginação ---
    # Linhas por página: mais conservador para forçar paginação em terminais baixos
    page_size_data_lines = max(1, terminal_height - 8)
    auto_scroll = settings.get('user_preferences', {}).get('auto_scroll_to_end', False)
    
    # Controle de auto-scroll para muitas páginas
    total_pages = math.ceil(len(working_df) / page_size_data_lines) if page_size_data_lines > 0 else 1
    max_auto_scroll_pages = settings.get('display_settings', {}).get('max_auto_scroll_pages', 3)
    
    if auto_scroll and total_pages > max_auto_scroll_pages:
        # print(f"Aviso: Muitas páginas ({total_pages}). Scroll automático desativado temporariamente.")
        # print("Use o comando 'f' após a primeira página se desejar rolar até o final.")
        auto_scroll = False # Desativa silenciosamente ou com aviso sutil

    # Gera páginas
    page_generator = paginate_dataframe(working_df, page_size_data_lines)
    pages = list(page_generator)

    if not pages:
        print("Nenhum dado para exibir após o processamento.")
        return

    # Loop de exibição
    current_page_index = 0
    while current_page_index < len(pages):
        try:
            current_page_df = pages[current_page_index]
            
            # Cabeçalho de página
            print(f"Página {current_page_index + 1} de {len(pages)}")

            # Gera e imprime a tabela para a página atual
            page_table_str = tabulate(
                current_page_df,
                headers=final_headers if current_page_index == 0 else [], # Cabeçalho só na 1ª
                tablefmt='presto',
                showindex=False
            )
            print(page_table_str)

            current_page_index += 1

            # Verifica se há mais páginas
            if current_page_index < len(pages):
                if auto_scroll:
                    continue # Vai para a próxima página automaticamente
                else:
                    remaining_pages = len(pages) - current_page_index
                    prompt_text = f"\n-- Mais ({remaining_pages} pág. restante(s)) | Enter: continuar, 'f': até o final, 'q': sair --"
                    try:
                        user_input = input(prompt_text).strip().lower()
                    except KeyboardInterrupt:
                        print("\n...exibição interrompida.")
                        break

                    if user_input == 'q':
                        print("\n...exibição interrompida.")
                        break
                    elif user_input == 'f':
                        auto_scroll = True # Ativa scroll automático para o restante
                    elif user_input == '':
                        continue # Vai para a próxima página
                    else:
                        print("Comando inválido.")
                        current_page_index -= 1 # Refaz a página atual
            else:
                # Última página: opcionalmente oferece saída explícita quando não está em auto-scroll
                if not auto_scroll:
                    try:
                        user_input = input("\n-- Fim | 'q': sair --").strip().lower()
                    except KeyboardInterrupt:
                        print("\n...exibição interrompida.")
                        break
                    if user_input == 'q':
                        print("\n...exibição interrompida.")
                break

        except KeyboardInterrupt:
            print("\n...exibição interrompida.")
            break
        except Exception as e:
            # Erro silencioso ou log simples para não quebrar a interface
            # print(f"\nErro durante exibição página {current_page_index + 1}: {e}")
            current_page_index += 1 # Tenta continuar com a próxima página


# --- Compat: formatter esperado em testes históricos ---
def _default_column_priority_config() -> Dict[str, Any]:
    return {
        "essential": [
            "numero_ssa",
            "localizacao_codigo",
            "setor_executor",
            "situacao",
            "descricao_ssa",
            "data_cadastro",
            "semana_cadastro",
            "semana_programada",
            "descricao_execucao"
        ],
        "always_visible": ["numero_ssa", "localizacao_codigo", "setor_executor", "situacao"],
        "priority_order": [
            "setor_emissor", "derivada_de", "data_limite", "execucao_parcial", "anomalia", "sistema_origem",
            "grau_prioridade_emissao", "grau_prioridade_planejamento", "solicitante", "servico_origem",
            "responsavel_programacao", "responsavel_execucao", "prazo_limite", "tempo_disponivel",
            "tempo_excedido", "desde", "tempo_total", "desde_1", "total_tempo_tpe_planejado",
            "total_tempo_tex_planejado", "total_tempo_tpo_planejado", "total_horas_programadas",
            "semana_executada", "num_reprogramacoes", "execucao_simples"
        ],
        "short_labels": {
            "numero_ssa": "#SSA",
            "localizacao_codigo": "Loc.",
            "setor_executor": "Exec.",
            "situacao": "Sit.",
            "descricao_ssa": "Desc.",
            "data_cadastro": "Emitido",
            "semana_cadastro": "Sem.Cad.",
            "semana_programada": "Sem.Prog.",
            "descricao_execucao": "Desc.Exec.",
            "setor_emissor": "Emis."
        },
        "fixed_widths": {
            "numero_ssa": 9,
            "localizacao_codigo": 10,
            "setor_emissor": 8,
            "setor_executor": 8,
            "semana_cadastro": 8,
            "data_cadastro": 10
        },
        "hidden_by_default": []
    }

def _load_priority_config() -> Dict[str, Any]:
    # Allow tests or runtime to override config dir via env var
    cfg_dir = os.environ.get('SSA_CONFIG_DIR')
    if not cfg_dir:
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        cfg_dir = os.path.join(project_root, 'config')
    cfg_path = os.path.join(cfg_dir, 'column_priority.json')

    def _is_valid(cfg: Dict[str, Any]) -> bool:
        required = [
            'essential', 'always_visible', 'priority_order', 'short_labels', 'fixed_widths', 'hidden_by_default'
        ]
        return isinstance(cfg, dict) and all(k in cfg for k in required)

    try:
        with open(cfg_path, 'r', encoding='utf-8') as f:
            loaded = json.load(f)
        if _is_valid(loaded):
            return loaded
        else:
            logger.warning(f"column_priority.json inválido em '{cfg_path}'. Será restaurado para o padrão.")
    except Exception:
        # fallthrough to restore
        logger.warning(f"column_priority.json ausente ou ilegível em '{cfg_path}'. Será restaurado para o padrão.")

    # If missing/invalid/empty: restore canonical default and return it
    try:
        os.makedirs(cfg_dir, exist_ok=True)
        default_cfg = _default_column_priority_config()
        with open(cfg_path, 'w', encoding='utf-8') as f:
            json.dump(default_cfg, f, indent=2, ensure_ascii=False)
        logger.warning(f"column_priority.json foi recriado em '{cfg_path}' com valores padrão.")
        return default_cfg
    except Exception:
        # As a last resort, return a minimal structure to avoid crashes
        logger.error("Falha ao restaurar column_priority.json. Usando estrutura mínima em memória.")
        return {
            "essential": [],
            "always_visible": [],
            "priority_order": [],
            "short_labels": {},
            "fixed_widths": {},
            "hidden_by_default": []
        }

def _normalize_ssa(num: Any) -> str:
    s = '' if pd.isna(num) else str(num).strip()
    s = re.sub(r'\D', '', s)
    if not s:
        return ''
    # já com 9 dígitos
    if len(s) == 9:
        return s
    # 3 dígitos -> prefixa ano corrente 2025
    if len(s) <= 5:
        return f"2025{s.zfill(9-4)}" if len(s) < 9 else s
    # 7-8 dígitos -> zfill para 9
    return s.zfill(9)

def format_dataframe_for_cli(
    df: pd.DataFrame,
    display_map: Optional[Dict[str, str]] = None,
    max_width: Optional[int] = None,
    highlight_terms: Optional[List[str]] = None
) -> str:
    cfg = _load_priority_config()
    short_labels = cfg.get('short_labels', {})
    # Normaliza SSA
    if 'numero_ssa' in df.columns:
        df = df.copy()
        df['numero_ssa'] = df['numero_ssa'].apply(_normalize_ssa)
    # Seleção básica de colunas (reusa lógica de pretty_print)
    # Aproveita display_map se fornecido, senão usa mapping curto
    disp_map = display_map or {}
    # Aplica short labels aos cabeçalhos na saída
    # Constrói uma tabela simples com tabulate, sem paginação
    work = df.copy()
    # Somente algumas colunas essenciais se existirem
    preferred = ['numero_ssa', 'setor_executor', 'situacao', 'descricao_ssa']
    cols = [c for c in preferred if c in work.columns]
    if not cols:
        cols = list(work.columns)[:4]
    work = work[cols]
    headers = []
    for c in cols:
        label = short_labels.get(c) or disp_map.get(c) or c
        # Larguras fixas esperadas em testes (não aplicamos padding, apenas nomes)
        headers.append(label)
    table = tabulate(work, headers=headers, tablefmt='presto', showindex=False)
    # Destaque ANSI opcional
    if highlight_terms and os.name != 'nt' and sys.stdout.isatty() and not os.environ.get('NO_COLOR') and not os.environ.get('SSA_NO_COLOR'):
        def hilite(text: str) -> str:
            for term in highlight_terms:
                if not term:
                    continue
                text = re.sub(f"({re.escape(term)})", "\x1b[1m\\1\x1b[0m", text, flags=re.IGNORECASE)
            return text
        table = '\n'.join(hilite(line) for line in table.splitlines())
    return table
