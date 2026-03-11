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


def _prepare_frozen_runtime(app_dir: str) -> Path:
    """Configura ambiente de runtime gravavel para execucao frozen."""
    runtime_dir = _resolve_runtime_home()
    runtime_logs = runtime_dir / "logs"
    runtime_logs.mkdir(parents=True, exist_ok=True)
    bundled_config = _find_bundled_config_dir(app_dir)
    _seed_runtime_config(runtime_dir, bundled_config)
    os.chdir(runtime_dir)
    return runtime_dir

# Adicionar diretorio raiz ao path CORRETAMENTE
if getattr(sys, 'frozen', False):
    # Executavel PyInstaller - buscar na raiz dos dados empacotados
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller - usar diretorio do executavel, NAO _MEIPASS (pasta temporaria)
        app_dir = os.path.dirname(os.path.abspath(sys.executable))
    else:
        app_dir = os.path.dirname(sys.executable)
    _prepare_frozen_runtime(app_dir)
else:
    # Script Python normal
    app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.insert(0, app_dir)

def main():
    """Entry point GUI v3.10"""
    try:
        from PyQt6.QtWidgets import QApplication
        from gui.gui_ssa import SSAMainWindow

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
        print(f"Arquivos em app_dir: {os.listdir(app_dir) if os.path.exists(app_dir) else 'N/A'}")
        sys.exit(1)
    except Exception as e:
        print(f"ERRO na GUI: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
