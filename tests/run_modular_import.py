#!/usr/bin/env python3
# ruff: noqa: E402
"""Test modular import without CLI."""

import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from core.app_logic import run_importer_logic

print("=" * 80)
print("TESTE DE IMPORTACAO MODULAR (SEM CLI)")
print("=" * 80)
print()


def progress_callback(event_type, data):
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


try:
    result = run_importer_logic(
        docs_dir="docs_entrada",
        data_dir="data",
        db_name="ssas.db",
        table_name="ssa_table",
        force_import=False,  # Only new files
        progress_callback=progress_callback,
    )

    print()
    print("=" * 80)
    if result:
        print("[SUCESSO] Importacao modular concluida")
    else:
        print("[INFO] Nenhum arquivo novo para processar")
    print("=" * 80)

except Exception as e:
    print()
    print("=" * 80)
    print(f"[ERRO] Falha na importacao: {e}")
    print("=" * 80)
    import traceback

    traceback.print_exc()
