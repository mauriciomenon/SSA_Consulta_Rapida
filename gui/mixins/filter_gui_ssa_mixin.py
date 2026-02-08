# gui/mixins/filter_gui_ssa_mixin.py
# Mixin containing all filter-related methods for SSAMainWindow

"""
FilterGUISSAMixin: Mixin para metodos de filtragem.

Extraido de gui_ssa.py para reduzir tamanho do arquivo.
Padrao de nomenclatura: funcao_pai_mixin.py
"""

# Imports necessarios
import logging
import copy
import os
import json
import re
import pandas as pd
from collections import OrderedDict
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (
    QMessageBox, QHBoxLayout, QVBoxLayout, QLabel,
    QLineEdit, QPushButton, QComboBox, QCheckBox,
    QFrame, QGroupBox, QSpacerItem, QSizePolicy,
    QWidget, QMenu
)

# Imports condicionais (podem nao estar disponiveis em modo headless)
try:
    from gui.workers import FilterWorker
except ImportError:
    FilterWorker = None

try:
    from gui.cache import FilterCache
except ImportError:
    FilterCache = None

try:
    from gui.widgets import FilterHelpDialog
except ImportError:
    FilterHelpDialog = None

# Imports do core
from core.app_logic import filter_dataframe, parse_search_terms
from core.config_manager import DEFAULT_DISPLAY_MAPPINGS

# Imports de gui helpers
from gui.helpers.formatting_helpers import normalize_chunk_for_parse, format_search_display

# Imports de utils
from utils.themes import get_theme_roles, normalize_theme

# Module logger
logger = logging.getLogger(__name__)

class FilterGUISSAMixin:
    """
    Mixin containing all filter-related methods.
    
    Methods extracted from SSAMainWindow to improve code organization.
    """

    def _safe_store_last_filter_state(self, reason: str = "") -> None:
        """Armazena snapshot do estado de filtros sem quebrar o fluxo da UI."""
        try:
            self._store_last_filter_state()
        except AttributeError as exc:
            if reason:
                logger.debug("Historico de filtros indisponivel (%s): %s", reason, exc)
            else:
                logger.debug("Historico de filtros indisponivel: %s", exc)
        except Exception as exc:
            if reason:
                logger.warning("Falha ao salvar historico de filtros (%s): %s", reason, exc)
            else:
                logger.warning("Falha ao salvar historico de filtros: %s", exc)

    def _has_any_active_filters(self) -> bool:
        try:
            search_text = self.search_input.text().strip() if hasattr(self, "search_input") else ""
        except Exception:
            search_text = ""
        try:
            column_filters = getattr(self, "_active_column_filters", {}) or {}
            has_column_filters = any(str(v).strip() for v in column_filters.values())
        except Exception:
            has_column_filters = False
        try:
            has_exclude_ste = bool(getattr(self, "_exclude_ste_sca", False))
        except Exception:
            has_exclude_ste = False
        try:
            has_advanced = bool(getattr(self, "_advanced_filters_active", False))
        except Exception:
            has_advanced = False
        return bool(search_text or has_column_filters or has_exclude_ste or has_advanced)

    def _set_filter_ui_idle(self) -> None:
        """Garante estado visual de ociosidade após abortar/limpar filtros."""
        try:
            progress_bar = getattr(self, "progress_bar", None)
            if progress_bar is not None:
                progress_bar.setVisible(False)
        except Exception:
            pass
        for btn_attr in ("load_button", "search_button"):
            try:
                button = getattr(self, btn_attr, None)
                if button is not None:
                    button.setEnabled(True)
            except Exception:
                pass

    def _invalidate_active_filter_request(self, reason: str = "") -> int:
        """Invalida resultados assíncronos pendentes para evitar sobrescrita tardia."""
        try:
            next_request_id = int(getattr(self, "_filter_request_seq", 0) or 0) + 1
        except Exception:
            next_request_id = 1
        self._filter_request_seq = next_request_id
        self._active_filter_request_id = next_request_id
        if reason:
            logger.debug("Filtro ativo invalidado (%s): request_id=%s", reason, next_request_id)
        return next_request_id

    def initiate_filtering(self):
        if self.df_completo.empty:
            QMessageBox.information(self, "Aviso", "Nenhum dado carregado para filtrar.")
            return

        self._safe_store_last_filter_state("initiate_filtering")
        try:
            self._debounce_timer.stop()
        except Exception:
            pass
        request_id = int(getattr(self, "_filter_request_seq", 0)) + 1
        self._filter_request_seq = request_id
        self._active_filter_request_id = request_id

        search_text = self.search_input.text().strip()
        raw_chunks = self._split_search_expression(search_text) if search_text else []
        chunk_terms_lists = [self._normalize_chunk_for_parse(chunk) for chunk in raw_chunks] if raw_chunks else ([] if not search_text else [self._normalize_chunk_for_parse(search_text)])
        # remove empty chunk lists
        chunk_terms_lists = [terms for terms in chunk_terms_lists if terms]

        if hasattr(self, 'clear_filter_button'):
            self.clear_filter_button.setEnabled(self._has_any_active_filters())

        if chunk_terms_lists:
            display_text = self._format_search_display(chunk_terms_lists)
        else:
            display_text = search_text if search_text else ''
        self._pending_search_display = display_text

        self.status_label.setText("Status: Filtrando dados...")
        self.progress_bar.setVisible(True)
        self.load_button.setEnabled(False)
        self.search_button.setEnabled(False)

        # Descobre default_mode nas configuracoes JSON (OTIMIZACAO: usando cache)
        if not hasattr(self, '_cached_default_mode'):
            # Inline import para evitar ciclo (SSAMainWindow -> mixin -> gui_ssa). Mantido propositalmente.
            from gui import gui_ssa  # noqa: WPS433
            gui_settings = gui_ssa.GUI_MAIN_PREFERENCES.get("gui_settings", {})
            self._cached_default_mode = gui_settings.get("default_filter_mode", "contains")
        default_mode = self._cached_default_mode

        # Modo síncrono (sem QThread) opcional para testes
        if getattr(self, '_sync_filtering', False):
            try:
                if chunk_terms_lists:
                    frames = []
                    for terms in chunk_terms_lists:
                        parsed = parse_search_terms(terms, default_mode=default_mode)
                        frames.append(filter_dataframe(self.df_completo, parsed))
                    df_filtrado = pd.concat(frames, axis=0, ignore_index=False).drop_duplicates().reset_index(drop=True) if frames else self.df_completo.copy()
                else:
                    df_filtrado = self.df_completo.copy()
                self.on_filter_finished(df_filtrado, request_id=request_id)
                # Em modo síncrono, garanta larguras válidas imediatamente após aplicar o filtro
                try:
                    self._ensure_nonzero_column_widths()
                except Exception:
                    pass
                try:
                    if self.table_widget.columnCount() > 1 and self.table_widget.columnWidth(1) == 0:
                        self.table_widget.setColumnWidth(1, 80)
                except Exception:
                    pass
            except Exception as e:  # noqa: BLE001
                self.on_filter_error(f"Erro ao filtrar dados: {e}", request_id=request_id)
            finally:
                self.on_filter_finished_cleanup(None, request_id=request_id)
            return

        # Fallback defensivo para ambientes sem worker assíncrono disponível
        if FilterWorker is None:
            logger.warning("FilterWorker indisponivel; aplicando filtro em modo sincrono")
            try:
                if chunk_terms_lists:
                    frames = []
                    for terms in chunk_terms_lists:
                        parsed = parse_search_terms(terms, default_mode=default_mode)
                        frames.append(filter_dataframe(self.df_completo, parsed))
                    df_filtrado = pd.concat(frames, axis=0, ignore_index=False).drop_duplicates().reset_index(drop=True) if frames else self.df_completo.copy()
                else:
                    df_filtrado = self.df_completo.copy()
                self.on_filter_finished(df_filtrado, request_id=request_id)
            except Exception as e:  # noqa: BLE001
                self.on_filter_error(f"Erro ao filtrar dados: {e}", request_id=request_id)
            finally:
                self.on_filter_finished_cleanup(None, request_id=request_id)
            return

        # Inicia a thread de filtragem (modo padrão assíncrono)
        worker = FilterWorker(self.df_completo, chunk_terms_lists, default_mode=default_mode)
        self.filter_thread = worker
        worker.filter_finished.connect(lambda df, rid=request_id: self.on_filter_finished(df, request_id=rid))
        worker.error_occurred.connect(lambda msg, rid=request_id: self.on_filter_error(msg, request_id=rid))
        worker.finished.connect(lambda w=worker, rid=request_id: self.on_filter_finished_cleanup(w, request_id=rid))
        # Garante destruição segura do objeto thread após terminar
        try:
            worker.finished.connect(worker.deleteLater)
        except Exception:
            pass
        worker.start()


    def on_filter_finished(self, df_filtrado: pd.DataFrame, request_id: int | None = None):
        active_id = getattr(self, "_active_filter_request_id", None)
        if request_id is not None and active_id is not None and request_id != active_id:
            logger.debug("Ignorando resultado de filtro obsoleto (request_id=%s, active=%s)", request_id, active_id)
            return
        # Atualiza baseline do resultado da busca global
        self._df_last_search_filtered = df_filtrado.copy()
        # OTIMIZACAO: Sinaliza que larguras precisam ser recalculadas para novo dataset
        self._widths_computed_for_df_hash = None
        self._refresh_after_filter_change()
        # CORRECAO 2026-01-08: Exibir contagem de hits e termos de busca
        total_original = len(self.df_completo) if hasattr(self, 'df_completo') and self.df_completo is not None else 0
        total_filtrado = len(self.df_exibido)
        search_text = self.search_input.text().strip() if hasattr(self, 'search_input') else ''
        if search_text:
            self.status_label.setText(f"Status: {total_filtrado} de {total_original} SSAs encontradas para '{search_text}'")
        else:
            self.status_label.setText(f"Status: {total_filtrado} SSAs encontradas.")
        if hasattr(self, 'clear_filter_button'):
            self.clear_filter_button.setEnabled(self._has_any_active_filters())
        self._apply_search_display()
        # Reforça reaplicação de larguras após busca para evitar colunas zeradas em headless/CI
        try:
            self._ensure_nonzero_column_widths()
        except Exception:
            pass
        # Recalcula e aplica larguras com base no slice atual exibido para garantir consistência imediata
        try:
            if hasattr(self, 'df_para_tabela') and not self.df_para_tabela.empty:
                self._compute_gui_column_widths(self.df_para_tabela)
                self._apply_computed_widths_only()
        except Exception:
            pass
        # Garantia específica: coluna 1 (primeira após '#') nunca deve ficar com largura 0
        try:
            if self.table_widget.columnCount() > 1 and self.table_widget.columnWidth(1) == 0:
                self.table_widget.setColumnWidth(1, 80)
        except Exception:
            pass
        # Agenda um ajuste seguro pós-loop de eventos
        try:
            QTimer.singleShot(0, lambda: self._set_safe_width_for_col_index(1, 80))
        except Exception:
            pass


    def on_filter_error(self, error_msg: str, request_id: int | None = None):
        active_id = getattr(self, "_active_filter_request_id", None)
        if request_id is not None and active_id is not None and request_id != active_id:
            logger.debug("Ignorando erro de filtro obsoleto (request_id=%s, active=%s)", request_id, active_id)
            return
        QMessageBox.critical(self, "Erro de Filtro", error_msg)
        self.status_label.setText("Status: Erro ao aplicar filtro.")


    def _cleanup_filter_worker(self, worker) -> None:
        if worker is None:
            return
        try:
            try:
                worker.filter_finished.disconnect()
            except Exception:
                pass
            try:
                worker.error_occurred.disconnect()
            except Exception:
                pass
            try:
                worker.finished.disconnect()
            except Exception:
                pass
            try:
                if hasattr(worker, 'isRunning') and worker.isRunning():
                    worker.quit()
                    worker.wait(1500)
            except Exception:
                pass
            try:
                worker.deleteLater()
            except Exception:
                pass
        except Exception:
            pass


    def on_filter_finished_cleanup(self, worker=None, request_id: int | None = None):
        """Limpa estado pós-thread de filtragem com checagens defensivas.

        Em execuções headless/CI alguns widgets podem já ter sido destruídos
        (ex.: fechamento da janela durante teardown de teste), o que pode causar
        abort em chamadas Qt nativas. Garantimos que os atributos existem e que
        o thread já não está em execução antes de manipular.
        """
        active_id = getattr(self, "_active_filter_request_id", None)
        is_stale = request_id is not None and active_id is not None and request_id != active_id
        if is_stale:
            self._cleanup_filter_worker(worker)
            if worker is not None and getattr(self, "filter_thread", None) is worker:
                self.filter_thread = None
            return
        # Debug trace para investigação de estabilidade em testes headless
        try:
            progress_bar = getattr(self, "progress_bar", None)
            if progress_bar is not None:
                try:
                    progress_bar.setVisible(False)
                except Exception:
                    pass
            for btn_attr in ("load_button", "search_button"):
                btn = getattr(self, btn_attr, None)
                if btn is not None:
                    try:
                        btn.setEnabled(True)
                    except Exception:
                        pass
            target_worker = worker if worker is not None else getattr(self, "filter_thread", None)
            self._cleanup_filter_worker(target_worker)
            if target_worker is not None and getattr(self, "filter_thread", None) is target_worker:
                self.filter_thread = None
        except Exception:
            # Nunca propagar exceção daqui; log mínimo opcional futuro
            self.filter_thread = None


    def clear_filter(self):
        """Limpa o filtro e mostra todos os dados."""
        self._safe_store_last_filter_state("clear_filter")
        self._invalidate_active_filter_request("clear_filter")
        self._set_filter_ui_idle()
        try:
            self.search_input.blockSignals(True)
            self.search_input.clear()
            self.search_input.setText('')
        finally:
            self.search_input.blockSignals(False)
        self._pending_search_display = None
        # self._active_column_filters.clear()  # Comentado para não limpar filtros por coluna
        # Limpa o cache de filtros ao limpar filtros
        self.clear_filter_cache()
        self.df_exibido = self.df_completo.copy()
        self._df_last_search_filtered = self.df_completo.copy()
        self.paginator.set_dataframe(self.df_exibido)
        (lambda cp=max(1, min(getattr(self.paginator,'current_page',1), getattr(self.paginator,'total_pages',1))): self.display_current_page(cp))()
        self.status_label.setText(f"Status: Filtro limpo. {len(self.df_exibido)} SSAs exibidas.")
        self._build_column_filters_panel()
        try:
            if hasattr(self, 'clear_filter_button'):
                self.clear_filter_button.setEnabled(self._has_any_active_filters())
        except Exception:
            pass
        # Atualizar resumo de filtros
        try:
            self._update_filters_summary()
        except Exception:
            pass

    # --- Ordenaçção por clique no cabeçalho ---

    def _on_search_text_changed(self, _text: str):
        """Reinicia o temporizador de debounce ao digitar na busca."""
        # Chamar start() novamente reinicia o QTimer automaticamente
        try:
            self._debounce_timer.start()
        except Exception:
            pass
    

    def clear_filter_cache(self):
        """Limpa o cache de filtros."""
        # Usa logger e verifica disponibilidade do FilterWorker e cache
        if FilterWorker is not None and hasattr(FilterWorker, '_cache'):
            try:
                FilterWorker._cache.clear()
                logger.info("Cache de filtros limpo")
            except Exception as e:  # pragma: no cover
                logger.debug("Falha ao limpar cache de filtros: %s", e)
        else:
            logger.debug("FilterWorker indisponivel; cache nao limpo")
    

    def get_filter_cache_stats(self) -> dict:
        """Retorna estatísticas do cache de filtros."""
        if FilterWorker is not None and hasattr(FilterWorker, '_cache') and hasattr(FilterWorker._cache, 'get_stats'):
            try:
                return FilterWorker._cache.get_stats()
            except Exception:  # pragma: no cover
                return {}
        return {}

    # --- Slots e Handlers ---


    def _open_add_column_filter_menu(self):
        """Exibe menu com colunas visiveis para ativar filtros dedicados."""
        try:
            from PyQt6.QtWidgets import QMenu
        except Exception:
            return
        if not hasattr(self, '_current_display_columns') or not self._current_display_columns:
            return
        menu = QMenu(self)
        columns = []
        for col in self._current_display_columns:
            if col == '#':
                continue
            display = DEFAULT_DISPLAY_MAPPINGS.get(col, self.internal_to_display.get(col, col))
            action = menu.addAction(display)
            action.setCheckable(True)
            action.setChecked(col in self._active_column_filters)
            action.setData(col)
            columns.append(action)
        if not columns:
            menu.deleteLater()
            return
        chosen = menu.exec(self.add_column_filter_btn.mapToGlobal(self.add_column_filter_btn.rect().bottomLeft()))
        if chosen is None:
            return
        col_name = chosen.data()
        if not col_name:
            return
        if col_name in self._active_column_filters:
            self._deactivate_column_filter(col_name)
        else:
            self._activate_column_filter(col_name)


    def _activate_column_filter(self, col_name: str):
        """Garante entrada para a coluna solicitada e prepara foco na interface."""
        if not col_name:
            return
        if col_name not in self._active_column_filters:
            self._active_column_filters[col_name] = ""
            try:
                self._mark_profile_as_custom()
            except Exception:
                pass
        self._pending_filter_focus = col_name
        self._build_column_filters_panel()



    def _deactivate_column_filter(self, col_name: str):
        """Remove coluna do conjunto de filtros ativos e atualiza a interface."""
        if not col_name:
            return
        removed = False
        if col_name in self._column_to_or_group:
            group = self._column_to_or_group.get(col_name)
            if group:
                for member in group.get('columns', []):
                    if member in self._active_column_filters:
                        self._active_column_filters.pop(member, None)
                        removed = True
                group['values'] = []
        elif col_name in self._active_column_filters:
            self._active_column_filters.pop(col_name, None)
            removed = True
        if not removed:
            return
        try:
            self._mark_profile_as_custom()
        except Exception:
            pass
        self._pending_filter_focus = None
        self._build_column_filters_panel()
        self._refresh_after_filter_change()


    def _build_column_filters_panel(self):
        # Escolhe layout de lista (compatável com versões antigas e novas)
        target_layout = None
        if hasattr(self, 'col_filters_list_layout'):
            target_layout = self.col_filters_list_layout
        elif hasattr(self, 'col_filters_layout'):
            target_layout = self.col_filters_layout
        else:
            return

        # Limpa layout
        while target_layout.count():
            item = target_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self._column_filter_inputs = {}
        self._column_filter_labels = {}
        # Controle de linhas ocultas (somente exibição)
        if not hasattr(self, '_hidden_column_filter_lines'):
            self._hidden_column_filter_lines = set()

        if not self._active_column_filters:
            lbl = QLabel("Nenhum filtro por coluna aplicado.")
            lbl.setWordWrap(True)
            target_layout.addWidget(lbl)
            target_layout.addStretch()
            self._column_filter_inputs = {}
            self._column_filter_labels = {}
            self._pending_filter_focus = None
            self._update_col_filter_indicator()
            return


        for col, term in self._active_column_filters.items():
            # Pula linhas ocultas (removidas da exibição)
            if hasattr(self, '_hidden_column_filter_lines') and col in self._hidden_column_filter_lines:
                continue
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(4)
            full_name = DEFAULT_DISPLAY_MAPPINGS.get(col, self.internal_to_display.get(col, col))
            name_lbl = QLabel(full_name)
            self._column_filter_labels[col] = name_lbl
            name_lbl.setMinimumWidth(100)
            try:
                name_lbl.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            except Exception:
                pass
            # Exibe 'OU' no campo (apenas visual). Internamente continuamos usando vírgulas.
            try:
                display_text = self._format_column_filter_display_value(str(term), column=col)
            except Exception:
                display_text = str(term)
            term_box = QLineEdit(display_text)
            self._column_filter_inputs[col] = term_box
            # Placeholder sem conectivos OU/AND — OR agora é dedicado
            term_box.setPlaceholderText("Separe termos por vírgulas. Modos: foo, ^pre, suf$, =exato, ~regex, !neg")
            # Reduzido para garantir visibilidade dos botões em telas estreitas
            term_box.setMinimumWidth(220)
            try:
                term_box.setMinimumHeight(26)
            except Exception:
                pass
            try:
                term_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            except Exception:
                pass
            self._apply_filter_widget_theme(name_lbl, term_box)
            # Enter aplica o filtro desta coluna
            try:
                term_box.returnPressed.connect(lambda c=col, tb=term_box: _mk_apply(c, tb)())
            except Exception:
                pass
            # Botao Aplicar atualiza o filtro com o texto da caixa
            apply_btn = QPushButton("Aplicar")
            try:
                apply_btn.setMinimumHeight(26)
            except Exception:
                pass
            try:
                apply_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            except Exception:
                pass
            try:
                apply_btn.setFixedWidth(72)
            except Exception:
                pass
            def _mk_apply(c=col, tb=term_box):
                def _inner():
                    # Simplified: use text directly (comma-separated terms = OR logic)
                    new_text = str(tb.text()).strip()
                    self._safe_store_last_filter_state("apply_column_filter")
                    self._active_column_filters[c] = new_text
                    self._sync_or_group_values(c, new_text)
                    self._mark_profile_as_custom()
                    self._build_column_filters_panel()
                    self._refresh_after_filter_change()
                    try:
                        if hasattr(self, "clear_filter_button"):
                            self.clear_filter_button.setEnabled(self._has_any_active_filters())
                    except Exception:
                        pass
                return _inner
            apply_btn.clicked.connect(_mk_apply())
            # Botão para remover a linha da exibição (não altera o valor do filtro)
            clear_btn = QPushButton("Remover")  # Corrigido capitalização
            try:
                clear_btn.setMinimumHeight(26)
            except Exception:
                pass
            try:
                clear_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            except Exception:
                pass
            try:
                clear_btn.setFixedWidth(72)  # Padronizado com o botão Aplicar
            except Exception:
                pass
            
            def _mk_remove_line(c=col):
                def _inner():
                    try:
                        self._hidden_column_filter_lines.add(c)
                    except Exception:
                        self._hidden_column_filter_lines = {c}
                    # Não altera self._active_column_filters[c]
                    self._build_column_filters_panel()
                    # Não refiltra; apenas exibição
                return _inner
            try:
                clear_btn.clicked.connect(_mk_remove_line())
            except Exception:
                pass
            # Oculta o botão para colunas fixas que não devem ser removidas da exibição
            try:
                fixed_cols = {"descricao_ssa", "setor_executor", "situacao", "localizacao_codigo", "descricao_localizacao"}
                if col in fixed_cols:
                    clear_btn.setVisible(False)
            except Exception:
                pass
            row.addWidget(name_lbl)
            row.addWidget(term_box, 1)
            row.addWidget(apply_btn)
            row.addWidget(clear_btn)
            # Layout order: label, input, Aplicar, Remover (OU button removed - only commas needed)
            row_w = QWidget()
            row_w.setLayout(row)
            target_layout.addWidget(row_w)

        self._update_col_filter_indicator()
        focus_col = self._pending_filter_focus
        if focus_col and focus_col in self._column_filter_inputs:
            try:
                widget = self._column_filter_inputs[focus_col]
                widget.setFocus()
                widget.selectAll()
            except Exception:
                pass
        self._pending_filter_focus = None
        self._refresh_column_filter_widgets()
        # Botção limpar todos
        # Rodape centralizado (se nao houver barra fixa)
        if not hasattr(self, 'clear_all_btn'):
            clear_all = QPushButton("Limpar todos filtros de colunas")
            clear_all.setMaximumWidth(260)
            clear_all.clicked.connect(self._clear_all_column_filters)
            footer = QHBoxLayout()
            footer.addStretch()
            footer.addWidget(clear_all)
            footer.addStretch()
            row_w = QWidget()
            row_w.setLayout(footer)
            target_layout.addWidget(row_w)
        target_layout.addStretch()



    def _apply_filter_widget_theme(self, label_widget=None, input_widget=None):
        theme = getattr(self, '_current_theme', '') or 'dark'
        roles = get_theme_roles(theme)
        label_color = roles.get('support_text_color') or roles.get('label_color')
        if label_widget is not None:
            label_widget.setStyleSheet(f'color:{label_color};')
        if input_widget is not None:
            input_text = roles.get('input_text')
            input_bg = roles.get('input_bg')
            input_border = roles.get('input_border')
            input_focus = roles.get('input_border_focus') or roles.get('accent')
            input_placeholder = roles.get('input_placeholder')
            style = (
                f"QLineEdit {{ font-size:11px; color:{input_text}; background:{input_bg}; border:1px solid {input_border}; border-radius:4px; padding:3px 6px; }}\n"
                f"QLineEdit::placeholder {{ color:{input_placeholder}; }}\n"
                f"QLineEdit:focus {{ border:1px solid {input_focus}; }}\n"
            )
            input_widget.setStyleSheet(style)


    def _refresh_column_filter_widgets(self):
        labels = getattr(self, '_column_filter_labels', {}) or {}
        inputs = getattr(self, '_column_filter_inputs', {}) or {}
        for col, label in labels.items():
            self._apply_filter_widget_theme(label, inputs.get(col))

    def _clear_single_column_filter(self, col_name: str, current_text: str = None):
        if col_name in self._active_column_filters:
            # Se já está vazio e o campo também está vazio, não faz nada
            try:
                if str(self._active_column_filters.get(col_name, '')).strip() == '' and (current_text is None or str(current_text).strip() == ''):
                    return
            except Exception:
                pass
            self._safe_store_last_filter_state("clear_single_column_filter")
            if col_name in self._column_to_or_group:
                self._sync_or_group_values(col_name, "")
            elif col_name in self._active_column_filters:
                self._active_column_filters[col_name] = ""
            self._mark_profile_as_custom()
            self._build_column_filters_panel()
            self._refresh_after_filter_change()
            try:
                if hasattr(self, "clear_filter_button"):
                    self.clear_filter_button.setEnabled(self._has_any_active_filters())
            except Exception:
                pass


    def _clear_all_column_filters(self):
        if self._active_column_filters:
            self._safe_store_last_filter_state("clear_all_column_filters")
            for group in getattr(self, '_column_or_groups', []):
                group['values'] = []
                for col in group.get('columns', []):
                    self._active_column_filters[col] = ""
            for col in list(self._active_column_filters.keys()):
                if col not in self._column_to_or_group:
                    self._active_column_filters[col] = ""
            # Restaura linhas ocultas apenas na exibição
            try:
                self._hidden_column_filter_lines.clear()
            except Exception:
                self._hidden_column_filter_lines = set()
            # Limpa também o texto dedicado de OR (somente exibição)
            self._dedicated_or_text = ''
            self._mark_profile_as_custom()
            self._build_column_filters_panel()
            self._refresh_after_filter_change()
            try:
                if hasattr(self, "clear_filter_button"):
                    self.clear_filter_button.setEnabled(self._has_any_active_filters())
            except Exception:
                pass


    def _on_exclude_ste_sca_toggled(self, checked: bool):
        self._safe_store_last_filter_state("toggle_exclude_ste")
        checked_bool = bool(checked)
        self._exclude_ste_sca = checked_bool
        try:
            tab_contexts = getattr(self, "_tab_contexts", None)
            if isinstance(tab_contexts, list):
                for ctx in tab_contexts:
                    if not isinstance(ctx, dict):
                        continue
                    checkbox = ctx.get("exclude_ste_checkbox")
                    if checkbox is None:
                        continue
                    try:
                        if checkbox.isChecked() != checked_bool:
                            checkbox.blockSignals(True)
                            checkbox.setChecked(checked_bool)
                    finally:
                        try:
                            checkbox.blockSignals(False)
                        except Exception:
                            pass
            elif hasattr(self, "exclude_ste_checkbox") and self.exclude_ste_checkbox is not None:
                checkbox = self.exclude_ste_checkbox
                try:
                    if checkbox.isChecked() != checked_bool:
                        checkbox.blockSignals(True)
                        checkbox.setChecked(checked_bool)
                finally:
                    try:
                        checkbox.blockSignals(False)
                    except Exception:
                        pass
        except Exception:
            pass
        self._mark_profile_as_custom()
        self._refresh_after_filter_change()


    def _clear_all_filters_global(self):
        """Limpa todos os filtros: busca geral + filtros de coluna"""
        self._safe_store_last_filter_state("clear_all_filters_global")
        self._invalidate_active_filter_request("clear_all_filters_global")
        self._set_filter_ui_idle()
        # Limpar filtro de busca geral
        try:
            self._debounce_timer.stop()
        except Exception:
            pass
        try:
            sector_timer = getattr(self, "_sector_debounce_timer", None)
            if sector_timer is not None:
                sector_timer.stop()
        except Exception:
            pass
        try:
            self.search_input.blockSignals(True)
            self.search_input.clear()
            self.search_input.setText('')
        finally:
            try:
                self.search_input.blockSignals(False)
            except Exception:
                pass
        self._pending_search_display = None
        self._df_last_search_filtered = pd.DataFrame()

        # Limpar todos os filtros de coluna
        if self._active_column_filters:
            self._active_column_filters.clear()
            for k in ("situacao", "setor_executor", "descricao_ssa"):
                self._active_column_filters[k] = ""

        # Limpar filtros auxiliares/avancados
        self._exclude_ste_sca = False
        self._advanced_filters = {}
        self._advanced_filters_active = False
        tab_contexts = getattr(self, "_tab_contexts", None)
        if isinstance(tab_contexts, list):
            for ctx in tab_contexts:
                if not isinstance(ctx, dict):
                    continue
                checkbox = ctx.get("exclude_ste_checkbox")
                if checkbox is None:
                    continue
                try:
                    checkbox.blockSignals(True)
                    checkbox.setChecked(False)
                except Exception:
                    pass
                finally:
                    try:
                        checkbox.blockSignals(False)
                    except Exception:
                        pass
        try:
            if hasattr(self, "_sync_advanced_filter_ui"):
                self._sync_advanced_filter_ui()
        except Exception:
            pass

        # Resetar para dataset completo
        self.df_exibido = self.df_completo.copy()
        self.paginator.set_dataframe(self.df_exibido)
        self.display_current_page(1)
        # Restaura linhas ocultas e limpa Filtro OU dedicado (exibição)
        try:
            self._hidden_column_filter_lines.clear()
        except Exception:
            self._hidden_column_filter_lines = set()
        self._dedicated_or_text = ''
        self._build_column_filters_panel()
        self._update_col_filter_indicator()

        # Atualizar interface
        self.status_label.setText(f"Status: {len(self.df_exibido)} SSAs carregadas. Pronto para filtrar.")
        if hasattr(self, 'clear_filter_button'):
            self.clear_filter_button.setEnabled(self._has_any_active_filters())

        # Atualizar resumo de filtros
        self._update_filters_summary()


    def _update_filters_summary(self):
        """Atualiza o resumo de filtros ativos na interface"""
        # Coleta filtros ativos
        active_filters = []
        tab_kind = getattr(self, "_current_tab_kind", None)
        show_basic = tab_kind != "filters"

        # Filtro de busca geral
        if show_basic and hasattr(self, 'search_input') and self.search_input.text().strip():
            active_filters.append(f"Busca: '{self.search_input.text().strip()}'")

        def _display_name(col: str) -> str:
            if col == 'setor_executor':
                return 'Executor'
            if col == 'setor_emissor':
                return 'Emissor'
            if col == 'descricao_ssa':
                return 'Descricao da SSA'
            if col == 'situacao':
                return 'Situacao'
            return self.internal_to_display.get(col, col.replace('_', ' ').title())

        # Filtro OU dedicado (exibição)
        or_text = str(getattr(self, '_dedicated_or_text', '') or '').strip()
        if show_basic and or_text:
            active_filters.append(f"Filtro OU: {self._format_column_filter_display_value(or_text)}")

        # Filtros de coluna (exibição)
        if show_basic and hasattr(self, '_active_column_filters') and self._active_column_filters:
            processed_groups = set()
            for group in getattr(self, '_column_or_groups', []):
                if not group.get('values'):
                    continue
                gid = id(group)
                processed_groups.add(gid)
                columns = group.get('columns', [])
                if set(columns) == {'setor_executor', 'setor_emissor'}:
                    label = 'Executor ou Emissor (OU)'
                else:
                    label = f"{' ou '.join(_display_name(c) for c in columns)} (OU)"
                values_txt = self._format_column_filter_display_value(', '.join(group.get('values', [])))
                if values_txt:
                    active_filters.append(f"{label}: {values_txt}")

            for col_name, filter_value in self._active_column_filters.items():
                if col_name in self._column_to_or_group:
                    continue
                normalized_value = self._format_column_filter_display_value(str(filter_value), column=col_name)
                if not normalized_value:
                    continue
                active_filters.append(f"{_display_name(col_name)}: {normalized_value}")

        adv = getattr(self, "_advanced_filters", None) or {}
        adv_active = bool(getattr(self, "_advanced_filters_active", False))
        def _add_adv(label, values, op: str | None = None):
            if not values:
                return
            if isinstance(values, list):
                txt = ", ".join(str(v) for v in values if str(v).strip())
            else:
                txt = str(values).strip()
            if not txt:
                return
            if op:
                active_filters.append(f"{label} {op} {txt}")
            else:
                active_filters.append(f"{label}: {txt}")

        def _fmt_week_range(start, end):
            if start is None and end is None:
                return None
            if start is None:
                return f"<= {end}"
            if end is None:
                return f">= {start}"
            return f"{start}-{end}"

        if adv_active:
            _add_adv("Executor", adv.get("setor_executor"))
            _add_adv("Executor", adv.get("setor_executor_exclude_values"), "!=")
            _add_adv("Emissor", adv.get("setor_emissor"))
            _add_adv("Emissor", adv.get("setor_emissor_exclude_values"), "!=")
            _add_adv("Divisao", adv.get("divisao"))
            _add_adv("Divisao", adv.get("divisao_exclude_values"), "!=")
            _add_adv("Situacao", adv.get("situacao"))
            _add_adv("Situacao", adv.get("situacao_exclude_values"), "!=")
            _add_adv("Solicitante", adv.get("solicitante"))
            _add_adv("Solicitante", adv.get("solicitante_exclude_values"), "!=")
            _add_adv("Resp Programacao", adv.get("responsavel_programacao"))
            _add_adv("Resp Programacao", adv.get("responsavel_programacao_exclude_values"), "!=")
            _add_adv("Resp Execucao", adv.get("responsavel_execucao"))
            _add_adv("Resp Execucao", adv.get("responsavel_execucao_exclude_values"), "!=")
            _add_adv("Resp Emissao", adv.get("responsavel_emissor"))
            _add_adv("Resp Emissao", adv.get("responsavel_emissor_exclude_values"), "!=")
            _add_adv("Prio Emissao", adv.get("prioridade_emissao_values"))
            _add_adv("Prio Emissao", adv.get("prioridade_emissao_exclude_values"), "!=")
            _add_adv("Prio Planejamento", adv.get("prioridade_planejamento_values"))
            _add_adv("Prio Planejamento", adv.get("prioridade_planejamento_exclude_values"), "!=")

            ano_emissao_vals = adv.get("ano_emissao_values")
            ano_emissao_exc = adv.get("ano_emissao_exclude_values")
            if ano_emissao_vals is None and adv.get("ano_emissao") is not None:
                ano_emissao_vals = [adv.get("ano_emissao")]
            if ano_emissao_exc is None and adv.get("ano_emissao_exclude") and adv.get("ano_emissao") is not None:
                ano_emissao_exc = [adv.get("ano_emissao")]
            _add_adv("Ano Emissao", ano_emissao_vals)
            _add_adv("Ano Emissao", ano_emissao_exc, "!=")

            ano_execucao_vals = adv.get("ano_execucao_values")
            ano_execucao_exc = adv.get("ano_execucao_exclude_values")
            if ano_execucao_vals is None and adv.get("ano_execucao") is not None:
                ano_execucao_vals = [adv.get("ano_execucao")]
            if ano_execucao_exc is None and adv.get("ano_execucao_exclude") and adv.get("ano_execucao") is not None:
                ano_execucao_exc = [adv.get("ano_execucao")]
            _add_adv("Ano Execucao", ano_execucao_vals)
            _add_adv("Ano Execucao", ano_execucao_exc, "!=")

            em_range = _fmt_week_range(adv.get("semana_emissao_inicio"), adv.get("semana_emissao_fim"))
            if em_range:
                label = "Semana Emissao"
                op = "!=" if adv.get("semana_emissao_exclude") else None
                _add_adv(label, [em_range], op)
            ex_range = _fmt_week_range(adv.get("semana_execucao_inicio"), adv.get("semana_execucao_fim"))
            if ex_range:
                label = "Semana Execucao"
                op = "!=" if adv.get("semana_execucao_exclude") else None
                _add_adv(label, [ex_range], op)

            if adv.get("derivada_has"):
                active_filters.append("Possui derivada")
            if adv.get("derivada_all_ste"):
                active_filters.append("Derivadas em STE")
            if adv.get("derivada_is"):
                active_filters.append("SSA derivada")
            if adv.get("macro_filter"):
                macro_val = adv.get("macro_filter")
                macro_label = "SSAs para baixar" if macro_val == "ssas_para_baixar" else str(macro_val)
                active_filters.append(f"Macro: {macro_label}")

        if show_basic and getattr(self, '_exclude_ste_sca', False):
            active_filters.append("situacao!=STE/SCA")

        # Monta texto do resumo
        if active_filters:
            summary_text = "Filtros ativos: " + "; ".join(active_filters)
        else:
            summary_text = "Nenhum filtro ativo"

        # Atualiza label de resumo principal
        if hasattr(self, 'filters_summary_label'):
            self.filters_summary_label.setText(summary_text)


    def _format_column_filter_display_value(self, raw: str, *, column: str | None = None) -> str:
        """Normaliza um valor de filtro de coluna para exibicao consistente.

        SIMPLIFIED: No logical operators - just comma-separated terms.
        - Splits by commas only
        - Removes extra spaces
        - Maintains markers (^, $, =, ~, !) in tokens
        - Applies optional column aliases for display
        - Returns comma-separated terms (OR logic implicit)
        """
        if not raw:
            return ""
        try:
            text = str(raw).strip()
            # Remove extra spaces
            text = re.sub(r'\s+', ' ', text).strip()
            # Split by commas only
            tokens = [t.strip() for t in text.split(',') if t.strip()]
            # Apply optional display aliases per column
            if tokens:
                alias_map = self._get_filter_alias_map()
                mapped: list[str] = []
                col_map = None
                if column and isinstance(alias_map, dict):
                    col_map = alias_map.get(column) or alias_map.get(column.lower())
                global_map = alias_map.get('_global') if isinstance(alias_map, dict) else None
                for tok in tokens:
                    key = tok.casefold()
                    new_tok = None
                    if isinstance(col_map, dict):
                        new_tok = col_map.get(key) or col_map.get(tok)
                    if new_tok is None and isinstance(global_map, dict):
                        new_tok = global_map.get(key) or global_map.get(tok)
                    mapped.append(new_tok if isinstance(new_tok, str) and new_tok.strip() else tok)
                tokens = mapped
            # Display as comma-separated (OR logic)
            return ', '.join(tokens)
        except Exception:
            # Fallback: display raw, trimmed
            return str(raw).strip()


    def _get_filter_alias_map(self) -> dict:
        """Carrega mapeamento opcional de aliases para exibição de filtros de coluna.
        Estrutura esperada (config/filter_aliases.json):
        {
          "_global": { "ste": "STE" },
          "setor_executor": { "svp": "S/P" }
        }
        Chaves de lookup aceitam minúsculas (casefold). Retorna {} se ausente/erro.
        """
        if hasattr(self, '_filter_alias_map') and isinstance(self._filter_alias_map, dict):
            return self._filter_alias_map
        try:
            # Resolve config path relative to repository root, avoiding reliance on project_root
            # Walk up three levels from this file: gui/mixins/ -> gui/ -> repo root
            repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            cfg_path = os.path.join(repo_root, 'config', 'filter_aliases.json')
            if os.path.exists(cfg_path):
                with open(cfg_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                # Normaliza apenas para dict
                if isinstance(data, dict):
                    self._filter_alias_map = data
                    return self._filter_alias_map
        except Exception:
            pass
        self._filter_alias_map = {}
        return self._filter_alias_map


    def _update_col_filter_indicator(self):
        if not hasattr(self, 'col_filter_indicator'):
            return
        try:
            if not self.col_filter_indicator.isVisible():
                return
        except Exception:
            pass
        # Ativo quando existe ao menos um termo nao vazio em filtros por coluna
        active = any((str(v).strip() != "") for _, v in (self._active_column_filters or {}).items())
        txt = "Filtros por coluna: Ativo" if active else "Filtros por coluna: Nao ativo"
        try:
            self.col_filter_indicator.setText(txt)
        except Exception:
            pass


    def show_filter_help(self):
        try:
            dlg = FilterHelpDialog(self)
            dlg.exec()
        except Exception:
            # Em ambientes sem GUI completa, ignore
            pass


    def _collect_profile_columns(self, profiles: dict) -> list:
        cols = []
        for profile_data in profiles.values():
            if isinstance(profile_data, dict):
                all_section = profile_data.get('all') if isinstance(profile_data.get('all'), dict) else None
                if all_section:
                    for col_name in all_section.keys():
                        if col_name not in cols:
                            cols.append(col_name)
                any_section = profile_data.get('any') if isinstance(profile_data.get('any'), list) else None
                if any_section:
                    for group in any_section:
                        columns = group.get('columns') if isinstance(group, dict) else None
                        if isinstance(columns, list):
                            for col_name in columns:
                                if col_name not in cols:
                                    cols.append(col_name)
                # Suporte legado: simples dict coluna->valor
                if not (all_section or any_section):
                    for col_name in profile_data.keys():
                        if col_name not in cols:
                            cols.append(col_name)
            elif isinstance(profile_data, list):
                for col_name in profile_data:
                    if isinstance(col_name, str) and col_name not in cols:
                        cols.append(col_name)
        return cols


    def _initialize_profile_filter_placeholders(self):
        """Garante que colunas monitoradas tenham entradas nas estruturas de filtro."""
        if not isinstance(self._active_column_filters, OrderedDict):
            self._active_column_filters = OrderedDict(self._active_column_filters or {})
        for col in self._profile_columns:
            if col not in self._active_column_filters:
                self._active_column_filters[col] = ""
        # Garante linhas iniciais úteis mesmo sem perfil aplicado
        for default_col in ("setor_executor", "setor_emissor", "descricao_ssa"):
            if default_col not in self._active_column_filters:
                self._active_column_filters[default_col] = ""


    def _reset_or_groups(self):
        self._column_or_groups = []
        self._column_to_or_group = {}


    def _register_or_group(self, columns: list, values: list):
        normalized_columns = [c for c in (columns or []) if isinstance(c, str) and c]
        normalized_values = [str(v).strip() for v in (values or []) if str(v).strip()]
        if not normalized_columns:
            return None
        group = {
            'columns': normalized_columns,
            'values': normalized_values,
        }
        self._column_or_groups.append(group)
        for col in normalized_columns:
            self._column_to_or_group[col] = group
        return group


    def _sync_or_group_values(self, column: str, text: str):
        """Syncs filter values across columns in same OR group.

        SIMPLIFIED: No logical operators - just comma-separated terms.
        """
        group = self._column_to_or_group.get(column)
        if not group:
            return
        normalized = str(text or '').strip()
        # Remove extra spaces, semicolons
        normalized = normalized.replace(';', ',')
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        # Split by commas only
        tokens = [token.strip() for token in normalized.split(',') if token.strip()]
        group['values'] = tokens
        # Store internally as comma-separated list (OR logic)
        common_text = ', '.join(tokens)
        for col in group['columns']:
            self._active_column_filters[col] = common_text


    def _apply_column_filters(self, df: pd.DataFrame) -> pd.DataFrame:
        """Aplica todos os filtros por coluna com as mesmas regras de busca (prefixo ^, sufixo $, =exato, ~regex, !neg)."""
        if df is None or df.empty or not self._active_column_filters:
            return df
        working_df = df
        mask = pd.Series(True, index=working_df.index)
        for col, raw in self._active_column_filters.items():
            if col not in working_df.columns:
                continue
            raw_str = str(raw).strip()
            if not raw_str:
                continue
            col_series = working_df[col].astype(str)
            mask &= self._build_column_mask(col_series, raw_str)

        if mask.all():
            return working_df
        return working_df[mask]


    def _refresh_after_filter_change(self):
        """Reaplica filtros de coluna, atualiza tabela e indicadores."""
        base = self._df_last_search_filtered if not self._df_last_search_filtered.empty else self.df_completo
        filtered = base
        if hasattr(self, "_apply_advanced_filters"):
            try:
                filtered = self._apply_advanced_filters(filtered)
            except Exception:
                pass
        filtered = self._apply_column_filters(filtered)
        if getattr(self, '_exclude_ste_sca', False) and not filtered.empty and 'situacao' in filtered.columns:
            try:
                mask = ~filtered['situacao'].astype(str).str.upper().isin({'STE', 'SCA'})
                filtered = filtered[mask]
            except Exception:
                pass
        # CORRECAO 2026-01-08: Ordenar por numero_ssa decrescente apos filtro
        if not filtered.empty and 'numero_ssa' in filtered.columns:
            try:
                filtered = filtered.sort_values('numero_ssa', ascending=False)
            except Exception:
                pass
        self.df_exibido = filtered
        self.paginator.set_dataframe(self.df_exibido)
        try:
            current = max(1, min(self.paginator.current_page, self.paginator.total_pages))
            self.display_current_page(current)
        except Exception:
            (lambda cp=max(1, min(getattr(self.paginator, 'current_page', 1), getattr(self.paginator, 'total_pages', 1))): self.display_current_page(cp))()
        self._update_col_filter_indicator()
        try:
            self._update_filters_summary()
        except Exception:
            pass


    def _snapshot_filter_state(self) -> dict:
        try:
            search_text = self.search_input.text()
        except Exception:
            search_text = ""
        try:
            active_filters = OrderedDict(self._active_column_filters or {})
        except Exception:
            active_filters = OrderedDict()
        groups_snapshot = []
        for group in getattr(self, '_column_or_groups', []) or []:
            groups_snapshot.append({
                'columns': tuple(group.get('columns', ())),
                'values': list(group.get('values', ())),
            })
        try:
            df_last = self._df_last_search_filtered.copy()
        except Exception:
            df_last = pd.DataFrame()
        return {
            "search_text": search_text,
            "pending_search_display": getattr(self, "_pending_search_display", None),
            "active_column_filters": active_filters,
            "column_or_groups": groups_snapshot,
            "exclude_ste_sca": bool(getattr(self, "_exclude_ste_sca", False)),
            "advanced_filters": copy.deepcopy(getattr(self, "_advanced_filters", None) or {}),
            "advanced_filters_active": bool(getattr(self, "_advanced_filters_active", False)),
            "df_last_search_filtered": df_last,
            "current_filter_profile": getattr(self, "current_filter_profile", None),
            "profile_base_filters": copy.deepcopy(getattr(self, "_profile_base_filters", {}) or {}),
            "hidden_column_filter_lines": set(getattr(self, "_hidden_column_filter_lines", set())),
            "dedicated_or_text": str(getattr(self, "_dedicated_or_text", "")),
        }


    def _store_last_filter_state(self) -> None:
        if getattr(self, "_restoring_filter_state", False):
            return
        try:
            self._last_filter_state = self._snapshot_filter_state()
        except Exception:
            self._last_filter_state = None
        self._update_undo_button_state()


    def _restore_last_filter_state(self) -> None:
        state = getattr(self, "_last_filter_state", None)
        if not state:
            return
        self._invalidate_active_filter_request("restore_last_filter_state")
        self._set_filter_ui_idle()
        self._restoring_filter_state = True
        try:
            self._last_filter_state = None
            try:
                self.search_input.blockSignals(True)
                self.search_input.setText(state.get("search_text", "") or "")
            finally:
                try:
                    self.search_input.blockSignals(False)
                except Exception:
                    pass
            self._pending_search_display = state.get("pending_search_display")
            self._active_column_filters = OrderedDict(state.get("active_column_filters") or {})
            self._reset_or_groups()
            for group in state.get("column_or_groups") or []:
                self._register_or_group(list(group.get("columns") or []), list(group.get("values") or []))
            self._exclude_ste_sca = bool(state.get("exclude_ste_sca"))
            tab_contexts = getattr(self, "_tab_contexts", None)
            if isinstance(tab_contexts, list):
                for ctx in tab_contexts:
                    checkbox = ctx.get("exclude_ste_checkbox") if isinstance(ctx, dict) else None
                    if checkbox is None:
                        continue
                    try:
                        checkbox.blockSignals(True)
                        checkbox.setChecked(self._exclude_ste_sca)
                    except Exception:
                        pass
                    finally:
                        try:
                            checkbox.blockSignals(False)
                        except Exception:
                            pass
            else:
                try:
                    self.exclude_ste_checkbox.blockSignals(True)
                    self.exclude_ste_checkbox.setChecked(self._exclude_ste_sca)
                except Exception:
                    pass
                finally:
                    try:
                        self.exclude_ste_checkbox.blockSignals(False)
                    except Exception:
                        pass
            self._advanced_filters = state.get("advanced_filters") or {}
            self._advanced_filters_active = bool(state.get("advanced_filters_active"))
            df_last = state.get("df_last_search_filtered")
            if isinstance(df_last, pd.DataFrame):
                self._df_last_search_filtered = df_last
            else:
                self._df_last_search_filtered = pd.DataFrame()
            self.current_filter_profile = state.get("current_filter_profile")
            self._profile_base_filters = state.get("profile_base_filters") or {}
            self._hidden_column_filter_lines = set(state.get("hidden_column_filter_lines") or set())
            self._dedicated_or_text = str(state.get("dedicated_or_text") or "")
            try:
                self._sync_advanced_filter_ui()
            except Exception:
                pass
            self._build_column_filters_panel()
            self._refresh_after_filter_change()
            try:
                self.update_filter_tags()
            except Exception:
                pass
            try:
                self._update_filters_summary()
            except Exception:
                pass
            try:
                self.clear_filter_button.setEnabled(self._has_any_active_filters())
            except Exception:
                pass
            selector = getattr(self, 'profile_selector', None)
            if selector is not None:
                idx = selector.findData(self.current_filter_profile) if self.current_filter_profile else selector.findData(None)
                if idx >= 0:
                    self._profile_lock = True
                    try:
                        selector.setCurrentIndex(idx)
                    finally:
                        self._profile_lock = False
        finally:
            self._restoring_filter_state = False
            self._update_undo_button_state()


    def _update_undo_button_state(self) -> None:
        btn = getattr(self, "undo_filter_btn", None)
        if btn is None:
            return
        try:
            btn.setEnabled(bool(getattr(self, "_last_filter_state", None)))
        except Exception:
            pass
        except Exception:
            pass


    def _apply_search_display(self):
        display_text = getattr(self, '_pending_search_display', None)
        if display_text is None:
            return

        # Don't modify text while user is typing
        if self.search_input.hasFocus():
            return

        try:
            self.search_input.blockSignals(True)
            if display_text:
                self.search_input.setText(display_text)
            else:
                self.search_input.clear()
        finally:
            self.search_input.blockSignals(False)
        self._pending_search_display = None


    def _mark_profile_as_custom(self):
        """Marca o perfil atual como personalizado quando filtros divergem."""
        if getattr(self, '_profile_lock', False):
            return
        base = self._profile_base_filters or {}
        base_columns = {k: str(v).strip() for k, v in (base.get('columns') or {}).items()}
        base_groups = base.get('or_groups') or []
        base_exclude = bool(base.get('exclude_ste_sca', False))

        if self.current_filter_profile and self.current_filter_profile in self.filter_profiles:
            mismatch = False
            # Verifica colunas mapeadas
            current_columns = {}
            referenced_columns = set(base_columns.keys()) | set(self._active_column_filters.keys())
            for col in referenced_columns:
                if col in self._column_to_or_group:
                    group = self._column_to_or_group.get(col)
                    current_columns[col] = ', '.join(group.get('values', [])) if group else ''
                else:
                    current_columns[col] = str(self._active_column_filters.get(col, '')).strip()

            for col, expected in base_columns.items():
                if current_columns.get(col, '').strip() != expected:
                    mismatch = True
                    break

            if not mismatch:
                # Valores adicionais além do perfil base
                for col, current in current_columns.items():
                    if col not in base_columns and current.strip():
                        mismatch = True
                        break

            if not mismatch:
                # Compara grupos OR
                def _group_repr(group):
                    cols = tuple(group.get('columns', ()))
                    vals = tuple(group.get('values', ()))
                    return (cols, vals)

                current_groups = sorted(_group_repr(g) for g in getattr(self, '_column_or_groups', []))
                expected_groups = sorted(_group_repr({'columns': g.get('columns', ()), 'values': g.get('values', ())}) for g in base_groups)
                if current_groups != expected_groups:
                    mismatch = True

            if not mismatch and base_exclude != bool(self._exclude_ste_sca):
                mismatch = True

            if not mismatch:
                return
        self.current_filter_profile = None
        self._profile_base_filters = {}
        selector = getattr(self, 'profile_selector', None)
        if selector is not None:
            idx = selector.findData(None)
            if idx >= 0 and selector.currentIndex() != idx:
                self._profile_lock = True
                try:
                    selector.setCurrentIndex(idx)
                finally:
                    self._profile_lock = False


    def _apply_filter_profile(self, profile_name, update_selector=True, refresh=True):
        """Aplica filtros pré-configurados de setor."""
        if not profile_name or profile_name not in self.filter_profiles:
            # Fallback ad-hoc: permite strings como "IEE3 + MEL3 + MEL4" para grupo Executor/Emissor
            try:
                import re as _re
                raw = str(profile_name)
                tokens = [_t.strip() for _t in _re.split(r"[+,]", raw) if _t and _t.strip()]
                if tokens:
                    self._reset_or_groups()
                    self._register_or_group(['setor_executor', 'setor_emissor'], tokens)
                    # Garante colunas monitoradas
                    for _col in ('setor_executor', 'setor_emissor'):
                        if _col not in self._profile_columns:
                            self._profile_columns.append(_col)
                    # Define filtros subjacentes separados por vírgulas (lógica)
                    new_filters = OrderedDict(self._active_column_filters or {})
                    for _col in ('setor_executor', 'setor_emissor'):
                        new_filters[_col] = ', '.join(tokens)
                    self._active_column_filters = new_filters
                    # Base do perfil para marcação de personalizado
                    self._profile_base_filters = {
                        'columns': {c: new_filters.get(c, '') for c in ('setor_executor', 'setor_emissor')},
                        'or_groups': [{'columns': ('setor_executor', 'setor_emissor'), 'values': tuple(tokens)}],
                        'exclude_ste_sca': bool(self._exclude_ste_sca),
                    }
                    self._build_column_filters_panel()
                    if refresh:
                        self._refresh_after_filter_change()
                return
            except Exception:
                return
        profile_def = self.filter_profiles.get(profile_name) or {}
        def normalize_values(value) -> list:
            if isinstance(value, list):
                return [str(v).strip() for v in value if str(v).strip()]
            if isinstance(value, str):
                return [value.strip()] if value.strip() else []
            if value is None:
                return []
            text = str(value).strip()
            return [text] if text else []

        normalized_columns = OrderedDict()
        normalized_groups = []
        self._reset_or_groups()

        if isinstance(profile_def, dict):
            all_section = profile_def.get('all') if isinstance(profile_def.get('all'), dict) else None
            if all_section:
                for col, value in all_section.items():
                    values_list = normalize_values(value)
                    normalized_columns[col] = ', '.join(values_list) if values_list else ''
                    if col not in self._profile_columns:
                        self._profile_columns.append(col)
            any_section = profile_def.get('any') if isinstance(profile_def.get('any'), list) else None
            if any_section:
                for group in any_section:
                    if not isinstance(group, dict):
                        continue
                    columns = group.get('columns') if isinstance(group.get('columns'), list) else None
                    values_list = normalize_values(group.get('values'))
                    registered = self._register_or_group(columns, values_list)
                    if registered:
                        display_values = ', '.join(registered['values'])
                        for col in registered['columns']:
                            normalized_columns[col] = display_values
                        for col in registered['columns']:
                            if col not in self._profile_columns:
                                self._profile_columns.append(col)
                        normalized_groups.append({
                            'columns': tuple(registered['columns']),
                            'values': tuple(registered['values'])
                        })
            if not all_section and 'any' not in profile_def:
                for col, value in profile_def.items():
                    values_list = normalize_values(value)
                    normalized_columns[col] = ', '.join(values_list) if values_list else ''
                    if col not in self._profile_columns:
                        self._profile_columns.append(col)
        else:
            values_list = normalize_values(profile_def)
            if values_list:
                normalized_columns['situacao'] = ', '.join(values_list)
                if 'situacao' not in self._profile_columns:
                    self._profile_columns.append('situacao')

        self._profile_lock = True
        try:
            self.current_filter_profile = profile_name
            new_filters = OrderedDict()
            for col in self._profile_columns:
                new_filters[col] = ""
            for col, text in normalized_columns.items():
                if col not in new_filters:
                    new_filters[col] = text
                else:
                    new_filters[col] = text
            for group in self._column_or_groups:
                group_text = ', '.join(group.get('values', []))
                for col in group.get('columns', []):
                    if col not in new_filters:
                        new_filters[col] = group_text
                    else:
                        new_filters[col] = group_text
            self._active_column_filters = new_filters
            # Garante consistência das strings dos grupos OR (subjacente em vírgulas)
            for group in self._column_or_groups:
                display_group = ', '.join(group.get('values', []))
                for col in group.get('columns', []):
                    self._active_column_filters[col] = display_group
            self._profile_base_filters = {
                'columns': {col: new_filters.get(col, '').strip() for col in new_filters},
                'or_groups': normalized_groups,
                'exclude_ste_sca': bool(self._exclude_ste_sca)
            }
            if update_selector and getattr(self, 'profile_selector', None) is not None:
                idx = self.profile_selector.findData(profile_name)
                if idx >= 0 and self.profile_selector.currentIndex() != idx:
                    self.profile_selector.setCurrentIndex(idx)
        finally:
            self._profile_lock = False
        self._build_column_filters_panel()
        if refresh:
            self._refresh_after_filter_change()


    def _apply_initial_filter_profile(self):
        """Seleciona e aplica o perfil inicial definido em configuração."""
        selector = getattr(self, 'profile_selector', None)
        if selector is None:
            return
        initial_profile = self.default_filter_profile if self.default_filter_profile in self.filter_profiles else None
        if not initial_profile and self.filter_profiles:
            initial_profile = next(iter(self.filter_profiles.keys()))
        if initial_profile:
            self._apply_filter_profile(initial_profile, update_selector=True, refresh=False)
        else:
            idx = selector.findData(None)
            if idx >= 0:
                self._profile_lock = True
                try:
                    selector.setCurrentIndex(idx)
                finally:
                    self._profile_lock = False
        self._build_column_filters_panel()
        self._refresh_after_filter_change()


    def on_profile_changed(self, index):
        """Callback ao trocar o perfil de filtros por setor."""
        if getattr(self, '_profile_lock', False):
            return
        selector = getattr(self, 'profile_selector', None)
        if selector is None:
            return
        self._safe_store_last_filter_state("on_profile_changed")
        profile_name = selector.itemData(index)
        if profile_name:
            self._apply_filter_profile(profile_name, update_selector=False)
        else:
            self.current_filter_profile = None
            self._profile_base_filters = {}


    def _build_column_mask(self, series: pd.Series, raw: str) -> pd.Series:
        # Divide SOMENTE por vírgulas; não há conectivos especiais aqui.
        normalized = str(raw)
        tokens = [t.strip() for t in normalized.split(',') if t.strip()]
        if not tokens:
            return pd.Series([True]*len(series), index=series.index)

        # Determina modo padrao a partir das preferencias
        if not hasattr(self, '_cached_default_mode'):
            from gui import gui_ssa
            gui_settings = gui_ssa.GUI_MAIN_PREFERENCES.get("gui_settings", {})
            self._cached_default_mode = gui_settings.get("default_filter_mode", "contains")
        default_mode = self._cached_default_mode

        def match_token(s: pd.Series, token: str) -> pd.Series:
            neg = token.startswith('!')
            t = token[1:] if neg else token
            # VAZIOS/NULL: aceita NULL ou =NULL (case-insensitive)
            if t.upper() in ('NULL', '=NULL'):
                # Considera nulos, strings vazias e '-'
                res = s.isna() | (s.str.strip().eq('', na=False)) | (s == '-')
                return ~res if neg else res
            # Regex explácito
            if t.startswith('~') and len(t) > 1:
                try:
                    import re
                    pat = re.compile(t[1:], re.IGNORECASE)
                    res = s.str.contains(pat, na=False)
                except Exception:
                    res = s.str.contains(t[1:], case=False, na=False)
            elif t.startswith('='):
                res = s.str.casefold().eq(t[1:].casefold())
            elif t.startswith('^'):
                res = s.str.casefold().str.startswith(t[1:].casefold())
            elif t.endswith('$'):
                res = s.str.casefold().str.endswith(t[:-1].casefold())
            else:
                if default_mode == 'prefix':
                    res = s.str.casefold().str.startswith(t.casefold())
                elif default_mode == 'suffix':
                    res = s.str.casefold().str.endswith(t.casefold())
                elif default_mode == 'exact':
                    res = s.str.casefold().eq(t.casefold())
                elif default_mode == 'regex':
                    try:
                        import re
                        pat = re.compile(t, re.IGNORECASE)
                        res = s.str.contains(pat, na=False)
                    except Exception:
                        res = s.str.contains(t, case=False, na=False)
                else:  # contains
                    res = s.str.contains(t, case=False, na=False)
            return ~res if neg else res

    # OR entre inclusões no MESMO CAMPO; exclusões (com !) removem
        includes = [tok for tok in tokens if not tok.startswith('!')]
        excludes = [tok for tok in tokens if tok.startswith('!')]

        if includes:
            m = match_token(series, includes[0])
            for tok in includes[1:]:
                m = m | match_token(series, tok)
        else:
            m = pd.Series([True]*len(series), index=series.index)
        for tok in excludes:
            m = m & match_token(series, tok)
        return m

    # --- Helpers: Busca Geral com suporte a OR/AND amigável ---


    def _split_search_expression(self, text: str) -> list[str]:
        # Simplified: General search uses ONLY AND logic (commas separate terms)
        # No OR/OU splitting - returns single chunk containing all terms
        if not text:
            return []
        # Return text as single chunk - will be split by commas in _normalize_chunk_for_parse
        return [text.strip()] if text.strip() else []


    def _normalize_chunk_for_parse(self, chunk: str) -> list[str]:
        """Delegate to helper function."""
        return normalize_chunk_for_parse(chunk)


    def _format_search_display(self, chunks: list[list[str]]) -> str:
        """Delegate to helper function."""
        return format_search_display(chunks)


    def filter_data(self):  # chama o fluxo novo de filtragem
        try:
            self.initiate_filtering()
        except Exception:
            pass


    def load_persistent_filters(self):
        """Carrega filtros persistentes salvos (inicia vazio)."""
        self.persistent_filters = []
        self.update_filter_tags()


    def save_current_filter(self):
        """Salva o filtro atual como persistente."""
        current_text = self.search_input.text().strip()
        if not current_text:
            QMessageBox.information(self, "Aviso", "Digite um filtro na caixa de pesquisa antes de salvar.")
            return

        # Cria um nome baseado no filtro (limitado para exibicao)
        filter_name = current_text[:20] + "..." if len(current_text) > 20 else current_text

        # Verifica se ja existe
        for f in self.persistent_filters:
            if f["terms"] == current_text:
                QMessageBox.information(self, "Aviso", "Este filtro ja esta salvo.")
                return

        # Adiciona novo filtro
        new_filter = {"name": filter_name, "terms": current_text}
        self.persistent_filters.append(new_filter)
        self.persistent_filters.sort(key=lambda f: f["name"].casefold())
        self.update_filter_tags()

        QMessageBox.information(self, "Sucesso", f"Filtro '{filter_name}' salvo com sucesso!")


    def update_filter_tags(self):
        """Atualiza as tags visuais dos filtros persistentes."""
        # Remove tags existentes
        for i in reversed(range(self.filter_tags_layout.count())):
            child = self.filter_tags_layout.takeAt(i)
            if child.widget():
                child.widget().deleteLater()

        roles = get_theme_roles(getattr(self, '_current_theme', 'dark'))
        fg = roles.get('summary_text_color', self.palette().windowText().color().name())
        border = roles.get('tag_border')
        bg_normal = roles.get('tag_normal_bg')
        bg_hover = roles.get('tag_hover')
        bg_pressed = roles.get('tag_pressed')

        tag_css = f"""
            QPushButton {{
                color: {fg};
                background-color: {bg_normal};
                border: 1px solid {border};
                border-radius: 3px;
                padding: 2px 8px;
                font-size: 10px;
            }}
            QPushButton:hover {{
                background-color: {bg_hover};
            }}
            QPushButton:pressed {{
                background-color: {bg_pressed};
            }}
        """

        # Adiciona novas tags
        for filter_data in sorted(self.persistent_filters, key=lambda f: f["name"].casefold()):
            tag_button = QPushButton(filter_data["name"])
            tag_button.setMaximumHeight(25)
            tag_button.setStyleSheet(tag_css)
            tag_button.setToolTip(f"Clique para aplicar: {filter_data['terms']}")
            tag_button.clicked.connect(lambda checked, terms=filter_data["terms"]: self.apply_persistent_filter(terms))

            # Botção X para remover
            remove_button = QPushButton("X")
            remove_button.setMaximumSize(20, 20)
            remove_button.setStyleSheet(tag_css)
            remove_button.setToolTip("Remover filtro")
            remove_button.clicked.connect(lambda checked, filter_data=filter_data: self.remove_persistent_filter(filter_data))

            # Layout horizontal para tag + botção remover
            tag_layout = QHBoxLayout()
            tag_layout.setContentsMargins(0, 0, 0, 0)
            tag_layout.setSpacing(2)
            tag_layout.addWidget(tag_button)
            tag_layout.addWidget(remove_button)

            tag_widget = QWidget()
            tag_widget.setLayout(tag_layout)
            self.filter_tags_layout.addWidget(tag_widget)


    def apply_persistent_filter(self, terms):
        """Aplica um filtro persistente."""
        self.search_input.setText(terms)
        self.initiate_filtering()


