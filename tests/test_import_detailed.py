#!/usr/bin/env python3
# ruff: noqa: E402
"""
Teste LEVE de importação - usa apenas 3 arquivos para validação rápida.
Para teste completo, use: python tests/run_import_detailed.py
"""

import os
import shutil
import sys
import tempfile

# Adiciona o diretório raiz ao path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from armazenamento.database import (
    initialize_database,
    insert_dataframe_with_smart_upsert,
)
from extracao.extractor import extract_data_from_excel


def test_import_limited():
    """Testa importação com apenas 3 arquivos (teste rápido)."""
    docs_dir = "docs_entrada"

    # Verificar se diretório existe
    assert os.path.exists(docs_dir), f"Diretório {docs_dir} não encontrado"

    # Listar arquivos Excel de importacao regular (exclui planilhas especiais de derivadas)
    arquivos = [
        f
        for f in os.listdir(docs_dir)
        if f.endswith(".xlsx")
        and not f.strip().casefold().startswith("ssas derivadas e relacionadas")
    ]
    assert len(arquivos) > 0, "Nenhum arquivo .xlsx encontrado"

    # Pegar apenas os 3 primeiros
    arquivos_teste = arquivos[:3]
    print(
        f"\n[INFO] Testando importação com {len(arquivos_teste)} arquivos (de {len(arquivos)} disponíveis)"
    )

    # Criar banco temporário
    temp_dir = tempfile.mkdtemp(prefix="test_import_")
    db_path = os.path.join(temp_dir, "test_ssas.db")
    schema_path = "config/schema.sql"

    try:
        # Inicializar banco
        assert os.path.exists(schema_path), f"Schema não encontrado: {schema_path}"
        success = initialize_database(db_path, schema_path)
        assert success, "Falha ao inicializar banco de teste"

        total_registros = 0
        arquivos_ok = 0

        for arquivo in arquivos_teste:
            file_path = os.path.join(docs_dir, arquivo)
            print(f"  Importando: {arquivo}")

            # Extrair dados
            df = extract_data_from_excel(file_path)
            assert df is not None, f"Falha ao extrair: {arquivo}"

            if not df.empty:
                # Inserir no banco
                success = insert_dataframe_with_smart_upsert(df, db_path)
                assert success, f"Falha ao inserir: {arquivo}"
                total_registros += len(df)
                arquivos_ok += 1
                print(f"    [OK] {len(df)} registros")

        print(f"\n[RESULTADO] {arquivos_ok}/{len(arquivos_teste)} arquivos importados")
        print(f"[RESULTADO] {total_registros} registros totais")

        assert arquivos_ok == len(arquivos_teste), (
            "Nem todos os arquivos foram importados"
        )
        assert total_registros > 0, "Nenhum registro importado"

    finally:
        # Limpar
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


if __name__ == "__main__":
    test_import_limited()
