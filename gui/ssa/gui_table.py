# gui/ssa/gui_table.py
# Relation: used by gui/gui_ssa.py (SSAMainWindow facade).
# Relation: handles table rendering, pagination, and column width logic.
# Relation: does not modify filter state.

from __future__ import annotations

import sys
from contextlib import contextmanager

import pandas as pd

from gui.qt_stubs import QHeaderView, Qt, QTableWidgetItem, QTimer
from gui.ssa import gui_details as ssa_gui_details
from utils.formatting import format_dataframe_for_display
from utils.robust_logging import get_robust_logger

logger = get_robust_logger().get_logger(__name__, "gui")


def _fallback_column_width(col_name: str) -> int:
    if col_name == "#":
        return 24
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


def _build_page_render_signature(
    window, display_df: pd.DataFrame, display_headers: list[str]
) -> tuple:
    try:
        viewport_width = int(window.table_widget.viewport().width())
    except Exception:
        viewport_width = -1

    row_markers: tuple[tuple[str, ...], ...] = tuple()
    try:
        marker_columns = [
            col
            for col in ("numero_ssa", "derivada_de", "situacao")
            if col in display_df.columns
        ]
        if not marker_columns:
            marker_columns = list(display_df.columns[: min(3, len(display_df.columns))])
        if marker_columns:
            marker_df = display_df[marker_columns].fillna("")
            row_markers = tuple(
                tuple(str(value) for value in row_values)
                for row_values in marker_df.itertuples(index=False, name=None)
            )
    except Exception as exc:
        logger.debug("Falha ao construir marcadores da assinatura de render: %s", exc)

    return (
        getattr(window, "_data_uuid", None),
        id(getattr(window, "df_exibido", None)),
        int(getattr(window.paginator, "current_page", 1)),
        int(getattr(window.paginator, "page_size", 0)),
        viewport_width,
        tuple(display_df.columns),
        tuple(display_headers),
        int(len(display_df)),
        row_markers,
    )


@contextmanager
def _freeze_table_batch_state(window, header):
    updates_enabled = None
    sorting_enabled = None
    table_signals_were_blocked = None
    header_updates_enabled = None
    header_signals_were_blocked = None

    if hasattr(window.table_widget, "updatesEnabled"):
        try:
            updates_enabled = bool(window.table_widget.updatesEnabled())
        except Exception as exc:
            logger.debug("Falha ao consultar updatesEnabled da tabela: %s", exc)
    if hasattr(window.table_widget, "isSortingEnabled"):
        try:
            sorting_enabled = bool(window.table_widget.isSortingEnabled())
        except Exception as exc:
            logger.debug("Falha ao consultar sorting da tabela: %s", exc)
    if hasattr(window.table_widget, "signalsBlocked"):
        try:
            table_signals_were_blocked = bool(window.table_widget.signalsBlocked())
        except Exception as exc:
            logger.debug("Falha ao consultar estado de sinais da tabela: %s", exc)
    if header is not None and hasattr(header, "updatesEnabled"):
        try:
            header_updates_enabled = bool(header.updatesEnabled())
        except Exception as exc:
            logger.debug("Falha ao consultar updatesEnabled do header: %s", exc)
    if header is not None and hasattr(header, "signalsBlocked"):
        try:
            header_signals_were_blocked = bool(header.signalsBlocked())
        except Exception as exc:
            logger.debug("Falha ao consultar estado de sinais do header: %s", exc)

    try:
        if hasattr(window.table_widget, "setUpdatesEnabled"):
            window.table_widget.setUpdatesEnabled(False)
    except Exception as exc:
        logger.debug("Falha ao congelar updates da tabela: %s", exc)
    try:
        if sorting_enabled and hasattr(window.table_widget, "setSortingEnabled"):
            window.table_widget.setSortingEnabled(False)
    except Exception as exc:
        logger.debug("Falha ao congelar sorting da tabela: %s", exc)
    try:
        if table_signals_were_blocked is not None:
            window.table_widget.blockSignals(True)
    except Exception as exc:
        logger.debug("Falha ao bloquear sinais da tabela: %s", exc)
    try:
        if header is not None and hasattr(header, "setUpdatesEnabled"):
            header.setUpdatesEnabled(False)
    except Exception as exc:
        logger.debug("Falha ao congelar updates do header: %s", exc)
    try:
        if header is not None and header_signals_were_blocked is not None:
            header.blockSignals(True)
    except Exception as exc:
        logger.debug("Falha ao bloquear sinais do header: %s", exc)

    try:
        yield
    finally:
        try:
            if updates_enabled is not None and hasattr(
                window.table_widget, "setUpdatesEnabled"
            ):
                window.table_widget.setUpdatesEnabled(updates_enabled)
        except Exception as exc:
            logger.debug("Falha ao restaurar updatesEnabled da tabela: %s", exc)
        try:
            if sorting_enabled is not None and hasattr(
                window.table_widget, "setSortingEnabled"
            ):
                window.table_widget.setSortingEnabled(sorting_enabled)
        except Exception as exc:
            logger.debug("Falha ao restaurar sorting da tabela: %s", exc)
        try:
            if table_signals_were_blocked is not None:
                window.table_widget.blockSignals(table_signals_were_blocked)
        except Exception as exc:
            logger.debug("Falha ao restaurar sinais da tabela: %s", exc)
        try:
            if (
                header is not None
                and header_updates_enabled is not None
                and hasattr(header, "setUpdatesEnabled")
            ):
                header.setUpdatesEnabled(header_updates_enabled)
        except Exception as exc:
            logger.debug("Falha ao restaurar updatesEnabled do header: %s", exc)
        try:
            if header is not None and header_signals_were_blocked is not None:
                header.blockSignals(header_signals_were_blocked)
        except Exception as exc:
            logger.debug("Falha ao restaurar sinais do header: %s", exc)


def _refresh_initial_details(window, *, update_details):
    if not update_details:
        return
    first_row_series = (
        window._get_series_from_row(0) if window.table_widget.rowCount() > 0 else None
    )
    try:
        next_signature = ssa_gui_details._get_details_render_signature(
            window, first_row_series
        )
        current_signature = window.details_text.property("details_render_signature")
        if (
            first_row_series is not None
            and current_signature == next_signature
            and not window.details_text.document().isEmpty()
        ):
            return
    except Exception:
        pass
    ssa_gui_details._update_details_from_series(window, first_row_series)


def display_current_page(window, page_number, *, update_details=True):
    """Exibe a pagina especificada do DataFrame filtrado."""
    try:
        requested_page = int(page_number)
    except Exception:
        requested_page = int(getattr(window.paginator, "current_page", 1))
    if requested_page < 1:
        requested_page = 1
    try:
        window.paginator.current_page = requested_page
        window.paginator.update_pagination_info()
        window.paginator.update_buttons()
    except Exception as exc:
        logger.debug("Falha ao sincronizar pagina atual do paginator: %s", exc)

    # Obtem o slice de dados para a pagina atual do paginator
    window.df_para_tabela = window.paginator.get_current_slice()
    try:
        if hasattr(window, "_ensure_data_revision"):
            window._ensure_data_revision()
    except Exception as exc:
        logger.debug(
            "Falha ao validar revisao de dados antes de renderizar pagina: %s", exc
        )

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
            base_cols = list(getattr(window, "df_exibido", pd.DataFrame()).columns)
            if base_cols:
                valid_cols = [c for c in window.visible_columns if c in base_cols]
        except Exception as exc:
            logger.debug("Falha ao resolver colunas validas para tabela vazia: %s", exc)
            valid_cols = list(window.visible_columns)

        if not valid_cols:
            valid_cols = (
                [c for c in window.default_columns if c in base_cols]
                if base_cols
                else list(window.visible_columns)
            )

        # Atualiza colunas atuais (inclui '#') e aplica cabecalhos
        window._current_display_columns = ["#"] + list(valid_cols)
        window.table_widget.setColumnCount(len(window._current_display_columns))
        headers = []
        for col in window._current_display_columns:
            base = "#" if col == "#" else window.internal_to_display.get(col, col)
            term = window._active_column_filters.get(col)
            has_filter = bool(term) and str(term).strip() != "" and col != "#"
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
                logger.debug(
                    "Falha ao aplicar largura da coluna %s em tabela vazia: %s",
                    col_name,
                    exc,
                )

        # Garantia extra para a primeira coluna de dados
        try:
            if (
                window.table_widget.columnCount() > 1
                and window.table_widget.columnWidth(1) == 0
            ):
                window.table_widget.setColumnWidth(1, 80)
        except Exception as exc:
            logger.debug(
                "Falha ao reforcar largura da primeira coluna de dados em tabela vazia: %s",
                exc,
            )

        # Restaura modo interativo com limites minimos apos aplicar larguras
        try:
            if header is not None:
                header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
                header.setMinimumSectionSize(26)
                header.setDefaultSectionSize(92)
        except Exception as exc:
            logger.debug(
                "Falha ao restaurar configuracao do header em tabela vazia: %s", exc
            )
        if update_details:
            ssa_gui_details._update_details_from_series(window, None)
        return

    # Seleciona apenas as colunas visiveis
    cols_to_show = [
        col for col in window.visible_columns if col in window.df_para_tabela.columns
    ]
    if not cols_to_show:
        # Se nenhuma coluna selecionada for valida, mostra as padroes
        cols_to_show = [
            col
            for col in window.default_columns
            if col in window.df_para_tabela.columns
        ]
        if not cols_to_show:
            # Ultimo recurso: mostra todas
            cols_to_show = window.df_para_tabela.columns.tolist()

    # Mantem a ordem EXATA definida em gui_main_preferences.json
    # Sem reordenacao para garantir correspondencia com as larguras calculadas

    display_df = window.df_para_tabela[cols_to_show].copy()
    # Mantem colunas atuais para mapear indice->nome ao salvar larguras
    window._current_display_columns = ["#"] + list(display_df.columns)

    # Adiciona a coluna de indice '#'
    if "#" not in display_df.columns:
        display_df.insert(
            0,
            "#",
            range(
                (window.paginator.current_page - 1) * window.paginator.page_size + 1,
                (window.paginator.current_page - 1) * window.paginator.page_size
                + 1
                + len(display_df),
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
            width_signature = ()
            try:
                width_manager = getattr(window, "width_manager", None)
                min_char_sizes = getattr(width_manager, "min_char_sizes", None)
                if isinstance(min_char_sizes, dict):
                    width_signature = tuple(
                        (col, min_char_sizes.get(col, "__default__"))
                        for col in display_df.columns
                    )
            except Exception as exc:
                logger.debug(
                    "Falha ao compor assinatura de largura para chave de cache: %s", exc
                )
            display_df_hash = (
                data_uuid,
                df_exibido_id,
                page,
                page_size,
                len(display_df),
                tuple(display_df.columns),
                width_signature,
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

    # Define cabecalhos de exibicao com indicador de filtro [f] por coluna
    display_headers = []
    for col in display_df.columns:
        base = "#" if col == "#" else window.internal_to_display.get(col, col)
        term = window._active_column_filters.get(col)
        has_filter = bool(term) and str(term).strip() != ""
        if has_filter and col != "#":
            base = f"[f] {base}"
        display_headers.append(base)

    render_signature = _build_page_render_signature(window, display_df, display_headers)
    previous_signature = getattr(window, "_last_table_render_signature", None)
    reuse_render = (
        previous_signature == render_signature
        and window.table_widget.rowCount() == len(display_df)
        and window.table_widget.columnCount() == len(display_df.columns)
    )

    if not reuse_render:
        with _freeze_table_batch_state(window, header):
            # Configura a tabela
            window.table_widget.setRowCount(len(display_df))
            window.table_widget.setColumnCount(len(display_df.columns))
            window.table_widget.setHorizontalHeaderLabels(display_headers)

            # Preenche os dados usando batch operations para melhor performance
            columns_list = list(display_df.columns)
            cell_render_failures = 0
            for row_idx in range(len(display_df)):
                row_data = display_df.iloc[row_idx]
                for col_idx, col_name in enumerate(columns_list):
                    try:
                        value = row_data.iloc[col_idx]
                        item_text = "" if pd.isna(value) else str(value)
                        # Keep table cells single-line to avoid visual clipping on fixed row height.
                        if item_text:
                            if "\\n" in item_text or "\\r" in item_text:
                                item_text = item_text.replace("\\n", " ").replace(
                                    "\\r", " "
                                )
                            if "\n" in item_text or "\r" in item_text:
                                item_text = " ".join(item_text.split())

                        item = QTableWidgetItem(item_text)
                        item.setTextAlignment(
                            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
                        )
                        # Armazena o indice da linha original nos dados filtrados para referencia
                        if col_name == "#":
                            item.setData(
                                Qt.ItemDataRole.UserRole,
                                row_idx
                                + (window.paginator.current_page - 1)
                                * window.paginator.page_size,
                            )
                        window.table_widget.setItem(row_idx, col_idx, item)
                    except Exception as exc:
                        cell_render_failures += 1
                        logger.debug(
                            "Falha ao renderizar celula da tabela (row=%s col=%s key=%s): %s",
                            row_idx,
                            col_idx,
                            col_name,
                            exc,
                        )
                        try:
                            window.table_widget.setItem(
                                row_idx, col_idx, QTableWidgetItem("")
                            )
                        except Exception as fallback_exc:
                            logger.debug(
                                "Falha ao aplicar fallback vazio na celula (row=%s col=%s): %s",
                                row_idx,
                                col_idx,
                                fallback_exc,
                            )
            if cell_render_failures:
                logger.warning(
                    "Renderizacao da tabela concluiu com %s falhas de celula.",
                    cell_render_failures,
                )

    # Recalcula larguras APENAS quando o conjunto/ordem de colunas muda
    # ou quando a largura util do viewport mudar significativamente
    cols_sig = tuple(display_df.columns)
    try:
        vw = window.table_widget.viewport().width()
    except Exception:
        vw = -1
    need_cols = (not hasattr(window, "_widths_columns_sig")) or (
        window._widths_columns_sig != cols_sig
    )
    need_vw = (not hasattr(window, "_last_viewport_w")) or (
        abs(vw - window._last_viewport_w) > 12
    )
    if bool(getattr(window, "_skip_width_recompute_once", False)):
        window._skip_width_recompute_once = False
        need_cols = False
        need_vw = False
    if need_cols or need_vw:
        window._compute_gui_column_widths(display_df)
        window._widths_columns_sig = cols_sig
        window._last_viewport_w = vw

    # Continuamos com header congelado (Fixed) ate aplicar larguras calculadas
    header = window.table_widget.horizontalHeader()

    for i, col_name in enumerate(display_df.columns):
        # Usa a coluna diretamente do DataFrame (que ja inclui '#')
        col_key = col_name

        px = getattr(window, "_gui_column_pixel_widths", {}).get(col_key)

        # Se nao ha largura calculada, usa configuracao salva manualmente pelo usuario
        if px is None:
            px = window._saved_gui_column_widths.get(col_key)

        # Fallbacks apenas se nenhuma das anteriores estiver disponivel
        if px is None:
            px = _fallback_column_width(col_key)

        # Aplica limites de seguranca por coluna.
        max_px = 1000
        width_manager = getattr(window, "width_manager", None)
        max_map = getattr(width_manager, "max_pixel_widths", None)
        if isinstance(max_map, dict):
            try:
                max_px = int(max_map.get(col_key, max_px))
            except Exception:
                max_px = 1000
        min_px = 24 if str(col_key) == "#" else 30
        px = max(min_px, min(int(px), max_px))

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
            header.setMinimumSectionSize(26)
            header.setDefaultSectionSize(92)
    except Exception as exc:
        logger.debug("Falha ao restaurar configuracao interativa do header: %s", exc)

    # Atualiza os detalhes da primeira linha sem forcar selecao automatica.
    _refresh_initial_details(window, update_details=update_details)

    window._last_table_render_signature = render_signature

    # Reaplica garantia de larguras nao zeradas apos eventos de layout pendentes
    try:
        QTimer.singleShot(0, window._ensure_nonzero_column_widths)
    except Exception as exc:
        logger.debug("Falha ao agendar reforco de largura de colunas: %s", exc)


# --- Wrappers de compatibilidade com testes antigos (PoC) ---
def display_data(window, df):  # usado em testes legados
    try:
        if df is None or getattr(df, "empty", True):
            return
        window.df_completo = df.copy()
        window.df_exibido = df.copy()
        window.paginator.set_dataframe(window.df_exibido)
        window.display_current_page(getattr(window.paginator, "current_page", 1))
    except Exception as exc:
        logger.warning(
            "Falha ao exibir DataFrame via display_data de compatibilidade: %s", exc
        )


def _force_column_widths(window):
    """Forca reaplicacao das larguras das colunas para garantir que sejam respeitadas."""
    if not hasattr(window, "visible_columns") or not window.visible_columns:
        return

    for i, col_name in enumerate(["#"] + window.visible_columns):
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
                    logger.debug(
                        "Falha ao redimensionar coluna %s por conteudo: %s", i, exc
                    )
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
    if hasattr(df, "columns"):
        existing_visible_cols = [col for col in visible_columns if col in df.columns]
        if not existing_visible_cols:
            return None
        visible_df = df[existing_visible_cols].reindex(columns=existing_visible_cols)
    else:
        existing_visible_cols = list(visible_columns)
        visible_df = df
    table_width = widget_width
    if table_width < 500:
        table_width = max(1000 if sys.platform == "darwin" else 1400, window_width - 50)
    else:
        table_width = table_width - 40
    min_width = 1100 if sys.platform == "darwin" else 1400
    table_width = max(table_width, min_width)
    correct_column_order = ["#"] + existing_visible_cols
    column_widths = width_manager.compute_optimal_widths(
        df=visible_df, available_width=table_width, column_order=correct_column_order
    )
    if sys.platform == "darwin":
        column_widths = {
            key: (value + 2 if key != "#" else value)
            for key, value in column_widths.items()
        }
    return column_widths


def _compute_gui_column_widths(window, df: pd.DataFrame):
    """
    Calcula larguras de colunas usando o WidthManager unificado.
    Substitui 150+ linhas de codigo frankenstein por uma chamada limpa.
    """
    try:
        visible_columns = getattr(window, "visible_columns", None)
        if isinstance(visible_columns, (list, tuple)):
            visible_columns = list(visible_columns)
        else:
            visible_columns = []
        if not visible_columns:
            return
        width_manager = getattr(window, "width_manager", None)
        if width_manager is None:
            logger.debug("WidthManager nao inicializado; pulando calculo de larguras.")
            return

        internal_to_display = getattr(window, "internal_to_display", {})
        saved_widths = getattr(window, "_saved_gui_column_widths", {})
        try:
            widget_width = int(window.table_widget.width())
        except Exception as exc:
            logger.debug(
                "Falha ao ler largura do table_widget em _compute_gui_column_widths: %s",
                exc,
            )
            widget_width = 0
        try:
            window_width = int(window.width())
        except Exception as exc:
            logger.debug(
                "Falha ao ler largura da janela em _compute_gui_column_widths: %s", exc
            )
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
        visible_cols = ["#"] + (visible_columns if visible_columns else [])
        window._gui_column_pixel_widths = {col: 100 for col in visible_cols}


def _on_header_section_resized(
    window, logical_index: int, old_size: int, new_size: int
):
    """Salva a largura ajustada pelo usuario na configuracao persistente."""
    try:
        cols = getattr(window, "_current_display_columns", None)
        if not cols or logical_index < 0 or logical_index >= len(cols):
            return
        col_name = cols[logical_index]
        new_px = max(30, min(int(new_size), 1200))
        if col_name:
            window._saved_gui_column_widths[col_name] = new_px
            if hasattr(window, "_gui_column_pixel_widths"):
                window._gui_column_pixel_widths[col_name] = new_px
            _schedule_column_width_preferences_persist(window)
    except Exception as exc:  # noqa: BLE001
        # Evita quebrar a GUI por falhas de IO, mas preserva evidencia no log.
        logger.debug("Falha ao persistir largura de coluna redimensionada: %s", exc)


def _flush_column_width_preferences(window) -> None:
    """Persiste larguras salvas em cache local para preferencias da GUI."""
    try:
        saved_widths = getattr(window, "_saved_gui_column_widths", None)
        if not isinstance(saved_widths, dict):
            return
        from gui.gui_config import GUI_MAIN_PREFERENCES

        prefs_widths = GUI_MAIN_PREFERENCES.setdefault("column_widths", {})
        changed = False
        for col_name, width in saved_widths.items():
            if not isinstance(col_name, str) or not col_name:
                continue
            try:
                width_px = max(30, min(int(width), 1200))
            except (TypeError, ValueError):
                continue
            if prefs_widths.get(col_name) != width_px:
                prefs_widths[col_name] = width_px
                changed = True
        if changed and hasattr(window, "_persist_gui_preferences"):
            window._persist_gui_preferences()
    except Exception as exc:  # noqa: BLE001
        logger.debug("Falha ao atualizar preferencias de largura de coluna: %s", exc)


def _schedule_column_width_preferences_persist(window) -> None:
    """Debounce de persistencia de largura para evitar IO excessivo em drag de header."""
    timer = getattr(window, "_column_width_persist_timer", None)
    try:
        if timer is None:
            timer = QTimer(window)
            timer.setSingleShot(True)
            timer.timeout.connect(lambda: _flush_column_width_preferences(window))
            setattr(window, "_column_width_persist_timer", timer)
        timer.start(250)
    except Exception as exc:  # noqa: BLE001
        logger.debug("Falha ao agendar persistencia de largura de coluna: %s", exc)
