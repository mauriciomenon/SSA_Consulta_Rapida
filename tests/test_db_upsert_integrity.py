#!/usr/bin/env python3
"""Testes focados em comportamento de upsert inteligente.

Objetivos:
  * Garantir que registros mais novos (data_cadastro) sobrescrevam anteriores
  * Inserção de novo registro não afeta existentes
  * Integridade pós-upsert (sem duplicatas para mesma chave primaria lógica numero_ssa)
"""
from __future__ import annotations

import sqlite3
import pandas as pd
import pytest

from armazenamento import database


@pytest.mark.parametrize("use_smart", [True])  # espaço para parametrizar variantes futuras
def test_upsert_newer_replaces_older(temp_db, sample_upsert_batches, use_smart):
    conn = sqlite3.connect(temp_db)
    database.initialize_database(conn)
    batch1, batch2 = sample_upsert_batches

    if use_smart:
        database.insert_dataframe_with_smart_upsert(conn, batch1)
        database.insert_dataframe_with_smart_upsert(conn, batch2)
    else:  # pragma: no cover - reservado a estratégia alternativa
        database.insert_dataframe_to_db(conn, batch1)
        database.insert_dataframe_to_db(conn, batch2)

    cur = conn.cursor()
    cur.execute("SELECT numero_ssa, situacao, data_cadastro, descricao_ssa FROM ssa_chamados ORDER BY numero_ssa")
    rows = cur.fetchall()

    # Esperado: 3 registros únicos (345 atualizado, 346 original, 347 novo)
    numeros = [r[0] for r in rows]
    assert len(numeros) == len(set(numeros)) == 3

    row_345 = next(r for r in rows if r[0] == "202512345")
    assert row_345[1] == "EM ANDAMENTO"  # situacao atualizada
    assert "Upd" in (row_345[3] or "")


def test_upsert_older_does_not_override(temp_db):
    conn = sqlite3.connect(temp_db)
    database.initialize_database(conn)

    newer = pd.DataFrame(
        {
            "numero_ssa": ["202512390"],
            "situacao": ["EM ANDAMENTO"],
            "data_cadastro": ["2025-01-05 10:00:00"],
            "descricao_ssa": ["Novo estado"],
        }
    )
    older = pd.DataFrame(
        {
            "numero_ssa": ["202512390"],
            "situacao": ["ABERTA"],
            "data_cadastro": ["2025-01-04 09:00:00"],
            "descricao_ssa": ["Versao antiga"],
        }
    )

    database.insert_dataframe_with_smart_upsert(conn, newer)
    database.insert_dataframe_with_smart_upsert(conn, older)  # deve ignorar ou não reverter

    cur = conn.cursor()
    cur.execute("SELECT situacao, data_cadastro, descricao_ssa FROM ssa_chamados WHERE numero_ssa='202512390'")
    row = cur.fetchone()
    assert row is not None
    situacao, data_cadastro, descricao = row
    assert situacao == "EM ANDAMENTO"  # não revertido
    assert data_cadastro.startswith("2025-01-05")
    assert "Novo" in descricao
