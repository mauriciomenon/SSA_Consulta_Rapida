#!/usr/bin/env python3
"""
Script para copiar dados (DB e Excel) para builds, facilitando distribuicao.

Copia automaticamente:
- Database principal (ssas.db) para data/
- Arquivos Excel mais recentes de docs_entrada/

Uso:
    uv run --python 3.13 scripts/copy_data_to_builds.py --build-system pyinstaller --allow-local-data
    uv run --python 3.13 scripts/copy_data_to_builds.py --build-system pyoxidizer --allow-local-data
    uv run --python 3.13 scripts/copy_data_to_builds.py --build-system nuitka --allow-local-data
    uv run --python 3.13 scripts/copy_data_to_builds.py --all --allow-local-data  # Copia para todos os builds
"""

import argparse
import importlib
import os
import shutil
import sqlite3
import sys
import tempfile
from contextlib import closing
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

MultiPlatformBuilder = importlib.import_module(
    "launchers.build_multiplatform"
).MultiPlatformBuilder
_SUPPORTED_PLATFORMS = tuple(sorted(MultiPlatformBuilder.PLATFORMS))

PYINSTALLER_CANONICAL_DIRS = tuple(
    f"launchers/dist/{platform}" for platform in _SUPPORTED_PLATFORMS
)
PYINSTALLER_EQUIVALENT_DIRS = tuple(
    f"builds/pyinstaller/{platform}" for platform in _SUPPORTED_PLATFORMS
)
NUITKA_PLATFORM_DIRS = tuple(
    f"builds/nuitka/{platform}" for platform in _SUPPORTED_PLATFORMS
)
PYOXIDIZER_PLATFORM_DIRS = tuple(
    f"builds/pyoxidizer/{platform}" for platform in _SUPPORTED_PLATFORMS
)


def _looks_like_runtime_dir(candidate: Path) -> bool:
    """Retorna True quando a pasta parece ser um runtime executavel."""
    if not candidate.is_dir():
        return False

    if candidate.name.endswith(".dist"):
        return True

    if candidate.name.startswith("SSA_"):
        for child in candidate.iterdir():
            if child.is_file() and child.stem == candidate.name:
                return True
        if (candidate / "_internal").is_dir():
            return True

    return False


def _resolve_runtime_dirs(build_dir: Path) -> list[Path]:
    """Resolve diretorios que devem receber config/data/docs no build."""
    runtime_dirs: list[Path] = []
    try:
        for child in build_dir.iterdir():
            if _looks_like_runtime_dir(child):
                runtime_dirs.append(child)
    except OSError:
        return []

    if not runtime_dirs:
        runtime_dirs = [build_dir]

    dedup: list[Path] = []
    for item in runtime_dirs:
        if item not in dedup:
            dedup.append(item)
    return dedup


def resolve_target_build_dirs(base_dir: Path, build_system: str) -> list[Path]:
    """Resolve diretorios de destino para copia de dados."""
    targets: list[Path] = []

    if build_system == "pyinstaller":
        for rel_path in PYINSTALLER_CANONICAL_DIRS + PYINSTALLER_EQUIVALENT_DIRS:
            candidate = base_dir / rel_path
            if candidate.exists():
                targets.append(candidate)
        if targets:
            return targets
        return [base_dir / rel for rel in PYINSTALLER_CANONICAL_DIRS]

    if build_system == "nuitka":
        for rel_path in NUITKA_PLATFORM_DIRS:
            candidate = base_dir / rel_path
            if candidate.exists():
                targets.append(candidate)
        if targets:
            return targets
        return [base_dir / rel for rel in NUITKA_PLATFORM_DIRS]

    if build_system == "pyoxidizer":
        platform_targets: list[Path] = []
        for rel_path in PYOXIDIZER_PLATFORM_DIRS:
            candidate = base_dir / rel_path
            if candidate.exists():
                platform_targets.append(candidate)
        if platform_targets:
            return platform_targets
        legacy_dir = base_dir / "builds" / "pyoxidizer"
        if legacy_dir.exists():
            return [legacy_dir]
        return [base_dir / rel for rel in PYOXIDIZER_PLATFORM_DIRS]

    legacy_dir = base_dir / "builds" / build_system
    return [legacy_dir]


def copy_data_to_build(
    build_dir: Path,
    verbose: bool = True,
    db_path: Path | None = None,
    docs_dir: Path | None = None,
    max_excel_files: int | None = None,
):
    """Copia database e Excel samples para diretorio de build."""
    if not build_dir.exists():
        print(f"ERR Build nao encontrado: {build_dir}")
        return False

    success = True
    runtime_dirs = _resolve_runtime_dirs(build_dir)
    if not runtime_dirs:
        if verbose:
            print(f"WARN  Nenhum runtime acessivel para copia: {build_dir}")
        return False

    # Diretorio base do projeto (independente do cwd)
    base_dir = Path(__file__).resolve().parents[1]
    # Defaults (relativos ao base_dir)
    db_path = db_path or (base_dir / "data" / "ssas.db")
    docs_dir = docs_dir or (base_dir / "docs_entrada")
    config_dir = base_dir / "config"
    max_excel_files = 3 if max_excel_files is None else max_excel_files

    # 1. Validar DB local uma vez
    source_db = db_path
    db_ok = source_db.exists()
    db_size_mb = 0.0
    if db_ok:
        db_size_mb = source_db.stat().st_size / (1024 * 1024)
        if db_size_mb > 100:
            if verbose:
                print(
                    f"WARN  Pulando DB grande ({db_size_mb:.1f} MB) - risco de dados sensiveis"
                )
            db_ok = False
            success = False

    if not db_ok and verbose:
        print(f"WARN  DB nao encontrado: {source_db}")

    # 2. Coletar excels uma vez
    docs_entrada = docs_dir
    excel_files: list[tuple[Path, float, float]] = []
    if docs_entrada.exists():
        excel_files = sorted(
            (
                (
                    path,
                    stat_result.st_size / 1024,
                    stat_result.st_mtime,
                )
                for path in docs_entrada.glob("*.xlsx")
                for stat_result in [path.stat()]
            ),
            key=lambda item: item[2],
            reverse=True,
        )
    elif verbose:
        print("WARN  Diretorio docs_entrada nao encontrado")

    config_available = config_dir.exists()
    if not config_available and verbose:
        print(f"WARN  Diretorio config nao encontrado: {config_dir}")

    if verbose and (db_ok or excel_files):
        print(
            "WARN  Revise se DB e planilhas contem dados sensiveis antes de distribuir o build"
        )

    staged_config_dir: Path | None = None
    with tempfile.TemporaryDirectory(prefix="ssa_copy_config_") as stage_dir_str:
        if config_available and len(runtime_dirs) > 1:
            staged_config_dir = Path(stage_dir_str) / "config"
            try:
                shutil.copytree(config_dir, staged_config_dir, dirs_exist_ok=True)
            except Exception as e:
                print(f"   ERR Erro ao preparar stage de config: {e}")
                success = False
                staged_config_dir = None

        for runtime_dir in runtime_dirs:
            target_data_dir = runtime_dir / "data"
            target_docs_entrada_dir = runtime_dir / "docs_entrada"
            target_docs_saida_dir = runtime_dir / "docs_saida"
            target_config_dir = runtime_dir / "config"
            target_data_dir.mkdir(exist_ok=True)
            target_docs_entrada_dir.mkdir(exist_ok=True)
            target_docs_saida_dir.mkdir(exist_ok=True)

            if config_available:
                copy_source_dir = staged_config_dir or config_dir
                try:
                    shutil.copytree(
                        copy_source_dir, target_config_dir, dirs_exist_ok=True
                    )
                    if verbose:
                        print(
                            f"CFG Config copiado: {copy_source_dir} -> {target_config_dir}"
                        )
                except Exception as e:
                    print(f"   ERR Erro ao copiar config para {runtime_dir}: {e}")
                    success = False

            if db_ok:
                target_db = target_data_dir / "ssas.db"
                temporary_db = target_db.with_name(f"{target_db.name}.tmp")
                if verbose:
                    print(f"PKG Copiando DB: {source_db} -> {target_db}")
                try:
                    temporary_db.unlink(missing_ok=True)
                    source_uri = f"{source_db.resolve().as_uri()}?mode=ro"
                    with closing(
                        sqlite3.connect(source_uri, uri=True, timeout=5)
                    ) as source_conn:
                        with closing(sqlite3.connect(temporary_db)) as target_conn:
                            source_conn.backup(target_conn)
                            if target_conn.execute("PRAGMA quick_check").fetchone() != (
                                "ok",
                            ):
                                raise sqlite3.DatabaseError(
                                    "snapshot do banco falhou no quick_check"
                                )
                    os.replace(temporary_db, target_db)
                    if verbose:
                        print(f"    DB copiado ({db_size_mb:.1f} MB)")
                except (OSError, sqlite3.Error) as e:
                    temporary_db.unlink(missing_ok=True)
                    print(f"   ERR Erro ao copiar DB para {runtime_dir}: {e}")
                    success = False

            copied_count = 0
            if verbose and excel_files:
                print(
                    f"INFO Copiando Excel samples para {runtime_dir} (maximo {max_excel_files}):"
                )

            for excel_file, excel_size_kb, _excel_mtime in excel_files[
                :max_excel_files
            ]:
                target_excel = target_docs_entrada_dir / excel_file.name
                try:
                    shutil.copy2(excel_file, target_excel)
                    if verbose:
                        print(f"    {excel_file.name} ({excel_size_kb:.0f} KB)")
                    copied_count += 1
                except Exception as e:
                    print(
                        f"   ERR Erro ao copiar {excel_file.name} para {runtime_dir}: {e}"
                    )
                    success = False

            if verbose and copied_count > 0:
                print(f"   Total: {copied_count} arquivo(s) Excel copiado(s)")

    return success


def main():
    parser = argparse.ArgumentParser(description="Copia dados (DB e Excel) para builds")
    parser.add_argument(
        "--build-system",
        choices=["pyinstaller", "pyoxidizer", "nuitka"],
        help="Build system especifico para copiar dados",
    )
    parser.add_argument(
        "--all", action="store_true", help="Copiar para todos os builds existentes"
    )
    parser.add_argument(
        "--db-path",
        default="data/ssas.db",
        help="Caminho para o arquivo do banco de dados (default: data/ssas.db)",
    )
    parser.add_argument(
        "--docs-dir",
        default="docs_entrada",
        help="Diretorio de entrada de documentos Excel (default: docs_entrada)",
    )
    parser.add_argument(
        "--max-excels",
        type=int,
        default=3,
        help="Quantidade maxima de arquivos Excel para copiar (default: 3)",
    )
    parser.add_argument(
        "--quiet", action="store_true", help="Modo silencioso (menos output)"
    )
    parser.add_argument(
        "--allow-local-data",
        action="store_true",
        help="Confirma explicitamente que dados locais podem ser copiados para build",
    )

    args = parser.parse_args()

    if not args.build_system and not args.all:
        parser.error("Especifique --build-system ou --all")

    verbose = not args.quiet
    if verbose:
        print(
            "WARN Este utilitario copia dados locais para diretorios de build. "
            "Use apenas em ambiente controlado."
        )
    if not args.allow_local_data:
        print(
            "ERR Operacao bloqueada por seguranca. Use --allow-local-data para confirmar."
        )
        return 2

    # Diretorio base do projeto (independente do cwd)
    base_dir = Path(__file__).resolve().parents[1]
    db_path_arg = Path(args.db_path)
    docs_dir_arg = Path(args.docs_dir)
    if not db_path_arg.is_absolute():
        db_path_arg = (base_dir / db_path_arg).resolve()
    if not docs_dir_arg.is_absolute():
        docs_dir_arg = (base_dir / docs_dir_arg).resolve()

    # Mapeamento de build system para diretorios (ancorado ao base_dir)
    build_dirs = {
        "pyinstaller": resolve_target_build_dirs(base_dir, "pyinstaller"),
        "pyoxidizer": resolve_target_build_dirs(base_dir, "pyoxidizer"),
        "nuitka": resolve_target_build_dirs(base_dir, "nuitka"),
    }

    overall_success = True

    if args.all:
        if verbose:
            print("=" * 60)
            print("Copiando dados para TODOS os builds encontrados")
            print("=" * 60)

        for build_system, target_dirs in build_dirs.items():
            existing_dirs = [path for path in target_dirs if path.exists()]
            if not existing_dirs:
                if verbose:
                    print(f"\nSKIP Pulando {build_system} (build nao encontrado)")
                continue

            for build_dir in existing_dirs:
                if verbose:
                    print(f"\nFIX Build: {build_system.upper()} -> {build_dir}")
                    print("-" * 60)
                success = copy_data_to_build(
                    build_dir,
                    verbose,
                    db_path=db_path_arg,
                    docs_dir=docs_dir_arg,
                    max_excel_files=args.max_excels,
                )
                overall_success = overall_success and success
    else:
        target_dirs = build_dirs[args.build_system]
        existing_dirs = [path for path in target_dirs if path.exists()]
        if not existing_dirs:
            if verbose:
                expected_targets = ", ".join(str(path) for path in target_dirs)
                print(
                    "WARN Nenhum diretorio de build encontrado entre os candidatos: "
                    f"{expected_targets}"
                )
            return 1
        for build_dir in existing_dirs:
            if verbose:
                print("=" * 60)
                print(
                    f"Copiando dados para build: {args.build_system.upper()} -> {build_dir}"
                )
                print("=" * 60)
                print()
            success = copy_data_to_build(
                build_dir,
                verbose,
                db_path=db_path_arg,
                docs_dir=docs_dir_arg,
                max_excel_files=args.max_excels,
            )
            overall_success = overall_success and success

    if verbose:
        print()
        print("=" * 60)
        if overall_success:
            print("OK Copia concluida com sucesso!")
        else:
            print("WARN  Copia concluida com alguns erros")
        print("=" * 60)

    return 0 if overall_success else 1


if __name__ == "__main__":
    sys.exit(main())
