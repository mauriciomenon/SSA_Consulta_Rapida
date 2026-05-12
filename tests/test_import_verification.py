#!/usr/bin/env python3
"""Teste leve de verificacao de importacao com XLSX sintetico."""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, ".")

from armazenamento.database import (
    get_db_connection,
    initialize_database,
    insert_dataframe_with_smart_upsert,
)
from core.app_logic import import_files_to_database
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


def _write_import_workbooks(docs_dir: Path, count: int) -> list[Path]:
    files: list[Path] = []
    for index in range(count):
        path = docs_dir / f"Consulta SSA - 01-01-2026_010{index}AM.xlsx"
        _write_import_workbook(path, f"20269910{index}")
        files.append(path)
    return files


def _count_imported_rows(db_path: Path) -> tuple[int, int]:
    with get_db_connection(str(db_path)) as conn:
        total = conn.execute("SELECT COUNT(*) FROM ssa_table").fetchone()[0]
        unique = conn.execute(
            "SELECT COUNT(DISTINCT numero_ssa) FROM ssa_table WHERE numero_ssa IS NOT NULL"
        ).fetchone()[0]
    return int(total), int(unique)


def test_import_few_files(tmp_path: Path):
    """Testa importacao de 3 arquivos XLSX reais gerados no teste."""
    temp_docs = tmp_path / "docs_entrada"
    db_path = tmp_path / "test_ssas.db"
    test_files = _write_import_workbooks(temp_docs, 3)

    print(f"DIR Testando com {len(test_files)} arquivos sinteticos")
    print("RUN Iniciando importacao...")
    success = import_files_to_database(str(temp_docs), str(db_path), force_import=True)
    assert success, "Falha na importacao"
    print("OK Importacao concluida")

    total, unique = _count_imported_rows(db_path)
    print(f"INFO Total de registros: {total}")
    print(f" SSAs unicas: {unique}")
    assert total == len(test_files)
    assert unique == len(test_files)


def test_upsert_logic_limited(tmp_path: Path):
    """Testa logica de upsert com XLSX gerado no teste."""
    file_path = tmp_path / "docs_entrada" / "Consulta SSA - 01-01-2026_0100AM.xlsx"
    _write_import_workbook(file_path, "202699200")
    db_path = tmp_path / "test_ssas.db"
    schema_path = Path("config/schema.sql")

    success = initialize_database(str(db_path), str(schema_path))
    assert success, "Falha ao inicializar banco"

    df = extract_data_from_excel(str(file_path))
    assert df is not None and not df.empty, "Falha ao extrair dados"

    success1 = insert_dataframe_with_smart_upsert(df, str(db_path))
    assert success1, "Falha na primeira insercao"
    count1, _unique1 = _count_imported_rows(db_path)
    print(f"  Primeira insercao: {count1} registros")

    success2 = insert_dataframe_with_smart_upsert(df, str(db_path))
    assert success2, "Falha na segunda insercao"
    count2, _unique2 = _count_imported_rows(db_path)

    print(f"  Segunda insercao: {count2} registros")
    print(f"  Diferenca: {count2 - count1}")

    assert count2 == count1, f"Upsert criou duplicatas: {count1} -> {count2}"
    print("OK Upsert funcionando corretamente")
