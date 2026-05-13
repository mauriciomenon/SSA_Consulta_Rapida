# gui/mixins/filter_gui_ssa_mixin.py
# Mixin containing all filter-related methods for SSAMainWindow

"""
FilterGUISSAMixin: Mixin para metodos de filtragem.

Extraido de gui_ssa.py para reduzir tamanho do arquivo.
Padrao de nomenclatura: funcao_pai_mixin.py
"""

# Imports necessarios
import copy
import json
import os
import re
from collections import OrderedDict
from collections.abc import Callable
from time import perf_counter
from typing import TYPE_CHECKING, Any, Optional, cast

import pandas as pd
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
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
    from gui.cache import FilterCache
except ImportError:
    FilterCache = cast(Any, None)

try:
    from gui.widgets import FilterHelpDialog
except ImportError:
    FilterHelpDialog = cast(Any, None)

# Imports do core
from core.app_logic import FILTER_SEARCH_CACHE_ATTR, FILTER_SEARCH_TOKEN_ATTR
from core.app_logic import filter_dataframe, parse_search_terms
from core.config_manager import DEFAULT_DISPLAY_MAPPINGS, atomic_write_json_file
from gui.gui_config import COMPATIBILITY_NULL_UI_COLUMNS, get_gui_main_preferences_path

# Imports de gui helpers
from gui.helpers.formatting_helpers import (
    format_search_display,
    normalize_chunk_for_parse,
)
from gui.ssa import gui_details as ssa_gui_details
from gui.ssa.filter_status_manager import FilterStatusManager, FilterStatusPayload
from shared.date_utils import parse_datetime_series_mixed
from utils.robust_logging import get_robust_logger

# Imports de utils
from utils.themes import get_theme_roles

# Module logger
logger = get_robust_logger().get_logger(__name__, "gui")
_FILTER_ALIAS_MAP_CACHE: dict[str, Any] | None = None
_FILTER_ALIAS_MAP_CACHE_SIGNATURE: tuple[str, int | None] | None = None


def get_gui_saved_filters_path() -> str:
    config_dir = os.path.dirname(get_gui_main_preferences_path())
    return os.path.join(config_dir, "gui_saved_filters.json")
_NESTED_QUANTIFIER_RE = re.compile(r"\((?:[^()]*[+*][^()]*)\)\s*[+*{]")
_HEAVY_QUANTIFIER_CHAIN_RE = re.compile(r"(?:[+*]|\{[^}]*\}){3,}")
_REGEX_META_CHAR_RE = re.compile(r"[*+?{}|()[\]]")
_EXCLUDED_TERMINAL_STATUSES = frozenset({"SCA", "SES", "STE"})
_EXCLUDED_TERMINAL_SUMMARY = "situacao!=SCA/SES/STE"
_CLEAR_FILTER_HARD_RESET_CLICK_TARGET = 3
_CLEAR_FILTER_HARD_RESET_WINDOW_SEC = 3.0
_GUI_GENERAL_SEARCH_PRIORITY_COLUMNS = (
    "numero_ssa",
    "situacao",
    "derivada_de",
    "localizacao_codigo",
    "descricao_localizacao",
    "equipamento",
    "descricao_ssa",
    "descricao_execucao",
    "setor_emissor",
    "setor_executor",
    "solicitante",
    "responsavel_solicitante",
    "responsavel_programacao",
    "responsavel_execucao",
    "responsavel_emissor",
    "servico_origem",
    "sistema_origem",
    "arquivo_origem",
    "justificativa",
    "anomalia",
    "situacao_espera",
    "situacao_reprogramacao",
    "situacao_de_desvio",
    "atividade_especial",
    "destino",
    "origem",
    "numero_ssa_relacionada_1",
    "numero_ssa_relacionada_2",
    "numero_ssa_relacionada_3",
    "setor_emissor_relacionado_1",
    "setor_emissor_relacionado_2",
    "setor_executor_relacionado_1",
    "setor_executor_relacionado_2",
    "situacao_relacionada_1",
    "situacao_relacionada_2",
    "relacao",
    "grau_prioridade",
    "grau_prioridade_emissao",
    "grau_prioridade_planejamento",
    "prioridade_emissao",
    "prioridade_planejamento",
    "semana_cadastro",
    "semana_programada",
    "semana_executada",
)
_GUI_GENERAL_SEARCH_EXCLUDED_COLUMNS = frozenset(
    {
        "id",
        "data_cadastro",
        "data_planilha",
        "execucao_simples",
        "prazo_limite",
        "prazo_limite_str",
        "status_execucao_prazo",
        "tempo_disponivel",
        "data_limite",
        "tempo_excedido",
        "desde",
        "tempo_total",
        "desde_1",
        "total_tempo_tpe_planejado",
        "total_tempo_tex_planejado",
        "total_tempo_tpo_planejado",
        "total_horas_programadas",
        "total_tempo_tpe_executada",
        "num_reprogramacoes",
        "execucao_parcial",
        "registros_espera",
        "num_reprobaciones",
        "numero_desvios",
        "ate",
        "total_tempo_tex_executada",
        "parciais",
        "situacao_da_parcial",
        "ate_1",
        "ate_2",
        "desde_2",
        "total_tempo_tpo_executada",
        "equipamento_retirado",
        "sn_retirado",
        "equipamento_instalado",
        "sn_instalado",
        "sn_extra",
        "desativacao_da_localizacao",
        "instalacao_estimada",
        "executado",
        "concluido",
        "data_inicio_programada",
        "data_programacao",
        "data_inicio_reprogramada",
        "data_reprogramacao",
        "total_de_reprogramacoes",
        "data_arquivo_origem",
        "data_cadastro_str",
    }
)
_GUI_GENERAL_SEARCH_AUTO_EXCLUDE_PREFIXES = (
    "_",
    "data_",
    "tempo_",
    "total_",
    "sn_",
)
_GUI_GENERAL_SEARCH_AUTO_EXCLUDE_SUFFIXES = (
    "_ts",
    "_timestamp",
    "_str",
)
_ADVANCED_FILTER_VISUAL_COLUMN_MAP = {
    "setor_executor": ("setor_executor",),
    "setor_executor_exclude_values": ("setor_executor",),
    "setor_emissor": ("setor_emissor",),
    "setor_emissor_exclude_values": ("setor_emissor",),
    "divisao": ("divisao",),
    "divisao_exclude_values": ("divisao",),
    "situacao": ("situacao",),
    "situacao_exclude_values": ("situacao",),
    "solicitante": ("solicitante", "responsavel_solicitante"),
    "solicitante_exclude_values": ("solicitante", "responsavel_solicitante"),
    "responsavel_programacao": ("responsavel_programacao",),
    "responsavel_programacao_exclude_values": ("responsavel_programacao",),
    "responsavel_execucao": ("responsavel_execucao",),
    "responsavel_execucao_exclude_values": ("responsavel_execucao",),
    "prioridade_emissao_values": ("prioridade_emissao", "grau_prioridade_emissao"),
    "prioridade_emissao_exclude_values": (
        "prioridade_emissao",
        "grau_prioridade_emissao",
    ),
    "prioridade_planejamento_values": (
        "prioridade_planejamento",
        "grau_prioridade_planejamento",
    ),
    "prioridade_planejamento_exclude_values": (
        "prioridade_planejamento",
        "grau_prioridade_planejamento",
    ),
    "ano_emissao": ("data_cadastro",),
    "ano_emissao_values": ("data_cadastro",),
    "ano_emissao_exclude_values": ("data_cadastro",),
    "ano_execucao": ("data_programada",),
    "ano_execucao_values": ("data_programada",),
    "ano_execucao_exclude_values": ("data_programada",),
    "semana_emissao_inicio": ("semana_cadastro",),
    "semana_emissao_fim": ("semana_cadastro",),
    "semana_execucao_inicio": ("semana_programada",),
    "semana_execucao_fim": ("semana_programada",),
    "derivada_has": ("derivada_de",),
    "derivada_all_ste": ("derivada_de",),
    "derivada_is": ("derivada_de",),
}

SummaryAction = dict[str, Any]
SummaryEntry = dict[str, Any]


def _is_gui_general_search_auto_excluded(column_name: str) -> bool:
    normalized_name = str(column_name or "").strip()
    if not normalized_name:
        return True
    if normalized_name in _GUI_GENERAL_SEARCH_EXCLUDED_COLUMNS:
        return True
    if normalized_name.startswith("semana_") or normalized_name.startswith(
        "grau_prioridade"
    ):
        return False
    if normalized_name.startswith("prioridade_"):
        return False
    for prefix in _GUI_GENERAL_SEARCH_AUTO_EXCLUDE_PREFIXES:
        if normalized_name.startswith(prefix):
            return True
    for suffix in _GUI_GENERAL_SEARCH_AUTO_EXCLUDE_SUFFIXES:
        if normalized_name.endswith(suffix):
            return True
    return False


def _is_gui_general_search_auto_includable(series: pd.Series) -> bool:
    return bool(
        pd.api.types.is_string_dtype(series)
        or pd.api.types.is_object_dtype(series)
        or pd.api.types.is_categorical_dtype(series)
    )


def build_gui_general_search_columns(df: pd.DataFrame | None) -> list[str]:
    """
    Build the GUI-owned general search contract from the current DataFrame.

    The GUI keeps an explicit ordered base list for core business columns and
    then appends additional textual columns that are eligible by rule. Date/time,
    totals, timers, serials, cache fields, and other technical columns stay out
    of the free-text search by default.
    """
    if not isinstance(df, pd.DataFrame) or df.empty and len(df.columns) == 0:
        return []

    non_null_columns: set[str] | None = None
    try:
        non_null_attr = df.attrs.get("ssa_non_null_cols")
        if isinstance(non_null_attr, (list, tuple, set, frozenset)):
            non_null_columns = {str(col) for col in non_null_attr if str(col)}
    except Exception as exc:
        logger.debug(
            "Falha ao ler attrs de colunas nao nulas para busca geral: %s", exc
        )

    selected_columns: list[str] = []
    seen_columns: set[str] = set()

    for column_name in _GUI_GENERAL_SEARCH_PRIORITY_COLUMNS:
        if non_null_columns is not None and column_name not in non_null_columns:
            continue
        if column_name in df.columns and column_name not in seen_columns:
            selected_columns.append(column_name)
            seen_columns.add(column_name)

    for column_name in df.columns:
        if column_name in seen_columns:
            continue
        if non_null_columns is not None and column_name not in non_null_columns:
            continue
        if _is_gui_general_search_auto_excluded(column_name):
            continue
        series = df[column_name]
        if _is_gui_general_search_auto_includable(series):
            selected_columns.append(column_name)
            seen_columns.add(column_name)

    return selected_columns


def _append_unique_text(target: list[str], value: str) -> None:
    text = str(value or "").strip()
    if not text or text in target:
        return
    target.append(text)


def _summary_week_range(start: Any, end: Any) -> str | None:
    if start is None and end is None:
        return None
    if start is None:
        return f"<= {end}"
    if end is None:
        return f">= {start}"
    return f"{start}-{end}"


def _merge_summary_actions(
    target: dict[str, SummaryEntry],
    *,
    text: str,
    actions: list[SummaryAction],
) -> None:
    normalized_text = str(text or "").strip()
    if not normalized_text:
        return
    entry = target.get(normalized_text)
    if entry is None:
        target[normalized_text] = {"text": normalized_text, "actions": list(actions)}
        return
    existing_actions = entry.setdefault("actions", [])
    seen_signatures = {
        json.dumps(action, sort_keys=True, ensure_ascii=True, default=str)
        for action in existing_actions
        if isinstance(action, dict)
    }
    for action in actions:
        if not isinstance(action, dict):
            continue
        signature = json.dumps(action, sort_keys=True, ensure_ascii=True, default=str)
        if signature in seen_signatures:
            continue
        existing_actions.append(action)
        seen_signatures.add(signature)


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


# Retencao global defensiva para workers de filtro que sobreviverem ao ciclo da janela.
GLOBAL_RETIRED_FILTER_WORKERS = []
MAX_GLOBAL_RETIRED_FILTER_WORKERS = 64


class FilterGUISSAMixin:
    """
    Mixin containing all filter-related methods.

    Methods extracted from SSAMainWindow to improve code organization.
    """

    if TYPE_CHECKING:

        def __getattr__(self, name: str) -> Any: ...

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
                logger.warning(
                    "Falha ao salvar historico de filtros (%s): %s", reason, exc
                )
            else:
                logger.warning("Falha ao salvar historico de filtros: %s", exc)

    def _iter_search_inputs(self):
        """Itera por todos os campos de busca das abas sem duplicar referências."""
        seen = set()
        try:
            current = getattr(self, "search_input", None)
            if current is not None:
                seen.add(id(current))
                yield current
        except Exception as exc:
            logger.debug("Falha ao obter campo de busca principal: %s", exc)

        tab_contexts = getattr(self, "_tab_contexts", None)
        if not isinstance(tab_contexts, list):
            return
        for ctx in tab_contexts:
            if not isinstance(ctx, dict):
                continue
            widget = ctx.get("search_input")
            if widget is None:
                continue
            widget_id = id(widget)
            if widget_id in seen:
                continue
            seen.add(widget_id)
            yield widget

    def _get_live_search_inputs_snapshot(self) -> list[Any]:
        widgets: list[Any] = []
        for widget in self._iter_search_inputs():
            if not _is_search_widget_valid(widget):
                continue
            try:
                widget.objectName()
            except RuntimeError:
                continue
            except Exception as exc:
                logger.debug(
                    "Falha ao validar widget de busca ao montar snapshot: %s", exc
                )
            widgets.append(widget)
        return widgets

    def _set_search_text_across_tabs(self, text: str) -> None:
        """Aplica o mesmo texto em todos os campos de busca para evitar divergência entre abas."""
        normalized_text = str(text or "")
        for widget in self._get_live_search_inputs_snapshot():
            blocked = False
            try:
                widget.blockSignals(True)
                blocked = True
                widget.setText(normalized_text)
            except RuntimeError as exc:
                logger.debug(
                    "Widget de busca invalido durante sync global entre abas: %s", exc
                )
            finally:
                if blocked:
                    try:
                        widget.blockSignals(False)
                    except RuntimeError:
                        pass
                    except Exception as exc:
                        logger.debug(
                            "Falha ao reativar sinais do campo de busca sincronizado: %s",
                            exc,
                        )

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
                return any(_has_value(item) for item in value)
            return bool(str(value).strip())

        for key, mapped_columns in _ADVANCED_FILTER_VISUAL_COLUMN_MAP.items():
            if not _has_value(adv.get(key)):
                continue
            columns.update(mapped_columns)

        return columns

    def _iter_clear_filter_buttons(self):
        seen_ids = set()
        direct_button = getattr(self, "clear_filter_button", None)
        if direct_button is not None:
            seen_ids.add(id(direct_button))
            yield direct_button
        tab_contexts = getattr(self, "_tab_contexts", None)
        if not isinstance(tab_contexts, list):
            return
        for ctx in tab_contexts:
            if not isinstance(ctx, dict):
                continue
            button = ctx.get("clear_filter_button")
            if button is None:
                continue
            button_id = id(button)
            if button_id in seen_ids:
                continue
            seen_ids.add(button_id)
            yield button

    def _set_clear_filter_buttons_enabled(self, enabled: bool) -> None:
        target_state = bool(enabled)
        for button in self._iter_clear_filter_buttons():
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
        seen_ids = set()
        direct_button = getattr(self, "undo_filter_btn", None)
        if direct_button is not None:
            seen_ids.add(id(direct_button))
            yield direct_button
        tab_contexts = getattr(self, "_tab_contexts", None)
        if not isinstance(tab_contexts, list):
            return
        for ctx in tab_contexts:
            if not isinstance(ctx, dict):
                continue
            button = ctx.get("undo_filter_btn")
            if button is None:
                continue
            button_id = id(button)
            if button_id in seen_ids:
                continue
            seen_ids.add(button_id)
            yield button

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
        try:
            progress_bar = getattr(self, "progress_bar", None)
            if progress_bar is not None:
                progress_bar.setVisible(False)
        except Exception as exc:
            logger.debug(
                "Falha ao ocultar progress bar em estado idle de filtro: %s", exc
            )
        for btn_attr in ("load_button", "search_button"):
            try:
                button = getattr(self, btn_attr, None)
                if button is not None:
                    button.setEnabled(True)
            except Exception as exc:
                logger.debug(
                    "Falha ao habilitar botao %s em estado idle de filtro: %s",
                    btn_attr,
                    exc,
                )

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

    def _cancel_active_filter_worker(
        self, reason: str = "", wait_ms: int = 1500
    ) -> None:
        """Cancela worker anterior antes de iniciar uma nova filtragem assíncrona."""
        worker = getattr(self, "filter_thread", None)
        if worker is None:
            return
        try:
            self._cleanup_filter_worker(worker, wait_ms=wait_ms)
        except Exception as exc:
            logger.debug(
                "Falha ao cancelar worker ativo (%s): %s", reason or "sem_motivo", exc
            )
        finally:
            if getattr(self, "filter_thread", None) is worker:
                self.filter_thread = None
        if reason:
            logger.debug("Worker anterior cancelado (%s)", reason)

    def _on_general_search_apply_clicked(self, tab_kind: str) -> None:
        logger.debug("Acao aplicar busca geral acionada (tab_kind=%s)", tab_kind)
        self.initiate_filtering()

    def _on_general_search_clear_clicked(self, tab_kind: str) -> None:
        logger.debug("Acao limpar busca geral acionada (tab_kind=%s)", tab_kind)
        self.clear_filter()
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
            FILTER_SEARCH_TOKEN_ATTR,
            FILTER_SEARCH_CACHE_ATTR,
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

    def _reset_repeated_clear_click_tracking(self) -> None:
        self._clear_filter_click_count = 0
        self._clear_filter_last_click_ts = 0.0

    def _register_repeated_clear_click(self) -> bool:
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
        if not self._register_repeated_clear_click():
            return
        if os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get(
            "SSA_NON_INTERACTIVE"
        ):
            logger.debug(
                "Confirmacao de hard reset suprimida em ambiente nao interativo."
            )
            return
        buttons = getattr(QMessageBox, "StandardButton", None)
        try:
            if buttons is not None:
                reply = QMessageBox.question(
                    _qt_parent(self),
                    "Limpar Filtros",
                    "Voce clicou varias vezes em limpar filtros. Deseja resetar todos os filtros?",
                    buttons.Yes | buttons.No,
                    buttons.No,
                )
                accepted = reply == buttons.Yes
            else:
                reply = QMessageBox.question(
                    _qt_parent(self),
                    "Limpar Filtros",
                    "Voce clicou varias vezes em limpar filtros. Deseja resetar todos os filtros?",
                )
                accepted = reply == getattr(QMessageBox, "Yes", reply)
        except Exception as exc:
            logger.debug(
                "Falha ao exibir confirmacao de hard reset apos cliques repetidos: %s",
                exc,
            )
            accepted = False
        if accepted:
            self._hard_reset_filters_state()

    def initiate_filtering(self):
        if self.df_completo.empty:
            QMessageBox.information(
                _qt_parent(self), "Aviso", "Nenhum dado carregado para filtrar."
            )
            return

        self._safe_store_last_filter_state("initiate_filtering")
        try:
            self._debounce_timer.stop()
        except Exception as exc:
            logger.debug("Falha ao parar debounce antes de iniciar filtragem: %s", exc)
        request_id = self._invalidate_active_filter_request("initiate_filtering")

        search_text = self.search_input.text().strip()
        raw_chunks = self._split_search_expression(search_text) if search_text else []
        chunk_terms_lists = (
            [self._normalize_chunk_for_parse(chunk) for chunk in raw_chunks]
            if raw_chunks
            else (
                []
                if not search_text
                else [self._normalize_chunk_for_parse(search_text)]
            )
        )
        # remove empty chunk lists
        chunk_terms_lists = [terms for terms in chunk_terms_lists if terms]
        unique_chunk_terms_lists = []
        seen_chunk_terms = set()
        for terms in chunk_terms_lists:
            chunk_key = tuple(str(term) for term in terms)
            if chunk_key in seen_chunk_terms:
                continue
            seen_chunk_terms.add(chunk_key)
            unique_chunk_terms_lists.append(list(terms))

        self._sync_clear_filter_button_state()

        if chunk_terms_lists:
            display_text = self._format_search_display(chunk_terms_lists)
        else:
            display_text = search_text if search_text else ""
        filter_source_candidate = self.df_completo
        try:
            last_search_filtered = getattr(self, "_df_last_search_filtered", None)
            column_filters = getattr(self, "_active_column_filters", {}) or {}
            has_column_filters = any(
                str(filter_value).strip() for filter_value in column_filters.values()
            )
            previous_search_display = str(
                getattr(self, "_active_filter_search_display", "") or ""
            ).strip()
            previous_terms = (
                self._normalize_chunk_for_parse(previous_search_display)
                if previous_search_display
                else []
            )
            current_terms = chunk_terms_lists[0] if chunk_terms_lists else []
            has_active_worker = getattr(self, "filter_thread", None) is not None
            if (
                isinstance(last_search_filtered, pd.DataFrame)
                and list(last_search_filtered.columns)
                and previous_terms
                and current_terms
                and not getattr(self, "_advanced_filters_active", False)
                and not has_column_filters
                and not getattr(self, "_exclude_ste_sca", False)
                and not has_active_worker
            ):
                remaining_current_terms = [
                    str(term).strip().casefold()
                    for term in current_terms
                    if str(term).strip()
                ]
                refinement_ok = True
                for previous_term in previous_terms:
                    normalized_previous = str(previous_term).strip()
                    if not normalized_previous:
                        continue
                    previous_key = normalized_previous.casefold()
                    exact_only = normalized_previous[:1] in {"!", "=", "~"}
                    matched_index = None
                    for index, current_key in enumerate(remaining_current_terms):
                        if current_key == previous_key or (
                            not exact_only and current_key.startswith(previous_key)
                        ):
                            matched_index = index
                            break
                    if matched_index is None:
                        refinement_ok = False
                        break
                    remaining_current_terms.pop(matched_index)
                if refinement_ok:
                    filter_source_candidate = last_search_filtered
        except Exception as exc:
            logger.debug(
                "Falha ao avaliar refinamento seguro da busca; usando df_completo: %s",
                exc,
            )
        self._pending_search_display = display_text
        self._active_filter_search_display = display_text
        self._active_filter_search_request_id = request_id

        self.status_label.setText("Status: Filtrando dados...")
        self.progress_bar.setVisible(True)
        self.load_button.setEnabled(False)
        self.search_button.setEnabled(False)

        # Descobre default_mode nas configuracoes JSON (OTIMIZACAO: usando cache)
        if not hasattr(self, "_cached_default_mode"):
            from gui.gui_config import GUI_MAIN_PREFERENCES

            gui_settings = GUI_MAIN_PREFERENCES.get("gui_settings", {})
            self._cached_default_mode = gui_settings.get(
                "default_filter_mode", "contains"
            )
        default_mode = self._cached_default_mode
        filter_source = self._get_filter_source_dataframe(filter_source_candidate)
        general_search_columns = build_gui_general_search_columns(filter_source)

        # Modo síncrono (sem QThread) opcional para testes
        if getattr(self, "_sync_filtering", False):
            try:
                if unique_chunk_terms_lists:
                    frames = []
                    for terms in unique_chunk_terms_lists:
                        parsed = parse_search_terms(terms, default_mode=default_mode)
                        frames.append(
                            filter_dataframe(
                                filter_source,
                                parsed,
                                search_columns=general_search_columns,
                            )
                        )
                    if frames:
                        if len(frames) == 1:
                            df_filtrado = frames[0]
                        else:
                            merged_frames = pd.concat(
                                frames, axis=0, ignore_index=False
                            )
                            df_filtrado = merged_frames.loc[
                                ~merged_frames.index.duplicated(keep="first")
                            ].reset_index(drop=True)
                    else:
                        df_filtrado = filter_source.copy(deep=False)
                else:
                    df_filtrado = filter_source.copy(deep=False)
                self.on_filter_finished(df_filtrado, request_id=request_id)
                # Em modo síncrono, garanta larguras válidas imediatamente após aplicar o filtro
                try:
                    self._ensure_nonzero_column_widths()
                except Exception as exc:
                    logger.debug(
                        "Falha ao reforcar largura minima no filtro sincrono: %s", exc
                    )
                try:
                    if (
                        self.table_widget.columnCount() > 1
                        and self.table_widget.columnWidth(1) == 0
                    ):
                        self.table_widget.setColumnWidth(1, 80)
                except Exception as exc:
                    logger.debug(
                        "Falha ao ajustar largura da coluna principal no filtro sincrono: %s",
                        exc,
                    )
            except Exception as e:  # noqa: BLE001
                self.on_filter_error(
                    f"Erro ao filtrar dados: {e}", request_id=request_id
                )
            finally:
                self.on_filter_finished_cleanup(None, request_id=request_id)
            return

        self._cancel_active_filter_worker("initiate_filtering_new_request", wait_ms=0)

        # Fallback defensivo para ambientes sem worker assíncrono disponível
        if FilterWorker is None:
            logger.warning(
                "FilterWorker indisponivel; aplicando filtro em modo sincrono"
            )
            try:
                if unique_chunk_terms_lists:
                    frames = []
                    for terms in unique_chunk_terms_lists:
                        parsed = parse_search_terms(terms, default_mode=default_mode)
                        frames.append(
                            filter_dataframe(
                                filter_source,
                                parsed,
                                search_columns=general_search_columns,
                            )
                        )
                    if frames:
                        if len(frames) == 1:
                            df_filtrado = frames[0]
                        else:
                            merged_frames = pd.concat(
                                frames, axis=0, ignore_index=False
                            )
                            df_filtrado = merged_frames.loc[
                                ~merged_frames.index.duplicated(keep="first")
                            ].reset_index(drop=True)
                    else:
                        df_filtrado = filter_source.copy(deep=False)
                else:
                    df_filtrado = filter_source.copy(deep=False)
                self.on_filter_finished(df_filtrado, request_id=request_id)
            except Exception as e:  # noqa: BLE001
                self.on_filter_error(
                    f"Erro ao filtrar dados: {e}", request_id=request_id
                )
            finally:
                self.on_filter_finished_cleanup(None, request_id=request_id)
            return

        # Inicia a thread de filtragem (modo padrao assincrono)
        filter_cache_context = self._build_filter_cache_context()
        worker = FilterWorker(
            filter_source,
            unique_chunk_terms_lists,
            search_columns=general_search_columns,
            default_mode=default_mode,
            cache_context=filter_cache_context,
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
            self.on_filter_error(
                "Falha ao iniciar filtro: conexoes de sinais indisponiveis.",
                request_id=request_id,
            )
            self.on_filter_finished_cleanup(worker, request_id=request_id)
            return
        # Garante destruição segura do objeto thread após terminar
        if not _connect_filter_signal(
            worker.finished,
            worker.deleteLater,
            label="filter_worker.finished.deleteLater",
        ):
            logger.debug("Falha ao conectar deleteLater no worker de filtro atual.")
        worker.start()

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
        try:
            if not df_filtrado.empty and "numero_ssa" in df_filtrado.columns:
                df_filtrado.sort_values("numero_ssa", ascending=False, inplace=True)
                df_filtrado.attrs["ssa_sorted_for_display"] = True
        except Exception as exc:
            logger.warning(
                "Falha ao ordenar numero_ssa no fim do filtro geral: %s", exc
            )
        # Atualiza baseline do resultado da busca global
        self._df_last_search_filtered = df_filtrado
        # OTIMIZACAO: Sinaliza que larguras precisam ser recalculadas para novo dataset
        self._widths_computed_for_df_hash = None
        self._refresh_after_filter_change()
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
        if not search_text:
            search_text = str(
                getattr(self, "_pending_search_display", "") or ""
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
        table_widget = getattr(self, "table_widget", None)
        table_widget_valid = _is_search_widget_valid(table_widget)
        if not table_widget_valid:
            logger.debug(
                "table_widget indisponivel no fim de on_filter_finished; pulando ajustes de largura."
            )
            return
        # Reforça reaplicação de larguras após busca para evitar colunas zeradas em headless/CI
        try:
            self._ensure_nonzero_column_widths()
        except Exception as exc:
            logger.debug("Falha ao reforcar largura minima apos filtro: %s", exc)
        # Recalcula e aplica larguras com base no slice atual exibido para garantir consistência imediata
        try:
            if hasattr(self, "df_para_tabela") and not self.df_para_tabela.empty:
                self._compute_gui_column_widths(self.df_para_tabela)
                self._apply_computed_widths_only()
        except Exception as exc:
            logger.debug("Falha ao recalcular/aplicar larguras apos filtro: %s", exc)
        # Garantia específica: coluna 1 (primeira após '#') nunca deve ficar com largura 0
        try:
            if (
                self.table_widget.columnCount() > 1
                and self.table_widget.columnWidth(1) == 0
            ):
                self.table_widget.setColumnWidth(1, 80)
        except Exception as exc:
            logger.debug(
                "Falha ao aplicar largura de seguranca na coluna principal: %s", exc
            )
        # Agenda um ajuste seguro pós-loop de eventos
        try:
            QTimer.singleShot(0, lambda: self._set_safe_width_for_col_index(1, 80))
        except Exception as exc:
            logger.debug(
                "Falha ao agendar ajuste deferido de largura da coluna principal: %s",
                exc,
            )
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
        pending_jump = getattr(self, "_pending_jump_to_ssa", None)
        if (
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
        self.status_label.setText("Status: Erro ao aplicar filtro.")

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
            default_mode = getattr(self, "_cached_default_mode", None)
            if not default_mode:
                from gui.gui_config import GUI_MAIN_PREFERENCES

                gui_settings = GUI_MAIN_PREFERENCES.get("gui_settings", {})
                default_mode = gui_settings.get("default_filter_mode", "contains")
                self._cached_default_mode = default_mode
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

    def _retain_filter_worker_until_finished(self, worker) -> None:
        if worker is None:
            return
        retired = getattr(self, "_retired_filter_workers", None)
        if retired is None:
            retired = []
            self._retired_filter_workers = retired
        if worker in retired:
            return
        retired.append(worker)
        if worker not in GLOBAL_RETIRED_FILTER_WORKERS:
            GLOBAL_RETIRED_FILTER_WORKERS.append(worker)
        try:
            self._prune_retired_filter_workers()
        except Exception as exc:
            logger.debug(
                "Falha ao podar lista de workers de filtro aposentados: %s", exc
            )

        def _release_worker_ref(w=worker):
            try:
                if w in self._retired_filter_workers:
                    self._retired_filter_workers.remove(w)
            except Exception as exc:
                logger.debug(
                    "Falha ao remover worker da lista local de aposentados: %s", exc
                )
            try:
                if w in GLOBAL_RETIRED_FILTER_WORKERS:
                    GLOBAL_RETIRED_FILTER_WORKERS.remove(w)
            except Exception as exc:
                logger.debug(
                    "Falha ao remover worker da lista global de aposentados: %s", exc
                )
            try:
                self._prune_retired_filter_workers()
            except Exception as exc:
                logger.debug(
                    "Falha ao podar lista de workers de filtro apos release: %s", exc
                )

        if not _connect_filter_signal(
            worker.finished,
            _release_worker_ref,
            label="filter_worker.finished.release",
        ):
            logger.debug(
                "Falha ao conectar release de worker finalizado; liberando referencia imediato."
            )
            _release_worker_ref()
        if not _connect_filter_signal(
            worker.finished,
            worker.deleteLater,
            label="filter_worker.finished.deleteLater",
        ):
            logger.debug("Falha ao conectar deleteLater do worker de filtro.")

    def _is_filter_worker_running(self, worker) -> bool:
        if worker is None:
            return False
        is_running = False
        try:
            if hasattr(worker, "isRunning"):
                is_running = bool(worker.isRunning())
        except Exception as exc:
            logger.debug("Falha ao verificar estado do worker de filtro: %s", exc)
            return False
        return is_running

    def _prune_retired_filter_workers(self) -> None:
        retired_local = list(getattr(self, "_retired_filter_workers", []) or [])
        if retired_local:
            self._retired_filter_workers = [
                w for w in retired_local if self._is_filter_worker_running(w)
            ]
        else:
            self._retired_filter_workers = []

        running_global = [
            w
            for w in GLOBAL_RETIRED_FILTER_WORKERS
            if self._is_filter_worker_running(w)
        ]
        if len(running_global) > MAX_GLOBAL_RETIRED_FILTER_WORKERS:
            running_global = running_global[-MAX_GLOBAL_RETIRED_FILTER_WORKERS:]
        GLOBAL_RETIRED_FILTER_WORKERS[:] = running_global

    def _cleanup_filter_worker(self, worker, wait_ms: int = 1500) -> bool:
        if worker is None:
            return True
        try:
            try:
                worker.filter_finished.disconnect()
            except Exception as exc:
                logger.debug(
                    "Falha ao desconectar filter_finished do worker de filtro: %s", exc
                )
            try:
                worker.error_occurred.disconnect()
            except Exception as exc:
                logger.debug(
                    "Falha ao desconectar error_occurred do worker de filtro: %s", exc
                )
            try:
                worker.finished.disconnect()
            except Exception as exc:
                logger.debug(
                    "Falha ao desconectar finished do worker de filtro: %s", exc
                )
            still_running = False
            try:
                if hasattr(worker, "cancel"):
                    worker.cancel()
                elif hasattr(worker, "requestInterruption"):
                    worker.requestInterruption()
                if hasattr(worker, "isRunning") and worker.isRunning():
                    worker.quit()
                    if int(wait_ms or 0) > 0:
                        worker.wait(int(wait_ms))
                still_running = bool(
                    hasattr(worker, "isRunning") and worker.isRunning()
                )
            except Exception as exc:
                logger.warning(
                    "Falha ao solicitar encerramento do worker de filtro: %s", exc
                )
                still_running = True
            if still_running:
                self._retain_filter_worker_until_finished(worker)
                return False
            try:
                worker.deleteLater()
            except Exception as exc:
                logger.debug("Falha ao chamar deleteLater no worker de filtro: %s", exc)
            try:
                self._prune_retired_filter_workers()
            except Exception as exc:
                logger.debug("Falha ao podar workers de filtro apos cleanup: %s", exc)
        except Exception as exc:
            logger.warning("Falha durante cleanup do worker de filtro: %s", exc)
            return False
        return True

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
            if worker is not None and getattr(self, "filter_thread", None) is worker:
                self.filter_thread = None
            try:
                self._prune_retired_filter_workers()
            except Exception as exc:
                logger.debug(
                    "Falha ao podar workers de filtro em cleanup obsoleto: %s", exc
                )
            return
        # Debug trace para investigação de estabilidade em testes headless
        try:
            progress_bar = getattr(self, "progress_bar", None)
            if progress_bar is not None:
                try:
                    progress_bar.setVisible(False)
                except Exception as exc:
                    logger.debug(
                        "Falha ao ocultar progress bar em cleanup de filtro: %s", exc
                    )
            for btn_attr in ("load_button", "search_button"):
                btn = getattr(self, btn_attr, None)
                if btn is not None:
                    try:
                        btn.setEnabled(True)
                    except Exception as exc:
                        logger.debug(
                            "Falha ao habilitar botao %s em cleanup de filtro: %s",
                            btn_attr,
                            exc,
                        )
            target_worker = (
                worker if worker is not None else getattr(self, "filter_thread", None)
            )
            self._cleanup_filter_worker(target_worker)
            if (
                target_worker is not None
                and getattr(self, "filter_thread", None) is target_worker
            ):
                self.filter_thread = None
            try:
                self._prune_retired_filter_workers()
            except Exception as exc:
                logger.debug("Falha ao podar workers de filtro em finalizacao: %s", exc)
        except Exception as exc:
            # Nunca propagar exceção daqui; log mínimo opcional futuro
            logger.warning("Falha inesperada no cleanup final de filtro: %s", exc)
            self.filter_thread = None

    def clear_filter(self):
        """Limpa apenas a busca geral e reaplica filtros ativos."""
        self._safe_store_last_filter_state("clear_filter")
        self._invalidate_active_filter_request("clear_filter")
        self._cancel_active_filter_worker("clear_filter", wait_ms=0)
        self._set_filter_ui_idle()
        try:
            self._debounce_timer.stop()
        except Exception as exc:
            logger.debug("Falha ao parar debounce em clear_filter: %s", exc)
        try:
            self._set_search_text_across_tabs("")
        except Exception as exc:
            logger.warning(
                "Falha ao sincronizar campos de busca no clear_filter: %s", exc
            )
            try:
                self.search_input.blockSignals(True)
                self.search_input.clear()
                self.search_input.setText("")
            finally:
                try:
                    self.search_input.blockSignals(False)
                except Exception as unblock_exc:
                    logger.debug(
                        "Falha ao reativar sinais do campo de busca apos clear_filter: %s",
                        unblock_exc,
                    )
        self._pending_search_display = None
        self._active_filter_search_display = ""
        self._active_filter_search_request_id = None
        # Nao limpa filtros avancados nem filtros de coluna aqui.
        # Esse botao limpa apenas a busca geral; limpeza global usa "_clear_all_filters_global".
        self._df_last_search_filtered = self.df_completo
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

    # --- Ordenaçção por clique no cabeçalho ---

    def _on_search_text_changed(self, _text: str):
        """Reinicia o temporizador de debounce ao digitar na busca."""
        try:
            current_widget = getattr(self, "search_input", None)
            normalized_text = str(_text or "")
            for widget in self._get_live_search_inputs_snapshot():
                if widget is current_widget:
                    continue
                blocked = False
                try:
                    widget.blockSignals(True)
                    blocked = True
                    widget.setText(normalized_text)
                except RuntimeError as exc:
                    logger.debug(
                        "Widget de busca invalido durante sincronizacao entre abas: %s",
                        exc,
                    )
                finally:
                    if blocked:
                        try:
                            widget.blockSignals(False)
                        except RuntimeError:
                            pass
                        except Exception as exc:
                            logger.debug(
                                "Falha ao reativar sinais do campo de busca sincronizado: %s",
                                exc,
                            )
        except Exception as exc:
            logger.debug("Falha ao sincronizar texto de busca entre abas: %s", exc)
        # Chamar start() novamente reinicia o QTimer automaticamente
        try:
            self._debounce_timer.start()
        except Exception as exc:
            logger.debug("Falha ao reiniciar debounce na busca: %s", exc)

    def clear_filter_cache(self):
        """Limpa o cache de filtros."""
        # Usa logger e verifica disponibilidade do FilterWorker e cache
        if FilterWorker is not None and hasattr(FilterWorker, "_cache"):
            try:
                FilterWorker._cache.clear()
                logger.info("Cache de filtros limpo")
            except Exception as e:  # pragma: no cover
                logger.debug("Falha ao limpar cache de filtros: %s", e)
        else:
            logger.debug("FilterWorker indisponivel; cache nao limpo")

    def get_filter_cache_stats(self) -> dict:
        """Retorna estatísticas do cache de filtros."""
        if (
            FilterWorker is not None
            and hasattr(FilterWorker, "_cache")
            and hasattr(FilterWorker._cache, "get_stats")
        ):
            try:
                return FilterWorker._cache.get_stats()
            except Exception:  # pragma: no cover
                return {}
        return {}

    # --- Slots e Handlers ---

    def _open_add_column_filter_menu(self):
        """Exibe menu com todas as colunas disponiveis para ativar filtros dedicados."""
        try:
            from PyQt6.QtWidgets import QMenu
        except Exception:
            return
        menu = QMenu(_qt_parent(self))
        columns = []
        candidates = []
        canonical_provider = getattr(self, "_get_canonical_available_columns", None)
        if callable(canonical_provider):
            try:
                candidates.extend(canonical_provider())
            except Exception as exc:
                logger.debug(
                    "Falha ao obter lista canonica de colunas para menu de filtros: %s",
                    exc,
                )
        candidates.extend((self._active_column_filters or {}).keys())

        seen = set()
        try:
            self._last_unmapped_alias_columns = self._find_unmapped_alias_columns(
                candidates
            )
        except Exception as exc:
            logger.debug("Falha ao mapear colunas sem alias: %s", exc)
            self._last_unmapped_alias_columns = []
        legacy_invalid_columns = {
            "Número da SSA",
            "Numero da SSA",
            "No SSA",
            "Data Cadastro",
        }
        valid_cols = []
        for col in candidates:
            if not isinstance(col, str) or not col or col == "#" or col in seen:
                continue
            if col in COMPATIBILITY_NULL_UI_COLUMNS:
                continue
            if col in legacy_invalid_columns:
                continue
            display = self._resolve_column_display_name(col)
            if str(display).strip() == "No SSA" and col != "numero_ssa":
                continue
            seen.add(col)
            valid_cols.append(col)

        pinned = []
        pinned_seen = set()
        for col in getattr(self, "_current_display_columns", []) or []:
            if col in valid_cols and col not in pinned_seen:
                pinned.append(col)
                pinned_seen.add(col)
        for col in self._active_column_filters.keys():
            if col in valid_cols and col not in pinned_seen:
                pinned.append(col)
                pinned_seen.add(col)
        remaining = [c for c in valid_cols if c not in pinned_seen]
        remaining.sort(key=lambda c: self._expand_column_alias_for_filter(c).casefold())
        ordered_cols = pinned + remaining

        label_counts = {}
        for col in ordered_cols:
            display = self._expand_column_alias_for_filter(col)
            key = str(display).strip().casefold()
            label_counts[key] = label_counts.get(key, 0) + 1
        for col in ordered_cols:
            display = self._expand_column_alias_for_filter(col)
            display_text = str(display)
            if label_counts.get(display_text.strip().casefold(), 0) > 1:
                display_text = f"{display_text} [{col}]"
            action = menu.addAction(display_text)
            if action is None:
                continue
            action.setCheckable(True)
            action.setChecked(col in self._active_column_filters)
            action.setData(col)
            columns.append(action)
        if not columns:
            menu.deleteLater()
            return
        chosen = menu.exec(
            self.add_column_filter_btn.mapToGlobal(
                self.add_column_filter_btn.rect().bottomLeft()
            )
        )
        if chosen is None:
            return
        col_name = chosen.data()
        if not col_name:
            return
        if col_name in self._active_column_filters:
            self._deactivate_column_filter(col_name)
        else:
            self._activate_column_filter(col_name)

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
        """Prefer full labels in the column-filter list when short aliases exist."""
        resolved = self._resolve_column_display_name(col)
        expanded_aliases = {
            "Exec.": "Setor executor",
            "Emis.": "Setor emissor",
            "Sit.": "Situacao",
            "Loc.": "Localizacao",
            "Prog.": "Semana programada",
            "Sem. Cad.": "Semana cadastro",
            "Prio.": "Prioridade",
            "Prio. Emissao": "Prioridade emissao",
            "Prio. Planej.": "Prioridade planejamento",
            "Resp. Prog.": "Responsavel programacao",
            "Resp. Exec.": "Responsavel execucao",
        }
        return expanded_aliases.get(resolved, resolved)

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
        # Escolhe layout de lista (compatável com versões antigas e novas)
        target_layout = None
        if hasattr(self, "col_filters_list_layout"):
            target_layout = self.col_filters_list_layout
        elif hasattr(self, "col_filters_layout"):
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
        if not hasattr(self, "_hidden_column_filter_lines"):
            self._hidden_column_filter_lines = set()

        if not self._active_column_filters:
            self._active_column_filters = OrderedDict(
                (col, "") for col in self._column_filter_default_columns()
            )

        # Keep a minimum label column aligned with "Descricao Execucao".
        # If a label is longer, current behavior still pushes the input right.
        min_label_column_width = 100
        try:
            ref_name = self._expand_column_alias_for_filter("descricao_execucao")
            ref_probe = QLabel(ref_name)
            ref_metrics = ref_probe.fontMetrics()
            ref_width = int(ref_metrics.horizontalAdvance(ref_name) + 16)
            min_label_column_width = max(100, min(260, ref_width))
        except Exception as exc:
            logger.debug(
                "Falha ao calcular largura minima de alinhamento dos labels de filtro: %s",
                exc,
            )

        for col, term in self._active_column_filters.items():
            # Pula linhas ocultas (removidas da exibição)
            if (
                hasattr(self, "_hidden_column_filter_lines")
                and col in self._hidden_column_filter_lines
            ):
                continue
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(4)
            full_name = self._expand_column_alias_for_filter(col)
            name_lbl = QLabel(full_name)
            self._column_filter_labels[col] = name_lbl
            try:
                label_metrics = name_lbl.fontMetrics()
                desired_width = int(label_metrics.horizontalAdvance(full_name) + 16)
                dynamic_width = max(90, min(260, desired_width))
                name_lbl.setMinimumWidth(max(min_label_column_width, dynamic_width))
            except Exception as exc:
                logger.debug(
                    "Falha ao ajustar largura do label do filtro de coluna %s: %s",
                    col,
                    exc,
                )
                name_lbl.setMinimumWidth(min_label_column_width)
            try:
                name_lbl.setSizePolicy(
                    QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
                )
            except Exception as exc:
                logger.debug(
                    "Falha ao aplicar size policy no label do filtro de coluna %s: %s",
                    col,
                    exc,
                )
            # Exibe 'OU' no campo (apenas visual). Internamente continuamos usando vírgulas.
            try:
                display_text = self._format_column_filter_display_value(
                    str(term), column=col
                )
            except Exception:
                display_text = str(term)
            term_box = QLineEdit(display_text)
            self._column_filter_inputs[col] = term_box
            # Placeholder sem conectivos OU/AND - OR agora e dedicado
            term_box.setPlaceholderText(
                "Separe termos por vírgulas. Modos: foo, ^pre, suf$, =exato, ~regex, !neg"
            )
            # Reduzido para garantir visibilidade dos botões em telas estreitas
            term_box.setMinimumWidth(220)
            try:
                term_box.setMinimumHeight(26)
            except Exception as exc:
                logger.debug(
                    "Falha ao aplicar altura minima no input do filtro de coluna %s: %s",
                    col,
                    exc,
                )
            try:
                term_box.setSizePolicy(
                    QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
                )
            except Exception as exc:
                logger.debug(
                    "Falha ao aplicar size policy no input do filtro de coluna %s: %s",
                    col,
                    exc,
                )
            self._apply_filter_widget_theme(name_lbl, term_box)
            # Enter aplica o filtro desta coluna
            try:
                term_box.returnPressed.connect(
                    lambda c=col, tb=term_box: _mk_apply(c, tb)()
                )
            except Exception as exc:
                logger.debug(
                    "Falha ao conectar Enter no filtro de coluna %s: %s", col, exc
                )
            # Botao Aplicar atualiza o filtro com o texto da caixa
            apply_btn = QPushButton("Aplicar")
            try:
                apply_btn.setMinimumHeight(26)
            except Exception as exc:
                logger.debug(
                    "Falha ao aplicar altura minima no botao Aplicar da coluna %s: %s",
                    col,
                    exc,
                )
            try:
                apply_btn.setSizePolicy(
                    QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
                )
            except Exception as exc:
                logger.debug(
                    "Falha ao aplicar size policy no botao Aplicar da coluna %s: %s",
                    col,
                    exc,
                )
            try:
                apply_btn.setFixedWidth(66)
            except Exception as exc:
                logger.debug(
                    "Falha ao aplicar largura fixa no botao Aplicar da coluna %s: %s",
                    col,
                    exc,
                )

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
                    self._sync_clear_filter_button_state()

                return _inner

            apply_btn.clicked.connect(_mk_apply())
            # Botao Limpar remove o valor do filtro, mas mantem a linha visivel.
            clear_btn = QPushButton("Limpar")
            try:
                clear_btn.setMinimumHeight(26)
            except Exception as exc:
                logger.debug(
                    "Falha ao aplicar altura minima no botao Limpar da coluna %s: %s",
                    col,
                    exc,
                )
            try:
                clear_btn.setSizePolicy(
                    QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
                )
            except Exception as exc:
                logger.debug(
                    "Falha ao aplicar size policy no botao Limpar da coluna %s: %s",
                    col,
                    exc,
                )
            try:
                clear_btn.setFixedWidth(66)
            except Exception as exc:
                logger.debug(
                    "Falha ao aplicar largura fixa no botao Limpar da coluna %s: %s",
                    col,
                    exc,
                )
            try:
                clear_btn.setToolTip(
                    "Limpa o valor desta coluna e reaplica os filtros."
                )
            except Exception as exc:
                logger.debug(
                    "Falha ao aplicar tooltip no botao Limpar da coluna %s: %s",
                    col,
                    exc,
                )

            def _mk_clear_value(c=col, tb=term_box):
                def _inner():
                    current_text = str(self._active_column_filters.get(c, "")).strip()
                    typed_text = str(tb.text()).strip()
                    if not current_text and not typed_text:
                        return
                    self._safe_store_last_filter_state("clear_column_filter_value")
                    self._active_column_filters[c] = ""
                    self._sync_or_group_values(c, "")
                    try:
                        tb.blockSignals(True)
                        tb.setText("")
                    finally:
                        try:
                            tb.blockSignals(False)
                        except Exception as exc:
                            logger.debug(
                                "Falha ao reativar sinais no input apos limpar coluna %s: %s",
                                c,
                                exc,
                            )
                    self._mark_profile_as_custom()
                    self._build_column_filters_panel()
                    self._refresh_after_filter_change()
                    self._sync_clear_filter_button_state()

                return _inner

            try:
                clear_btn.clicked.connect(_mk_clear_value())
            except Exception as exc:
                logger.debug(
                    "Falha ao conectar botao limpar para filtro de coluna %s: %s",
                    col,
                    exc,
                )

            # Botao para ocultar a linha da exibicao quando nao houver filtro ativo
            hide_btn = QPushButton("Ocultar")
            try:
                hide_btn.setMinimumHeight(26)
            except Exception as exc:
                logger.debug(
                    "Falha ao aplicar altura minima no botao Ocultar da coluna %s: %s",
                    col,
                    exc,
                )
            try:
                hide_btn.setSizePolicy(
                    QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
                )
            except Exception as exc:
                logger.debug(
                    "Falha ao aplicar size policy no botao Ocultar da coluna %s: %s",
                    col,
                    exc,
                )
            try:
                hide_btn.setFixedWidth(66)
            except Exception as exc:
                logger.debug(
                    "Falha ao aplicar largura fixa no botao Ocultar da coluna %s: %s",
                    col,
                    exc,
                )
            try:
                hide_btn.setToolTip(
                    "Oculta a linha somente quando o filtro da coluna estiver vazio."
                )
            except Exception as exc:
                logger.debug(
                    "Falha ao aplicar tooltip no botao Ocultar da coluna %s: %s",
                    col,
                    exc,
                )

            def _mk_remove_line(c=col):
                def _inner():
                    self._handle_hide_column_filter_line(c)

                return _inner

            try:
                hide_btn.clicked.connect(_mk_remove_line())
            except Exception as exc:
                logger.debug(
                    "Falha ao conectar botao ocultar para filtro de coluna %s: %s",
                    col,
                    exc,
                )

            row.addWidget(name_lbl)
            row.addWidget(term_box, 1)
            row.addWidget(apply_btn)
            row.addWidget(clear_btn)
            row.addWidget(hide_btn)
            # Layout order: label, input, Aplicar, Limpar, Ocultar
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
            except Exception as exc:
                logger.debug(
                    "Falha ao focar campo do filtro de coluna %s: %s", focus_col, exc
                )
        self._pending_filter_focus = None
        self._refresh_column_filter_widgets()
        # Botção limpar todos
        # Rodape centralizado (se nao houver barra fixa)
        if not hasattr(self, "clear_all_btn"):
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
        try:
            if hasattr(self, "_sync_bottom_panel_heights"):
                self._sync_bottom_panel_heights()
        except Exception as exc:
            logger.debug(
                "Falha ao sincronizar altura dos paineis inferiores apos rebuild de filtros por coluna: %s",
                exc,
            )

    def _apply_filter_widget_theme(self, label_widget=None, input_widget=None):
        theme = getattr(self, "_current_theme", "") or "dark"
        roles = get_theme_roles(theme)
        label_color = roles.get("support_text_color") or roles.get("label_color")
        if label_widget is not None:
            label_widget.setStyleSheet(f"color:{label_color};")
        if input_widget is not None:
            input_text = roles.get("input_text")
            input_bg = roles.get("input_bg")
            input_border = roles.get("input_border")
            input_focus = roles.get("input_border_focus") or roles.get("accent")
            input_placeholder = roles.get("input_placeholder")
            style = (
                f"QLineEdit {{ font-size:11px; color:{input_text}; background:{input_bg}; border:1px solid {input_border}; border-radius:4px; padding:3px 6px; }}\n"
                f"QLineEdit::placeholder {{ color:{input_placeholder}; }}\n"
                f"QLineEdit:focus {{ border:1px solid {input_focus}; }}\n"
            )
            input_widget.setStyleSheet(style)

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
        return FilterStatusManager.apply(
            payload=payload,
            filtered_status_label=getattr(self, "filtered_status_label", None),
            status_label=getattr(self, "status_label", None),
        )

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
    ) -> str:
        count_status_text, _ = self._update_filter_status_display(
            filtered_total=filtered_total,
            original_total=original_total,
            search_text=None,
            suffix="",
        )
        return count_status_text

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
                        except Exception as exc:
                            logger.debug(
                                "Falha ao reativar sinais de checkbox exclude_ste por aba: %s",
                                exc,
                            )
            elif (
                hasattr(self, "exclude_ste_checkbox")
                and self.exclude_ste_checkbox is not None
            ):
                checkbox = self.exclude_ste_checkbox
                try:
                    if checkbox.isChecked() != checked_bool:
                        checkbox.blockSignals(True)
                        checkbox.setChecked(checked_bool)
                finally:
                    try:
                        checkbox.blockSignals(False)
                    except Exception as exc:
                        logger.debug(
                            "Falha ao reativar sinais de checkbox exclude_ste principal: %s",
                            exc,
                        )
        except Exception as exc:
            logger.warning(
                "Falha ao sincronizar toggle de excluir STE/SCA entre abas: %s", exc
            )
        self._mark_profile_as_custom()
        self._refresh_after_filter_change()

    def _clear_all_filters_global(self):
        """Limpa todos os filtros: busca geral + filtros de coluna"""
        self._safe_store_last_filter_state("clear_all_filters_global")
        self._invalidate_active_filter_request("clear_all_filters_global")
        self._cancel_active_filter_worker("clear_all_filters_global", wait_ms=0)
        self._set_filter_ui_idle()
        # Limpar filtro de busca geral
        try:
            self._debounce_timer.stop()
        except Exception as exc:
            logger.debug(
                "Falha ao parar debounce principal em clear_all_filters_global: %s", exc
            )
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
            try:
                self.search_input.blockSignals(True)
                self.search_input.clear()
                self.search_input.setText("")
            finally:
                try:
                    self.search_input.blockSignals(False)
                except Exception as unblock_exc:
                    logger.debug(
                        "Falha ao reativar sinais do campo principal em clear_all_filters_global: %s",
                        unblock_exc,
                    )
        self._pending_search_display = None
        self._df_last_search_filtered = pd.DataFrame()

        # Limpar todos os filtros de coluna com o mesmo baseline padrao
        self._active_column_filters = OrderedDict(
            (col, "") for col in self._column_filter_default_columns()
        )
        self._reset_or_groups()

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
                except Exception as exc:
                    logger.debug(
                        "Falha ao limpar checkbox exclude_ste em contexto de aba: %s",
                        exc,
                    )
                finally:
                    try:
                        checkbox.blockSignals(False)
                    except Exception as exc:
                        logger.debug(
                            "Falha ao reativar sinais de checkbox exclude_ste em clear_all_filters_global: %s",
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

        # Resetar para dataset completo sem duplicar o DataFrame base
        self.df_exibido = self.df_completo
        try:
            if hasattr(self, "_bump_data_revision"):
                self._bump_data_revision("clear_all_filters")
        except Exception as exc:
            logger.debug(
                "Falha ao atualizar data revision em clear_all_filters: %s", exc
            )
        self.paginator.set_dataframe(self.df_exibido)
        self.display_current_page(1)
        # Restaura linhas ocultas e limpa Filtro OU dedicado (exibição)
        try:
            self._hidden_column_filter_lines.clear()
        except Exception:
            self._hidden_column_filter_lines = set()
        self._dedicated_or_text = ""
        self._build_column_filters_panel()
        self._update_col_filter_indicator()

        # Atualizar interface
        self._set_filtered_count_status()
        self._sync_clear_filter_button_state()

        # Atualizar resumo de filtros
        self._update_filters_summary()
        try:
            sync_combo = getattr(
                self, "_sync_quick_setor_executor_combo_from_filters", None
            )
            if callable(sync_combo):
                sync_combo()
        except Exception as exc:
            logger.debug(
                "Falha ao sincronizar combo rapido de setor executor em clear_all_filters_global: %s",
                exc,
            )

    def _hard_reset_filters_state(self):
        """Reseta agressivamente estado interno e visual dos filtros sem tocar nos botoes atuais."""
        self._reset_repeated_clear_click_tracking()
        self._invalidate_active_filter_request("hard_reset_filters_state")
        self._cancel_active_filter_worker("hard_reset_filters_state", wait_ms=0)
        self._set_filter_ui_idle()

        try:
            self._debounce_timer.stop()
        except Exception as exc:
            logger.debug(
                "Falha ao parar debounce principal em hard_reset_filters_state: %s", exc
            )
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
            try:
                self.search_input.blockSignals(True)
                self.search_input.clear()
                self.search_input.setText("")
            finally:
                try:
                    self.search_input.blockSignals(False)
                except Exception as unblock_exc:
                    logger.debug(
                        "Falha ao reativar sinais do campo principal em hard_reset_filters_state: %s",
                        unblock_exc,
                    )

        self._pending_search_display = None
        self._pending_filter_focus = None
        self._df_last_search_filtered = pd.DataFrame()
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

        tab_contexts = getattr(self, "_tab_contexts", None)
        if isinstance(tab_contexts, list):
            for ctx in tab_contexts:
                if not isinstance(ctx, dict):
                    continue
                search_input = ctx.get("search_input")
                if search_input is not None:
                    try:
                        search_input.blockSignals(True)
                        search_input.clear()
                        search_input.setText("")
                    except Exception as exc:
                        logger.debug(
                            "Falha ao limpar search_input em hard_reset_filters_state: %s",
                            exc,
                        )
                    finally:
                        try:
                            search_input.blockSignals(False)
                        except Exception as exc:
                            logger.debug(
                                "Falha ao reativar sinais de search_input em hard_reset_filters_state: %s",
                                exc,
                            )
                selector = ctx.get("profile_selector")
                checkbox = ctx.get("exclude_ste_checkbox")
                if checkbox is None:
                    try:
                        if selector is not None:
                            selector.blockSignals(True)
                            selector.setCurrentIndex(0)
                    except Exception as exc:
                        logger.debug(
                            "Falha ao limpar seletor de perfil em hard_reset_filters_state: %s",
                            exc,
                        )
                    finally:
                        try:
                            if selector is not None:
                                selector.blockSignals(False)
                        except Exception as exc:
                            logger.debug(
                                "Falha ao reativar sinais do seletor de perfil em hard_reset_filters_state: %s",
                                exc,
                            )
                    continue
                try:
                    checkbox.blockSignals(True)
                    checkbox.setChecked(False)
                except Exception as exc:
                    logger.debug(
                        "Falha ao limpar checkbox exclude_ste em hard_reset_filters_state: %s",
                        exc,
                    )
                finally:
                    try:
                        checkbox.blockSignals(False)
                    except Exception as exc:
                        logger.debug(
                            "Falha ao reativar sinais de checkbox exclude_ste em hard_reset_filters_state: %s",
                            exc,
                        )
                try:
                    if selector is not None:
                        selector.blockSignals(True)
                        selector.setCurrentIndex(0)
                except Exception as exc:
                    logger.debug(
                        "Falha ao limpar seletor de perfil em hard_reset_filters_state: %s",
                        exc,
                    )
                finally:
                    try:
                        if selector is not None:
                            selector.blockSignals(False)
                    except Exception as exc:
                        logger.debug(
                            "Falha ao reativar sinais do seletor de perfil em hard_reset_filters_state: %s",
                            exc,
                        )
        selector = getattr(self, "profile_selector", None)
        if selector is not None:
            try:
                selector.blockSignals(True)
                selector.setCurrentIndex(0)
            except Exception as exc:
                logger.debug(
                    "Falha ao limpar seletor de perfil principal em hard_reset_filters_state: %s",
                    exc,
                )
            finally:
                try:
                    selector.blockSignals(False)
                except Exception as exc:
                    logger.debug(
                        "Falha ao reativar sinais do seletor de perfil principal em hard_reset_filters_state: %s",
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

        self.df_exibido = self.df_completo
        try:
            if hasattr(self, "_bump_data_revision"):
                self._bump_data_revision("hard_reset_filters")
        except Exception as exc:
            logger.debug(
                "Falha ao atualizar data revision em hard_reset_filters_state: %s", exc
            )
        self.paginator.set_dataframe(self.df_exibido)
        self.display_current_page(1)
        self._build_column_filters_panel()
        self._update_col_filter_indicator()
        self._update_filters_summary()
        self._sync_clear_filter_button_state()
        self._update_undo_button_state()
        try:
            self.update_filter_tags()
        except Exception as exc:
            logger.debug("Falha ao atualizar tags em hard_reset_filters_state: %s", exc)
        try:
            sync_combo = getattr(
                self, "_sync_quick_setor_executor_combo_from_filters", None
            )
            if callable(sync_combo):
                sync_combo()
        except Exception as exc:
            logger.debug(
                "Falha ao sincronizar combo rapido em hard_reset_filters_state: %s", exc
            )
        self._set_filtered_count_status()
        try:
            self.status_label.setText("Status: Filtros resetados completamente.")
        except Exception as exc:
            logger.debug(
                "Falha ao atualizar status em hard_reset_filters_state: %s", exc
            )

    def _update_filters_summary(self):
        """Atualiza o resumo de filtros ativos na interface"""
        summary_entries: OrderedDict[str, SummaryEntry] = OrderedDict()

        def _display_name(col: str) -> str:
            if col == "setor_executor":
                return "Executor"
            if col == "setor_emissor":
                return "Emissor"
            if col == "descricao_ssa":
                return "Descricao da SSA"
            if col == "situacao":
                return "Situacao"
            return self._resolve_column_display_name(col)

        search_text = ""
        if hasattr(self, "search_input"):
            try:
                search_text = str(self.search_input.text() or "").strip()
            except Exception as exc:
                logger.debug(
                    "Falha ao obter busca atual para resumo de filtros: %s", exc
                )
        if search_text:
            _merge_summary_actions(
                summary_entries,
                text=f"Busca: '{search_text}'",
                actions=[{"kind": "search"}],
            )

        or_text = str(getattr(self, "_dedicated_or_text", "") or "").strip()
        if or_text:
            _merge_summary_actions(
                summary_entries,
                text=f"Filtro OU: {self._format_column_filter_display_value(or_text)}",
                actions=[{"kind": "dedicated_or"}],
            )

        active_column_filters = getattr(self, "_active_column_filters", {}) or {}
        if active_column_filters:
            for group in getattr(self, "_column_or_groups", []):
                values = list(group.get("values", []) or [])
                if not values:
                    continue
                columns = list(group.get("columns", []) or [])
                if set(columns) == {"setor_executor", "setor_emissor"}:
                    label = "Executor ou Emissor (OU)"
                else:
                    label = f"{' ou '.join(_display_name(c) for c in columns)} (OU)"
                values_txt = self._format_column_filter_display_value(", ".join(values))
                if not values_txt:
                    continue
                action_column = str(columns[0]) if columns else ""
                _merge_summary_actions(
                    summary_entries,
                    text=f"{label}: {values_txt}",
                    actions=[
                        {
                            "kind": "column_or_group",
                            "column": action_column,
                            "columns": columns,
                        }
                    ],
                )

            for col_name, filter_value in active_column_filters.items():
                if col_name in self._column_to_or_group:
                    continue
                normalized_value = self._format_column_filter_display_value(
                    str(filter_value), column=col_name
                )
                if not normalized_value:
                    continue
                _merge_summary_actions(
                    summary_entries,
                    text=f"{_display_name(col_name)}: {normalized_value}",
                    actions=[{"kind": "column", "column": str(col_name)}],
                )

        adv = getattr(self, "_advanced_filters", None) or {}
        adv_active = bool(getattr(self, "_advanced_filters_active", False))

        def _add_adv(
            label,
            values,
            op: str | None = None,
            *,
            action_keys: list[str] | None = None,
        ):
            if not values:
                return
            if isinstance(values, list):
                txt = ", ".join(str(v) for v in values if str(v).strip())
            else:
                txt = str(values).strip()
            if not txt:
                return
            if op:
                text = f"{label} {op} {txt}"
            else:
                text = f"{label}: {txt}"
            keys = [str(key) for key in (action_keys or []) if str(key).strip()]
            if not keys:
                return
            _merge_summary_actions(
                summary_entries,
                text=text,
                actions=[{"kind": "advanced_keys", "keys": keys}],
            )

        if adv_active:
            _add_adv(
                "Executor",
                adv.get("setor_executor"),
                action_keys=["setor_executor"],
            )
            _add_adv(
                "Executor",
                adv.get("setor_executor_exclude_values"),
                "!=",
                action_keys=["setor_executor_exclude_values"],
            )
            _add_adv("Emissor", adv.get("setor_emissor"), action_keys=["setor_emissor"])
            _add_adv(
                "Emissor",
                adv.get("setor_emissor_exclude_values"),
                "!=",
                action_keys=["setor_emissor_exclude_values"],
            )
            _add_adv("Divisao", adv.get("divisao"), action_keys=["divisao"])
            _add_adv(
                "Divisao",
                adv.get("divisao_exclude_values"),
                "!=",
                action_keys=["divisao_exclude_values"],
            )
            _add_adv("Situacao", adv.get("situacao"), action_keys=["situacao"])
            _add_adv(
                "Situacao",
                adv.get("situacao_exclude_values"),
                "!=",
                action_keys=["situacao_exclude_values"],
            )
            _add_adv("Solicitante", adv.get("solicitante"), action_keys=["solicitante"])
            _add_adv(
                "Solicitante",
                adv.get("solicitante_exclude_values"),
                "!=",
                action_keys=["solicitante_exclude_values"],
            )
            _add_adv(
                "Resp Programacao",
                adv.get("responsavel_programacao"),
                action_keys=["responsavel_programacao"],
            )
            _add_adv(
                "Resp Programacao",
                adv.get("responsavel_programacao_exclude_values"),
                "!=",
                action_keys=["responsavel_programacao_exclude_values"],
            )
            _add_adv(
                "Resp Execucao",
                adv.get("responsavel_execucao"),
                action_keys=["responsavel_execucao"],
            )
            _add_adv(
                "Resp Execucao",
                adv.get("responsavel_execucao_exclude_values"),
                "!=",
                action_keys=["responsavel_execucao_exclude_values"],
            )
            _add_adv(
                "Prio Emissao",
                adv.get("prioridade_emissao_values"),
                action_keys=["prioridade_emissao_values"],
            )
            _add_adv(
                "Prio Emissao",
                adv.get("prioridade_emissao_exclude_values"),
                "!=",
                action_keys=["prioridade_emissao_exclude_values"],
            )
            _add_adv(
                "Prio Planejamento",
                adv.get("prioridade_planejamento_values"),
                action_keys=["prioridade_planejamento_values"],
            )
            _add_adv(
                "Prio Planejamento",
                adv.get("prioridade_planejamento_exclude_values"),
                "!=",
                action_keys=["prioridade_planejamento_exclude_values"],
            )

            ano_emissao_vals = adv.get("ano_emissao_values")
            ano_emissao_exc = adv.get("ano_emissao_exclude_values")
            if ano_emissao_vals is None and adv.get("ano_emissao") is not None:
                ano_emissao_vals = [adv.get("ano_emissao")]
            if (
                ano_emissao_exc is None
                and adv.get("ano_emissao_exclude")
                and adv.get("ano_emissao") is not None
            ):
                ano_emissao_exc = [adv.get("ano_emissao")]
            _add_adv(
                "Ano Emissao",
                ano_emissao_vals,
                action_keys=["ano_emissao", "ano_emissao_values"],
            )
            _add_adv(
                "Ano Emissao",
                ano_emissao_exc,
                "!=",
                action_keys=["ano_emissao_exclude", "ano_emissao_exclude_values"],
            )

            ano_execucao_vals = adv.get("ano_execucao_values")
            ano_execucao_exc = adv.get("ano_execucao_exclude_values")
            if ano_execucao_vals is None and adv.get("ano_execucao") is not None:
                ano_execucao_vals = [adv.get("ano_execucao")]
            if (
                ano_execucao_exc is None
                and adv.get("ano_execucao_exclude")
                and adv.get("ano_execucao") is not None
            ):
                ano_execucao_exc = [adv.get("ano_execucao")]
            _add_adv(
                "Ano Execucao",
                ano_execucao_vals,
                action_keys=["ano_execucao", "ano_execucao_values"],
            )
            _add_adv(
                "Ano Execucao",
                ano_execucao_exc,
                "!=",
                action_keys=["ano_execucao_exclude", "ano_execucao_exclude_values"],
            )

            em_range = _summary_week_range(
                adv.get("semana_emissao_inicio"), adv.get("semana_emissao_fim")
            )
            if em_range:
                label = "Semana Emissao"
                op = "!=" if adv.get("semana_emissao_exclude") else None
                action_keys = ["semana_emissao_inicio", "semana_emissao_fim"]
                if adv.get("semana_emissao_exclude"):
                    action_keys.append("semana_emissao_exclude")
                _add_adv(label, [em_range], op, action_keys=action_keys)
            ex_range = _summary_week_range(
                adv.get("semana_execucao_inicio"), adv.get("semana_execucao_fim")
            )
            if ex_range:
                label = "Semana Execucao"
                op = "!=" if adv.get("semana_execucao_exclude") else None
                action_keys = ["semana_execucao_inicio", "semana_execucao_fim"]
                if adv.get("semana_execucao_exclude"):
                    action_keys.append("semana_execucao_exclude")
                _add_adv(label, [ex_range], op, action_keys=action_keys)

            if adv.get("derivada_has"):
                _merge_summary_actions(
                    summary_entries,
                    text="Possui derivada",
                    actions=[{"kind": "advanced_keys", "keys": ["derivada_has"]}],
                )
            # Compatibilidade: mantemos a chave legada "derivada_all_ste",
            # mas o comportamento funcional agora considera STE e SES.
            if adv.get("derivada_all_ste"):
                _merge_summary_actions(
                    summary_entries,
                    text="Derivadas em STE/SES",
                    actions=[{"kind": "advanced_keys", "keys": ["derivada_all_ste"]}],
                )
            if adv.get("derivada_is"):
                _merge_summary_actions(
                    summary_entries,
                    text="SSA derivada",
                    actions=[{"kind": "advanced_keys", "keys": ["derivada_is"]}],
                )
            if adv.get("macro_filter"):
                macro_val = adv.get("macro_filter")
                macro_label = (
                    "SSAs para baixar"
                    if macro_val == "ssas_para_baixar"
                    else str(macro_val)
                )
                _merge_summary_actions(
                    summary_entries,
                    text=f"Macro: {macro_label}",
                    actions=[{"kind": "advanced_keys", "keys": ["macro_filter"]}],
                )

        if getattr(self, "_exclude_ste_sca", False):
            _merge_summary_actions(
                summary_entries,
                text=_EXCLUDED_TERMINAL_SUMMARY,
                actions=[{"kind": "exclude_ste_sca"}],
            )

        active_filters = [entry["text"] for entry in summary_entries.values()]

        # Monta texto do resumo
        if active_filters:
            summary_text = "Filtros ativos: " + "; ".join(active_filters)
        else:
            summary_text = "Nenhum filtro ativo"

        active_state = bool(active_filters)
        roles = get_theme_roles(getattr(self, "_current_theme", "dark"))
        summary_color = (
            roles.get("summary_text_color")
            or roles.get("panel_text")
            or roles.get("label_color")
            or "palette(windowText)"
        )
        if (
            hasattr(self, "filters_summary_frame")
            and self.filters_summary_frame is not None
        ):
            summary_bg = (
                roles.get("summary_frame_bg") or roles.get("panel_bg") or "transparent"
            )
            active_border = (
                roles.get("accent")
                or roles.get("input_border_focus")
                or roles.get("panel_text")
                or "palette(highlight)"
            )
            idle_border = (
                roles.get("input_border") or roles.get("panel_border") or "palette(mid)"
            )
            frame_border = active_border if active_state else idle_border
            self.filters_summary_frame.setStyleSheet(
                "QFrame#filtersSummaryFrame {"
                f"background:{summary_bg};"
                f"border:1px solid {frame_border};"
                "border-radius:4px;"
                "}"
            )
        if hasattr(self, "filters_summary_label"):
            self.filters_summary_label.setText(
                "Filtros ativos:" if active_state else "Nenhum filtro ativo"
            )
            self.filters_summary_label.setToolTip(summary_text if active_state else "")
            self.filters_summary_label.setStyleSheet(
                f"color:{summary_color};"
                + ("font-weight:700;" if active_state else "font-weight:400;")
            )
        scroll = getattr(self, "filters_summary_scroll", None)
        if scroll is not None:
            try:
                scroll.setVisible(active_state)
            except Exception as exc:
                logger.debug(
                    "Falha ao atualizar visibilidade do scroll de filtros ativos: %s",
                    exc,
                )
        try:
            self._rebuild_filters_summary_buttons(list(summary_entries.values()))
        except Exception as exc:
            logger.warning(
                "Falha ao reconstruir botoes clicaveis do resumo de filtros: %s", exc
            )

    def _clear_filters_summary_buttons(self) -> None:
        layout = getattr(self, "filters_summary_items_layout", None)
        if layout is None:
            return
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _rebuild_filters_summary_buttons(self, entries: list[SummaryEntry]) -> None:
        self._clear_filters_summary_buttons()
        layout = getattr(self, "filters_summary_items_layout", None)
        container = getattr(self, "filters_summary_items_widget", None)
        if layout is None or container is None:
            return
        roles = get_theme_roles(getattr(self, "_current_theme", "dark"))
        accent = roles.get("accent") or roles.get("input_border_focus") or "#4a90e2"
        border = roles.get("input_border") or roles.get("panel_border") or accent
        text_color = roles.get("panel_text") or roles.get("label_color") or "inherit"
        background = roles.get("input_bg") or "transparent"
        try:
            container.setFixedHeight(22)
            container.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        except Exception as exc:
            logger.debug(
                "Falha ao configurar tamanho do container de filtros ativos: %s", exc
            )
        content_width = 1
        spacing = 0
        try:
            spacing = int(layout.spacing() or 0)
        except Exception as exc:
            logger.debug("Falha ao obter espacamento dos filtros ativos: %s", exc)
        for entry in entries:
            text = str(entry.get("text") or "").strip()
            raw_actions = entry.get("actions")
            if not text or not isinstance(raw_actions, list) or not raw_actions:
                continue
            actions: list[SummaryAction] = [
                cast(SummaryAction, dict(action))
                for action in raw_actions
                if isinstance(action, dict)
            ]
            if not actions:
                continue
            button = QPushButton(text)
            button.setToolTip(f"Clique para remover este filtro: {text}")
            try:
                button.setFixedHeight(22)
                button.setSizePolicy(
                    QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed
                )
                button.setStyleSheet(
                    "QPushButton {"
                    f"border:1px solid {border};"
                    "border-radius:4px;"
                    "padding:2px 8px;"
                    "font-weight:600;"
                    f"background:{background};"
                    f"color:{text_color};"
                    "text-align:left;"
                    "}"
                    "QPushButton:hover {"
                    f"border-color:{accent};"
                    "font-weight:600;"
                    "}"
                )
            except Exception as exc:
                logger.debug(
                    "Falha ao aplicar estilo em botao do resumo de filtros '%s': %s",
                    text,
                    exc,
                )
            button.clicked.connect(
                self._build_filters_summary_click_handler(text, actions)
            )
            layout.addWidget(button, 0)
            try:
                content_width += int(button.sizeHint().width()) + spacing
            except Exception as exc:
                logger.debug(
                    "Falha ao medir largura do botao de filtro ativo '%s': %s",
                    text,
                    exc,
                )
        try:
            layout.activate()
            container.setFixedSize(max(1, content_width), 22)
        except Exception as exc:
            logger.debug("Falha ao ajustar largura dos filtros ativos: %s", exc)
        try:
            container.setVisible(bool(entries))
        except Exception as exc:
            logger.debug(
                "Falha ao atualizar visibilidade do container de resumo de filtros: %s",
                exc,
            )

    def _build_filters_summary_click_handler(
        self, item_text: str, actions: list[SummaryAction]
    ) -> Callable[[bool], None]:
        captured_actions = list(actions)

        def _handler(_checked: bool = False) -> None:
            self._on_filters_summary_item_clicked(item_text, captured_actions)

        return _handler

    def _confirm_filter_summary_item_removal(self, item_text: str) -> bool:
        buttons = getattr(QMessageBox, "StandardButton", None)
        title = "Remover filtro"
        message = f"Deseja remover este filtro ativo?\n\n{item_text}"
        if os.environ.get("PYTEST_CURRENT_TEST"):
            logger.debug(
                "PYTEST_CURRENT_TEST set; mantendo confirmacao de remocao ativa."
            )
        try:
            if buttons is not None:
                reply = QMessageBox.question(
                    _qt_parent(self),
                    title,
                    message,
                    buttons.Yes | buttons.No,
                    buttons.No,
                )
                return reply == buttons.Yes
            reply = QMessageBox.question(_qt_parent(self), title, message)
            return reply == getattr(QMessageBox, "Yes", reply)
        except Exception as exc:
            logger.warning(
                "Falha ao solicitar confirmacao para remocao de filtro '%s': %s",
                item_text,
                exc,
            )
            raise

    def _clear_general_search_state(self) -> None:
        self._invalidate_active_filter_request("clear_general_search_state")
        self._cancel_active_filter_worker("clear_general_search_state", wait_ms=0)
        self._set_filter_ui_idle()
        try:
            self._debounce_timer.stop()
        except Exception as exc:
            logger.debug(
                "Falha ao parar debounce ao limpar busca via resumo de filtros: %s", exc
            )
        self._set_search_text_across_tabs("")
        self._pending_search_display = None
        self._active_filter_search_display = ""
        self._active_filter_search_request_id = None
        self._df_last_search_filtered = self.df_completo

    def _sync_exclude_ste_checkbox_state(self, checked: bool) -> None:
        checked_bool = bool(checked)
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
                    checkbox.setChecked(checked_bool)
                finally:
                    try:
                        checkbox.blockSignals(False)
                    except Exception as exc:
                        logger.debug(
                            "Falha ao reativar sinais de checkbox exclude_ste no resumo de filtros: %s",
                            exc,
                        )
            return
        checkbox = getattr(self, "exclude_ste_checkbox", None)
        if checkbox is None:
            return
        try:
            checkbox.blockSignals(True)
            checkbox.setChecked(checked_bool)
        finally:
            try:
                checkbox.blockSignals(False)
            except Exception as exc:
                logger.debug(
                    "Falha ao reativar sinais de checkbox exclude_ste principal no resumo de filtros: %s",
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
        refresh_needed = False
        sync_advanced_ui = False
        sync_quick_combo = False
        status_reset_needed = False
        pending_column_clears: list[str] = []
        pending_advanced_keys: list[str] = []
        for action in actions:
            if not isinstance(action, dict):
                continue
            kind = str(action.get("kind") or "").strip()
            if kind == "search":
                self._clear_general_search_state()
                refresh_needed = True
                status_reset_needed = True
                continue
            if kind == "dedicated_or":
                self._dedicated_or_text = ""
                continue
            if kind == "exclude_ste_sca":
                self._exclude_ste_sca = False
                self._sync_exclude_ste_checkbox_state(False)
                sync_advanced_ui = True
                refresh_needed = True
                continue
            if kind in {"column", "column_or_group"}:
                column_name = str(action.get("column") or "").strip()
                if not column_name:
                    raise ValueError(
                        f"Resumo de filtros recebeu acao sem coluna valida: {action!r}"
                    )
                if column_name not in pending_column_clears:
                    pending_column_clears.append(column_name)
                continue
            if kind == "advanced_keys":
                raw_keys = action.get("keys")
                keys = [
                    str(key).strip()
                    for key in (raw_keys if isinstance(raw_keys, list) else [])
                    if str(key).strip()
                ]
                if not keys:
                    raise ValueError(
                        f"Resumo de filtros recebeu advanced_keys sem chaves: {action!r}"
                    )
                for key in keys:
                    if key not in pending_advanced_keys:
                        pending_advanced_keys.append(key)
                continue
            raise ValueError(f"Acao de resumo de filtros nao suportada: {action!r}")
        for key in pending_advanced_keys:
            self._advanced_filters.pop(key, None)
        if pending_advanced_keys:
            self._advanced_filters_active = bool(
                self._has_active_advanced_filters(self._advanced_filters)
            )
            sync_advanced_ui = True
            refresh_needed = True
            if any(
                key.startswith("setor_executor") or key == "macro_filter"
                for key in pending_advanced_keys
            ):
                sync_quick_combo = True
        if pending_column_clears:
            for column_name in pending_column_clears:
                if column_name in self._active_column_filters or column_name in getattr(
                    self, "_column_to_or_group", {}
                ):
                    if column_name in self._column_to_or_group:
                        group = self._column_to_or_group.get(column_name)
                        if group:
                            group["values"] = []
                            for member in group.get("columns", []):
                                self._active_column_filters[member] = ""
                    else:
                        self._active_column_filters[column_name] = ""
            self._build_column_filters_panel()
            refresh_needed = True
        if sync_advanced_ui:
            self._sync_advanced_filter_ui()
        if refresh_needed:
            self._mark_profile_as_custom()
            self._refresh_after_filter_change()
        else:
            self._update_filters_summary()
        if status_reset_needed and not self._has_any_active_filters():
            self._set_filtered_count_status()
        self._sync_clear_filter_button_state()
        if sync_quick_combo:
            self._sync_quick_setor_executor_combo_from_filters()

    def _on_filters_summary_item_clicked(
        self, item_text: str, actions: list[SummaryAction]
    ) -> None:
        self._remove_filters_summary_actions(item_text, actions)

    def _format_column_filter_display_value(
        self, raw: str, *, column: str | None = None
    ) -> str:
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
            text = re.sub(r"\s+", " ", text).strip()
            # Split by commas only
            tokens = [t.strip() for t in text.split(",") if t.strip()]
            # Apply optional display aliases per column
            if tokens:
                alias_map = self._get_filter_alias_map()
                mapped: list[str] = []
                col_map = None
                if column and isinstance(alias_map, dict):
                    col_map = alias_map.get(column) or alias_map.get(column.lower())
                global_map = (
                    alias_map.get("_global") if isinstance(alias_map, dict) else None
                )
                for tok in tokens:
                    key = tok.casefold()
                    new_tok = None
                    if isinstance(col_map, dict):
                        new_tok = col_map.get(key) or col_map.get(tok)
                    if new_tok is None and isinstance(global_map, dict):
                        new_tok = global_map.get(key) or global_map.get(tok)
                    mapped.append(
                        new_tok if isinstance(new_tok, str) and new_tok.strip() else tok
                    )
                tokens = mapped
            # Display as comma-separated (OR logic)
            return ", ".join(tokens)
        except Exception:
            # Fallback: display raw, trimmed
            return str(raw).strip()

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
        try:
            global _FILTER_ALIAS_MAP_CACHE, _FILTER_ALIAS_MAP_CACHE_SIGNATURE
            repo_root = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            cfg_path = os.path.join(repo_root, "config", "filter_aliases.json")
            mtime_ns = os.stat(cfg_path).st_mtime_ns if os.path.exists(cfg_path) else None
            signature = (cfg_path, mtime_ns)
            if (
                _FILTER_ALIAS_MAP_CACHE_SIGNATURE == signature
                and isinstance(_FILTER_ALIAS_MAP_CACHE, dict)
            ):
                self._filter_alias_map = _FILTER_ALIAS_MAP_CACHE
                return self._filter_alias_map
            if os.path.exists(cfg_path):
                with open(cfg_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    _FILTER_ALIAS_MAP_CACHE = data
                    _FILTER_ALIAS_MAP_CACHE_SIGNATURE = signature
                    self._filter_alias_map = data
                    return self._filter_alias_map
        except Exception as exc:
            logger.debug(
                "Falha ao carregar aliases de filtro em arquivo local: %s", exc
            )
        _FILTER_ALIAS_MAP_CACHE = {}
        _FILTER_ALIAS_MAP_CACHE_SIGNATURE = None
        self._filter_alias_map = _FILTER_ALIAS_MAP_CACHE
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
        # O label textual segue refletindo apenas o painel de filtros por coluna.
        active = any(
            str(value).strip()
            for value in (getattr(self, "_active_column_filters", {}) or {}).values()
        )
        txt = "Filtros por coluna: Ativo" if active else "Filtros por coluna: Nao ativo"
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
        for profile_data in profiles.values():
            if isinstance(profile_data, dict):
                all_section = (
                    profile_data.get("all")
                    if isinstance(profile_data.get("all"), dict)
                    else None
                )
                if all_section:
                    for col_name in all_section.keys():
                        if col_name not in cols:
                            cols.append(col_name)
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
        """Syncs filter values across columns in same OR group.

        SIMPLIFIED: No logical operators - just comma-separated terms.
        """
        group = self._column_to_or_group.get(column)
        if not group:
            return
        normalized = str(text or "").strip()
        # Remove extra spaces, semicolons
        normalized = normalized.replace(";", ",")
        normalized = re.sub(r"\s+", " ", normalized).strip()
        # Split by commas only
        tokens = [token.strip() for token in normalized.split(",") if token.strip()]
        if not tokens:
            group["values"] = []
            for col in group["columns"]:
                self._active_column_filters.pop(col, None)
            return
        group["values"] = tokens
        # Store internally as comma-separated list (OR logic)
        common_text = ", ".join(tokens)
        for col in group["columns"]:
            self._active_column_filters[col] = common_text

    def _apply_column_filters(self, df: pd.DataFrame) -> pd.DataFrame:
        """Aplica todos os filtros por coluna com as mesmas regras de busca (prefixo ^, sufixo $, =exato, ~regex, !neg)."""
        if df is None or df.empty or not self._active_column_filters:
            return df
        current_revision = getattr(self, "_data_revision", 0)
        cache_revision = getattr(self, "_column_filter_series_cache_revision", None)
        if cache_revision != current_revision:
            self._column_filter_series_cache_revision = current_revision
            self._column_filter_series_cache = {}
        series_cache = getattr(self, "_column_filter_series_cache", None)
        if not isinstance(series_cache, dict):
            series_cache = {}
            self._column_filter_series_cache = series_cache
        working_df = df
        for col, raw in self._active_column_filters.items():
            if working_df.empty:
                return working_df
            if col not in working_df.columns:
                continue
            raw_str = str(raw).strip()
            if not raw_str:
                continue
            cache_key = (id(df), str(col))
            cached_series = series_cache.get(cache_key)
            if isinstance(cached_series, pd.Series):
                col_series = cached_series
                if working_df is not df:
                    col_series = col_series.reindex(working_df.index)
            else:
                col_series = df[col].astype("string").fillna("")
                series_cache[cache_key] = col_series
                if working_df is not df:
                    col_series = col_series.reindex(working_df.index)
            col_mask = self._build_column_mask(col_series, raw_str)
            display_dates = None
            if self._should_match_date_display_filter(col, raw_str):
                display_dates = self._get_column_filter_date_display_series(
                    working_df, col
                )
            if isinstance(display_dates, pd.Series) and not display_dates.empty:
                tokens = [token.strip() for token in raw_str.split(",") if token.strip()]
                include_tokens = [
                    token for token in tokens if not token.startswith("!")
                ]
                exclude_tokens = [token for token in tokens if token.startswith("!")]

                if include_tokens:
                    include_expr = ", ".join(include_tokens)
                    col_mask = self._build_column_mask(
                        col_series, include_expr
                    ) | self._build_column_mask(display_dates, include_expr)
                else:
                    col_mask = pd.Series([True] * len(col_series), index=col_series.index)

                if exclude_tokens:
                    exclude_expr = ", ".join(
                        token[1:].strip()
                        for token in exclude_tokens
                        if token[1:].strip()
                    )
                    if exclude_expr:
                        excluded_mask = self._build_column_mask(
                            col_series, exclude_expr
                        ) | self._build_column_mask(display_dates, exclude_expr)
                        col_mask = col_mask & ~excluded_mask
            if not col_mask.all():
                working_df = working_df[col_mask]
        return working_df

    def _should_match_date_display_filter(self, col: str, raw_filter: str) -> bool:
        col_lower = str(col or "").casefold()
        if "data" not in col_lower and not col_lower.startswith("dt_"):
            return False
        return "/" in str(raw_filter or "")

    def _get_column_filter_date_display_series(
        self, df: pd.DataFrame, col: str
    ) -> pd.Series | None:
        if df is None or col not in df.columns:
            return None
        current_revision = getattr(self, "_data_revision", 0)
        cache_scope = getattr(self, "_column_filter_date_cache_scope", None)
        next_scope = (current_revision, id(df))
        if cache_scope != next_scope:
            self._column_filter_date_cache_scope = next_scope
            self._column_filter_date_cache = {}
        cache = getattr(self, "_column_filter_date_cache", None)
        if not isinstance(cache, dict):
            cache = {}
            self._column_filter_date_cache = cache
        cached = cache.get(col)
        if isinstance(cached, pd.Series):
            return cached
        parsed_dates = parse_datetime_series_mixed(df[col])
        display_dates = parsed_dates.dt.strftime("%d/%m/%Y").fillna("").astype(str)
        cache[col] = display_dates
        return display_dates

    def _handle_hide_column_filter_line(self, column_name: str) -> None:
        current_value = ""
        try:
            current_value = str(
                (getattr(self, "_active_column_filters", {}) or {}).get(column_name, "")
            ).strip()
        except Exception:
            current_value = ""
        if current_value:
            try:
                display_name = self._resolve_column_display_name(column_name)
            except Exception:
                display_name = str(column_name)
            try:
                self.status_label.setText(
                    f"Status: Limpe o filtro de {display_name} antes de ocultar a linha."
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

    def _refresh_after_filter_change(self):
        """Reaplica filtros de coluna, atualiza tabela e indicadores."""
        refresh_started = perf_counter()
        current_details_ssa = getattr(self, "_details_current_ssa", None)
        timings: dict[str, float] = {
            "advanced": 0.0,
            "column": 0.0,
            "exclude": 0.0,
            "sort": 0.0,
            "paginate": 0.0,
            "render": 0.0,
            "indicator": 0.0,
            "summary": 0.0,
            "status": 0.0,
            "sync": 0.0,
        }

        def _measure_timing(name: str, callback):
            started = perf_counter()
            result = callback()
            timings[name] = (perf_counter() - started) * 1000.0
            return result

        has_general_search = False
        try:
            for widget in self._iter_search_inputs():
                if widget.text().strip():
                    has_general_search = True
                    break
        except Exception:
            has_general_search = False
        if not has_general_search:
            active_search_display = str(
                getattr(self, "_active_filter_search_display", "") or ""
            ).strip()
            pending_search_display = str(
                getattr(self, "_pending_search_display", "") or ""
            ).strip()
            has_general_search = bool(active_search_display or pending_search_display)

        base = (
            self._df_last_search_filtered
            if has_general_search or not self._df_last_search_filtered.empty
            else self.df_completo
        )
        filtered = base
        try:
            column_filters = getattr(self, "_active_column_filters", {}) or {}
            has_column_filters = any(str(value).strip() for value in column_filters.values())
        except Exception:
            has_column_filters = False
        has_advanced_filters = bool(getattr(self, "_advanced_filters_active", False))
        has_excluded_terminal_status = bool(getattr(self, "_exclude_ste_sca", False))
        has_post_search_filters = (
            has_column_filters
            or has_advanced_filters
            or has_excluded_terminal_status
        )
        if has_post_search_filters and hasattr(self, "_apply_advanced_filters"):
            try:
                filtered = _measure_timing(
                    "advanced", lambda: self._apply_advanced_filters(filtered)
                )
            except Exception as exc:
                logger.warning(
                    "Falha ao aplicar filtros avancados no refresh de filtros: %s", exc
                )
        if has_post_search_filters:
            filtered = _measure_timing(
                "column", lambda: self._apply_column_filters(filtered)
            )
        if (
            has_post_search_filters
            and has_excluded_terminal_status
            and not filtered.empty
            and "situacao" in filtered.columns
        ):
            try:
                # Compatibilidade: o nome legado _exclude_ste_sca permanece por
                # contrato interno, mas SES entrou no mesmo grupo terminal.
                filtered = _measure_timing(
                    "exclude",
                    lambda: filtered[
                        ~filtered["situacao"]
                        .astype(str)
                        .str.upper()
                        .isin(_EXCLUDED_TERMINAL_STATUSES)
                    ],
                )
            except Exception as exc:
                logger.warning(
                    "Falha ao aplicar exclusao SCA/SES/STE no refresh de filtros: %s",
                    exc,
                )
        # CORRECAO 2026-01-08: Ordenar por numero_ssa decrescente apos filtro
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
                filtered = _measure_timing(
                    "sort", lambda: filtered.sort_values("numero_ssa", ascending=False)
                )
            except Exception as exc:
                logger.warning(
                    "Falha ao ordenar numero_ssa no refresh de filtros: %s", exc
                )
        self.df_exibido = filtered
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
        _measure_timing(
            "paginate", lambda: self.paginator.set_dataframe(self.df_exibido)
        )
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
                            slice_norm = self._normalize_ssa_series(
                                current_slice["numero_ssa"]
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
                _measure_timing(
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
                _measure_timing("render", lambda: self.display_current_page(current))
        except Exception as exc:
            logger.debug(
                "Falha ao renderizar pagina atual diretamente no refresh; usando fallback: %s",
                exc,
            )
            _measure_timing(
                "render",
                lambda cp=max(
                    1,
                    min(
                        getattr(self.paginator, "current_page", 1),
                        getattr(self.paginator, "total_pages", 1),
                    ),
                ): self.display_current_page(cp),
            )
        _measure_timing("indicator", self._update_col_filter_indicator)
        try:
            _measure_timing("summary", self._update_filters_summary)
        except Exception as exc:
            logger.debug("Falha ao atualizar resumo de filtros no refresh: %s", exc)
        self._sync_clear_filter_button_state()
        try:
            _measure_timing("status", self._set_filtered_count_status)
        except Exception as exc:
            logger.debug(
                "Falha ao atualizar status de total filtrado no refresh: %s", exc
            )
        try:
            sync_combo = getattr(
                self, "_sync_quick_setor_executor_combo_from_filters", None
            )
            if callable(sync_combo):
                _measure_timing("sync", sync_combo)
        except Exception as exc:
            logger.debug(
                "Falha ao sincronizar combo rapido de setor executor no refresh de filtros: %s",
                exc,
            )
        total_ms = (perf_counter() - refresh_started) * 1000.0
        logger.debug(
            (
                "Filter refresh timings ms: total=%.2f advanced=%.2f column=%.2f "
                "exclude=%.2f sort=%.2f paginate=%.2f render=%.2f indicator=%.2f "
                "summary=%.2f status=%.2f sync=%.2f rows=%s->%s"
            ),
            total_ms,
            timings["advanced"],
            timings["column"],
            timings["exclude"],
            timings["sort"],
            timings["paginate"],
            timings["render"],
            timings["indicator"],
            timings["summary"],
            timings["status"],
            timings["sync"],
            len(base) if isinstance(base, pd.DataFrame) else "na",
            len(filtered) if isinstance(filtered, pd.DataFrame) else "na",
        )

    def _build_filter_cache_context(self) -> str:
        """Gera contexto deterministico do estado efetivo de filtros para o cache."""
        try:
            active_filters = OrderedDict()
            for column_name, filter_value in sorted(
                (getattr(self, "_active_column_filters", {}) or {}).items()
            ):
                normalized_value = str(filter_value).strip()
                if normalized_value:
                    active_filters[column_name] = normalized_value

            advanced_filters_active = bool(
                getattr(self, "_advanced_filters_active", False)
            )
            raw_advanced_filters = getattr(self, "_advanced_filters", None) or {}
            advanced_filters = (
                copy.deepcopy(raw_advanced_filters) if advanced_filters_active else {}
            )

            cache_payload = {
                "active_column_filters": active_filters,
                "advanced_filters": advanced_filters,
                "advanced_filters_active": advanced_filters_active,
                "exclude_ste_sca": bool(getattr(self, "_exclude_ste_sca", False)),
            }
            if not (
                cache_payload["active_column_filters"]
                or cache_payload["advanced_filters"]
                or cache_payload["exclude_ste_sca"]
            ):
                return ""
            return json.dumps(
                cache_payload,
                sort_keys=True,
                ensure_ascii=True,
                default=str,
            )
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
        return {
            column_name
            for column_name in hidden_set
            if not str(current_filters.get(column_name, "")).strip()
        }

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
        for group in getattr(self, "_column_or_groups", []) or []:
            groups_snapshot.append(
                {
                    "columns": tuple(group.get("columns", ())),
                    "values": list(group.get("values", ())),
                }
            )
        return {
            "search_text": search_text,
            "pending_search_display": getattr(self, "_pending_search_display", None),
            "active_column_filters": active_filters,
            "column_or_groups": groups_snapshot,
            "exclude_ste_sca": bool(getattr(self, "_exclude_ste_sca", False)),
            "advanced_filters": copy.deepcopy(
                getattr(self, "_advanced_filters", None) or {}
            ),
            "advanced_filters_active": bool(
                getattr(self, "_advanced_filters_active", False)
            ),
            "current_filter_profile": getattr(self, "current_filter_profile", None),
            "profile_base_filters": copy.deepcopy(
                getattr(self, "_profile_base_filters", {}) or {}
            ),
            "hidden_column_filter_lines": set(
                getattr(self, "_hidden_column_filter_lines", set())
            ),
            "dedicated_or_text": str(getattr(self, "_dedicated_or_text", "")),
        }

    def _store_last_filter_state(self) -> None:
        if getattr(self, "_restoring_filter_state", False):
            return
        try:
            self._last_filter_state = self._snapshot_filter_state()
        except Exception as exc:
            logger.warning("Falha ao gerar snapshot de estado de filtros: %s", exc)
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
            restored_search_text = str(state.get("search_text", "") or "")
            try:
                self._set_search_text_across_tabs(restored_search_text)
            except Exception as exc:
                logger.warning("Falha ao restaurar texto de busca entre abas: %s", exc)
                try:
                    self.search_input.blockSignals(True)
                    self.search_input.setText(restored_search_text)
                finally:
                    try:
                        self.search_input.blockSignals(False)
                    except Exception as unblock_exc:
                        logger.debug(
                            "Falha ao reativar sinais do campo de busca ao restaurar estado: %s",
                            unblock_exc,
                        )
            self._pending_search_display = state.get("pending_search_display")
            self._active_column_filters = OrderedDict(
                state.get("active_column_filters") or {}
            )
            self._reset_or_groups()
            for group in state.get("column_or_groups") or []:
                self._register_or_group(
                    list(group.get("columns") or []), list(group.get("values") or [])
                )
            self._exclude_ste_sca = bool(state.get("exclude_ste_sca"))
            tab_contexts = getattr(self, "_tab_contexts", None)
            if isinstance(tab_contexts, list):
                for ctx in tab_contexts:
                    checkbox = (
                        ctx.get("exclude_ste_checkbox")
                        if isinstance(ctx, dict)
                        else None
                    )
                    if checkbox is None:
                        continue
                    try:
                        checkbox.blockSignals(True)
                        checkbox.setChecked(self._exclude_ste_sca)
                    except Exception as exc:
                        logger.debug(
                            "Falha ao restaurar checkbox exclude_ste em aba: %s", exc
                        )
                    finally:
                        try:
                            checkbox.blockSignals(False)
                        except Exception as exc:
                            logger.debug(
                                "Falha ao reativar sinais de checkbox exclude_ste em aba: %s",
                                exc,
                            )
            else:
                try:
                    self.exclude_ste_checkbox.blockSignals(True)
                    self.exclude_ste_checkbox.setChecked(self._exclude_ste_sca)
                except Exception as exc:
                    logger.debug(
                        "Falha ao restaurar checkbox exclude_ste principal: %s", exc
                    )
                finally:
                    try:
                        self.exclude_ste_checkbox.blockSignals(False)
                    except Exception as exc:
                        logger.debug(
                            "Falha ao reativar sinais do checkbox exclude_ste principal: %s",
                            exc,
                        )
            self._advanced_filters = state.get("advanced_filters") or {}
            self._advanced_filters_active = bool(state.get("advanced_filters_active"))
            self._df_last_search_filtered = (
                pd.DataFrame() if restored_search_text.strip() else self.df_completo
            )
            self.current_filter_profile = state.get("current_filter_profile")
            self._profile_base_filters = state.get("profile_base_filters") or {}
            self._hidden_column_filter_lines = (
                self._sanitize_hidden_column_filter_lines(
                    state.get("hidden_column_filter_lines") or set(),
                    self._active_column_filters,
                )
            )
            self._dedicated_or_text = str(state.get("dedicated_or_text") or "")
            try:
                self._sync_advanced_filter_ui()
            except Exception as exc:
                logger.warning(
                    "Falha ao sincronizar UI de filtros avancados no restore: %s", exc
                )
            self._build_column_filters_panel()
            try:
                self.update_filter_tags()
            except Exception as exc:
                logger.debug("Falha ao atualizar tags de filtros no restore: %s", exc)
            selector = getattr(self, "profile_selector", None)
            if selector is not None:
                idx = (
                    selector.findData(self.current_filter_profile)
                    if self.current_filter_profile
                    else selector.findData(None)
                )
                if idx >= 0:
                    self._profile_lock = True
                    try:
                        selector.setCurrentIndex(idx)
                    finally:
                        self._profile_lock = False
            if restored_search_text.strip():
                self.initiate_filtering()
            else:
                self._refresh_after_filter_change()
                try:
                    self._update_filters_summary()
                except Exception as exc:
                    logger.debug(
                        "Falha ao atualizar resumo de filtros no restore: %s", exc
                    )
                self._sync_clear_filter_button_state()
        finally:
            self._restoring_filter_state = False
            self._update_undo_button_state()

    def _update_undo_button_state(self) -> None:
        self._set_undo_filter_buttons_enabled(
            bool(getattr(self, "_last_filter_state", None))
        )

    def _apply_search_display(self):
        display_text = getattr(self, "_pending_search_display", None)
        if display_text is None:
            return

        widgets = self._get_live_search_inputs_snapshot()
        for widget in widgets:
            try:
                if widget.hasFocus():
                    return
            except RuntimeError as exc:
                logger.debug(
                    "Widget de busca invalido durante verificacao de foco: %s", exc
                )
                continue
            except Exception as exc:
                logger.debug("Falha ao verificar foco durante sync de busca: %s", exc)
                continue
        for widget in widgets:
            blocked = False
            try:
                widget.blockSignals(True)
                blocked = True
                widget.setText(display_text)
            except RuntimeError as exc:
                logger.debug(
                    "Widget de busca invalido durante apply_search_display: %s", exc
                )
            finally:
                if blocked:
                    try:
                        widget.blockSignals(False)
                    except RuntimeError:
                        pass
                    except Exception as exc:
                        logger.debug(
                            "Falha ao reativar sinais do campo em apply_search_display: %s",
                            exc,
                        )
        self._pending_search_display = None

    def _mark_profile_as_custom(self):
        """Marca o perfil atual como personalizado quando filtros divergem."""
        if getattr(self, "_profile_lock", False):
            return
        base_raw = self._profile_base_filters or {}
        base = base_raw if isinstance(base_raw, dict) else {}
        base_columns_candidate = base.get("columns")
        base_columns_raw = (
            base_columns_candidate if isinstance(base_columns_candidate, dict) else {}
        )
        base_columns = {str(k): str(v).strip() for k, v in base_columns_raw.items()}
        base_groups_raw = base.get("or_groups")
        base_groups = base_groups_raw if isinstance(base_groups_raw, list) else []
        base_exclude = bool(base.get("exclude_ste_sca", False))

        if (
            self.current_filter_profile
            and self.current_filter_profile in self.filter_profiles
        ):
            mismatch = False
            # Verifica colunas mapeadas
            current_columns = {}
            referenced_columns = set(base_columns.keys()) | set(
                self._active_column_filters.keys()
            )
            for col in referenced_columns:
                if col in self._column_to_or_group:
                    group = self._column_to_or_group.get(col)
                    current_columns[col] = (
                        ", ".join(group.get("values", [])) if group else ""
                    )
                else:
                    current_columns[col] = str(
                        self._active_column_filters.get(col, "")
                    ).strip()

            for col, expected in base_columns.items():
                if current_columns.get(col, "").strip() != expected:
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
                def _group_repr(group: Any):
                    if not isinstance(group, dict):
                        return (tuple(), tuple())
                    cols_raw = group.get("columns", ())
                    vals_raw = group.get("values", ())
                    cols = (
                        tuple(cols_raw)
                        if isinstance(cols_raw, (list, tuple))
                        else tuple()
                    )
                    vals = (
                        tuple(vals_raw)
                        if isinstance(vals_raw, (list, tuple))
                        else tuple()
                    )
                    return (cols, vals)

                current_groups = sorted(
                    _group_repr(g) for g in getattr(self, "_column_or_groups", [])
                )
                expected_groups = sorted(_group_repr(g) for g in base_groups)
                if current_groups != expected_groups:
                    mismatch = True

            if not mismatch and base_exclude != bool(self._exclude_ste_sca):
                mismatch = True

            if not mismatch:
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
        """Aplica filtros pré-configurados de setor."""
        if not profile_name or profile_name not in self.filter_profiles:
            # Fallback ad-hoc: permite strings como "IEE3 + MEL3 + MEL4" para grupo Executor/Emissor
            try:
                raw = str(profile_name)
                tokens = [
                    _t.strip() for _t in re.split(r"[+,]", raw) if _t and _t.strip()
                ]
                if tokens:
                    self._reset_or_groups()
                    self._register_or_group(["setor_executor", "setor_emissor"], tokens)
                    # Garante colunas monitoradas
                    for _col in ("setor_executor", "setor_emissor"):
                        if _col not in self._profile_columns:
                            self._profile_columns.append(_col)
                    # Define filtros subjacentes separados por vírgulas (lógica)
                    new_filters = OrderedDict(self._active_column_filters or {})
                    for _col in ("setor_executor", "setor_emissor"):
                        new_filters[_col] = ", ".join(tokens)
                    self._active_column_filters = new_filters
                    # Base do perfil para marcação de personalizado
                    self._profile_base_filters = {
                        "columns": {
                            c: new_filters.get(c, "")
                            for c in ("setor_executor", "setor_emissor")
                        },
                        "or_groups": [
                            {
                                "columns": ("setor_executor", "setor_emissor"),
                                "values": tuple(tokens),
                            }
                        ],
                        "exclude_ste_sca": bool(self._exclude_ste_sca),
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
            all_section = (
                profile_def.get("all")
                if isinstance(profile_def.get("all"), dict)
                else None
            )
            if all_section:
                for col, value in all_section.items():
                    values_list = normalize_values(value)
                    normalized_columns[col] = (
                        ", ".join(values_list) if values_list else ""
                    )
                    if col not in self._profile_columns:
                        self._profile_columns.append(col)
            any_section = (
                profile_def.get("any")
                if isinstance(profile_def.get("any"), list)
                else None
            )
            if any_section:
                for group in any_section:
                    if not isinstance(group, dict):
                        continue
                    columns = (
                        group.get("columns")
                        if isinstance(group.get("columns"), list)
                        else []
                    )
                    values_list = normalize_values(group.get("values"))
                    registered = self._register_or_group(columns, values_list)
                    if registered:
                        display_values = ", ".join(registered["values"])
                        for col in registered["columns"]:
                            normalized_columns[col] = display_values
                        for col in registered["columns"]:
                            if col not in self._profile_columns:
                                self._profile_columns.append(col)
                        normalized_groups.append(
                            {
                                "columns": tuple(registered["columns"]),
                                "values": tuple(registered["values"]),
                            }
                        )
            if not all_section and "any" not in profile_def:
                for col, value in profile_def.items():
                    values_list = normalize_values(value)
                    normalized_columns[col] = (
                        ", ".join(values_list) if values_list else ""
                    )
                    if col not in self._profile_columns:
                        self._profile_columns.append(col)
        else:
            values_list = normalize_values(profile_def)
            if values_list:
                normalized_columns["situacao"] = ", ".join(values_list)
                if "situacao" not in self._profile_columns:
                    self._profile_columns.append("situacao")

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
                group_text = ", ".join(group.get("values", []))
                for col in group.get("columns", []):
                    if col not in new_filters:
                        new_filters[col] = group_text
                    else:
                        new_filters[col] = group_text
            self._active_column_filters = new_filters
            # Garante consistência das strings dos grupos OR (subjacente em vírgulas)
            for group in self._column_or_groups:
                display_group = ", ".join(group.get("values", []))
                for col in group.get("columns", []):
                    self._active_column_filters[col] = display_group
            self._profile_base_filters = {
                "columns": {
                    col: new_filters.get(col, "").strip() for col in new_filters
                },
                "or_groups": normalized_groups,
                "exclude_ste_sca": bool(self._exclude_ste_sca),
            }
            if update_selector and getattr(self, "profile_selector", None) is not None:
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
        self._refresh_after_filter_change()

    def on_profile_changed(self, index):
        """Callback ao trocar o perfil de filtros por setor."""
        if getattr(self, "_profile_lock", False):
            return
        selector = getattr(self, "profile_selector", None)
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
        tokens = [t.strip() for t in normalized.split(",") if t.strip()]
        if not tokens:
            return pd.Series([True] * len(series), index=series.index)

        # Determina modo padrao a partir das preferencias
        if not hasattr(self, "_cached_default_mode"):
            from gui.gui_config import GUI_MAIN_PREFERENCES

            gui_settings = GUI_MAIN_PREFERENCES.get("gui_settings", {})
            self._cached_default_mode = gui_settings.get(
                "default_filter_mode", "contains"
            )
        default_mode = self._cached_default_mode

        def _safe_regex_contains(s: pd.Series, pattern: str) -> pd.Series:
            pattern_text = str(pattern or "")
            if not pattern_text:
                return pd.Series([True] * len(s), index=s.index)
            has_lookaround = (
                "(?=" in pattern_text
                or "(?!" in pattern_text
                or "(?<=" in pattern_text
                or "(?<!" in pattern_text
            )
            has_backref = bool(re.search(r"\\[1-9]", pattern_text))
            meta_char_count = len(_REGEX_META_CHAR_RE.findall(pattern_text))
            has_alternation_with_quantifier = "|" in pattern_text and bool(
                re.search(r"[+*?{]", pattern_text)
            )
            if (
                len(pattern_text) > 120
                or _NESTED_QUANTIFIER_RE.search(pattern_text)
                or _HEAVY_QUANTIFIER_CHAIN_RE.search(pattern_text)
                or has_lookaround
                or has_backref
                or meta_char_count > 16
                or has_alternation_with_quantifier
            ):
                logger.warning(
                    "Regex de filtro bloqueado por seguranca; usando busca literal."
                )
                return s.str.contains(pattern_text, case=False, na=False, regex=False)
            try:
                pat = re.compile(pattern_text, re.IGNORECASE)
                return s.str.contains(pat, na=False)
            except re.error:
                return s.str.contains(pattern_text, case=False, na=False, regex=False)

        def match_token(s: pd.Series, token: str) -> pd.Series:
            neg = token.startswith("!")
            t = token[1:] if neg else token
            # VAZIOS/NULL: aceita NULL ou =NULL (case-insensitive)
            if t.upper() in ("NULL", "=NULL"):
                # Considera nulos, strings vazias e '-'
                stripped = s.str.strip()
                res = s.isna() | stripped.fillna("").eq("") | (s == "-")
                return ~res if neg else res
            # Regex explácito
            if t.startswith("~") and len(t) > 1:
                res = _safe_regex_contains(s, t[1:])
            elif t.startswith("="):
                res = s.str.casefold().eq(t[1:].casefold())
            elif t.startswith("^"):
                res = s.str.casefold().str.startswith(t[1:].casefold())
            elif t.endswith("$"):
                res = s.str.casefold().str.endswith(t[:-1].casefold())
            else:
                if default_mode == "prefix":
                    res = s.str.casefold().str.startswith(t.casefold())
                elif default_mode == "suffix":
                    res = s.str.casefold().str.endswith(t.casefold())
                elif default_mode == "exact":
                    res = s.str.casefold().eq(t.casefold())
                elif default_mode == "regex":
                    res = _safe_regex_contains(s, t)
                else:  # contains
                    res = s.str.contains(t, case=False, na=False, regex=False)
            return ~res if neg else res

        # OR entre inclusões no MESMO CAMPO; exclusões (com !) removem
        includes = [tok for tok in tokens if not tok.startswith("!")]
        excludes = [tok for tok in tokens if tok.startswith("!")]

        if includes:
            m = match_token(series, includes[0])
            for tok in includes[1:]:
                m = m | match_token(series, tok)
        else:
            m = pd.Series([True] * len(series), index=series.index)
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
        except Exception as exc:
            logger.warning(
                "Falha inesperada ao iniciar filtro via atalho filter_data: %s", exc
            )

    def load_persistent_filters(self):
        """Carrega filtros persistentes salvos."""
        self.persistent_filters = []
        path = get_gui_saved_filters_path()
        if os.path.exists(path):
            try:
                with open(path, encoding="utf-8") as handle:
                    payload = json.load(handle)
                filters = payload.get("filters") if isinstance(payload, dict) else payload
                if isinstance(filters, list):
                    loaded_filters = []
                    for item in filters:
                        if not isinstance(item, dict):
                            continue
                        name = str(item.get("name") or "").strip()
                        terms = str(item.get("terms") or "").strip()
                        state = item.get("state")
                        if not name or not isinstance(state, dict):
                            continue
                        loaded_filters.append(
                            {
                                "name": name,
                                "terms": terms,
                                "state": copy.deepcopy(state),
                            }
                        )
                    self.persistent_filters = sorted(
                        loaded_filters, key=lambda f: f["name"].casefold()
                    )
            except (OSError, json.JSONDecodeError) as exc:
                logger.warning("Falha ao carregar filtros salvos: %s", exc)
        self.update_filter_tags()

    def _save_persistent_filters_file(self) -> None:
        path = get_gui_saved_filters_path()

        def _json_safe(value):
            if isinstance(value, dict):
                return {str(key): _json_safe(val) for key, val in value.items()}
            if isinstance(value, set):
                return [_json_safe(item) for item in sorted(value, key=str)]
            if isinstance(value, (list, tuple)):
                return [_json_safe(item) for item in value]
            if value is None or isinstance(value, (str, int, float, bool)):
                return value
            return str(value)

        payload = {
            "version": 1,
            "filters": _json_safe(getattr(self, "persistent_filters", []) or []),
        }
        try:
            atomic_write_json_file(path, payload, indent=2, ensure_ascii=False)
        except Exception as exc:
            logger.warning("Falha ao salvar filtros persistentes: %s", exc)

    def save_current_filter(self):  # skipcq: PY-R1000
        """Salva o estado atual de filtros como persistente."""
        current_state = self._snapshot_filter_state()
        current_text = str(current_state.get("search_text", "") or "").strip()
        active_columns = current_state.get("active_column_filters") or {}
        active_column_values = [
            str(value).strip()
            for value in active_columns.values()
            if str(value).strip()
        ]
        has_filter_state = bool(
            current_text
            or active_column_values
            or current_state.get("column_or_groups")
            or current_state.get("exclude_ste_sca")
            or current_state.get("advanced_filters_active")
            or current_state.get("current_filter_profile")
        )
        if not has_filter_state:
            QMessageBox.information(
                _qt_parent(self),
                "Aviso",
                "Aplique algum filtro antes de salvar.",
            )
            return

        # Cria um nome baseado no filtro com truncamento por largura disponivel.
        filter_name = current_text or str(
            current_state.get("current_filter_profile") or ""
        ).strip()
        if not filter_name:
            filter_name = f"Filtro combinado {len(self.persistent_filters) + 1}"
        try:
            metrics = self.search_input.fontMetrics()
            width_px = int(
                self.search_input.width() or self.search_input.minimumWidth() or 320
            )
            available = max(64, width_px - 40)
            ellipsis = "..."
            if metrics.horizontalAdvance(filter_name) > available:
                trimmed = filter_name
                while (
                    trimmed
                    and metrics.horizontalAdvance(trimmed + ellipsis) > available
                ):
                    trimmed = trimmed[:-1]
                filter_name = (trimmed + ellipsis) if trimmed else ellipsis
        except Exception as exc:
            logger.debug(
                "Falha ao truncar nome de filtro persistente por largura: %s", exc
            )

        def _state_json_default(value):
            if isinstance(value, set):
                return sorted(value, key=str)
            return str(value)

        # Verifica se ja existe
        current_state_key = json.dumps(
            current_state,
            sort_keys=True,
            ensure_ascii=True,
            default=_state_json_default,
        )
        for f in self.persistent_filters:
            saved_state = f.get("state")
            saved_state_key = (
                json.dumps(
                    saved_state,
                    sort_keys=True,
                    ensure_ascii=True,
                    default=_state_json_default,
                )
                if isinstance(saved_state, dict)
                else ""
            )
            if saved_state_key == current_state_key or (
                not saved_state_key and f.get("terms") == current_text
            ):
                QMessageBox.information(
                    _qt_parent(self), "Aviso", "Este filtro ja esta salvo."
                )
                return

        # Adiciona novo filtro
        new_filter = {
            "name": filter_name,
            "terms": current_text,
            "state": copy.deepcopy(current_state),
        }
        self.persistent_filters.append(new_filter)
        self.persistent_filters.sort(key=lambda f: f["name"].casefold())
        self._save_persistent_filters_file()
        self.update_filter_tags()

        QMessageBox.information(
            _qt_parent(self), "Sucesso", f"Filtro '{filter_name}' salvo com sucesso!"
        )

    def update_filter_tags(self):
        """Atualiza as tags visuais dos filtros persistentes."""
        # Remove tags existentes
        for i in reversed(range(self.filter_tags_layout.count())):
            child = self.filter_tags_layout.takeAt(i)
            if child.widget():
                child.widget().deleteLater()

        roles = get_theme_roles(getattr(self, "_current_theme", "dark"))
        fg = roles.get("summary_text_color", self.palette().windowText().color().name())
        border = roles.get("tag_border")
        bg_normal = roles.get("tag_normal_bg")
        bg_hover = roles.get("tag_hover")
        bg_pressed = roles.get("tag_pressed")

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
        for filter_data in sorted(
            self.persistent_filters, key=lambda f: f["name"].casefold()
        ):
            tag_button = QPushButton(filter_data["name"])
            tag_button.setMaximumHeight(25)
            tag_button.setMaximumWidth(180)
            tag_button.setSizePolicy(
                QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed
            )
            tag_button.setStyleSheet(tag_css)
            tag_button.setToolTip(f"Clique para aplicar: {filter_data['terms']}")
            tag_button.clicked.connect(
                lambda checked,
                filter_data=filter_data: self.apply_persistent_filter(filter_data)
            )

            # Botção X para remover
            remove_button = QPushButton("X")
            remove_button.setMaximumSize(20, 20)
            remove_button.setStyleSheet(tag_css)
            remove_button.setToolTip("Remover filtro")
            remove_button.clicked.connect(
                lambda checked, filter_data=filter_data: self.remove_persistent_filter(
                    filter_data
                )
            )

            # Layout horizontal para tag + botção remover
            tag_layout = QHBoxLayout()
            tag_layout.setContentsMargins(0, 0, 0, 0)
            tag_layout.setSpacing(2)
            tag_layout.addWidget(tag_button)
            tag_layout.addWidget(remove_button)

            tag_widget = QWidget()
            tag_widget.setLayout(tag_layout)
            tag_widget.setSizePolicy(
                QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed
            )
            self.filter_tags_layout.addWidget(tag_widget)

    def apply_persistent_filter(self, filter_data):
        """Aplica um filtro persistente."""
        if isinstance(filter_data, dict) and isinstance(filter_data.get("state"), dict):
            try:
                previous_state = self._snapshot_filter_state()
            except Exception as exc:
                logger.warning(
                    "Falha ao salvar estado antes de aplicar filtro persistente: %s",
                    exc,
                )
                previous_state = None
            self._last_filter_state = copy.deepcopy(filter_data["state"])
            self._restore_last_filter_state()
            self._last_filter_state = previous_state
            self._update_undo_button_state()
            return
        if isinstance(filter_data, dict):
            terms = str(filter_data.get("terms", "") or "")
        else:
            terms = str(filter_data or "")
        self.search_input.setText(terms)
        self.initiate_filtering()
