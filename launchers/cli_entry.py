#!/usr/bin/env python3
"""
Entry point CLI para executavel v3.10
Separado do main.py principal
"""

import os
import shutil
import sys
import traceback
from pathlib import Path

APP_RUNTIME_NAME = "SSA_Consulta_Rapida"


def _resolve_runtime_home() -> Path:
    """Retorna diretorio gravavel de runtime para apps frozen."""
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


def _find_bundled_dir(app_dir: str, folder_name: str) -> Path | None:
    """Localiza pasta embutida em layouts de empacotamento comuns."""
    exe_path = Path(sys.executable).resolve()
    app_path = Path(app_dir)
    candidates = (
        app_path / folder_name,
        app_path / "_internal" / folder_name,
        exe_path.parent.parent / "Resources" / folder_name,
        exe_path.parent.parent / folder_name,
    )
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    return None


def _seed_runtime_config(runtime_dir: Path, bundled_config: Path | None) -> Path:
    """Inicializa config de runtime com defaults do bundle."""
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
        pass

    return runtime_config


def _seed_runtime_data(runtime_dir: Path, bundled_data: Path | None) -> Path:
    """Inicializa data de runtime com fallback para DB do bundle."""
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
            pass
    return runtime_data


def _prepare_frozen_runtime(app_dir: str) -> Path:
    """Configura runtime gravavel para execucao frozen."""
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

    bundled_config = _find_bundled_dir(app_dir, "config")
    bundled_data = _find_bundled_dir(app_dir, "data")
    runtime_config = _seed_runtime_config(runtime_dir, bundled_config)
    runtime_data = _seed_runtime_data(runtime_dir, bundled_data)

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
    """Entry point CLI v3.10.

    Comportamento especial para smoke test automático: se a variável de ambiente
    SSA_SMOKE_TEST=1 estiver presente, imprime um marcador simples e sai sem
    iniciar a interface interativa. Isso permite que scripts de CI validem
    rapidamente a integridade do carregamento sem bloquear esperando input.
    """
    if os.environ.get("SSA_SMOKE_TEST") == "1":
        try:
            from utils.version import get_app_version  # import leve
            version = get_app_version()
            print(f"SMOKE_CLI_OK v{version}")
            sys.exit(0)
        except Exception as exc:  # pragma: no cover - raríssimo
            print(f"SMOKE_CLI_FAIL {exc}")
            sys.exit(1)

    try:
        from interface.cli import start_cli_loop
        db_path = os.environ.get("SSA_DB_PATH") or os.path.join(app_dir, "data", "ssas.db")
        table_name = os.environ.get("SSA_TABLE_NAME") or "ssa_table"
        start_cli_loop(db_path, table_name)
    except ImportError as e:
        print(f"ERRO: Nao foi possivel importar interface.cli: {e}")
        print(f"Path atual: {sys.path}")
        print(f"App dir: {app_dir}")
        print(f"Arquivos em app_dir: {os.listdir(app_dir) if os.path.exists(app_dir) else 'N/A'}")
        sys.exit(1)
    except Exception as e:
        print(f"ERRO: Falha inesperada ao iniciar CLI: {e}")
        traceback.print_exc()
        print(f"Path atual: {sys.path}")
        print(f"App dir: {app_dir}")
        sys.exit(1)

if __name__ == "__main__":
    main()
