#!/usr/bin/env python3
"""
Build simplificado para gerar executaveis locais.
IMPORTANTE: Este script usa dist_simple que e temporario e NAO deve ir para o git!
"""

import atexit
from pathlib import Path
import shutil
import subprocess
import sys

if __package__ != "launchers":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    __package__ = "launchers"

from .smoke_validation import cli_executable_path, run_cli_import_smoke  # noqa: E402
from .version_info import REPO_ROOT, get_current_version  # noqa: E402

APP_VERSION = get_current_version()


def cleanup_dist_simple():
    """Funcao para limpar dist_simple ao sair"""
    dist_dir = REPO_ROOT / "launchers" / "dist_simple"
    if dist_dir.exists():
        try:
            shutil.rmtree(dist_dir)
            print(f"CLEAN Limpeza automática: {dist_dir} removido")
        except Exception as e:
            print(f"WARN  Erro na limpeza: {e}")


def main():
    print(f"=== SSA Consulta Rapida v{APP_VERSION} - Build Simples ===")
    print("WARN  AVISO: dist_simple é temporário e será limpo automaticamente!")

    # Registrar limpeza automática
    atexit.register(cleanup_dist_simple)

    # Diretórios
    base_dir = REPO_ROOT
    dist_dir = base_dir / "launchers" / "dist_simple"

    # Limpar build anterior
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    dist_dir.mkdir(parents=True, exist_ok=True)

    print(f"Base dir: {base_dir}")
    print(f"Dist dir: {dist_dir}")

    # Comando PyInstaller simples e FUNCIONAL
    cmd_cli = [
        "pyinstaller",
        "--onedir",
        "--console",
        "--name",
        f"SSA_CLI_v{APP_VERSION}_SIMPLES",
        "--distpath",
        str(dist_dir),
        "--workpath",
        str(dist_dir / "temp"),
        "--specpath",
        str(dist_dir),
        "--paths",
        str(base_dir),  # IMPORTANTE: path do projeto
        "--add-data",
        f"{base_dir}/config:config",
        "--add-data",
        f"{base_dir}/data:data",
        "--hidden-import",
        "pandas._libs.tslibs.base",
        "--hidden-import",
        "pandas._libs.tslibs.nattype",
        "--hidden-import",
        "openpyxl.descriptors.serialisable",
        str(base_dir / "launchers" / "cli_entry.py"),
    ]

    print("\\n=== Executando PyInstaller CLI ===")
    print(f"Comando: {' '.join(cmd_cli)}")

    try:
        subprocess.run(
            cmd_cli, cwd=base_dir, check=True, capture_output=True, text=True
        )
        print("OK Build CLI concluído com sucesso!")

        # Testar executavel com importacao XLSX real.
        exe_path = cli_executable_path(REPO_ROOT, APP_VERSION, simple=True)
        if exe_path.exists():
            print(f"OK Executavel gerado: {exe_path}")

            smoke_result = run_cli_import_smoke(executable=exe_path, repo_root=REPO_ROOT)

            if not smoke_result.ok:
                print(f"ERR Smoke funcional falhou: {smoke_result.details()}")
                return 1
            print(
                "OK Smoke funcional importou "
                f"{smoke_result.imported_rows} linha(s)"
            )
            print(f"Tamanho: {exe_path.stat().st_size / (1024 * 1024):.1f}M")
        else:
            print(f"ERR Executavel nao encontrado em: {exe_path}")
            return 1

    except subprocess.CalledProcessError as e:
        print(f"ERR Erro no build: {e}")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        return 1
    except Exception as e:
        print(f"ERR Erro inesperado: {e}")
        return 1

    print("\\nDONE BUILD SIMPLES COMPLETADO!")
    print("CLEAN dist_simple será limpo automaticamente ao sair")
    return 0


if __name__ == "__main__":
    sys.exit(main())
