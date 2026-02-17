# gui/ssa/gui_table.py
# Relation: used by gui/gui_ssa.py (SSAMainWindow facade).
# Relation: handles table rendering, pagination, and column width logic.
# Relation: does not modify filter state.

from __future__ import annotations

import sys

import pandas as pd

from gui.qt_stubs import Qt, QHeaderView, QTableWidgetItem, QTimer
from utils.formatting import format_dataframe_for_display
from utils.robust_logging import get_robust_logger

logger = get_robust_logger().get_logger(__name__, "gui")


def _fallback_column_width(col_name: str) -> int:
    if col_name == "#":
        return 30
    if col_name == "numero_ssa":
        return 110
    if col_name == "localizacao_codigo":
        return 86
    if col_name == "situacao":
        return 51
    if col_name == "descricao_ssa":
        return 296
    if col_name == "data_cadastro":
        return 100
    if col_name == "setor_emissor":
        return 58
    if col_name == "derivada_de":
        return 93
    if col_name == "semana_programada":
        return 72
    if col_name == "descricao_execucao":
        return 280
    return 80
def display_current_page(window, page_number):
    """Exibe a pagina especificada do DataFrame filtrado."""
    # Obtem o slice de dados para a pagina atual do paginator
    window.df_para_tabela = window.paginator.get_current_slice()
    try:
        if hasattr(window, "_ensure_data_revision"):
            window._ensure_data_revision()
    except Exception:
        pass

    # Congela redimensionamento automatico durante a reconstrucao da tabela
    try:
        header = window.table_widget.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
    except Exception as exc:
        logger.debug("Falha ao congelar modo de resize do header: %s", exc)
        header = None

    if window.df_para_tabela.empty:
        # Mesmo sem linhas, mantenha as colunas visiveis e larguras aplicadas
        window.table_widget.setRowCount(0)
        # Determina colunas validas a partir de df_exibido (mesmo vazio, mantem schema)
        valid_cols = []
        try:
            base_cols = list(getattr(window, 'df_exibido', pd.DataFrame()).columns)
            if base_cols:
                valid_cols = [c for c in window.visible_columns if c in base_cols]
        except Exception as exc:
            logger.debug("Falha ao resolver colunas validas para tabela vazia: %s", exc)
            valid_cols = list(window.visible_columns)

        if not valid_cols:
            valid_cols = [c for c in window.default_columns if c in base_cols] if base_cols else list(window.visible_columns)

        # Atualiza colunas atuais (inclui '#') e aplica cabecalhos
        window._current_display_columns = ['#'] + list(valid_cols)
        window.table_widget.setColumnCount(len(window._current_display_columns))
        headers = []
        for col in window._current_display_columns:
            base = '#' if col == '#' else window.internal_to_display.get(col, col)
            term = window._active_column_filters.get(col)
            has_filter = bool(term) and str(term).strip() != '' and col != '#'
            headers.append(f"[f] {base}" if has_filter else base)
        try:
            window.table_widget.setHorizontalHeaderLabels(headers)
        except Exception as exc:
            logger.debug("Falha ao aplicar cabecalhos da tabela vazia: %s", exc)

        # Aplica larguras salvas ou fallbacks seguros
        for i, col_name in enumerate(window._current_display_columns):
            px = window._saved_gui_column_widths.get(col_name)
            if px is None:
                px = _fallback_column_width(col_name)
            try:
                window.table_widget.setColumnWidth(i, max(30, int(px)))
            except Exception as exc:
                logger.debug("Falha ao aplicar largura da coluna %s em tabela vazia: %s", col_name, exc)

        # Garantia extra para a primeira coluna de dados
        try:
            if window.table_widget.columnCount() > 1 and window.table_widget.columnWidth(1) == 0:
                window.table_widget.setColumnWidth(1, 80)
        except Exception as exc:
            logger.debug("Falha ao reforcar largura da primeira coluna de dados em tabela vazia: %s", exc)

        # Restaura modo interativo com limites minimos apos aplicar larguras
        try:
            if header is not None:
                header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
                header.setMinimumSectionSize(80)
                header.setDefaultSectionSize(100)
        except Exception as exc:
            logger.debug("Falha ao restaurar configuracao do header em tabela vazia: %s", exc)
        return

    # Seleciona apenas as colunas visiveis
    cols_to_show = [col for col in window.visible_columns if col in window.df_para_tabela.columns]
    if not cols_to_show:
        # Se nenhuma coluna selecionada for valida, mostra as padroes
        cols_to_show = [col for col in window.default_columns if col in window.df_para_tabela.columns]
        if not cols_to_show:
            # Ultimo recurso: mostra todas
            cols_to_show = window.df_para_tabela.columns.tolist()

    # Mantem a ordem EXATA definida em gui_main_preferences.json
    # Sem reordenacao para garantir correspondencia com as larguras calculadas

    display_df = window.df_para_tabela[cols_to_show].copy()
    # Mantem colunas atuais para mapear indice->nome ao salvar larguras
    window._current_display_columns = ['#'] + list(display_df.columns)

    # Adiciona a coluna de indice '#'
    if '#' not in display_df.columns:
        display_df.insert(
            0,
            '#',
            range(
                (window.paginator.current_page - 1) * window.paginator.page_size + 1,
                (window.paginator.current_page - 1) * window.paginator.page_size + 1 + len(display_df)
            ),
        )

    # Single display-formatting entrypoint for GUI table rendering.
    # Keep format_dataframe_for_display here to avoid scattered per-cell rules.
    # OTIMIZACAO: Cache formatacao para evitar reformatar dados inalterados
    display_df_hash = None
    try:
        data_uuid = getattr(window, "_data_uuid", None)
        df_exibido_id = id(getattr(window, "df_exibido", None))
        if data_uuid is not None:
            page = int(window.paginator.current_page)
            page_size = int(window.paginator.page_size)
            display_df_hash = (
                data_uuid,
                df_exibido_id,
                page,
                page_size,
                len(display_df),
                tuple(display_df.columns),
            )
    except Exception as exc:
        logger.debug("Falha ao gerar chave de cache do DataFrame de exibicao: %s", exc)

    # Usa CacheManager unificado para cache de DataFrame formatado
    cached_formatted = None
    if display_df_hash is not None:
        cached_formatted = window.cache_manager.get_cached_formatted_df(display_df_hash)
    if cached_formatted is None:
        try:
            formatted_df = format_dataframe_for_display(display_df)
            if display_df_hash is not None:
                window.cache_manager.cache_formatted_df(display_df_hash, formatted_df)
            display_df = formatted_df
        except Exception as exc:
            # Falha de formatacao nao deve quebrar a GUI; segue sem formatar.
            logger.debug("Falha ao formatar DataFrame para exibicao na tabela: %s", exc)
    else:
        # Usa versao formatada do cache
        display_df = cached_formatted

    # Configura a tabela
    window.table_widget.setRowCount(len(display_df))
    window.table_widget.setColumnCount(len(display_df.columns))

    # Define cabecalhos de exibicao com indicador de filtro [f] por coluna
    display_headers = []
    for col in display_df.columns:
        base = '#' if col == '#' else window.internal_to_display.get(col, col)
        term = window._active_column_filters.get(col)
        has_filter = bool(term) and str(term).strip() != ''
        if has_filter and col != '#':
            base = f"[f] {base}"
        display_headers.append(base)
    window.table_widget.setHorizontalHeaderLabels(display_headers)

    # Preenche os dados usando batch operations para melhor performance
    columns_list = list(display_df.columns)
    for row_idx in range(len(display_df)):
        row_data = display_df.iloc[row_idx]
        for col_idx, col_name in enumerate(columns_list):
            value = row_data.iloc[col_idx]
            item_text = "" if pd.isna(value) else str(value)

            # CORRECAO v3.0.5: Nao truncar colunas de descricao e solicitante - deixar word wrap funcionar
            if col_name not in ['descricao_ssa', 'descricao_execucao', 'solicitante']:
                # Trunca apenas colunas que nao sao de descricao
                max_chars = window._calculate_max_chars_for_column(col_name, col_idx)
                if len(item_text) > max_chars:
                    item_text = item_text[:max_chars-3] + "..."

            item = QTableWidgetItem(item_text)
            item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            # Armazena o indice da linha original nos dados filtrados para referencia
            if col_name == '#':
                item.setData(
                    Qt.ItemDataRole.UserRole,
                    row_idx + (window.paginator.current_page - 1) * window.paginator.page_size,
                )
            window.table_widget.setItem(row_idx, col_idx, item)

    # Recalcula larguras APENAS quando o conjunto/ordem de colunas muda
    # ou quando a largura util do viewport mudar significativamente
    cols_sig = tuple(display_df.columns)
    try:
        vw = window.table_widget.viewport().width()
    except Exception:
        vw = -1
    need_cols = (not hasattr(window, '_widths_columns_sig')) or (window._widths_columns_sig != cols_sig)
    need_vw = (not hasattr(window, '_last_viewport_w')) or (abs(vw - window._last_viewport_w) > 12)
    if need_cols or need_vw:
        window._compute_gui_column_widths(display_df)
        window._widths_columns_sig = cols_sig
        window._last_viewport_w = vw

    # Continuamos com header congelado (Fixed) ate aplicar larguras calculadas
    header = window.table_widget.horizontalHeader()

    for i, col_name in enumerate(display_df.columns):
        # Usa a coluna diretamente do DataFrame (que ja inclui '#')
        col_key = col_name

        px = getattr(window, '_gui_column_pixel_widths', {}).get(col_key)

        # Se nao ha largura calculada, usa configuracao salva manualmente pelo usuario
        if px is None:
            px = window._saved_gui_column_widths.get(col_key)

        # Fallbacks apenas se nenhuma das anteriores estiver disponivel
        if px is None:
            px = _fallback_column_width(col_key)

        # Aplica limites de seguranca apenas
        px = max(30, min(int(px), 1000))  # Permite larguras maiores para descriptions

        window.table_widget.setColumnWidth(i, px)

    # Reforca larguras apos preencher dados para evitar zeragem em ambientes headless/CI
    try:
        window._force_column_widths()
    except Exception as exc:
        logger.debug("Falha ao reforcar larguras salvas da tabela: %s", exc)

    # Garantia final: se alguma coluna ainda ficou com largura 0, aplica fallback seguro
    try:
        window._ensure_nonzero_column_widths()
    except Exception as exc:
        logger.debug("Falha ao garantir larguras nao zeradas da tabela: %s", exc)

    # Apos aplicar larguras, restaura modo interativo com limites minimos
    try:
        if header is not None:
            header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
            header.setMinimumSectionSize(80)
            header.setDefaultSectionSize(100)
    except Exception as exc:
        logger.debug("Falha ao restaurar configuracao interativa do header: %s", exc)

    # Seleciona a primeira linha (se houver) e atualiza detalhes
    if window.table_widget.rowCount() > 0:
        window.table_widget.selectRow(0)
    window.update_details_from_selection()

    # Reaplica garantia de larguras nao zeradas apos eventos de layout pendentes
    try:
        QTimer.singleShot(0, window._ensure_nonzero_column_widths)
    except Exception as exc:
        logger.debug("Falha ao agendar reforco de largura de colunas: %s", exc)

# --- Wrappers de compatibilidade com testes antigos (PoC) ---
def display_data(window, df):  # usado em testes legados
    try:
        if df is None or getattr(df, 'empty', True):
            return
        window.df_completo = df.copy()
        window.df_exibido = df.copy()
        window.paginator.set_dataframe(window.df_exibido)
        window.display_current_page(getattr(window.paginator, 'current_page', 1))
    except Exception as exc:
        logger.warning("Falha ao exibir DataFrame via display_data de compatibilidade: %s", exc)

def _force_column_widths(window):
    """Forca reaplicacao das larguras das colunas para garantir que sejam respeitadas."""
    if not hasattr(window, 'visible_columns') or not window.visible_columns:
        return

    for i, col_name in enumerate(['#'] + window.visible_columns):
        # Busca largura salva das configuracoes
        px = window._saved_gui_column_widths.get(col_name)
        if px is not None:
            current_width = window.table_widget.columnWidth(i)
            if current_width != px:
                window.table_widget.setColumnWidth(i, int(px))

def _ensure_nonzero_column_widths(window):
    """Garante que nenhuma coluna permanece com largura 0.
    Estrategia simples por indice: se alguma coluna estiver com 0px, define 80px.
    """
    try:
        col_count = window.table_widget.columnCount()
        if col_count <= 0:
            return
        for i in range(col_count):
            if window.table_widget.columnWidth(i) == 0:
                # Primeiro tenta dimensionar pelo conteudo
                try:
                    window.table_widget.resizeColumnToContents(i)
                except Exception as exc:
                    logger.debug("Falha ao redimensionar coluna %s por conteudo: %s", i, exc)
                if window.table_widget.columnWidth(i) == 0:
                    window.table_widget.setColumnWidth(i, 80)
    except Exception as exc:
        logger.debug("Falha ao garantir larguras nao zeradas da tabela: %s", exc)

def _set_safe_width_for_col_index(window, idx: int, px: int = 80):
    """Define uma largura segura para um indice de coluna, se possivel."""
    try:
        if idx < 0:
            return
        if window.table_widget.columnCount() <= idx:
            return
        if window.table_widget.columnWidth(idx) == 0:
            window.table_widget.setColumnWidth(idx, max(30, int(px)))
    except Exception as exc:
        logger.debug("Falha ao aplicar largura segura para coluna %s: %s", idx, exc)

def _compute_widths_for_df(
    df: pd.DataFrame,
    visible_columns,
    width_manager,
    internal_to_display,
    saved_widths,
    widget_width: int,
    window_width: int,
):
    if not visible_columns:
        return None
    if hasattr(df, 'columns'):
        existing_visible_cols = [col for col in visible_columns if col in df.columns]
        if not existing_visible_cols:
            return None
        visible_df = df[existing_visible_cols].reindex(columns=existing_visible_cols)
    else:
        existing_visible_cols = list(visible_columns)
        visible_df = df
    table_width = widget_width
    if table_width < 500:
        table_width = max(1000 if sys.platform == 'darwin' else 1400, window_width - 50)
    else:
        table_width = table_width - 40
    min_width = 1100 if sys.platform == 'darwin' else 1400
    table_width = max(table_width, min_width)
    correct_column_order = ['#'] + existing_visible_cols
    column_widths = width_manager.compute_optimal_widths(
        df=visible_df,
        available_width=table_width,
        display_mappings=internal_to_display,
        saved_widths=saved_widths,
        column_order=correct_column_order
    )
    if sys.platform == "darwin":
        column_widths = {
            key: (value + 2 if key != '#' else value)
            for key, value in column_widths.items()
        }
    return column_widths


def _compute_gui_column_widths(window, df: pd.DataFrame):
    """
    Calcula larguras de colunas usando o WidthManager unificado.
    Substitui 150+ linhas de codigo frankenstein por uma chamada limpa.
    """
    try:
        visible_columns = getattr(window, 'visible_columns', None)
        if isinstance(visible_columns, (list, tuple)):
            visible_columns = list(visible_columns)
        else:
            visible_columns = []
        if not visible_columns:
            return
        width_manager = getattr(window, 'width_manager', None)
        if width_manager is None:
            logger.debug("WidthManager nao inicializado; pulando calculo de larguras.")
            return

        internal_to_display = getattr(window, 'internal_to_display', {})
        saved_widths = getattr(window, '_saved_gui_column_widths', {})
        try:
            widget_width = int(window.table_widget.width())
        except Exception:
            widget_width = 0
        try:
            window_width = int(window.width())
        except Exception:
            window_width = widget_width

        column_widths = _compute_widths_for_df(
            df,
            visible_columns,
            width_manager,
            internal_to_display,
            saved_widths,
            widget_width,
            window_width,
        )
        if not column_widths:
            logger.error("Nenhuma coluna visivel encontrada no DataFrame")
            return
        window._gui_column_pixel_widths = column_widths

    except Exception as exc:
        logger.error("Falha em _compute_gui_column_widths: %s", exc)
        # Fallback para larguras minimas das colunas visiveis apenas
        visible_cols = ['#'] + (visible_columns if visible_columns else [])
        window._gui_column_pixel_widths = {col: 100 for col in visible_cols}

def _calculate_max_chars_for_column(window, col_name: str, col_idx: int) -> int:
    """Calcula o numero maximo de caracteres baseado na largura da coluna."""
    try:
        # Usa largura calculada pelo WidthManager ou largura atual da coluna
        width_px = getattr(window, '_gui_column_pixel_widths', {}).get(col_name)
        if width_px is None:
            width_px = window.table_widget.columnWidth(col_idx)

        # Converte pixels em caracteres (aproximadamente 7px por caractere)
        width_px = max(1, int(width_px))
        max_chars = max(15, int((width_px - 10) / 6.5))  # Melhores proporcoes

        # Limites especificos por tipo de coluna
        if col_name in ['descricao_ssa', 'descricao_execucao']:
            # Descricoes podem usar toda largura disponivel
            max_chars = max(50, max_chars)  # Minimo mais alto para descricoes
        elif col_name in ['numero_ssa', 'localizacao_codigo']:
            # Campos curtos nao precisam de muito espaco
            max_chars = min(max_chars, 25)
        elif col_name == 'solicitante':
            # Solicitante deve caber pelo menos "MAURICIO MENON"
            max_chars = max(15, max_chars)  # Garante pelo menos 15 caracteres
        else:
            # Campos gerais - mais generoso
            max_chars = min(max_chars, 80)  # Limite mais alto

        return max_chars
    except Exception:  # noqa: BLE001
        # Fallback mais generoso
        return 80

def _on_header_section_resized(window, logical_index: int, old_size: int, new_size: int):
    """Salva a largura ajustada pelo usuario na configuracao persistente."""
    try:
        cols = getattr(window, '_current_display_columns', None)
        if not cols or logical_index < 0 or logical_index >= len(cols):
            return
        col_name = cols[logical_index]
        new_px = max(30, min(int(new_size), 1200))
        if col_name:
            window._saved_gui_column_widths[col_name] = new_px
            if hasattr(window, '_gui_column_pixel_widths'):
                window._gui_column_pixel_widths[col_name] = new_px
    except Exception:  # noqa: BLE001
        # Evita quebrar a GUI por falhas de IO
        pass
