#!/usr/bin/env python3
# ruff: noqa: E402
"""Teste leve de importacao com XLSX sintetico e banco temporario."""

import os
import sys
from pathlib import Path

import pandas as pd

# Adiciona o diretório raiz ao path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from armazenamento.database import (
    initialize_database,
    insert_dataframe_with_smart_upsert,
)
from extracao.extractor import extract_data_from_excel


def _write_import_workbook(path: Path, numero_ssa: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {
                "Numero SSA": numero_ssa,
                "Situacao": "ABERTA",
                "Setor Executor": "SMOKE",
                "Emitida Em": "01/01/2026",
                "Descricao": f"Smoke import {numero_ssa}",
            }
        ]
    ).to_excel(path, index=False)


def test_import_limited(tmp_path: Path):
    """Testa importacao com 3 arquivos XLSX reais gerados no teste."""
    docs_dir = tmp_path / "docs_entrada"
    arquivos_teste: list[Path] = []
    for index in range(3):
        path = docs_dir / f"Consulta SSA - 01-01-2026_010{index}AM.xlsx"
        _write_import_workbook(path, f"20269900{index}")
        arquivos_teste.append(path)

    db_path = tmp_path / "test_ssas.db"
    schema_path = Path(project_root) / "config" / "schema.sql"
    assert schema_path.exists(), f"Schema nao encontrado: {schema_path}"
    success = initialize_database(str(db_path), str(schema_path))
    assert success, "Falha ao inicializar banco de teste"

    total_registros = 0
    arquivos_ok = 0

    for file_path in arquivos_teste:
        print(f"  Importando: {file_path.name}")
        df = extract_data_from_excel(str(file_path))
        assert df is not None, f"Falha ao extrair: {file_path.name}"

        if not df.empty:
            success = insert_dataframe_with_smart_upsert(df, str(db_path))
            assert success, f"Falha ao inserir: {file_path.name}"
            total_registros += len(df)
            arquivos_ok += 1
            print(f"    [OK] {len(df)} registros")

    print(f"\n[RESULTADO] {arquivos_ok}/{len(arquivos_teste)} arquivos importados")
    print(f"[RESULTADO] {total_registros} registros totais")

    assert arquivos_ok == len(arquivos_teste), "Nem todos os arquivos foram importados"
    assert total_registros == len(arquivos_teste)
