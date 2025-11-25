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
import sys
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

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
                dest = target_dir / "LEIA-ME.txt"
            else:
                dest = docs_dir / src.name

            shutil.copy2(src, dest)
            logger.info(f"  Copiado: {src.name}")


def create_readme_usuario(target_dir: Path, build_system: str, version: str):
    """Cria README especifico para usuario final."""
    readme_content = f"""SSA Consulta Rapida v{version}
Build: {BUILD_SYSTEMS[build_system]['name']}

INSTALACAO E USO

1. PRIMEIRA EXECUCAO
   - Clique duas vezes em SSA_Consulta_Rapida.exe (ou main.exe para Nuitka)
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
   SSA_Consulta_Rapida.exe --gui

2. Interface CLI (Linha de Comando):
   SSA_Consulta_Rapida.exe

3. Dashboard Web (Streamlit):
   SSA_Consulta_Rapida.exe --streamlit

CONFIGURACAO DE ANTIVIRUS

Caso o antivirus bloqueie o executavel, adicione excecao para:
- Pasta completa do programa
- Consulte: docs/ANTIVIRUS_EXCLUSOES.txt para instrucoes detalhadas

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
    build_dir = PROJECT_ROOT / build_info["base_dir"]

    if not build_dir.exists():
        logger.error(f"Diretorio de build nao encontrado: {build_dir}")
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

        if build_system == "nuitka":
            # Nuitka: copiar tudo do diretorio
            for item in build_dir.iterdir():
                if item.is_file():
                    shutil.copy2(item, package_dir / item.name)
                elif item.is_dir() and item.name not in ['.git', '__pycache__', 'logs']:
                    shutil.copytree(item, package_dir / item.name, dirs_exist_ok=True)
        else:
            # PyInstaller/PyOxidizer: copiar executavel
            exe_src = PROJECT_ROOT / build_info["exe_path"]
            exe_dest = package_dir / exe_src.name
            shutil.copy2(exe_src, exe_dest)

            # Copiar pasta _internal ou lib
            if build_info["internal_dir"]:
                internal_src = build_dir / build_info["internal_dir"]
                if internal_src.exists():
                    shutil.copytree(
                        internal_src,
                        package_dir / build_info["internal_dir"],
                        dirs_exist_ok=True
                    )

        # Copiar config se existir
        config_src = build_dir / "config"
        if config_src.exists():
            shutil.copytree(config_src, package_dir / "config", dirs_exist_ok=True)
        else:
            # Copiar config da raiz do projeto
            config_src = PROJECT_ROOT / "config"
            if config_src.exists():
                shutil.copytree(config_src, package_dir / "config", dirs_exist_ok=True)

        # Criar estrutura de diretorios para usuario
        create_user_structure(package_dir)

        # Copiar documentacao
        copy_documentation(package_dir)

        # Criar README especifico
        create_readme_usuario(package_dir, build_system, version)

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
                    arcname = file_path.relative_to(temp_dir)
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

    build_info = BUILD_SYSTEMS[build_system]

    # Nome do executavel principal
    if build_system == "nuitka":
        exe_name = "main.exe"
    else:
        exe_name = "SSA_Consulta_Rapida.exe"

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
OutputDir=..\\..\\dist_packages
OutputBaseFilename=SSA_Consulta_Rapida_v{version}_{build_system}_Setup
SetupIconFile=..\\..\\assets\\icon.ico
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
Source: "..\\..\\{build_info['base_dir']}\\{exe_name}"; DestDir: "{{app}}"; Flags: ignoreversion
Source: "..\\..\\{build_info['base_dir']}\\*"; DestDir: "{{app}}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "*.log,*.tmp,__pycache__"

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


def compile_installer(iss_path: Path) -> bool:
    """Compila instalador usando Inno Setup."""
    logger.info("Compilando instalador com Inno Setup...")

    # Procurar ISCC.exe (compilador Inno Setup)
    possible_paths = [
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
        r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe",
        r"C:\Program Files\Inno Setup 5\ISCC.exe",
    ]

    iscc_path = None
    for path in possible_paths:
        if os.path.exists(path):
            iscc_path = path
            break

    if not iscc_path:
        logger.warning("Inno Setup nao encontrado. Instalador nao sera criado.")
        logger.info("  Para criar instaladores, instale Inno Setup de: https://jrsoftware.org/isdl.php")
        return False

    try:
        result = subprocess.run(
            [iscc_path, str(iss_path)],
            capture_output=True,
            text=True,
            timeout=300
        )

        if result.returncode == 0:
            logger.info("  Instalador compilado com sucesso!")
            return True
        else:
            logger.error(f"Erro ao compilar instalador: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        logger.error("Timeout ao compilar instalador")
        return False
    except Exception as e:
        logger.error(f"Erro ao executar Inno Setup: {e}")
        return False


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
            if iss_path and compile_installer(iss_path):
                results[bs]["installer"] = True
            else:
                results[bs]["installer"] = False

    # Relatorio final
    logger.info(f"\n{'='*60}")
    logger.info("RELATORIO FINAL")
    logger.info(f"{'='*60}\n")

    for bs, result in results.items():
        logger.info(f"{BUILD_SYSTEMS[bs]['name']}:")
        if result["zip"]:
            logger.info(f"  ZIP: {result['zip'].name}")
        if result["installer"]:
            logger.info(f"  Instalador: Criado com sucesso")
        elif result["installer"] is False:
            logger.info(f"  Instalador: Nao criado (Inno Setup nao disponivel)")
        logger.info("")

    logger.info(f"Pacotes salvos em: {DIST_OUTPUT}")


if __name__ == "__main__":
    main()
