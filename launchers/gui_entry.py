#!/usr/bin/env python3
"""
Entry point GUI para executavel v3.10
Separado do main.py principal
"""

import os
import shutil
import sys
from pathlib import Path

APP_RUNTIME_NAME = "SSA_Consulta_Rapida"


def _resolve_runtime_home() -> Path:
    """Retorna diretório gravavel de runtime para apps congelados."""
    home_dir = Path.home()
    if sys.platform == "darwin":
        base_dir = home_dir / "Library" / "Application Support"
    elif sys.platform.startswith("win"):
        appdata = os.environ.get("APPDATA")
        if appdata:
            base_dir = Path(appdata)
        else:
            base_dir = home_dir / "AppData" / "Roaming"
    else:
        base_dir = Path(os.environ.get("XDG_DATA_HOME", home_dir / ".local" / "share"))
    runtime_dir = base_dir / APP_RUNTIME_NAME
    runtime_dir.mkdir(parents=True, exist_ok=True)
    return runtime_dir


def _find_bundled_config_dir(app_dir: str) -> Path | None:
    """Localiza config embutida em diferentes layouts de empacotamento."""
    exe_path = Path(sys.executable).resolve()
    app_path = Path(app_dir)
    candidates = (
        app_path / "config",
        app_path / "_internal" / "config",
        exe_path.parent.parent / "Resources" / "config",
        exe_path.parent.parent / "config",
    )
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    return None


def _find_bundled_data_dir(app_dir: str) -> Path | None:
    """Localiza data embutida em diferentes layouts de empacotamento."""
    exe_path = Path(sys.executable).resolve()
    app_path = Path(app_dir)
    candidates = (
        app_path / "data",
        app_path / "_internal" / "data",
        exe_path.parent.parent / "Resources" / "data",
    )
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    return None


def _find_bundled_resources_dir(app_dir: str) -> Path | None:
    """Localiza resources embutido em diferentes layouts de empacotamento."""
    exe_path = Path(sys.executable).resolve()
    app_path = Path(app_dir)
    candidates = (
        app_path / "resources",
        app_path / "_internal" / "resources",
        exe_path.parent.parent / "Resources" / "resources",
        exe_path.parent.parent / "resources",
    )
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    return None


def _seed_runtime_config(runtime_dir: Path, bundled_config: Path | None) -> Path:
    """Inicializa config de runtime do usuario com defaults empacotados."""
    runtime_config = runtime_dir / "config"
    runtime_config.mkdir(parents=True, exist_ok=True)
    if bundled_config is None:
        return runtime_config
    try:
        for source in bundled_config.iterdir():
            target = runtime_config / source.name
            if source.is_dir():
                try:
                    shutil.copytree(source, target, dirs_exist_ok=True)
                except TypeError:
                    if not target.exists():
                        shutil.copytree(source, target)
            elif source.is_file() and not target.exists():
                shutil.copy2(source, target)
    except Exception:
        # Seed de config e best-effort para nao bloquear startup da GUI.
        pass
    return runtime_config


def _seed_runtime_data(runtime_dir: Path, bundled_data: Path | None) -> Path:
    """Inicializa data de runtime com fallback para bundle."""
    runtime_data = runtime_dir / "data"
    runtime_data.mkdir(parents=True, exist_ok=True)
    if bundled_data is None:
        return runtime_data

    source_db = bundled_data / "ssas.db"
    target_db = runtime_data / "ssas.db"
    if source_db.is_file() and not target_db.exists():
        try:
            shutil.copy2(source_db, target_db)
        except Exception:
            # DB local pode nao existir em certos builds; nao bloquear startup.
            pass
    return runtime_data


def _seed_runtime_resources(runtime_dir: Path, bundled_resources: Path | None) -> Path:
    """Inicializa resources local para manter icones e assets da UI."""
    runtime_resources = runtime_dir / "resources"
    runtime_resources.mkdir(parents=True, exist_ok=True)
    if bundled_resources is None:
        return runtime_resources
    try:
        for source in bundled_resources.iterdir():
            target = runtime_resources / source.name
            if source.is_dir():
                try:
                    shutil.copytree(source, target, dirs_exist_ok=True)
                except TypeError:
                    if not target.exists():
                        shutil.copytree(source, target)
            elif source.is_file() and not target.exists():
                shutil.copy2(source, target)
    except Exception:
        # Resources sao auxiliares e nao devem bloquear startup.
        pass
    return runtime_resources


def _prepare_frozen_runtime(app_dir: str) -> Path:
    """Configura ambiente de runtime gravavel para execucao frozen."""
    runtime_dir = _resolve_runtime_home()
    runtime_logs = runtime_dir / "logs"
    runtime_docs_in = runtime_dir / "docs_entrada"
    runtime_docs_out = runtime_dir / "docs_saida"
    runtime_reports = runtime_dir / "reports"
    runtime_exportacao = runtime_dir / "exportacao"
    runtime_data_backups = runtime_dir / "data" / "historico_backups"
    for folder in (
        runtime_logs,
        runtime_docs_in,
        runtime_docs_out,
        runtime_reports,
        runtime_exportacao,
        runtime_data_backups,
    ):
        folder.mkdir(parents=True, exist_ok=True)
    bundled_config = _find_bundled_config_dir(app_dir)
    bundled_data = _find_bundled_data_dir(app_dir)
    bundled_resources = _find_bundled_resources_dir(app_dir)
    runtime_config = _seed_runtime_config(runtime_dir, bundled_config)
    runtime_data = _seed_runtime_data(runtime_dir, bundled_data)
    _seed_runtime_resources(runtime_dir, bundled_resources)
    os.environ.setdefault("SSA_BUNDLED_ROOT", app_dir)
    os.environ.setdefault("SSA_RUNTIME_ROOT", str(runtime_dir))
    os.environ.setdefault("SSA_CONFIG_DIR", str(runtime_config))
    os.environ.setdefault("SSA_DB_PATH", str(runtime_data / "ssas.db"))
    allowed_roots = [
        str(runtime_dir),
        str(runtime_config),
        str(runtime_data),
        str(runtime_docs_in),
        str(runtime_docs_out),
        str(runtime_reports),
        str(runtime_exportacao),
        str(runtime_logs),
    ]
    existing_extra = os.environ.get("SSA_EXTRA_ALLOWED_PATHS", "")
    for candidate in existing_extra.split(os.pathsep):
        candidate = candidate.strip()
        if candidate:
            allowed_roots.append(candidate)
    dedup_allowed: list[str] = []
    for candidate in allowed_roots:
        if candidate not in dedup_allowed:
            dedup_allowed.append(candidate)
    os.environ["SSA_EXTRA_ALLOWED_PATHS"] = os.pathsep.join(dedup_allowed)
    os.chdir(runtime_dir)
    return runtime_dir


# Adicionar diretorio raiz ao path CORRETAMENTE
exe_path = Path(sys.executable)
is_frozen_runtime = bool(
    getattr(sys, "frozen", False)
    or getattr(sys, "oxidized", False)
    or "__compiled__" in globals()
    or exe_path.parent.name.endswith(".dist")
    or exe_path.name.startswith(("SSA_GUI_", "SSA_Consulta_Rapida"))
)
if is_frozen_runtime:
    # Executavel empacotado - buscar na raiz dos dados empacotados.
    if hasattr(sys, "_MEIPASS"):
        # PyInstaller - usar diretorio do executavel, NAO _MEIPASS (pasta temporaria)
        app_dir = os.path.dirname(os.path.abspath(sys.executable))
    else:
        app_dir = os.path.dirname(os.path.abspath(sys.executable))
    _prepare_frozen_runtime(app_dir)
else:
    # Script Python normal
    app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.insert(0, app_dir)


def main():
    """Entry point GUI v3.10"""
    try:
        from PyQt6.QtWidgets import QApplication

        from core.config_manager import ensure_default_settings
        from gui.gui_ssa import SSAMainWindow
        from utils import setup_project_structure

        setup_project_structure.setup_dirs()
        ensure_default_settings(fail_fast=False)

        app = QApplication(sys.argv)
        app.setApplicationName("Consulta Rapida de SSAs")
        app.setApplicationDisplayName("Consulta Rapida de SSAs")
        window = SSAMainWindow()
        window.show()
        sys.exit(app.exec())
    except ImportError as e:
        print(f"ERRO: Nao foi possivel importar modulos GUI: {e}")
        print(f"Path atual: {sys.path}")
        print(f"App dir: {app_dir}")
        print(
            f"Arquivos em app_dir: {os.listdir(app_dir) if os.path.exists(app_dir) else 'N/A'}"
        )
        sys.exit(1)
    except Exception as e:
        print(f"ERRO na GUI: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
