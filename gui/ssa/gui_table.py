# gui/ssa/gui_table.py
# Relation: used by gui/gui_ssa.py (SSAMainWindow facade).
# Relation: handles table rendering, pagination, and column width logic.
# Relation: does not modify filter state.

from __future__ import annotations

import logging
import sys

import pandas as pd

from utils.formatting import format_dataframe_for_display

logger = logging.getLogger(__name__)

QT_AVAILABLE = True
try:
    from PyQt6.QtCore import Qt, QTimer
    from PyQt6.QtWidgets import QHeaderView, QTableWidgetItem
except ImportError:
    QT_AVAILABLE = False

    class Qt:
        class AlignmentFlag:
            AlignVCenter = 0
            AlignLeft = 0

        class ItemDataRole:
            UserRole = 0

    class QHeaderView:
        class ResizeMode:
            Fixed = 0
            Interactive = 0

    class QTableWidgetItem:
        def __init__(self, *_args, **_kwargs):
            return None

        def setTextAlignment(self, *_args, **_kwargs):
            return None

        def setData(self, *_args, **_kwargs):
            return None

    class QTimer:
        @staticmethod
        def singleShot(*_args, **_kwargs):
            return None
def display_current_page(self, page_number):
    """Exibe a pãgina especificada do DataFrame filtrado."""
    # Obtem o slice de dados para a pãgina atual do paginator
    self.df_para_tabela = self.paginator.get_current_slice()

    # Congela redimensionamento automático durante a reconstrução da tabela
    try:
        header = self.table_widget.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
    except Exception as exc:
        logger.debug("Falha ao congelar modo de resize do header: %s", exc)
        header = None

    if self.df_para_tabela.empty:
        # Mesmo sem linhas, mantenha as colunas visíveis e larguras aplicadas
        self.table_widget.setRowCount(0)
        # Determina colunas válidas a partir de df_exibido (mesmo vazio, mantém schema)
        valid_cols = []
        try:
            base_cols = list(getattr(self, 'df_exibido', pd.DataFrame()).columns)
            if base_cols:
                valid_cols = [c for c in self.visible_columns if c in base_cols]
        except Exception as exc:
            logger.debug("Falha ao resolver colunas validas para tabela vazia: %s", exc)
            valid_cols = list(self.visible_columns)

        if not valid_cols:
            valid_cols = [c for c in self.default_columns if c in base_cols] if base_cols else list(self.visible_columns)

        # Atualiza colunas atuais (inclui '#') e aplica cabeçalhos
        self._current_display_columns = ['#'] + list(valid_cols)
        self.table_widget.setColumnCount(len(self._current_display_columns))
        headers = []
        for col in self._current_display_columns:
            base = '#' if col == '#' else self.internal_to_display.get(col, col)
            term = self._active_column_filters.get(col)
            has_filter = bool(term) and str(term).strip() != '' and col != '#'
            headers.append(f"[f] {base}" if has_filter else base)
        try:
            self.table_widget.setHorizontalHeaderLabels(headers)
        except Exception as exc:
            logger.debug("Falha ao aplicar cabecalhos da tabela vazia: %s", exc)

        # Aplica larguras salvas ou fallbacks seguros
        for i, col_name in enumerate(self._current_display_columns):
            px = self._saved_gui_column_widths.get(col_name)
            if px is None:
                if col_name == '#':
                    px = 30
                elif col_name == 'numero_ssa':
                    px = 110
                elif col_name == 'localizacao_codigo':
                    px = 86
                elif col_name == 'situacao':
                    px = 51
                elif col_name == 'descricao_ssa':
                    px = 296
                elif col_name == 'data_cadastro':
                    px = 100
                elif col_name == 'setor_emissor':
                    px = 58
                elif col_name == 'derivada_de':
                    px = 93
                elif col_name == 'semana_programada':
                    px = 72
                elif col_name == 'descricao_execucao':
                    px = 280
                else:
                    px = 80
            try:
                self.table_widget.setColumnWidth(i, max(30, int(px)))
            except Exception as exc:
                logger.debug("Falha ao aplicar largura da coluna %s em tabela vazia: %s", col_name, exc)

        # Garantia extra para a primeira coluna de dados
        try:
            if self.table_widget.columnCount() > 1 and self.table_widget.columnWidth(1) == 0:
                self.table_widget.setColumnWidth(1, 80)
        except Exception as exc:
            logger.debug("Falha ao reforcar largura da primeira coluna de dados em tabela vazia: %s", exc)

        # Restaura modo interativo com limites mínimos após aplicar larguras
        try:
            if header is not None:
                header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
                header.setMinimumSectionSize(80)
                header.setDefaultSectionSize(100)
        except Exception as exc:
            logger.debug("Falha ao restaurar configuracao do header em tabela vazia: %s", exc)
        return

    # Seleciona apenas as colunas visáveis
    cols_to_show = [col for col in self.visible_columns if col in self.df_para_tabela.columns]
    if not cols_to_show:
        # Se nenhuma coluna selecionada for valida, mostra as padroes
        cols_to_show = [col for col in self.default_columns if col in self.df_para_tabela.columns]
        if not cols_to_show:
            # Ultimo recurso: mostra todas
            cols_to_show = self.df_para_tabela.columns.tolist()

    # Mantêm a ordem EXATA definida em gui_main_preferences.json
    # Sem reordenacao para garantir correspondencia com as larguras calculadas

    display_df = self.df_para_tabela[cols_to_show].copy()
    # Mantêm colunas atuais para mapear ándice->nome ao salvar larguras
    self._current_display_columns = ['#'] + list(display_df.columns)

    # Adiciona a coluna de ándice '#'
    if '#' not in display_df.columns:
        display_df.insert(
            0,
            '#',
            range(
                (self.paginator.current_page - 1) * self.paginator.page_size + 1,
                (self.paginator.current_page - 1) * self.paginator.page_size + 1 + len(display_df)
            ),
        )

    # Single display-formatting entrypoint for GUI table rendering.
    # Keep format_dataframe_for_display here to avoid scattered per-cell rules.
    # OTIMIZACAO: Cache formatacao para evitar reformatar dados inalterados
    try:
        display_df_hash = int(pd.util.hash_pandas_object(display_df, index=True).sum())
    except Exception as exc:
        logger.debug("Falha ao calcular hash do DataFrame de exibicao: %s", exc)
        display_df_hash = hash(
            str(display_df.shape)
            + str(list(display_df.columns))
            + str(display_df.iloc[0].values.tobytes() if len(display_df) > 0 else "")
        )

    # Usa CacheManager unificado para cache de DataFrame formatado
    cached_formatted = self.cache_manager.get_cached_formatted_df(display_df_hash)
    if cached_formatted is None:
        try:
            formatted_df = format_dataframe_for_display(display_df)
            self.cache_manager.cache_formatted_df(display_df_hash, formatted_df)
            display_df = formatted_df
        except Exception as exc:
            # Falha de formatacao nao deve quebrar a GUI; segue sem formatar.
            logger.debug("Falha ao formatar DataFrame para exibicao na tabela: %s", exc)
    else:
        # Usa versção formatada do cache
        display_df = cached_formatted

# Configura a tabela
    self.table_widget.setRowCount(len(display_df))
    self.table_widget.setColumnCount(len(display_df.columns))

    # Define cabeçalhos de exibiçção com indicador de filtro [f] por coluna
    display_headers = []
    for col in display_df.columns:
        base = '#' if col == '#' else self.internal_to_display.get(col, col)
        term = self._active_column_filters.get(col)
        has_filter = bool(term) and str(term).strip() != ''
        if has_filter and col != '#':
            base = f"[f] {base}"
        display_headers.append(base)
    self.table_widget.setHorizontalHeaderLabels(display_headers)

    # Preenche os dados usando batch operations para melhor performance
    columns_list = list(display_df.columns)
    for row_idx in range(len(display_df)):
        row_data = display_df.iloc[row_idx]
        for col_idx, col_name in enumerate(columns_list):
            value = row_data.iloc[col_idx]
            item_text = "" if pd.isna(value) else str(value)

            # CORRECAO v3.0.5: Nao truncar colunas de descricao e solicitante - deixar word wrap funcionar
            if col_name not in ['descricao_ssa', 'descricao_execucao', 'solicitante']:
                # Trunca apenas colunas que nção sção de descriçção
                max_chars = self._calculate_max_chars_for_column(col_name, col_idx)
                if len(item_text) > max_chars:
                    item_text = item_text[:max_chars-3] + "..."

            item = QTableWidgetItem(item_text)
            item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            # Armazena o indice da linha original nos dados filtrados para referencia
            if col_name == '#':
                item.setData(
                    Qt.ItemDataRole.UserRole,
                    row_idx + (self.paginator.current_page - 1) * self.paginator.page_size,
                )
            self.table_widget.setItem(row_idx, col_idx, item)

    # Recalcula larguras APENAS quando o conjunto/ordem de colunas muda
    # ou quando a largura util do viewport mudar significativamente
    cols_sig = tuple(display_df.columns)
    try:
        vw = self.table_widget.viewport().width()
    except Exception:
        vw = -1
    need_cols = (not hasattr(self, '_widths_columns_sig')) or (self._widths_columns_sig != cols_sig)
    need_vw = (not hasattr(self, '_last_viewport_w')) or (abs(vw - self._last_viewport_w) > 12)
    if need_cols or need_vw:
        self._compute_gui_column_widths(display_df)
        self._widths_columns_sig = cols_sig
        self._last_viewport_w = vw

    # Continuamos com header congelado (Fixed) até aplicar larguras calculadas
    header = self.table_widget.horizontalHeader()

    for i, col_name in enumerate(display_df.columns):
        # Usa a coluna diretamente do DataFrame (que jã inclui '#')
        col_key = col_name

        px = getattr(self, '_gui_column_pixel_widths', {}).get(col_key)

        # Se nção hã largura calculada, usa configuraçção salva manualmente pelo usuãrio
        if px is None:
            px = self._saved_gui_column_widths.get(col_key)

        # Fallbacks apenas se nenhuma das anteriores estiver disponável
        if px is None:
            if col_key == '#':
                px = 30
            elif col_key == 'numero_ssa':
                px = 110  # leve aumento para leitura do n┬║ SSA
            elif col_key == 'localizacao_codigo':
                px = 86  # 10 chars * 7 + 16
            elif col_key == 'situacao':
                px = 51  # 5 chars * 7 + 16
            elif col_key == 'descricao_ssa':
                px = 296  # 40 chars * 7 + 16
            elif col_key == 'data_cadastro':
                px = 100  # 12 chars * 7 + 16
            elif col_key == 'setor_emissor':
                px = 58  # 6 chars * 7 + 16
            elif col_key == 'derivada_de':
                px = 93  # 11 chars * 7 + 16
            elif col_key == 'semana_programada':
                px = 72  # 8 chars * 7 + 16
            elif col_key == 'descricao_execucao':
                px = 280  # Menor que descriçção_ssa
            else:
                px = 80  # Fallback geral

        # Aplica limites de segurança apenas
        px = max(30, min(int(px), 1000))  # Permite larguras maiores para descriptions

        self.table_widget.setColumnWidth(i, px)

    # Reforça larguras após preencher dados para evitar zeragem em ambientes headless/CI
    try:
        self._force_column_widths()
    except Exception as exc:
        logger.debug("Falha ao reforcar larguras salvas da tabela: %s", exc)

    # Garantia final: se alguma coluna ainda ficou com largura 0, aplica fallback seguro
    try:
        self._ensure_nonzero_column_widths()
    except Exception as exc:
        logger.debug("Falha ao garantir larguras nao zeradas da tabela: %s", exc)

    # Após aplicar larguras, restaura modo interativo com limites mínimos
    try:
        if header is not None:
            header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
            header.setMinimumSectionSize(80)
            header.setDefaultSectionSize(100)
    except Exception as exc:
        logger.debug("Falha ao restaurar configuracao interativa do header: %s", exc)

    # Seleciona a primeira linha (se houver) e atualiza detalhes
    if self.table_widget.rowCount() > 0:
        self.table_widget.selectRow(0)
    self.update_details_from_selection()

    # Reaplica garantia de larguras não zeradas após eventos de layout pendentes
    try:
        QTimer.singleShot(0, self._ensure_nonzero_column_widths)
    except Exception as exc:
        logger.debug("Falha ao agendar reforco de largura de colunas: %s", exc)

# --- Wrappers de compatibilidade com testes antigos (PoC) ---
def display_data(self, df):  # usado em testes legados
    try:
        if df is None or getattr(df, 'empty', True):
            return
        self.df_completo = df.copy()
        self.df_exibido = df.copy()
        self.paginator.set_dataframe(self.df_exibido)
        self.display_current_page(getattr(self.paginator, 'current_page', 1))
    except Exception as exc:
        logger.warning("Falha ao exibir DataFrame via display_data de compatibilidade: %s", exc)

def _force_column_widths(self):
    """Força reaplicaçção das larguras das colunas para garantir que sejam respeitadas."""
    if not hasattr(self, 'visible_columns') or not self.visible_columns:
        return

    for i, col_name in enumerate(['#'] + self.visible_columns):
        # Busca largura salva das configurações
        px = self._saved_gui_column_widths.get(col_name)
        if px is not None:
            current_width = self.table_widget.columnWidth(i)
            if current_width != px:
                self.table_widget.setColumnWidth(i, int(px))

def _ensure_nonzero_column_widths(self):
    """Garante que nenhuma coluna permaneça com largura 0.
    Estratégia simples por índice: se alguma coluna estiver com 0px, define 80px.
    """
    try:
        col_count = self.table_widget.columnCount()
        if col_count <= 0:
            return
        for i in range(col_count):
            if self.table_widget.columnWidth(i) == 0:
                # Primeiro tenta dimensionar pelo conteúdo
                try:
                    self.table_widget.resizeColumnToContents(i)
                except Exception as exc:
                    logger.debug("Falha ao redimensionar coluna %s por conteudo: %s", i, exc)
                if self.table_widget.columnWidth(i) == 0:
                    self.table_widget.setColumnWidth(i, 80)
    except Exception as exc:
        logger.debug("Falha ao garantir larguras nao zeradas da tabela: %s", exc)

def _set_safe_width_for_col_index(self, idx: int, px: int = 80):
    """Define uma largura segura para um índice de coluna, se possível."""
    try:
        if idx < 0:
            return
        if self.table_widget.columnCount() <= idx:
            return
        if self.table_widget.columnWidth(idx) == 0:
            self.table_widget.setColumnWidth(idx, max(30, int(px)))
    except Exception as exc:
        logger.debug("Falha ao aplicar largura segura para coluna %s: %s", idx, exc)

def _compute_gui_column_widths(self, df: pd.DataFrame):
    """
    Calcula larguras de colunas usando o WidthManager unificado.
    Substitui 150+ linhas de codigo frankenstein por uma chamada limpa.
    """
    try:
        # Garante que visible_columns esteja definido
        if not hasattr(self, 'visible_columns') or not self.visible_columns:
            return

        # CORRECAO CRITICA: Filtra visible_columns para incluir apenas colunas que EXISTEM no DataFrame
        if hasattr(df, 'columns'):
            existing_visible_cols = [col for col in self.visible_columns if col in df.columns]
            if not existing_visible_cols:
                logger.error("Nenhuma coluna visivel encontrada no DataFrame")
                return

            # IMPORTANTE: Mantêm a ordem exata de self.visible_columns
            visible_df = df[existing_visible_cols].reindex(columns=existing_visible_cols)
        else:
            visible_df = df

        # Obtêm largura da tabela
        widget_width = self.table_widget.width()

        if widget_width < 500:  # Tabela ainda nção inicializada
            table_width = max(1000 if sys.platform == 'darwin' else 1400, self.width() - 50)
        else:
            table_width = widget_width - 40  # Margem para scrollbars

        min_width = 1100 if sys.platform == 'darwin' else 1400
        table_width = max(table_width, min_width)

        # Usa o WidthManager para calcular larguras otimizadas
        # IMPORTANTE: Força ordem correta das colunas (adiciona '#' no inácio)
        correct_column_order = ['#'] + existing_visible_cols
        column_widths = self.width_manager.compute_optimal_widths(
            df=visible_df,
            available_width=table_width,
            display_mappings=self.internal_to_display,
            saved_widths=self._saved_gui_column_widths,
            column_order=correct_column_order
        )

        if sys.platform == "darwin":
            column_widths = {
                key: (value + 2 if key != '#' else value)
                for key, value in column_widths.items()
            }

        # Mantem compatibilidade com codigo existente
        self._gui_column_pixel_widths = column_widths

    except Exception as e:
        logger.error("Falha em _compute_gui_column_widths: %s", e)
        # Fallback para larguras mánimas das colunas visáveis apenas
        visible_cols = ['#'] + (self.visible_columns if hasattr(self, 'visible_columns') else [])
        self._gui_column_pixel_widths = {col: 100 for col in visible_cols}

def _calculate_max_chars_for_column(self, col_name: str, col_idx: int) -> int:
    """Calcula o numero maximo de caracteres baseado na largura da coluna."""
    try:
        # Usa largura calculada pelo WidthManager ou largura atual da coluna
        width_px = getattr(self, '_gui_column_pixel_widths', {}).get(col_name)
        if width_px is None:
            width_px = self.table_widget.columnWidth(col_idx)

        # Converte pixels em caracteres (aproximadamente 7px por caractere)
        max_chars = max(15, int((width_px - 10) / 6.5))  # Melhores proporções

        # Limites especáficos por tipo de coluna
        if col_name in ['descricao_ssa', 'descricao_execucao']:
            # Descrições podem usar toda largura disponável
            max_chars = max(50, max_chars)  # Mánimo mais alto para descrições
        elif col_name in ['numero_ssa', 'localizacao_codigo']:
            # Campos curtos nção precisam de muito espaço
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

def _on_header_section_resized(self, logical_index: int, old_size: int, new_size: int):
    """Salva a largura ajustada pelo usuãrio na configuraçção persistente."""
    try:
        cols = getattr(self, '_current_display_columns', None)
        if not cols or logical_index < 0 or logical_index >= len(cols):
            return
        col_name = cols[logical_index]
        new_px = max(30, min(int(new_size), 1200))
        if col_name:
            self._saved_gui_column_widths[col_name] = new_px
            if hasattr(self, '_gui_column_pixel_widths'):
                self._gui_column_pixel_widths[col_name] = new_px
    except Exception:  # noqa: BLE001
        # Evita quebrar a GUI por falhas de IO
        pass
