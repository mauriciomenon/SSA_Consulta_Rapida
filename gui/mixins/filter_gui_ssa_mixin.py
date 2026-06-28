# gui/mixins/filter_gui_ssa_mixin.py
# Mixin containing all filter-related methods for SSAMainWindow

"""
FilterGUISSAMixin: Mixin para metodos de filtragem.

Extraido de gui_ssa.py para reduzir tamanho do arquivo.
Padrao de nomenclatura: funcao_pai_mixin.py
"""

# Imports necessarios
import os
import re
import weakref
from collections import OrderedDict
from contextlib import contextmanager
from time import perf_counter
from typing import TYPE_CHECKING, Any, Optional, cast

import pandas as pd
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (
    QLineEdit,
    QMessageBox,
    QWidget,
)

try:
    from PyQt6.QtCore import Qt as _Qt

    _FILTER_QT_QUEUED = _Qt.ConnectionType.QueuedConnection
except Exception:
    _FILTER_QT_QUEUED = None
try:
    from PyQt6 import sip
except Exception:
    sip = cast(Any, None)

# Imports condicionais (podem nao estar disponiveis em modo headless)
try:
    from gui.workers import FilterWorker
except ImportError:
    FilterWorker = cast(Any, None)

try:
    from gui.widgets import FilterHelpDialog
except ImportError:
    FilterHelpDialog = cast(Any, None)

# Imports do core
from core.app_logic import FILTER_SEARCH_CACHE_ATTR, FILTER_SEARCH_MARKER_ATTR
from core.search_filter_constants import FILTER_SEARCH_SIGNATURE_CACHE_ATTR
from core.app_logic import filter_dataframe, parse_search_terms
from core.dataframe_fingerprint import build_dataframe_filter_hash
from core.search_filter import apply_general_search_terms
from core.config_manager import DEFAULT_DISPLAY_MAPPINGS

# Imports de gui helpers
from gui.helpers.formatting_helpers import (
    format_search_display,
    normalize_chunk_for_parse,
)
from gui.ssa import gui_details as ssa_gui_details
from gui.ssa.column_filter_runtime import (
    ColumnFilterRuntimeState,
    apply_column_filters_with_state,
    get_column_filter_date_display_columns,
    get_date_display_series,
    is_column_filter_date_display_column,
    should_match_date_filter,
)
from gui.ssa.column_filter_engine import ColumnFilterCaches
from gui.ssa.column_filter_engine import apply_column_filters as apply_column_filters
from gui.ssa.column_filter_panel import (
    build_column_filters_panel,
    open_add_column_filter_menu,
)
from gui.ssa.filter_cache_context import (
    build_filter_cache_context_from_parts,
    build_filter_cache_parts,
)
from gui.ssa.filter_domain_rules import (
    ADVANCED_FILTER_VISUAL_COLUMN_MAP as _ADVANCED_FILTER_VISUAL_COLUMN_MAP,
)
from gui.ssa.filter_domain_rules import (
    EXCLUDED_TERMINAL_SUMMARY as _EXCLUDED_TERMINAL_SUMMARY,
)
from gui.ssa.filter_aliases import load_filter_alias_map_once
from gui.ssa.filter_mask_logic import build_column_mask
from gui.ssa.filter_profile_logic import (
    NormalizedFilterProfile,
    filter_profile_is_custom,
    normalize_inline_executor_emissor_profile,
    normalize_named_filter_profile,
)
from gui.ssa.filter_refresh_pipeline import apply_filter_refresh_pipeline
from gui.ssa.filter_worker_lifecycle import (
    MAX_GLOBAL_RETIRED_FILTER_WORKERS,
    DeferredFilterWorkerRegistry,
    FilterWorkerLifecycle,
)
from gui.ssa.filter_ui_state import FilterUiStatePresenter
from gui.ssa.general_search_columns import build_gui_general_search_columns
from gui.ssa.persistent_filter_ui import PersistentFilterUiController
from gui.ssa.persistent_filters import get_gui_saved_filters_path
from gui.ssa.filter_status_manager import FilterStatusManager, FilterStatusPayload
from gui.ssa.filter_summary_advanced import build_advanced_summary_entries
from gui.ssa.filter_summary_entries import (
    FilterSummaryContext,
    SummaryAction,
    SummaryEntry,
    build_filters_summary_base_entries,
    build_filters_summary_raw_signature,
    compact_column_filter_display_name,
    filters_summary_display_name,
    format_column_filter_display_value,
    merge_summary_actions as _merge_summary_actions,
)
from gui.ssa.filter_summary_presenter import (
    FilterSummaryPresenter,
    FilterSummaryWidgets,
)
from gui.ssa.filter_summary_removal import (
    SummaryRemovalPlan,
    build_summary_removal_plan,
)
from gui.ssa.gui_filters_advanced_logic import AdvancedFilterMaskError
from gui.ssa import filter_search_undo_controller as search_undo_controller
from gui.ssa.filter_state_utils import copy_filter_mapping as _copy_filter_mapping
from utils.robust_logging import get_robust_logger

# Imports de utils
from utils.themes import get_theme_roles

# Module logger
logger = get_robust_logger().get_logger(__name__, "gui")

_WHITESPACE_RE = re.compile(r"\s+")
_FILTER_VALUE_SEPARATOR_RE = re.compile(r"[;,]")
__all__ = [
    "apply_column_filters",
    "build_column_mask",
    "FilterGUISSAMixin",
    "MAX_GLOBAL_RETIRED_FILTER_WORKERS",
    "DeferredFilterWorkerRegistry",
]


_CLEAR_FILTER_HARD_RESET_CLICK_TARGET = 3
_CLEAR_FILTER_HARD_RESET_WINDOW_SEC = 3.0


class FilterRefreshTimer:
    def __init__(self) -> None:
        self.started = perf_counter()
        self.timings = {
            "advanced": 0.0,
            "column": 0.0,
            "exclude": 0.0,
            "sort": 0.0,
            "paginate": 0.0,
            "render": 0.0,
            "status_indicator": 0.0,
            "summary": 0.0,
            "status": 0.0,
            "sync": 0.0,
        }

    def measure(self, name: str, callback):
        started = perf_counter()
        result = callback()
        self.timings[name] = (perf_counter() - started) * 1000.0
        return result


def _qt_parent(obj: Any) -> QWidget | None:
    return cast(QWidget | None, obj)


def _is_search_widget_valid(widget: Any) -> bool:
    if widget is None:
        return False
    if sip is None:
        return True
    try:
        return not sip.isdeleted(widget)
    except Exception:
        return False


def _has_named_alias(mapping: dict[str, str] | None, col: str) -> bool:
    if not isinstance(mapping, dict):
        return False
    value = str(mapping.get(col, "") or "").strip()
    return bool(value and value != col)


def _connect_filter_signal(signal, slot, *, label: str) -> bool:
    if signal is None:
        logger.debug("Signal ausente para %s; pulando conexao.", label)
        return False
    if not hasattr(signal, "connect"):
        logger.debug("Signal invalido para %s; sem metodo connect.", label)
        return False
    try:
        queued_connection = _FILTER_QT_QUEUED
        if queued_connection is not None and not isinstance(queued_connection, type):
            try:
                signal.connect(slot, queued_connection)
            except TypeError:
                try:
                    signal.connect(slot, type=queued_connection)
                except TypeError:
                    signal.connect(slot)
        else:
            signal.connect(slot)
        return True
    except Exception as exc:
        logger.debug("Falha ao conectar signal de filtro %s: %s", label, exc)
        return False


@contextmanager
def _blocked_widget_signals(widget: Any, *, log_context: str):
    if not _is_search_widget_valid(widget):
        logger.debug("Widget invalido ao bloquear sinais em %s.", log_context)
        yield
        return
    previous_state = False
    try:
        previous_state = bool(widget.blockSignals(True))
        yield
    finally:
        try:
            widget.blockSignals(previous_state)
        except Exception as exc:
            logger.debug("Falha ao reativar sinais em %s: %s", log_context, exc)


class FilterGUISSAMixin:
    """
    Mixin containing all filter-related methods.

    Methods extracted from SSAMainWindow to improve code organization.
    """

    if TYPE_CHECKING:

        def __getattr__(self, name: str) -> Any: ...

    def _safe_store_last_filter_state(
        self,
        reason: str = "",
        *,
        search_text_override: str | None = None,
        pending_search_display_override: str | None = None,
    ) -> None:
        search_undo_controller.safe_store_last_filter_state(
            self,
            reason,
            search_text_override=search_text_override,
            pending_search_display_override=pending_search_display_override,
        )

    def _iter_search_inputs(self):
        current = getattr(self, "search_input", None)
        if _is_search_widget_valid(current):
            yield current

    def _get_live_search_inputs_snapshot(self) -> list[Any]:
        return list(self._iter_search_inputs())

    def _sync_search_inputs(
        self,
        text: str,
        *,
        exclude_widget: Any | None = None,
        skip_if_any_focused: bool = False,
        log_context: str = "sync_search_inputs",
    ) -> bool:
        normalized_text = str(text or "")
        for timer_name in ("_debounce_timer", "_sector_debounce_timer"):
            try:
                debounce_timer = getattr(self, timer_name, None)
                if debounce_timer is not None:
                    debounce_timer.stop()
            except Exception as exc:
                logger.debug(
                    "Falha ao parar %s durante %s: %s",
                    timer_name,
                    log_context,
                    exc,
                )
        widgets = self._get_live_search_inputs_snapshot()
        all_synchronized = True
        for widget in widgets:
            if widget is exclude_widget:
                continue
            if skip_if_any_focused:
                try:
                    if widget.hasFocus():
                        all_synchronized = False
                        continue
                except RuntimeError as exc:
                    logger.debug(
                        "Widget de busca invalido durante verificacao de foco: %s", exc
                    )
                    continue
                except Exception as exc:
                    logger.debug(
                        "Falha ao verificar foco durante %s: %s", log_context, exc
                    )
                    continue
            try:
                if not _is_search_widget_valid(widget):
                    continue
                with _blocked_widget_signals(widget, log_context=log_context):
                    widget.setText(normalized_text)
            except RuntimeError as exc:
                logger.debug(
                    "Widget de busca invalido durante %s: %s", log_context, exc
                )
        return all_synchronized

    def _set_search_text_across_tabs(self, text: str) -> None:
        """Aplica texto no campo de busca vivo."""
        self._sync_search_inputs(text, log_context="set_search_text_across_tabs")

    def _has_any_active_filters(self) -> bool:
        has_search = False
        try:
            for widget in self._iter_search_inputs():
                text = widget.text().strip()
                if text:
                    has_search = True
                    break
        except Exception:
            has_search = False
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
        return bool(has_search or has_column_filters or has_exclude_ste or has_advanced)

    def _get_visual_filter_columns(self) -> set[str]:
        columns: set[str] = set()
        try:
            for col_name, raw_value in (
                getattr(self, "_active_column_filters", {}) or {}
            ).items():
                if col_name == "#":
                    continue
                if str(raw_value).strip():
                    columns.add(str(col_name))
        except Exception as exc:
            logger.debug(
                "Falha ao coletar colunas visuais de filtros por coluna: %s", exc
            )

        if not bool(getattr(self, "_advanced_filters_active", False)):
            return columns

        adv = getattr(self, "_advanced_filters", None) or {}

        def _has_value(value) -> bool:
            if value is None:
                return False
            if isinstance(value, bool):
                return bool(value)
            if isinstance(value, (list, tuple, set)):
                return len(value) > 0
            return bool(str(value).strip())

        for key, mapped_columns in _ADVANCED_FILTER_VISUAL_COLUMN_MAP.items():
            if not _has_value(adv.get(key)):
                continue
            columns.update(mapped_columns)

        return columns

    def _get_clear_filter_button(self):
        return getattr(self, "clear_filter_button", None)

    def _set_clear_filter_buttons_enabled(self, enabled: bool) -> None:
        target_state = bool(enabled)
        button = self._get_clear_filter_button()
        if button is not None:
            try:
                button.setEnabled(target_state)
            except Exception as exc:
                logger.debug(
                    "Falha ao sincronizar estado de botao limpar em contexto de aba: %s",
                    exc,
                )

    def _sync_clear_filter_button_state(self) -> None:
        self._set_clear_filter_buttons_enabled(self._has_any_active_filters())

    def _iter_undo_filter_buttons(self):
        direct_button = getattr(self, "undo_filter_btn", None)
        if direct_button is not None:
            yield direct_button

    def _set_undo_filter_buttons_enabled(self, enabled: bool) -> None:
        target_state = bool(enabled)
        for button in self._iter_undo_filter_buttons():
            try:
                button.setEnabled(target_state)
            except Exception as exc:
                logger.debug(
                    "Falha ao sincronizar estado de botao undo em contexto de aba: %s",
                    exc,
                )

    def _set_filter_ui_idle(self) -> None:
        """Garante estado visual de ociosidade após abortar/limpar filtros."""
        required_widgets = (
            "progress_bar",
            "load_button",
            "search_button",
            "status_label",
        )
        if any(getattr(self, name, None) is None for name in required_widgets):
            logger.debug(
                "Estado visual de filtro ignorado antes da UI de filtro estar pronta"
            )
            return
        self._filter_ui_state().set_idle()

    def _set_checked_without_signal(
        self,
        widget: Any,
        checked: bool,
        *,
        log_context: str,
    ) -> None:
        try:
            with _blocked_widget_signals(widget, log_context=log_context):
                widget.setChecked(bool(checked))
        except Exception as exc:
            logger.debug("Falha ao alterar checked em %s: %s", log_context, exc)

    def _ask_yes_no(
        self,
        *,
        title: str,
        message: str,
        default_no: bool = True,
    ) -> bool:
        buttons = getattr(QMessageBox, "StandardButton", None)
        if buttons is not None:
            yes_button = buttons.Yes
            reply = QMessageBox.question(
                _qt_parent(self),
                title,
                message,
                yes_button | buttons.No,
                buttons.No if default_no else buttons.Yes,
            )
            return reply == yes_button
        reply = QMessageBox.question(_qt_parent(self), title, message)
        return reply == getattr(QMessageBox, "Yes", reply)

    def _filter_ui_state(self) -> FilterUiStatePresenter:
        presenter = getattr(self, "_filter_ui_state_presenter", None)
        if not isinstance(presenter, FilterUiStatePresenter):
            presenter = FilterUiStatePresenter(
                progress_bar=getattr(self, "progress_bar", None),
                load_button=getattr(self, "load_button", None),
                search_button=getattr(self, "search_button", None),
                status_label=getattr(self, "status_label", None),
                logger=logger,
            )
            self._filter_ui_state_presenter = presenter
        return presenter

    def _invalidate_active_filter_request(self, reason: str = "") -> int:
        """Invalida resultados assíncronos pendentes para evitar sobrescrita tardia."""
        try:
            next_request_id = int(getattr(self, "_filter_request_seq", 0) or 0) + 1
        except Exception:
            next_request_id = 1
        self._filter_request_seq = next_request_id
        self._active_filter_request_id = next_request_id
        if reason:
            logger.debug(
                "Filtro ativo invalidado (%s): request_id=%s", reason, next_request_id
            )
        return next_request_id

    def _filter_worker_lifecycle(self) -> FilterWorkerLifecycle:
        controller = getattr(self, "_filter_worker_lifecycle_controller", None)
        if not isinstance(controller, FilterWorkerLifecycle):
            registry = getattr(self, "_filter_worker_registry", None)
            if not isinstance(registry, DeferredFilterWorkerRegistry):
                registry = DeferredFilterWorkerRegistry()
                self._filter_worker_registry = registry
            controller = FilterWorkerLifecycle(
                logger,
                _connect_filter_signal,
                registry,
                self._get_active_filter_worker,
                self._clear_active_filter_worker_reference,
            )
            self._filter_worker_lifecycle_controller = controller
        return controller

    def _get_active_filter_worker(self):
        return getattr(self, "filter_thread", None)

    def _clear_active_filter_worker_reference(self, worker) -> None:
        if getattr(self, "filter_thread", None) is worker:
            self.filter_thread = None

    def _cancel_active_filter_worker(self, reason: str = "") -> None:
        """Cancela worker anterior antes de iniciar uma nova filtragem assíncrona."""
        self._filter_worker_lifecycle().deactivate_active(reason)

    def _abort_active_filtering(self, reason: str) -> int:
        request_id = self._invalidate_active_filter_request(reason)
        self._cancel_active_filter_worker(reason)
        self._set_filter_ui_idle()
        try:
            self._debounce_timer.stop()
        except Exception as exc:
            logger.debug("Falha ao parar debounce em %s: %s", reason, exc)
        return request_id

    def _on_general_search_apply_clicked(self) -> None:
        logger.debug("Acao aplicar busca geral acionada")
        self.initiate_filtering()

    def _on_general_search_clear_clicked(self) -> None:
        logger.debug("Acao limpar busca geral acionada")
        self.clear_general_search()
        self._maybe_offer_hard_reset_after_repeated_clear_click()

    def _on_clear_all_filters_clicked(self) -> None:
        logger.debug("Acao limpar todos os filtros acionada")
        self._clear_all_filters_global()
        self._maybe_offer_hard_reset_after_repeated_clear_click()

    def _get_filter_source_dataframe(
        self, source: pd.DataFrame | None = None
    ) -> pd.DataFrame:
        """Retorna a fonte de busca preservando cache seguro entre requests."""
        source = self.df_completo if source is None else source
        try:
            source_attrs = getattr(source, "attrs", {})
        except Exception as exc:
            logger.debug(
                "Falha ao ler attrs da fonte de busca; usando df_completo original: %s",
                exc,
            )
            return source

        if not isinstance(source_attrs, dict) or not source_attrs:
            return source

        safe_attr_keys = {
            FILTER_SEARCH_MARKER_ATTR,
            FILTER_SEARCH_CACHE_ATTR,
            FILTER_SEARCH_SIGNATURE_CACHE_ATTR,
            "ssa_preprocessed_for_gui",
            "ssa_non_null_cols",
        }
        unexpected_attr_keys = [
            key for key in source_attrs.keys() if key not in safe_attr_keys
        ]
        if not unexpected_attr_keys:
            return source

        try:
            safe_source = source.copy(deep=False)
        except Exception as exc:
            logger.debug(
                "Falha ao criar copia rasa da fonte de busca; usando df_completo original: %s",
                exc,
            )
            return source

        try:
            safe_source.attrs = {
                key: source_attrs[key] for key in safe_attr_keys if key in source_attrs
            }
        except Exception as exc:
            logger.debug(
                "Falha ao preservar attrs seguros da fonte de busca: %s", exc
            )
        return safe_source

    def _build_filter_worker_df_token(self, source: pd.DataFrame) -> str:
        shape = tuple(getattr(source, "shape", (0, 0)))
        revision = getattr(self, "_data_revision", None)
        data_uuid = getattr(self, "_data_uuid", None)
        content_hash = build_dataframe_filter_hash(source)
        cached = getattr(self, "_filter_worker_df_token_cache", None)
        if isinstance(cached, tuple) and len(cached) == 5:
            (
                cached_source_id,
                cached_shape,
                cached_revision,
                cached_content_hash,
                cached_token,
            ) = cached
            if (
                cached_source_id == id(source)
                and cached_shape == shape
                and cached_revision == (revision, data_uuid)
                and cached_content_hash == content_hash
            ):
                return str(cached_token)
        columns = tuple(str(column) for column in getattr(source, "columns", ()))
        token = repr(
            ("gui-filter-source", content_hash, shape, columns, revision, data_uuid)
        )
        self._filter_worker_df_token_cache = (
            id(source),
            shape,
            (revision, data_uuid),
            content_hash,
            token,
        )
        return token

    def _reset_repeated_clear_click_tracking(self) -> None:
        self._clear_filter_click_count = 0
        self._clear_filter_last_click_ts = 0.0

    def _update_and_check_repeated_clear_click(self) -> bool:
        now = perf_counter()
        try:
            last_click = float(getattr(self, "_clear_filter_last_click_ts", 0.0) or 0.0)
        except Exception:
            last_click = 0.0
        try:
            click_count = int(getattr(self, "_clear_filter_click_count", 0) or 0)
        except Exception:
            click_count = 0
        if (now - last_click) > _CLEAR_FILTER_HARD_RESET_WINDOW_SEC:
            click_count = 0
        click_count += 1
        self._clear_filter_click_count = click_count
        self._clear_filter_last_click_ts = now
        if click_count < _CLEAR_FILTER_HARD_RESET_CLICK_TARGET:
            return False
        self._reset_repeated_clear_click_tracking()
        return True

    def _maybe_offer_hard_reset_after_repeated_clear_click(self) -> None:
        if not self._update_and_check_repeated_clear_click():
            return
        if os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get(
            "SSA_NON_INTERACTIVE"
        ):
            logger.debug(
                "Confirmacao de hard reset suprimida em ambiente nao interativo."
            )
            return
        try:
            accepted = self._ask_yes_no(
                title="Limpar Filtros",
                message=(
                    "Voce clicou varias vezes em limpar filtros. Deseja fazer um "
                    "reset completo, restaurando defaults e limpando a busca?"
                ),
            )
        except Exception as exc:
            logger.debug(
                "Falha ao exibir confirmacao de hard reset apos cliques repetidos: %s",
                exc,
            )
            accepted = False
        if accepted:
            self._hard_reset_filters_state()

    def _apply_general_search_terms(
        self,
        filter_source: pd.DataFrame,
        unique_chunk_terms_lists: list[list[str]],
        *,
        default_mode: str,
        general_search_columns: list[str],
    ) -> pd.DataFrame:
        return apply_general_search_terms(
            filter_source,
            unique_chunk_terms_lists,
            default_mode=default_mode,
            general_search_columns=general_search_columns,
            filter_dataframe_func=filter_dataframe,
        )

    def _get_default_filter_mode(self) -> str:
        if not hasattr(self, "_cached_default_mode"):
            from gui.gui_config import GUI_MAIN_PREFERENCES

            gui_settings = GUI_MAIN_PREFERENCES.get("gui_settings", {})
            self._cached_default_mode = gui_settings.get(
                "default_filter_mode", "contains"
            )
        return str(self._cached_default_mode or "contains")

    def _current_general_search_text(self) -> str:
        return search_undo_controller.current_general_search_text(
            self,
            is_widget_valid=_is_search_widget_valid,
        )

    def _select_general_filter_source_candidate(
        self, search_text: str
    ) -> pd.DataFrame:
        return search_undo_controller.select_general_filter_source_candidate(
            self,
            search_text,
        )

    def _normalized_search_chunks_for_sync(
        self, search_chunks: list[str]
    ) -> list[list[str]]:
        sync_chunks = [
            self._normalize_chunk_for_parse(chunk) for chunk in search_chunks
        ]
        return [terms for terms in sync_chunks if terms]

    def _run_general_filter_synchronously(
        self,
        filter_source: pd.DataFrame,
        search_chunks: list[str],
        *,
        default_mode: str,
        general_search_columns: list[str],
        request_id: int,
        width_safety_context: str | None = None,
    ) -> None:
        try:
            sync_chunks = self._normalized_search_chunks_for_sync(search_chunks)
            df_filtrado = self._apply_general_search_terms(
                filter_source,
                sync_chunks,
                default_mode=default_mode,
                general_search_columns=general_search_columns,
            )
            self.on_filter_finished(df_filtrado, request_id=request_id)
            if width_safety_context is not None:
                self._apply_filter_result_width_safety(width_safety_context)
        except Exception as e:  # noqa: BLE001
            self.on_filter_error(f"Erro ao filtrar dados: {e}", request_id=request_id)
        finally:
            self.on_filter_finished_cleanup(None, request_id=request_id)

    def _start_general_filter_worker(
        self,
        filter_source: pd.DataFrame,
        search_chunks: list[str],
        *,
        default_mode: str,
        general_search_columns: list[str],
        request_id: int,
    ) -> None:
        filter_cache_context = self._build_filter_cache_context()
        worker = FilterWorker(
            filter_source,
            search_chunks,
            search_columns=general_search_columns,
            default_mode=default_mode,
            cache_context=filter_cache_context,
            df_hash=self._build_filter_worker_df_token(filter_source),
        )
        self.filter_thread = worker
        filter_finished_connected = _connect_filter_signal(
            worker.filter_finished,
            lambda df, *_, rid=request_id: self.on_filter_finished(df, request_id=rid),
            label="filter_worker.filter_finished",
        )
        error_connected = _connect_filter_signal(
            worker.error_occurred,
            lambda msg, *_, rid=request_id: self.on_filter_error(msg, request_id=rid),
            label="filter_worker.error_occurred",
        )
        _connect_filter_signal(
            worker.finished,
            lambda *_, w=worker, rid=request_id: self.on_filter_finished_cleanup(
                w, request_id=rid
            ),
            label="filter_worker.finished.cleanup",
        )
        if not (filter_finished_connected and error_connected):
            logger.warning(
                "Falha ao conectar sinais criticos de filtro; abortando inicio do worker."
            )
            self._cleanup_filter_worker(worker)
            self._clear_active_filter_worker_reference(worker)
            self.on_filter_error(
                "Falha ao iniciar filtro: conexoes de sinais indisponiveis.",
                request_id=request_id,
            )
            return
        self._retain_filter_worker_until_finished(worker)
        worker.start()

    def initiate_filtering(self):
        if self.df_completo.empty:
            self._set_filter_ui_idle()
            QMessageBox.information(
                _qt_parent(self), "Aviso", "Nenhum dado carregado para filtrar."
            )
            return

        search_text = self._current_general_search_text()
        previous_search_text = str(
            getattr(self, "_active_filter_search_display", "") or ""
        )
        self._safe_store_last_filter_state(
            "initiate_filtering",
            search_text_override=previous_search_text,
            pending_search_display_override=previous_search_text,
        )
        try:
            self._debounce_timer.stop()
        except Exception as exc:
            logger.debug("Falha ao parar debounce antes de iniciar filtragem: %s", exc)
        request_id = self._invalidate_active_filter_request("initiate_filtering")

        raw_chunks = self._prepare_search_chunks(search_text) if search_text else []
        search_chunks_for_worker = raw_chunks

        self._sync_clear_filter_button_state()

        display_text = search_text if search_text else ""
        filter_source_candidate = self._select_general_filter_source_candidate(
            search_text
        )
        self._pending_search_display = display_text
        self._active_filter_search_display = display_text
        self._active_filter_search_request_id = request_id

        self._filter_ui_state().set_busy()

        default_mode = self._get_default_filter_mode()
        filter_source = self._get_filter_source_dataframe(filter_source_candidate)
        general_search_columns = build_gui_general_search_columns(filter_source)

        # Modo síncrono (sem QThread) opcional para testes
        if getattr(self, "_sync_filtering", False):
            self._run_general_filter_synchronously(
                filter_source,
                search_chunks_for_worker,
                default_mode=default_mode,
                general_search_columns=general_search_columns,
                request_id=request_id,
                width_safety_context="sync_filtering",
            )
            return

        self._cancel_active_filter_worker("initiate_filtering_new_request")

        # Fallback defensivo para ambientes sem worker assíncrono disponível
        if FilterWorker is None:
            logger.warning(
                "FilterWorker indisponivel; aplicando filtro em modo sincrono"
            )
            self._run_general_filter_synchronously(
                filter_source,
                search_chunks_for_worker,
                default_mode=default_mode,
                general_search_columns=general_search_columns,
                request_id=request_id,
            )
            return

        self._start_general_filter_worker(
            filter_source,
            search_chunks_for_worker,
            default_mode=default_mode,
            general_search_columns=general_search_columns,
            request_id=request_id,
        )

    def on_filter_finished(
        self, df_filtrado: pd.DataFrame, request_id: int | None = None
    ):
        active_id = getattr(self, "_active_filter_request_id", None)
        effective_request_id = request_id if request_id is not None else active_id
        if request_id is not None and active_id is not None and request_id != active_id:
            logger.debug(
                "Ignorando resultado de filtro obsoleto (request_id=%s, active=%s)",
                request_id,
                active_id,
            )
            return
        table_widget = getattr(self, "table_widget", None)
        if not _is_search_widget_valid(table_widget):
            logger.debug(
                "table_widget indisponivel no inicio de on_filter_finished; ignorando resultado."
            )
            return
        has_post_search_filters = False
        try:
            (
                has_column_filters,
                has_advanced_filters,
                has_excluded_terminal_status,
            ) = self._filter_refresh_flags()
            has_post_search_filters = self._compute_has_post_search_filters(
                has_column_filters=has_column_filters,
                has_advanced_filters=has_advanced_filters,
                has_excluded_terminal_status=has_excluded_terminal_status,
                for_sort_defer=True,
            )
        except Exception as exc:
            logger.debug(
                "Falha ao avaliar pos-filtros antes do sort de busca geral: %s",
                exc,
            )
        try:
            if (
                not has_post_search_filters
                and not df_filtrado.empty
                and "numero_ssa" in df_filtrado.columns
            ):
                df_filtrado = df_filtrado.sort_values(
                    "numero_ssa", ascending=False
                )
                df_filtrado.attrs["ssa_sorted_for_display"] = True
        except Exception as exc:
            logger.warning(
                "Falha ao ordenar numero_ssa no fim do filtro geral: %s", exc
            )
        # Atualiza baseline do resultado da busca global
        self._df_last_search_filtered = df_filtrado
        # OTIMIZACAO: Sinaliza que larguras precisam ser recalculadas para novo dataset
        self._widths_computed_for_df_hash = None
        self._refresh_after_filter_change(commit_pending_search=False)
        # CORRECAO 2026-01-08: Exibir contagem de hits e termos de busca
        search_text = ""
        current_search_request_id = getattr(
            self, "_active_filter_search_request_id", None
        )
        if (
            effective_request_id is not None
            and effective_request_id == current_search_request_id
        ):
            search_text = str(
                getattr(self, "_active_filter_search_display", "") or ""
            ).strip()
        filtered_total_current = None
        try:
            if hasattr(self, "df_exibido") and isinstance(
                self.df_exibido, pd.DataFrame
            ):
                filtered_total_current = len(self.df_exibido)
            elif isinstance(df_filtrado, pd.DataFrame):
                filtered_total_current = len(df_filtrado)
        except Exception:
            filtered_total_current = None
        zero_results_suffix = ""
        if filtered_total_current == 0:
            try:
                if self._has_any_active_filters():
                    zero_results_suffix = "Aviso: nenhum resultado para o filtro atual."
            except Exception as exc:
                logger.debug(
                    "Falha ao avaliar filtros ativos para aviso de zero resultado: %s",
                    exc,
                )
        self._update_filter_status_display(
            filtered_total=filtered_total_current,
            original_total=len(self.df_completo)
            if hasattr(self, "df_completo") and self.df_completo is not None
            else None,
            search_text=search_text,
            suffix=zero_results_suffix,
        )
        self._sync_clear_filter_button_state()
        self._apply_search_display()
        self._apply_filter_result_width_safety("filter_finished", deferred=True)
        self._consume_pending_jump_to_ssa(effective_request_id)

    def on_filter_error(self, error_msg: str, request_id: int | None = None):
        active_id = getattr(self, "_active_filter_request_id", None)
        if request_id is not None and active_id is not None and request_id != active_id:
            logger.debug(
                "Ignorando erro de filtro obsoleto (request_id=%s, active=%s)",
                request_id,
                active_id,
            )
            return
        table_available = _is_search_widget_valid(getattr(self, "table_widget", None))
        if not table_available:
            logger.debug(
                "table_widget indisponivel no inicio de on_filter_error; registrando erro sem recuperar selecao: %s",
                error_msg,
            )
        pending_jump = getattr(self, "_pending_jump_to_ssa", None)
        if (
            table_available
            and
            isinstance(pending_jump, dict)
            and request_id is not None
            and pending_jump.get("request_id") == request_id
        ):
            if self._recover_pending_jump_after_filter_error(
                pending_jump, error_msg, request_id
            ):
                return
            self._pending_jump_to_ssa = None
        # Avoid modal dialogs during automated tests (can deadlock the pytest runner).
        if os.environ.get("PYTEST_CURRENT_TEST"):
            logger.debug("PYTEST_CURRENT_TEST set; skipping modal filter error dialog.")
        else:
            QMessageBox.critical(_qt_parent(self), "Erro de Filtro", error_msg)
        self._filter_ui_state().set_error()

    def _recover_pending_jump_after_filter_error(
        self, pending_jump: dict[str, Any], error_msg: str, request_id: int | None
    ) -> bool:
        numero_ssa = str(pending_jump.get("numero_ssa") or "").strip()
        if not numero_ssa:
            return False
        try:
            current_search = str(self.search_input.text() or "").strip()
        except Exception as exc:
            logger.debug(
                "Falha ao ler busca atual durante recuperacao de salto pendente: %s",
                exc,
            )
            return False
        if current_search != f"={numero_ssa}":
            return False
        try:
            filter_source = self._get_filter_source_dataframe()
            default_mode = self._get_default_filter_mode()
            parsed = parse_search_terms([f"={numero_ssa}"], default_mode=default_mode)
            general_search_columns = build_gui_general_search_columns(filter_source)
            df_filtrado = filter_dataframe(
                filter_source,
                parsed,
                search_columns=general_search_columns,
            )
        except Exception as exc:
            logger.debug(
                "Falha no fallback sincrono do salto pendente para SSA %s apos erro '%s': %s",
                numero_ssa,
                error_msg,
                exc,
            )
            return False
        logger.warning(
            "Filtro assincrono falhou durante salto pendente para SSA %s; aplicando fallback sincrono. erro=%s",
            numero_ssa,
            error_msg,
        )
        self._pending_search_display = f"={numero_ssa}"
        self._active_filter_search_display = f"={numero_ssa}"
        self._active_filter_search_request_id = request_id
        try:
            self.search_input.setText(f"={numero_ssa}")
        except Exception as exc:
            logger.debug(
                "Falha ao restaurar texto de busca durante fallback do salto pendente: %s",
                exc,
            )
        self.on_filter_finished(df_filtrado, request_id=request_id)
        return True

    def _consume_pending_jump_to_ssa(self, request_id: int | None) -> None:
        pending_jump = getattr(self, "_pending_jump_to_ssa", None)
        if not (
            isinstance(pending_jump, dict)
            and pending_jump.get("request_id") == request_id
            and pending_jump.get("numero_ssa")
        ):
            return
        self._pending_jump_to_ssa = None
        try:
            self._jump_to_ssa(pending_jump["numero_ssa"], _allow_refilter=False)
        except Exception as exc:
            logger.debug(
                "Falha ao concluir salto pendente para SSA %s apos filtro: %s",
                pending_jump.get("numero_ssa"),
                exc,
            )

    def _apply_filter_result_width_safety(
        self, context: str, *, deferred: bool = False
    ) -> None:
        try:
            self._ensure_nonzero_column_widths()
        except Exception as exc:
            logger.debug("Falha ao reforcar largura minima em %s: %s", context, exc)
        try:
            self._apply_safe_width_for_main_column()
        except Exception as exc:
            logger.debug(
                "Falha ao aplicar largura de seguranca em %s: %s",
                context,
                exc,
            )
        if not deferred:
            return
        try:
            self_ref = weakref.ref(self)

            def _apply_width_if_alive() -> None:
                window = self_ref()
                if window is not None:
                    window._apply_safe_width_deferred(context)

            QTimer.singleShot(0, _apply_width_if_alive)
        except Exception as exc:
            logger.debug(
                "Falha ao agendar largura de seguranca em %s: %s",
                context,
                exc,
            )

    def _apply_safe_width_deferred(self, context: str) -> None:
        try:
            if sip is not None and sip.isdeleted(cast(Any, self)):
                return
        except Exception as exc:
            logger.debug(
                "Falha ao verificar janela antes da largura deferida em %s: %s",
                context,
                exc,
            )
            return
        try:
            self._ensure_nonzero_column_widths()
        except Exception as exc:
            logger.debug(
                "Falha ao reforcar largura minima deferida em %s: %s",
                context,
                exc,
            )
        try:
            self._apply_safe_width_for_main_column()
        except Exception as exc:
            logger.debug(
                "Falha ao aplicar largura deferida em %s: %s",
                context,
                exc,
            )

    def _apply_safe_width_for_main_column(self) -> None:
        table_widget = getattr(self, "table_widget", None)
        main_column_index = 1
        if table_widget is None or table_widget.columnCount() <= main_column_index:
            return
        if table_widget.columnWidth(main_column_index) == 0:
            self._set_safe_width_for_col_index(main_column_index, 80)

    def _retain_filter_worker_until_finished(self, worker) -> None:
        self._filter_worker_lifecycle().retain_until_finished(worker)

    def _is_filter_worker_running(self, worker) -> bool:
        return self._filter_worker_lifecycle().is_running(worker)

    def _prune_retired_filter_workers(self) -> None:
        self._filter_worker_lifecycle().prune()

    def _cleanup_filter_worker(self, worker) -> bool:
        return self._filter_worker_lifecycle().cleanup(worker)

    def on_filter_finished_cleanup(self, worker=None, request_id: int | None = None):
        """Limpa estado pós-thread de filtragem com checagens defensivas.

        Em execuções headless/CI alguns widgets podem já ter sido destruídos
        (ex.: fechamento da janela durante teardown de teste), o que pode causar
        abort em chamadas Qt nativas. Garantimos que os atributos existem e que
        o thread já não está em execução antes de manipular.
        """
        active_id = getattr(self, "_active_filter_request_id", None)
        is_stale = (
            request_id is not None and active_id is not None and request_id != active_id
        )
        if is_stale:
            self._cleanup_filter_worker(worker)
            try:
                self._prune_retired_filter_workers()
            except Exception as exc:
                logger.debug(
                    "Falha ao podar workers de filtro em cleanup obsoleto: %s", exc
            )
            return
        try:
            target_worker = (
                worker if worker is not None else getattr(self, "filter_thread", None)
            )
            self._cleanup_filter_worker(target_worker)
            self._filter_ui_state().set_cleanup()
            try:
                self._prune_retired_filter_workers()
            except Exception as exc:
                logger.debug("Falha ao podar workers de filtro em finalizacao: %s", exc)
        except Exception as exc:
            # Nunca propagar exceção daqui; log mínimo opcional futuro
            logger.warning("Falha inesperada no cleanup final de filtro: %s", exc)
            self._clear_active_filter_worker_reference(
                worker if worker is not None else getattr(self, "filter_thread", None)
            )

    def clear_general_search(self, *, reason: str = "clear_general_search"):
        """Limpa apenas a busca geral e reaplica filtros ativos."""
        had_applied_search = bool(
            str(getattr(self, "_active_filter_search_display", "") or "").strip()
        )
        self._safe_store_last_filter_state(reason)
        self._abort_active_filtering(reason)
        try:
            self._set_search_text_across_tabs("")
        except Exception as exc:
            logger.warning(
                "Falha ao sincronizar campos de busca em clear_general_search: %s", exc
            )
            with _blocked_widget_signals(
                self.search_input, log_context="clear_general_search"
            ):
                self.search_input.clear()
                self.search_input.setText("")
        self._pending_search_display = None
        self._active_filter_search_display = ""
        self._active_filter_search_request_id = None
        # Nao limpa filtros avancados nem filtros de coluna aqui.
        # Esse botao limpa apenas a busca geral; limpeza global usa "_clear_all_filters_global".
        self._df_last_search_filtered = self.df_completo
        has_column_filters, has_advanced_filters, has_excluded_terminal_status = (
            self._filter_refresh_flags()
        )
        if not (
            had_applied_search
            or has_column_filters
            or has_advanced_filters
            or has_excluded_terminal_status
        ):
            self._set_filtered_count_status()
            self._sync_clear_filter_button_state()
            try:
                self._update_filters_summary()
            except Exception as exc:
                logger.debug(
                    "Falha ao atualizar resumo de filtros em clear_filter: %s", exc
                )
            return
        self._refresh_after_filter_change()
        self._set_filtered_count_status()
        self._sync_clear_filter_button_state()
        # Atualizar resumo de filtros
        try:
            self._update_filters_summary()
        except Exception as exc:
            logger.debug(
                "Falha ao atualizar resumo de filtros em clear_filter: %s", exc
            )

    def clear_filter(self):
        """Compatibility alias for callers that clear only the general search."""
        self.clear_general_search(reason="clear_filter")

    # --- Ordenaçção por clique no cabeçalho ---

    def _on_search_text_changed(self, _text: str):
        """Reinicia o temporizador de debounce ao digitar na busca."""
        # Chamar start() novamente reinicia o QTimer automaticamente
        try:
            self._debounce_timer.start()
        except Exception as exc:
            logger.debug("Falha ao reiniciar debounce na busca: %s", exc)

    def clear_filter_cache(self):
        """Limpa o cache de filtros."""
        # Usa logger e verifica disponibilidade do FilterWorker e cache
        if FilterWorker is not None:
            try:
                FilterWorker.clear_shared_cache()
                logger.debug("Cache de filtros limpo")
            except Exception as e:  # pragma: no cover
                logger.debug("Falha ao limpar cache de filtros: %s", e)
        else:
            logger.debug("FilterWorker indisponivel; cache nao limpo")

    # --- Slots e Handlers ---

    def _open_add_column_filter_menu(self):
        """Exibe menu com todas as colunas disponiveis para ativar filtros dedicados."""
        open_add_column_filter_menu(self)

    def _resolve_column_display_name(self, col: str) -> str:
        internal_map = getattr(self, "internal_to_display", None)
        if not isinstance(internal_map, dict):
            internal_map = {}
        internal_alias = internal_map.get(col, col)
        if str(internal_alias).strip() and str(internal_alias).strip() != str(col):
            return str(internal_alias)
        default_alias = DEFAULT_DISPLAY_MAPPINGS.get(col)
        if str(default_alias or "").strip():
            return str(default_alias)
        logger.warning(
            "Coluna sem alias canonico encontrada no menu de filtro: %s", col
        )
        return str(col)

    def _expand_column_alias_for_filter(self, col: str) -> str:
        """Use compact labels in the column-filter list."""
        resolved = self._resolve_column_display_name(col)
        return compact_column_filter_display_name(resolved)

    def _find_unmapped_alias_columns(self, candidates) -> list[str]:
        seen = set()
        missing = []
        for col in candidates:
            if not isinstance(col, str) or not col or col in seen or col == "#":
                continue
            seen.add(col)
            has_internal = _has_named_alias(
                getattr(self, "internal_to_display", None), col
            )
            has_default = col in DEFAULT_DISPLAY_MAPPINGS
            if not has_internal and not has_default:
                missing.append(col)
        return sorted(missing)

    def _activate_column_filter(self, col_name: str):
        """Garante entrada para a coluna solicitada e prepara foco na interface."""
        if not col_name:
            return
        if col_name not in self._active_column_filters:
            self._safe_store_last_filter_state("activate_column_filter")
            self._active_column_filters[col_name] = ""
            try:
                self._mark_profile_as_custom()
            except Exception as exc:
                logger.debug(
                    "Falha ao marcar perfil como custom ao ativar filtro de coluna %s: %s",
                    col_name,
                    exc,
                )
        self._pending_filter_focus = col_name
        self._build_column_filters_panel()

    def _deactivate_column_filter(self, col_name: str):
        """Remove coluna do conjunto de filtros ativos e atualiza a interface."""
        if not col_name:
            return
        if (
            col_name not in self._active_column_filters
            and col_name not in self._column_to_or_group
        ):
            return
        self._safe_store_last_filter_state("deactivate_column_filter")
        removed = False
        if col_name in self._column_to_or_group:
            group = self._column_to_or_group.get(col_name)
            if group:
                for member in group.get("columns", []):
                    if member in self._active_column_filters:
                        self._active_column_filters.pop(member, None)
                        removed = True
                group["values"] = []
        elif col_name in self._active_column_filters:
            self._active_column_filters.pop(col_name, None)
            removed = True
        if not removed:
            return
        try:
            self._mark_profile_as_custom()
        except Exception as exc:
            logger.debug(
                "Falha ao marcar perfil como custom ao desativar filtro de coluna %s: %s",
                col_name,
                exc,
            )
        self._pending_filter_focus = None
        self._build_column_filters_panel()
        self._refresh_after_filter_change()

    def _build_column_filters_panel(self):
        build_column_filters_panel(self)

    def _capture_focused_column_filter_text(self) -> dict[str, str]:
        pending: dict[str, str] = {}
        for col, widget in (getattr(self, "_column_filter_inputs", {}) or {}).items():
            if not isinstance(widget, QLineEdit):
                continue
            try:
                if widget.hasFocus():
                    pending[str(col)] = str(widget.text() or "")
            except RuntimeError as exc:
                logger.debug("Filtro de coluna destruido ao capturar texto: %s", exc)
            except Exception as exc:
                logger.debug("Falha ao capturar texto pendente do filtro %s: %s", col, exc)
        return pending

    def _apply_filter_widget_theme(self, label_widget=None, input_widget=None):
        theme = getattr(self, "_current_theme", "") or "dark"
        roles = get_theme_roles(theme)
        label_color = (
            roles.get("panel_text") or roles.get("label_color") or "palette(text)"
        )
        if label_widget is not None:
            label_widget.setStyleSheet(f"color:{label_color};")
        if input_widget is not None:
            input_text = (
                roles.get("input_text") or roles.get("panel_text") or "palette(text)"
            )
            input_bg = roles.get("panel_bg") or roles.get("input_bg") or "palette(base)"
            input_border = (
                roles.get("input_border") or roles.get("panel_border") or "palette(mid)"
            )
            input_focus = (
                roles.get("input_border_focus") or roles.get("accent") or input_border
            )
            input_placeholder = (
                roles.get("input_placeholder") or roles.get("muted_text") or label_color
            )
            try:
                input_widget.setObjectName("columnFilterInput")
            except RuntimeError as exc:
                logger.debug("Filtro de coluna destruido ao nomear input: %s", exc)
                return
            style = (
                f"QLineEdit#columnFilterInput {{ font-size:11px; color:{input_text}; background-color:{input_bg}; border:1px solid {input_border}; border-radius:4px; padding:3px 6px; }}\n"
                f"QLineEdit#columnFilterInput::placeholder {{ color:{input_placeholder}; }}\n"
                f"QLineEdit#columnFilterInput:focus {{ border:1px solid {input_focus}; }}\n"
            )
            try:
                input_widget.setStyleSheet(style)
            except RuntimeError as exc:
                logger.debug("Filtro de coluna destruido ao aplicar estilo: %s", exc)

    def _resolve_status_totals(
        self,
        filtered_total: int | None = None,
        original_total: int | None = None,
    ) -> tuple[int, int]:
        total_original = (
            int(original_total)
            if original_total is not None
            else (
                len(self.df_completo)
                if hasattr(self, "df_completo") and self.df_completo is not None
                else 0
            )
        )
        total_filtrado = (
            int(filtered_total)
            if filtered_total is not None
            else (
                len(self.df_exibido)
                if hasattr(self, "df_exibido") and self.df_exibido is not None
                else 0
            )
        )
        return total_filtrado, total_original

    def update_filter_status_display(
        self,
        filtered_total: int | None = None,
        original_total: int | None = None,
        search_text: str | None = None,
        suffix: str = "",
    ) -> tuple[str, str]:
        return self._update_filter_status_display(
            filtered_total=filtered_total,
            original_total=original_total,
            search_text=search_text,
            suffix=suffix,
        )

    def _update_filter_status_display(
        self,
        filtered_total: int | None = None,
        original_total: int | None = None,
        search_text: str | None = None,
        suffix: str = "",
    ) -> tuple[str, str]:
        total_filtrado, total_original = self._resolve_status_totals(
            filtered_total=filtered_total,
            original_total=original_total,
        )
        resolved_search_text = self._resolve_status_search_text(search_text)
        payload = FilterStatusPayload(
            filtered_total=total_filtrado,
            original_total=total_original,
            search_text=resolved_search_text,
            suffix=suffix,
        )
        filtered_status_label = getattr(self, "filtered_status_label", None)
        status_label = getattr(self, "status_label", None)
        shares_single_status_label = (
            filtered_status_label is None
            or status_label is None
            or filtered_status_label is status_label
        )
        count_status_text, notice_status_text = FilterStatusManager.build_status_texts(
            payload=payload,
            split_labels=not shares_single_status_label,
        )
        if filtered_status_label is not None:
            filtered_status_label.setText(
                count_status_text.removeprefix("Status: ").strip()
            )
        if status_label is not None and status_label is not filtered_status_label:
            if shares_single_status_label:
                status_label.setText(count_status_text)
            else:
                status_label.setText(notice_status_text)
        return count_status_text, notice_status_text

    def _resolve_status_search_text(self, search_text: str | None = None) -> str:
        if search_text is not None:
            return str(search_text or "").strip()
        active_search_display = str(
            getattr(self, "_active_filter_search_display", "") or ""
        ).strip()
        if active_search_display:
            return active_search_display
        return str(getattr(self, "_pending_search_display", "") or "").strip()

    def _set_filtered_count_status(
        self,
        filtered_total: int | None = None,
        original_total: int | None = None,
    ) -> None:
        self._update_filter_status_display(
            filtered_total=filtered_total,
            original_total=original_total,
            search_text=None,
            suffix="",
        )

    def _refresh_column_filter_widgets(self):
        labels = getattr(self, "_column_filter_labels", {}) or {}
        inputs = getattr(self, "_column_filter_inputs", {}) or {}
        for col, label in labels.items():
            self._apply_filter_widget_theme(label, inputs.get(col))

    def _clear_single_column_filter(
        self, col_name: str, current_text: Optional[str] = None
    ):
        if col_name in self._active_column_filters:
            try:
                if str(
                    self._active_column_filters.get(col_name, "")
                ).strip() == "" and (
                    current_text is None or str(current_text).strip() == ""
                ):
                    return
            except Exception as exc:
                logger.debug(
                    "Falha ao verificar estado atual do filtro de coluna %s antes de limpar: %s",
                    col_name,
                    exc,
                )
            self._safe_store_last_filter_state("clear_single_column_filter")
            if col_name in self._column_to_or_group:
                group = self._column_to_or_group.get(col_name)
                if group:
                    group["values"] = []
                    for member in group.get("columns", []):
                        self._active_column_filters[member] = ""
            elif col_name in self._active_column_filters:
                self._active_column_filters[col_name] = ""
            self._mark_profile_as_custom()
            self._build_column_filters_panel()
            self._refresh_after_filter_change()
            self._sync_clear_filter_button_state()

    def _clear_all_column_filters(self):
        if not self._active_column_filters:
            self._active_column_filters = OrderedDict(
                (col, "") for col in self._column_filter_default_columns()
            )
            self._build_column_filters_panel()
            return
        self._safe_store_last_filter_state("clear_all_column_filters")
        for group in getattr(self, "_column_or_groups", []):
            group["values"] = []
        self._active_column_filters = OrderedDict(
            (col, "") for col in self._column_filter_default_columns()
        )
        # Restaura linhas ocultas apenas na exibição
        try:
            self._hidden_column_filter_lines.clear()
        except Exception:
            self._hidden_column_filter_lines = set()
        # Limpa também o texto dedicado de OR (somente exibição)
        self._dedicated_or_text = ""
        self._mark_profile_as_custom()
        self._build_column_filters_panel()
        self._refresh_after_filter_change()
        self._sync_clear_filter_button_state()

    def _on_exclude_ste_sca_toggled(self, checked: bool):
        self._safe_store_last_filter_state("toggle_exclude_ste")
        self._abort_active_filtering("toggle_exclude_ste")
        checked_bool = bool(checked)
        self._exclude_ste_sca = checked_bool
        try:
            if (
                hasattr(self, "exclude_ste_checkbox")
                and self.exclude_ste_checkbox is not None
            ):
                checkbox = self.exclude_ste_checkbox
                try:
                    if checkbox.isChecked() != checked_bool:
                        self._set_checked_without_signal(
                            checkbox,
                            checked_bool,
                            log_context="exclude_ste_checkbox",
                        )
                except Exception as exc:
                    logger.debug(
                        "Falha ao sincronizar checkbox exclude_ste principal: %s",
                        exc,
                    )
        except Exception as exc:
            logger.warning(
                "Falha ao sincronizar toggle de excluir STE/SCA: %s", exc
            )
        self._mark_profile_as_custom()
        self._refresh_after_filter_change()

    def _clear_all_filters_global(self):
        """Limpa todos os filtros: busca geral + filtros de coluna"""
        self._safe_store_last_filter_state("clear_all_filters_global")
        self._abort_active_filtering("clear_all_filters_global")
        # Limpar filtro de busca geral
        try:
            sector_timer = getattr(self, "_sector_debounce_timer", None)
            if sector_timer is not None:
                sector_timer.stop()
        except Exception as exc:
            logger.debug(
                "Falha ao parar debounce de setor em clear_all_filters_global: %s", exc
            )
        try:
            self._set_search_text_across_tabs("")
        except Exception as exc:
            logger.warning(
                "Falha ao limpar busca em todas as abas em clear_all_filters_global: %s",
                exc,
            )
            with _blocked_widget_signals(
                self.search_input, log_context="clear_all_filters_global"
            ):
                self.search_input.clear()
                self.search_input.setText("")
        self._pending_search_display = None
        self._active_filter_search_display = ""
        self._df_last_search_filtered = self.df_completo

        # Limpar todos os filtros de coluna com o mesmo baseline padrao
        self._active_column_filters = OrderedDict(
            (col, "") for col in self._column_filter_default_columns()
        )
        self._reset_or_groups()

        # Limpar filtros auxiliares/avancados
        self._exclude_ste_sca = False
        self._advanced_filters = {}
        self._advanced_filters_active = False
        self.current_filter_profile = None
        self._profile_base_filters = {}
        selector = getattr(self, "profile_selector", None)
        if selector is not None:
            try:
                with _blocked_widget_signals(
                    selector, log_context="clear_all_filters_profile_selector"
                ):
                    selector.setCurrentIndex(0)
            except Exception as exc:
                logger.debug(
                    "Falha ao limpar seletor de perfil em clear_all_filters_global: %s",
                    exc,
                )
        checkbox = getattr(self, "exclude_ste_checkbox", None)
        if checkbox is not None:
            try:
                with _blocked_widget_signals(
                    checkbox, log_context="clear_all_filters_exclude_checkbox"
                ):
                    checkbox.setChecked(False)
            except Exception as exc:
                logger.debug(
                    "Falha ao limpar checkbox exclude_ste em clear_all_filters_global: %s",
                    exc,
                )
        try:
            if hasattr(self, "_sync_advanced_filter_ui"):
                self._sync_advanced_filter_ui()
        except Exception as exc:
            logger.warning(
                "Falha ao sincronizar UI de filtros avancados em clear_all_filters_global: %s",
                exc,
            )

        # Restaura linhas ocultas e limpa Filtro OU dedicado (exibição)
        try:
            self._hidden_column_filter_lines.clear()
        except Exception:
            self._hidden_column_filter_lines = set()
        self._dedicated_or_text = ""
        self._build_column_filters_panel()
        self._render_filter_reset_baseline()

    def _hard_reset_filters_state(self):
        """Reseta agressivamente estado interno e visual dos filtros sem tocar nos botoes atuais."""
        self._reset_repeated_clear_click_tracking()
        self._abort_active_filtering("hard_reset_filters_state")
        try:
            sector_timer = getattr(self, "_sector_debounce_timer", None)
            if sector_timer is not None:
                sector_timer.stop()
        except Exception as exc:
            logger.debug(
                "Falha ao parar debounce de setor em hard_reset_filters_state: %s", exc
            )

        try:
            self._set_search_text_across_tabs("")
        except Exception as exc:
            logger.warning(
                "Falha ao limpar busca em todas as abas em hard_reset_filters_state: %s",
                exc,
            )
            with _blocked_widget_signals(
                self.search_input, log_context="hard_reset_filters_state"
            ):
                self.search_input.clear()
                self.search_input.setText("")

        self._pending_search_display = None
        self._pending_filter_focus = None
        self._df_last_search_filtered = self.df_completo
        self._active_column_filters = OrderedDict(
            (col, "") for col in self._column_filter_default_columns()
        )
        self._reset_or_groups()
        self._exclude_ste_sca = False
        self._advanced_filters = {}
        self._advanced_filters_active = False
        self.current_filter_profile = None
        self._profile_base_filters = {}
        self._last_filter_state = None
        self._hidden_column_filter_lines = set()
        self._dedicated_or_text = ""

        selector = getattr(self, "profile_selector", None)
        if selector is not None:
            try:
                with _blocked_widget_signals(
                    selector, log_context="hard_reset_profile_selector"
                ):
                    selector.setCurrentIndex(0)
            except Exception as exc:
                logger.debug(
                    "Falha ao limpar seletor de perfil principal em hard_reset_filters_state: %s",
                    exc,
                )
        checkbox = getattr(self, "exclude_ste_checkbox", None)
        if checkbox is not None:
            try:
                with _blocked_widget_signals(
                    checkbox, log_context="hard_reset_exclude_checkbox"
                ):
                    checkbox.setChecked(False)
            except Exception as exc:
                logger.debug(
                    "Falha ao limpar checkbox exclude_ste em hard_reset_filters_state: %s",
                    exc,
                )

        try:
            if hasattr(self, "_sync_advanced_filter_ui"):
                self._sync_advanced_filter_ui()
        except Exception as exc:
            logger.warning(
                "Falha ao sincronizar UI de filtros avancados em hard_reset_filters_state: %s",
                exc,
            )

        self._build_column_filters_panel()
        self._render_filter_reset_baseline()
        self._update_undo_button_state()
        try:
            self.update_filter_tags()
        except Exception as exc:
            logger.debug("Falha ao atualizar tags em hard_reset_filters_state: %s", exc)
        try:
            self.status_label.setText("Status: Filtros resetados completamente.")
        except Exception as exc:
            logger.debug(
                "Falha ao atualizar status em hard_reset_filters_state: %s", exc
            )

    def _render_filter_reset_baseline(self) -> None:
        """Render the full dataset after a full filter reset through one path."""
        self.df_exibido = self.df_completo
        self._last_table_render_signature = None
        try:
            self.paginator.current_page = 1
        except Exception as exc:
            logger.debug("Falha ao reposicionar paginador no reset de filtros: %s", exc)
        self.paginator.set_dataframe(self.df_exibido)
        self.display_current_page(1, update_details=False)
        self._schedule_filter_refresh_details_update()
        self._update_col_filter_indicator()
        self._set_filtered_count_status()
        self._sync_clear_filter_button_state()
        try:
            self._update_filters_summary()
        except Exception as exc:
            logger.debug(
                "Falha ao atualizar resumo de filtros no reset de filtros: %s", exc
            )
        try:
            sync_combo = getattr(
                self, "_sync_quick_setor_executor_combo_from_filters", None
            )
            if callable(sync_combo):
                sync_combo()
        except Exception as exc:
            logger.debug(
                "Falha ao sincronizar combo rapido no reset de filtros: %s", exc
            )

    def _filters_summary_display_name(self, col: str) -> str:
        return filters_summary_display_name(col, self._resolve_column_display_name)

    def _read_filters_summary_search_text(self) -> str:
        if not hasattr(self, "search_input"):
            return ""
        try:
            return str(self.search_input.text() or "").strip()
        except Exception as exc:
            logger.debug("Falha ao obter busca atual para resumo de filtros: %s", exc)
            return ""

    def _filters_summary_context(self) -> FilterSummaryContext:
        return FilterSummaryContext(
            search_text=self._read_filters_summary_search_text(),
            dedicated_or_text=str(getattr(self, "_dedicated_or_text", "") or ""),
            active_column_filters=getattr(self, "_active_column_filters", {}) or {},
            column_or_groups=getattr(self, "_column_or_groups", []) or [],
            column_to_or_group=getattr(self, "_column_to_or_group", {}) or {},
            advanced_filters=getattr(self, "_advanced_filters", None) or {},
            advanced_filters_active=bool(
                getattr(self, "_advanced_filters_active", False)
            ),
            exclude_terminal_statuses=bool(getattr(self, "_exclude_ste_sca", False)),
            theme_name=str(getattr(self, "_current_theme", "") or "dark"),
        )

    def _build_filters_summary_base_entries(
        self, context: FilterSummaryContext | None = None
    ) -> tuple[OrderedDict[str, SummaryEntry], tuple, dict, bool]:
        return build_filters_summary_base_entries(
            context=context or self._filters_summary_context(),
            display_name_for_column=self._filters_summary_display_name,
            format_value=self._format_column_filter_display_value,
        )

    def _append_filters_summary_advanced_entries(
        self, summary_entries: OrderedDict[str, SummaryEntry], adv: dict, adv_active: bool
    ) -> None:
        if adv_active:
            for text, entry in build_advanced_summary_entries(adv).items():
                _merge_summary_actions(
                    summary_entries,
                    text=text,
                    actions=list(entry.get("actions") or []),
                )

        if getattr(self, "_exclude_ste_sca", False):
            _merge_summary_actions(
                summary_entries,
                text=_EXCLUDED_TERMINAL_SUMMARY,
                actions=[{"kind": "exclude_ste_sca"}],
            )

    def _get_filter_summary_presenter(self) -> FilterSummaryPresenter | None:
        widgets = (
            getattr(self, "filters_summary_frame", None),
            getattr(self, "filters_summary_label", None),
            getattr(self, "filters_summary_items_widget", None),
            getattr(self, "filters_summary_items_layout", None),
            getattr(self, "filters_summary_scroll", None),
        )
        if any(widget is None for widget in widgets):
            return None
        presenter = getattr(self, "_filter_summary_presenter", None)
        if not isinstance(presenter, FilterSummaryPresenter):
            presenter = FilterSummaryPresenter(
                FilterSummaryWidgets(
                    frame=widgets[0],
                    label=widgets[1],
                    items_widget=widgets[2],
                    items_layout=widgets[3],
                    scroll=widgets[4],
                ),
                logger,
            )
            self._filter_summary_presenter = presenter
        return presenter

    def _update_filters_summary(self):
        """Atualiza o resumo de filtros ativos na interface"""
        summary_context = self._filters_summary_context()
        raw_summary_signature = build_filters_summary_raw_signature(
            context=summary_context,
        )
        if raw_summary_signature == getattr(self, "_filters_summary_raw_signature", None):
            return
        summary_entries, raw_summary_signature, adv, adv_active = (
            self._build_filters_summary_base_entries(summary_context)
        )
        self._filters_summary_raw_signature = raw_summary_signature

        self._append_filters_summary_advanced_entries(
            summary_entries, adv=adv, adv_active=adv_active
        )

        active_filters = [entry["text"] for entry in summary_entries.values()]

        if active_filters:
            summary_text = "Filtros ativos: " + "; ".join(active_filters)
        else:
            summary_text = "Nenhum filtro ativo"

        active_state = bool(active_filters)
        presenter = self._get_filter_summary_presenter()
        if presenter is not None:
            presenter.update(
                theme_name=str(getattr(self, "_current_theme", "") or "dark"),
                summary_text=summary_text,
                active_state=active_state,
                entries=list(summary_entries.values()),
                on_remove=self._on_filters_summary_item_clicked,
            )

    def _confirm_filter_summary_item_removal(self, item_text: str) -> bool:
        title = "Remover filtro"
        message = f"Deseja remover este filtro ativo?\n\n{item_text}"
        if os.environ.get("PYTEST_CURRENT_TEST"):
            logger.debug(
                "PYTEST_CURRENT_TEST set; mantendo confirmacao de remocao ativa."
            )
        try:
            return self._ask_yes_no(title=title, message=message)
        except Exception as exc:
            logger.warning(
                "Falha ao solicitar confirmacao para remocao de filtro '%s': %s",
                item_text,
                exc,
            )
            raise

    def _clear_general_search_state(self) -> None:
        self._abort_active_filtering("clear_general_search_state")
        self._set_search_text_across_tabs("")
        self._pending_search_display = None
        self._active_filter_search_display = ""
        self._active_filter_search_request_id = None
        self._df_last_search_filtered = self.df_completo

    def _sync_exclude_ste_checkbox_state(self, checked: bool) -> None:
        checked_bool = bool(checked)
        checkbox = getattr(self, "exclude_ste_checkbox", None)
        if checkbox is None:
            return
        try:
            self._set_checked_without_signal(
                checkbox,
                checked_bool,
                log_context="exclude_ste_checkbox_summary",
            )
        except Exception as exc:
            logger.debug(
                "Falha ao sincronizar checkbox exclude_ste principal no resumo: %s",
                exc,
            )

    def _remove_filters_summary_actions(
        self, item_text: str, actions: list[SummaryAction]
    ) -> None:
        if not actions:
            return
        if not self._confirm_filter_summary_item_removal(item_text):
            return
        self._safe_store_last_filter_state("remove_filters_summary_item")
        plan = build_summary_removal_plan(actions)
        self._apply_filters_summary_direct_resets(plan)
        self._apply_filters_summary_advanced_removals(plan)
        self._apply_filters_summary_column_removals(plan)
        self._finish_filters_summary_removal(plan)

    def _apply_filters_summary_direct_resets(self, plan: SummaryRemovalPlan) -> None:
        if plan.clear_dedicated_or_text:
            self._dedicated_or_text = ""
        if plan.clear_exclude_terminal_statuses:
            self._exclude_ste_sca = False
            self._sync_exclude_ste_checkbox_state(False)

    def _apply_filters_summary_advanced_removals(
        self, plan: SummaryRemovalPlan
    ) -> None:
        for key in plan.removal_advanced_keys:
            self._advanced_filters.pop(key, None)
        if plan.removal_advanced_keys:
            self._advanced_filters_active = bool(
                self._has_active_advanced_filters(self._advanced_filters)
            )
            plan.sync_advanced_ui = True
            plan.refresh_needed = True
            if any(
                key.startswith("setor_executor") or key == "macro_filter"
                for key in plan.removal_advanced_keys
            ):
                plan.sync_quick_combo = True

    def _apply_filters_summary_column_removals(self, plan: SummaryRemovalPlan) -> None:
        if not plan.columns_to_reset:
            return
        for column_name in plan.columns_to_reset:
            if column_name in self._active_column_filters or column_name in getattr(
                self, "_column_to_or_group", {}
            ):
                self._clear_filters_summary_column_or_group(column_name)
        self._build_column_filters_panel()
        plan.refresh_needed = True

    def _clear_filters_summary_column_or_group(self, column_name: str) -> None:
        if column_name in self._column_to_or_group:
            group = self._column_to_or_group.get(column_name)
            if group:
                group["values"] = []
                for member in group.get("columns", []):
                    self._active_column_filters[member] = ""
            return
        self._active_column_filters[column_name] = ""

    def _finish_filters_summary_removal(self, plan: SummaryRemovalPlan) -> None:
        if plan.clear_general_search_state:
            self._clear_general_search_state()
        if plan.sync_advanced_ui:
            self._sync_advanced_filter_ui()
        if plan.refresh_needed or plan.clear_general_search_state:
            self._mark_profile_as_custom()
            self._refresh_after_filter_change()
        else:
            self._update_filters_summary()
        if plan.clear_general_search_state and not self._has_any_active_filters():
            self._set_filtered_count_status()
        self._sync_clear_filter_button_state()
        if plan.sync_quick_combo:
            sync_quick_setor = getattr(
                self, "_sync_quick_setor_executor_combo_from_filters", None
            )
            if callable(sync_quick_setor):
                sync_quick_setor()

    def _on_filters_summary_item_clicked(
        self, item_text: str, actions: list[SummaryAction]
    ) -> None:
        self._remove_filters_summary_actions(item_text, actions)

    def _format_column_filter_display_value(
        self, raw: str, *, column: str | None = None
    ) -> str:
        """Normaliza um valor de filtro de coluna para exibicao consistente."""
        return format_column_filter_display_value(
            raw,
            column=column,
            alias_map=self._get_filter_alias_map(),
        )

    def _get_filter_alias_map(self) -> dict:
        """Carrega mapeamento opcional de aliases para exibicao de filtros de coluna.
        Estrutura esperada (config/filter_aliases.json):
        {
          "_global": { "ste": "STE", "sca": "SCA" },
          "setor_executor": {}
        }
        Chaves de lookup aceitam minusculas (casefold). Retorna {} se ausente/erro.
        """
        if hasattr(self, "_filter_alias_map") and isinstance(
            self._filter_alias_map, dict
        ):
            return self._filter_alias_map
        self._filter_alias_map = load_filter_alias_map_once()
        return self._filter_alias_map

    def _update_col_filter_indicator(self):
        if not hasattr(self, "col_filter_indicator"):
            return
        try:
            if not self.col_filter_indicator.isVisible():
                return
        except Exception as exc:
            logger.debug(
                "Falha ao consultar visibilidade do indicador de filtro de coluna: %s",
                exc,
            )
        column_active = any(
            str(value).strip()
            for value in (getattr(self, "_active_column_filters", {}) or {}).values()
        )
        if column_active:
            txt = "Filtros por coluna: Ativo"
        else:
            txt = "Filtros por coluna: Nao ativo"
        try:
            self.col_filter_indicator.setText(txt)
        except Exception as exc:
            logger.debug(
                "Falha ao atualizar texto do indicador de filtro de coluna: %s", exc
            )

    def show_filter_help(self):
        if FilterHelpDialog is None:
            logger.debug("FilterHelpDialog indisponivel; ajuda nao sera exibida.")
            return
        try:
            dlg = FilterHelpDialog(_qt_parent(self))
            dlg.exec()
        except Exception as exc:
            logger.debug("Falha ao abrir dialogo de ajuda de filtros: %s", exc)

    def _collect_profile_columns(self, profiles: dict) -> list:
        cols = []
        seen = set()

        def add_col(col_name) -> None:
            if isinstance(col_name, str) and col_name not in seen:
                seen.add(col_name)
                cols.append(col_name)

        for profile_data in profiles.values():
            if isinstance(profile_data, dict):
                all_section = (
                    profile_data.get("all")
                    if isinstance(profile_data.get("all"), dict)
                    else None
                )
                if all_section:
                    for col_name in all_section.keys():
                        add_col(col_name)
                any_section = (
                    profile_data.get("any")
                    if isinstance(profile_data.get("any"), list)
                    else None
                )
                if any_section:
                    for group in any_section:
                        columns = (
                            group.get("columns") if isinstance(group, dict) else None
                        )
                        if isinstance(columns, list):
                            for col_name in columns:
                                add_col(col_name)
                # Suporte legado: simples dict coluna->valor
                if not (all_section or any_section):
                    for col_name in profile_data.keys():
                        add_col(col_name)
            elif isinstance(profile_data, list):
                for col_name in profile_data:
                    add_col(col_name)
        return cols

    def _initialize_profile_filter_placeholders(self):
        """Garante que colunas monitoradas tenham entradas nas estruturas de filtro."""
        if not isinstance(self._active_column_filters, OrderedDict):
            self._active_column_filters = OrderedDict(self._active_column_filters or {})
        for col in self._profile_columns:
            if col not in self._active_column_filters:
                self._active_column_filters[col] = ""
        # Garante linhas iniciais úteis mesmo sem perfil aplicado
        for default_col in self._column_filter_default_columns():
            if default_col not in self._active_column_filters:
                self._active_column_filters[default_col] = ""

    def _column_filter_default_columns(self) -> tuple[str, ...]:
        """Colunas padrao sempre visiveis no painel de filtros por coluna."""
        return (
            "descricao_ssa",
            "setor_emissor",
            "setor_executor",
            "descricao_execucao",
            "semana_cadastro",
            "semana_programada",
            "semana_executada",
        )

    def _reset_or_groups(self):
        self._column_or_groups = []
        self._column_to_or_group = {}

    def _register_or_group(self, columns: list, values: list):
        normalized_columns = [c for c in (columns or []) if isinstance(c, str) and c]
        normalized_values = [str(v).strip() for v in (values or []) if str(v).strip()]
        if not normalized_columns:
            return None
        group = {
            "columns": normalized_columns,
            "values": normalized_values,
        }
        self._column_or_groups.append(group)
        for col in normalized_columns:
            self._column_to_or_group[col] = group
        return group

    def _sync_or_group_values(self, column: str, text: str):
        """Sync shared values for columns evaluated by the column-filter OR engine."""
        group = self._column_to_or_group.get(column)
        if not group:
            return
        normalized = str(text or "").strip()
        normalized = _WHITESPACE_RE.sub(" ", normalized).strip()
        tokens = [
            token.strip()
            for token in _FILTER_VALUE_SEPARATOR_RE.split(normalized)
            if token.strip()
        ]
        if not tokens:
            group["values"] = []
            for col in group["columns"]:
                self._active_column_filters[col] = ""
            return
        group["values"] = tokens
        # Store internally as comma-separated list (OR logic)
        common_text = ", ".join(tokens)
        for col in group["columns"]:
            self._active_column_filters[col] = common_text
        self._filter_cache_context_dirty = True

    def _apply_column_filters(self, df: pd.DataFrame) -> pd.DataFrame:
        """Aplica todos os filtros por coluna com as mesmas regras de busca (prefixo ^, sufixo $, =exato, ~regex, !neg)."""
        state = self._get_column_filter_runtime_state()
        filtered = apply_column_filters_with_state(
            state,
            df,
            getattr(self, "_active_column_filters", {}) or {},
            getattr(self, "_column_to_or_group", {}) or {},
            revision=getattr(self, "_data_revision", 0),
            build_column_mask=self._build_column_mask,
        )
        self._store_column_filter_runtime_state(state)
        return filtered

    def _get_column_filter_runtime_state(self) -> ColumnFilterRuntimeState:
        return ColumnFilterRuntimeState(
            ColumnFilterCaches(
                revision=getattr(self, "_column_filter_series_cache_revision", None),
                series=getattr(self, "_column_filter_series_cache", {}) or {},
                casefold=getattr(self, "_column_filter_casefold_cache", {}) or {},
                mask=getattr(self, "_column_filter_mask_cache", {}) or {},
                date_scope=getattr(self, "_column_filter_date_cache_scope", None),
                date_parsed=getattr(self, "_column_filter_date_parsed_cache", {}) or {},
                date=getattr(self, "_column_filter_date_cache", {}) or {},
                frame_tokens=getattr(self, "_column_filter_frame_tokens", {}) or {},
            )
        )

    def _store_column_filter_runtime_state(
        self, state: ColumnFilterRuntimeState
    ) -> None:
        caches = state.caches
        self._column_filter_series_cache_revision = caches.revision
        self._column_filter_series_cache = caches.series
        self._column_filter_casefold_cache = caches.casefold
        self._column_filter_mask_cache = caches.mask
        self._column_filter_date_cache_scope = caches.date_scope
        self._column_filter_date_parsed_cache = caches.date_parsed
        self._column_filter_date_cache = caches.date
        self._column_filter_frame_tokens = caches.frame_tokens

    def _should_match_date_display_filter(self, col: str, raw_filter: str) -> bool:
        return should_match_date_filter(
            col, raw_filter, getattr(self, "df_completo", None)
        )

    def _is_column_filter_date_display_column(self, col: str) -> bool:
        return is_column_filter_date_display_column(
            col, getattr(self, "df_completo", None)
        )

    def _get_column_filter_date_display_columns(
        self, df: pd.DataFrame
    ) -> frozenset[str]:
        return get_column_filter_date_display_columns(df)

    def _get_column_filter_date_display_series(
        self, df: pd.DataFrame, col: str
    ) -> pd.Series | None:
        state = self._get_column_filter_runtime_state()
        series = get_date_display_series(
            state,
            df,
            col,
            revision=getattr(self, "_data_revision", 0),
        )
        self._store_column_filter_runtime_state(state)
        return series

    def _try_hide_column_filter_line(self, column_name: str) -> None:
        current_value = ""
        try:
            current_value = str(
                (getattr(self, "_active_column_filters", {}) or {}).get(column_name, "")
            ).strip()
        except Exception:
            current_value = ""
        if current_value:
            hidden_lines = getattr(self, "_hidden_column_filter_lines", None)
            if isinstance(hidden_lines, set) and column_name in hidden_lines:
                hidden_lines.discard(column_name)
                self._pending_filter_focus = column_name
                self._build_column_filters_panel()
                return
            try:
                display_name = self._resolve_column_display_name(column_name)
            except Exception:
                display_name = str(column_name)
            try:
                self.status_label.setText(
                    f"Status: Limpe o filtro de {display_name} antes de ocultar/exibir a linha."
                )
            except Exception as exc:
                logger.debug(
                    "Falha ao atualizar status ao bloquear ocultacao da coluna %s: %s",
                    column_name,
                    exc,
                )
            try:
                input_widget = getattr(self, "_column_filter_inputs", {}).get(
                    column_name
                )
                if input_widget is not None:
                    input_widget.setFocus()
                    input_widget.selectAll()
            except Exception as exc:
                logger.debug(
                    "Falha ao focar filtro bloqueado da coluna %s: %s", column_name, exc
                )
            return

        hidden_lines = getattr(self, "_hidden_column_filter_lines", None)
        if not isinstance(hidden_lines, set):
            hidden_lines = set()
            self._hidden_column_filter_lines = hidden_lines
        hidden_lines.add(column_name)
        self._build_column_filters_panel()

    def _filter_refresh_has_general_search(self) -> bool:
        active_search_display = str(
            getattr(self, "_active_filter_search_display", "") or ""
        ).strip()
        if not active_search_display:
            return False
        try:
            live_search_texts = [
                str(widget.text() or "").strip()
                for widget in self._iter_search_inputs()
            ]
        except Exception as exc:
            logger.debug("Falha ao ler campos de busca no refresh de filtros: %s", exc)
            return True
        if not live_search_texts:
            return True
        return all(text == active_search_display for text in live_search_texts)

    def _filter_refresh_base_dataframe(self, has_general_search: bool) -> pd.DataFrame:
        if has_general_search:
            return self._df_last_search_filtered
        return self.df_completo

    def _filter_refresh_flags(self) -> tuple[bool, bool, bool]:
        try:
            column_filters = getattr(self, "_active_column_filters", {}) or {}
            has_column_filters = any(
                str(value).strip() for value in column_filters.values()
            )
        except Exception:
            has_column_filters = False
        return (
            has_column_filters,
            bool(getattr(self, "_advanced_filters_active", False)),
            bool(getattr(self, "_exclude_ste_sca", False)),
        )

    def _compute_has_post_search_filters(
        self,
        *,
        has_column_filters: bool,
        has_advanced_filters: bool,
        has_excluded_terminal_status: bool,
        for_sort_defer: bool,
    ) -> bool:
        """Return whether post-search filter stages should affect the current gate.

        Contract:
        - for_sort_defer=True (on_filter_finished pre-sort gate): includes terminal
          exclusion because refresh applies STE/SCA without column/advanced stages;
          pre-sort must defer when terminal-only is active.
        - for_sort_defer=False (refresh pipeline gate): excludes terminal exclusion;
          terminal is handled separately via has_excluded_terminal_status in the
          pipeline cache path (see _apply_filter_refresh_filters_and_update_cache).
        """
        base = has_column_filters or has_advanced_filters
        if for_sort_defer:
            return base or has_excluded_terminal_status
        return base

    def _apply_filter_refresh_filters_and_update_cache(
        self,
        filtered: pd.DataFrame,
        *,
        has_post_search_filters: bool,
        has_excluded_terminal_status: bool,
        measure_timing,
    ) -> pd.DataFrame:
        cache_key = None
        if has_post_search_filters or has_excluded_terminal_status:
            cache_context = self._build_filter_cache_context()
            cache_key = (
                getattr(self, "_data_revision", None),
                getattr(self, "_data_uuid", None),
                id(getattr(self, "df_completo", None)),
                id(filtered),
                len(filtered) if isinstance(filtered, pd.DataFrame) else -1,
                tuple(filtered.columns) if isinstance(filtered, pd.DataFrame) else (),
                cache_context,
                bool(has_excluded_terminal_status),
            )
        filtered, cache_update = apply_filter_refresh_pipeline(
            filtered,
            has_post_search_filters=has_post_search_filters,
            has_excluded_terminal_status=has_excluded_terminal_status,
            cache_key=cache_key,
            cached=getattr(self, "_filter_refresh_result_cache", None),
            apply_advanced_filters=getattr(self, "_apply_advanced_filters", None),
            apply_column_filters=self._apply_column_filters,
            measure_timing=measure_timing,
        )
        if cache_update is not None:
            self._filter_refresh_result_cache = cache_update
        return filtered

    def _sort_filter_refresh_result(
        self,
        filtered: pd.DataFrame,
        *,
        has_general_search: bool,
        has_column_filters: bool,
        has_advanced_filters: bool,
        has_excluded_terminal_status: bool,
        measure_timing,
    ) -> pd.DataFrame:
        can_reuse_preprocessed_load_result = (
            not has_general_search
            and not has_column_filters
            and not has_advanced_filters
            and not has_excluded_terminal_status
            and filtered is self.df_completo
            and bool(getattr(filtered, "attrs", {}).get("ssa_preprocessed_for_gui"))
        )
        can_reuse_general_search_sorted_result = (
            has_general_search
            and not has_column_filters
            and not has_advanced_filters
            and not has_excluded_terminal_status
            and filtered is self._df_last_search_filtered
            and bool(getattr(filtered, "attrs", {}).get("ssa_sorted_for_display"))
        )
        if (
            not can_reuse_preprocessed_load_result
            and not can_reuse_general_search_sorted_result
            and not filtered.empty
            and "numero_ssa" in filtered.columns
        ):
            try:
                return measure_timing(
                    "sort", lambda: filtered.sort_values("numero_ssa", ascending=False)
                )
            except Exception as exc:
                logger.warning(
                    "Falha ao ordenar numero_ssa no refresh de filtros: %s", exc
                )
        return filtered

    def _bump_filter_refresh_revision(self) -> None:
        try:
            if hasattr(self, "_bump_data_revision"):
                self._bump_data_revision("filter_refresh")
        except Exception as exc:
            logger.debug(
                "Falha ao atualizar data revision em refresh de filtros: %s", exc
            )
        try:
            if hasattr(self, "_ensure_data_revision"):
                self._ensure_data_revision()
        except Exception as exc:
            logger.debug(
                "Falha ao garantir data revision no refresh de filtros: %s", exc
            )

    def _render_filter_refresh_page(self, current_details_ssa, measure_timing) -> None:
        try:
            current = max(
                1, min(self.paginator.current_page, self.paginator.total_pages)
            )
            preserve_current_details = False
            current_details_series = None
            if current_details_ssa and not self.df_exibido.empty:
                try:
                    current_slice = self.paginator.get_current_slice()
                    if (
                        current_slice is not None
                        and not current_slice.empty
                        and "numero_ssa" in current_slice.columns
                    ):
                        current_norm = ssa_gui_details._normalize_ssa_relation_value(
                            current_details_ssa
                        )
                        if current_norm:
                            slice_norm = ssa_gui_details._normalize_ssa_series(
                                self, current_slice["numero_ssa"]
                            )
                            preserve_current_details = bool(
                                slice_norm.eq(current_norm).any()
                            )
                    if preserve_current_details:
                        current_details_series = ssa_gui_details._get_series_for_ssa(
                            self, current_details_ssa
                        )
                except Exception as exc:
                    logger.debug(
                        "Falha ao avaliar preservacao de detalhes no refresh de filtros: %s",
                        exc,
                    )
                    preserve_current_details = False
                    current_details_series = None

            if preserve_current_details and current_details_series is not None:
                measure_timing(
                    "render",
                    lambda: self.display_current_page(current, update_details=False),
                )
                try:
                    ssa_gui_details._update_details_from_series(
                        self, current_details_series
                    )
                except Exception as exc:
                    logger.debug(
                        "Falha ao restaurar detalhes apos refresh de filtros: %s", exc
                    )
            else:
                measure_timing(
                    "render",
                    lambda: self.display_current_page(current, update_details=False),
                )
                self._schedule_filter_refresh_details_update()
        except Exception as exc:
            logger.debug(
                "Falha ao renderizar pagina atual diretamente no refresh; usando fallback: %s",
                exc,
            )
            measure_timing(
                "render",
                lambda cp=max(
                    1,
                    min(
                        getattr(self.paginator, "current_page", 1),
                        getattr(self.paginator, "total_pages", 1),
                    ),
                ): self.display_current_page(cp, update_details=False),
            )
            self._schedule_filter_refresh_details_update()

    def _schedule_filter_refresh_details_update(self) -> None:
        expected_revision = int(getattr(self, "_data_revision", 0) or 0)
        self_ref = weakref.ref(self)

        def update_details_if_current() -> None:
            window = self_ref()
            if window is None:
                return
            try:
                if int(getattr(window, "_data_revision", 0) or 0) != expected_revision:
                    return
                table = getattr(window, "table_widget", None)
                row_count = int(table.rowCount()) if table is not None else 0
                series = window._get_series_from_row(0) if row_count > 0 else None
                ssa_gui_details._update_details_from_series(window, series)
            except Exception as exc:
                logger.debug(
                    "Falha ao atualizar detalhes apos refresh de filtros: %s", exc
                )

        try:
            QTimer.singleShot(0, update_details_if_current)
        except Exception as exc:
            logger.debug(
                "Falha ao agendar atualizacao de detalhes apos refresh: %s", exc
            )
            update_details_if_current()

    def _finish_filter_refresh_ui(self, measure_timing) -> None:
        measure_timing("status_indicator", self._update_col_filter_indicator)
        try:
            measure_timing("summary", self._update_filters_summary)
        except Exception as exc:
            logger.debug("Falha ao atualizar resumo de filtros no refresh: %s", exc)
        self._sync_clear_filter_button_state()
        try:
            measure_timing("status", self._set_filtered_count_status)
        except Exception as exc:
            logger.debug(
                "Falha ao atualizar status de total filtrado no refresh: %s", exc
            )
        try:
            sync_combo = getattr(
                self, "_sync_quick_setor_executor_combo_from_filters", None
            )
            if callable(sync_combo):
                measure_timing("sync", sync_combo)
        except Exception as exc:
            logger.debug(
                "Falha ao sincronizar combo rapido de setor executor no refresh de filtros: %s",
                exc,
            )

    def _log_filter_refresh_timings(
        self,
        *,
        refresh_started: float,
        timings: dict[str, float],
        base,
        filtered,
    ) -> None:
        total_ms = (perf_counter() - refresh_started) * 1000.0
        base_rows = len(base) if isinstance(base, pd.DataFrame) else "na"
        filtered_rows = len(filtered) if isinstance(filtered, pd.DataFrame) else "na"
        logger.debug(
            (
                "Filter refresh timings ms: total=%.2f advanced=%.2f column=%.2f "
                "exclude=%.2f sort=%.2f paginate=%.2f render=%.2f status_indicator=%.2f "
                "summary=%.2f status=%.2f sync=%.2f rows=%s->%s"
            ),
            total_ms,
            timings["advanced"],
            timings["column"],
            timings["exclude"],
            timings["sort"],
            timings["paginate"],
            timings["render"],
            timings["status_indicator"],
            timings["summary"],
            timings["status"],
            timings["sync"],
            base_rows,
            filtered_rows,
        )

    def _refresh_after_filter_change(self, *, commit_pending_search: bool = True):
        """Reaplica filtros de coluna, atualiza tabela e indicadores."""
        timer = FilterRefreshTimer()
        current_details_ssa = getattr(self, "_details_current_ssa", None)
        active_search_display = str(
            getattr(self, "_active_filter_search_display", "") or ""
        ).strip()
        current_search_text = self._current_general_search_text()
        if commit_pending_search and current_search_text != active_search_display:
            self.initiate_filtering()
            return
        has_general_search = (
            self._filter_refresh_has_general_search()
            if commit_pending_search
            else bool(active_search_display)
        )
        base = self._filter_refresh_base_dataframe(has_general_search)
        filtered = base
        (
            has_column_filters,
            has_advanced_filters,
            has_excluded_terminal_status,
        ) = self._filter_refresh_flags()
        has_post_search_filters = self._compute_has_post_search_filters(
            has_column_filters=has_column_filters,
            has_advanced_filters=has_advanced_filters,
            has_excluded_terminal_status=has_excluded_terminal_status,
            for_sort_defer=False,
        )
        try:
            filtered = self._apply_filter_refresh_filters_and_update_cache(
                filtered,
                has_post_search_filters=has_post_search_filters,
                has_excluded_terminal_status=has_excluded_terminal_status,
                measure_timing=timer.measure,
            )
        except AdvancedFilterMaskError as exc:
            from gui.ssa.gui_filters_advanced_ui import (
                _sync_status_after_advanced_filter_failure,
            )

            logger.warning(
                "Falha ao aplicar filtros avancados no refresh pos-busca: %s",
                exc,
            )
            _sync_status_after_advanced_filter_failure(self)
            return
        filtered = self._sort_filter_refresh_result(
            filtered,
            has_general_search=has_general_search,
            has_column_filters=has_column_filters,
            has_advanced_filters=has_advanced_filters,
            has_excluded_terminal_status=has_excluded_terminal_status,
            measure_timing=timer.measure,
        )
        self.df_exibido = filtered
        self._bump_filter_refresh_revision()
        timer.measure(
            "paginate", lambda: self.paginator.set_dataframe(self.df_exibido)
        )
        self._render_filter_refresh_page(current_details_ssa, timer.measure)
        self._finish_filter_refresh_ui(timer.measure)
        self._log_filter_refresh_timings(
            refresh_started=timer.started,
            timings=timer.timings,
            base=base,
            filtered=filtered,
        )

    def _build_filter_cache_context(self) -> str:
        """Gera contexto deterministico do estado efetivo de filtros para o cache."""
        raw_column_filters = getattr(self, "_active_column_filters", {}) or {}
        raw_advanced_filters = getattr(self, "_advanced_filters", None) or {}
        advanced_filters_active = bool(
            getattr(self, "_advanced_filters_active", False)
        )
        exclude_terminal_statuses = bool(getattr(self, "_exclude_ste_sca", False))
        try:
            cache_parts = build_filter_cache_parts(
                raw_column_filters,
                raw_advanced_filters,
                advanced_filters_active=advanced_filters_active,
                exclude_terminal_statuses=exclude_terminal_statuses,
            )
            current_fingerprint = cache_parts.fingerprint()
            if (
                not bool(getattr(self, "_filter_cache_context_dirty", True))
                and current_fingerprint
                == getattr(self, "_filter_cache_context_fingerprint", None)
            ):
                cached_context = getattr(self, "_filter_cache_context_value", None)
                if isinstance(cached_context, str):
                    return cached_context
            context = build_filter_cache_context_from_parts(cache_parts)
            self._filter_cache_context_value = context
            self._filter_cache_context_dirty = False
            self._filter_cache_context_fingerprint = current_fingerprint
            return context
        except Exception as exc:
            logger.debug("Falha ao montar contexto de cache para FilterWorker: %s", exc)
            return ""

    def _sanitize_hidden_column_filter_lines(
        self,
        hidden_lines: Any,
        active_filters: Any | None = None,
    ) -> set[str]:
        """Impede reidratacao de filtro ativo invisivel durante restore."""
        hidden_set = set(hidden_lines or set())
        current_filters = (
            active_filters
            if isinstance(active_filters, dict)
            else (getattr(self, "_active_column_filters", {}) or {})
        )
        active_filter_lookup = {
            str(column_name): str(value).strip()
            for column_name, value in current_filters.items()
        }
        return {
            str(column_name)
            for column_name in hidden_set
            if not active_filter_lookup.get(str(column_name), "")
        }

    def _snapshot_filter_state(
        self,
        *,
        search_text_override: str | None = None,
        pending_search_display_override: str | None = None,
    ) -> dict:
        return search_undo_controller.snapshot_filter_state(
            self,
            search_text_override=search_text_override,
            pending_search_display_override=pending_search_display_override,
        )

    def _filter_state_signature(
        self,
        *,
        search_text_override: str | None = None,
        pending_search_display_override: str | None = None,
        state: dict | None = None,
    ) -> tuple:
        return search_undo_controller.filter_state_signature(
            self,
            search_text_override=search_text_override,
            pending_search_display_override=pending_search_display_override,
            state=state,
        )

    def _store_last_filter_state(
        self,
        *,
        search_text_override: str | None = None,
        pending_search_display_override: str | None = None,
    ) -> None:
        search_undo_controller.store_last_filter_state(
            self,
            search_text_override=search_text_override,
            pending_search_display_override=pending_search_display_override,
        )

    def _restore_filter_search_state(self, state: dict) -> str:
        return search_undo_controller.restore_filter_search_state(self, state)

    def _restore_filter_column_state(self, state: dict) -> None:
        search_undo_controller.restore_filter_column_state(self, state)

    def _restore_filter_advanced_state(self, state: dict) -> None:
        search_undo_controller.restore_filter_advanced_state(self, state)

    def _restore_filter_profile_state(self, state: dict) -> None:
        search_undo_controller.restore_filter_profile_state(self, state)

    def _render_restored_filter_state(self, restored_search_text: str) -> None:
        search_undo_controller.render_restored_filter_state(
            self,
            restored_search_text,
        )

    def _restore_last_filter_state(
        self,
        state: dict | None = None,
        *,
        consume_undo: bool = True,
    ) -> None:
        search_undo_controller.restore_last_filter_state(
            self,
            state,
            consume_undo=consume_undo,
        )

    def _update_undo_button_state(self) -> None:
        search_undo_controller.update_undo_button_state(self)

    def _apply_search_display(self):
        display_text = getattr(self, "_pending_search_display", None)
        if display_text is None:
            return

        if self._sync_search_inputs(
            display_text,
            skip_if_any_focused=True,
            log_context="apply_search_display",
        ):
            self._pending_search_display = None

    def _mark_profile_as_custom(self):
        """Marca o perfil atual como personalizado quando filtros divergem."""
        if getattr(self, "_profile_lock", False):
            return
        if not filter_profile_is_custom(
            current_filter_profile=getattr(self, "current_filter_profile", None),
            filter_profiles=getattr(self, "filter_profiles", None),
            profile_base_filters=getattr(self, "_profile_base_filters", None),
            active_column_filters=getattr(self, "_active_column_filters", None),
            column_to_or_group=getattr(self, "_column_to_or_group", None),
            column_or_groups=getattr(self, "_column_or_groups", None),
            exclude_ste_sca=bool(getattr(self, "_exclude_ste_sca", False)),
        ):
            return
        self.current_filter_profile = None
        self._profile_base_filters = {}
        selector = getattr(self, "profile_selector", None)
        if selector is not None:
            idx = selector.findData(None)
            if idx >= 0 and selector.currentIndex() != idx:
                self._profile_lock = True
                try:
                    selector.setCurrentIndex(idx)
                finally:
                    self._profile_lock = False

    def _apply_filter_profile(self, profile_name, update_selector=True, refresh=True):
        """Aplica filtros pre-configurados de setor."""
        if not profile_name or profile_name not in self.filter_profiles:
            fallback = normalize_inline_executor_emissor_profile(profile_name)
            if fallback.columns:
                self._apply_normalized_filter_profile(
                    profile_name=None,
                    normalized=fallback,
                    update_selector=False,
                    refresh=refresh,
                    base_profile_name=None,
                )
            return

        normalized = normalize_named_filter_profile(
            self.filter_profiles.get(profile_name) or {}
        )
        self._apply_normalized_filter_profile(
            profile_name=profile_name,
            normalized=normalized,
            update_selector=update_selector,
            refresh=refresh,
            base_profile_name=profile_name,
        )

    def _apply_normalized_filter_profile(
        self,
        *,
        profile_name,
        normalized: NormalizedFilterProfile,
        update_selector: bool,
        refresh: bool,
        base_profile_name,
    ) -> None:
        normalized_columns = OrderedDict(normalized.columns)
        normalized_groups = []
        self._reset_or_groups()
        for group in normalized.or_groups:
            registered = self._register_or_group(
                list(group.columns),
                list(group.values),
            )
            if not registered:
                continue
            display_values = ", ".join(registered["values"])
            if display_values:
                for col in registered["columns"]:
                    normalized_columns[col] = display_values
            normalized_groups.append(
                {
                    "columns": tuple(registered["columns"]),
                    "values": tuple(registered["values"]),
                }
            )
        self._ensure_profile_columns(normalized.profile_columns)

        self._profile_lock = True
        try:
            self.current_filter_profile = profile_name
            new_filters = OrderedDict()
            for col in self._profile_columns:
                new_filters[col] = ""
            for col, text in normalized_columns.items():
                new_filters[col] = text
            for group in self._column_or_groups:
                group_text = ", ".join(group.get("values", []))
                if not group_text:
                    continue
                for col in group.get("columns", []):
                    new_filters[col] = group_text
            self._active_column_filters = new_filters
            self._profile_base_filters = {
                "columns": {
                    col: new_filters.get(col, "").strip() for col in new_filters
                },
                "or_groups": normalized_groups,
                "exclude_ste_sca": bool(self._exclude_ste_sca),
            }
            if update_selector and base_profile_name is not None:
                self._select_filter_profile(base_profile_name)
        finally:
            self._profile_lock = False
        self._build_column_filters_panel()
        if refresh:
            self._refresh_after_filter_change()

    def _ensure_profile_columns(self, columns: tuple[str, ...]) -> None:
        for column_name in columns:
            if column_name not in self._profile_columns:
                self._profile_columns.append(column_name)

    def _select_filter_profile(self, profile_name) -> None:
        if profile_name is None:
            return
        selector = getattr(self, "profile_selector", None)
        if selector is None:
            return
        idx = selector.findData(profile_name)
        if idx >= 0 and selector.currentIndex() != idx:
            selector.setCurrentIndex(idx)

    def _apply_initial_filter_profile(self):
        """Seleciona e aplica o perfil inicial definido em configuração."""
        selector = getattr(self, "profile_selector", None)
        if selector is None:
            return
        initial_profile = (
            self.default_filter_profile
            if self.default_filter_profile in self.filter_profiles
            else None
        )
        if not initial_profile and self.filter_profiles:
            initial_profile = next(iter(self.filter_profiles.keys()))
        if initial_profile:
            self._apply_filter_profile(
                initial_profile, update_selector=True, refresh=False
            )
        else:
            idx = selector.findData(None)
            if idx >= 0:
                self._profile_lock = True
                try:
                    selector.setCurrentIndex(idx)
                finally:
                    self._profile_lock = False
        self._build_column_filters_panel()
        if (
            isinstance(getattr(self, "df_completo", None), pd.DataFrame)
            and not self.df_completo.empty
        ):
            self._refresh_after_filter_change()

    def _build_column_mask(
        self,
        series: pd.Series,
        raw: str,
        *,
        casefolded_series: pd.Series | None = None,
    ) -> pd.Series:
        return build_column_mask(
            series,
            raw,
            default_mode=self._get_default_filter_mode(),
            casefolded_series=casefolded_series,
        )

    # --- Helpers: Busca Geral com suporte a OR/AND amigável ---

    def _prepare_search_chunks(self, text: str) -> list[str]:
        # General search keeps comma-separated terms in one chunk; parse_search_terms
        # applies the cumulative quick-search contract. Column filters use a
        # separate parser where commas mean alternatives within that column.
        if not text:
            return []
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
        except Exception as exc:
            logger.warning(
                "Falha inesperada ao iniciar filtro via atalho filter_data: %s", exc
            )

    def load_persistent_filters(self):
        """Carrega filtros persistentes salvos."""
        self._get_persistent_filter_ui_controller().load()

    def _get_persistent_filter_ui_controller(self) -> PersistentFilterUiController:
        controller = getattr(self, "_persistent_filter_ui_controller", None)
        if not isinstance(controller, PersistentFilterUiController):
            controller = PersistentFilterUiController(
                self,
                copy_filter_mapping=_copy_filter_mapping,
                saved_filters_path_factory=get_gui_saved_filters_path,
            )
            self._persistent_filter_ui_controller = controller
        return controller

    def _save_persistent_filters_file(self) -> bool:
        return self._get_persistent_filter_ui_controller().save_file()

    def _invalidate_persistent_filter_index(self) -> None:
        self._get_persistent_filter_ui_controller().invalidate_index()

    def _get_persistent_filter_index(self):
        return self._get_persistent_filter_ui_controller().index()

    def save_current_filter(self):  # skipcq: PY-R1000
        """Salva o estado atual de filtros como persistente."""
        self._get_persistent_filter_ui_controller().save_current()

    def update_filter_tags(self):
        """Atualiza as tags visuais dos filtros persistentes."""
        self._get_persistent_filter_ui_controller().update_tags()

    def apply_persistent_filter(self, filter_data):
        """Aplica um filtro persistente."""
        self._get_persistent_filter_ui_controller().apply(filter_data)
