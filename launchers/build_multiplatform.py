#!/usr/bin/env python3
"""
SSA Consulta Rapida - Build System Multi-Plataforma
Compila executaveis para Windows, macOS e Linux com otimizacoes de tamanho.
Inclui limpeza automatica, commit e push apos build bem-sucedido.
"""

import argparse
import json
import logging
import os
import platform
import plistlib
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


# Configuracao de logging robusto
def setup_logging():
    """Configura logging com criacao automatica de diretorios"""
    log_dir = Path(__file__).parent / "logs"
    log_dir.mkdir(exist_ok=True)

    log_file = log_dir / "build.log"

    handlers: list[logging.Handler] = [logging.StreamHandler()]

    try:
        handlers.append(logging.FileHandler(str(log_file)))
    except Exception as e:
        print(f"Aviso: Nao foi possivel criar log file: {e}")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=handlers,
        force=True,  # Força reconfiguração se já existe
    )

    return logging.getLogger(__name__)


logger = setup_logging()


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

    def _load_version(self):
        """Carrega versao do arquivo config/version.json"""
        try:
            version_file = self.base_dir / "config" / "version.json"
            with open(version_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("version_short", "3.10")
        except Exception as e:
            logger.warning(f"Nao foi possivel carregar versao: {e}")
            return "3.10"

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
        else:
            logger.error(f"Plataforma nao suportada: {system} {machine}")
            return None

    def setup_virtual_environment(self, platform_name):
        """Setup do ambiente virtual usando uv."""
        venv_dir = self.platforms_dir / platform_name / "venv"
        requirements_file = self.platforms_dir / platform_name / "requirements.txt"

        # Determinar executaveis
        if platform_name.startswith("windows"):
            python_exe = venv_dir / "Scripts" / "python.exe"
        else:
            python_exe = venv_dir / "bin" / "python"

        # Verificar se venv ja existe e esta funcional
        if venv_dir.exists() and python_exe.exists():
            logger.info(f"Ambiente virtual existente encontrado: {venv_dir}")
            try:
                cmd = [self.uv_cmd, "pip", "list", "--python", str(python_exe)]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                if result.returncode == 0 and len(result.stdout.split("\n")) > 5:
                    logger.info("Ambiente virtual ja configurado e funcional")
                    return python_exe
            except Exception:
                logger.info("Ambiente virtual precisa ser recriado")

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
        result = subprocess.run(cmd, capture_output=True, text=True)
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
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logger.error("Erro instalando dependencias: %s", result.stderr.strip())
                return False

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
            result = subprocess.run(
                cmd, capture_output=True, text=True, cwd=str(self.base_dir)
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

    def build_executable(self, platform_name, app_type, python_exe, config):
        """Constroi executavel para tipo especifico (cli/gui)"""
        logger.info(f"Construindo {app_type.upper()} para {platform_name}")

        # Configuracao base
        app_config = config[f"{app_type}_config"]
        pyinstaller_args = config["pyinstaller_args"]

        # Aviso amigável sobre compressão UPX opcional (não bloqueante)
        if platform_name.startswith("windows"):
            # Heurística: se config pyinstaller_args contiver algo indicando compressão futura
            # (ex.: flag custom que adicionaremos no futuro) ou simplesmente sempre avisar se upx ausente
            try:
                __import__("upx4py")  # noqa: F401
            except Exception:
                logger.warning(
                    "UPX não detectado (pacote 'upx4py' ausente). Build seguirá sem compressão. "
                    "Para habilitar instale: uv pip install --python %s -r launchers/platforms/windows_amd64/requirements_windows_build.txt",
                    str(python_exe),
                )

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
        ]  # -y força sobrescrita

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
        data_path = self.base_dir / "data"
        add_data_sep = ";" if platform_name.startswith("windows") else ":"

        if config_path.exists():
            cmd.extend(["--add-data", f"{config_path}{add_data_sep}config"])
        include_local_data = bool(pyinstaller_args.get("include_local_data", False))
        if include_local_data and data_path.exists():
            logger.warning(
                "include_local_data ativado; data/ sera embedado no build. "
                "Use apenas em ambiente controlado."
            )
            cmd.extend(["--add-data", f"{data_path}{add_data_sep}data"])

        # Argumentos adicionais
        for arg in app_config.get("additional_args", []):
            cmd.append(arg)

        # Arquivo de entrada
        entry_file = self.launchers_dir / f"{app_type}_entry.py"
        cmd.append(str(entry_file))

        # Executar build
        logger.info(f"Executando: {' '.join(cmd)}")

        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=str(self.base_dir)
        )

        if result.returncode == 0:
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

        if not platform_dist.exists():
            logger.warning(f"Diretorio dist nao encontrado: {platform_dist}")
            return False

        # Compressao UPX (apenas Linux e Windows)
        if post_config.get("compress", False) and platform_name != "macos_arm64":
            self._compress_executables(platform_dist)

        if platform_name == "macos_arm64" and "gui" in apps_set:
            if not self._sync_macos_gui_display_name(platform_dist):
                return False

        # Criar manifesto
        self._create_manifest(platform_name, platform_dist)

        if platform_name == "macos_arm64" and package_mode == "dmg":
            if "gui" not in apps_set:
                logger.info("Build macOS sem app GUI; etapa de DMG foi pulada.")
                return True
            if not self._create_macos_dmg(platform_dist):
                return False
            # Regerar manifesto para incluir o arquivo DMG no inventario final.
            self._create_manifest(platform_name, platform_dist)

        return True

    def _find_macos_gui_app(self, dist_dir):
        """Localiza o bundle .app principal da GUI para empacotamento DMG."""
        expected = dist_dir / f"SSA_GUI_v{self.version}_macos_arm64.app"
        if expected.exists() and expected.is_dir():
            return expected

        candidates = sorted(
            (path for path in dist_dir.glob("SSA_GUI_*.app") if path.is_dir()),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        if candidates:
            return candidates[0]
        return None

    def _sync_macos_gui_display_name(self, dist_dir):
        """Atualiza CFBundleName e CFBundleDisplayName do app GUI no macOS."""
        app_bundle = self._find_macos_gui_app(dist_dir)
        if app_bundle is None:
            logger.error(
                "Bundle .app da GUI nao encontrado para atualizar nome em %s", dist_dir
            )
            return False

        info_plist_path = app_bundle / "Contents" / "Info.plist"
        if not info_plist_path.exists():
            logger.error("Info.plist nao encontrado no bundle GUI: %s", info_plist_path)
            return False

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

    def _create_macos_dmg(self, dist_dir):
        """Gera instalador DMG a partir do bundle .app da GUI."""
        hdiutil_cmd = shutil.which("hdiutil")
        if not hdiutil_cmd:
            logger.error("hdiutil nao encontrado; nao foi possivel gerar DMG")
            return False

        app_bundle = self._find_macos_gui_app(dist_dir)
        if app_bundle is None:
            logger.error("Bundle .app da GUI nao encontrado em %s", dist_dir)
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
        result = subprocess.run(
            cmd,
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
                    subprocess.run(
                        [upx_cmd, "--best", str(exe_file)], capture_output=True
                    )
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
                size_bytes = self._compute_directory_size_bytes(artifact)
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
        for path in directory.rglob("*"):
            if path.is_symlink():
                continue
            if path.is_file():
                try:
                    total += path.stat().st_size
                except OSError:
                    # Ignore transient or permission failures while scanning artifact trees.
                    continue
        return total

    def build_platform(self, platform_name, apps=None):
        """Constroi executaveis para uma plataforma especifica"""
        if platform_name not in self.PLATFORMS:
            logger.error(f"Plataforma nao suportada: {platform_name}")
            return False

        logger.info(f"Iniciando build para {platform_name}")

        # Configurar ambiente
        python_exe = self.setup_virtual_environment(platform_name)
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
            if not self.build_executable(platform_name, app_type, python_exe, config):
                success = False

        # Pos-processamento
        if success:
            success = self.post_process(platform_name, config, apps=apps)

        return success

    def cleanup_build_artifacts(self):
        """Remove artefatos de build desnecessarios apos build bem-sucedido"""
        logger.info("Iniciando limpeza automatica de artefatos de build...")

        cleanup_count = 0

        # 1. Remover arquivos de cache Python
        cache_patterns = [
            "**/__pycache__",
            "**/*.pyc",
            "**/*.pyo",
            "**/.pytest_cache",
            "**/build",
            "**/dist",
            "**/*.egg-info",
        ]

        for pattern in cache_patterns:
            for path in self.base_dir.glob(pattern):
                if path.exists():
                    if path.is_dir():
                        shutil.rmtree(path)
                        logger.debug(f"Removido diretorio: {path}")
                    else:
                        path.unlink()
                        logger.debug(f"Removido arquivo: {path}")
                    cleanup_count += 1

        # 2. Remover logs antigos (manter apenas os 5 mais recentes)
        logs_dir = self.launchers_dir / "logs"
        if logs_dir.exists():
            log_files = sorted(
                logs_dir.glob("*.log"), key=lambda x: x.stat().st_mtime, reverse=True
            )
            for log_file in log_files[5:]:  # Remove logs alem dos 5 mais recentes
                log_file.unlink()
                logger.debug(f"Log antigo removido: {log_file}")
                cleanup_count += 1

        # 3. Remover arquivos temporarios do PyInstaller
        for temp_pattern in ["build", "*.spec"]:
            for temp_path in self.base_dir.glob(temp_pattern):
                if temp_path.exists():
                    if temp_path.is_dir():
                        shutil.rmtree(temp_path)
                    else:
                        temp_path.unlink()
                    cleanup_count += 1

        # 4. Limpar arquivos temporarios do sistema
        temp_patterns = [
            "**/.DS_Store",  # macOS
            "**/Thumbs.db",  # Windows
            "**/*.tmp",
            "**/*.temp",
        ]

        for pattern in temp_patterns:
            for temp_file in self.base_dir.glob(pattern):
                if temp_file.exists():
                    temp_file.unlink()
                    logger.debug(f"Arquivo temporario removido: {temp_file}")
                    cleanup_count += 1

        # 5. Limpar dist_simple (builds de desenvolvimento)
        dist_simple = self.launchers_dir / "dist_simple"
        if dist_simple.exists():
            shutil.rmtree(dist_simple)
            logger.info("Diretorio dist_simple removido")
            cleanup_count += 1

        logger.info(f"Limpeza concluida: {cleanup_count} itens removidos")
        return cleanup_count > 0

    def git_add_commit_push(self, custom_message=None):
        """Adiciona, commita e faz push das alteracoes para o git"""
        logger.info("Iniciando operacoes git...")

        try:
            # Verificar se estamos em um repositorio git
            result = subprocess.run(
                ["git", "status"],
                capture_output=True,
                text=True,
                cwd=str(self.base_dir),
            )
            if result.returncode != 0:
                logger.error("Nao e um repositorio git valido")
                return False

            # Verificar se ha alteracoes para commit
            result = subprocess.run(
                ["git", "status", "--porcelain"],
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
                "launchers/*.md",
                "config/*.json",
                "docs/*.md",
                "*.py",
                "*.md",
                "requirements.txt",
                "pyproject.toml",
            ]

            for file_pattern in files_to_add:
                subprocess.run(
                    ["git", "add", file_pattern],
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
            result = subprocess.run(
                ["git", "commit", "-m", commit_message],
                capture_output=True,
                text=True,
                cwd=str(self.base_dir),
            )

            if result.returncode == 0:
                logger.info(f"Commit realizado: {commit_message}")
            else:
                logger.warning(f"Nada para commitar ou erro: {result.stderr}")

            # Push
            result = subprocess.run(
                ["git", "push"], capture_output=True, text=True, cwd=str(self.base_dir)
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

        # Arquivos que devem ser removidos do controle de versao se existirem
        unnecessary_files = [
            # Executaveis
            "launchers/dist/**/*",
            "launchers/dist_simple/**/*",
            # Logs
            "launchers/logs/*.log",
            "logs/*.log",
            # Cache e temporarios
            "data/file_cache.json",
            "**/__pycache__/**/*",
            "**/*.pyc",
            "**/*.pyo",
            "**/build/**/*",
            "**/dist/**/*",
            "**/*.egg-info/**/*",
            # Arquivos de sistema
            "**/.DS_Store",
            "**/Thumbs.db",
            "**/*.tmp",
            "**/*.temp",
            # Backups de banco
            "data/*.backup_*",
            "data/historico_backups/**/*",
        ]

        files_removed = []
        for pattern in unnecessary_files:
            for file_path in self.base_dir.glob(pattern):
                if file_path.exists() and file_path.is_file():
                    try:
                        # Verificar se o arquivo esta sendo rastreado pelo git
                        result = subprocess.run(
                            ["git", "ls-files", str(file_path)],
                            capture_output=True,
                            text=True,
                            cwd=str(self.base_dir),
                        )

                        if result.stdout.strip():  # Arquivo esta sendo rastreado
                            subprocess.run(
                                ["git", "rm", "--cached", str(file_path)],
                                capture_output=True,
                                text=True,
                                cwd=str(self.base_dir),
                            )
                            files_removed.append(str(file_path))
                            logger.debug(f"Removido do git: {file_path}")
                    except Exception as e:
                        logger.debug(f"Erro removendo {file_path}: {e}")

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

            for platform in self.PLATFORMS:
                platform_dir = self.platforms_dir / platform
                venv_dir = platform_dir / "venv"
                temp_dir = platform_dir / "temp"

                for dir_path in [venv_dir, temp_dir]:
                    if dir_path.exists():
                        shutil.rmtree(dir_path)


def main():
    """Funcao principal"""
    parser = argparse.ArgumentParser(
        description="Build System Multi-Plataforma SSA Consulta Rapida"
    )

    parser.add_argument(
        "--platform",
        choices=["windows_amd64", "macos_arm64", "debian_amd64"],
        help="Plataforma especifica para build",
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Build de todos os apps da plataforma atual (sem cross-compilation)",
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
        help="Listar todas as plataformas suportadas",
    )

    parser.add_argument(
        "--skip-venv",
        action="store_true",
        help="Pular setup do ambiente virtual se já existir",
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

    args = parser.parse_args()

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

    if args.all:
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
                "nao implementada. Use --all para build da plataforma atual."
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
        if not builder.build_platform(plat, args.apps):
            success = False

    if success:
        logger.info("Build concluido com sucesso!")
        logger.info(f"Executaveis disponiveis em: {builder.dist_dir}")

        # Operacoes pos-build automaticas
        if args.auto_cleanup:
            logger.info("Executando limpeza automatica...")
            builder.cleanup_build_artifacts()

        if args.cleanup_online:
            logger.info("Limpando arquivos desnecessarios online...")
            builder.cleanup_online_unnecessary_files()

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
