# flake8: noqa
# gui_ssa.py (GUI PyQt6 para SSA_Consulta_Rapida)
# Last modified: 2025-10-30T16:05:00 (search simplification with explicit semantics in general/column filter tooltips)
"""
Prova de Conceito Refinada de uma Interface Gráfica (GUI) para o projeto SSA_Consulta_Rapida usando PyQt6.

Refinamentos em relação à PoC básica:
1. Seleção de colunas com base em display_mappings.json e prioridade.
2. Paginacao simples para lidar with grandes conjuntos de dados.
3. Uso de nomes de exibição para colunas.
4. Feedback mais detalhado ao usuário.
5. Estrutura mais preparada para expansão (ordenação, exportação).

Para executar: python gui_ssa.py
(Requer que o projeto ja tenha sido executado uma vez para criar o banco de dados ssas.db)
"""
# flake8: noqa

import copy
import json
import logging
import os
import re
import shutil
import subprocess  # nosec B404
import sys
import threading
from collections import OrderedDict
from datetime import datetime
from typing import Any, TypedDict, cast

import pandas as pd

try:
    from utils.version import get_app_version
except ImportError:

    def get_app_version(project_root: str | None = None) -> str:
        _ = project_root
        return "3.11+"


# --- Configuração do Path do Projeto (precisa vir antes das importações internas) ---
runtime_root_override = os.environ.get("SSA_RUNTIME_ROOT")
code_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if runtime_root_override:
    project_root = os.path.abspath(runtime_root_override)
else:
    project_root = code_root
if code_root not in sys.path:
    sys.path.insert(0, code_root)

from core.config_manager import COLUMN_AFFINITY_SCORES  # noqa: E402
from core.config_manager import DEFAULT_DISPLAY_MAPPINGS, atomic_write_json_file
from gui.gui_config import COLUMN_HEADER_LABEL_VARIANTS  # noqa: E402
from gui.gui_config import COMPATIBILITY_NULL_UI_COLUMNS  # noqa: E402
from gui.gui_config import DEFAULT_GUI_SETTINGS  # noqa: E402
from gui.gui_config import get_gui_main_preferences_path  # noqa: E402
from gui.gui_config import load_gui_main_preferences  # noqa: F401 - re-export for compatibility
from gui.gui_config import GUI_MAIN_PREFERENCES, REQUIRED_DISPLAY_COLUMNS

# Importações dos managers unificados
from gui.simple_width_manager import SimpleCacheManager  # noqa: E402
from gui.simple_width_manager import SimpleWidthManager
from gui.ssa import gui_details as ssa_gui_details  # noqa: E402
from gui.ssa import gui_filters_advanced as ssa_gui_filters  # noqa: E402
from gui.ssa import gui_table as ssa_gui_table  # noqa: E402
from gui.ssa import gui_theme as ssa_gui_theme  # noqa: E402
from gui.ssa import gui_workers as ssa_gui_workers  # noqa: E402
from gui.ssa import app_menus as ssa_app_menus  # noqa: E402
from gui.ssa import derivadas_sync_controller as ssa_derivadas_sync  # noqa: E402
from gui.ssa import database_operations as ssa_database_operations  # noqa: E402
from gui.ssa import list_export_controller as ssa_list_export_controller  # noqa: E402
from gui.ssa import system_integration as ssa_system  # noqa: E402
from gui.ssa.derivadas_table_resolver import resolve_derivadas_table_name  # noqa: E402
from gui.ssa.main_window_filter_bar import (  # noqa: E402
    build_filters_summary_bar,
    build_pagination_filter_bar,
    build_search_bar,
)
from gui.ssa import main_window_resize as ssa_gui_resize  # noqa: E402
from gui.ssa.main_window_bottom_section import build_bottom_filter_section  # noqa: E402
from gui.ssa.main_window_table_section import build_main_table_widget  # noqa: E402
from gui.ssa.table_context_menu import (  # noqa: E402
    TableContextMenuCallbacks,
    show_table_context_menu,
)
from gui.ssa import table_sorting as ssa_table_sorting  # noqa: E402
from gui.ssa.filter_domain_rules import (  # noqa: E402
    collect_nonempty_column_values,
    order_sector_values,
)
from gui.ssa.canonical_columns import (  # noqa: E402
    CanonicalColumnInputs,
    build_canonical_available_columns,
)
from gui.ssa.gui_filters_responsavel_state import (  # noqa: E402
    RESPONSAVEL_FILTER_PREFIXES,
    ResponsavelMaterializationState,
)
from shared.db_names import ALL_SSA_TABLE_NAMES  # noqa: E402
from shared.db_names import CANONICAL_SSA_TABLE

# Inicializar logging robusto
try:
    from utils.robust_logging import setup_logging

    setup_logging()
    logger = logging.getLogger(__name__)
    logger.debug(
        "Sistema de logging robusto inicializado na GUI", extra={"component": "gui"}
    )
except Exception as e:
    # Fallback para logging padrão
    logger = logging.getLogger(__name__)
    logger.error(f"Falha ao inicializar logging robusto: {e}")

# Compatibility aliases for tests and older imports. Ownership lives in gui_workers.
GLOBAL_RETIRED_DATA_LOADER_WORKERS = ssa_gui_workers.GLOBAL_RETIRED_DATA_LOADER_WORKERS
MAX_GLOBAL_RETIRED_DATA_LOADER_WORKERS = (
    ssa_gui_workers.MAX_GLOBAL_RETIRED_DATA_LOADER_WORKERS
)
GLOBAL_RETIRED_DATA_LOADER_META = ssa_gui_workers.GLOBAL_RETIRED_DATA_LOADER_META
GLOBAL_RETIRED_RESCAN_WORKERS = ssa_gui_workers.GLOBAL_RETIRED_RESCAN_WORKERS
MAX_GLOBAL_RETIRED_RESCAN_WORKERS = ssa_gui_workers.MAX_GLOBAL_RETIRED_RESCAN_WORKERS
GLOBAL_RETIRED_RESCAN_META = ssa_gui_workers.GLOBAL_RETIRED_RESCAN_META
RETIRED_WORKER_TTL_SEC = ssa_gui_workers.RETIRED_WORKER_TTL_SEC
RETIRED_WORKER_FORCE_WAIT_MS = ssa_gui_workers.RETIRED_WORKER_FORCE_WAIT_MS
logger.addHandler(logging.NullHandler())


class _DataLoaderRetentionKwargs(TypedDict):
    global_workers: list[Any]
    global_meta: dict[Any, Any]
    max_global_workers: int
    retired_ttl_sec: float
    retired_force_wait_ms: int


class _RescanRetentionKwargs(_DataLoaderRetentionKwargs):
    pass


class _CloseRetentionKwargs(TypedDict):
    data_loader_workers: list[Any]
    data_loader_meta: dict[Any, Any]
    max_data_loader_workers: int
    rescan_workers: list[Any]
    rescan_meta: dict[Any, Any]
    max_rescan_workers: int
    retired_ttl_sec: float
    retired_force_wait_ms: int


def _data_loader_retention_kwargs() -> _DataLoaderRetentionKwargs:
    return {
        "global_workers": GLOBAL_RETIRED_DATA_LOADER_WORKERS,
        "global_meta": GLOBAL_RETIRED_DATA_LOADER_META,
        "max_global_workers": MAX_GLOBAL_RETIRED_DATA_LOADER_WORKERS,
        "retired_ttl_sec": RETIRED_WORKER_TTL_SEC,
        "retired_force_wait_ms": RETIRED_WORKER_FORCE_WAIT_MS,
    }


def _rescan_retention_kwargs() -> _RescanRetentionKwargs:
    return {
        "global_workers": GLOBAL_RETIRED_RESCAN_WORKERS,
        "global_meta": GLOBAL_RETIRED_RESCAN_META,
        "max_global_workers": MAX_GLOBAL_RETIRED_RESCAN_WORKERS,
        "retired_ttl_sec": RETIRED_WORKER_TTL_SEC,
        "retired_force_wait_ms": RETIRED_WORKER_FORCE_WAIT_MS,
    }


def _close_retention_kwargs() -> _CloseRetentionKwargs:
    return {
        "data_loader_workers": GLOBAL_RETIRED_DATA_LOADER_WORKERS,
        "data_loader_meta": GLOBAL_RETIRED_DATA_LOADER_META,
        "max_data_loader_workers": MAX_GLOBAL_RETIRED_DATA_LOADER_WORKERS,
        "rescan_workers": GLOBAL_RETIRED_RESCAN_WORKERS,
        "rescan_meta": GLOBAL_RETIRED_RESCAN_META,
        "max_rescan_workers": MAX_GLOBAL_RETIRED_RESCAN_WORKERS,
        "retired_ttl_sec": RETIRED_WORKER_TTL_SEC,
        "retired_force_wait_ms": RETIRED_WORKER_FORCE_WAIT_MS,
    }


_COLUMN_FILTER_DIALOG_MIN_WIDTH = 420
_COLUMN_FILTER_DIALOG_HINT = "Aceita termo, !termo para exclusao"
_TABLE_CELL_ALIGNMENT_LABELS = {
    "left": "Esquerda",
    "center": "Centro",
    "right": "Direita",
}
_DEFAULT_TABLE_CELL_ALIGNMENT = str(DEFAULT_GUI_SETTINGS["table_cell_alignment"])

from armazenamento.database import query_db, vacuum_analyze_database  # noqa: E402
from armazenamento.derivadas_sync import (  # noqa: E402
    scan_derivadas_consistency,
    sync_derivadas,
)

# --- Importações do PyQt6 (com fallback headless para CI) ---
QT_AVAILABLE = True
try:
    from PyQt6 import sip
    from PyQt6.QtCore import (
        PYQT_VERSION_STR,
        QT_VERSION_STR,
        QEvent,
        Qt,
        QTimer,
        QUrl,
    )
    from PyQt6.QtGui import QAction, QDesktopServices, QFont
    from PyQt6.QtWidgets import (
        QApplication,
        QDialog,
        QFileDialog,
        QGridLayout,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMainWindow,
        QMenu,
        QMessageBox,
        QProgressBar,
        QPushButton,
        QSizePolicy,
        QStackedWidget,
        QTabBar,
        QTableWidget,
        QTabWidget,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )

    from gui.cache import FilterCache  # noqa: E402

    # Import mixins for code organization
    from gui.mixins import FilterGUISSAMixin  # noqa: E402
    from gui.widgets import ColumnSelector  # noqa: E402
    from gui.widgets import (
        ColumnFilterDialog,
        DataPaginator,
    )

    # Import workers, cache, widgets, and helpers from separate modules
    from gui.workers import DataLoaderWorker, FilterWorker  # noqa: E402
except ImportError as exc:
    QT_AVAILABLE = False
    logger.warning("PyQt6 import failed, using headless stub mode: %s", exc)
    from gui.ssa.headless_qt_stubs import (  # noqa: E402
        PYQT_VERSION_STR,
        QT_VERSION_STR,
        QAction,
        QApplication,
        QDesktopServices,
        QDialog,
        QEvent,
        QFileDialog,
        QFont,
        QGridLayout,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMainWindow,
        QMenu,
        QMessageBox,
        QProgressBar,
        QPushButton,
        QSizePolicy,
        QStackedWidget,
        QTabBar,
        QTabWidget,
        QTableWidget,
        QTextEdit,
        QTimer,
        QUrl,
        QVBoxLayout,
        QWidget,
        Qt,
        ColumnFilterDialog,
        ColumnSelector,
        DataLoaderWorker,
        FilterCache,
        FilterGUISSAMixin,
        FilterWorker,
        sip,
    )
    QWidget = cast(Any, QWidget)
    QApplication = cast(Any, QApplication)
    QMainWindow = cast(Any, QMainWindow)
    QVBoxLayout = cast(Any, QVBoxLayout)
    QHBoxLayout = cast(Any, QHBoxLayout)
    QGridLayout = cast(Any, QGridLayout)
    QLabel = cast(Any, QLabel)
    QPushButton = cast(Any, QPushButton)
    QLineEdit = cast(Any, QLineEdit)
    QTableWidget = cast(Any, QTableWidget)
    QProgressBar = cast(Any, QProgressBar)
    QStackedWidget = cast(Any, QStackedWidget)
    QTabBar = cast(Any, QTabBar)
    QTabWidget = cast(Any, QTabWidget)
    QMessageBox = cast(Any, QMessageBox)
    QFileDialog = cast(Any, QFileDialog)
    QMenu = cast(Any, QMenu)
    QAction = cast(Any, QAction)
    QTimer = cast(Any, QTimer)
    Qt = cast(Any, Qt)
    QEvent = cast(Any, QEvent)
    QUrl = cast(Any, QUrl)
    QDesktopServices = cast(Any, QDesktopServices)
    QSizePolicy = cast(Any, QSizePolicy)
    FilterGUISSAMixin = cast(Any, FilterGUISSAMixin)

def _is_widget_valid(widget) -> bool:
    """Return True when a Qt widget reference still points to a live object."""
    if widget is None:
        return False
    if sip is None:
        return True
    try:
        return not sip.isdeleted(widget)
    except Exception:
        return False


# --- Constantes ---
DB_PATH = os.environ.get("SSA_DB_PATH") or os.path.join(project_root, "data", "ssas.db")
TSM_DEBUG_ENABLED = str(os.environ.get("SSA_TSM_DEBUG", "")).strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}

# Constantes de UI
DETAILS_DIALOG_FONT_SIZE = 10  # pt
DETAILS_DIALOG_TABLE_PADDING = 8  # px
DETAILS_DIALOG_BORDER_COLOR = "#ccc"
HIGHLIGHT_BACKGROUND_COLOR = "yellow"
HIGHLIGHT_FONT_WEIGHT = "bold"

# Prefer explicit monospace families across Windows/macOS/Linux to avoid Qt
# trying (and failing) to resolve a generic "Monospace" alias.
MONO_FONT_FAMILY = (
    # macOS first
    "Menlo, Monaco, 'Andale Mono', "
    # Windows 11 common monospace families
    "Consolas, 'Cascadia Mono', 'Cascadia Code', 'Segoe UI Mono', 'Lucida Console', "
    # Debian / Linux common monospace families
    "'DejaVu Sans Mono', 'Liberation Mono', 'Noto Sans Mono', 'Ubuntu Mono', "
    "'Droid Sans Mono', 'FreeMono', 'Nimbus Mono L', 'Courier 10 Pitch', "
    # Popular developer fonts (often installed)
    "'Fira Code', 'Fira Mono', 'JetBrains Mono', 'Roboto Mono', "
    "Inconsolata, Hack, 'Source Code Pro', "
    # Last-resort fallbacks
    "'Courier New', Courier"
)

_TSM_DEBUG_EVENT_NAMES = {
    QEvent.Type.FocusIn: "focus_in",
    QEvent.Type.FocusOut: "focus_out",
    QEvent.Type.InputMethod: "input_method",
    QEvent.Type.InputMethodQuery: "input_method_query",
    QEvent.Type.Show: "show",
    QEvent.Type.Hide: "hide",
}

DIVISAO_SETORES = {
    "SMME": ["MEL1", "MEL2", "MEL3", "MEL4"],
    "SMIN": ["IEE1", "IEE2", "IEE3", "IEE4"],
    "SMIL": ["ILA1", "ILA2", "ILA3", "ILA4"],
    "SMMG": ["MEG1", "MEG2", "MEG3", "MEG4"],
}
SECTOR_TO_DIV = {sec: div for div, secs in DIVISAO_SETORES.items() for sec in secs}
try:
    ssa_gui_filters.configure_adv_filters_constants(
        DIVISAO_SETORES,
        SECTOR_TO_DIV,
        MONO_FONT_FAMILY,
    )
except Exception as exc:
    logger.debug("Falha ao configurar constantes de filtros avancados: %s", exc)

# Prioridade de campos para ordenacao em detalhes
DETAIL_FIELD_PRIORITY = [
    "numero_ssa",
    "situacao",
    "descricao_ssa",
    "localizacao_codigo",
    "descricao_servico",
    "setor_emissor",
    "setor_executor",
    "data_cadastro",
    "prazo_limite",
]

DETAIL_DISPLAY_OVERRIDES = {
    "situacao": "Situacao",
    "semana_cadastro": "Semana de Cadastro",
    "data_cadastro": "Data de Cadastro",
    "localizacao_codigo": "Localizacao",
    "loc": "Localizacao",
    "descricao_ssa": "Descricao da SSA",
    "setor_executor": "Setor Executor",
    "setor_emissor": "Setor Emissor",
    "responsavel_emissor": "Responsavel Emissor",
    "solicitante": "Solicitante",
    "servico_origem": "Servico de Origem",
    "grau_prioridade_emissao": "Grau de Prioridade (Emissao)",
    "grau_prioridade_planejamento": "Grau de Prioridade (Planejamento)",
    "execucao_simples": "Execucao Simples",
    "responsavel_programacao": "Responsavel pela Programacao",
    "responsavel_execucao": "Responsavel pela Execucao",
    "num_reprogramacoes": "Reprogramacoes",
    "semana_programada": "Semana Programada",
    "semana_executada": "Semana Executada",
    "prazo_limite": "Prazo Limite",
    "tempo_disponivel": "Tempo Disponivel",
    "data_limite": "Data Limite",
    "tempo_excedido": "Tempo Excedido",
    "total_tempo_tex_executada": "Tempo Total (TEX)",
    "total_tempo_tpe_executada": "Tempo Total (TPE)",
    "total_tempo_tpo_executada": "Tempo Total (TPO)",
    "numero_ssa": "Numero da SSA",
    "descricao_execucao": "Descricao da Execucao",
    "status_execucao_prazo": "Situacao do Prazo",
    "execucao_parcial": "Execucao Parcial",
}

try:
    ssa_gui_details.configure_details_constants(
        details_dialog_font_size=DETAILS_DIALOG_FONT_SIZE,
        details_dialog_table_padding=DETAILS_DIALOG_TABLE_PADDING,
        details_dialog_border_color=DETAILS_DIALOG_BORDER_COLOR,
        detail_field_priority=DETAIL_FIELD_PRIORITY,
        detail_display_overrides=DETAIL_DISPLAY_OVERRIDES,
        highlight_background_color=HIGHLIGHT_BACKGROUND_COLOR,
        highlight_font_weight=HIGHLIGHT_FONT_WEIGHT,
        mono_font_family=MONO_FONT_FAMILY,
    )
except Exception as exc:
    logger.debug("Falha ao configurar constantes de detalhes: %s", exc)

TABLE_NAME = CANONICAL_SSA_TABLE
# --- Funções Auxiliares ---


def load_display_mappings():
    """Carrega o mapeamento de nomes internos para nomes de exibiçção independente do CLI."""
    # Defensive merge keeps legacy aliases and stable labels even on partial JSON configs.
    merged_mappings = dict(DEFAULT_DISPLAY_MAPPINGS)
    merged_mappings.update(GUI_MAIN_PREFERENCES.get("column_display_names", {}))
    merged_mappings.update(GUI_MAIN_PREFERENCES.get("display_mappings", {}))
    return merged_mappings


def resolve_app_version_text() -> str:
    """Resolve versao da aplicacao para exibicao em UI."""
    try:
        app_version = str(get_app_version()).strip()
    except Exception as exc:
        logger.debug("Falha ao resolver versao da aplicacao: %s", exc)
        app_version = ""
    if not app_version:
        return "0.0.0"
    return app_version


def resolve_uv_version_text() -> str:
    """Resolve versao do uv para exibicao em UI."""
    uv_exe = shutil.which("uv")
    if not uv_exe:
        return "indisponivel"
    try:
        result = subprocess.run(  # nosec B603
            [uv_exe, "--version"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        output = str(result.stdout or result.stderr).strip()
        if output:
            return output
    except Exception as exc:
        logger.debug("Falha ao resolver versao do uv: %s", exc)
    return "indisponivel"


def _iter_build_info_candidates():
    seen = set()
    raw_candidates = []
    bundled_root = os.environ.get("SSA_BUNDLED_ROOT", "")
    if bundled_root:
        raw_candidates.append(os.path.join(bundled_root, "config", "build_info.json"))
        raw_candidates.append(
            os.path.join(bundled_root, "_internal", "config", "build_info.json")
        )
    config_dir = os.environ.get("SSA_CONFIG_DIR", "")
    if config_dir:
        raw_candidates.append(os.path.join(config_dir, "build_info.json"))
    raw_candidates.append(os.path.join(project_root, "config", "build_info.json"))
    for raw_path in raw_candidates:
        path = os.path.abspath(raw_path)
        if path in seen:
            continue
        seen.add(path)
        yield path


def _load_embedded_build_info() -> dict[str, Any]:
    for path in _iter_build_info_candidates():
        if not os.path.isfile(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
            if isinstance(payload, dict):
                return cast(dict[str, Any], payload)
        except (OSError, json.JSONDecodeError) as exc:
            logger.debug("Falha ao ler build_info %s: %s", path, exc)
    return {}


def _iter_installation_guide_candidates():
    seen = set()
    guide_rel_path = os.path.join("docs", "GUIA_MIGRACAO_NOVA_INSTALACAO.md")
    raw_candidates = [os.path.join(project_root, guide_rel_path)]
    bundled_root = os.environ.get("SSA_BUNDLED_ROOT", "")
    if bundled_root:
        raw_candidates.append(os.path.join(bundled_root, guide_rel_path))
        raw_candidates.append(
            os.path.join(bundled_root, "_internal", guide_rel_path)
        )
    for raw_path in raw_candidates:
        path = os.path.abspath(raw_path)
        if path in seen:
            continue
        seen.add(path)
        yield path


def resolve_git_commit_hash_text() -> str:
    """Resolve hash curto do commit atual para exibicao em UI."""
    git_exe = shutil.which("git")
    if not git_exe:
        return "indisponivel"
    try:
        result = subprocess.run(  # nosec B603
            [git_exe, "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
            cwd=project_root,
        )
        output = str(result.stdout or "").strip()
        if output:
            return output
    except Exception as exc:
        logger.debug("Falha ao resolver hash de commit: %s", exc)
    return "indisponivel"


def build_about_message(app_version: str) -> str:
    """Monta texto do dialogo Sobre."""
    python_version = str(sys.version.split()[0]) if sys.version else "indisponivel"
    pandas_version = str(getattr(pd, "__version__", "indisponivel"))
    pyqt_version = str(PYQT_VERSION_STR or "indisponivel")
    qt_version = str(QT_VERSION_STR or "indisponivel")
    build_info = _load_embedded_build_info()
    uv_version = resolve_uv_version_text()
    if uv_version == "indisponivel":
        uv_version = str(build_info.get("uv_version") or uv_version)
    commit_hash = resolve_git_commit_hash_text()
    if commit_hash == "indisponivel":
        commit_hash = str(
            build_info.get("git_commit_short")
            or build_info.get("git_commit")
            or commit_hash
        )
    lines = [
        "Consulta Rapida de SSAs",
        f"Versao app: {app_version}",
        "",
        f"Python: {python_version}",
        f"uv: {uv_version}",
        f"PyQt6: {pyqt_version}",
        f"Qt: {qt_version}",
        f"pandas: {pandas_version}",
        f"Commit: {commit_hash}",
    ]
    build_datetime = str(build_info.get("build_datetime") or "").strip()
    if build_datetime:
        lines.append(f"Build: {build_datetime}")
    c_compiler_version = str(build_info.get("c_compiler_version") or "").strip()
    if c_compiler_version:
        lines.append(f"C/C++: {c_compiler_version}")
    rustc_version = str(build_info.get("rustc_version") or "").strip()
    if rustc_version:
        lines.append(f"Rust: {rustc_version}")
    return "\n".join(lines)


# --- Worker Threads ---

# --- Componentes da GUI ---


# --- Janela Principal da Aplicacao ---
class SSAMainWindow(QMainWindow, FilterGUISSAMixin):
    """
    Janela principal da aplicação GUI.

    Inherits from FilterGUISSAMixin for filter-related methods.
    """

    def _set_widget_min_height_safe(
        self, widget: QWidget, height: int, label: str
    ) -> None:
        try:
            widget.setMinimumHeight(height)
        except Exception as exc:
            logger.debug("Falha ao aplicar altura minima em %s: %s", label, exc)

    def _set_widget_fixed_height_safe(
        self, widget: QWidget, height: int, label: str
    ) -> None:
        try:
            widget.setMinimumHeight(height)
            widget.setMaximumHeight(height)
        except Exception as exc:
            logger.debug("Falha ao aplicar altura fixa em %s: %s", label, exc)

    def _persist_gui_preferences(self):
        try:
            atomic_write_json_file(
                get_gui_main_preferences_path(),
                GUI_MAIN_PREFERENCES,
                indent=2,
                ensure_ascii=False,
            )
            return True
        except Exception as exc:
            logger.warning("Falha ao persistir preferencias GUI: %s", exc)
            return False

    def _resolve_startup_theme(self):
        gui_settings = GUI_MAIN_PREFERENCES.get("gui_settings", {})
        return ssa_gui_theme.resolve_startup_theme(gui_settings)

    def _bump_data_revision(self, reason: str = "") -> int:
        try:
            next_rev = int(self._data_revision or 0) + 1
        except (AttributeError, TypeError, ValueError):
            next_rev = 1
        self._data_revision = next_rev
        try:
            self._data_revision_df_ids = (id(self.df_completo), id(self.df_exibido))
        except AttributeError:
            self._data_revision_df_ids = None
        self._details_ssa_index_sources = None
        self._details_ssa_series_index = None
        self._canonical_available_columns_cache_key = None
        self._canonical_available_columns_cache = None
        if reason:
            logger.debug("Data revision bump (%s): %s", reason, next_rev)
        return next_rev

    def _ensure_data_revision(self) -> None:
        try:
            current_ids = (id(self.df_completo), id(self.df_exibido))
        except AttributeError:
            return
        if getattr(self, "_data_revision_df_ids", None) != current_ids:
            self._bump_data_revision("df_identity_change")

    def _sync_checks_to_tab_context(self) -> None:
        context = getattr(self, "_filter_panel_context", None)
        if not isinstance(context, dict):
            return
        synced = 0
        for attr, value in vars(self).items():
            if not attr.startswith("adv_") or not attr.endswith("_checks"):
                continue
            if value is None:
                continue
            context[attr] = value
            synced += 1
        logger.debug("Advanced filter checks synced to panel context: %s", synced)

    def _log_tsm_debug(self, event_name: str, *, widget_role: str, obj) -> None:
        if not TSM_DEBUG_ENABLED:
            return
        if not logger.isEnabledFor(logging.WARNING):
            return
        try:
            tab_index = (
                int(self.main_tabs.currentIndex())
                if hasattr(self, "main_tabs") and self.main_tabs is not None
                else -1
            )
        except Exception:
            tab_index = -1
        try:
            object_name = str(getattr(obj, "objectName", lambda: "")() or "")
        except Exception:
            object_name = ""
        logger.warning(
            "[TSM_DEBUG] event=%s role=%s class=%s object_name=%s tab=%s",
            event_name,
            widget_role,
            type(obj).__name__,
            object_name,
            tab_index,
        )

    def _register_tsm_debug_widget(self, widget, role: str) -> None:
        if not TSM_DEBUG_ENABLED or widget is None:
            return
        try:
            probes = getattr(self, "_tsm_debug_widget_roles", None)
            if not isinstance(probes, dict):
                probes = {}
                self._tsm_debug_widget_roles = probes
            probes[id(widget)] = str(role)
            widget.installEventFilter(self)
        except Exception as exc:
            logger.debug("Falha ao registrar widget para TSM debug (%s): %s", role, exc)

    def _setup_tsm_debug_probes(self) -> None:
        if not TSM_DEBUG_ENABLED:
            return
        try:
            self._register_tsm_debug_widget(getattr(self, "main_tabs", None), "tabs")
            context = getattr(self, "_filter_panel_context", None)
            if isinstance(context, dict):
                for key in (
                    "search_input",
                    "quick_setor_executor_combo",
                    "adv_week_emissao_start",
                    "adv_week_execucao_start",
                ):
                    self._register_tsm_debug_widget(context.get(key), f"filter.{key}")
        except Exception as exc:
            logger.debug("Falha ao instalar probes de TSM debug: %s", exc)

    def _apply_table_cell_alignment_preference(self, alignment_name: str):
        normalized = str(alignment_name or "").strip().lower()
        if normalized not in _TABLE_CELL_ALIGNMENT_LABELS:
            logger.warning(
                "Valor invalido para table_cell_alignment via menu: %r",
                alignment_name,
            )
            self.status_label.setText("Status: Alinhamento de celulas invalido.")
            return False

        gui_settings = GUI_MAIN_PREFERENCES.setdefault("gui_settings", {})
        gui_settings["table_cell_alignment"] = normalized

        for key, action in getattr(self, "_table_cell_alignment_actions", {}).items():
            try:
                action.setChecked(key == normalized)
            except Exception as exc:
                logger.debug("Falha ao atualizar check do alinhamento %s: %s", key, exc)

        persisted = self._persist_gui_preferences()
        ssa_gui_table.apply_table_cell_alignment(self, normalized)

        if persisted:
            self.status_label.setText(
                f"Status: Alinhamento das celulas definido para {_TABLE_CELL_ALIGNMENT_LABELS[normalized]}."
            )
        else:
            self.status_label.setText(
                "Status: Alinhamento aplicado, mas falhou a persistencia das preferencias."
            )
        return persisted

    def show_about_dialog(self):
        QMessageBox.information(self, "Sobre", build_about_message(self._app_version))

    def __init__(self):
        super().__init__()
        try:
            # Evita acumulo de janelas/widgets fechados (impacta performance ao reaplicar tema global).
            self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        except Exception as exc:
            logger.debug("Failed to set WA_DeleteOnClose on main window: %s", exc)
        self._app_version = resolve_app_version_text()
        self.setWindowTitle(f"Consulta Rapida de SSAs v{self._app_version}")
        self.setGeometry(100, 100, 1200, 890)
        self._last_window_width = self.width()
        # Icone da janela (prioriza .ico no Windows)
        try:
            from PyQt6.QtGui import QIcon

            if sys.platform == "darwin":
                icon_candidates = [
                    os.path.join(project_root, "resources", "app_icon.icns"),
                    os.path.join(project_root, "resources", "app_icon.png"),
                    os.path.join(project_root, "resources", "app_icon.ico"),
                    os.path.join(project_root, "resources", "app_icon.svg"),
                ]
            elif sys.platform.startswith("win"):
                icon_candidates = [
                    os.path.join(project_root, "resources", "app_icon.ico"),
                    os.path.join(project_root, "resources", "app_icon.png"),
                    os.path.join(project_root, "resources", "app_icon.svg"),
                    os.path.join(project_root, "resources", "app_icon.icns"),
                ]
            else:
                icon_candidates = [
                    os.path.join(project_root, "resources", "app_icon.png"),
                    os.path.join(project_root, "resources", "app_icon.svg"),
                    os.path.join(project_root, "resources", "app_icon.ico"),
                    os.path.join(project_root, "resources", "app_icon.icns"),
                ]
            for icon_path in icon_candidates:
                if not os.path.exists(icon_path):
                    continue
                app_icon = QIcon(icon_path)
                if app_icon.isNull():
                    continue
                self.setWindowIcon(app_icon)
                app_instance_getter = getattr(QApplication, "instance", None)
                app_instance = (
                    app_instance_getter() if callable(app_instance_getter) else None
                )
                if app_instance is not None and hasattr(app_instance, "setWindowIcon"):
                    app_instance.setWindowIcon(app_icon)
                if hasattr(QApplication, "setWindowIcon"):
                    QApplication.setWindowIcon(app_icon)
                break
        except Exception as exc:
            logger.debug("Failed to load window icon resources: %s", exc)

        self.df_completo = pd.DataFrame()
        self.df_exibido = pd.DataFrame()  # DataFrame filtrado
        self.df_para_tabela = pd.DataFrame()  # DataFrame paginado para exibiçção
        self._derivadas_sync_lock = threading.Lock()

        try:
            base_font = QFont(self.font())
            if base_font.pointSizeF() <= 0:
                base_font.setPointSizeF(11.0)
            self._info_font = base_font
        except Exception:
            self._info_font = None

        # Carrega mapeamentos de exibicao com merge defensivo para evitar labels tecnicos.
        # Fonte canonica: defaults + column_display_names + display_mappings.
        self.display_map = load_display_mappings()
        self.internal_to_display = {k: v for k, v in self.display_map.items()}

        # Colunas padrção para exibiçção (das configurações JSON)
        self.default_columns = GUI_MAIN_PREFERENCES.get(
            "display_columns", list(REQUIRED_DISPLAY_COLUMNS)
        )
        for required_col in REQUIRED_DISPLAY_COLUMNS:
            if required_col not in self.default_columns:
                self.default_columns.append(required_col)

        # Garante que colunas padrção existam no mapeamento
        self.visible_columns = [
            col
            for col in self.default_columns
            if col in self.internal_to_display or col == "#"
        ]

        # Perfis de filtro por setor (precarregados)
        self.filter_profiles = GUI_MAIN_PREFERENCES.get("filter_profiles", {})
        self.default_filter_profile = GUI_MAIN_PREFERENCES.get("default_filter_profile")
        self.current_filter_profile = None
        self._profile_base_filters = {}
        self._profile_lock = False
        self._profile_columns = self._collect_profile_columns(self.filter_profiles)
        for extra_col in ("descricao_ssa",):
            if extra_col not in self._profile_columns:
                self._profile_columns.append(extra_col)
        self._column_or_groups = []
        self._column_to_or_group = {}
        self._exclude_ste_sca = False
        self._pending_search_display = ""

        # Configurações de GUI (independentes do CLI)
        gui_settings = GUI_MAIN_PREFERENCES.get("gui_settings", {})
        self._restored_page_size = gui_settings.get("page_size", 50)

        # Inicializa managers unificados (substitui codigo frankenstein)
        self.width_manager = SimpleWidthManager()
        self.cache_manager = SimpleCacheManager()

        # Estado de ordenaçção e filtros por coluna
        self.sort_column = None
        self.sort_ascending = True
        self._active_column_filters = OrderedDict()
        self._column_filter_inputs = {}
        self._column_filter_labels = {}
        self._pending_filter_focus = None
        self._current_theme = None
        self._highlight_bg_color = HIGHLIGHT_BACKGROUND_COLOR
        self._highlight_text_color = None
        self._highlight_font_weight = HIGHLIGHT_FONT_WEIGHT
        self._df_last_search_filtered = pd.DataFrame()
        adv_default = gui_settings.get("advanced_filters_default")
        self._advanced_filters = (
            dict(adv_default) if isinstance(adv_default, dict) else {}
        )
        self._advanced_filters_active = False
        self._adv_options_dirty = True
        self._adv_cache_token = -1
        self._adv_values_cache = {}
        self._last_derivada_origem = None
        self._adv_sector_syncing = False
        self._adv_sector_handler_running = False
        self.responsavel_materialization_state = ResponsavelMaterializationState(
            all_prefixes=set(RESPONSAVEL_FILTER_PREFIXES),
            dirty_prefixes=set(RESPONSAVEL_FILTER_PREFIXES),
            built_prefixes=set(),
        )
        self._menu_pre_show_hooks = {}

        # Timer de debounce para otimização de filtros de setor (evita rebuilds excessivos)
        self._sector_debounce_delay = 300  # ms
        self._sector_debounce_timer = QTimer(self)
        self._sector_debounce_timer.setSingleShot(True)
        self._sector_debounce_timer.setInterval(self._sector_debounce_delay)
        self._sector_debounce_timer.timeout.connect(self._on_sector_debounce_timeout)

        self._initialize_profile_filter_placeholders()

        # Larguras salvas por coluna (das configurações JSON) - mantido para compatibilidade
        self._saved_gui_column_widths = GUI_MAIN_PREFERENCES.get(
            "column_widths", {}
        ).copy()

        # Debounce de filtro (da configuracao JSON).
        # Mantemos um piso para incentivar uso do botao "Aplicar" sem remover debounce.
        debounce_delay = gui_settings.get("debounce_delay", 250)
        try:
            debounce_delay = int(debounce_delay)
        except (TypeError, ValueError) as exc:
            logger.warning(
                "Valor invalido para debounce_delay nas preferencias (%s); usando fallback 250 ms.",
                exc,
            )
            debounce_delay = 250
        minimum_search_debounce_ms = 1400  # ms
        if debounce_delay < minimum_search_debounce_ms:
            debounce_delay = minimum_search_debounce_ms
        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(debounce_delay)
        self._debounce_timer.timeout.connect(self.initiate_filtering)

        # Filtros persistentes
        self.persistent_filters = []

        self.init_ui()

        # Carrega filtros apos a GUI estar configurada
        self.load_persistent_filters()
        # Aplica o tema preferido antes do auto-load
        preferred_theme = self._resolve_startup_theme()
        self.apply_theme(preferred_theme)
        try:
            GUI_MAIN_PREFERENCES.setdefault("gui_settings", {})["theme"] = (
                preferred_theme
            )
            self._persist_gui_preferences()
        except Exception as exc:
            logger.debug("Failed to persist preferred startup theme: %s", exc)
        # Aplica perfil inicial de filtros por setor
        self._apply_initial_filter_profile()

        # Auto-carregar dados na abertura (assáncrono, mantêm a janela responsiva)
        QTimer.singleShot(150, self.load_data)

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(cast(Any, central_widget))
        self._setup_app_menus()

        # --- Barra de Ferramentas Superior ---
        toolbar_layout = QHBoxLayout()

        # Botões principais de dados
        self.open_sam_button = QPushButton("Abrir SAM")
        self.open_sam_button.setToolTip("Abrir pagina principal do SAM no navegador")
        self.open_sam_button.clicked.connect(self._open_sam_home)
        toolbar_layout.addWidget(cast(Any, self.open_sam_button))

        self.load_button = QPushButton("Carregar Dados")
        self.load_button.setToolTip("Carregar dados do banco de dados existente")
        self.load_button.clicked.connect(self.load_data)
        toolbar_layout.addWidget(cast(Any, self.load_button))

        # Botões de ações
        self.rescan_button = QPushButton("Reescanear")
        self.rescan_button.setToolTip(
            "Abrir opcoes de sincronizacao do banco, incluindo importacao e reescaneamento"
        )
        self.rescan_button.clicked.connect(self.rescan_data)
        toolbar_layout.addWidget(cast(Any, self.rescan_button))

        self.update_derivadas_button = None
        # Semana Atual (YYYYWW) como indicador informativo na barra superior
        try:
            from datetime import date

            y, w, _ = date.today().isocalendar()
            week_str = f"{y}{w:02d}"
        except Exception:
            week_str = "-"
        self.week_label = QLabel(f"Semana Atual: {week_str}")
        # Destaque visual em caixa
        self._week_label_style = "font-weight:600; border:1px solid palette(mid); border-radius:4px; padding:2px 6px;"
        self.week_label.setStyleSheet(self._week_label_style)
        self.week_label.setToolTip("Semana ISO atual")
        toolbar_layout.addSpacing(6)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(cast(Any, self.week_label))
        toolbar_layout.addStretch()

        self.filtered_status_label = QLabel("Status: 0 de 0 SSAs")
        self.filtered_status_label.setStyleSheet(
            "border:1px solid palette(mid); border-radius:4px; padding:2px 6px;"
        )
        self.filtered_status_label.setMinimumWidth(170)
        self.filtered_status_label.setMaximumWidth(240)
        self.filtered_status_label.setSizePolicy(
            cast(Any, QSizePolicy.Policy.Fixed),
            cast(Any, QSizePolicy.Policy.Fixed),
        )
        toolbar_layout.addWidget(cast(Any, self.filtered_status_label))

        # Status em caixa e progresso
        self.status_label = QLabel("Status: Aguardando carregamento dos dados...")
        self.status_label.setStyleSheet(
            "border:1px solid palette(mid); border-radius:4px; padding:2px 6px;"
        )
        # Keep toolbar geometry stable even when status text gets longer.
        self.status_label.setMinimumWidth(280)
        self.status_label.setMaximumWidth(520)
        self.status_label.setSizePolicy(
            cast(Any, QSizePolicy.Policy.Preferred),
            cast(Any, QSizePolicy.Policy.Fixed),
        )
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0)

        toolbar_layout.addWidget(cast(Any, self.status_label))
        toolbar_layout.addWidget(cast(Any, self.progress_bar))

        # Botao de Tema no lado direito
        theme_button = QPushButton("Tema")
        theme_button.setToolTip("Selecionar tema em caixa de dialogo")
        theme_button.clicked.connect(self.toggle_theme_menu)
        toolbar_layout.addWidget(cast(Any, theme_button))

        main_layout.addLayout(cast(Any, toolbar_layout))
        self.main_tabs = QTabWidget()
        tab_main = QWidget()
        ctx_main = self._build_tab_content(tab_main)
        self.main_tabs.addTab(cast(Any, tab_main), "SSAs")
        try:
            tab_bar = self.main_tabs.tabBar()
            if tab_bar is not None:
                tab_bar.setVisible(False)
                tab_bar.setMaximumHeight(0)
        except Exception as exc:
            logger.debug("Falha ao ocultar barra nativa de abas: %s", exc)
        self._filter_panel_context = ctx_main
        self._active_filter_panel_kind = "columns"
        for name, value in ctx_main.items():
            if name.startswith("_"):
                continue
            setattr(self, name, value)
        try:
            self._build_column_filters_panel()
        except Exception as exc:
            logger.warning("Falha ao construir filtros por coluna iniciais: %s", exc)
        main_layout.addWidget(cast(Any, self.main_tabs))
        self._setup_tsm_debug_probes()
        try:
            QTimer.singleShot(0, self._sync_bottom_panel_heights)
        except Exception as exc:
            logger.debug(
                "Falha ao agendar sincronizacao inicial de altura dos paineis inferiores: %s",
                exc,
            )

        # --- Conecta Workers / Flags ---
        # Threads iniciadas sob demanda
        self.data_loader_thread = None
        self._retired_data_loader_workers = []
        self.filter_thread = None
        self._data_load_request_seq = 0
        self._active_data_load_request_id = 0
        self._data_revision = 0
        self._data_revision_request_id = None
        self._data_uuid = None
        self._num_reprog_sort_cache = {
            "source_marker": None,
            "source_len": 0,
            "keys_df": None,
        }
        self._mixed_text_sort_cache = {
            "column_name": None,
            "source_marker": None,
            "source_len": 0,
            "keys_df": None,
        }
        self._resize_timer_cls = QTimer
        ssa_gui_resize.initialize_resize_controller(self, QTimer)
        self._filter_request_seq = 0
        self._active_filter_request_id = 0
        self._active_filter_search_request_id = None
        self._active_filter_search_display = ""
        # Flag de fallback síncrono (para estabilizar testes headless / CI)
        self._sync_filtering = os.environ.get("SSA_SYNC_FILTER", "").lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
        # Em ambiente de testes (pytest), force modo síncrono para previsibilidade
        if not self._sync_filtering and os.environ.get("PYTEST_CURRENT_TEST"):
            self._sync_filtering = True

        # Configura cache size da configuração
        gui_settings = GUI_MAIN_PREFERENCES.get("gui_settings", {})
        cache_size = gui_settings.get("filter_cache_size", 50)
        if FilterWorker is not None and FilterCache is not None:
            FilterWorker._cache = FilterCache(max_size=cache_size)
        else:
            logger.warning(
                "FilterWorker/FilterCache indisponivel; cache de filtro nao inicializado"
            )

    def _build_tab_content(self, page: QWidget) -> dict:
        tab_layout = QVBoxLayout(page)
        tab_layout.setSpacing(4)
        ctx = {}

        # Top spacing for search row
        tab_layout.addSpacing(6)

        search_context = build_search_bar(
            self, tab_layout, action_button_style=self._week_label_style
        )
        search_input = search_context["search_input"]
        search_box = search_context["quick_search_box"]
        search_button = search_context["search_button"]
        clear_filter_button = search_context["clear_filter_button"]
        undo_filter_btn = search_context["undo_filter_btn"]
        export_list_btn = search_context["export_list_btn"]
        save_filter_button = search_context["save_filter_button"]
        filter_tags_widget = search_context["filter_tags_widget"]
        filter_tags_layout = search_context["filter_tags_layout"]
        search_help = search_context["search_help"]
        try:
            summary_context = build_filters_summary_bar(
                self, tab_layout, action_button_style=self._week_label_style
            )
        except Exception as exc:
            logger.warning(
                "Falha ao construir painel de resumo de filtros da aba: %s", exc
            )
            summary_context = {
                "filters_summary_frame": None,
                "filters_summary_label": None,
                "filters_summary_items_widget": None,
                "filters_summary_items_layout": None,
                "filters_summary_scroll": None,
                "clear_all_filters_btn": None,
            }
        filters_summary_frame = summary_context["filters_summary_frame"]
        filters_summary_label = summary_context["filters_summary_label"]
        filters_summary_items_widget = summary_context["filters_summary_items_widget"]
        filters_summary_items_layout = summary_context["filters_summary_items_layout"]
        filters_summary_scroll = summary_context["filters_summary_scroll"]
        clear_all_filters_btn = summary_context["clear_all_filters_btn"]

        pagination_context = build_pagination_filter_bar(
            self,
            tab_layout,
            column_selector_cls=ColumnSelector,
            paginator_cls=DataPaginator,
        )
        column_selector = pagination_context["column_selector"]
        quick_setor_executor_label = pagination_context["quick_setor_executor_label"]
        quick_setor_executor_combo = pagination_context["quick_setor_executor_combo"]
        paginator = pagination_context["paginator"]
        profile_selector = pagination_context["profile_selector"]
        persistent_filters_layout = pagination_context["persistent_filters_layout"]
        exclude_ste_checkbox = pagination_context["exclude_ste_checkbox"]
        col_filter_indicator = pagination_context["col_filter_indicator"]

        if (
            isinstance(self._restored_page_size, int)
            and 10 <= self._restored_page_size <= 500
        ):
            try:
                paginator.page_size_spinbox.setValue(self._restored_page_size)
            except Exception as exc:
                logger.debug("Falha ao restaurar page size na paginacao: %s", exc)
        try:
            paginator.page_size_spinbox.valueChanged.connect(self._save_page_size_pref)
        except Exception as exc:
            logger.warning(
                "Falha ao conectar persistencia de page size na paginacao: %s", exc
            )

        table_widget = build_main_table_widget(self)
        tab_layout.addWidget(cast(Any, table_widget), 6)

        bottom_context = build_bottom_filter_section(self)
        bottom_layout = bottom_context.pop("_bottom_layout")
        adv_ctx = bottom_context.pop("_adv_ctx")
        tab_layout.addSpacing(0)
        tab_layout.addLayout(bottom_layout, 4)

        ctx.update(
            {
                "search_input": search_input,
                "quick_search_box": search_box,
                "search_button": search_button,
                "clear_filter_button": clear_filter_button,
                "save_filter_button": save_filter_button,
                "column_selector": column_selector,
                "quick_setor_executor_label": quick_setor_executor_label,
                "quick_setor_executor_combo": quick_setor_executor_combo,
                "search_help": search_help,
                "paginator": paginator,
                "profile_selector": profile_selector,
                "persistent_filters_layout": persistent_filters_layout,
                "filter_tags_widget": filter_tags_widget,
                "filter_tags_layout": filter_tags_layout,
                "exclude_ste_checkbox": exclude_ste_checkbox,
                "col_filter_indicator": col_filter_indicator,
                "filters_summary_frame": filters_summary_frame,
                "filters_summary_label": filters_summary_label,
                "filters_summary_items_widget": filters_summary_items_widget,
                "filters_summary_items_layout": filters_summary_items_layout,
                "filters_summary_scroll": filters_summary_scroll,
                "clear_all_filters_btn": clear_all_filters_btn,
                "export_list_btn": export_list_btn,
                "undo_filter_btn": undo_filter_btn,
                "table_widget": table_widget,
            }
        )
        ctx.update(bottom_context)
        ctx.update(adv_ctx)
        self._adv_ctx = adv_ctx
        return ctx

    def _get_canonical_available_columns(self) -> list[str]:
        """Retorna colunas elegiveis para seletores de UI (sem legados invalidos)."""
        allowed_columns_text = str(os.environ.get("SSA_ALLOWED_COLUMNS", "") or "")
        inputs = CanonicalColumnInputs(
            visible_columns=tuple(getattr(self, "visible_columns", None) or ()),
            default_columns=tuple(getattr(self, "default_columns", None) or ()),
            profile_columns=tuple(getattr(self, "_profile_columns", None) or ()),
            current_display_columns=tuple(
                getattr(self, "_current_display_columns", None) or ()
            ),
            active_filter_columns=tuple(
                (getattr(self, "_active_column_filters", {}) or {}).keys()
            ),
            widget_columns=tuple(
                (getattr(self, "_column_filter_widgets", {}) or {}).keys()
            ),
            non_null_columns=tuple(getattr(self, "_non_null_cols_cache", set()) or ()),
            allowed_columns_text=allowed_columns_text,
            default_display_mappings=DEFAULT_DISPLAY_MAPPINGS,
            internal_to_display=getattr(self, "internal_to_display", None),
            display_map=getattr(self, "display_map", None),
            compatibility_null_ui_columns=set(COMPATIBILITY_NULL_UI_COLUMNS),
        )
        source_key = inputs.cache_key(int(getattr(self, "_data_revision", 0) or 0))
        if source_key == getattr(self, "_canonical_available_columns_cache_key", None):
            cached = getattr(self, "_canonical_available_columns_cache", None)
            if isinstance(cached, list):
                return [str(column) for column in cached]

        try:
            result = build_canonical_available_columns(inputs)
        except Exception as exc:
            logger.debug(
                "Falha ao montar lista canonica de colunas de filtro: %s", exc
            )
            result = []
        self._canonical_available_columns_cache_key = source_key
        self._canonical_available_columns_cache = list(result)
        return result

    def _schedule_adv_options_refresh(self):
        if getattr(self, "_adv_options_scheduled", False):
            return
        self._adv_options_scheduled = True
        try:
            QTimer.singleShot(0, self._run_adv_options_refresh)
        except Exception as exc:
            logger.warning("Falha ao agendar refresh de filtros avancados: %s", exc)
            self._adv_options_scheduled = False
            try:
                self._run_adv_options_refresh()
            except Exception as fallback_exc:
                logger.warning(
                    "Falha no fallback de refresh de filtros avancados: %s",
                    fallback_exc,
                )

    def _run_adv_options_refresh(self):
        self._adv_options_scheduled = False
        if getattr(self, "_active_filter_panel_kind", None) != "advanced":
            return
        if not getattr(self, "_adv_options_dirty", False):
            return
        try:
            self._refresh_advanced_filter_options()
            self._sync_advanced_executor_ui_from_active_filter()
            self._adv_options_dirty = False
        except Exception as exc:
            logger.warning("Falha ao executar refresh de filtros avancados: %s", exc)

    def _compute_bottom_panel_target_height(self) -> int:
        try:
            window_height = int(self.height())
        except Exception:
            window_height = 900
        if window_height <= 0:
            window_height = 900
        try:
            base_font_pt = int(self.font().pointSize())
        except Exception:
            base_font_pt = 10
        if base_font_pt <= 0:
            base_font_pt = 10
        base_height = int(window_height * 0.31)
        font_adjust = max(0, base_font_pt - 10) * 8
        target = base_height + font_adjust
        return max(250, min(320, target))

    def _queue_bottom_panel_height_sync(self) -> None:
        try:
            QTimer.singleShot(0, self._sync_bottom_panel_heights)
        except Exception as exc:
            logger.debug(
                "Falha ao enfileirar sincronizacao de altura dos paineis inferiores: %s",
                exc,
            )
            self._sync_bottom_panel_heights()

    def _sync_bottom_panel_heights(self) -> None:
        target = self._compute_bottom_panel_target_height()
        seen = set()
        groups = []
        context = getattr(self, "_filter_panel_context", None)
        if isinstance(context, dict):
            for key in ("details_group", "col_filters_group", "adv_filters_group"):
                widget = context.get(key)
                if widget is None:
                    continue
                wid = id(widget)
                if wid in seen:
                    continue
                seen.add(wid)
                groups.append(widget)
        for widget in groups:
            self._set_widget_fixed_height_safe(
                widget, target, f"painel inferior {type(widget).__name__}"
            )
        try:
            current_kind = getattr(self, "_active_filter_panel_kind", None)
            if (
                current_kind == "advanced"
                and hasattr(self, "adv_filters_group")
                and self.adv_filters_group is not None
            ):
                self._reorganize_advanced_filters_grid(self.adv_filters_group.width())
        except Exception as exc:
            logger.debug(
                "Falha ao reorganizar painel avancado apos sync de altura: %s", exc
            )

    def _make_multiselect_box(
        self,
        title: str,
        placeholder: str = "Selecionar",
        with_exclude: bool = True,
        layout_baseline=None,
    ):
        return ssa_gui_filters._make_multiselect_box(
            self,
            title,
            placeholder,
            with_exclude,
            layout_baseline=layout_baseline,
        )

    def _set_menu_pre_show_hook(self, button, callback):
        return ssa_gui_filters._set_menu_pre_show_hook(self, button, callback)

    def _run_menu_pre_show_hook(self, button):
        return ssa_gui_filters._run_menu_pre_show_hook(self, button)

    def _set_checkbox_checked_quietly(self, checkbox, checked: bool):
        return ssa_gui_filters._set_checkbox_checked_quietly(self, checkbox, checked)

    def _sync_responsavel_flags(self):
        return ssa_gui_filters._sync_responsavel_flags(self)

    def _mark_responsavel_dirty(self, prefixes=None):
        return ssa_gui_filters._mark_responsavel_dirty(self, prefixes)

    def _on_sector_debounce_timeout(self):
        return ssa_gui_filters._on_sector_debounce_timeout(self)

    def _ensure_responsavel_options_materialized(
        self, target_prefix: str | None = None, force: bool = False
    ):
        return ssa_gui_filters._ensure_responsavel_options_materialized(
            self, target_prefix, force
        )

    def _sync_responsavel_button_summaries(self, only_prefixes=None):
        return ssa_gui_filters._sync_responsavel_button_summaries(self, only_prefixes)

    def _attach_multiselect_menu(self, button, menu):
        return ssa_gui_filters._attach_multiselect_menu(self, button, menu)

    def _update_multiselect_button(
        self, button, checks, placeholder: str = "Selecionar", exclude_checks=None
    ):
        return ssa_gui_filters._update_multiselect_button(
            self, button, checks, placeholder, exclude_checks
        )

    def _rebuild_multiselect_menu(
        self,
        button,
        menu,
        values,
        selected_set,
        on_toggle=None,
        show_footer=None,
        exclude_selected_set=None,
        on_exclude_toggle=None,
    ):
        return ssa_gui_filters._rebuild_multiselect_menu(
            self,
            button,
            menu,
            values,
            selected_set,
            on_toggle,
            show_footer,
            exclude_selected_set,
            on_exclude_toggle,
        )

    def _checkbox_value(self, checkbox):
        return ssa_gui_filters._checkbox_value(self, checkbox)

    def _sync_multiselect_checks(
        self, button, checks, selected, exclude_checks=None, exclude_selected=None
    ):
        return ssa_gui_filters._sync_multiselect_checks(
            self, button, checks, selected, exclude_checks, exclude_selected
        )

    def _build_advanced_filters_panel(self):
        return ssa_gui_filters._build_advanced_filters_panel(self)

    def _show_derivadas_popup(self):
        return ssa_gui_filters._show_derivadas_popup(self)

    def _build_derivadas_tree(
        self, df: pd.DataFrame, numero_col: str, derivada_col: str
    ):
        cache_token = ssa_gui_filters._cache_token(
            getattr(self, "_data_load_request_seq", None),
            getattr(self, "_active_data_load_request_id", None),
            (id(df), df.shape, getattr(self, "_data_uuid", None)),
        )
        return ssa_gui_filters._build_derivadas_tree(
            self,
            df,
            numero_col,
            derivada_col,
            cache_token=cache_token,
            normalize_ssa_series=self._normalize_ssa_series,
        )

    def _update_derivadas_button_state(self):
        return ssa_gui_filters._update_derivadas_button_state(self)

    def _save_advanced_filters_default(self):
        return ssa_gui_filters._save_advanced_filters_default(self)

    def _on_macro_filter_changed(self):
        return ssa_gui_filters._on_macro_filter_changed(self)

    def _reorganize_advanced_filters_grid(self, width: int):
        return ssa_gui_filters._reorganize_advanced_filters_grid(self, width)

    def _on_adv_sector_selection_changed(self, *_):
        return ssa_gui_filters._on_adv_sector_selection_changed(self, *_)

    def _on_adv_sector_exclude_changed(self, *_):
        return ssa_gui_filters._on_adv_sector_exclude_changed(self, *_)

    def _schedule_sector_options_refresh(self):
        return ssa_gui_filters._schedule_sector_options_refresh(self)

    def _collect_divisao_setores(self, divisao_values):
        return ssa_gui_filters._collect_divisao_setores(self, divisao_values)

    def _sector_sort_key(self, sector: str):
        return ssa_gui_filters._sector_sort_key(self, sector)

    def _sort_sectors(self, values):
        return ssa_gui_filters._sort_sectors(self, values)

    def _sort_responsavel_values(
        self, df_subset, values, resp_col: str, df_source=None
    ):
        return ssa_gui_filters._sort_responsavel_values(
            self, df_subset, values, resp_col, df_source=df_source
        )

    def _apply_divisao_to_setor_checks(self):
        return ssa_gui_filters._apply_divisao_to_setor_checks(self)

    def _refresh_responsavel_options(self, target_prefixes=None):
        return ssa_gui_filters._refresh_responsavel_options(self, target_prefixes)

    def _clear_advanced_filters(self):
        return ssa_gui_filters._clear_advanced_filters(self)

    def _has_active_advanced_filters(self, data: dict):
        handler = getattr(ssa_gui_filters, "_has_active_advanced_filters", None)
        if callable(handler):
            return handler(self, data)
        from gui.ssa import (
            gui_filters_advanced_ui as ssa_gui_filters_ui,
        )  # local fallback during split

        fallback_handler = getattr(
            ssa_gui_filters_ui, "_has_active_advanced_filters", None
        )
        if callable(fallback_handler):
            return fallback_handler(self, data)
        logger.warning(
            "Advanced filters activity handler is unavailable; assuming inactive filters."
        )
        return False

    def _apply_advanced_filters_from_ui(self, store_only: bool = False):
        return ssa_gui_filters._apply_advanced_filters_from_ui(self, store_only)

    def _parse_week(self, raw: str):
        return ssa_gui_filters._parse_week(self, raw)

    def _get_checked_values(self, source):
        return ssa_gui_filters._get_checked_values(self, source)

    def _sync_advanced_filter_ui(self):
        return ssa_gui_filters._sync_advanced_filter_ui(self)

    def _refresh_sector_menus(
        self, exec_vals, emis_vals, status_vals, filters, apply_cb
    ):
        return ssa_gui_filters._refresh_sector_menus(
            self, exec_vals, emis_vals, status_vals, filters, apply_cb
        )

    def _refresh_year_menus(self, emissao_years, execucao_years, filters, apply_cb):
        return ssa_gui_filters._refresh_year_menus(
            self, emissao_years, execucao_years, filters, apply_cb
        )

    def _refresh_priority_menus(
        self, prio_emissao_vals, prio_planejamento_vals, filters, apply_cb
    ):
        return ssa_gui_filters._refresh_priority_menus(
            self, prio_emissao_vals, prio_planejamento_vals, filters, apply_cb
        )

    def _refresh_reprogramacoes_menu(self, reprog_vals, filters, apply_cb):
        return ssa_gui_filters._refresh_reprogramacoes_menu(
            self, reprog_vals, filters, apply_cb
        )

    def _refresh_advanced_filter_options(self):
        return ssa_gui_filters._refresh_advanced_filter_options(self)

    def _apply_advanced_filters(self, df: pd.DataFrame):
        cache_token = ssa_gui_filters._cache_token(
            getattr(self, "_data_load_request_seq", None),
            getattr(self, "_active_data_load_request_id", None),
            (id(df), df.shape, getattr(self, "_data_uuid", None)),
        )
        notice_callback = getattr(self, "_adv_notice_callback", None)
        return ssa_gui_filters._apply_advanced_filters(
            self,
            df,
            cache_token=cache_token,
            normalize_ssa_series=self._normalize_ssa_series,
            notice_callback=notice_callback,
        )

    def load_data(self):
        ssa_gui_workers.load_data(
            self,
            db_path=DB_PATH,
            table_name=TABLE_NAME,
            data_loader_cls=DataLoaderWorker,
            qmessagebox=QMessageBox,
            **_data_loader_retention_kwargs(),
            sip_module=sip,
        )

    def on_data_loaded(self, df: pd.DataFrame, request_id: int | None = None):
        ssa_gui_workers.on_data_loaded(self, df, request_id=request_id)
        try:
            self._refresh_quick_setor_executor_options()
            self._sync_quick_setor_executor_combo_from_filters()
            self._sync_advanced_executor_ui_from_active_filter()
        except Exception as exc:
            logger.debug(
                "Falha ao atualizar combo rapido de setor executor apos carga: %s", exc
            )

    def on_load_error(self, error_msg: str, request_id: int | None = None):
        ssa_gui_workers.on_load_error(
            self,
            error_msg,
            request_id=request_id,
            db_path=DB_PATH,
            qmessagebox=QMessageBox,
            **_data_loader_retention_kwargs(),
            sip_module=sip,
        )

    def on_load_finished(self, worker=None, request_id: int | None = None):
        ssa_gui_workers.on_load_finished(
            self,
            worker=worker,
            request_id=request_id,
            **_data_loader_retention_kwargs(),
            sip_module=sip,
        )

    def _sort_num_reprogramacoes_robust(self, ascending: bool) -> pd.DataFrame:
        return ssa_table_sorting.sort_num_reprogramacoes_robust(self, ascending)

    def _build_num_reprogramacoes_sort_keys(
        self, source_df: pd.DataFrame
    ) -> pd.DataFrame:
        return ssa_table_sorting.build_num_reprogramacoes_sort_keys(source_df)

    def _should_use_mixed_text_sort(self, column_name: str) -> bool:
        return ssa_table_sorting.should_use_mixed_text_sort(
            self.df_exibido, column_name
        )

    def _build_mixed_text_sort_keys(self, source_series: pd.Series) -> pd.DataFrame:
        return ssa_table_sorting.build_mixed_text_sort_keys(source_series)

    def _get_mixed_text_sort_keys(
        self, source_df: pd.DataFrame, column_name: str
    ) -> pd.DataFrame:
        return ssa_table_sorting.get_mixed_text_sort_keys(
            self, source_df, column_name
        )

    def _sort_mixed_text_column_robust(
        self, column_name: str, ascending: bool
    ) -> pd.DataFrame:
        return ssa_table_sorting.sort_mixed_text_column_robust(
            self, column_name, ascending
        )

    def _reset_mixed_text_sort_cache(self) -> None:
        self._mixed_text_sort_cache = {
            "column_name": None,
            "source_marker": None,
            "source_len": 0,
            "keys_df": None,
        }

    def _get_num_reprogramacoes_sort_keys(self) -> pd.DataFrame:
        return ssa_table_sorting.get_num_reprogramacoes_sort_keys(self)

    def _reset_num_reprogramacoes_sort_cache(self) -> None:
        self._num_reprog_sort_cache = {
            "source_marker": None,
            "source_len": 0,
            "keys_df": None,
        }

    def _prime_num_reprogramacoes_sort_cache(self) -> None:
        ssa_table_sorting.prime_num_reprogramacoes_sort_cache(self)

    def _resolve_header_column_name(self, logical_index: int) -> str | None:
        if logical_index < 0 or self.table_widget.columnCount() == 0:
            return None
        current_columns = list(getattr(self, "_current_display_columns", []) or [])
        if not current_columns or logical_index >= len(current_columns):
            return None
        resolved = str(current_columns[logical_index] or "").strip()
        if not resolved or resolved == "#":
            return None
        return resolved

    def on_header_clicked(self, logical_index: int):
        try:
            col_name = self._resolve_header_column_name(logical_index)
            if not col_name:
                return
            preserved_widths = self._capture_current_column_widths()
            self._skip_width_recompute_once = True

            # Alterna direçção ao clicar na mesma coluna
            if getattr(self, "sort_column", None) == col_name:
                self.sort_ascending = not getattr(self, "sort_ascending", True)
            else:
                self.sort_column = col_name
                self.sort_ascending = True

            # Ordena resultado filtrado atual e reinicia paginaçção
            try:
                if self.sort_column == "num_reprogramacoes":
                    self.df_exibido = self._sort_num_reprogramacoes_robust(
                        self.sort_ascending
                    )
                    sorted_keys = getattr(self, "_last_num_reprog_sorted_keys", None)
                    if isinstance(
                        sorted_keys, pd.DataFrame
                    ) and sorted_keys.index.equals(self.df_exibido.index):
                        ssa_table_sorting.store_num_reprogramacoes_sort_cache(
                            self, self.df_exibido, sorted_keys
                        )
                    else:
                        self._prime_num_reprogramacoes_sort_cache()
                    self._last_num_reprog_sorted_keys = None
                else:
                    if self._should_use_mixed_text_sort(self.sort_column):
                        self.df_exibido = self._sort_mixed_text_column_robust(
                            self.sort_column, self.sort_ascending
                        )
                    else:
                        self.df_exibido = self.df_exibido.sort_values(
                            by=self.sort_column,
                            ascending=self.sort_ascending,
                            na_position="last",
                        )
                self._bump_data_revision("sort_column")
            except Exception as exc:
                logger.warning(
                    "Falha ao ordenar coluna '%s' (ascending=%s): %s",
                    self.sort_column,
                    self.sort_ascending,
                    exc,
                )

            self.paginator.set_dataframe(self.df_exibido)
            current_page = max(
                1,
                min(
                    getattr(self.paginator, "current_page", 1),
                    getattr(self.paginator, "total_pages", 1),
                ),
            )
            self.display_current_page(current_page, update_details=False)
            self._restore_column_widths(preserved_widths)

            # Indicador visual na UI
            try:
                header = self.table_widget.horizontalHeader()
                order = (
                    Qt.SortOrder.AscendingOrder
                    if self.sort_ascending
                    else Qt.SortOrder.DescendingOrder
                )
                header.setSortIndicatorShown(True)
                header.setSortIndicator(logical_index, order)
            except Exception as exc:
                logger.debug(
                    "Falha ao atualizar indicador visual de ordenacao: %s", exc
                )
        except Exception as exc:
            logger.exception("Erro ao processar clique no cabecalho da tabela: %s", exc)

    # --- Filtro por coluna via clique direito no cabeçalho ---
    def _prompt_column_filter_term(self, full_name: str, initial_value: str = ""):
        if not QT_AVAILABLE or ColumnFilterDialog is None:
            return None
        try:
            if TSM_DEBUG_ENABLED:
                logger.warning(
                    "[TSM_DEBUG] open_column_filter_dialog column=%s has_initial=%s",
                    full_name,
                    bool(str(initial_value or "").strip()),
                )
            dialog = ColumnFilterDialog(
                full_name,
                str(initial_value or ""),
                hint_text=_COLUMN_FILTER_DIALOG_HINT,
                min_width=_COLUMN_FILTER_DIALOG_MIN_WIDTH,
                parent=self,
            )
            try:
                dialog._position_on_parent_screen()
            except Exception as exc:
                logger.debug(
                    "Falha ao posicionar dialogo de filtro por coluna na tela ativa: %s",
                    exc,
                )
            accepted = dialog.exec() == QDialog.DialogCode.Accepted
            if not accepted:
                return None
            return dialog.get_value()
        except Exception as exc:
            logger.debug("Falha ao abrir dialogo de filtro por coluna: %s", exc)
            return None

    def _resolve_column_filter_prompt_name(self, col_name: str) -> str:
        variants = COLUMN_HEADER_LABEL_VARIANTS.get(str(col_name), {})
        for key in ("long", "medium"):
            value = str(variants.get(key) or "").strip()
            if value:
                return value
        return self._resolve_column_display_name(col_name)

    def show_header_context_menu(self, pos):
        try:
            header = self.table_widget.horizontalHeader()
            logical_index = header.logicalIndexAt(pos)
            col_name = self._resolve_header_column_name(logical_index)
            if not col_name:
                return

            menu = QMenu(self)
            full_name = self._resolve_column_filter_prompt_name(col_name)
            apply_action = QAction(f"Filtrar '{full_name}'...", self)
            clear_action = QAction("Limpar filtro desta coluna", self)
            clear_all_action = QAction("Limpar todos filtros de colunas", self)
            best_fit_visible_action = QAction("Best fit colunas visiveis", self)
            show_all_affinity_action = QAction("Exibir todas colunas (afinidade)", self)

            def _apply():
                term = self._prompt_column_filter_term(
                    full_name,
                    str(self._active_column_filters.get(col_name, "")).strip(),
                )
                if term is not None:
                    normalized_term = str(term).strip()
                    if (
                        str(self._active_column_filters.get(col_name, "")).strip()
                        != normalized_term
                    ):
                        self._safe_store_last_filter_state(
                            "header_context_apply_column_filter"
                        )
                    self._active_column_filters[col_name] = normalized_term
                    self._mark_profile_as_custom()
                    self._build_column_filters_panel()
                    self._refresh_after_filter_change()

            def _clear():
                self._clear_single_column_filter(col_name)

            def _clear_all():
                self._clear_all_column_filters()

            apply_action.triggered.connect(_apply)
            clear_action.triggered.connect(_clear)
            clear_all_action.triggered.connect(_clear_all)
            best_fit_visible_action.triggered.connect(self.best_fit_visible_columns)
            show_all_affinity_action.triggered.connect(
                self._show_all_columns_by_affinity
            )

            cast(Any, menu).addAction(apply_action)
            if col_name in self._active_column_filters:
                cast(Any, menu).addAction(clear_action)
            if self._active_column_filters:
                cast(Any, menu).addAction(clear_all_action)
            cast(Any, menu).addAction(best_fit_visible_action)
            cast(Any, menu).addAction(show_all_affinity_action)
            menu.exec(header.mapToGlobal(pos))
        except Exception as exc:
            logger.debug("Falha ao abrir menu de contexto do header da tabela: %s", exc)

    def eventFilter(self, obj, event):
        try:
            if TSM_DEBUG_ENABLED:
                probes = getattr(self, "_tsm_debug_widget_roles", None)
                if isinstance(probes, dict):
                    role = probes.get(id(obj))
                    event_name = _TSM_DEBUG_EVENT_NAMES.get(event.type())
                    if role and event_name:
                        self._log_tsm_debug(event_name, widget_role=role, obj=obj)
            header = self.table_widget.horizontalHeader()
            if obj is header:
                et = event.type()
                if et == QEvent.Type.ContextMenu:
                    self.show_header_context_menu(event.pos())
                    return True
                # Qt6: MouseButtonPress com botção direito
                if et == QEvent.Type.MouseButtonPress:
                    btn = getattr(event, "button", lambda: None)()
                    if btn == Qt.MouseButton.RightButton:
                        # Compatável com position() (Qt6) e pos()
                        pos = getattr(event, "position", None)
                        if callable(pos):
                            p = pos().toPoint()
                        else:
                            p = event.pos()
                        self.show_header_context_menu(p)
                        return True
            details_viewport = getattr(self, "_details_text_viewport", None)
            if obj is details_viewport and event.type() in (
                QEvent.Type.MouseButtonPress,
                QEvent.Type.MouseButtonDblClick,
            ):
                pos = getattr(event, "position", None)
                if callable(pos):
                    point = pos().toPoint()
                else:
                    point = event.pos()
                details_text = getattr(self, "details_text", None)
                anchor = ""
                if details_text is not None:
                    try:
                        anchor = str(details_text.anchorAt(point) or "")
                    except Exception:
                        anchor = ""
                if anchor.startswith("copy-ssa:"):
                    target = anchor[len("copy-ssa:") :].strip().lstrip("/")
                    if target:
                        self._copy_ssa_to_clipboard(target)
                        return True
        except Exception as exc:
            logger.debug("Falha no eventFilter do header da tabela: %s", exc)
        return super().eventFilter(obj, event)

    # --- Helpers: painel e aplicaçção dos filtros por coluna ---
    def toggle_theme_menu(self):
        if TSM_DEBUG_ENABLED:
            logger.warning("[TSM_DEBUG] open_theme_dialog")
        return ssa_gui_theme.show_theme_selection_dialog(
            self,
            gui_prefs=GUI_MAIN_PREFERENCES,
            project_root=project_root,
        )

    def apply_theme(self, name: str):
        ssa_gui_theme.apply_theme(
            self,
            name,
            gui_prefs=GUI_MAIN_PREFERENCES,
            project_root=project_root,
            highlight_defaults=(HIGHLIGHT_BACKGROUND_COLOR, HIGHLIGHT_FONT_WEIGHT),
        )

    def on_columns_changed(self, new_columns):
        """Chamado quando a seleçção de colunas muda."""
        self.visible_columns = list(new_columns)
        if hasattr(self, "column_selector") and self.column_selector is not None:
            try:
                self.column_selector.set_selected_columns(self.visible_columns)
            except Exception as exc:
                logger.debug(
                    "Falha ao sincronizar colunas selecionadas no selector: %s", exc
                )
        # Reexibe a pãgina atual com as novas colunas
        self.display_current_page(self.paginator.current_page, update_details=False)
        try:
            self._persist_visible_columns_order()
        except Exception as exc:
            logger.debug(
                "Falha ao persistir estado de colunas visiveis apos alteracao: %s", exc
            )

    def _persist_visible_columns_order(self) -> None:
        ordered_visible_columns = []
        seen_visible = set()
        for column_name in list(self.visible_columns):
            if not isinstance(column_name, str):
                continue
            cleaned = column_name.strip()
            if not cleaned or cleaned == "#" or cleaned in seen_visible:
                continue
            seen_visible.add(cleaned)
            ordered_visible_columns.append(cleaned)

        available_columns = []
        selector = getattr(self, "column_selector", None)
        if selector is not None:
            available_columns.extend(getattr(selector, "available_columns", []) or [])
        available_columns.extend(getattr(self, "default_columns", []) or [])
        available_columns.extend(GUI_MAIN_PREFERENCES.get("display_columns", []) or [])
        available_columns.extend(GUI_MAIN_PREFERENCES.get("hidden_columns", []) or [])
        display_map = getattr(self, "display_map", None)
        if isinstance(display_map, dict):
            available_columns.extend(display_map.keys())

        known_columns = []
        seen_known = set()
        for column_name in available_columns:
            if not isinstance(column_name, str):
                continue
            cleaned = column_name.strip()
            if not cleaned or cleaned == "#" or cleaned in seen_known:
                continue
            seen_known.add(cleaned)
            known_columns.append(cleaned)

        hidden_columns = [
            column_name
            for column_name in known_columns
            if column_name not in seen_visible
        ]

        current_display = GUI_MAIN_PREFERENCES.setdefault("display_columns", [])
        current_hidden = GUI_MAIN_PREFERENCES.setdefault("hidden_columns", [])
        if (
            current_display == ordered_visible_columns
            and current_hidden == hidden_columns
        ):
            return
        GUI_MAIN_PREFERENCES["display_columns"] = list(ordered_visible_columns)
        GUI_MAIN_PREFERENCES["hidden_columns"] = list(hidden_columns)
        if os.environ.get("PYTEST_CURRENT_TEST"):
            return
        snapshot = copy.deepcopy(GUI_MAIN_PREFERENCES)
        snapshot["display_columns"] = list(ordered_visible_columns)
        snapshot["hidden_columns"] = list(hidden_columns)
        try:
            atomic_write_json_file(
                get_gui_main_preferences_path(),
                snapshot,
                indent=2,
                ensure_ascii=False,
            )
        except Exception as exc:
            logger.warning(
                "Falha ao persistir nova ordem de colunas apos drag no header: %s", exc
            )

    def _on_header_section_moved(
        self,
        logical_index: int,
        old_visual_index: int,
        new_visual_index: int,
    ) -> None:
        _ = old_visual_index
        _ = new_visual_index
        if bool(getattr(self, "_header_order_sync_suspended", False)):
            return
        header = self.table_widget.horizontalHeader()
        if header is None:
            return
        current_columns = list(getattr(self, "_current_display_columns", []) or [])
        if (
            not current_columns
            or logical_index < 0
            or logical_index >= len(current_columns)
        ):
            return
        if current_columns[0] == "#" and header.visualIndex(0) != 0:
            try:
                self._header_order_sync_suspended = True
                header.moveSection(header.visualIndex(0), 0)
            except Exception as exc:
                logger.debug("Falha ao restaurar coluna # apos drag: %s", exc)
            finally:
                self._header_order_sync_suspended = False
        ordered_columns = ssa_gui_table._get_header_visual_column_order(self)
        if not ordered_columns:
            return
        ordered_visible_columns = [col for col in ordered_columns if col != "#"]
        if not ordered_visible_columns:
            return
        current_visible_columns = list(getattr(self, "visible_columns", []) or [])
        missing_visible_columns = [
            column_name
            for column_name in current_visible_columns
            if column_name not in ordered_visible_columns
        ]
        merged_visible_columns = ordered_visible_columns + missing_visible_columns
        if (
            not merged_visible_columns
            or merged_visible_columns == current_visible_columns
        ):
            return
        preserved_widths = self._capture_current_column_widths()
        self._current_display_columns = list(ordered_columns)
        self.visible_columns = merged_visible_columns
        if hasattr(self, "column_selector") and self.column_selector is not None:
            try:
                self.column_selector.set_selected_columns(self.visible_columns)
            except Exception as exc:
                logger.debug(
                    "Falha ao sincronizar selector apos reorder de colunas: %s", exc
                )
        try:
            self._persist_visible_columns_order()
        except Exception as exc:
            logger.debug("Falha ao persistir nova ordem de colunas apos drag: %s", exc)
        self._skip_width_recompute_once = True
        self.display_current_page(self.paginator.current_page, update_details=False)
        self._restore_column_widths(preserved_widths)

    @staticmethod
    def _order_setor_executor_values(values: list[str]) -> list[str]:
        return order_sector_values(values, sector_to_div=SECTOR_TO_DIV)

    def _collect_setor_executor_values_for_combo(self) -> list[str]:
        base_df = getattr(self, "df_completo", None)
        if not isinstance(base_df, pd.DataFrame) or base_df.empty:
            base_df = getattr(self, "df_exibido", None)
        if not isinstance(base_df, pd.DataFrame) or base_df.empty:
            return []
        if "setor_executor" not in base_df.columns:
            return []
        raw_values = collect_nonempty_column_values(base_df, "setor_executor")
        return self._order_setor_executor_values(raw_values)

    def _populate_quick_setor_executor_combo(
        self, combo, selected_value: str = ""
    ) -> None:
        if combo is None:
            return
        options = self._collect_setor_executor_values_for_combo()
        selected = str(selected_value or "").strip()
        try:
            combo.blockSignals(True)
            combo.clear()
            combo.addItem("Todos", "")
            for value in options:
                combo.addItem(value, value)
            idx = combo.findData(selected)
            if idx < 0:
                idx = 0
            combo.setCurrentIndex(idx)
            self._update_quick_setor_executor_combo_display(combo)
        except Exception as exc:
            logger.debug("Falha ao popular combo rapido de setor executor: %s", exc)
        finally:
            try:
                combo.blockSignals(False)
            except Exception as exc:
                logger.debug(
                    "Falha ao reativar sinais do combo rapido de setor executor: %s",
                    exc,
                )

    def _update_quick_setor_executor_combo_display(self, combo) -> None:
        if combo is None:
            return
        value = ""
        try:
            value = str(combo.currentData() or "").strip()
        except Exception as exc:
            logger.debug(
                "Falha ao ler valor atual do combo rapido de setor executor: %s", exc
            )
        display_text = value if value else "Todos"
        try:
            line_edit = combo.lineEdit()
            if line_edit is not None:
                line_edit.setText(display_text)
        except Exception as exc:
            logger.debug(
                "Falha ao atualizar texto exibido do combo rapido de setor executor: %s",
                exc,
            )

    @staticmethod
    def _split_filter_csv_values(raw_value: str) -> list[str]:
        values = []
        seen = set()
        for part in str(raw_value or "").split(","):
            item = str(part or "").strip()
            if not item:
                continue
            key = item.casefold()
            if key in seen:
                continue
            seen.add(key)
            values.append(item)
        return values

    @staticmethod
    def _normalize_filter_sequence_values(raw_values) -> list[str]:
        values = []
        seen = set()
        for raw in raw_values or []:
            item = str(raw or "").strip()
            if not item:
                continue
            key = item.casefold()
            if key in seen:
                continue
            seen.add(key)
            values.append(item)
        return values

    def _sync_advanced_executor_filter_from_active_filters(
        self, *, clear_exclude: bool = False
    ) -> None:
        active_filters = OrderedDict(getattr(self, "_active_column_filters", {}) or {})
        selected_raw = str(active_filters.get("setor_executor", "") or "").strip()
        selected_values = self._split_filter_csv_values(selected_raw)
        advanced_filters = dict(getattr(self, "_advanced_filters", {}) or {})
        if selected_values:
            advanced_filters["setor_executor"] = selected_values
            if clear_exclude and "setor_executor_exclude_values" not in advanced_filters:
                advanced_filters["setor_executor_exclude_values"] = []
        else:
            advanced_filters.pop("setor_executor", None)
            if clear_exclude and not advanced_filters.get(
                "setor_executor_exclude_values"
            ):
                advanced_filters.pop("setor_executor_exclude_values", None)
        self._advanced_filters = advanced_filters
        self._advanced_filters_active = self._has_active_advanced_filters(
            advanced_filters
        )
        self._adv_options_dirty = True
        self._mark_responsavel_dirty()

    def _sync_active_executor_filter_from_advanced_filters(
        self, *, clear_when_missing: bool = False
    ) -> None:
        advanced_filters = dict(getattr(self, "_advanced_filters", {}) or {})
        selected_values = self._normalize_filter_sequence_values(
            advanced_filters.get("setor_executor")
        )
        active_filters = OrderedDict(getattr(self, "_active_column_filters", {}) or {})
        if selected_values:
            active_filters["setor_executor"] = ", ".join(selected_values)
        elif clear_when_missing:
            active_filters.pop("setor_executor", None)
        self._active_column_filters = active_filters

    def _sync_advanced_executor_ui_from_active_filter(self) -> None:
        active_filters = OrderedDict(getattr(self, "_active_column_filters", {}) or {})
        advanced_filters = dict(getattr(self, "_advanced_filters", {}) or {})
        selected_values = self._normalize_filter_sequence_values(
            advanced_filters.get("setor_executor")
        )
        exclude_values = self._normalize_filter_sequence_values(
            advanced_filters.get("setor_executor_exclude_values")
        )
        if not selected_values and not exclude_values:
            selected_raw = str(active_filters.get("setor_executor", "") or "").strip()
            selected_values = self._split_filter_csv_values(selected_raw)
        button = getattr(self, "adv_executor_button", None)
        checks = getattr(self, "adv_executor_checks", None)
        exclude_checks = getattr(self, "adv_executor_exclude_checks", None)
        if button is None:
            return
        if checks:
            self._sync_multiselect_checks(
                button,
                checks,
                selected_values,
                exclude_checks,
                exclude_values,
            )
            return
        if selected_values and exclude_values:
            button.setText(
                f"Incluir: {', '.join(selected_values)} | Diferente: {', '.join(exclude_values)}"
            )
        elif selected_values:
            button.setText(f"Incluir: {', '.join(selected_values)}")
        elif exclude_values:
            button.setText(f"Diferente: {', '.join(exclude_values)}")
        else:
            button.setText("Selecionar")

    def _resolve_quick_setor_executor_value(self) -> str:
        active_filters = OrderedDict(getattr(self, "_active_column_filters", {}) or {})
        selected_value = str(active_filters.get("setor_executor", "") or "").strip()
        advanced_filters = dict(getattr(self, "_advanced_filters", {}) or {})
        advanced_executor_candidates = self._normalize_filter_sequence_values(
            advanced_filters.get("setor_executor")
        )
        advanced_excludes = self._normalize_filter_sequence_values(
            advanced_filters.get("setor_executor_exclude_values")
        )
        if (
            not selected_value
            and len(advanced_executor_candidates) == 1
            and not advanced_excludes
        ):
            selected_value = advanced_executor_candidates[0]
        if "," in selected_value:
            return ""
        return selected_value

    def _sync_quick_setor_executor_combo_from_filters(self) -> None:
        selected_value = self._resolve_quick_setor_executor_value()
        combo = getattr(self, "quick_setor_executor_combo", None)
        if combo is None:
            return
        try:
            has_existing_options = combo.count() > 0
        except Exception:
            has_existing_options = False
        if has_existing_options:
            try:
                idx = combo.findData(selected_value)
            except Exception:
                idx = -1
            if idx >= 0:
                try:
                    combo.blockSignals(True)
                    combo.setCurrentIndex(idx)
                    self._update_quick_setor_executor_combo_display(combo)
                except Exception as exc:
                    logger.debug(
                        "Falha ao sincronizar selecao do combo rapido de setor executor: %s",
                        exc,
                    )
                finally:
                    try:
                        combo.blockSignals(False)
                    except Exception as exc:
                        logger.debug(
                            "Falha ao reativar sinais na sincronizacao do combo rapido de setor executor: %s",
                            exc,
                        )
                return
        self._populate_quick_setor_executor_combo(
            combo, selected_value=selected_value
        )

    def _refresh_quick_setor_executor_options(self) -> None:
        combo = getattr(self, "quick_setor_executor_combo", None)
        if combo is not None:
            self._populate_quick_setor_executor_combo(
                combo, selected_value=self._resolve_quick_setor_executor_value()
            )

    def _on_quick_setor_executor_changed(self, combo) -> None:
        selected = ""
        try:
            selected = str(combo.currentData() or "").strip()
        except Exception as exc:
            logger.debug(
                "Falha ao ler valor do combo rapido de setor executor: %s", exc
            )
        self._safe_store_last_filter_state("quick_setor_executor_changed")
        active_filters = OrderedDict(getattr(self, "_active_column_filters", {}) or {})
        if selected:
            active_filters["setor_executor"] = selected
        else:
            active_filters.pop("setor_executor", None)
        self._update_quick_setor_executor_combo_display(combo)
        self._active_column_filters = active_filters
        self._sync_advanced_executor_filter_from_active_filters(
            clear_exclude=bool(selected)
        )
        self._sync_advanced_filter_ui()
        if hasattr(self, "_schedule_sector_options_refresh"):
            self._schedule_sector_options_refresh()
        self._mark_profile_as_custom()
        self._build_column_filters_panel()
        self._refresh_after_filter_change()

    def _get_select_all_columns_from_selector(self) -> list[str]:
        selector = getattr(self, "column_selector", None)
        available = []
        selected = []
        default_columns = list(getattr(self, "default_columns", []) or [])
        if selector is not None:
            available = list(getattr(selector, "available_columns", []) or [])
            selected = list(getattr(selector, "selected_internal_columns", []) or [])
        canonical = list(self._get_canonical_available_columns() or [])
        if not available:
            available = canonical
        else:
            available = list(
                dict.fromkeys(
                    available + [col for col in canonical if col not in available]
                )
            )
        selection = [col for col in selected if col in available]
        if not selection:
            selection = [col for col in default_columns if col in available]
        remaining = [col for col in available if col not in selection]
        return selection + remaining

    def _sort_columns_by_affinity_desc(self, columns: list[str]) -> list[str]:
        if not columns:
            return []
        base_index = {col: idx for idx, col in enumerate(columns)}
        return sorted(
            list(dict.fromkeys(columns)),
            key=lambda col: (
                -int(COLUMN_AFFINITY_SCORES.get(col, 0)),
                int(base_index.get(col, 10000)),
            ),
        )

    def _show_all_columns_by_affinity(self) -> None:
        select_all_columns = self._get_select_all_columns_from_selector()
        if not select_all_columns:
            return
        ordered_columns = self._sort_columns_by_affinity_desc(select_all_columns)
        self.on_columns_changed(ordered_columns)

    def _capture_current_column_widths(self) -> dict[str, int]:
        width_manager = getattr(self, "width_manager", None)
        if width_manager is None or not hasattr(
            width_manager, "capture_current_column_widths"
        ):
            return {}
        return width_manager.capture_current_column_widths(
            self.table_widget,
            getattr(self, "_current_display_columns", []),
        )

    def _restore_column_widths(self, widths: dict[str, int]) -> None:
        if not isinstance(widths, dict) or not widths:
            return
        width_manager = getattr(self, "width_manager", None)
        if width_manager is None or not hasattr(width_manager, "restore_column_widths"):
            return
        gui_widths = getattr(self, "_gui_column_pixel_widths", None)
        if not isinstance(gui_widths, dict):
            gui_widths = {}
            self._gui_column_pixel_widths = gui_widths
        width_manager.restore_column_widths(
            self.table_widget,
            getattr(self, "_current_display_columns", []),
            widths,
            saved_widths=getattr(self, "_saved_gui_column_widths", {}),
            gui_widths=gui_widths,
        )

    def display_current_page(self, page_number, *, update_details=True):
        return ssa_gui_table.display_current_page(
            self, page_number, update_details=update_details
        )

    def display_data(self, df):
        return ssa_gui_table.display_data(self, df)

    def _force_column_widths(self):
        return ssa_gui_table._force_column_widths(self)

    def _ensure_nonzero_column_widths(self):
        return ssa_gui_table._ensure_nonzero_column_widths(self)

    def _set_safe_width_for_col_index(self, idx: int, px: int = 80):
        return ssa_gui_table._set_safe_width_for_col_index(self, idx, px)

    def _compute_gui_column_widths(self, df: pd.DataFrame):
        return ssa_gui_table._compute_gui_column_widths(self, df)

    def _on_header_section_resized(
        self, logical_index: int, old_size: int, new_size: int
    ):
        return ssa_gui_table._on_header_section_resized(
            self, logical_index, old_size, new_size
        )

    def _normalize_highlight_term(self, term):
        return ssa_gui_details._normalize_highlight_term(self, term)

    def _get_current_search_terms(self):
        return ssa_gui_details._get_current_search_terms(self)

    def _collect_highlight_terms(self):
        return ssa_gui_details._collect_highlight_terms(self)

    def _highlight_text(self, text, terms):
        return ssa_gui_details._highlight_text(self, text, terms)

    def _format_details_html(
        self,
        series,
        highlight_search_terms=False,
        font_size_pt=None,
        linkify=False,
        label_font_size_pt=None,
    ):
        return ssa_gui_details._format_details_html(
            self,
            series,
            highlight_search_terms=highlight_search_terms,
            font_size_pt=font_size_pt,
            linkify=linkify,
            label_font_size_pt=label_font_size_pt,
        )

    @staticmethod
    def _build_sam_ssa_url(numero_ssa: str) -> str:
        return ssa_system.build_sam_ssa_url(numero_ssa)

    def _open_url_in_browser(self, url: str, *, success_status: str) -> bool:
        qurl = QUrl(str(url or ""))
        if not ssa_system.is_allowed_sam_url(qurl):
            logger.warning(
                "URL externa bloqueada por politica local: scheme=%s host=%s",
                str(qurl.scheme() or "").casefold() or "<empty>",
                str(qurl.host() or "").casefold() or "<empty>",
            )
            return False
        ok = ssa_system.open_allowed_url(
            url,
            qdesktopservices=QDesktopServices,
            qurl_cls=QUrl,
            logger=logger,
        )
        if ok and hasattr(self, "status_label"):
            self.status_label.setText(success_status)
        return ok

    def _open_sam_home(self):
        opened = self._open_url_in_browser(
            ssa_system.SAM_HOME_URL,
            success_status="Status: SAM aberto no navegador.",
        )
        if not opened and not os.environ.get("PYTEST_CURRENT_TEST"):
            QMessageBox.warning(self, "Erro", "Falha ao abrir o SAM no navegador.")
        return opened

    def _open_sam_ssa(self, numero_ssa: str):
        safe_numero = self._normalize_ssa_value(numero_ssa)
        if not re.fullmatch(r"[A-Za-z0-9]+", safe_numero):
            logger.warning("Numero SSA invalido para URL SAM: %s", safe_numero)
            return False
        sam_url = self._build_sam_ssa_url(safe_numero)
        if not ssa_system.is_allowed_sam_url(QUrl(sam_url)):
            logger.warning("URL SAM rejeitada por host fora da allow-list.")
            return False
        opened = self._open_url_in_browser(
            sam_url,
            success_status=f"Status: SSA {safe_numero} aberta no SAM.",
        )
        if not opened and not os.environ.get("PYTEST_CURRENT_TEST"):
            QMessageBox.warning(
                self,
                "Erro",
                f"Falha ao abrir a SSA {safe_numero} no navegador.",
            )
        return opened

    def _copy_ssa_to_clipboard(
        self, numero_ssa: str, *, status_text: str = "Status: Numero da SSA copiado."
    ) -> bool:
        safe_numero = self._normalize_ssa_value(numero_ssa)
        if not safe_numero:
            return False
        clipboard = QApplication.clipboard()
        if clipboard is None:
            return False
        clipboard.setText(safe_numero)
        if hasattr(self, "status_label"):
            self.status_label.setText(status_text)
        return True

    def on_table_cell_clicked(self, row: int, column: int):
        if self._resolve_header_column_name(column) not in {"#", "numero_ssa"}:
            return
        series = self._get_series_from_row(row)
        if series is None:
            return
        numero_ssa = series.get("numero_ssa")
        self._open_sam_ssa(numero_ssa)

    def on_table_double_click(self, index):
        """Mostra janela de detalhes formatada ao duplo clique."""
        clicked_column_name = ""
        try:
            clicked_column = int(index.column())
        except Exception:
            clicked_column = -1
        try:
            display_columns = getattr(self, "_current_display_columns", None)
            if isinstance(display_columns, list) and 0 <= clicked_column < len(
                display_columns
            ):
                clicked_column_name = str(display_columns[clicked_column] or "")
        except Exception:
            clicked_column_name = ""

        row = index.row()
        series = self._get_series_from_row(row)
        if series is None:
            QMessageBox.information(
                self,
                "Info",
                "Nao foi possivel encontrar os dados detalhados para esta linha.",
            )
            return

        numero_ssa = series.get("numero_ssa")
        if clicked_column_name == "numero_ssa":
            self._copy_ssa_to_clipboard(numero_ssa)
            return
        self._open_details_dialog_for_ssa(numero_ssa, series=series)

    def _save_page_size_pref(self, new_size: int):
        """Persiste o tamanho da pagina no settings da GUI."""
        try:
            page_size = int(new_size)
        except (TypeError, ValueError):
            logger.warning("Page size invalido ignorado: %r", new_size)
            return False
        if page_size < 10 or page_size > 500:
            logger.warning("Page size fora do intervalo permitido: %s", page_size)
            return False
        gui_settings = GUI_MAIN_PREFERENCES.setdefault("gui_settings", {})
        if gui_settings.get("page_size") == page_size:
            self._restored_page_size = page_size
            return True
        gui_settings["page_size"] = page_size
        self._restored_page_size = page_size
        if os.environ.get("PYTEST_CURRENT_TEST"):
            return True
        return self._persist_gui_preferences()

    def _get_series_from_row(self, row: int):
        visible_numero = self._get_visible_numero_ssa_from_row(row)
        try:
            index_item = self.table_widget.item(row, 0)
        except Exception:
            index_item = None
        original_index = None
        if index_item:
            try:
                original_index = index_item.data(Qt.ItemDataRole.UserRole)
            except Exception:
                original_index = None
        if original_index is not None and 0 <= original_index < len(self.df_exibido):
            try:
                candidate = self.df_exibido.iloc[int(original_index)]
                if visible_numero:
                    candidate_numero = self._normalize_ssa_value(
                        candidate.get("numero_ssa")
                    )
                    if candidate_numero != visible_numero:
                        candidate = None
                if candidate is not None:
                    return candidate
            except Exception as exc:
                logger.debug("Falha ao resolver serie da linha visivel %s: %s", row, exc)
        if visible_numero:
            return ssa_gui_details._get_series_for_ssa(self, visible_numero)
        return None

    def _get_visible_numero_ssa_from_row(self, row: int) -> str:
        try:
            display_columns = list(getattr(self, "_current_display_columns", []) or [])
            numero_col = display_columns.index("numero_ssa")
        except (ValueError, TypeError):
            return ""
        try:
            item = self.table_widget.item(row, numero_col)
        except Exception:
            return ""
        if not item:
            return ""
        return self._normalize_ssa_value(item.text())

    def _normalize_ssa_value(self, value):
        return ssa_gui_details._normalize_ssa_value(self, value)

    def _normalize_ssa_series(self, series: pd.Series) -> pd.Series:
        return ssa_gui_details._normalize_ssa_series(self, series)

    def update_details_from_selection(self):
        return ssa_gui_details.update_details_from_selection(self)

    def _get_derivadas_for_ssa(self, numero_ssa):
        return ssa_gui_details._get_derivadas_for_ssa(self, numero_ssa)

    def _jump_to_ssa(self, numero_ssa, **kwargs):
        return ssa_gui_details._jump_to_ssa(self, numero_ssa, **kwargs)

    def _on_details_anchor_clicked(self, url):
        return ssa_gui_details._on_details_anchor_clicked(self, url)

    def _open_details_dialog_for_ssa(self, numero_ssa, series=None):
        return ssa_gui_details._open_details_dialog_for_ssa(
            self, numero_ssa, series=series
        )

    def _filter_by_derivadas(self, numero_ssa):
        return ssa_gui_details._filter_by_derivadas(self, numero_ssa)

    def _clear_derivadas_filter(self):
        return ssa_gui_details._clear_derivadas_filter(self)

    def show_context_menu(self, position):
        """Mostra menu de contexto na tabela."""
        show_table_context_menu(
            self,
            self.table_widget,
            position,
            TableContextMenuCallbacks(
                copy_cell_value=self.copy_cell_value,
                copy_row_data=self.copy_row_data,
                export_current_list_txt=self._export_current_list_txt,
                get_series_from_row=self._get_series_from_row,
                jump_to_ssa=self._jump_to_ssa,
                filter_by_derivadas=self._filter_by_derivadas,
                clear_derivadas_filter=self._clear_derivadas_filter,
                remove_column_by_index=self.remove_column_by_index,
                auto_fit_column=self.auto_fit_column,
                last_derivada_origem=lambda: getattr(
                    self, "_last_derivada_origem", None
                ),
            ),
            action_cls=QAction,
            menu_cls=QMenu,
        )

    def copy_cell_value(self, *_):  # QAction triggered pode enviar 'checked'
        """Copia o valor da celula selecionada."""
        current_item = self.table_widget.currentItem()
        if current_item:
            clipboard = QApplication.clipboard()
            if clipboard is not None:
                clipboard.setText(current_item.text())

    def copy_row_data(self, *_):  # aceita args opcionais de QAction
        """Copia todos os dados da linha selecionada."""
        current_row = self.table_widget.currentRow()
        if current_row >= 0:
            row_data = []
            for col in range(self.table_widget.columnCount()):
                item = self.table_widget.item(current_row, col)
                row_data.append(item.text() if item else "")

            clipboard = QApplication.clipboard()
            if clipboard is not None:
                clipboard.setText("\t".join(row_data))

    def _export_current_list_txt(self):
        state = getattr(self, "_list_export_state", None)
        if not isinstance(state, ssa_list_export_controller.ListExportState):
            state = ssa_list_export_controller.ListExportState()
            self._list_export_state = state
        return ssa_list_export_controller.export_current_list_tsv(
            self,
            state,
            file_dialog=QFileDialog,
            message_box=QMessageBox,
        )

    def remove_column_by_index(self, column_index):
        """Remove uma coluna especifica baseada no indice da tabela."""
        if column_index <= 0:
            return
        internal_index = column_index - 1  # Coluna 0 da tabela e '#'
        if internal_index < 0 or internal_index >= len(self.visible_columns):
            return
        internal_column = self.visible_columns[internal_index]
        if internal_column in self.visible_columns:
            self.visible_columns.remove(internal_column)
            self.on_columns_changed(self.visible_columns)

    def _compute_best_fit_width_for_column(
        self, column_index: int, sample_limit: int = 2000
    ) -> int | None:
        if column_index < 0 or column_index >= self.table_widget.columnCount():
            return None
        cols = getattr(self, "_current_display_columns", None)
        if not cols or column_index >= len(cols):
            return None
        col_name = cols[column_index]
        header_item = self.table_widget.horizontalHeaderItem(column_index)
        header_text = (
            str(header_item.text()) if header_item is not None else str(col_name)
        )
        width_manager = getattr(self, "width_manager", None)
        font_metrics = self.table_widget.fontMetrics()
        series = None
        if (
            self.df_exibido is not None
            and not self.df_exibido.empty
            and col_name in self.df_exibido.columns
        ):
            series = self.df_exibido[col_name]
        if width_manager is not None and hasattr(
            width_manager, "compute_best_fit_width"
        ):
            return int(
                width_manager.compute_best_fit_width(
                    series=series,
                    header_text=header_text,
                    col_name=col_name,
                    measure_text=font_metrics.horizontalAdvance,
                    sample_limit=int(sample_limit),
                )
            )
        header_px = int(font_metrics.horizontalAdvance(str(header_text))) + 28
        if col_name == "#":
            return max(26, min(int(header_px), 90))
        return max(40, min(int(header_px), 420))

    def _best_fit_column_width(self, column_index: int) -> bool:
        width = self._compute_best_fit_width_for_column(column_index)
        if width is None:
            return False
        old_width = self.table_widget.columnWidth(column_index)
        self.table_widget.setColumnWidth(column_index, int(width))
        self._on_header_section_resized(column_index, old_width, int(width))
        return True

    def best_fit_visible_columns(self):
        col_count = self.table_widget.columnCount()
        if col_count <= 0:
            return
        current_columns = list(getattr(self, "_current_display_columns", []) or [])
        for column_index in range(col_count):
            column_name = (
                str(current_columns[column_index])
                if column_index < len(current_columns)
                else ""
            )
            if column_name == "#":
                continue
            self._best_fit_column_width(column_index)

    def auto_fit_column(self, column_index):
        """Ajusta automaticamente a largura da coluna baseada no conteudo."""
        if self._best_fit_column_width(column_index):
            return
        old_width = self.table_widget.columnWidth(column_index)
        self.table_widget.resizeColumnToContents(column_index)
        new_width = self.table_widget.columnWidth(column_index)
        self._on_header_section_resized(column_index, old_width, new_width)

    def _setup_app_menus(self) -> None:
        ssa_app_menus.setup_app_menus(
            self,
            action_cls=QAction,
            preferences=GUI_MAIN_PREFERENCES,
            project_root=project_root,
            default_table_alignment=_DEFAULT_TABLE_CELL_ALIGNMENT,
            table_alignment_labels=_TABLE_CELL_ALIGNMENT_LABELS,
        )

    def import_external_excel_files(self):
        """Enfileira importacao externa; o staging roda em background."""
        selected_files, _ = QFileDialog.getOpenFileNames(
            self,
            "Selecionar arquivos Excel para importar",
            os.path.expanduser("~"),
            "Arquivos Excel (*.xlsx *.xls);;Todos os Arquivos (*)",
        )

        if not selected_files:
            return {
                "selected": 0,
                "copied": 0,
                "skipped": 0,
                "failed": 0,
                "unsupported": 0,
                "staged": 0,
                "result_scope": "queue",
                "db_updated": False,
                "db_update_requested": False,
                "queued": False,
            }

        selected_count = len(selected_files)
        skipped = 0
        failed = 0
        unsupported = 0
        queued = False
        safe_selected_files: list[str] = []
        for raw_source in selected_files:
            source = str(raw_source or "").strip()
            if not source:
                skipped += 1
                continue
            try:
                validated_source = SSAMainWindow._validate_local_open_target(
                    source,
                    must_exist=True,
                    expect_dir=False,
                )
            except Exception as exc:
                logger.warning(
                    "Importacao externa rejeitou caminho invalido '%s': %s",
                    source,
                    exc,
                )
                failed += 1
                continue
            if not validated_source.casefold().endswith((".xlsx", ".xls")):
                logger.info(
                    "Importacao externa ignorou arquivo nao suportado pelo pipeline: %s",
                    validated_source,
                )
                unsupported += 1
                continue
            safe_selected_files.append(validated_source)
        try:
            from gui.widgets import RescanProgressDialog
            from gui.workers import RescanWorker

            if safe_selected_files:
                ssa_gui_workers.rescan_data(
                    self,
                    project_root=project_root,
                    rescan_worker_cls=RescanWorker,
                    rescan_dialog_cls=RescanProgressDialog,
                    qmessagebox=QMessageBox,
                    **_rescan_retention_kwargs(),
                    sip_module=sip,
                    rescan_mode="explicit",
                    source_files=tuple(safe_selected_files),
                    db_path=DB_PATH,
                    operation_label="Importacao externa",
                    reload_on_success=True,
                    operation_kind="import",
                )
                queued = True
        except Exception as exc:
            logger.warning("Falha ao iniciar importacao externa: %s", exc)
            failed += len(safe_selected_files)

        if hasattr(self, "status_label") and not queued:
            summary = (
                f"Status: Importacao externa preparada - selecionados={selected_count}, "
                f"falhas={failed}, "
                f"enfileirada=nao."
            )
            self.status_label.setText(summary)

        return {
            "selected": selected_count,
            "copied": 0,
            "copied_scope": "async_worker",
            "skipped": skipped,
            "failed": failed,
            "unsupported": unsupported,
            "staged": len(safe_selected_files) if queued else 0,
            "result_scope": "queue",
            "db_updated": False,
            "db_update_requested": queued,
            "queued": queued,
        }

    def _resolve_settings_file_path(self) -> str:
        try:
            from core import config_manager

            resolver = getattr(config_manager, "_resolve_config_path", None)
            if callable(resolver):
                return str(resolver(config_manager.USER_SETTINGS_FILE))
        except Exception as exc:
            logger.debug("Falha ao resolver settings path via config_manager: %s", exc)
        return os.path.join(project_root, "config", "settings.json")

    @staticmethod
    def _validate_local_open_target(
        target_path: str,
        *,
        must_exist: bool,
        expect_dir: bool | None,
        allowed_base: str | list[str] | tuple[str, ...] | None = None,
    ) -> str:
        return ssa_system.validate_local_open_target(
            target_path,
            must_exist=must_exist,
            expect_dir=expect_dir,
            allowed_base=allowed_base or project_root,
        )

    @staticmethod
    def _resolve_platform_open_command() -> str:
        return ssa_system.resolve_platform_open_command()

    def open_settings_file_with_backup(self):
        """Abre settings.json para edicao apos criar backup failsafe com timestamp."""
        settings_path = os.path.abspath(self._resolve_settings_file_path())
        os.makedirs(os.path.dirname(settings_path), exist_ok=True)

        try:
            if not os.path.exists(settings_path):
                from core.config_manager import load_settings, save_settings

                save_settings(load_settings())
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            backup_path = f"{settings_path}.bak_{timestamp}"
            shutil.copy2(settings_path, backup_path)
        except Exception as exc:
            logger.warning("Falha ao preparar backup de settings: %s", exc)
            if not os.environ.get("PYTEST_CURRENT_TEST"):
                QMessageBox.warning(
                    self,
                    "Erro",
                    f"Falha ao preparar backup de opcoes: {exc}",
                )
            return {
                "opened": False,
                "backup_created": False,
                "settings_path": settings_path,
            }

        try:
            safe_settings_path = SSAMainWindow._validate_local_open_target(
                settings_path,
                must_exist=True,
                expect_dir=False,
                allowed_base=(
                    os.path.join(project_root, "config"),
                    os.path.dirname(settings_path),
                ),
            )
        except Exception as exc:
            logger.warning("Caminho de settings invalido para abertura: %s", exc)
            if not os.environ.get("PYTEST_CURRENT_TEST"):
                QMessageBox.warning(self, "Erro", f"Caminho de opcoes invalido: {exc}")
            return {
                "opened": False,
                "backup_created": True,
                "settings_path": settings_path,
            }

        opened = False
        try:
            if QT_AVAILABLE:
                opened = bool(
                    QDesktopServices.openUrl(QUrl.fromLocalFile(safe_settings_path))
                )
            if not opened:
                resolved = SSAMainWindow._resolve_platform_open_command()
                subprocess.Popen(  # nosec B603
                    ssa_system.build_platform_open_args(resolved, safe_settings_path),
                    shell=False,
                )
                opened = True
        except Exception as exc:
            logger.warning("Falha ao abrir settings para edicao: %s", exc)
            if not os.environ.get("PYTEST_CURRENT_TEST"):
                QMessageBox.warning(self, "Erro", f"Falha ao abrir opcoes: {exc}")
            return {
                "opened": False,
                "backup_created": True,
                "settings_path": settings_path,
            }

        if hasattr(self, "status_label"):
            self.status_label.setText(
                "Status: Opcoes abertas no editor externo (arquivo principal)."
            )
        return {
            "opened": opened,
            "backup_created": True,
            "settings_path": safe_settings_path,
        }

    def reset_settings_to_defaults(self):
        """Restaura settings.json para os valores padrao com backup previo."""
        settings_path = self._resolve_settings_file_path()
        os.makedirs(os.path.dirname(settings_path), exist_ok=True)

        try:
            from core import config_manager

            resolver = getattr(config_manager, "_resolve_config_path", None)
            if callable(resolver):
                default_settings_path = str(
                    resolver(config_manager.DEFAULT_SETTINGS_FILE)
                )
            else:
                default_settings_path = os.path.join(
                    project_root, "config", "default_settings.json"
                )
            if not os.path.exists(default_settings_path):
                config_manager.ensure_default_settings(fail_fast=False)
            with open(default_settings_path, "r", encoding="utf-8") as handle:
                default_settings = json.load(handle)
        except Exception as exc:
            logger.warning("Falha ao carregar defaults de opcoes: %s", exc)
            if not os.environ.get("PYTEST_CURRENT_TEST"):
                QMessageBox.warning(
                    self, "Erro", f"Falha ao carregar opcoes padrao: {exc}"
                )
            return {"ok": False, "reason": "load_default_failed"}

        if not os.environ.get("PYTEST_CURRENT_TEST"):
            qmessagebox = cast(Any, QMessageBox)
            answer = qmessagebox.question(
                self,
                "Confirmar restauracao",
                (f"Restaurar opcoes padrao agora? Isso sobrescreve {settings_path}."),
                qmessagebox.StandardButton.Yes | qmessagebox.StandardButton.No,
                qmessagebox.StandardButton.No,
            )
            if answer != qmessagebox.StandardButton.Yes:
                return {"ok": False, "cancelled": True}

        backup_created = False
        backup_path = ""
        try:
            if os.path.exists(settings_path):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                backup_path = f"{settings_path}.bak_{timestamp}"
                shutil.copy2(settings_path, backup_path)
                backup_created = True
        except Exception as exc:
            logger.warning("Falha ao criar backup antes do reset de opcoes: %s", exc)
            if not os.environ.get("PYTEST_CURRENT_TEST"):
                QMessageBox.warning(
                    self, "Erro", f"Falha ao criar backup de opcoes: {exc}"
                )
            return {"ok": False, "reason": "backup_failed"}

        try:
            from core.config_manager import save_settings

            save_settings(default_settings)
        except Exception as exc:
            logger.warning("Falha ao restaurar opcoes padrao: %s", exc)
            if not os.environ.get("PYTEST_CURRENT_TEST"):
                QMessageBox.warning(self, "Erro", f"Falha ao restaurar opcoes: {exc}")
            return {"ok": False, "reason": "save_failed"}

        if hasattr(self, "status_label"):
            self.status_label.setText("Status: Opcoes padrao restauradas com sucesso.")
        if not os.environ.get("PYTEST_CURRENT_TEST"):
            QMessageBox.information(self, "Sucesso", "Opcoes padrao restauradas.")
        return {
            "ok": True,
            "settings_path": settings_path,
            "backup_created": backup_created,
            "backup_path": backup_path,
        }

    def consolidate_input_files(self):
        """Enfileira consolidacao de docs_entrada para processadas em background."""
        queued = False
        failed = 0
        try:
            from gui.widgets import RescanProgressDialog
            from gui.workers import RescanWorker

            ssa_gui_workers.rescan_data(
                self,
                project_root=project_root,
                rescan_worker_cls=RescanWorker,
                rescan_dialog_cls=RescanProgressDialog,
                qmessagebox=QMessageBox,
                **_rescan_retention_kwargs(),
                sip_module=sip,
                rescan_mode="diff",
                operation_label="Consolidacao de arquivos",
                reload_on_success=False,
                operation_kind="consolidate",
            )
            queued = True
        except Exception as exc:
            logger.warning("Falha ao iniciar consolidacao de arquivos: %s", exc)
            failed = 1

        if hasattr(self, "status_label") and not queued:
            self.status_label.setText(
                "Status: Falha ao enfileirar consolidacao de arquivos."
            )
        return {
            "moved": 0,
            "nosurvivor": 0,
            "pending": 0,
            "failed": failed,
            "queued": queued,
            "result_scope": "queue",
        }

    def rescan_data(self):
        """Abre o fluxo de reescaneamento/importacao com feedback visual."""
        from gui.widgets import RescanProgressDialog
        from gui.workers import RescanWorker

        return ssa_gui_workers.rescan_data(
            self,
            project_root=project_root,
            rescan_worker_cls=RescanWorker,
            rescan_dialog_cls=RescanProgressDialog,
            qmessagebox=QMessageBox,
            **_rescan_retention_kwargs(),
            sip_module=sip,
            rescan_mode="prompt",
            db_path=DB_PATH,
            reload_on_success=True,
        )

    def rescan_diff_data(self):
        """Reprocessa somente arquivos alterados por hash (modo diff)."""
        from gui.widgets import RescanProgressDialog
        from gui.workers import RescanWorker

        return ssa_gui_workers.rescan_data(
            self,
            project_root=project_root,
            rescan_worker_cls=RescanWorker,
            rescan_dialog_cls=RescanProgressDialog,
            qmessagebox=QMessageBox,
            **_rescan_retention_kwargs(),
            sip_module=sip,
            rescan_mode="diff",
            db_path=DB_PATH,
            reload_on_success=True,
        )

    def rescan_full_data(self):
        """Reprocessa tudo recriando DB candidato (modo full)."""
        from gui.widgets import RescanProgressDialog
        from gui.workers import RescanWorker

        return ssa_gui_workers.rescan_data(
            self,
            project_root=project_root,
            rescan_worker_cls=RescanWorker,
            rescan_dialog_cls=RescanProgressDialog,
            qmessagebox=QMessageBox,
            **_rescan_retention_kwargs(),
            sip_module=sip,
            rescan_mode="full",
            db_path=DB_PATH,
            reload_on_success=True,
        )

    def open_docs_folder(self):
        """Abre a pasta docs_entrada no explorador de arquivos (nao bloqueante)."""
        docs_path = os.path.join(project_root, "docs_entrada")
        if hasattr(self, "status_label"):
            self.status_label.setText(f"Status: Pasta de entrada: {docs_path}")
        SSAMainWindow._open_folder_non_blocking(
            cast(Any, self),
            folder_path=docs_path,
            folder_label="pasta de entrada",
        )

    def open_processadas_folder(self):
        """Abre docs_entrada/processadas no explorador de arquivos."""
        folder_path = os.path.join(project_root, "docs_entrada", "processadas")
        SSAMainWindow._open_folder_non_blocking(
            cast(Any, self),
            folder_path=folder_path,
            folder_label="pasta processadas",
        )

    def open_nosurvivor_folder(self):
        """Abre docs_entrada/processadas/nosurvivor no explorador de arquivos."""
        folder_path = os.path.join(
            project_root,
            "docs_entrada",
            "processadas",
            "nosurvivor",
        )
        SSAMainWindow._open_folder_non_blocking(
            cast(Any, self),
            folder_path=folder_path,
            folder_label="pasta sem sobreviventes",
        )

    def open_installation_guide(self):
        """Abre o guia de instalacao no editor/sistema padrao."""
        doc_candidates = list(_iter_installation_guide_candidates())
        doc_path = next((path for path in doc_candidates if os.path.exists(path)), "")
        if not os.path.exists(doc_path):
            missing_reference = (
                doc_candidates[0]
                if doc_candidates
                else os.path.abspath(
                    os.path.join(
                        project_root, "docs", "GUIA_MIGRACAO_NOVA_INSTALACAO.md"
                    )
                )
            )
            if not os.environ.get("PYTEST_CURRENT_TEST"):
                QMessageBox.warning(
                    self,
                    "Erro",
                    f"Guia de instalacao nao encontrado: {missing_reference}",
                )
            return {"opened": False, "reason": "missing_file"}
        try:
            safe_doc_path = SSAMainWindow._validate_local_open_target(
                doc_path,
                must_exist=True,
                expect_dir=False,
                allowed_base=tuple(
                    os.path.dirname(path)
                    for path in _iter_installation_guide_candidates()
                ),
            )
            opened = False
            if QT_AVAILABLE:
                safe_doc_url = QUrl.fromLocalFile(safe_doc_path)
                opened = bool(QDesktopServices.openUrl(safe_doc_url))
            if not opened:
                resolved = SSAMainWindow._resolve_platform_open_command()
                subprocess.Popen(  # nosec B603
                    ssa_system.build_platform_open_args(resolved, safe_doc_path),
                    shell=False,
                )
                opened = True
            if hasattr(self, "status_label"):
                self.status_label.setText("Status: Guia de instalacao aberto.")
            return {"opened": opened, "path": safe_doc_path}
        except Exception as exc:
            logger.warning("Falha ao abrir guia de instalacao: %s", exc)
            if not os.environ.get("PYTEST_CURRENT_TEST"):
                QMessageBox.warning(
                    self, "Erro", f"Falha ao abrir guia de instalacao: {exc}"
                )
            return {"opened": False, "reason": "open_failed", "error": str(exc)}

    def run_vacuum_analyze(self):
        """Executa VACUUM/ANALYZE manualmente no banco principal."""
        db_path = DB_PATH
        if not db_path or not os.path.exists(db_path):
            if os.environ.get("PYTEST_CURRENT_TEST"):
                return {"ok": False, "reason": "missing_db"}
            QMessageBox.warning(self, "Erro", f"Banco nao encontrado: {db_path}")
            return {"ok": False, "reason": "missing_db"}

        if not os.environ.get("PYTEST_CURRENT_TEST"):
            qmessagebox = cast(Any, QMessageBox)
            answer = qmessagebox.question(
                self,
                "Confirmar",
                "Compactar DB e atualizar estatisticas agora?",
                qmessagebox.StandardButton.Yes | qmessagebox.StandardButton.No,
                qmessagebox.StandardButton.No,
            )
            if answer != qmessagebox.StandardButton.Yes:
                return {"ok": False, "cancelled": True}

        if bool(getattr(self, "_vacuum_analyze_running", False)):
            if hasattr(self, "status_label"):
                self.status_label.setText("Status: Compactacao do DB ja em andamento.")
            return {"ok": False, "reason": "already_running", "db_path": db_path}

        if hasattr(self, "status_label"):
            self.status_label.setText(
                "Status: Compactando DB e atualizando estatisticas..."
            )

        if os.environ.get("PYTEST_CURRENT_TEST"):
            result = SSAMainWindow._execute_vacuum_analyze(db_path)
            return SSAMainWindow._finalize_vacuum_analyze_result(self, result)

        self._vacuum_analyze_running = True
        self._vacuum_analyze_pending_result = None

        def _window_alive() -> bool:
            if self is None:
                return False
            # Test stubs and lightweight stand-ins are not Qt widgets.
            if not hasattr(self, "metaObject"):
                return True
            if sip is None:
                return True
            try:
                return not sip.isdeleted(self)
            except Exception:
                return False

        def _work() -> None:
            try:
                result = SSAMainWindow._execute_vacuum_analyze(db_path)
            except Exception as exc:
                result = {"ok": False, "error": str(exc), "db_path": db_path}
            self._vacuum_analyze_pending_result = result

        def _poll_delivery() -> None:
            if not _window_alive():
                self._vacuum_analyze_pending_result = None
                self._vacuum_analyze_running = False
                self._vacuum_analyze_thread = None
                return
            pending = getattr(self, "_vacuum_analyze_pending_result", None)
            if pending is None:
                if bool(getattr(self, "_vacuum_analyze_running", False)):
                    QTimer.singleShot(100, _poll_delivery)
                return
            self._vacuum_analyze_pending_result = None
            SSAMainWindow._finalize_vacuum_analyze_result(self, pending)

        worker = threading.Thread(target=_work, daemon=True)
        self._vacuum_analyze_thread = worker
        worker.start()
        QTimer.singleShot(100, _poll_delivery)
        return {"ok": True, "started": True, "db_path": db_path}

    @staticmethod
    def _execute_vacuum_analyze(db_path: str) -> dict[str, Any]:
        return ssa_database_operations.execute_vacuum_analyze(
            db_path, vacuum_analyze_database
        )

    def _finalize_vacuum_analyze_result(self, result: dict[str, Any]) -> dict[str, Any]:
        self._vacuum_analyze_running = False
        self._vacuum_analyze_thread = None

        if bool(result.get("ok")):
            if hasattr(self, "status_label"):
                self.status_label.setText(
                    "Status: DB compactado e estatisticas atualizadas."
                )
            if not os.environ.get("PYTEST_CURRENT_TEST"):
                QMessageBox.information(
                    self, "Sucesso", "Compactacao e atualizacao do DB concluidas."
                )
            return result

        error = str(result.get("error") or "Erro desconhecido")
        logger.error("Falha ao compactar DB e atualizar estatisticas: %s", error)
        if not os.environ.get("PYTEST_CURRENT_TEST"):
            QMessageBox.warning(self, "Erro", f"Falha na compactacao do DB: {error}")
        return {"ok": False, "error": error, "db_path": result.get("db_path")}

    def _open_folder_non_blocking(self, folder_path: str, folder_label: str) -> None:
        try:
            folder_path = SSAMainWindow._validate_local_open_target(
                folder_path,
                must_exist=False,
                expect_dir=True,
            )
        except Exception as exc:
            logger.warning(
                "Caminho de pasta invalido para abertura (%s): %s", folder_label, exc
            )
            if not os.environ.get("PYTEST_CURRENT_TEST"):
                QMessageBox.warning(self, "Erro", f"Caminho de pasta invalido: {exc}")
            return
        if not os.path.exists(folder_path):
            if os.environ.get("PYTEST_CURRENT_TEST"):
                return
            qmessagebox = cast(Any, QMessageBox)
            answer = qmessagebox.question(
                self,
                "Pasta nao encontrada",
                (
                    f"A pasta '{folder_label}' nao existe.\n\n"
                    "Deseja criar agora?\n"
                    f"{folder_path}"
                ),
                qmessagebox.StandardButton.Yes | qmessagebox.StandardButton.No,
                qmessagebox.StandardButton.Yes,
            )
            if answer != qmessagebox.StandardButton.Yes:
                return
            try:
                os.makedirs(folder_path, exist_ok=True)
            except Exception as create_exc:
                logger.warning("Falha ao criar pasta %s: %s", folder_path, create_exc)
                qmessagebox.warning(self, "Erro", f"Falha ao criar pasta: {create_exc}")
                return

        try:
            safe_folder_path = SSAMainWindow._validate_local_open_target(
                folder_path,
                must_exist=True,
                expect_dir=True,
            )
        except Exception as exc:
            logger.warning(
                "Caminho de pasta invalido apos validacao (%s): %s", folder_label, exc
            )
            if os.environ.get("PYTEST_CURRENT_TEST"):
                return
            QMessageBox.warning(self, "Erro", f"Caminho de pasta invalido: {exc}")
            return

        try:
            # Prefer Qt abstraction to avoid blocking UI and keep cross-platform behavior.
            if QT_AVAILABLE:
                url = QUrl.fromLocalFile(safe_folder_path)
                if str(url.scheme() or "").casefold() != "file":
                    raise RuntimeError("URL local gerou scheme inesperado")
                ok = QDesktopServices.openUrl(url)
                if ok:
                    return
                raise RuntimeError("QDesktopServices.openUrl returned False")
            raise RuntimeError("Qt not available to open folders")
        except Exception as open_exc:
            logger.warning("Falha ao abrir pasta %s via Qt: %s", folder_label, open_exc)
            try:
                # Best-effort fallback, non-blocking.
                resolved = SSAMainWindow._resolve_platform_open_command()
                subprocess.Popen(  # nosec B603
                    ssa_system.build_platform_open_args(resolved, safe_folder_path),
                    shell=False,
                )
                return
            except Exception as fallback_exc:
                logger.warning("Fallback para abrir pasta falhou: %s", fallback_exc)
                if os.environ.get("PYTEST_CURRENT_TEST"):
                    return
                QMessageBox.warning(
                    self, "Erro", f"Erro ao abrir pasta: {fallback_exc}"
                )

    def _list_special_derivadas_sheets(self) -> list[str]:
        return ssa_derivadas_sync.list_special_derivadas_sheets(project_root)

    def _resolve_derivadas_table_name(self, db_path: str) -> str:
        return resolve_derivadas_table_name(
            db_path,
            (TABLE_NAME, *ALL_SSA_TABLE_NAMES),
            CANONICAL_SSA_TABLE,
        )

    def _get_derivadas_sync_state(self) -> ssa_derivadas_sync.DerivadasSyncState:
        state = getattr(self, "_derivadas_sync_state", None)
        if not isinstance(state, ssa_derivadas_sync.DerivadasSyncState):
            phase_status = str(getattr(self, "_derivadas_sync_phase_status", "") or "")
            state = ssa_derivadas_sync.DerivadasSyncState(
                running=bool(getattr(self, "_derivadas_sync_running", False)),
                thread=getattr(self, "_derivadas_sync_thread", None),
                pending_result=getattr(self, "_derivadas_sync_pending_result", None),
                phase_status=phase_status,
                ui_state=getattr(self, "_derivadas_sync_ui_state", {}) or {},
                table_name=str(getattr(self, "_derivadas_sync_table_name", "") or ""),
                last_status_text=phase_status,
            )
            self._derivadas_sync_state = state
        return state

    def _sync_derivadas_sync_state_attrs(
        self, state: ssa_derivadas_sync.DerivadasSyncState | None = None
    ) -> None:
        current = state or self._get_derivadas_sync_state()
        self._derivadas_sync_running = current.running
        self._derivadas_sync_thread = current.thread
        self._derivadas_sync_pending_result = current.pending_result
        self._derivadas_sync_phase_status = current.phase_status
        self._derivadas_sync_ui_state = current.ui_state
        self._derivadas_sync_table_name = current.table_name

    def _derivadas_sync_ui_refs(self) -> ssa_derivadas_sync.DerivadasSyncUiRefs:
        return ssa_derivadas_sync.DerivadasSyncUiRefs(
            message_parent=self,
            status_label=getattr(self, "status_label", None),
            progress_bar=getattr(self, "progress_bar", None),
            update_button=getattr(self, "update_derivadas_button", None),
            refresh_button_state=self._update_derivadas_button_state,
        )

    def update_derivadas_from_sources(self):
        state = self._get_derivadas_sync_state()
        deps = ssa_derivadas_sync.DerivadasSyncDependencies(
            qmessagebox=QMessageBox,
            qtimer=QTimer,
            sip_module=sip,
            thread_factory=threading.Thread,
            list_special_sheets=self._list_special_derivadas_sheets,
            resolve_table_name=self._resolve_derivadas_table_name,
            execute_job=SSAMainWindow._execute_derivadas_sync_job,
            finalize_result=SSAMainWindow._finalize_derivadas_sync_result,
            sync_state_callback=lambda: self._sync_derivadas_sync_state_attrs(state),
            logger=logger,
        )
        return ssa_derivadas_sync.update_derivadas_from_sources(
            self._derivadas_sync_ui_refs(),
            state,
            db_path=DB_PATH,
            deps=deps,
        )

    def _start_derivadas_sync_ui_state(
        self, previous_ui_state: dict[str, Any], initial_status: str
    ) -> None:
        state = self._get_derivadas_sync_state()
        return ssa_derivadas_sync.start_derivadas_sync_ui_state(
            self._derivadas_sync_ui_refs(),
            state,
            previous_ui_state,
            initial_status,
            logger,
        )

    @staticmethod
    def _execute_derivadas_sync_job(
        *,
        db_path: str,
        table_name: str,
        special_files: list[str],
        status_callback=None,
    ) -> dict[str, Any]:
        return ssa_derivadas_sync.execute_derivadas_sync_job(
            db_path=db_path,
            table_name=table_name,
            special_files=special_files,
            sync_derivadas_fn=sync_derivadas,
            scan_derivadas_consistency_fn=scan_derivadas_consistency,
            status_callback=status_callback,
        )

    def _finalize_derivadas_sync_result(
        self,
        result: dict[str, Any],
        *,
        previous_ui_state: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        state = self._get_derivadas_sync_state()
        finalized = ssa_derivadas_sync.finalize_derivadas_sync_result(
            self._derivadas_sync_ui_refs(),
            state,
            result,
            previous_ui_state=previous_ui_state,
            qmessagebox=QMessageBox,
            logger=logger,
        )
        self._sync_derivadas_sync_state_attrs(state)
        return finalized

    @staticmethod
    def _validate_database_candidate(db_file: str) -> dict[str, Any]:
        return ssa_database_operations.validate_database_candidate(
            db_file,
            table_name=TABLE_NAME,
            query_db_fn=query_db,
        )

    def _finalize_database_candidate_validation(
        self, result: dict[str, Any]
    ) -> dict[str, Any]:
        self._other_db_validation_running = False
        self._other_db_validation_thread = None
        self._other_db_validation_pending_result = None

        db_file = str(result.get("db_file") or "").strip()
        if bool(result.get("ok")) and db_file:
            global DB_PATH
            DB_PATH = db_file
            self.status_label.setText(
                f"Status: Banco alternativo selecionado: {os.path.basename(db_file)}"
            )
            if not os.environ.get("PYTEST_CURRENT_TEST"):
                QMessageBox.information(
                    self,
                    "Sucesso",
                    (
                        f"Banco de dados selecionado: {os.path.basename(db_file)}\n\n"
                        "Clique em 'Carregar Dados' para carregar os dados."
                    ),
                )
            return result

        error = str(result.get("error") or "").strip()
        if error:
            if not os.environ.get("PYTEST_CURRENT_TEST"):
                QMessageBox.critical(
                    self, "Erro", f"Erro ao abrir o banco de dados: {error}"
                )
            self.status_label.setText("Status: Falha ao validar banco alternativo.")
            return result

        if not os.environ.get("PYTEST_CURRENT_TEST"):
            QMessageBox.warning(
                self,
                "Erro",
                "O arquivo selecionado nao contem dados validos na tabela principal de SSAs.",
            )
        self.status_label.setText("Status: Banco alternativo invalido.")
        return {"ok": False, "db_file": db_file}

    def load_other_database(self):
        """Permite selecionar e carregar outro arquivo de banco de dados."""
        file_dialog = QFileDialog()
        db_file, _ = file_dialog.getOpenFileName(
            self,
            "Selecionar Banco de Dados",
            os.path.join(project_root, "data"),
            "Arquivos de Banco (*.db *.sqlite);;Todos os Arquivos (*)",
        )

        if db_file and os.path.exists(db_file):
            if bool(getattr(self, "_other_db_validation_running", False)):
                self.status_label.setText(
                    "Status: Validacao de banco alternativo ja em andamento."
                )
                return {"ok": False, "reason": "already_running", "db_file": db_file}
            self.status_label.setText("Status: Validando banco alternativo...")
            if os.environ.get("PYTEST_CURRENT_TEST"):
                result = SSAMainWindow._validate_database_candidate(db_file)
                return self._finalize_database_candidate_validation(result)

            self._other_db_validation_running = True
            self._other_db_validation_thread = None
            self._other_db_validation_pending_result = None

            def _window_alive() -> bool:
                if self is None:
                    return False
                if not hasattr(self, "metaObject"):
                    return True
                if sip is None:
                    return True
                try:
                    return not sip.isdeleted(self)
                except Exception:
                    return False

            def _work() -> None:
                self._other_db_validation_pending_result = (
                    SSAMainWindow._validate_database_candidate(db_file)
                )

            def _poll_delivery() -> None:
                if not _window_alive():
                    self._other_db_validation_pending_result = None
                    self._other_db_validation_thread = None
                    self._other_db_validation_running = False
                    return
                pending = getattr(self, "_other_db_validation_pending_result", None)
                if pending is None:
                    if bool(getattr(self, "_other_db_validation_running", False)):
                        QTimer.singleShot(100, _poll_delivery)
                    return
                self._other_db_validation_pending_result = None
                SSAMainWindow._finalize_database_candidate_validation(self, pending)

            worker = threading.Thread(target=_work, daemon=True)
            self._other_db_validation_thread = worker
            worker.start()
            QTimer.singleShot(100, _poll_delivery)
            return {"ok": True, "started": True, "db_file": db_file}
        elif db_file:  # Arquivo selecionado mas nao existe
            QMessageBox.warning(self, "Erro", "Arquivo selecionado nao existe.")

    def remove_persistent_filter(self, filter_data):
        """Remove um filtro persistente e atualiza imediatamente."""
        if filter_data in self.persistent_filters:
            current_search = self.search_input.text().strip()
            removed_active_filter = current_search == filter_data["terms"]
            previous_filter_state = None
            if removed_active_filter:
                try:
                    self._safe_store_last_filter_state("remove_persistent_filter")
                    previous_filter_state = copy.deepcopy(
                        getattr(self, "_last_filter_state", None)
                    )
                except Exception as exc:
                    logger.warning(
                        "Falha ao salvar estado antes de remover filtro persistente: %s",
                        exc,
                    )
            self.persistent_filters.remove(filter_data)
            if hasattr(self, "_invalidate_persistent_filter_index"):
                self._invalidate_persistent_filter_index()
            try:
                self._save_persistent_filters_file()
            except Exception as exc:
                logger.warning("Falha ao persistir remocao de filtro salvo: %s", exc)
            self.update_filter_tags()
            # Atualiza imediatamente se o filtro removido estava ativo
            if removed_active_filter:
                self.search_input.clear()
                self.initiate_filtering()
                if previous_filter_state:
                    self._last_filter_state = previous_filter_state
                    try:
                        self._update_undo_button_state()
                    except Exception as exc:
                        logger.debug(
                            "Falha ao atualizar botao undo apos remover filtro persistente: %s",
                            exc,
                        )

    def resizeEvent(self, event):
        """Reotimiza larguras das colunas quando a janela eh redimensionada."""
        super().resizeEvent(event)
        ssa_gui_resize.handle_resize_event(self, event)

    def _recompute_column_widths_on_resize(self, expected_revision=None):
        """Recalcula e aplica larguras das colunas apos resize da janela."""
        return ssa_gui_resize.recompute_column_widths_on_resize(
            self, expected_revision=expected_revision
        )

    def _schedule_resize_recompute(self, expected_revision: int) -> None:
        return ssa_gui_resize.schedule_resize_recompute(self, expected_revision)

    def _on_resize_recompute_timeout(self) -> None:
        return ssa_gui_resize.on_resize_recompute_timeout(self)

    def _apply_computed_widths_only(self):
        """Aplica apenas as larguras calculadas pelo WidthManager (ignora configurações salvas)."""
        return ssa_gui_resize.apply_computed_widths_only(self)

    def closeEvent(self, event):
        """
        Metodo chamado quando a janela eh fechada.
        Garante cleanup adequado dos QThreads para evitar o erro:
        'QThread: Destroyed while thread is still running'
        """
        ssa_gui_workers.cleanup_window_workers_on_close(
            self,
            **_close_retention_kwargs(),
            sip_module=sip,
        )

        # Aceita o evento de fechamento
        event.accept()


# --- Ponto de Entrada ---
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SSAMainWindow()
    window.show()
    sys.exit(app.exec())
