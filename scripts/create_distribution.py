"""
Script para criar pacotes de distribuicao do SSA Consulta Rapida.

Cria:
1. Arquivo ZIP portatil com executavel e estrutura completa
2. Instalador Windows usando Inno Setup (se disponivel)

Uso:
    uv run --python 3.13 scripts/create_distribution.py --build-system pyinstaller
    uv run --python 3.13 scripts/create_distribution.py --build-system pyoxidizer --skip-installer
    uv run --python 3.13 scripts/create_distribution.py --all
"""

import argparse
import json
import os
import shutil
import subprocess
import zipfile
from pathlib import Path
from typing import Optional

from shared.date_utils import format_current_timestamp
from utils.robust_logging import get_robust_logger

logger = get_robust_logger().get_logger(__name__, "distribution")

# Configuracoes
PROJECT_ROOT = Path(__file__).parent.parent
VERSION_FILE = PROJECT_ROOT / "VERSION"
DIST_OUTPUT = PROJECT_ROOT / "dist_packages"
PYINSTALLER_CANONICAL_DIRS = (
    "launchers/dist/windows_amd64",
    "launchers/dist/macos_arm64",
    "launchers/dist/debian_amd64",
)
PACKAGE_PLATFORMS = (
    "windows_amd64",
    "macos_arm64",
    "debian_amd64",
    "debian_arm64",
)
EXCLUDED_BUNDLE_ITEMS = {
    "data",
    "docs_entrada",
    "logs",
    "reports",
    "exportacao",
    "historico_backups",
}

SENSITIVE_LOCAL_EXTENSIONS: set[str] = {
    ".db",
    ".xls",
    ".xlsx",
}
SENSITIVE_LOCAL_NAME_FRAGMENTS = (
    ".bak",
    ".backup",
)
SAMPLE_DB_ASSET_DIR = Path("dist_assets") / "sample_db"
SAMPLE_DB_ASSET_NAME = "ssas_example.db"
SAMPLE_DB_ASSET_README_NAME = "LEIA-ME.txt"
APP_RUNTIME_DIR = "SSA_Consulta_Rapida"
PACKAGE_SAMPLE_DB_DIR = "BancoExemplo"
INSTALLER_SAMPLE_DB_DIR_SPEC = r"{userdocs}\SSA Consulta Rapida\BancoExemplo"
PACKAGE_LOCAL_DB_DIR = "BancoLocal"
INSTALLER_LOCAL_DB_DIR_SPEC = r"{userdocs}\SSA Consulta Rapida\BancoLocal"

# Informacoes dos build systems
BUILD_SYSTEMS = {
    "pyinstaller": {
        "name": "PyInstaller",
        "exe_path": "launchers/dist/windows_amd64/SSA_GUI.exe",
        "base_dir": "launchers/dist/windows_amd64",
        "canonical_dirs": [
            "launchers/dist/windows_amd64",
            "builds/pyinstaller/windows_amd64",
            "launchers/dist/macos_arm64",
            "builds/pyinstaller/macos_arm64",
            "launchers/dist/debian_amd64",
            "builds/pyinstaller/debian_amd64",
        ],
        "internal_dir": "_internal",
    },
    "pyoxidizer": {
        "name": "PyOxidizer",
        "exe_path": "builds/pyoxidizer/windows_amd64/SSA_Consulta_Rapida.exe",
        "base_dir": "builds/pyoxidizer/windows_amd64",
        "internal_dir": "lib",
    },
    "nuitka": {
        "name": "Nuitka",
        "exe_path": "builds/nuitka/windows_amd64/main.exe",
        "base_dir": "builds/nuitka/windows_amd64",
        "internal_dir": None,
    },
}

# Diretorios que devem ser criados para o usuario
USER_DIRS = [
    "data",
    "data/historico_backups",
    "docs_entrada",
    "docs_saida",
    "logs",
    "reports",
    "exportacao",
]

# Arquivos de documentacao para incluir
DOC_FILES = [
    "README.md",
    "docs/ANTIVIRUS_EXCLUSOES.md",
    "docs/GUIA_MIGRACAO_NOVA_INSTALACAO.md",
]


def _has_packagable_content(directory: Path) -> bool:
    """Retorna True quando o diretorio tem conteudo util para empacotamento."""
    if not directory.exists() or not directory.is_dir():
        return False
    for item in directory.iterdir():
        if item.name in {".git", "__pycache__", "logs"}:
            continue
        return True
    return False


def _get_pyinstaller_canonical_dirs() -> tuple[str, ...]:
    """Retorna lista de diretorios canonicos do PyInstaller (configuravel)."""
    build_info = BUILD_SYSTEMS.get("pyinstaller", {})
    configured = build_info.get("canonical_dirs")
    if isinstance(configured, (list, tuple)):
        normalized = tuple(str(item) for item in configured if isinstance(item, str))
        if normalized:
            return normalized
    return PYINSTALLER_CANONICAL_DIRS


def _has_primary_executable(build_dir: Path, build_system: str) -> bool:
    """Valida existencia de executavel primario esperado no diretorio de build."""
    if not build_dir.exists() or not build_dir.is_dir():
        return False

    if build_system == "pyinstaller":
        return _resolve_primary_executable_name(build_dir, prefer_gui=True) is not None

    if build_system == "nuitka":
        return _resolve_primary_executable_name(build_dir, prefer_gui=True) is not None

    build_info = BUILD_SYSTEMS.get(build_system, {})
    exe_path_value = build_info.get("exe_path")
    if isinstance(exe_path_value, str):
        expected = PROJECT_ROOT / exe_path_value
        if expected.is_file():
            return True
        expected_local = build_dir / Path(exe_path_value).name
        if expected_local.is_file():
            return True
        if expected_local.suffix and (build_dir / expected_local.stem).is_file():
            return True
    return False


PRIMARY_EXECUTABLE_NAMES = (
    "SSA_Consulta_Rapida.exe",
    "SSA_GUI.exe",
    "main.exe",
)
POSIX_EXECUTABLE_MAGICS = {
    b"\x7fELF",
    b"\xfe\xed\xfa\xce",
    b"\xfe\xed\xfa\xcf",
    b"\xce\xfa\xed\xfe",
    b"\xcf\xfa\xed\xfe",
    b"\xca\xfe\xba\xbe",
    b"\xbe\xba\xfe\xca",
    b"\xca\xfe\xba\xbf",
    b"\xbf\xba\xfe\xca",
}


def _preferred_file_candidates(_source_dir: Path, file_entries: list[Path]) -> list[str]:
    existing = {p.name for p in file_entries}
    return [name for name in PRIMARY_EXECUTABLE_NAMES if name in existing]


def _gui_dir_candidates(source_dir: Path, _file_entries: list[Path]) -> list[str]:
    candidates: list[str] = []
    for gui_dir in sorted(p for p in source_dir.glob("*GUI*") if p.is_dir()):
        canonical_exe = gui_dir / f"{gui_dir.name}.exe"
        if canonical_exe.is_file():
            candidates.append(f"{gui_dir.name}\\{canonical_exe.name}")
            continue
        nested_exes = sorted(p for p in gui_dir.glob("*.exe") if p.is_file())
        if nested_exes:
            candidates.append(f"{gui_dir.name}\\{nested_exes[0].name}")
    return candidates


def _exe_file_candidates(
    _source_dir: Path, file_entries: list[Path], prefer_gui: bool
) -> list[str]:
    gui_matches = [
        p.name for p in sorted(file_entries) if prefer_gui and "GUI" in p.name
    ]
    exe_matches = [p.name for p in sorted(file_entries) if p.suffix.lower() == ".exe"]
    return gui_matches + [name for name in exe_matches if name not in gui_matches]


def _posix_executable_candidates(
    _source_dir: Path, file_entries: list[Path]
) -> list[str]:
    candidates = []
    for path in sorted(file_entries):
        if not os.access(path, os.X_OK):
            continue
        with path.open("rb") as stream:
            magic = stream.read(4)
        if magic in POSIX_EXECUTABLE_MAGICS or magic.startswith(b"#!"):
            candidates.append(path.name)
    return candidates


def _app_bundle_candidates(source_dir: Path, _file_entries: list[Path]) -> list[str]:
    return sorted(
        p.name for p in source_dir.iterdir() if p.is_dir() and p.name.lower().endswith(".app")
    )


def _embedded_executable_candidates(source_dir: Path, _file_entries: list[Path]) -> list[str]:
    return sorted(
        f"{p.name}/{p.name}"
        for p in source_dir.iterdir()
        if p.is_dir() and (p / p.name).is_file() and os.access(p / p.name, os.X_OK)
    )


def _embedded_exe_candidates(source_dir: Path, _file_entries: list[Path]) -> list[str]:
    return sorted(
        f"{p.name}/{p.name}.exe"
        for p in source_dir.iterdir()
        if p.is_dir() and (p / f"{p.name}.exe").is_file()
    )


def _resolve_primary_executable_name(
    source_dir: Path, prefer_gui: bool = False
) -> Optional[str]:
    """Resolve executavel principal dentro de um diretorio de build."""
    if not source_dir.exists() or not source_dir.is_dir():
        return None

    file_entries = [p for p in source_dir.iterdir() if p.is_file()]
    candidates = _preferred_file_candidates(source_dir, file_entries)
    if candidates:
        return candidates[0]

    if prefer_gui:
        candidates = _gui_dir_candidates(source_dir, file_entries)
        if candidates:
            return candidates[0]

    probe_results = (
        _exe_file_candidates(source_dir, file_entries, prefer_gui),
        _posix_executable_candidates(source_dir, file_entries),
        _app_bundle_candidates(source_dir, file_entries),
        _embedded_executable_candidates(source_dir, file_entries),
        _embedded_exe_candidates(source_dir, file_entries),
    )
    for candidates in probe_results:
        if candidates:
            return candidates[0]
    return None


def _resolve_nuitka_bundle_dir() -> Optional[Path]:
    """Resolve pasta *.dist mais recente do build Nuitka Windows."""
    base_dir = PROJECT_ROOT / str(BUILD_SYSTEMS["nuitka"]["base_dir"])
    if not base_dir.exists() or not base_dir.is_dir():
        return None

    canonical_gui = base_dir / "gui_entry.dist"
    if canonical_gui.is_dir():
        return canonical_gui

    gui_by_contents = sorted(
        (
            p
            for p in base_dir.glob("*.dist")
            if p.is_dir() and any(child.is_file() for child in p.glob("*GUI*.exe"))
        ),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if gui_by_contents:
        return gui_by_contents[0]

    gui_candidates = sorted(
        (p for p in base_dir.glob("*GUI*.dist") if p.is_dir()),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if gui_candidates:
        return gui_candidates[0]

    generic_candidates = sorted(
        (p for p in base_dir.glob("*.dist") if p.is_dir()),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if generic_candidates:
        return generic_candidates[0]

    return None


def _build_dir_status(build_dir: Path, build_system: str) -> str:
    """Retorna status do diretorio de build: missing|empty|no_primary|ok."""
    if not build_dir.exists() or not build_dir.is_dir():
        return "missing"
    if not _has_packagable_content(build_dir):
        return "empty"
    if not _has_primary_executable(build_dir, build_system):
        return "no_primary"
    return "ok"


def _build_directory_candidates(build_system: str) -> list[Path]:
    build_info = BUILD_SYSTEMS.get(build_system, {})
    base_dir_value = build_info.get("base_dir")
    candidates: list[Path] = []
    if build_system == "nuitka":
        bundle_dir = _resolve_nuitka_bundle_dir()
        return [bundle_dir] if bundle_dir is not None else []
    if build_system == "pyinstaller":
        candidates.extend(PROJECT_ROOT / rel for rel in _get_pyinstaller_canonical_dirs())
    if isinstance(base_dir_value, str):
        candidates.append(PROJECT_ROOT / base_dir_value)
    return candidates


def _resolve_build_directory(build_system: str) -> Optional[Path]:
    """Resolve diretorio de build. PyInstaller usa canonical com fallback legacy."""
    for build_dir in _build_directory_candidates(build_system):
        if _build_dir_status(build_dir, build_system) == "ok":
            return build_dir
    return None


def _resolve_build_directory_failure_reason(build_system: str) -> str:
    """Retorna motivo detalhado quando _resolve_build_directory falha."""
    build_info = BUILD_SYSTEMS.get(build_system, {})

    if build_system == "nuitka":
        base_dir = PROJECT_ROOT / str(build_info.get("base_dir", ""))
        if not base_dir.exists():
            return f"Diretorio de build ausente: {base_dir}"
        if _resolve_nuitka_bundle_dir() is None:
            return f"Nenhum bundle *.dist encontrado em: {base_dir}"
        return "Bundle Nuitka encontrado, mas sem executavel primario"

    if build_system == "pyinstaller":
        for path in _build_directory_candidates("pyinstaller"):
            if _build_dir_status(path, "pyinstaller") == "no_primary":
                if _is_canonical_pyinstaller_directory(path):
                    return f"Executavel primario ausente em diretorio canonico: {path}"
                return f"Executavel primario ausente no diretorio: {path}"

    base_dir_value = build_info.get("base_dir")
    if not isinstance(base_dir_value, str):
        return f"Configuracao invalida: base_dir ausente para {build_system}"

    legacy_dir = PROJECT_ROOT / base_dir_value
    legacy_status = _build_dir_status(legacy_dir, build_system)
    if legacy_status == "missing":
        return f"Diretorio de build ausente: {legacy_dir}"
    if legacy_status == "empty":
        return f"Diretorio de build sem conteudo empacotavel: {legacy_dir}"
    if legacy_status == "no_primary":
        return f"Executavel primario ausente no diretorio: {legacy_dir}"
    return f"Diretorio de build nao resolvido para {build_system}"


def _copy_build_tree_sanitized(source_dir: Path, target_dir: Path) -> None:
    """Copia build para distribuicao, removendo dados locais sensiveis."""
    for item in source_dir.iterdir():
        if _should_skip_bundle_path(item, bundle_root=source_dir):
            continue
        destination = target_dir / item.name
        try:
            if item.is_file():
                shutil.copy2(item, destination)
            elif item.is_dir():
                shutil.copytree(
                    item,
                    destination,
                    dirs_exist_ok=True,
                    ignore=lambda src, names: _build_bundle_ignore(
                        source_dir, src, names
                    ),
                )
        except OSError as exc:
            logger.error(
                "Falha ao copiar item do build para pacote: %s -> %s: %s",
                item,
                destination,
                exc,
            )
            raise


def _should_skip_bundle_entry(name: str, is_file: bool) -> bool:
    if name in {".git", "__pycache__", "logs"}:
        return True
    if name in EXCLUDED_BUNDLE_ITEMS:
        return True
    lowered_name = name.lower()
    if any(fragment in lowered_name for fragment in SENSITIVE_LOCAL_NAME_FRAGMENTS):
        return True
    if is_file and Path(name).suffix.lower() in SENSITIVE_LOCAL_EXTENSIONS:
        return True
    return False


def _should_skip_bundle_path(candidate: Path, *, bundle_root: Path | None = None) -> bool:
    if _should_skip_bundle_entry(candidate.name, candidate.is_file()):
        return True
    if candidate.is_file() and candidate.name == "__init__.py":
        if bundle_root is None:
            return candidate.parent.name == "config"
        return candidate.parent.name == "config" and candidate.parent.parent == bundle_root
    return False


def _build_bundle_ignore(bundle_root: Path, _src: str, names: list[str]) -> set[str]:
    ignored: set[str] = set()
    src_path = Path(_src)
    for name in names:
        candidate = src_path / name
        if _should_skip_bundle_path(candidate, bundle_root=bundle_root):
            ignored.add(name)
    return ignored


def _infer_platform_from_path(build_dir: Path) -> Optional[str]:
    parts = build_dir.resolve(strict=False).parts
    for platform in PACKAGE_PLATFORMS:
        if platform in parts:
            return platform
    return None


def _package_output_dir(build_dir: Path) -> Optional[Path]:
    platform = _infer_platform_from_path(build_dir)
    if platform is None:
        logger.error("Nao foi possivel inferir plataforma do build: %s", build_dir)
        return None
    return PROJECT_ROOT / "builds" / "packages" / platform


def _resolve_sample_db_assets() -> Optional[tuple[Path, Path]]:
    """Resolve os assets fixos do banco de exemplo aprovados no repositorio."""
    sample_db_dir = PROJECT_ROOT / SAMPLE_DB_ASSET_DIR
    sample_db_path = sample_db_dir / SAMPLE_DB_ASSET_NAME
    sample_db_readme_path = sample_db_dir / SAMPLE_DB_ASSET_README_NAME

    missing_assets = [
        str(path)
        for path in (sample_db_path, sample_db_readme_path)
        if not path.is_file()
    ]
    if missing_assets:
        logger.error(
            "Assets fixos do banco de exemplo ausentes: %s",
            ", ".join(missing_assets),
        )
        return None

    return sample_db_path, sample_db_readme_path


def _copy_sample_db_assets(target_dir: Path) -> bool:
    """Copia o banco de exemplo aprovado para uma pasta separada do pacote."""
    resolved_assets = _resolve_sample_db_assets()
    if resolved_assets is None:
        return False

    sample_db_path, sample_db_readme_path = resolved_assets
    sample_db_target_dir = target_dir / PACKAGE_SAMPLE_DB_DIR
    sample_db_target_dir.mkdir(parents=True, exist_ok=True)

    shutil.copy2(sample_db_path, sample_db_target_dir / SAMPLE_DB_ASSET_NAME)
    shutil.copy2(
        sample_db_readme_path,
        sample_db_target_dir / SAMPLE_DB_ASSET_README_NAME,
    )
    logger.info(
        "Banco de exemplo copiado para %s",
        sample_db_target_dir,
    )
    return True


def _resolve_local_db_asset(local_db_path: str) -> Optional[Path]:
    """Resolve um banco local explicitamente aprovado para empacotamento."""
    raw_value = str(local_db_path or "").strip()
    if not raw_value:
        logger.error("Parametro include_local_db vazio")
        return None

    candidate = Path(raw_value).expanduser()
    if not candidate.is_absolute():
        candidate = PROJECT_ROOT / candidate
    try:
        resolved = candidate.resolve(strict=True)
    except FileNotFoundError:
        logger.error(
            "Banco local explicitamente solicitado nao encontrado: %s", candidate
        )
        return None

    if not resolved.is_file():
        logger.error(
            "Banco local explicitamente solicitado nao e arquivo: %s", resolved
        )
        return None
    if resolved.suffix.lower() != ".db":
        logger.error(
            "Banco local explicitamente solicitado deve terminar em .db: %s", resolved
        )
        return None
    return resolved


def _copy_local_db_asset(target_dir: Path, local_db_path: str) -> bool:
    """Copia um banco local explicitamente escolhido para uma pasta separada do pacote."""
    resolved_local_db = _resolve_local_db_asset(local_db_path)
    if resolved_local_db is None:
        return False

    local_db_target_dir = target_dir / PACKAGE_LOCAL_DB_DIR
    local_db_target_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(resolved_local_db, local_db_target_dir / resolved_local_db.name)
    logger.info(
        "Banco local explicitamente escolhido copiado para %s",
        local_db_target_dir,
    )
    return True


def _detect_primary_executable_name(package_dir: Path) -> Optional[str]:
    """Escolhe executavel principal para instrucoes do usuario."""
    return _resolve_primary_executable_name(package_dir, prefer_gui=True)


def _resolve_inno_source(build_system: str) -> Optional[tuple[Path, str]]:
    """Resolve diretorio/arquivo principal usado no script Inno Setup."""
    if build_system == "pyinstaller":
        canonical_windows = next(
            (
                PROJECT_ROOT / rel
                for rel in _get_pyinstaller_canonical_dirs()
                if "windows_amd64" in rel
            ),
            PROJECT_ROOT / "launchers" / "dist" / "windows_amd64",
        )
        if _has_packagable_content(canonical_windows):
            exe_name = _resolve_primary_executable_name(
                canonical_windows, prefer_gui=True
            )
            if exe_name:
                return canonical_windows, exe_name

    if build_system == "nuitka":
        source_dir = _resolve_nuitka_bundle_dir()
        if source_dir is None:
            return None
        exe_name = _resolve_primary_executable_name(source_dir, prefer_gui=True)
        if exe_name is None:
            return None
        return source_dir, exe_name

    if build_system == "pyoxidizer":
        base_dir_value = BUILD_SYSTEMS["pyoxidizer"].get("base_dir")
        if not isinstance(base_dir_value, str):
            return None
        source_dir = PROJECT_ROOT / base_dir_value
        if not source_dir.exists():
            return None
        exe_name = _resolve_primary_executable_name(source_dir, prefer_gui=False)
        if exe_name is None:
            return None
        return source_dir, exe_name

    build_info = BUILD_SYSTEMS[build_system]
    base_dir_value = build_info.get("base_dir")
    if not isinstance(base_dir_value, str):
        return None
    source_dir = PROJECT_ROOT / base_dir_value
    if not source_dir.exists():
        return None

    exe_path_value = build_info.get("exe_path")
    if isinstance(exe_path_value, str):
        return source_dir, Path(exe_path_value).name
    return None


def _is_canonical_pyinstaller_directory(build_dir: Path) -> bool:
    """Retorna True quando o build_dir aponta para launchers/dist canonico."""
    canonical = {PROJECT_ROOT / rel for rel in _get_pyinstaller_canonical_dirs()}
    return build_dir in canonical


def get_version() -> str:
    """Le o numero de versao sem aceitar fallback silencioso."""
    if VERSION_FILE.is_file():
        version = VERSION_FILE.read_text(encoding="utf-8").strip()
        if version:
            return version
        raise RuntimeError(f"VERSION vazio: {VERSION_FILE}")

    version_json = PROJECT_ROOT / "config" / "version.json"
    if not version_json.is_file():
        raise RuntimeError(f"Arquivo de versao ausente: {version_json}")

    try:
        data = json.loads(version_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Arquivo de versao invalido: {version_json}: {exc}") from exc

    version = str(data.get("version_short") or data.get("version") or "").strip()
    if not version:
        raise RuntimeError(f"version_short ausente em {version_json}")
    return version


def create_user_structure(target_dir: Path):
    """Cria estrutura de diretorios para usuario final."""
    logger.info("Criando estrutura de diretorios em %s", target_dir)

    for dir_name in USER_DIRS:
        dir_path = target_dir / dir_name
        dir_path.mkdir(parents=True, exist_ok=True)

        # Criar arquivo .gitkeep para manter diretorios no ZIP
        gitkeep = dir_path / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.touch()

    logger.info("Criados %s diretorios", len(USER_DIRS))


def copy_documentation(target_dir: Path):
    """Copia documentacao essencial para o pacote."""
    logger.info("Copiando documentacao")

    docs_dir = target_dir / "docs"
    docs_dir.mkdir(exist_ok=True)

    for doc_file in DOC_FILES:
        src = PROJECT_ROOT / doc_file
        if src.exists():
            if doc_file == "README.md":
                dest = target_dir / "LEIA-ME.md"
            else:
                dest = docs_dir / src.name

            shutil.copy2(src, dest)
            logger.info("  Copiado: %s", src.name)


def create_readme_usuario(
    target_dir: Path,
    build_system: str,
    version: str,
    primary_executable_name: str,
    include_sample_db: bool,
    included_local_db_name: Optional[str] = None,
):
    """Cria README especifico para usuario final."""
    if include_sample_db:
        sample_db_block = f"""
6. BANCO DE EXEMPLO
   - Esta entrega inclui um banco de exemplo separado em: {PACKAGE_SAMPLE_DB_DIR}/{SAMPLE_DB_ASSET_NAME}
   - O banco de exemplo nao substitui o banco operacional em: data/ssas.db
   - Consulte {PACKAGE_SAMPLE_DB_DIR}/{SAMPLE_DB_ASSET_README_NAME} antes de usar
"""
    else:
        sample_db_block = """
6. BANCO DE EXEMPLO
   - Esta entrega nao inclui banco de exemplo
   - Para incluir o banco de exemplo aprovado do repositorio, gere o pacote com:
     uv run --python 3.13 scripts/create_distribution.py --build-system pyinstaller --include-sample-db
"""

    if included_local_db_name:
        local_db_block = f"""
7. BANCO LOCAL ESCOLHIDO EXPLICITAMENTE
   - Esta entrega inclui um banco local separado em: {PACKAGE_LOCAL_DB_DIR}/{included_local_db_name}
   - Esse arquivo foi escolhido explicitamente no empacotamento
   - Ele nao substitui automaticamente o banco operacional em: data/ssas.db
"""
    else:
        local_db_block = """
7. BANCO LOCAL ESCOLHIDO EXPLICITAMENTE
   - Esta entrega nao inclui banco local escolhido explicitamente
   - Para incluir um banco local especifico, gere o pacote com:
     uv run --python 3.13 scripts/create_distribution.py --build-system pyinstaller --include-local-db data/ssas.db
"""

    readme_content = f"""SSA Consulta Rapida v{version}
Build: {BUILD_SYSTEMS[build_system]["name"]}

INSTALACAO E USO

1. PRIMEIRA EXECUCAO
   - Extraia o ZIP e abra a pasta principal do pacote
   - Clique duas vezes no executavel principal dentro da pasta extraida
   - Exemplo nesta entrega: {primary_executable_name}
   - A estrutura basica de diretorios ja vem no pacote

2. IMPORTAR DADOS
   - Na GUI, use Importacao externa ou Abrir pasta de entrada
   - Em app instalado, a pasta tecnica de runtime e: {APP_RUNTIME_DIR}
   - A pasta real de entrada fica no perfil do usuario:
     Windows: %APPDATA%\\{APP_RUNTIME_DIR}\\docs_entrada
     macOS: ~/Library/Application Support/{APP_RUNTIME_DIR}/docs_entrada
     Linux: ${{XDG_DATA_HOME:-~/.local/share}}/{APP_RUNTIME_DIR}/docs_entrada
   - Nao use a pasta de instalacao como area de trabalho

3. BANCOS DE DADOS
   - Banco principal no app instalado:
     Windows: %APPDATA%\\{APP_RUNTIME_DIR}\\data\\ssas.db
     macOS: ~/Library/Application Support/{APP_RUNTIME_DIR}/data/ssas.db
     Linux: ${{XDG_DATA_HOME:-~/.local/share}}/{APP_RUNTIME_DIR}/data/ssas.db
   - Backups automaticos ficam em data/historico_backups dentro da pasta de runtime

4. EXPORTACOES
   - Arquivos CSV/Excel exportados vao para docs_saida dentro da pasta de runtime

5. LOGS
   - Logs de execucao ficam em logs/ssa.log dentro da pasta de runtime
{sample_db_block}
{local_db_block}

MODOS DE USO

1. Interface Grafica (GUI):
   {primary_executable_name} --gui

2. Interface CLI (Linha de Comando):
   {primary_executable_name}

3. Dashboard Web (Streamlit):
   {primary_executable_name} --streamlit

CONFIGURACAO DE ANTIVIRUS

Caso o antivirus bloqueie o executavel, adicione excecao para:
- Pasta completa do programa
- Consulte: docs/ANTIVIRUS_EXCLUSOES.md para instrucoes detalhadas

SUPORTE

- Documentacao completa: docs/
- Versao: {version}
- Build System: {BUILD_SYSTEMS[build_system]["name"]}

ATUALIZACAO

Para atualizar o pacote instalado, substitua apenas os executaveis do pacote.
Em app instalado, dados e configuracoes de runtime ficam no perfil do usuario
na pasta tecnica {APP_RUNTIME_DIR}; nao precisam ser copiados da pasta de
instalacao.
Preserve manualmente apenas arquivos que voce colocou dentro da pasta extraida.
"""

    readme_path = target_dir / "LEIA-ME-USUARIO.txt"
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(readme_content)

    logger.info("README para usuario criado")


def _copy_runtime_bundle(
    build_system: str,
    build_info: dict[str, object],
    build_dir: Path,
    package_dir: Path,
) -> bool:
    """Copia executavel/dependencias e config para o pacote staged."""
    logger.info("  Copiando executavel e dependencias...")

    is_canonical_pyinstaller = (
        build_system == "pyinstaller" and _is_canonical_pyinstaller_directory(build_dir)
    )
    if build_system == "nuitka" or is_canonical_pyinstaller:
        _copy_build_tree_sanitized(build_dir, package_dir)
    else:
        exe_path_value = build_info.get("exe_path")
        if not isinstance(exe_path_value, str):
            logger.error(
                "Configuracao invalida: exe_path ausente para %s", build_system
            )
            return False
        exe_src = PROJECT_ROOT / exe_path_value
        if not exe_src.is_file():
            logger.error("Executavel nao encontrado para empacotamento: %s", exe_src)
            return False
        shutil.copy2(exe_src, package_dir / exe_src.name)

        internal_dir_name = build_info.get("internal_dir")
        if isinstance(internal_dir_name, str) and internal_dir_name:
            internal_src = build_dir / internal_dir_name
            if internal_src.exists():
                shutil.copytree(
                    internal_src,
                    package_dir / internal_dir_name,
                    dirs_exist_ok=True,
                    ignore=lambda src, names: _build_bundle_ignore(
                        internal_src, src, names
                    ),
                )

    config_src = build_dir / "config"
    if config_src.exists():
        shutil.copytree(
            config_src,
            package_dir / "config",
            dirs_exist_ok=True,
            ignore=lambda src, names: _build_bundle_ignore(
                config_src.parent, src, names
            ),
        )
    else:
        config_src = PROJECT_ROOT / "config"
        if config_src.exists():
            shutil.copytree(
                config_src,
                package_dir / "config",
                dirs_exist_ok=True,
                ignore=lambda src, names: _build_bundle_ignore(
                    config_src.parent, src, names
                ),
            )

    return True


def _write_package_version_file(
    package_dir: Path, version: str, build_name: str
) -> None:
    """Escreve VERSION.txt no pacote staged."""
    with open(package_dir / "VERSION.txt", "w") as f:
        f.write(f"{version}\n")
        f.write(f"Build System: {build_name}\n")
        f.write(f"Data: {format_current_timestamp()}\n")


def _create_package_zip(package_dir: Path, package_name: str, zip_path: Path) -> None:
    """Gera arquivo ZIP final a partir do pacote staged."""
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(package_dir):
            for file in files:
                file_path = Path(root) / file
                arcname = Path(package_name) / file_path.relative_to(package_dir)
                zipf.write(file_path, arcname)


def _prepare_package_staging(
    build_system: str,
    build_info: dict[str, object],
    build_dir: Path,
    package_dir: Path,
    version: str,
    build_name: str,
    include_sample_db: bool = False,
    include_local_db: Optional[str] = None,
) -> bool:
    """Prepara estrutura staged do pacote antes da compactacao."""
    if not _copy_runtime_bundle(build_system, build_info, build_dir, package_dir):
        return False

    create_user_structure(package_dir)
    copy_documentation(package_dir)
    if include_sample_db and not _copy_sample_db_assets(package_dir):
        return False
    included_local_db_name = None
    if include_local_db:
        if not _copy_local_db_asset(package_dir, include_local_db):
            return False
        resolved_local_db = _resolve_local_db_asset(include_local_db)
        if resolved_local_db is None:
            return False
        included_local_db_name = resolved_local_db.name

    primary_executable_name = _detect_primary_executable_name(package_dir)
    if primary_executable_name is None:
        logger.error("Nao foi possivel detectar executavel primario no pacote staged")
        return False

    create_readme_usuario(
        package_dir,
        build_system,
        version,
        primary_executable_name,
        include_sample_db,
        included_local_db_name,
    )
    _write_package_version_file(package_dir, version, build_name)
    return True


def create_zip_package(
    build_system: str,
    version: str,
    include_sample_db: bool = False,
    include_local_db: Optional[str] = None,
) -> Optional[Path]:
    """Cria pacote ZIP portatil."""
    build_info: dict[str, object] = dict(BUILD_SYSTEMS[build_system])
    build_name_value = build_info.get("name")
    build_name = build_name_value if isinstance(build_name_value, str) else build_system
    logger.info("Criando pacote ZIP para %s", build_name)

    build_dir = _resolve_build_directory(build_system)
    if build_dir is None:
        logger.error(
            "Falha na resolucao de build para %s: %s",
            build_system,
            _resolve_build_directory_failure_reason(build_system),
        )
        return None

    package_output_dir = _package_output_dir(build_dir)
    if package_output_dir is None:
        return None
    package_output_dir.mkdir(parents=True, exist_ok=True)

    # Criar diretorio temporario para montagem
    timestamp = format_current_timestamp("%Y%m%d_%H%M%S")
    temp_dir = package_output_dir / f"temp_{build_system}_{timestamp}"
    temp_dir.mkdir(parents=True, exist_ok=True)

    package_name = f"SSA_Consulta_Rapida_v{version}_{build_system}"
    package_dir = temp_dir / package_name
    package_dir.mkdir(exist_ok=True)

    try:
        if not _prepare_package_staging(
            build_system,
            build_info,
            build_dir,
            package_dir,
            version,
            build_name,
            include_sample_db,
            include_local_db,
        ):
            if temp_dir.exists():
                try:
                    shutil.rmtree(temp_dir)
                except OSError as exc:
                    logger.error(
                        "Falha ao remover diretorio temporario do pacote: %s: %s",
                        temp_dir,
                        exc,
                    )
                    raise
            return None

        # Criar ZIP
        zip_name = f"{package_name}.zip"
        zip_path = package_output_dir / zip_name

        logger.info("  Criando arquivo ZIP: %s", zip_name)

        _create_package_zip(package_dir, package_name, zip_path)

        # Limpar diretorio temporario
        try:
            shutil.rmtree(temp_dir)
        except OSError as exc:
            logger.error(
                "Falha ao remover diretorio temporario do pacote: %s: %s",
                temp_dir,
                exc,
            )
            raise

        file_size = zip_path.stat().st_size / (1024 * 1024)  # MB
        logger.info("  ZIP criado: %s (%.1f MB)", zip_path.name, file_size)

        return zip_path

    except Exception as e:
        logger.error("Erro ao criar ZIP: %s", e)
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        return None


def _normalize_windows_path(raw_value: str) -> str:
    """Normaliza path para formato Windows e remove aspas."""
    return raw_value.replace("/", "\\").replace('"', "")


def _build_inno_excludes_str() -> str:
    """Monta lista de excludes usada pelo template Inno."""
    inno_excludes = ["*.log", "*.tmp", "__pycache__"]
    inno_excludes.extend(
        [
            "*.bak",
            "*.bak*",
            "*.backup",
            "*.backup*",
            "*.backup_*",
            "config\\__init__.py",
            "*\\config\\__init__.py",
        ]
    )
    for item in sorted(EXCLUDED_BUNDLE_ITEMS):
        inno_excludes.append(f"{item}\\*")
    return ",".join(inno_excludes)


def _build_inno_sample_db_blocks(
    sample_db_source_spec: Optional[str],
    sample_db_readme_source_spec: Optional[str],
) -> tuple[str, str]:
    """Renderiza blocos opcionais do banco de exemplo para o instalador."""
    if not sample_db_source_spec or not sample_db_readme_source_spec:
        return "", ""

    dirs_block = f'Name: "{INSTALLER_SAMPLE_DB_DIR_SPEC}"'
    files_block = "\n".join(
        [
            (
                f'Source: "{sample_db_source_spec}"; '
                f'DestDir: "{INSTALLER_SAMPLE_DB_DIR_SPEC}"; '
                f'DestName: "{SAMPLE_DB_ASSET_NAME}"; Flags: ignoreversion'
            ),
            (
                f'Source: "{sample_db_readme_source_spec}"; '
                f'DestDir: "{INSTALLER_SAMPLE_DB_DIR_SPEC}"; '
                f'DestName: "{SAMPLE_DB_ASSET_README_NAME}"; Flags: ignoreversion'
            ),
        ]
    )
    return dirs_block, files_block


def _build_inno_local_db_blocks(
    local_db_source_spec: Optional[str],
    local_db_name: Optional[str],
) -> tuple[str, str]:
    """Renderiza blocos opcionais do banco local explicitamente escolhido."""
    if not local_db_source_spec or not local_db_name:
        return "", ""

    dirs_block = f'Name: "{INSTALLER_LOCAL_DB_DIR_SPEC}"'
    files_block = (
        f'Source: "{local_db_source_spec}"; '
        f'DestDir: "{INSTALLER_LOCAL_DB_DIR_SPEC}"; '
        f'DestName: "{local_db_name}"; Flags: ignoreversion'
    )
    return dirs_block, files_block


def _build_inno_iss_content(
    build_system: str,
    version: str,
    exe_name: str,
    source_dir_spec: str,
    dist_output_spec: str,
    inno_excludes_str: str,
    setup_icon_spec: Optional[str],
    sample_db_dirs_block: str,
    sample_db_files_block: str,
    local_db_dirs_block: str,
    local_db_files_block: str,
) -> str:
    """Renderiza conteudo do arquivo ISS."""
    setup_icon_line = f"SetupIconFile={setup_icon_spec}" if setup_icon_spec else ""
    sample_db_dirs_section = f"{sample_db_dirs_block}\n" if sample_db_dirs_block else ""
    sample_db_files_section = (
        f"{sample_db_files_block}\n" if sample_db_files_block else ""
    )
    local_db_dirs_section = f"{local_db_dirs_block}\n" if local_db_dirs_block else ""
    local_db_files_section = f"{local_db_files_block}\n" if local_db_files_block else ""
    return f"""
; Script Inno Setup para SSA Consulta Rapida
; Build System: {BUILD_SYSTEMS[build_system]["name"]}
; Versao: {version}

#define MyAppName "SSA Consulta Rapida"
#define MyAppVersion "{version}"
#define MyAppPublisher "ITAIPU Binacional"
#define MyAppExeName "{exe_name}"
#define BuildSystem "{build_system}"
#define SourcePath "{dist_output_spec}"
#define SourceDir "{source_dir_spec}"
#define SourcePathMode "absolute"

[Setup]
AppId={{{{3D8A9B2C-5E1F-4A7B-9C3D-1E2F3A4B5C6D}}}}
AppName={{#MyAppName}}
AppVersion={{#MyAppVersion}}
AppPublisher={{#MyAppPublisher}}
DefaultDirName={{autopf}}\\{{#MyAppName}}
DefaultGroupName={{#MyAppName}}
AllowNoIcons=yes
OutputBaseFilename=SSA_Consulta_Rapida_v{version}_{build_system}_Setup
{setup_icon_line}
OutputDir={{#SourcePath}}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "{{cm:CreateDesktopIcon}}"; GroupDescription: "{{cm:AdditionalIcons}}"

[Files]
Source: "{{#SourceDir}}\\{exe_name}"; DestDir: "{{app}}"; Flags: ignoreversion
Source: "{{#SourceDir}}\\*"; DestDir: "{{app}}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "{inno_excludes_str}"
{sample_db_files_section}
{local_db_files_section}

[Dirs]
Name: "{{app}}\\data"
Name: "{{app}}\\data\\historico_backups"
Name: "{{app}}\\docs_entrada"
Name: "{{app}}\\docs_saida"
Name: "{{app}}\\logs"
Name: "{{app}}\\reports"
Name: "{{app}}\\exportacao"
{sample_db_dirs_section}
{local_db_dirs_section}

[Icons]
Name: "{{group}}\\{{#MyAppName}}"; Filename: "{{app}}\\{{#MyAppExeName}}"
Name: "{{group}}\\{{#MyAppName}} (GUI)"; Filename: "{{app}}\\{{#MyAppExeName}}"; Parameters: "--gui"
Name: "{{autodesktop}}\\{{#MyAppName}}"; Filename: "{{app}}\\{{#MyAppExeName}}"; Parameters: "--gui"; Tasks: desktopicon

[Run]
Filename: "{{app}}\\{{#MyAppExeName}}"; Parameters: "--gui"; Description: "{{cm:LaunchProgram,{{#StringChange(MyAppName, '&', '&&')}}}}"; Flags: nowait postinstall skipifsilent

[Code]
function InitializeSetup(): Boolean;
begin
  Result := True;
end;
"""


def _resolve_inno_setup_icon() -> Optional[str]:
    """Resolve icone do instalador Inno Setup."""
    icon_candidates = [
        PROJECT_ROOT / "resources" / "app_icon.ico",
        PROJECT_ROOT / "launchers" / "assets" / "icon.ico",
    ]
    for icon_path in icon_candidates:
        if icon_path.is_file():
            return _normalize_windows_path(str(icon_path.resolve()))
    return None


def create_inno_setup_script(
    build_system: str,
    version: str,
    include_sample_db: bool = False,
    include_local_db: Optional[str] = None,
) -> Optional[Path]:
    """Cria script Inno Setup para instalador Windows."""
    logger.info("Criando script Inno Setup para %s", BUILD_SYSTEMS[build_system]["name"])
    resolved = _resolve_inno_source(build_system)
    if resolved is None:
        logger.error(
            "Nao foi possivel resolver origem para instalador: %s", build_system
        )
        return None

    source_dir, exe_name = resolved
    source_dir_spec = _normalize_windows_path(str(source_dir.resolve()))
    dist_output_spec = _normalize_windows_path(str(DIST_OUTPUT.resolve()))
    exe_name = exe_name.replace('"', "")
    inno_excludes_str = _build_inno_excludes_str()
    setup_icon_spec = _resolve_inno_setup_icon()
    if setup_icon_spec is None:
        logger.warning(
            "Icone Inno Setup nao encontrado; instalador sera gerado sem SetupIconFile"
        )
    sample_db_source_spec = None
    sample_db_readme_source_spec = None
    if include_sample_db:
        resolved_assets = _resolve_sample_db_assets()
        if resolved_assets is None:
            return None
        sample_db_path, sample_db_readme_path = resolved_assets
        sample_db_source_spec = _normalize_windows_path(str(sample_db_path.resolve()))
        sample_db_readme_source_spec = _normalize_windows_path(
            str(sample_db_readme_path.resolve())
        )
    local_db_source_spec = None
    local_db_name = None
    if include_local_db:
        resolved_local_db = _resolve_local_db_asset(include_local_db)
        if resolved_local_db is None:
            return None
        local_db_source_spec = _normalize_windows_path(str(resolved_local_db.resolve()))
        local_db_name = resolved_local_db.name
    sample_db_dirs_block, sample_db_files_block = _build_inno_sample_db_blocks(
        sample_db_source_spec,
        sample_db_readme_source_spec,
    )
    local_db_dirs_block, local_db_files_block = _build_inno_local_db_blocks(
        local_db_source_spec,
        local_db_name,
    )
    iss_content = _build_inno_iss_content(
        build_system,
        version,
        exe_name,
        source_dir_spec,
        dist_output_spec,
        inno_excludes_str,
        setup_icon_spec,
        sample_db_dirs_block,
        sample_db_files_block,
        local_db_dirs_block,
        local_db_files_block,
    )

    iss_path = DIST_OUTPUT / f"installer_{build_system}.iss"
    with open(iss_path, "w", encoding="utf-8") as f:
        f.write(iss_content)

    logger.info("  Script ISS criado: %s", iss_path.name)
    return iss_path


def _get_iscc_path() -> Optional[str]:
    """Resolve caminho do compilador Inno Setup (ISCC)."""
    possible_paths: list[str] = []
    trusted_inno_parents = [
        Path(r"C:\Program Files (x86)\Inno Setup 6"),
        Path(r"C:\Program Files\Inno Setup 6"),
        Path(r"C:\Program Files (x86)\Inno Setup 5"),
        Path(r"C:\Program Files\Inno Setup 5"),
    ]

    iscc_in_path = shutil.which("iscc") or shutil.which("ISCC")
    if iscc_in_path:
        try:
            trusted_inno_parents.append(Path(iscc_in_path).resolve().parent)
        except Exception:
            trusted_inno_parents.append(Path(iscc_in_path).parent)
        possible_paths.append(iscc_in_path)

    configured_path = os.environ.get("INNO_SETUP_COMPILER")
    if configured_path:
        configured_candidate = Path(configured_path).expanduser()
        allowed_names = {"iscc", "iscc.exe"}

        reason = None
        if not configured_candidate.is_absolute():
            reason = "caminho nao absoluto"
        elif configured_candidate.name.lower() not in allowed_names:
            reason = "nome de executavel nao permitido"
        elif not configured_candidate.is_file():
            reason = "arquivo inexistente"
        else:
            try:
                resolved_candidate = configured_candidate.resolve()
            except Exception:
                resolved_candidate = configured_candidate

            candidate_parent = resolved_candidate.parent
            trusted_parent_match = any(
                candidate_parent == trusted_parent
                or trusted_parent in candidate_parent.parents
                for trusted_parent in trusted_inno_parents
            )
            if trusted_parent_match:
                possible_paths.insert(0, str(resolved_candidate))
            else:
                reason = "diretorio fora da allowlist confiavel"

        if reason is not None:
            logger.warning(
                "INNO_SETUP_COMPILER ignorado por validacao de seguranca (%s): %s",
                reason,
                configured_path,
            )

    possible_paths.extend(
        [
            r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
            r"C:\Program Files\Inno Setup 6\ISCC.exe",
            r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe",
            r"C:\Program Files\Inno Setup 5\ISCC.exe",
        ]
    )

    for path in possible_paths:
        if os.path.exists(path):
            return path
    return None


def _run_iscc_compile(iscc_path: str, iss_path: Path) -> str:
    """Executa compilacao do instalador com ISCC."""
    try:
        result = subprocess.run(
            [iscc_path, str(iss_path)], capture_output=True, text=True, timeout=300
        )

        if result.returncode == 0:
            logger.info("  Instalador compilado com sucesso!")
            return "success"
        else:
            logger.error("Erro ao compilar instalador: %s", result.stderr)
            return "failed"

    except subprocess.TimeoutExpired:
        logger.error("Timeout ao compilar instalador")
        return "failed"
    except Exception as e:
        logger.error("Erro ao executar Inno Setup: %s", e)
        return "failed"


def compile_installer(iss_path: Path) -> str:
    """Compila instalador usando Inno Setup."""
    logger.info("Compilando instalador com Inno Setup...")

    iscc_path = _get_iscc_path()
    if not iscc_path:
        logger.warning("Inno Setup nao encontrado. Instalador nao sera criado.")
        logger.info(
            "  Para criar instaladores, instale Inno Setup de: https://jrsoftware.org/isdl.php"
        )
        return "missing"

    return _run_iscc_compile(iscc_path, iss_path)


def _parse_distribution_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Criar pacotes de distribuicao do SSA Consulta Rapida"
    )
    parser.add_argument(
        "--build-system",
        choices=list(BUILD_SYSTEMS.keys()),
        help="Build system especifico para empacotar",
    )
    parser.add_argument(
        "--all", action="store_true", help="Criar pacotes para todos os build systems"
    )
    parser.add_argument(
        "--skip-installer",
        action="store_true",
        help="Pular criacao do instalador (criar apenas ZIP)",
    )
    parser.add_argument(
        "--installer-only",
        action="store_true",
        help="Criar apenas instalador (pular ZIP)",
    )
    parser.add_argument(
        "--include-sample-db",
        action="store_true",
        help=(
            "Incluir o banco de exemplo fixo do repositorio em BancoExemplo/ "
            "sem liberar bancos locais acidentais"
        ),
    )
    parser.add_argument(
        "--include-local-db",
        help=(
            "Incluir exatamente um banco local escolhido por caminho em BancoLocal/ "
            "sem liberar outros bancos locais acidentais"
        ),
    )

    args = parser.parse_args()
    if not args.build_system and not args.all:
        parser.error("Especifique --build-system ou --all")
    return args


def _selected_build_systems(args: argparse.Namespace) -> list[str]:
    if args.all:
        return list(BUILD_SYSTEMS.keys())
    return [args.build_system]


def _create_distribution_outputs(
    build_systems: list[str], version: str, args: argparse.Namespace
) -> dict[str, dict[str, Optional[Path] | str]]:
    results: dict[str, dict[str, Optional[Path] | str]] = {}
    for bs in build_systems:
        logger.info("\n%s", "=" * 60)
        logger.info("Processando: %s", BUILD_SYSTEMS[bs]["name"])
        logger.info("%s\n", "=" * 60)

        results[bs] = {"zip": None, "installer": None}
        if not args.installer_only:
            zip_path = create_zip_package(
                bs,
                version,
                include_sample_db=args.include_sample_db,
                include_local_db=args.include_local_db,
            )
            results[bs]["zip"] = zip_path

        if not args.skip_installer:
            iss_path = create_inno_setup_script(
                bs,
                version,
                include_sample_db=args.include_sample_db,
                include_local_db=args.include_local_db,
            )
            if iss_path:
                results[bs]["installer"] = compile_installer(iss_path)
            else:
                results[bs]["installer"] = "script_failed"
    return results


def _update_installer_exit_code(installer_status, args: argparse.Namespace) -> int:
    if installer_status == "success":
        logger.info("  Instalador: Criado com sucesso")
        return 0
    if installer_status == "missing":
        logger.info("  Instalador: Nao criado (Inno Setup nao disponivel)")
        return int(args.installer_only)
    if installer_status == "failed":
        logger.info("  Instalador: Falha na compilacao")
        return 1
    if installer_status == "script_failed":
        logger.info("  Instalador: Falha na geracao do script")
        return 1
    return 0


def _log_distribution_report(
    results: dict[str, dict[str, Optional[Path] | str]], args: argparse.Namespace
) -> int:
    logger.info("\n%s", "=" * 60)
    logger.info("RELATORIO FINAL")
    logger.info("%s\n", "=" * 60)

    exit_code = 0
    zip_output_dirs: set[Path] = set()
    for bs, result in results.items():
        logger.info("%s:", BUILD_SYSTEMS[bs]["name"])
        if result["zip"]:
            zip_path = result["zip"]
            if not isinstance(zip_path, Path):
                raise TypeError(f"Resultado de ZIP invalido para {bs}: {zip_path!r}")
            logger.info("  ZIP: %s", zip_path.name)
            zip_output_dirs.add(zip_path.parent)
        elif not args.installer_only:
            logger.info("  ZIP: Nao criado")
            exit_code = 1
        exit_code = max(exit_code, _update_installer_exit_code(result["installer"], args))
        logger.info("")

    if zip_output_dirs:
        for output_dir in sorted(zip_output_dirs):
            logger.info("ZIPs salvos em: %s", output_dir)
    if not args.skip_installer:
        logger.info("Instaladores/scripts em: %s", DIST_OUTPUT)
    if exit_code:
        logger.error("Distribuicao falhou: artefato esperado nao foi criado.")
    return exit_code


def main() -> int:
    """Create requested distribution artifacts and return a process exit code."""
    args = _parse_distribution_args()
    if not args.skip_installer:
        DIST_OUTPUT.mkdir(exist_ok=True)

    version = get_version()
    logger.info("Versao: %s", version)
    results = _create_distribution_outputs(_selected_build_systems(args), version, args)
    return _log_distribution_report(results, args)


if __name__ == "__main__":
    raise SystemExit(main())
