#!/usr/bin/env python3
# ruff: noqa: E402
"""Run modular import in an isolated workspace by default."""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.app_logic import run_importer_logic


def progress_callback(event_type: str, data: dict[str, Any]) -> None:
    """Simple progress callback for testing."""
    if event_type == "start":
        print(f"Iniciando: {data.get('total', 0)} arquivos")
    elif event_type == "file_start":
        print(f"  [{data.get('current')}/{data.get('total')}] {data.get('filename')}")
    elif event_type == "file_success":
        print(f"    [OK] {data.get('records', 0)} registros")
    elif event_type == "file_error":
        print(f"    [ERRO] {data.get('error', 'Unknown')}")
    elif event_type == "finish":
        print(f"Concluido: {data.get('processed')}/{data.get('total')}")


def _run_modular_import(
    *,
    docs_dir: Path,
    data_dir: Path,
    db_name: str,
    force_import: bool,
) -> int:
    docs_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    print("=" * 80)
    print("TESTE DE IMPORTACAO MODULAR (SEM CLI)")
    print("=" * 80)
    print(f"Docs: {docs_dir}")
    print(f"Data: {data_dir / db_name}")
    print()
    try:
        result = run_importer_logic(
            docs_dir=str(docs_dir),
            data_dir=str(data_dir),
            db_name=db_name,
            table_name="ssa_table",
            force_import=force_import,
            progress_callback=progress_callback,
        )
    except Exception as exc:
        print("\n" + "=" * 80)
        print(f"[ERRO] Falha na importacao: {exc}")
        print("=" * 80)
        import traceback

        traceback.print_exc()
        return 1

    print("\n" + "=" * 80)
    if result:
        print("[SUCESSO] Importacao modular concluida")
    else:
        print("[INFO] Nenhum arquivo novo para processar")
    print("=" * 80)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docs-dir", help="Diretorio de entrada. Omitido usa temp.")
    parser.add_argument("--data-dir", help="Diretorio do banco. Omitido usa temp.")
    parser.add_argument("--db-name", default="ssas.db")
    parser.add_argument("--force-import", action="store_true")
    args = parser.parse_args(argv)
    if args.docs_dir or args.data_dir:
        if not (args.docs_dir and args.data_dir):
            parser.error("--docs-dir e --data-dir devem ser informados juntos")
        return _run_modular_import(
            docs_dir=Path(args.docs_dir).expanduser(),
            data_dir=Path(args.data_dir).expanduser(),
            db_name=str(args.db_name),
            force_import=bool(args.force_import),
        )
    with tempfile.TemporaryDirectory(prefix="ssa_modular_import_") as tmpdir:
        root = Path(tmpdir)
        return _run_modular_import(
            docs_dir=root / "docs_entrada",
            data_dir=root / "data",
            db_name=str(args.db_name),
            force_import=bool(args.force_import),
        )


if __name__ == "__main__":
    raise SystemExit(main())
