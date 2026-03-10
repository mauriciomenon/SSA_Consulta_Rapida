#!/usr/bin/env python3
"""
Script para copiar dados (DB e Excel) para builds, facilitando distribuicao.

Copia automaticamente:
- Database principal (ssas.db) para data/
- Arquivos Excel mais recentes de docs_entrada/

Uso:
    python scripts/copy_data_to_builds.py --build-system pyinstaller --allow-local-data
    python scripts/copy_data_to_builds.py --build-system pyoxidizer --allow-local-data
    python scripts/copy_data_to_builds.py --build-system nuitka --allow-local-data
    python scripts/copy_data_to_builds.py --all --allow-local-data  # Copia para todos os builds
"""

import argparse
import shutil
from pathlib import Path
import sys

PYINSTALLER_CANONICAL_DIRS = (
    "launchers/dist/windows_amd64",
    "launchers/dist/macos_arm64",
    "launchers/dist/debian_amd64",
)


def resolve_target_build_dirs(base_dir: Path, build_system: str) -> list[Path]:
    """Resolve diretorios de destino para copia de dados."""
    targets: list[Path] = []

    if build_system == "pyinstaller":
        for rel_path in PYINSTALLER_CANONICAL_DIRS:
            candidate = base_dir / rel_path
            if candidate.exists():
                targets.append(candidate)
        if targets:
            return targets

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

    # Diretorio base do projeto (independente do cwd)
    base_dir = Path(__file__).resolve().parents[1]
    # Defaults (relativos ao base_dir)
    db_path = db_path or (base_dir / "data" / "ssas.db")
    docs_dir = docs_dir or (base_dir / "docs_entrada")
    max_excel_files = 3 if max_excel_files is None else max_excel_files

    # 1. Copiar database principal
    source_db = db_path
    if source_db.exists():
        # Safety check: skip large databases to avoid distributing sensitive data
        db_size_mb = source_db.stat().st_size / (1024 * 1024)
        if db_size_mb > 100:
            if verbose:
                print(f"WARN  Pulando DB grande ({db_size_mb:.1f} MB) - risco de dados sensiveis")
            return False

        target_data_dir = build_dir / "data"
        target_data_dir.mkdir(exist_ok=True)
        target_db = target_data_dir / "ssas.db"

        if verbose:
            print(f"PKG Copiando DB: {source_db} -> {target_db}")
        try:
            shutil.copy2(source_db, target_db)
            size_mb = target_db.stat().st_size / (1024 * 1024)
            if verbose:
                print(f"    DB copiado ({size_mb:.1f} MB)")
        except Exception as e:
            print(f"   ERR Erro ao copiar DB: {e}")
            success = False
    else:
        if verbose:
            print(f"WARN  DB nao encontrado: {source_db}")

    # 2. Copiar Excel samples (até 3 mais recentes)
    docs_entrada = docs_dir
    if docs_entrada.exists():
        target_docs = build_dir / "docs_entrada"
        target_docs.mkdir(exist_ok=True)

        # Buscar arquivos Excel ordenados por data de modificacao (mais recentes primeiro)
        excel_files = sorted(
            docs_entrada.glob("*.xlsx"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )

        # Copiar ate N arquivos mais recentes
        copied_count = 0
        max_files = max_excel_files

        if verbose and excel_files:
            print(f"INFO Copiando Excel samples (maximo {max_files}):")

        for excel_file in excel_files[:max_files]:
            target_excel = target_docs / excel_file.name
            try:
                shutil.copy2(excel_file, target_excel)
                size_kb = target_excel.stat().st_size / 1024
                if verbose:
                    print(f"    {excel_file.name} ({size_kb:.0f} KB)")
                copied_count += 1
            except Exception as e:
                print(f"   ERR Erro ao copiar {excel_file.name}: {e}")
                success = False

        if verbose and copied_count > 0:
            print(f"   Total: {copied_count} arquivo(s) Excel copiado(s)")
    else:
        if verbose:
            print("WARN  Diretorio docs_entrada nao encontrado")

    return success


def main():
    parser = argparse.ArgumentParser(
        description="Copia dados (DB e Excel) para builds"
    )
    parser.add_argument(
        "--build-system",
        choices=["pyinstaller", "pyoxidizer", "nuitka"],
        help="Build system especifico para copiar dados"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Copiar para todos os builds existentes"
    )
    parser.add_argument(
        "--db-path",
        default="data/ssas.db",
        help="Caminho para o arquivo do banco de dados (default: data/ssas.db)"
    )
    parser.add_argument(
        "--docs-dir",
        default="docs_entrada",
        help="Diretorio de entrada de documentos Excel (default: docs_entrada)"
    )
    parser.add_argument(
        "--max-excels",
        type=int,
        default=3,
        help="Quantidade maxima de arquivos Excel para copiar (default: 3)"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Modo silencioso (menos output)"
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
                print(f"WARN Build directory not found: {target_dirs[0]}")
            return 1
        for build_dir in existing_dirs:
            if verbose:
                print("=" * 60)
                print(f"Copiando dados para build: {args.build_system.upper()} -> {build_dir}")
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
