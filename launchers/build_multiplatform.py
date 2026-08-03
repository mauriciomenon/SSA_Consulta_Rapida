#!/usr/bin/env python3
"""
SSA Consulta Rapida - Build System Multi-Plataforma
Compila executaveis para Windows, macOS e Linux com otimizacoes de tamanho.
Inclui limpeza automatica, commit e push apos build bem-sucedido.
"""

import argparse
import hashlib
import json
import logging
import os
import importlib
import platform
import plistlib
import shlex
import shutil
import subprocess  # nosec B404
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

robust_logging = importlib.import_module("utils.robust_logging")
logger = robust_logging.get_robust_logger().get_logger(__name__, "maintenance")
write_build_info = importlib.import_module("dev_env.build.write_build_info")


class MultiPlatformBuilder:
    """Construtor de executaveis multi-plataforma"""

    APP_DISPLAY_NAME = "Consulta Rapida de SSAs"

    PLATFORMS = {
        "windows_amd64": {
            "system": "Windows",
            "arch": "AMD64",
            "executable_ext": ".exe",
        },
        "macos_arm64": {"system": "Darwin", "arch": "arm64", "executable_ext": ""},
        "debian_amd64": {"system": "Linux", "arch": "x86_64", "executable_ext": ""},
        "debian_arm64": {"system": "Linux", "arch": "aarch64", "executable_ext": ""},
    }

    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        self.launchers_dir = self.base_dir / "launchers"
        self.platforms_dir = self.launchers_dir / "platforms"
        self.dist_dir = self.launchers_dir / "dist"
        self.logs_dir = self.launchers_dir / "logs"

        # Garantir que diretorios existam
        self.dist_dir.mkdir(exist_ok=True)
        self.logs_dir.mkdir(exist_ok=True)

        # Carregar versao
        self.version = self._load_version()
        self.runtime_python = os.environ.get("UV_PYTHON", "3.13")
        self.uv_cmd = shutil.which("uv") or "uv"

        logger.info(f"Iniciando build para SSA Consulta Rapida v{self.version}")
        logger.info(f"Runtime Python padrao (uv): {self.runtime_python}")

    @staticmethod
    def _run_command(cmd, *, timeout, cwd=None, capture_output=True, text=True):
        """Executa comando com timeout padrao e retorno padronizado."""
        command = [str(item) for item in cmd]
        command_for_log = " ".join(shlex.quote(item) for item in command)
        logger.debug("Executando comando: %s", command_for_log)
        try:
            return subprocess.run(  # nosec B603
                command,
                check=False,
                capture_output=capture_output,
                text=text,
                cwd=str(cwd) if cwd else None,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as exc:
            return subprocess.CompletedProcess(
                command,
                returncode=124,
                stdout="" if capture_output else None,
                stderr=(
                    f"Timeout apos {timeout}s: {command_for_log}: {exc}"
                    if capture_output
                    else None
                ),
            )
        except OSError as exc:
            return subprocess.CompletedProcess(
                command,
                returncode=1,
                stdout="" if capture_output else None,
                stderr=str(exc) if capture_output else None,
            )

    @staticmethod
    def _command_failed(result: subprocess.CompletedProcess, command_name: str) -> bool:
        if result.returncode == 0:
            return False

        stderr = str(result.stderr).strip() if result.stderr is not None else ""
        stdout = str(result.stdout).strip() if result.stdout is not None else ""
        logger.error(
            "%s falhou (%s): %s",
            command_name,
            result.returncode,
            stderr or stdout,
        )
        return True

    def _command_stdout(self, cmd, *, timeout=20) -> str:
        result = self._run_command(
            cmd,
            timeout=timeout,
            capture_output=True,
            text=True,
            cwd=str(self.base_dir),
        )
        if result.returncode != 0:
            command_text = " ".join(shlex.quote(str(item)) for item in cmd)
            stdout = str(result.stdout or "").strip()
            stderr = str(result.stderr or "").strip()
            detail = (stderr or stdout)[:1000]
            logger.warning(
                "Metadata command failed (%s): %s%s",
                result.returncode,
                command_text,
                f": {detail}" if detail else "",
            )
            return ""
        return str(result.stdout or "").strip()

    def _build_info_payload(self, build_system: str, platform_name: str) -> dict:
        return write_build_info.build_payload(
            self.base_dir,
            build_system,
            platform_name,
            self.version,
        )

    def _write_build_info_file(self, build_system: str, platform_name: str) -> Path:
        metadata_dir = self.platforms_dir / platform_name / "temp"
        metadata_dir.mkdir(parents=True, exist_ok=True)
        build_info_path = metadata_dir / "build_info.json"
        try:
            build_info_path.write_text(
                json.dumps(
                    self._build_info_payload(build_system, platform_name),
                    ensure_ascii=True,
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
        except OSError:
            logger.error("Failed to write build info to %s", build_info_path)
            raise
        return build_info_path

    @staticmethod
    def _windows_version_tuple(version: str) -> tuple[int, int, int, int]:
        parts: list[int] = []
        for raw_part in str(version or "0").split("."):
            digits = "".join(ch for ch in raw_part if ch.isdigit())
            parts.append(int(digits or 0))
            if len(parts) == 4:
                break
        while len(parts) < 4:
            parts.append(0)
        return (parts[0], parts[1], parts[2], parts[3])

    @staticmethod
    def _pyinstaller_version_value(value: object) -> str:
        return str(value or "").replace("\\", "\\\\").replace("'", "\\'")

    def _write_pyinstaller_windows_version_file(self, platform_name: str, app_name: str) -> Path:
        metadata_dir = self.platforms_dir / platform_name / "temp"
        metadata_dir.mkdir(parents=True, exist_ok=True)
        version_file_path = metadata_dir / f"{app_name}_version_info.txt"
        version_tuple = self._windows_version_tuple(self.version)
        version_text = ".".join(str(part) for part in version_tuple)
        original_filename = f"{app_name}.exe"
        version_file_path.write_text(
            f"""# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={version_tuple},
    prodvers={version_tuple},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        '040904B0',
        [
          StringStruct('CompanyName', 'SSA Consulta Rapida'),
          StringStruct('FileDescription', '{self._pyinstaller_version_value(original_filename)}'),
          StringStruct('FileVersion', '{self._pyinstaller_version_value(version_text)}'),
          StringStruct('InternalName', '{self._pyinstaller_version_value(app_name)}'),
          StringStruct('OriginalFilename', '{self._pyinstaller_version_value(original_filename)}'),
          StringStruct('ProductName', 'SSA Consulta Rapida'),
          StringStruct('ProductVersion', '{self._pyinstaller_version_value(version_text)}')
        ]
      )
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
""",
            encoding="utf-8",
        )
        return version_file_path

    def _load_requirements_signature(self, requirements_file: Path) -> str:
        """Retorna hash deterministico do conteudo de requirements."""
        digest = hashlib.sha256()
        try:
            with requirements_file.open("r", encoding="utf-8") as file_handle:
                for raw_line in file_handle:
                    line = raw_line.strip()
                    if not line or line.startswith("#"):
                        continue
                    digest.update((line + "\n").encode("utf-8"))
            return digest.hexdigest()
        except OSError as exc:
            logger.warning(
                "Nao foi possivel calcular signature de requirements em %s: %s",
                requirements_file,
                exc,
            )
            return ""

    def _load_version(self):
        """Carrega versao do arquivo config/version.json sem fallback silencioso."""
        version_file = self.base_dir / "config" / "version.json"
        if not version_file.is_file():
            raise RuntimeError(f"Arquivo de versao ausente: {version_file}")
        try:
            data = json.loads(version_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Arquivo de versao invalido: {version_file}: {exc}") from exc
        version = str(data.get("version_short") or data.get("version") or "").strip()
        if not version:
            raise RuntimeError(f"version_short ausente em {version_file}")
        return version

    def detect_current_platform(self):
        """Detecta plataforma atual"""
        system = platform.system()
        machine = platform.machine().lower()

        if system == "Windows" and machine in ["amd64", "x86_64"]:
            return "windows_amd64"
        elif system == "Darwin" and machine in ["arm64", "aarch64"]:
            return "macos_arm64"
        elif system == "Linux" and machine in ["x86_64", "amd64"]:
            return "debian_amd64"
        elif system == "Linux" and machine in ["aarch64", "arm64"]:
            return "debian_arm64"
        else:
            logger.error(f"Plataforma nao suportada: {system} {machine}")
            return None

    def _python_executable(self, platform_name: str) -> Path:
        """Retorna caminho esperado do python dentro do venv."""
        venv_dir = self.platforms_dir / platform_name / "venv"
        if platform_name.startswith("windows"):
            return venv_dir / "Scripts" / "python.exe"
        return venv_dir / "bin" / "python"

    def _is_python_executable_ok(self, python_exe: Path) -> bool:
        """Verifica se o python do venv responde normalmente."""
        result = self._run_command(
            [python_exe, "-c", "import sys"], timeout=15, capture_output=True, text=True
        )
        return result.returncode == 0

    def _is_venv_compatible(self, platform_name: str, requirements_file: Path) -> bool:
        """Valida se o venv existente pode ser reutilizado."""
        venv_dir = self.platforms_dir / platform_name / "venv"
        python_exe = self._python_executable(platform_name)
        if not (venv_dir.exists() and python_exe.exists()):
            return False
        if not self._is_python_executable_ok(python_exe):
            return False

        if not requirements_file.exists():
            return True

        marker_path = venv_dir / ".requirements_signature"
        if not marker_path.exists():
            logger.info("Recriando venv: marcador de requirements ausente")
            return False

        current_signature = self._load_requirements_signature(requirements_file)
        if not current_signature:
            return False

        try:
            return marker_path.read_text(encoding="utf-8").strip() == current_signature
        except OSError as exc:
            logger.info(
                "Recriando venv por falha ao ler marcador em %s: %s",
                marker_path,
                exc,
            )
            return False

    def _save_requirements_signature(self, venv_dir: Path, requirements_file: Path) -> None:
        """Salva assinatura de requirements no venv para reutilizacao."""
        signature = self._load_requirements_signature(requirements_file)
        if not signature:
            return
        marker_path = venv_dir / ".requirements_signature"
        try:
            marker_path.write_text(f"{signature}\n", encoding="utf-8")
        except OSError as exc:
            logger.warning(
                "Nao foi possivel gravar marcador de requirements em %s: %s",
                marker_path,
                exc,
            )

    def setup_virtual_environment(self, platform_name, skip_if_exists=False):
        """Setup do ambiente virtual usando uv."""
        venv_dir = self.platforms_dir / platform_name / "venv"
        requirements_file = self.platforms_dir / platform_name / "requirements.txt"

        # Determinar executaveis
        python_exe = self._python_executable(platform_name)

        # Verificar se venv ja existe e esta funcional
        if self._is_venv_compatible(platform_name, requirements_file):
            logger.info(f"Ambiente virtual existente encontrado: {venv_dir}")
            if skip_if_exists:
                logger.info("Reaproveitando venv existente por --skip-venv")
            return python_exe

        if skip_if_exists:
            logger.error("Venv nao pode ser reaproveitado; passe sem --skip-venv para recriar")
            return False

        # Remover venv antigo se existir
        if venv_dir.exists():
            logger.info("Removendo ambiente virtual antigo")
            shutil.rmtree(venv_dir)

        logger.info(f"Criando novo ambiente virtual: {venv_dir}")

        cmd = [
            self.uv_cmd,
            "venv",
            "--python",
            self.runtime_python,
            str(venv_dir),
        ]
        result = self._run_command(cmd, timeout=600, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error("Erro criando venv via uv: %s", result.stderr.strip())
            return False

        # Instalar dependencias
        if requirements_file.exists():
            logger.info("Instalando dependencias com uv pip...")
            cmd = [
                self.uv_cmd,
                "pip",
                "install",
                "--python",
                str(python_exe),
                "-r",
                str(requirements_file),
            ]
            result = self._run_command(cmd, timeout=1200, capture_output=True, text=True)
            if result.returncode != 0:
                logger.error("Erro instalando dependencias: %s", result.stderr.strip())
                return False
            self._save_requirements_signature(venv_dir, requirements_file)

        logger.info(f"Ambiente virtual configurado: {venv_dir}")
        return python_exe

    def load_build_config(self, platform_name):
        """Carrega configuracao de build para plataforma"""
        config_file = self.platforms_dir / platform_name / "build_config.json"

        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
                # Substituir placeholders de versao
                config_str = json.dumps(config)
                config_str = config_str.replace("{version}", self.version)
                return json.loads(config_str)
        except Exception as e:
            logger.error(f"Erro carregando config: {e}")
            return None

    def convert_icons(self, python_exe: Path):
        """Converte icones para formatos necessarios"""
        logger.info("Convertendo icones para diferentes formatos")

        resources_dir = self.base_dir / "resources"
        svg_icon = resources_dir / "app_icon.svg"

        if not svg_icon.exists():
            logger.warning("Icone SVG nao encontrado")
            return False

        target_icons = [
            resources_dir / "app_icon.ico",
            resources_dir / "app_icon.icns",
            resources_dir / "app_icon.png",
        ]
        if all(target.exists() for target in target_icons):
            source_mtime = svg_icon.stat().st_mtime
            if all(target.stat().st_mtime >= source_mtime for target in target_icons):
                logger.info("Icones atualizados; pulando convert_icon.py")
                return True

        try:
            # Executar script de conversao
            convert_script = self.launchers_dir / "convert_icon.py"
            cmd = [
                self.uv_cmd,
                "run",
                "--no-project",
                "--python",
                str(python_exe),
                str(convert_script),
            ]
            result = self._run_command(
                cmd,
                timeout=300,
                capture_output=True,
                text=True,
                cwd=str(self.base_dir),
            )

            if result.returncode == 0:
                logger.info("Icones convertidos com sucesso")
                return True
            else:
                logger.error(f"Erro convertendo icones: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Erro executando conversao de icones: {e}")
            return False

    def build_executable(
        self, platform_name, app_type, python_exe, config, runtime_db=None
    ):
        """Constroi executavel para tipo especifico (cli/gui)"""
        logger.info(f"Construindo {app_type.upper()} para {platform_name}")

        # Configuracao base
        app_config = config[f"{app_type}_config"]
        pyinstaller_args = config["pyinstaller_args"]
        if pyinstaller_args.get("onefile", False) or not pyinstaller_args.get(
            "onedir", False
        ):
            logger.error("Build de distribuicao exige modo onedir: %s", platform_name)
            return False
        if runtime_db is None and pyinstaller_args.get("include_local_data", False):
            runtime_db = self.base_dir / "data" / "ssas.db"
            logger.warning(
                "include_local_data legado ativado; somente data/ssas.db sera "
                "copiado externamente."
            )
        runtime_db_path = None
        if runtime_db is not None:
            runtime_db_path = Path(runtime_db).resolve()
            if runtime_db_path.name != "ssas.db" or not runtime_db_path.is_file():
                logger.error("Banco de runtime invalido ou ausente: %s", runtime_db_path)
                return False

        # Comando base
        cmd = [
            self.uv_cmd,
            "run",
            "--no-project",
            "--python",
            str(python_exe),
            "-m",
            "PyInstaller",
            "-y",
            ]  # -y forca sobrescrita

        # Opcoes de empacotamento
        if pyinstaller_args.get("onefile", False):
            cmd.append("--onefile")
        elif pyinstaller_args.get("onedir", False):
            cmd.append("--onedir")

        # Opcoes de interface
        if app_config.get("console", False):
            cmd.append("--console")
        elif app_config.get("windowed", False):
            cmd.append("--windowed")

        # Nome do executavel
        cmd.extend(["--name", app_config["name"]])

        # Icone
        icon_path = self.base_dir / app_config.get("icon", "")
        if icon_path.exists():
            cmd.extend(["--icon", str(icon_path)])

        if platform_name.startswith("windows"):
            version_file_path = self._write_pyinstaller_windows_version_file(
                platform_name,
                app_config["name"],
            )
            cmd.extend(["--version-file", str(version_file_path)])

        # Otimizacoes
        if pyinstaller_args.get("optimize"):
            cmd.extend(["--optimize", str(pyinstaller_args["optimize"])])

        if pyinstaller_args.get("strip", False):
            cmd.append("--strip")

        # Exclusoes de modulos
        for module in pyinstaller_args.get("exclude_modules", []):
            cmd.extend(["--exclude-module", module])

        # Imports ocultos
        for imp in pyinstaller_args.get("hidden_imports", []):
            cmd.extend(["--hidden-import", imp])

        # Adicionar path do projeto para encontrar modulos locais
        cmd.extend(["--paths", str(self.base_dir)])

        # Dados adicionais
        config_path = self.base_dir / "config"
        guide_path = self.base_dir / "docs" / "GUIA_MIGRACAO_NOVA_INSTALACAO.md"
        build_info_path = self._write_build_info_file("pyinstaller", platform_name)
        add_data_sep = ";" if platform_name.startswith("windows") else ":"

        if config_path.exists():
            for config_file in sorted(config_path.rglob("*")):
                if (
                    not config_file.is_file()
                    or "__pycache__" in config_file.parts
                    or config_file.suffix.lower() in {".py", ".pyc"}
                ):
                    continue
                config_destination = Path("config") / config_file.relative_to(
                    config_path
                ).parent
                cmd.extend(
                    [
                        "--add-data",
                        f"{config_file}{add_data_sep}{config_destination.as_posix()}",
                    ]
                )
        if guide_path.exists():
            cmd.extend(["--add-data", f"{guide_path}{add_data_sep}docs"])
        cmd.extend(["--add-data", f"{build_info_path}{add_data_sep}config"])
        # Argumentos adicionais
        for arg in app_config.get("additional_args", []):
            cmd.append(arg)

        # Arquivo de entrada
        entry_file = self.launchers_dir / f"{app_type}_entry.py"
        cmd.append(str(entry_file))

        # Executar build
        logger.info(f"Executando: {' '.join(cmd)}")

        result = self._run_command(
            cmd,
            timeout=1800,
            capture_output=True,
            text=True,
            cwd=str(self.base_dir),
        )

        if result.returncode == 0:
            bundle_root = self.dist_dir / platform_name / app_config["name"]
            runtime_root = bundle_root
            if platform_name == "macos_arm64" and app_config.get("windowed", False):
                bundle_root = bundle_root.with_suffix(".app")
                runtime_root = bundle_root / "Contents" / "MacOS"
            if runtime_db_path is not None:
                if not bundle_root.is_dir():
                    logger.error("Bundle onedir nao encontrado: %s", bundle_root)
                    return False
                internal_sensitive = [
                    path
                    for path in bundle_root.rglob("*")
                    if path.is_file()
                    and "_internal" in path.parts
                    and path.suffix.lower()
                    in {".db", ".xls", ".xlsx", ".xlsm", ".ods"}
                ]
                if internal_sensitive:
                    logger.error(
                        "Bundle contem banco ou planilha em _internal: %s",
                        ", ".join(str(path) for path in internal_sensitive),
                    )
                    return False
                runtime_data = runtime_root / "data"
                runtime_data.mkdir(parents=True, exist_ok=True)
                shutil.copy2(runtime_db_path, runtime_data / "ssas.db")
                logger.info(
                    "Banco operacional copiado externamente: %s",
                    runtime_data / "ssas.db",
                )
            for folder in (
                runtime_root / "data" / "historico_backups",
                runtime_root / "docs_entrada",
                runtime_root / "docs_saida",
                runtime_root / "logs",
                runtime_root / "reports",
                runtime_root / "exportacao",
            ):
                folder.mkdir(parents=True, exist_ok=True)
            logger.info(f"{app_type.upper()} construido com sucesso")
            return True
        else:
            logger.error(f"Erro construindo {app_type}: {result.stderr}")
            return False

    def post_process(self, platform_name, config, apps=None):
        """Pos-processamento dos executaveis"""
        logger.info(f"Pos-processando executaveis para {platform_name}")

        post_config = config.get("post_build", {})
        package_mode = str(post_config.get("package", "")).strip().lower()
        apps_set = set(apps or ["cli", "gui"])
        platform_dist = self.dist_dir / platform_name
        macos_gui_app_bundle = None

        if not platform_dist.exists():
            logger.warning(f"Diretorio dist nao encontrado: {platform_dist}")
            return False

        # Compressao UPX (apenas Linux e Windows)
        if post_config.get("compress", False) and platform_name != "macos_arm64":
            self._compress_executables(platform_dist)

        if platform_name == "macos_arm64" and "gui" in apps_set:
            macos_gui_app_bundle = self._sync_macos_gui_display_name(
                platform_dist,
                config,
                sign_bundle=bool(post_config.get("sign", False)),
            )
            if macos_gui_app_bundle is None:
                return False

        if platform_name == "macos_arm64" and package_mode == "dmg":
            if "gui" not in apps_set:
                logger.info("Build macOS sem app GUI; etapa de DMG foi pulada.")
            elif not self._create_macos_dmg(
                platform_dist, app_bundle=macos_gui_app_bundle
            ):
                return False

        # Criar manifesto apos finalizar os artefatos de pacote.
        self._create_manifest(platform_name, platform_dist)

        return True

    def _find_macos_gui_app(self, dist_dir, *, allow_fallback=True):
        """Localiza o bundle .app principal da GUI para empacotamento DMG."""
        expected = dist_dir / f"SSA_GUI_v{self.version}_macos_arm64.app"
        if expected.exists() and expected.is_dir():
            return expected

        if not allow_fallback:
            return None

        candidates = sorted(
            (path for path in dist_dir.glob("SSA_GUI_*.app") if path.is_dir()),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        if candidates:
            return candidates[0]
        return None

    def _sync_macos_gui_display_name(self, dist_dir, config=None, *, sign_bundle=False):
        """Atualiza CFBundleName e CFBundleDisplayName do app GUI no macOS."""
        app_bundle = self._resolve_macos_gui_app_bundle_for_display_name(dist_dir, config)
        if app_bundle is None:
            return None

        info_plist_path = app_bundle / "Contents" / "Info.plist"
        if not info_plist_path.exists():
            logger.error("Info.plist nao encontrado no bundle GUI: %s", info_plist_path)
            return None

        if not self._update_macos_info_plist_display_name(info_plist_path):
            return None

        if sign_bundle and platform.system() == "Darwin":
            if not self._sign_macos_gui_app_bundle(app_bundle):
                return None

        return app_bundle

    def _resolve_macos_gui_app_bundle_for_display_name(self, dist_dir, config=None):
        app_bundle = None
        gui_config = (config or {}).get("gui_config") or {}
        if isinstance(gui_config, dict):
            raw_name = gui_config.get("name") or ""
            configured_name = (
                str(raw_name).replace("{version}", self.version) if raw_name else ""
            )
            if configured_name:
                configured_bundle = dist_dir / f"{configured_name}.app"
                if configured_bundle.exists() and configured_bundle.is_dir():
                    app_bundle = configured_bundle
                else:
                    logger.error(
                        "Bundle .app configurado para GUI nao encontrado em %s",
                        configured_bundle,
                    )
                    return None
        if app_bundle is None:
            app_bundle = self._find_macos_gui_app(dist_dir, allow_fallback=False)
        if app_bundle is None:
            logger.error(
                "Bundle .app da GUI da versao atual nao encontrado para atualizar nome em %s",
                dist_dir,
            )
            return None
        return app_bundle

    def _update_macos_info_plist_display_name(self, info_plist_path):
        try:
            with open(info_plist_path, "rb") as plist_file:
                plist_data = plistlib.load(plist_file)
        except (OSError, plistlib.InvalidFileException, ValueError) as exc:
            logger.error("Falha ao ler Info.plist '%s': %s", info_plist_path, exc)
            return False

        plist_data["CFBundleName"] = self.APP_DISPLAY_NAME
        plist_data["CFBundleDisplayName"] = self.APP_DISPLAY_NAME

        try:
            with open(info_plist_path, "wb") as plist_file:
                plistlib.dump(plist_data, plist_file)
        except OSError as exc:
            logger.error("Falha ao atualizar Info.plist '%s': %s", info_plist_path, exc)
            return False

        logger.info(
            "Nome de exibicao do bundle macOS atualizado para '%s'",
            self.APP_DISPLAY_NAME,
        )
        return True

    def _sign_macos_gui_app_bundle(self, app_bundle):
        codesign_cmd = shutil.which("codesign")
        if not codesign_cmd:
            logger.error("codesign nao encontrado para validar bundle macOS")
            return False

        codesign_identity = os.environ.get("MACOS_CODESIGN_IDENTITY") or "-"
        sign_result = self._run_command(
            [
                codesign_cmd,
                "--force",
                "--deep",
                "--sign",
                codesign_identity,
                str(app_bundle),
            ],
            timeout=300,
            capture_output=True,
            text=True,
            cwd=str(self.base_dir),
        )
        if sign_result.returncode != 0:
            logger.error("Falha ao assinar bundle macOS: %s", sign_result.stderr.strip())
            return False

        verify_result = self._run_command(
            [
                codesign_cmd,
                "--verify",
                "--deep",
                "--strict",
                "--verbose=2",
                str(app_bundle),
            ],
            timeout=300,
            capture_output=True,
            text=True,
            cwd=str(self.base_dir),
        )
        if verify_result.returncode != 0:
            logger.error(
                "Falha ao verificar assinatura do bundle macOS: %s",
                (verify_result.stderr or verify_result.stdout).strip(),
            )
            return False
        return True

    def _create_macos_dmg(self, dist_dir, *, app_bundle=None):
        """Gera instalador DMG a partir do bundle .app da GUI."""
        hdiutil_cmd = shutil.which("hdiutil")
        if not hdiutil_cmd:
            logger.error("hdiutil nao encontrado; nao foi possivel gerar DMG")
            return False

        app_bundle = app_bundle or self._find_macos_gui_app(dist_dir, allow_fallback=False)
        if app_bundle is None:
            logger.error("Bundle .app da GUI da versao atual nao encontrado em %s", dist_dir)
            return False

        dmg_name = self._get_macos_dmg_name()
        dmg_path = dist_dir / dmg_name
        if dmg_path.exists():
            try:
                dmg_path.unlink()
            except OSError as exc:
                logger.error("Falha ao remover DMG anterior '%s': %s", dmg_path, exc)
                return False

        cmd = [
            hdiutil_cmd,
            "create",
            "-volname",
            f"SSA Consulta Rapida v{self.version}",
            "-srcfolder",
            str(app_bundle),
            "-ov",
            "-format",
            "UDZO",
            str(dmg_path),
        ]
        logger.info("Gerando DMG macOS: %s", dmg_path)
        result = self._run_command(
            cmd,
            timeout=900,
            capture_output=True,
            text=True,
            cwd=str(self.base_dir),
        )
        if result.returncode != 0:
            logger.error("Falha ao gerar DMG: %s", result.stderr.strip())
            return False
        if not dmg_path.exists():
            logger.error("hdiutil finalizou sem gerar DMG esperado: %s", dmg_path)
            return False

        logger.info("DMG gerado com sucesso: %s", dmg_path)
        return True

    def _get_macos_dmg_name(self):
        return f"SSA_Consulta_Rapida_v{self.version}_macos_arm64.dmg"

    def _compress_executables(self, dist_dir):
        """Comprime executaveis com UPX"""
        try:
            # Procurar UPX no sistema
            upx_cmd = shutil.which("upx")
            if not upx_cmd:
                logger.warning("UPX nao encontrado, pulando compressao")
                return

            for exe_file in dist_dir.glob("*"):
                if exe_file.is_file() and not exe_file.suffix == ".app":
                    logger.info(f"Comprimindo {exe_file.name}")
                    result = self._run_command(
                        [upx_cmd, "--best", str(exe_file)],
                        timeout=120,
                        capture_output=True,
                        text=True,
                    )
                    if result.returncode != 0:
                        logger.warning("UPX falhou em %s: %s", exe_file, result.stderr)
        except Exception as e:
            logger.warning(f"Erro na compressao: {e}")

    def _create_manifest(self, platform_name, dist_dir):
        """Cria manifesto de build"""
        manifest = {
            "platform": platform_name,
            "version": self.version,
            "build_date": datetime.now().isoformat(),
            "executables": [],
        }
        directory_size_cache: dict[Path, int] = {}

        for artifact in sorted(
            dist_dir.glob("*"), key=lambda path: path.name.casefold()
        ):
            name = artifact.name
            if name in {"build_manifest.json", ".DS_Store"}:
                continue
            if name.startswith("."):
                continue

            if artifact.is_file():
                size_bytes = artifact.stat().st_size
                artifact_kind = "file"
            elif artifact.is_dir():
                cache_key = artifact.resolve(strict=False)
                size_bytes = directory_size_cache.get(cache_key)
                if size_bytes is None:
                    size_bytes = self._compute_directory_size_bytes(artifact)
                    directory_size_cache[cache_key] = size_bytes
                artifact_kind = "directory"
            else:
                continue

            size_mb = 0.0 if size_bytes <= 0 else (size_bytes / (1024 * 1024))
            manifest["executables"].append(
                {
                    "name": name,
                    "kind": artifact_kind,
                    "size_mb": round(size_mb, 2),
                    "path": str(artifact.relative_to(self.dist_dir)),
                }
            )

        manifest_file = dist_dir / "build_manifest.json"
        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

        logger.info(f"Manifesto criado: {manifest_file}")

    @staticmethod
    def _compute_directory_size_bytes(directory: Path) -> int:
        total = 0
        stack = [directory]

        while stack:
            current = stack.pop()
            try:
                entry_iter = os.scandir(current)
            except OSError:
                continue

            for entry in entry_iter:
                if entry.is_symlink():
                    continue
                try:
                    if entry.is_dir(follow_symlinks=False):
                        stack.append(Path(entry.path))
                    elif entry.is_file(follow_symlinks=False):
                        total += entry.stat(follow_symlinks=False).st_size
                except OSError:
                    # Ignore transient or permission failures while scanning artifact trees.
                    continue

        return total

    def build_platform(
        self, platform_name, apps=None, skip_venv=False, runtime_db=None
    ):
        """Constroi executaveis para uma plataforma especifica"""
        if platform_name not in self.PLATFORMS:
            logger.error(f"Plataforma nao suportada: {platform_name}")
            return False

        logger.info(f"Iniciando build para {platform_name}")

        # Configurar ambiente
        python_exe = self.setup_virtual_environment(platform_name, skip_if_exists=skip_venv)
        if not python_exe:
            return False

        # Carregar configuracao
        config = self.load_build_config(platform_name)
        if not config:
            return False

        # Converter icones
        if not self.convert_icons(python_exe):
            logger.warning("Continuando sem icones")

        # Construir aplicacoes
        apps = apps or ["cli", "gui"]
        success = True

        for app_type in apps:
            if not self.build_executable(
                platform_name, app_type, python_exe, config, runtime_db=runtime_db
            ):
                success = False

        # Pos-processamento
        if success:
            success = self.post_process(platform_name, config, apps=apps)

        return success

    def cleanup_build_artifacts(self):
        """Remove artefatos de build desnecessarios apos build bem-sucedido"""
        logger.info("Iniciando limpeza automatica de artefatos de build...")

        cleanup_count = 0

        def remove_path(target_path: Path) -> bool:
            if not target_path.exists():
                return False
            if target_path.is_dir():
                shutil.rmtree(target_path)
            else:
                target_path.unlink()
            return True

        # 1. Limpeza de diretorios temporarios de build
        build_cleanup_dirs = [
            self.base_dir / "build",
            self.launchers_dir / "dist_simple",
        ]

        for candidate in build_cleanup_dirs:
            if remove_path(candidate):
                logger.debug("Removido diretorio de build: %s", candidate)
                cleanup_count += 1

        # 2. Remover arquivos de cache Python
        cache_roots = [
            self.launchers_dir,
            self.base_dir / "builds",
            self.base_dir / "build",
        ]
        cache_dirs = ["__pycache__", ".pytest_cache"]
        cache_file_patterns = ["*.pyc", "*.pyo"]
        for root in cache_roots:
            if not root.exists():
                continue
            for cache_dir in cache_dirs:
                cache_path = root / cache_dir
                if cache_path.exists():
                    if remove_path(cache_path):
                        logger.debug("Cache removido: %s", cache_path)
                        cleanup_count += 1
            for pattern in cache_file_patterns:
                for path in root.glob(pattern):
                    if remove_path(path):
                        logger.debug("Arquivo cache removido: %s", path)
                        cleanup_count += 1
            for path in root.glob("*.egg-info"):
                if remove_path(path):
                    logger.debug("Arquivo cache removido: %s", path)
                    cleanup_count += 1

        # 3. Remover logs antigos (manter apenas os 5 mais recentes)
        logs_dir = self.launchers_dir / "logs"
        if logs_dir.exists():
            log_files = sorted(
                logs_dir.glob("*.log"), key=lambda x: x.stat().st_mtime, reverse=True
            )
            for log_file in log_files[5:]:  # Remove logs alem dos 5 mais recentes
                log_file.unlink()
                logger.debug(f"Log antigo removido: {log_file}")
                cleanup_count += 1

        # 4. Remover arquivos temporarios do sistema
        temp_roots = [
            self.launchers_dir,
            self.base_dir / "build",
            self.base_dir / "builds",
            self.base_dir / "dist",
            self.base_dir / "dist_packages",
            self.base_dir / "logs",
        ]
        temp_patterns = [
            ".DS_Store",
            "Thumbs.db",
            "*.tmp",
            "*.temp",
        ]
        for pattern in temp_patterns:
            for root in temp_roots:
                if not root.exists():
                    continue
                for temp_file in root.glob(pattern):
                    if temp_file.is_file() and temp_file.exists():
                        if remove_path(temp_file):
                            logger.debug("Arquivo temporario removido: %s", temp_file)
                            cleanup_count += 1

        logger.info(f"Limpeza concluida: {cleanup_count} itens removidos")
        return cleanup_count > 0

    def git_add_commit_push(self, custom_message=None):
        """Adiciona, commita e faz push das alteracoes para o git"""
        logger.info("Iniciando operacoes git...")

        try:
            # Verificar se estamos em um repositorio git
            result = self._run_command(
                ["git", "status"],
                timeout=20,
                capture_output=True,
                text=True,
                cwd=str(self.base_dir),
            )
            if result.returncode != 0:
                logger.error("Nao e um repositorio git valido")
                return False

            # Verificar se ha alteracoes para commit
            result = self._run_command(
                ["git", "status", "--porcelain"],
                timeout=20,
                capture_output=True,
                text=True,
                cwd=str(self.base_dir),
            )

            if not result.stdout.strip():
                logger.info("Nenhuma alteracao para commit")
                return True

            # Adicionar arquivos importantes (excluir executaveis)
            files_to_add = [
                "launchers/*.py",
                "launchers/platforms/*/build_config.json",
                "launchers/platforms/*/requirements.txt",
                "launchers/*.md",
                "dev_env/build/*.sh",
                "config/*.json",
                "docs/*.md",
                "*.py",
                "*.md",
                "requirements.txt",
                "pyproject.toml",
            ]

            for file_pattern in files_to_add:
                self._run_command(
                    ["git", "add", file_pattern],
                    timeout=30,
                    capture_output=True,
                    text=True,
                    cwd=str(self.base_dir),
                )

            # Criar mensagem de commit
            if custom_message:
                commit_message = custom_message
            else:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                commit_message = f"Build automatico v{self.version} - {timestamp}"

            # Commit
            result = self._run_command(
                ["git", "commit", "-m", commit_message],
                timeout=60,
                capture_output=True,
                text=True,
                cwd=str(self.base_dir),
            )

            if result.returncode == 0:
                logger.info(f"Commit realizado: {commit_message}")
            else:
                logger.warning(f"Nada para commitar ou erro: {result.stderr}")

            # Push
            result = self._run_command(
                ["git", "push"],
                timeout=120,
                capture_output=True,
                text=True,
                cwd=str(self.base_dir),
            )

            if result.returncode == 0:
                logger.info("Push realizado com sucesso")
                return True
            else:
                logger.error(f"Erro no push: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Erro nas operacoes git: {e}")
            return False

    def cleanup_online_unnecessary_files(self):
        """Remove arquivos desnecessarios que podem estar online"""
        logger.info("Verificando arquivos desnecessarios online...")
        tracked_result = self._run_command(
            ["git", "ls-files"],
            timeout=30,
            capture_output=True,
            text=True,
            cwd=str(self.base_dir),
        )
        if tracked_result.returncode != 0:
            logger.warning("Nao foi possivel carregar lista de arquivos rastreados")
            return False

        tracked_files = {
            line.strip()
            for line in tracked_result.stdout.splitlines()
            if line.strip()
        }
        tracked_scope_map = {
            "launchers/dist": set(),
            "launchers/dist_simple": set(),
        }

        for tracked_path in tracked_files:
            normalized = tracked_path.replace("\\", "/")
            for scope_prefix in tracked_scope_map:
                prefix = f"{scope_prefix}/"
                if not normalized.startswith(prefix):
                    continue
                tracked_scope_map[scope_prefix].add(normalized)

        unnecessary_scopes = [
            self.launchers_dir / "dist",
            self.launchers_dir / "dist_simple",
            self.launchers_dir / "logs",
            self.base_dir / "build",
            self.base_dir / "builds",
            self.base_dir / "dist_packages",
            self.base_dir / "logs",
            self.base_dir / "dist",
        ]

        unnecessary_patterns = [
            # Arquivos de controle
            "file_cache.json",
            "*.backup_*",
            # Cache e temporarios
            "*.pyc",
            "*.pyo",
            "Thumbs.db",
            ".DS_Store",
            "*.tmp",
            "*.temp",
        ]

        def collect_scope_top_level(scope_dir: Path) -> list[str]:
            scope_prefix = str(scope_dir.relative_to(self.base_dir)).replace("\\", "/")
            return sorted(tracked_scope_map.get(scope_prefix, set()))

        def is_tracked(file_path: Path) -> bool:
            try:
                rel_path = str(file_path.relative_to(self.base_dir)).replace("\\", "/")
            except ValueError:
                return False
            return rel_path in tracked_files

        files_to_remove: list[str] = []

        def collect_for_cleanup(file_path: Path) -> None:
            if file_path.exists() and file_path.is_file() and is_tracked(file_path):
                files_to_remove.append(
                    str(file_path.relative_to(self.base_dir)).replace("\\", "/")
                )

        for scope_dir in unnecessary_scopes:
            if not scope_dir.exists():
                continue

            if scope_dir in {
                self.launchers_dir / "dist",
                self.launchers_dir / "dist_simple",
            }:
                for relative in collect_scope_top_level(scope_dir):
                    files_to_remove.append(relative)
                continue

            for pattern in unnecessary_patterns:
                for file_path in scope_dir.glob(pattern):
                    collect_for_cleanup(file_path)

            for dir_path in [scope_dir / "historico_backups"]:
                if not dir_path.exists() or not dir_path.is_dir():
                    continue
                directory_stack = [dir_path]
                while directory_stack:
                    current_directory = directory_stack.pop()
                    try:
                        dir_entries = os.scandir(current_directory)
                    except OSError:
                        continue
                    for entry in dir_entries:
                        if entry.is_symlink():
                            continue
                        entry_path = Path(entry.path)
                        try:
                            if entry.is_dir(follow_symlinks=False):
                                directory_stack.append(entry_path)
                            elif entry.is_file(follow_symlinks=False):
                                collect_for_cleanup(entry_path)
                        except OSError:
                            continue

        # Escopo restrito para dados: arquivos explicitos para evitar varredura ampla
        data_dir = self.base_dir / "data"
        if data_dir.exists():
            collect_for_cleanup(data_dir / "file_cache.json")
            for file_path in data_dir.glob("*.backup_*"):
                collect_for_cleanup(file_path)
            historico_backups = data_dir / "historico_backups"
            if historico_backups.is_dir():
                directory_stack = [historico_backups]
                while directory_stack:
                    current_directory = directory_stack.pop()
                    try:
                        dir_entries = os.scandir(current_directory)
                    except OSError:
                        continue
                    for entry in dir_entries:
                        if entry.is_symlink():
                            continue
                        entry_path = Path(entry.path)
                        try:
                            if entry.is_dir(follow_symlinks=False):
                                directory_stack.append(entry_path)
                            elif entry.is_file(follow_symlinks=False):
                                collect_for_cleanup(entry_path)
                        except OSError:
                            continue

        files_removed = []
        if files_to_remove:
            for index in range(0, len(files_to_remove), 500):
                batch = files_to_remove[index : index + 500]
                rm_result = self._run_command(
                    ["git", "rm", "--cached", "--"] + batch,
                    timeout=30,
                    capture_output=True,
                    text=True,
                    cwd=str(self.base_dir),
                )
                if rm_result.returncode == 0:
                    files_removed.extend(batch)
                else:
                    logger.warning(
                        "Falha parcial ao remover arquivos do cache git: %s",
                        rm_result.stderr.strip() or rm_result.stdout.strip(),
                    )

        if files_removed:
            logger.info(
                f"Removidos {len(files_removed)} arquivos desnecessarios do controle de versao"
            )
        else:
            logger.info("Nenhum arquivo desnecessario encontrado no controle de versao")

        return len(files_removed) > 0

    def clean(self, platform_name=None):
        """Limpa builds anteriores"""
        if platform_name:
            # Limpar plataforma especifica
            platform_dir = self.platforms_dir / platform_name
            venv_dir = platform_dir / "venv"
            temp_dir = platform_dir / "temp"
            dist_dir = self.dist_dir / platform_name

            for dir_path in [venv_dir, temp_dir, dist_dir]:
                if dir_path.exists():
                    logger.info(f"Removendo {dir_path}")
                    shutil.rmtree(dir_path)
        else:
            # Limpar tudo
            logger.info("Limpando todos os builds")
            if self.dist_dir.exists():
                shutil.rmtree(self.dist_dir)

            for platform_id in self.PLATFORMS:
                platform_dir = self.platforms_dir / platform_id
                venv_dir = platform_dir / "venv"
                temp_dir = platform_dir / "temp"

                for dir_path in [venv_dir, temp_dir]:
                    if dir_path.exists():
                        shutil.rmtree(dir_path)


def main(argv=None):
    """Funcao principal"""
    parser = argparse.ArgumentParser(
        description=(
            "Build local por plataforma para SSA Consulta Rapida "
            "(sem cross-compilation automatica)"
        )
    )

    parser.add_argument(
        "--platform",
        choices=sorted(MultiPlatformBuilder.PLATFORMS),
        help="Plataforma local esperada para build",
    )

    parser.add_argument(
        "--current-platform",
        action="store_true",
        dest="current_platform",
        help="Build da plataforma atual (sem cross-compilation)",
    )

    parser.add_argument(
        "--all",
        action="store_true",
        dest="current_platform",
        help="[DEPRECATED] use --current-platform",
    )

    parser.add_argument(
        "--apps",
        nargs="+",
        choices=["cli", "gui"],
        default=["cli", "gui"],
        help="Aplicacoes para construir",
    )

    parser.add_argument("--clean", action="store_true", help="Limpar builds anteriores")

    parser.add_argument(
        "--clean-all", action="store_true", help="Limpar todos os builds e ambientes"
    )

    parser.add_argument(
        "--debug", action="store_true", help="Modo debug com logs detalhados"
    )

    parser.add_argument(
        "--detect-platform",
        action="store_true",
        help="Detectar e mostrar plataforma atual",
    )

    parser.add_argument(
        "--list-platforms",
        action="store_true",
        help="Listar alvos conhecidos; build deve rodar no host correspondente",
    )

    parser.add_argument(
        "--skip-venv",
        action="store_true",
        help="Pular setup do ambiente virtual se ja existir",
    )

    parser.add_argument(
        "--runtime-db",
        type=Path,
        help="Embedar exatamente um data/ssas.db no bundle onedir",
    )

    parser.add_argument(
        "--auto-cleanup",
        action="store_true",
        help="Executar limpeza automatica apos build bem-sucedido",
    )

    parser.add_argument(
        "--auto-git",
        action="store_true",
        help="Executar commit e push automaticos apos build bem-sucedido",
    )

    parser.add_argument(
        "--git-message", type=str, help="Mensagem personalizada para commit automatico"
    )

    parser.add_argument(
        "--cleanup-online",
        action="store_true",
        help="Limpar arquivos desnecessarios do controle de versao online",
    )

    args = parser.parse_args(argv)

    # Configurar logging
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # Criar builder
    builder = MultiPlatformBuilder()

    # Comandos informativos
    if args.detect_platform:
        current = builder.detect_current_platform()
        if current:
            print(f"Plataforma atual detectada: {current}")
            platform_info = builder.PLATFORMS[current]
            print(f"Sistema: {platform_info['system']}")
            print(f"Arquitetura: {platform_info['arch']}")
        else:
            print("Erro: Nao foi possivel detectar a plataforma atual")
        return 0

    if args.list_platforms:
        print("Plataformas suportadas:")
        for platform_id, info in builder.PLATFORMS.items():
            print(f"  {platform_id}: {info['system']} {info['arch']}")
        return 0

    # Limpeza
    if args.clean_all:
        builder.clean()
        logger.info("Limpeza completa realizada")
        return 0

    if args.clean:
        if args.platform:
            builder.clean(args.platform)
        else:
            builder.clean()
        logger.info("Limpeza realizada")
        return 0

    # Limpeza online de arquivos desnecessarios
    if args.cleanup_online:
        logger.info("Executando limpeza de arquivos desnecessarios online...")
        builder.cleanup_online_unnecessary_files()
        logger.info("Limpeza online concluida")
        return 0

    # Determinar plataformas para build
    platforms_to_build = []

    if args.current_platform:
        # Build para plataforma atual apenas (cross-compilation complexa)
        current_platform = builder.detect_current_platform()
        if current_platform:
            platforms_to_build = [current_platform]
        else:
            logger.error("Nao foi possivel detectar plataforma atual")
            return 1
    elif args.platform:
        # Verificar se pode construir para plataforma especificada
        current_platform = builder.detect_current_platform()
        if args.platform == current_platform:
            platforms_to_build = [args.platform]
        else:
            logger.warning(
                f"Cross-compilation de {current_platform} para {args.platform} "
                "nao implementada. Use --current-platform para build da plataforma atual."
            )
            return 1
    else:
        # Build para plataforma atual
        current_platform = builder.detect_current_platform()
        if current_platform:
            platforms_to_build = [current_platform]
        else:
            logger.error("Nao foi possivel detectar plataforma atual")
            return 1

    # Executar builds
    success = True
    for plat in platforms_to_build:
        if not builder.build_platform(
            plat,
            args.apps,
            skip_venv=args.skip_venv,
            runtime_db=args.runtime_db,
        ):
            success = False

    if success:
        logger.info("Build concluido com sucesso!")
        logger.info(f"Executaveis disponiveis em: {builder.dist_dir}")

        # Operacoes pos-build automaticas
        if args.auto_cleanup:
            logger.info("Executando limpeza automatica...")
            builder.cleanup_build_artifacts()

        if args.auto_git:
            logger.info("Executando operacoes git automaticas...")
            if builder.git_add_commit_push(args.git_message):
                logger.info("Commit e push realizados com sucesso!")
            else:
                logger.warning("Problemas nas operacoes git - verifique manualmente")

        return 0
    else:
        logger.error("Build falhou")
        return 1


if __name__ == "__main__":
    sys.exit(main())
