"""
Script para criar pacotes de distribuicao do SSA Consulta Rapida.

Cria:
1. Arquivo ZIP portatil com executavel e estrutura completa
2. Instalador Windows usando Inno Setup (se disponivel)

Uso:
    python scripts/create_distribution.py --build-system pyinstaller
    python scripts/create_distribution.py --build-system pyoxidizer --skip-installer
    python scripts/create_distribution.py --all
"""

import argparse
import json
import logging
import os
import shutil
import subprocess
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional

# Configuracao de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuracoes
PROJECT_ROOT = Path(__file__).parent.parent
VERSION_FILE = PROJECT_ROOT / "VERSION"
DIST_OUTPUT = PROJECT_ROOT / "dist_packages"
PYINSTALLER_CANONICAL_DIRS = (
    "launchers/dist/windows_amd64",
    "launchers/dist/macos_arm64",
    "launchers/dist/debian_amd64",
)
EXCLUDED_BUNDLE_ITEMS = {
    "data",
    "docs_entrada",
    "docs_saida",
    "logs",
    "reports",
    "exportacao",
    "historico_backups",
}

SENSITIVE_LOCAL_EXTENSIONS = {".db", ".xlsx", ".xls"}

# Informacoes dos build systems
BUILD_SYSTEMS = {
    "pyinstaller": {
        "name": "PyInstaller",
        "exe_path": "builds/pyinstaller/SSA_Consulta_Rapida.exe",
        "base_dir": "builds/pyinstaller",
        "internal_dir": "_internal",
    },
    "pyoxidizer": {
        "name": "PyOxidizer",
        "exe_path": "builds/pyoxidizer/SSA_Consulta_Rapida.exe",
        "base_dir": "builds/pyoxidizer",
        "internal_dir": "lib",
    },
    "nuitka": {
        "name": "Nuitka",
        "exe_path": "builds/nuitka/main.exe",
        "base_dir": "builds/nuitka",
        "internal_dir": None,
    }
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
        for item in build_dir.iterdir():
            if item.is_file():
                if item.suffix.lower() == ".exe":
                    return True
                if item.suffix == "" and os.access(item, os.X_OK):
                    return True
            elif item.is_dir():
                if item.suffix.lower() == ".app":
                    contents_candidate = item / "Contents" / "MacOS"
                    if contents_candidate.is_dir():
                        for child in contents_candidate.iterdir():
                            if child.is_file() and os.access(child, os.X_OK):
                                return True
                embedded = item / item.name
                if embedded.is_file() and os.access(embedded, os.X_OK):
                    return True
        return False

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


def _resolve_build_directory(build_system: str) -> Optional[Path]:
    """Resolve diretorio de build com prioridade para caminho canonico."""
    if build_system == "pyinstaller":
        candidates = [PROJECT_ROOT / rel for rel in _get_pyinstaller_canonical_dirs()]
        for path in candidates:
            if _has_packagable_content(path) and _has_primary_executable(path, "pyinstaller"):
                return path

    build_info = BUILD_SYSTEMS[build_system]
    base_dir_value = build_info.get("base_dir")
    if not isinstance(base_dir_value, str):
        return None

    legacy_dir = PROJECT_ROOT / base_dir_value
    if _has_packagable_content(legacy_dir):
        if not _has_primary_executable(legacy_dir, build_system):
            return None
        return legacy_dir
    return None


def _copy_build_tree_sanitized(source_dir: Path, target_dir: Path) -> None:
    """Copia build para distribuicao, removendo dados locais sensiveis."""
    for item in source_dir.iterdir():
        if _should_skip_bundle_entry(item.name, item.is_file()):
            continue
        destination = target_dir / item.name
        if item.is_file():
            shutil.copy2(item, destination)
        elif item.is_dir():
            shutil.copytree(
                item,
                destination,
                dirs_exist_ok=True,
                ignore=_build_bundle_ignore,
            )


def _should_skip_bundle_entry(name: str, is_file: bool) -> bool:
    if name in {".git", "__pycache__", "logs"}:
        return True
    if name in EXCLUDED_BUNDLE_ITEMS:
        return True
    if is_file and Path(name).suffix.lower() in SENSITIVE_LOCAL_EXTENSIONS:
        return True
    return False


def _build_bundle_ignore(_src: str, names: list[str]) -> set[str]:
    ignored: set[str] = set()
    src_path = Path(_src)
    for name in names:
        candidate = src_path / name
        if _should_skip_bundle_entry(name, candidate.is_file()):
            ignored.add(name)
    return ignored


def _detect_primary_executable_name(package_dir: Path) -> Optional[str]:
    """Escolhe executavel principal para instrucoes do usuario."""
    preferred = (
        "SSA_Consulta_Rapida.exe",
        "SSA_GUI.exe",
        "main.exe",
    )
    existing = [p.name for p in package_dir.iterdir() if p.is_file()]
    for name in preferred:
        if name in existing:
            return name

    gui_like = sorted(name for name in existing if "GUI" in name.upper())
    if gui_like:
        return gui_like[0]

    exe_like = sorted(name for name in existing if name.lower().endswith(".exe"))
    if exe_like:
        return exe_like[0]

    app_like = sorted(name for name in existing if name.lower().endswith(".app"))
    if app_like:
        return app_like[0]

    return None


def _resolve_inno_source(build_system: str) -> Optional[tuple[Path, str]]:
    """Resolve diretorio/arquivo principal usado no script Inno Setup."""
    build_info = BUILD_SYSTEMS[build_system]

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
            gui_candidates = sorted(canonical_windows.glob("*GUI*.exe"))
            if gui_candidates:
                return canonical_windows, gui_candidates[0].name
            exe_candidates = sorted(canonical_windows.glob("*.exe"))
            if exe_candidates:
                return canonical_windows, exe_candidates[0].name

    base_dir_value = build_info.get("base_dir")
    if not isinstance(base_dir_value, str):
        return None
    source_dir = PROJECT_ROOT / base_dir_value
    if not source_dir.exists():
        return None

    if build_system == "nuitka":
        exe_path_value = build_info.get("exe_path")
        if isinstance(exe_path_value, str):
            return source_dir, Path(exe_path_value).name
        return source_dir, "main.exe"
    return source_dir, "SSA_Consulta_Rapida.exe"


def _is_canonical_pyinstaller_directory(build_dir: Path) -> bool:
    """Retorna True quando o build_dir aponta para launchers/dist canonico."""
    canonical = {PROJECT_ROOT / rel for rel in _get_pyinstaller_canonical_dirs()}
    return build_dir in canonical


def get_version() -> str:
    """Le o numero de versao do arquivo VERSION ou retorna default."""
    try:
        with open(VERSION_FILE, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception:
        try:
            with open(PROJECT_ROOT / "config" / "version.json", 'r', encoding='utf-8') as f:
                data = json.load(f)
                return str(data.get('version_short') or data.get('version') or '0.0.0')
        except Exception:
            return "0.0.0"


def create_user_structure(target_dir: Path):
    """Cria estrutura de diretorios para usuario final."""
    logger.info(f"Criando estrutura de diretorios em {target_dir}")

    for dir_name in USER_DIRS:
        dir_path = target_dir / dir_name
        dir_path.mkdir(parents=True, exist_ok=True)

        # Criar arquivo .gitkeep para manter diretorios no ZIP
        gitkeep = dir_path / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.touch()

    logger.info(f"Criados {len(USER_DIRS)} diretorios")


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
            logger.info(f"  Copiado: {src.name}")


def create_readme_usuario(
    target_dir: Path,
    build_system: str,
    version: str,
    primary_executable_name: str,
):
    """Cria README especifico para usuario final."""
    readme_content = f"""SSA Consulta Rapida v{version}
Build: {BUILD_SYSTEMS[build_system]['name']}

INSTALACAO E USO

1. PRIMEIRA EXECUCAO
   - Extraia o ZIP e abra a pasta principal do pacote
   - Clique duas vezes no executavel principal dentro da pasta extraida
   - Exemplo nesta entrega: {primary_executable_name}
   - O programa criara automaticamente os diretorios necessarios

2. IMPORTAR DADOS
   - Coloque arquivos Excel na pasta: docs_entrada/
   - Execute o programa
   - Os dados serao importados automaticamente

3. BANCOS DE DADOS
   - Arquivo principal: data/ssas.db
   - Backups automaticos em: data/historico_backups/

4. EXPORTACOES
   - Arquivos CSV/Excel exportados vao para: docs_saida/

5. LOGS
   - Logs de execucao em: logs/ssa.log

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
- Build System: {BUILD_SYSTEMS[build_system]['name']}

ATUALIZACAO

Para atualizar, substitua apenas o executavel principal mantendo:
- Pasta data/ (seus bancos de dados)
- Pasta config/ (suas configuracoes personalizadas)
- Pastas docs_entrada/ e docs_saida/ (seus arquivos)
"""

    readme_path = target_dir / "LEIA-ME-USUARIO.txt"
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(readme_content)

    logger.info("README para usuario criado")


def create_zip_package(build_system: str, version: str) -> Optional[Path]:
    """Cria pacote ZIP portatil."""
    logger.info(f"Criando pacote ZIP para {BUILD_SYSTEMS[build_system]['name']}")

    build_info = BUILD_SYSTEMS[build_system]
    build_dir = _resolve_build_directory(build_system)
    if build_dir is None:
        logger.error("Diretorio de build ou executavel principal nao encontrado para %s", build_system)
        return None

    # Criar diretorio temporario para montagem
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    temp_dir = DIST_OUTPUT / f"temp_{build_system}_{timestamp}"
    temp_dir.mkdir(parents=True, exist_ok=True)

    package_name = f"SSA_Consulta_Rapida_v{version}_{build_system}"
    package_dir = temp_dir / package_name
    package_dir.mkdir(exist_ok=True)

    try:
        # Copiar executavel e dependencias
        logger.info("  Copiando executavel e dependencias...")

        is_canonical_pyinstaller = (
            build_system == "pyinstaller" and _is_canonical_pyinstaller_directory(build_dir)
        )
        if build_system == "nuitka" or is_canonical_pyinstaller:
            _copy_build_tree_sanitized(build_dir, package_dir)
        else:
            # PyInstaller/PyOxidizer: copiar executavel
            exe_path_value = build_info.get("exe_path")
            if not isinstance(exe_path_value, str):
                logger.error("Configuracao invalida: exe_path ausente para %s", build_system)
                if temp_dir.exists():
                    shutil.rmtree(temp_dir)
                return None
            exe_src = PROJECT_ROOT / exe_path_value
            if not exe_src.is_file():
                logger.error("Executavel nao encontrado para empacotamento: %s", exe_src)
                if temp_dir.exists():
                    shutil.rmtree(temp_dir)
                return None
            exe_dest = package_dir / exe_src.name
            shutil.copy2(exe_src, exe_dest)

            # Copiar pasta _internal ou lib
            internal_dir_name = build_info.get("internal_dir")
            if isinstance(internal_dir_name, str) and internal_dir_name:
                internal_src = build_dir / internal_dir_name
                if internal_src.exists():
                    shutil.copytree(
                        internal_src,
                        package_dir / internal_dir_name,
                        dirs_exist_ok=True,
                        ignore=_build_bundle_ignore,
                    )

        # Copiar config se existir
        config_src = build_dir / "config"
        if config_src.exists():
            shutil.copytree(config_src, package_dir / "config", dirs_exist_ok=True)
        else:
            # Copiar config da raiz do projeto
            config_src = PROJECT_ROOT / "config"
            if config_src.exists():
                shutil.copytree(
                    config_src,
                    package_dir / "config",
                    dirs_exist_ok=True,
                    ignore=_build_bundle_ignore,
                )

        # Criar estrutura de diretorios para usuario
        create_user_structure(package_dir)

        # Copiar documentacao
        copy_documentation(package_dir)

        # Criar README especifico
        primary_executable_name = _detect_primary_executable_name(package_dir)
        if primary_executable_name is None:
            logger.error("Nao foi possivel detectar executavel primario no pacote staged")
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
            return None
        create_readme_usuario(
            package_dir,
            build_system,
            version,
            primary_executable_name,
        )

        # Criar arquivo de versao
        with open(package_dir / "VERSION.txt", 'w') as f:
            f.write(f"{version}\n")
            f.write(f"Build System: {BUILD_SYSTEMS[build_system]['name']}\n")
            f.write(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        # Criar ZIP
        zip_name = f"{package_name}.zip"
        zip_path = DIST_OUTPUT / zip_name

        logger.info(f"  Criando arquivo ZIP: {zip_name}")

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(package_dir):
                for file in files:
                    file_path = Path(root) / file
                    arcname = Path(package_name) / file_path.relative_to(package_dir)
                    zipf.write(file_path, arcname)

        # Limpar diretorio temporario
        shutil.rmtree(temp_dir)

        file_size = zip_path.stat().st_size / (1024 * 1024)  # MB
        logger.info(f"  ZIP criado: {zip_path.name} ({file_size:.1f} MB)")

        return zip_path

    except Exception as e:
        logger.error(f"Erro ao criar ZIP: {e}")
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        return None


def create_inno_setup_script(build_system: str, version: str) -> Optional[Path]:
    """Cria script Inno Setup para instalador Windows."""
    logger.info(f"Criando script Inno Setup para {BUILD_SYSTEMS[build_system]['name']}")
    resolved = _resolve_inno_source(build_system)
    if resolved is None:
        logger.error("Nao foi possivel resolver origem para instalador: %s", build_system)
        return None

    source_dir, exe_name = resolved
    source_dir_absolute = False
    try:
        source_dir_rel = source_dir.relative_to(PROJECT_ROOT).as_posix().replace("/", "\\")
    except ValueError:
        source_dir_absolute = True
        source_dir_rel = str(source_dir).replace("/", "\\")
    source_dir_spec = source_dir_rel if source_dir_absolute else f"..\\..\\{source_dir_rel}"
    source_dir_spec = source_dir_spec.replace('"', '')
    exe_name = exe_name.replace('"', '')
    inno_excludes = ["*.log", "*.tmp", "__pycache__"]
    for item in sorted(EXCLUDED_BUNDLE_ITEMS):
        inno_excludes.append(f"{item}\\*")
    inno_excludes_str = ",".join(inno_excludes)

    iss_content = f"""
; Script Inno Setup para SSA Consulta Rapida
; Build System: {BUILD_SYSTEMS[build_system]['name']}
; Versao: {version}

#define MyAppName "SSA Consulta Rapida"
#define MyAppVersion "{version}"
#define MyAppPublisher "ITAIPU Binacional"
#define MyAppExeName "{exe_name}"
#define BuildSystem "{build_system}"

[Setup]
AppId={{{{3D8A9B2C-5E1F-4A7B-9C3D-1E2F3A4B5C6D}}}}
AppName={{#MyAppName}}
AppVersion={{#MyAppVersion}}
AppPublisher={{#MyAppPublisher}}
DefaultDirName={{autopf}}\\{{#MyAppName}}
DefaultGroupName={{#MyAppName}}
AllowNoIcons=yes
OutputDir=.
OutputBaseFilename=SSA_Consulta_Rapida_v{version}_{build_system}_Setup
SetupIconFile=..\\assets\\icon.ico
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
Source: "{source_dir_spec}\\{exe_name}"; DestDir: "{{app}}"; Flags: ignoreversion
Source: "{source_dir_spec}\\*"; DestDir: "{{app}}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "{inno_excludes_str}"

[Dirs]
Name: "{{app}}\\data"
Name: "{{app}}\\data\\historico_backups"
Name: "{{app}}\\docs_entrada"
Name: "{{app}}\\docs_saida"
Name: "{{app}}\\logs"
Name: "{{app}}\\reports"
Name: "{{app}}\\exportacao"

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

    iss_path = DIST_OUTPUT / f"installer_{build_system}.iss"
    with open(iss_path, 'w', encoding='utf-8') as f:
        f.write(iss_content)

    logger.info(f"  Script ISS criado: {iss_path.name}")
    return iss_path


def compile_installer(iss_path: Path) -> str:
    """Compila instalador usando Inno Setup."""
    logger.info("Compilando instalador com Inno Setup...")

    # Procurar ISCC.exe (compilador Inno Setup)
    configured_path = os.environ.get("INNO_SETUP_COMPILER")
    possible_paths: list[str] = []
    if configured_path:
        configured_candidate = Path(configured_path).expanduser()
        allowed_names = {"iscc", "iscc.exe"}
        if configured_candidate.is_file() and configured_candidate.name.lower() in allowed_names:
            possible_paths.append(str(configured_candidate))
        else:
            logger.warning(
                "INNO_SETUP_COMPILER ignorado por validacao de seguranca: %s",
                configured_path,
            )

    iscc_in_path = shutil.which("iscc") or shutil.which("ISCC")
    if iscc_in_path:
        possible_paths.append(iscc_in_path)

    possible_paths.extend([
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
        r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe",
        r"C:\Program Files\Inno Setup 5\ISCC.exe",
    ])

    iscc_path = None
    for path in possible_paths:
        if os.path.exists(path):
            iscc_path = path
            break

    if not iscc_path:
        logger.warning("Inno Setup nao encontrado. Instalador nao sera criado.")
        logger.info("  Para criar instaladores, instale Inno Setup de: https://jrsoftware.org/isdl.php")
        return "missing"

    try:
        result = subprocess.run(
            [iscc_path, str(iss_path)],
            capture_output=True,
            text=True,
            timeout=300
        )

        if result.returncode == 0:
            logger.info("  Instalador compilado com sucesso!")
            return "success"
        else:
            logger.error(f"Erro ao compilar instalador: {result.stderr}")
            return "failed"

    except subprocess.TimeoutExpired:
        logger.error("Timeout ao compilar instalador")
        return "failed"
    except Exception as e:
        logger.error(f"Erro ao executar Inno Setup: {e}")
        return "failed"


def main():
    parser = argparse.ArgumentParser(
        description="Criar pacotes de distribuicao do SSA Consulta Rapida"
    )
    parser.add_argument(
        "--build-system",
        choices=list(BUILD_SYSTEMS.keys()),
        help="Build system especifico para empacotar"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Criar pacotes para todos os build systems"
    )
    parser.add_argument(
        "--skip-installer",
        action="store_true",
        help="Pular criacao do instalador (criar apenas ZIP)"
    )
    parser.add_argument(
        "--installer-only",
        action="store_true",
        help="Criar apenas instalador (pular ZIP)"
    )

    args = parser.parse_args()

    # Validar argumentos
    if not args.build_system and not args.all:
        parser.error("Especifique --build-system ou --all")

    # Criar diretorio de saida
    DIST_OUTPUT.mkdir(exist_ok=True)

    # Obter versao
    version = get_version()
    logger.info(f"Versao: {version}")

    # Determinar build systems para processar
    if args.all:
        build_systems = list(BUILD_SYSTEMS.keys())
    else:
        build_systems = [args.build_system]

    # Processar cada build system
    results = {}
    for bs in build_systems:
        logger.info(f"\n{'='*60}")
        logger.info(f"Processando: {BUILD_SYSTEMS[bs]['name']}")
        logger.info(f"{'='*60}\n")

        results[bs] = {"zip": None, "installer": None}

        # Criar ZIP
        if not args.installer_only:
            zip_path = create_zip_package(bs, version)
            results[bs]["zip"] = zip_path

        # Criar instalador
        if not args.skip_installer:
            iss_path = create_inno_setup_script(bs, version)
            if iss_path:
                results[bs]["installer"] = compile_installer(iss_path)
            else:
                results[bs]["installer"] = "script_failed"

    # Relatorio final
    logger.info(f"\n{'='*60}")
    logger.info("RELATORIO FINAL")
    logger.info(f"{'='*60}\n")

    for bs, result in results.items():
        logger.info(f"{BUILD_SYSTEMS[bs]['name']}:")
        if result["zip"]:
            logger.info(f"  ZIP: {result['zip'].name}")
        elif not args.installer_only:
            logger.info("  ZIP: Nao criado")
        installer_status = result["installer"]
        if installer_status == "success":
            logger.info("  Instalador: Criado com sucesso")
        elif installer_status == "missing":
            logger.info("  Instalador: Nao criado (Inno Setup nao disponivel)")
        elif installer_status == "failed":
            logger.info("  Instalador: Falha na compilacao")
        elif installer_status == "script_failed":
            logger.info("  Instalador: Falha na geracao do script")
        logger.info("")

    logger.info(f"Pacotes salvos em: {DIST_OUTPUT}")


if __name__ == "__main__":
    main()
