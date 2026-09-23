import logging
import os

import pandas as pd

from armazenamento import database, database_upsert_logic
from armazenamento.database import (
    get_db_connection,
    initialize_database,
    insert_dataframe_to_db,
    insert_dataframe_with_smart_upsert,
)
from armazenamento.database_upsert_logic import _should_update_existing

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS ssas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero_ssa INTEGER,
    situacao TEXT,
    data_cadastro TEXT,
    descricao_ssa TEXT,
    setor_executor TEXT
);
"""


def _init_db(tmp_path):
    db_path = os.path.join(tmp_path, "upsert.sqlite")
    schema_path = os.path.join(tmp_path, "schema.sql")
    with open(schema_path, "w", encoding="utf-8") as f:
        f.write(SCHEMA_SQL)
    initialize_database(db_path, schema_path)
    return db_path


def _fetch_all(db_path):
    with get_db_connection(db_path) as conn:
        return pd.read_sql_query("SELECT * FROM ssas ORDER BY numero_ssa", conn)


def test_upsert_insert_new(tmp_path):
    db_path = _init_db(tmp_path)
    df = pd.DataFrame(
        [
            {
                "numero_ssa": "202501111",  # valid 9 digits
                "situacao": "NOVA",
                "data_cadastro": "01/01/2025",
                "descricao_ssa": "primeira",
                "setor_executor": "SET1",
            }
        ]
    )
    assert insert_dataframe_with_smart_upsert(df, db_path, "ssas") is True


# Alias para compatibilidade com comando previamente utilizado pelo usuário
def test_upsert_inserts_new_records(tmp_path):  # noqa: D401
    """Alias equivalente a test_upsert_insert_new para compatibilidade histórica."""
    db_path = _init_db(tmp_path)
    df = pd.DataFrame(
        [
            {
                "numero_ssa": "202501111",  # valid 9 digits
                "situacao": "NOVA",
                "data_cadastro": "01/01/2025",
                "descricao_ssa": "primeira",
                "setor_executor": "SET1",
            }
        ]
    )
    assert insert_dataframe_with_smart_upsert(df, db_path, "ssas") is True
    rows = _fetch_all(db_path)
    assert len(rows) == 1
    assert rows.iloc[0]["situacao"] == "NOVA"


def test_upsert_update_with_newer_date(tmp_path):
    db_path = _init_db(tmp_path)
    first = pd.DataFrame(
        [
            {
                "numero_ssa": "202501222",
                "situacao": "OLD",
                "data_cadastro": "01/01/2025",
                "descricao_ssa": "old desc",
                "setor_executor": "A",
            }
        ]
    )
    insert_dataframe_to_db(first, db_path, "ssas")
    second = pd.DataFrame(
        [
            {
                "numero_ssa": "202501222",
                "situacao": "UPDATED",
                "data_cadastro": "05/01/2025",  # newer
                "descricao_ssa": "new desc",
                "setor_executor": "B",
            }
        ]
    )
    assert insert_dataframe_with_smart_upsert(second, db_path, "ssas") is True
    rows = _fetch_all(db_path)
    assert len(rows) == 1
    assert rows.iloc[0]["situacao"] == "UPDATED"
    assert rows.iloc[0]["setor_executor"] == "B"


def test_upsert_ignore_older_date(tmp_path):
    db_path = _init_db(tmp_path)
    base = pd.DataFrame(
        [
            {
                "numero_ssa": "202501333",
                "situacao": "BASE",
                "data_cadastro": "10/01/2025",
                "descricao_ssa": "base",
                "setor_executor": "X",
            }
        ]
    )
    insert_dataframe_to_db(base, db_path, "ssas")
    older_attempt = pd.DataFrame(
        [
            {
                "numero_ssa": "202501333",
                "situacao": "OLDER",
                "data_cadastro": "05/01/2025",  # older than existing
                "descricao_ssa": "older attempt",
                "setor_executor": "Y",
            }
        ]
    )
    assert insert_dataframe_with_smart_upsert(older_attempt, db_path, "ssas") is True
    rows = _fetch_all(db_path)
    assert len(rows) == 1
    # Must preserve original BASE row since incoming date is older
    assert rows.iloc[0]["situacao"] == "BASE"
    assert rows.iloc[0]["setor_executor"] == "X"


def test_upsert_existing_missing_date_new_has_date(tmp_path):
    """Se a linha existente não tem data e a nova tem, deve atualizar."""
    db_path = _init_db(tmp_path)
    existing = pd.DataFrame(
        [
            {
                "numero_ssa": "202501444",
                "situacao": "NO_DATE",
                "data_cadastro": "",  # missing
                "descricao_ssa": "sem data",
                "setor_executor": "OLD",
            }
        ]
    )
    insert_dataframe_to_db(existing, db_path, "ssas")
    incoming = pd.DataFrame(
        [
            {
                "numero_ssa": "202501444",
                "situacao": "WITH_DATE",
                "data_cadastro": "15/01/2025",  # valid date
                "descricao_ssa": "com data",
                "setor_executor": "NEW",
            }
        ]
    )
    assert insert_dataframe_with_smart_upsert(incoming, db_path, "ssas") is True
    rows = _fetch_all(db_path)
    assert len(rows) == 1
    assert rows.iloc[0]["situacao"] == "WITH_DATE"
    assert rows.iloc[0]["setor_executor"] == "NEW"


def test_upsert_both_missing_dates(tmp_path):
    """Se ambas as linhas não tem data, a nova substitui (empate -> atualiza)."""
    db_path = _init_db(tmp_path)
    first = pd.DataFrame(
        [
            {
                "numero_ssa": "202501555",
                "situacao": "FIRST",
                "data_cadastro": "",  # missing
                "descricao_ssa": "primeira",
                "setor_executor": "A",
            }
        ]
    )
    insert_dataframe_to_db(first, db_path, "ssas")
    second = pd.DataFrame(
        [
            {
                "numero_ssa": "202501555",
                "situacao": "SECOND",
                "data_cadastro": "",  # also missing
                "descricao_ssa": "segunda",
                "setor_executor": "B",
            }
        ]
    )
    assert insert_dataframe_with_smart_upsert(second, db_path, "ssas") is True
    rows = _fetch_all(db_path)
    assert len(rows) == 1
    assert rows.iloc[0]["situacao"] == "SECOND"
    assert rows.iloc[0]["setor_executor"] == "B"


def test_upsert_existing_has_date_new_missing_does_not_update(tmp_path):
    """Se existente tem data e nova linha não tem, NÃO deve atualizar."""
    db_path = _init_db(tmp_path)
    base = pd.DataFrame(
        [
            {
                "numero_ssa": "202501666",
                "situacao": "WITH_DATE",
                "data_cadastro": "20/01/2025",
                "descricao_ssa": "original",
                "setor_executor": "ORIG",
            }
        ]
    )
    insert_dataframe_to_db(base, db_path, "ssas")
    incoming = pd.DataFrame(
        [
            {
                "numero_ssa": "202501666",
                "situacao": "MISSING_NEW",
                "data_cadastro": "",  # missing date => should NOT replace dated row
                "descricao_ssa": "tentativa",
                "setor_executor": "NEWX",
            }
        ]
    )
    assert insert_dataframe_with_smart_upsert(incoming, db_path, "ssas") is True
    rows = _fetch_all(db_path)
    assert len(rows) == 1
    # Must preserve original row
    assert rows.iloc[0]["situacao"] == "WITH_DATE"
    assert rows.iloc[0]["setor_executor"] == "ORIG"


def test_upsert_logs_setor_executor_change_when_newer_row_wins(tmp_path, caplog):
    db_path = _init_db(tmp_path)
    first = pd.DataFrame(
        [
            {
                "numero_ssa": "202501777",
                "situacao": "OLD",
                "data_cadastro": "01/01/2025",
                "descricao_ssa": "old desc",
                "setor_executor": "IEE3",
            }
        ]
    )
    insert_dataframe_to_db(first, db_path, "ssas")
    newer = pd.DataFrame(
        [
            {
                "numero_ssa": "202501777",
                "situacao": "UPDATED",
                "data_cadastro": "05/01/2025",
                "descricao_ssa": "new desc",
                "setor_executor": "IEE4",
            }
        ]
    )

    with caplog.at_level(logging.INFO, logger="armazenamento.database_upsert_logic"):
        assert insert_dataframe_with_smart_upsert(newer, db_path, "ssas") is True

    rows = _fetch_all(db_path)
    assert rows.iloc[0]["setor_executor"] == "IEE4"
    assert "202501777" in caplog.text
    assert "IEE3 -> IEE4" in caplog.text


def test_upsert_does_not_log_setor_executor_change_for_older_row(tmp_path, caplog):
    db_path = _init_db(tmp_path)
    first = pd.DataFrame(
        [
            {
                "numero_ssa": "202501888",
                "situacao": "BASE",
                "data_cadastro": "10/01/2025",
                "descricao_ssa": "base",
                "setor_executor": "IEE3",
            }
        ]
    )
    insert_dataframe_to_db(first, db_path, "ssas")
    older = pd.DataFrame(
        [
            {
                "numero_ssa": "202501888",
                "situacao": "OLDER",
                "data_cadastro": "05/01/2025",
                "descricao_ssa": "older attempt",
                "setor_executor": "IEE4",
            }
        ]
    )

    with caplog.at_level(logging.INFO, logger="armazenamento.database_upsert_logic"):
        assert insert_dataframe_with_smart_upsert(older, db_path, "ssas") is True

    rows = _fetch_all(db_path)
    assert rows.iloc[0]["setor_executor"] == "IEE3"
    assert "202501888" not in caplog.text
    assert "IEE3 -> IEE4" not in caplog.text


def test_upsert_same_date_does_not_downgrade_situacao(tmp_path):
    db_path = _init_db(tmp_path)
    first = pd.DataFrame(
        [
            {
                "numero_ssa": "202600654",
                "situacao": "STE",
                "data_cadastro": "16/01/2026",
                "descricao_ssa": "estado final",
                "setor_executor": "IEE3",
            }
        ]
    )
    insert_dataframe_to_db(first, db_path, "ssas")
    incoming = pd.DataFrame(
        [
            {
                "numero_ssa": "202600654",
                "situacao": "ADM",
                "data_cadastro": "16/01/2026",
                "descricao_ssa": "tentativa downgrade",
                "setor_executor": "IEE3",
            }
        ]
    )
    assert insert_dataframe_with_smart_upsert(incoming, db_path, "ssas") is True
    rows = _fetch_all(db_path)
    assert len(rows) == 1
    assert rows.iloc[0]["situacao"] == "STE"


def test_upsert_same_date_allows_upgrade_situacao(tmp_path):
    db_path = _init_db(tmp_path)
    first = pd.DataFrame(
        [
            {
                "numero_ssa": "202600655",
                "situacao": "ADM",
                "data_cadastro": "16/01/2026",
                "descricao_ssa": "estado aguardando",
                "setor_executor": "IEE3",
            }
        ]
    )
    insert_dataframe_to_db(first, db_path, "ssas")
    incoming = pd.DataFrame(
        [
            {
                "numero_ssa": "202600655",
                "situacao": "STE",
                "data_cadastro": "16/01/2026",
                "descricao_ssa": "estado final",
                "setor_executor": "IEE3",
            }
        ]
    )
    assert insert_dataframe_with_smart_upsert(incoming, db_path, "ssas") is True
    rows = _fetch_all(db_path)
    assert len(rows) == 1
    assert rows.iloc[0]["situacao"] == "STE"


def test_upsert_newer_data_cadastro_cannot_downgrade_from_ste(tmp_path):
    db_path = _init_db(tmp_path)
    first = pd.DataFrame(
        [
            {
                "numero_ssa": "202600656",
                "situacao": "STE",
                "data_cadastro": "16/01/2026",
                "descricao_ssa": "estado terminal",
                "setor_executor": "IEE3",
            }
        ]
    )
    insert_dataframe_to_db(first, db_path, "ssas")
    incoming = pd.DataFrame(
        [
            {
                "numero_ssa": "202600656",
                "situacao": "ADM",
                "data_cadastro": "17/01/2026",
                "descricao_ssa": "tentativa downgrade com data maior",
                "setor_executor": "IEE3",
            }
        ]
    )
    assert insert_dataframe_with_smart_upsert(incoming, db_path, "ssas") is True
    rows = _fetch_all(db_path)
    assert len(rows) == 1
    assert rows.iloc[0]["situacao"] == "STE"


def test_should_update_existing_blocks_older_snapshot_filename() -> None:
    existing = {
        "data_cadastro": "2026-03-26 10:00:00",
        "situacao": "ADM",
        "arquivo_origem": "Consulta SSA - 26-03-2026_0237PM.xlsx",
    }
    incoming = {
        "data_cadastro": "2026-03-27 10:00:00",
        "situacao": "ADM",
        "arquivo_origem": "Consulta SSA - 25-03-2026_0237PM.xlsx",
    }
    assert _should_update_existing(existing, incoming) is False


def test_should_update_existing_blocks_older_data_arquivo_origem_for_generic_names() -> (
    None
):
    existing = {
        "data_cadastro": "2026-03-27 10:00:00",
        "situacao": "ADM",
        "arquivo_origem": "generic_new.xlsx",
        "data_arquivo_origem": "2026-03-27 12:00:00",
    }
    incoming = {
        "data_cadastro": "2026-03-28 10:00:00",
        "situacao": "ADM",
        "arquivo_origem": "generic_old.xlsx",
        "data_arquivo_origem": "2026-03-26 12:00:00",
    }
    assert _should_update_existing(existing, incoming) is False


def test_should_update_existing_blocks_terminal_sca() -> None:
    existing = {
        "data_cadastro": "2026-03-27 10:00:00",
        "situacao": "SCA",
        "data_planilha": "2026-03-27T12:00:00",
    }
    incoming = {
        "data_cadastro": "2026-03-28 10:00:00",
        "situacao": "SEE",
        "data_planilha": "2026-03-28T12:00:00",
    }
    assert _should_update_existing(existing, incoming) is False


def test_should_update_existing_blocks_terminal_ste_with_formatted_status() -> None:
    existing = {
        "data_cadastro": "2026-03-27 10:00:00",
        "situacao": "STE - Servico Terminado",
        "data_planilha": "2026-03-27T12:00:00",
    }
    incoming = {
        "data_cadastro": "2026-03-28 10:00:00",
        "situacao": "ADM",
        "data_planilha": "2026-03-28T12:00:00",
    }
    assert _should_update_existing(existing, incoming) is False


def test_should_update_existing_blocks_when_incoming_has_no_snapshot_time() -> None:
    existing = {
        "data_cadastro": "2026-03-27 10:00:00",
        "situacao": "ADM",
        "arquivo_origem": "Consulta SSA - 27-03-2026_0900AM.xlsx",
    }
    incoming = {
        "data_cadastro": "2026-03-28 10:00:00",
        "situacao": "STE",
        "arquivo_origem": "arquivo_sem_data.xlsx",
    }
    assert _should_update_existing(existing, incoming) is False


def test_should_update_existing_accepts_newer_data_planilha_even_with_older_data_cadastro() -> (
    None
):
    existing = {
        "data_cadastro": "2026-03-27 10:00:00",
        "situacao": "ADM",
        "data_planilha": "2026-03-27T12:00:00",
    }
    incoming = {
        "data_cadastro": "2026-03-20 10:00:00",
        "situacao": "SEE",
        "data_planilha": "2026-03-28T12:00:00",
    }
    assert _should_update_existing(existing, incoming) is True


def test_event_records_persist_for_terminal_ssa_without_overwriting_parent(tmp_path):
    db_path = _init_db(tmp_path)
    existing = pd.DataFrame(
        [
            {
                "numero_ssa": "202601001",
                "situacao": "STE",
                "data_cadastro": "2026-01-01 10:00:00",
                "descricao_ssa": "descricao preservada",
                "setor_executor": "OLD",
            }
        ]
    )
    insert_dataframe_to_db(existing, db_path, "ssas")
    incoming = pd.DataFrame(
        [
            {
                "numero_ssa": "202601001",
                "situacao": "STE",
                "data_cadastro": "2026-01-01 10:00:00",
                "descricao_ssa": "descricao que nao pode sobrescrever",
                "setor_executor": "NEW",
                "arquivo_origem": "reprogramacoes.xlsx",
                "data_planilha": "2026-08-06T09:06:00",
            }
        ]
    )
    incoming.attrs["ssa_event_records"] = [
        {
            "numero_ssa": "202601001",
            "record_type": "num_reprogramacoes",
            "record_order": 1,
            "record_label": "Reprogramacao #1",
            "payload_json": '{"num_reprogramacoes":"Reprogramacao #1"}',
            "source_sheet": "Sheet1",
            "source_row": 2,
        },
        {
            "numero_ssa": "202601001",
            "record_type": "num_reprogramacoes",
            "record_order": 2,
            "record_label": "Reprogramacao #2",
            "payload_json": '{"num_reprogramacoes":"Reprogramacao #2"}',
            "source_sheet": "Sheet1",
            "source_row": 3,
        },
    ]
    metrics: dict[str, int] = {}

    database.set_optimized_mode(True)
    try:
        assert (
            insert_dataframe_with_smart_upsert(
                incoming,
                db_path,
                "ssas",
                metrics_out=metrics,
            )
            is True
        )
    finally:
        database.set_optimized_mode(False)

    assert metrics["ssa_event_records_processed"] == 2
    assert len(incoming.attrs["ssa_event_records"]) == 2
    parent = _fetch_all(db_path).iloc[0]
    assert parent["descricao_ssa"] == "descricao preservada"
    assert parent["setor_executor"] == "OLD"
    with get_db_connection(db_path) as conn:
        events = pd.read_sql_query(
            "SELECT record_order, record_label, payload_json "
            "FROM ssa_event_records ORDER BY record_order, payload_json",
            conn,
        )
    assert events["record_label"].tolist() == [
        "Reprogramacao #1",
        "Reprogramacao #2",
    ]

    assert insert_dataframe_with_smart_upsert(incoming, db_path, "ssas") is True
    variant = incoming.copy()
    variant.attrs["ssa_event_records"] = [
        {
            **incoming.attrs["ssa_event_records"][1],
            "payload_json": '{"num_reprogramacoes":"Reprogramacao #2 corrigida"}',
        }
    ]
    assert insert_dataframe_with_smart_upsert(variant, db_path, "ssas") is True
    with get_db_connection(db_path) as conn:
        event_count = conn.execute("SELECT COUNT(*) FROM ssa_event_records").fetchone()[
            0
        ]
    assert event_count == 3


def test_event_record_uses_per_record_recency_without_dataframe_metadata(tmp_path):
    db_path = _init_db(tmp_path)
    incoming = pd.DataFrame(
        [
            {
                "numero_ssa": "202601003",
                "situacao": "ADM",
                "data_cadastro": "2026-01-01 10:00:00",
                "descricao_ssa": "evento autocontido",
                "setor_executor": "MEL1",
            }
        ]
    )
    event = {
        "numero_ssa": "202601003",
        "record_type": "Deviation Records",
        "record_order": 1,
        "record_label": "Deviation #1",
        "payload_json": '{"Deviation Records":"Deviation #1"}',
        "arquivo_origem": "deviation_06-08-2026_0912AM__1.xlsx",
        "data_planilha": "2026-08-06T09:12:00",
        "data_arquivo_origem": "2026-08-06 09:12:00",
        "source_sheet": "Sheet1",
        "source_row": 2,
    }
    incoming.attrs["ssa_event_records"] = [event]

    assert insert_dataframe_with_smart_upsert(incoming, db_path, "ssas") is True
    incoming.attrs["ssa_event_records"] = [
        {
            **event,
            "arquivo_origem": "deviation_06-08-2026_0912AM.xlsx",
        }
    ]
    assert insert_dataframe_with_smart_upsert(incoming, db_path, "ssas") is True
    incoming.attrs["ssa_event_records"] = [event]
    assert insert_dataframe_with_smart_upsert(incoming, db_path, "ssas") is True
    with get_db_connection(db_path) as conn:
        origin_after_tie = conn.execute(
            "SELECT arquivo_origem FROM ssa_event_records"
        ).fetchone()[0]
    # Equal timestamps keep the lexicographically smaller base filename.
    assert origin_after_tie == "deviation_06-08-2026_0912AM.xlsx"

    incoming.attrs["ssa_event_records"] = [
        {
            **event,
            "arquivo_origem": "deviation_05-08-2026_0912AM.xlsx",
            "data_planilha": "2026-08-05T09:12:00",
            "data_arquivo_origem": "2026-08-05 09:12:00",
        }
    ]
    assert insert_dataframe_with_smart_upsert(incoming, db_path, "ssas") is True
    with get_db_connection(db_path) as conn:
        origin_after_older = conn.execute(
            "SELECT arquivo_origem FROM ssa_event_records"
        ).fetchone()[0]
    assert origin_after_older == "deviation_06-08-2026_0912AM.xlsx"

    incoming.attrs["ssa_event_records"] = [
        {
            **event,
            "arquivo_origem": "deviation_07-08-2026_0912AM.xlsx",
            "data_planilha": "2026-08-07T09:12:00",
            "data_arquivo_origem": "2026-08-07 09:12:00",
        }
    ]
    assert insert_dataframe_with_smart_upsert(incoming, db_path, "ssas") is True
    with get_db_connection(db_path) as conn:
        event_source = conn.execute(
            "SELECT arquivo_origem, data_planilha, data_arquivo_origem "
            "FROM ssa_event_records"
        ).fetchone()
    assert event_source == (
        "deviation_07-08-2026_0912AM.xlsx",
        "2026-08-07T09:12:00",
        "2026-08-07 09:12:00",
    )

    null_date_event = {
        **event,
        "record_order": 2,
        "payload_json": '{"Deviation Records":"Deviation #2"}',
        "arquivo_origem": "undated-first.xlsx",
        "data_planilha": None,
        "data_arquivo_origem": None,
    }
    incoming.attrs["ssa_event_records"] = [null_date_event]
    assert insert_dataframe_with_smart_upsert(incoming, db_path, "ssas") is True
    incoming.attrs["ssa_event_records"] = [
        {**null_date_event, "arquivo_origem": "undated-second.xlsx"}
    ]
    assert insert_dataframe_with_smart_upsert(incoming, db_path, "ssas") is True
    with get_db_connection(db_path) as conn:
        undated_origin = conn.execute(
            "SELECT arquivo_origem FROM ssa_event_records WHERE record_order = 2"
        ).fetchone()[0]
    assert undated_origin == "undated-first.xlsx"


def test_event_record_rejects_missing_origin_and_ambiguous_snapshot_date(
    tmp_path,
    caplog,
):
    db_path = _init_db(tmp_path)
    incoming = pd.DataFrame(
        [
            {
                "numero_ssa": "202601004",
                "situacao": "ADM",
                "data_cadastro": "2026-01-01 10:00:00",
                "descricao_ssa": "evento invalido",
                "setor_executor": "MEL1",
            }
        ]
    )
    event = {
        "numero_ssa": "202601004",
        "record_type": "Deviation Records",
        "record_order": 1,
        "record_label": "Deviation #1",
        "payload_json": '{"Deviation Records":"Deviation #1"}',
        "source_sheet": "Sheet1",
        "source_row": 2,
    }

    caplog.set_level(logging.ERROR)
    incoming.attrs["ssa_event_records"] = [event]
    assert insert_dataframe_with_smart_upsert(incoming, db_path, "ssas") is False
    assert "require arquivo_origem metadata" in caplog.text

    caplog.clear()
    incoming.attrs["ssa_event_records"] = [
        {
            **event,
            "arquivo_origem": "ambiguous-date.xlsx",
            "data_planilha": "2026-8-6 9:2:0",
        }
    ]
    assert insert_dataframe_with_smart_upsert(incoming, db_path, "ssas") is False
    assert "data_planilha must use YYYY-MM-DDTHH:MM:SS" in caplog.text

    caplog.clear()
    metadata_incoming = incoming.assign(data_planilha="2026-8-6 9:2:0")
    metadata_incoming.attrs["ssa_event_records"] = [
        {**event, "arquivo_origem": "ambiguous-metadata-date.xlsx"}
    ]
    assert (
        insert_dataframe_with_smart_upsert(metadata_incoming, db_path, "ssas") is False
    )
    assert "data_planilha must use YYYY-MM-DDTHH:MM:SS" in caplog.text
    assert _fetch_all(db_path).empty


def test_event_persistence_failure_rolls_back_parent_update(tmp_path, monkeypatch):
    db_path = _init_db(tmp_path)
    existing = pd.DataFrame(
        [
            {
                "numero_ssa": "202601002",
                "situacao": "ADM",
                "data_cadastro": "2026-01-01 10:00:00",
                "descricao_ssa": "antes",
                "setor_executor": "OLD",
            }
        ]
    )
    insert_dataframe_to_db(existing, db_path, "ssas")
    incoming = pd.DataFrame(
        [
            {
                "numero_ssa": "202601002",
                "situacao": "SEE",
                "data_cadastro": "2026-01-02 10:00:00",
                "descricao_ssa": "depois",
                "setor_executor": "NEW",
                "arquivo_origem": "parciais.xlsx",
                "data_planilha": "2026-08-06T09:19:00",
            }
        ]
    )
    incoming.attrs["ssa_event_records"] = [
        {
            "numero_ssa": "202601002",
            "record_type": "parciais",
            "record_order": 1,
            "record_label": "Parcial #1",
            "payload_json": '{"parciais":"Parcial #1"}',
            "source_sheet": "Sheet1",
            "source_row": 2,
        }
    ]

    def fail_event_persistence(*_args, **_kwargs):
        raise RuntimeError("falha injetada em eventos")

    monkeypatch.setattr(
        database_upsert_logic,
        "_persist_ssa_event_records",
        fail_event_persistence,
    )

    assert insert_dataframe_with_smart_upsert(incoming, db_path, "ssas") is False
    parent = _fetch_all(db_path).iloc[0]
    assert parent["descricao_ssa"] == "antes"
    assert parent["setor_executor"] == "OLD"
