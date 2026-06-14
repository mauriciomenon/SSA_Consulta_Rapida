#!/usr/bin/env python3
# ruff: noqa: E402
"""Quick isolated test of import corrections."""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def _run_quick_import(db_path: Path) -> int:
    import pandas as pd

    from armazenamento.database import query_db
    from armazenamento.database_optimized import insert_dataframe_optimized

    print("=" * 80)
    print("TESTE RAPIDO DAS CORRECOES DE IMPORTACAO")
    print("=" * 80)
    print(f"\n[INFO] Banco de teste: {db_path}")

    test_df = pd.DataFrame(
        {
            "numero_ssa": ["TEST001", "TEST002"],
            "data_cadastro": ["2025-01-01", "2025-01-02"],
            "descricao_ssa": ["Teste 1", "Teste 2"],
        }
    )
    db_path.parent.mkdir(parents=True, exist_ok=True)

    print("\n[TEST 1] Testando criacao de tabela quando nao existe...")
    if not insert_dataframe_optimized(test_df, str(db_path), "ssa_table"):
        print("  [ERRO] Falha ao inserir dados")
        return 1
    print("  [OK] Dados inseridos com sucesso em tabela nova")

    print("\n[TEST 2] Verificando se dados foram inseridos...")
    df = query_db(str(db_path), "ssas")
    if df is None or len(df) != 2:
        print(f"  [ERRO] Esperado 2 registros, encontrado {len(df) if df is not None else 0}")
        return 1
    print(f"  [OK] {len(df)} registros encontrados no banco")

    print("\n[TEST 3] Testando segunda insercao (tabela existe)...")
    test_df2 = pd.DataFrame(
        {
            "numero_ssa": ["TEST003"],
            "data_cadastro": ["2025-01-03"],
            "descricao_ssa": ["Teste 3"],
        }
    )
    if not insert_dataframe_optimized(test_df2, str(db_path), "ssa_table"):
        print("  [ERRO] Falha ao inserir dados")
        return 1

    df = query_db(str(db_path), "ssas")
    if df is None or len(df) != 3:
        print(f"  [ERRO] Esperado 3 registros, encontrado {len(df) if df is not None else 0}")
        return 1

    print(f"  [OK] Total de {len(df)} registros no banco")
    print("\n" + "=" * 80)
    print("[CONCLUIDO] Testes rapidos completos")
    print("=" * 80)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--db-path",
        help="Banco de teste. Se omitido, usa diretorio temporario isolado.",
    )
    args = parser.parse_args(argv)
    if args.db_path:
        return _run_quick_import(Path(args.db_path).expanduser())
    with tempfile.TemporaryDirectory(prefix="ssa_quick_import_") as tmpdir:
        return _run_quick_import(Path(tmpdir) / "ssas.db")


if __name__ == "__main__":
    raise SystemExit(main())
