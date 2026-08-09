#!/usr/bin/env python3
# tests/test_database_verification.py
"""
Testes para as novas funcionalidades de verificação e integridade do banco de dados.
"""

import os
import sqlite3
import logging
import threading
import time
from contextlib import closing
from pathlib import Path

import pandas as pd
import pytest

import armazenamento.database_integrity as database_integrity_module
import armazenamento.database_validation as database_validation
from armazenamento.database import (
    ensure_column_exists,
    initialize_database,
    query_db,
    repair_database_if_needed,
    validate_dataframe_before_insert,
    verify_database_integrity,
)
from armazenamento.database_optimized import insert_dataframe_optimized
from armazenamento.database_lock import database_writer_lock
from shared.db_names import SSA_READ_REQUIRED_COLUMNS
from utils.db_maintenance import DatabaseAnalyzer, DatabaseMigrator

TOTAL_VALID_ROWS = 2  # Constante para evitar magic numbers


def _runtime_schema_sql(
    table_name: str = "ssa_table",
    *,
    missing: frozenset[str] = frozenset(),
    legacy_status: bool = False,
    optional_columns: bool = True,
) -> str:
    columns: list[str] = []
    for column in SSA_READ_REQUIRED_COLUMNS:
        if column in missing:
            continue
        name = "status" if legacy_status and column == "situacao" else column
        if name == "id":
            definition = "INTEGER PRIMARY KEY AUTOINCREMENT"
        elif name in {
            "semana_cadastro",
            "semana_programada",
            "semana_executada",
            "num_reprogramacoes",
        }:
            definition = "INTEGER"
        else:
            definition = "TEXT"
        columns.append(f'"{name}" {definition}')
    if optional_columns:
        columns.extend(('"arquivo_origem" TEXT', '"data_planilha" TEXT'))
    return f'CREATE TABLE "{table_name}" ({", ".join(columns)});'


def _write_runtime_schema(
    schema_path: str,
    table_name: str = "ssa_table",
    **kwargs,
) -> None:
    Path(schema_path).write_text(
        _runtime_schema_sql(table_name, **kwargs),
        encoding="utf-8",
    )


class TestDatabaseVerification:  # noqa: D101
    """Testes para verificação de integridade do banco."""

    def test_ensure_column_exists_no_error_when_table_absent(self, tmp_path, caplog):
        """Nao deve logar erro quando a tabela ainda nao existe no bootstrap."""
        db_path = os.path.join(tmp_path, "no_table_yet.db")

        added = ensure_column_exists(db_path, "ssa_table", "arquivo_origem", "TEXT")

        assert added is False
        assert "Falha ao garantir coluna" not in caplog.text

    def test_ensure_column_exists_rejects_invalid_definition(self, tmp_path, caplog):
        """Definicao SQL fora da whitelist deve falhar antes do ALTER TABLE."""
        db_path = os.path.join(tmp_path, "invalid_definition.db")
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE ssas (numero_ssa INTEGER)")
        conn.commit()
        conn.close()

        with caplog.at_level(logging.ERROR, logger="armazenamento.database"):
            added = ensure_column_exists(
                db_path,
                "ssas",
                "arquivo_origem",
                "TEXT DEFAULT 'x'",
            )

        assert added is False
        assert "Invalid SQL column definition" in caplog.text

    def test_verify_nonexistent_database(self):
        """Banco inexistente deve ser invalido e marcado para criacao."""
        fake_path = "/path/that/does/not/exist/fake.db"
        report = verify_database_integrity(fake_path)

        assert report["is_valid"] is False
        assert not report["database_exists"]
        assert report.get("needs_creation") is True
        assert len(report["issues"]) > 0
        assert "nao encontrado" in str(report["issues"])

    def test_verify_valid_database(self, tmp_path):
        """Testa verificação de banco válido."""
        # Criar banco temporário válido
        db_path = os.path.join(tmp_path, "test.db")
        schema_path = os.path.join(tmp_path, "schema.sql")

        _write_runtime_schema(schema_path, "ssas")

        # Inicializar banco
        initialize_database(db_path, schema_path)

        # Verificar integridade (tabela principal atual: 'ssas')
        report = verify_database_integrity(db_path, table_name="ssas")

        assert report["is_valid"]
        assert report["database_exists"]
        assert report["database_accessible"]
        assert report["table_exists"]
        assert report["schema_valid"]

    def test_verify_alias_table_resolves_to_canonical_table(self, tmp_path):
        """Alias legado deve resolver para a tabela canonica quando ela existe."""
        db_path = os.path.join(tmp_path, "canonical_alias.db")
        with sqlite3.connect(db_path) as conn:
            conn.execute(_runtime_schema_sql())

        report = verify_database_integrity(db_path, table_name="ssas")

        assert report["is_valid"] is True
        assert report["table_name"] == "ssa_table"
        assert report["table_exists"] is True

    def test_verify_prefers_table_over_view_when_both_exist(self, tmp_path):
        """Quando alias existe como view e tabela canonica existe, deve priorizar tabela."""
        db_path = os.path.join(tmp_path, "prefer_table_over_view.db")
        with sqlite3.connect(db_path) as conn:
            conn.execute(_runtime_schema_sql())
            conn.execute("CREATE VIEW ssas AS SELECT * FROM ssa_table")

        report = verify_database_integrity(db_path, table_name="ssas")

        assert report["is_valid"] is True
        assert report["table_name"] == "ssa_table"
        assert report["table_exists"] is True

    def test_verify_view_only_alias_is_rejected_for_runtime_storage(self, tmp_path):
        """A view sem tabela SSA fisica nao pode passar o contrato de escrita."""
        db_path = os.path.join(tmp_path, "view_only_alias.db")
        conn = sqlite3.connect(db_path)
        conn.execute(
            """
            CREATE TABLE source_rows (
                numero_ssa INTEGER,
                situacao TEXT,
                data_cadastro TEXT,
                descricao_ssa TEXT
            )
            """
        )
        conn.execute(
            """
            INSERT INTO source_rows (numero_ssa, situacao, data_cadastro, descricao_ssa)
            VALUES (202312345, 'STE', '2023-12-01 10:00:00', 'Teste view')
            """
        )
        conn.execute(
            """
            CREATE VIEW ssas AS
            SELECT numero_ssa, situacao, data_cadastro, descricao_ssa
            FROM source_rows
            """
        )
        conn.commit()
        conn.close()

        report = verify_database_integrity(db_path, table_name="ssas")

        assert report["is_valid"] is False
        assert report["table_name"] == "ssas"
        assert report["table_exists"] is False
        assert any("view sem tabela fisica" in issue for issue in report["issues"])

    def test_verify_rejects_two_physical_ssa_tables(self, tmp_path):
        db_path = os.path.join(tmp_path, "ambiguous.db")
        with sqlite3.connect(db_path) as conn:
            conn.execute(_runtime_schema_sql("ssa_table"))
            conn.execute(_runtime_schema_sql("ssas"))

        report = verify_database_integrity(db_path, table_name="ssas")

        assert report["is_valid"] is False
        assert any("Ambiguous SSA storage tables" in issue for issue in report["issues"])

    def test_verify_and_repair_canonical_request_accept_legacy_only_storage(
        self, tmp_path
    ):
        db_path = os.path.join(tmp_path, "legacy_only.db")
        schema_path = os.path.join(tmp_path, "schema.sql")
        _write_runtime_schema(schema_path)
        with sqlite3.connect(db_path) as conn:
            conn.execute(_runtime_schema_sql("ssas"))

        report = verify_database_integrity(db_path, table_name="ssa_table")

        assert report["is_valid"] is True
        assert report["table_name"] == "ssas"
        assert repair_database_if_needed(db_path, schema_path) is True
        with closing(sqlite3.connect(db_path)) as conn:
            physical_tables = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
        assert "ssas" in physical_tables
        assert "ssa_table" not in physical_tables

    def test_verify_resolves_uppercase_canonical_table(self, tmp_path):
        db_path = os.path.join(tmp_path, "uppercase.db")
        with sqlite3.connect(db_path) as conn:
            conn.execute(_runtime_schema_sql("SSA_TABLE"))

        report = verify_database_integrity(db_path, table_name="ssas")

        assert report["is_valid"] is True
        assert report["table_name"] == "SSA_TABLE"

    @pytest.mark.parametrize(
        ("numero_ssa", "situacao", "data_cadastro", "issue_key"),
        [
            ("BAD-ID", "STE", "2026-01-02 03:04:05", "invalid_numero_ssa"),
            ("202600001", "ZZZ", "2026-01-02 03:04:05", "unknown_situacao"),
            ("202600001", "STE", "not-a-date", "invalid_data_cadastro"),
        ],
    )
    def test_verify_rejects_malformed_operational_data(
        self,
        tmp_path,
        numero_ssa,
        situacao,
        data_cadastro,
        issue_key,
    ):
        db_path = os.path.join(tmp_path, f"invalid_{issue_key}.db")
        with sqlite3.connect(db_path) as conn:
            conn.execute(_runtime_schema_sql())
            conn.execute(
                "INSERT INTO ssa_table (numero_ssa, situacao, data_cadastro) "
                "VALUES (?, ?, ?)",
                (numero_ssa, situacao, data_cadastro),
            )

        report = verify_database_integrity(db_path)

        assert report["is_valid"] is False
        assert report["data_consistent"] is False
        assert report["invalid_data"][issue_key]

    def test_verify_rejects_duplicate_canonical_ssa(self, tmp_path):
        db_path = os.path.join(tmp_path, "duplicate.db")
        with sqlite3.connect(db_path) as conn:
            conn.execute(_runtime_schema_sql())
            conn.executemany(
                "INSERT INTO ssa_table (numero_ssa, situacao, data_cadastro) "
                "VALUES (?, 'STE', '2026-01-02 03:04:05')",
                [("202600001",), ("202600001",)],
            )

        report = verify_database_integrity(db_path)

        assert report["is_valid"] is False
        assert report["invalid_data"]["duplicate_numero_ssa"] == 1

    def test_verify_accepts_incomplete_rows_persisted_by_import_contract(self, tmp_path):
        db_path = os.path.join(tmp_path, "incomplete_import_row.db")
        schema_path = os.path.join(tmp_path, "schema.sql")
        _write_runtime_schema(schema_path)
        initialize_database(db_path, schema_path)
        frame = pd.DataFrame(
            {
                "numero_ssa": [None],
                "situacao": [None],
                "data_cadastro": ["2026-01-02 03:04:05"],
                "descricao_ssa": ["linha incompleta tolerada"],
            }
        )
        assert insert_dataframe_optimized(frame, db_path, "ssa_table") is True

        report = verify_database_integrity(db_path)

        assert report["is_valid"] is True
        assert report["invalid_data"]["missing_numero_ssa"] == 1
        assert report["invalid_data"]["missing_situacao"] == 1
        assert report["invalid_data"]["invalid_numero_ssa"] == 0
        assert report["invalid_data"]["unknown_situacao"] == []

    def test_verify_null_status_does_not_hide_missing_required_date(self, tmp_path):
        db_path = os.path.join(tmp_path, "null_status_and_date.db")
        with sqlite3.connect(db_path) as conn:
            conn.execute(_runtime_schema_sql())
            conn.execute(
                "INSERT INTO ssa_table (numero_ssa, situacao, data_cadastro) "
                "VALUES ('202600001', NULL, NULL)"
            )

        report = verify_database_integrity(db_path)

        assert report["is_valid"] is False
        assert report["invalid_data"]["missing_situacao"] == 1
        assert report["invalid_data"]["invalid_data_cadastro"] == 1

    def test_verify_corrupted_database(self, tmp_path):
        """Testa verificação de banco corrompido."""
        # Criar arquivo corrompido (não é SQLite válido)
        db_path = os.path.join(tmp_path, "corrupted.db")
        with open(db_path, "w") as f:
            f.write("This is not a valid SQLite file")

        report = verify_database_integrity(db_path)

        assert not report["is_valid"]
        assert report["database_exists"]
        assert not report["database_accessible"]

    def test_verify_empty_file_database(self, tmp_path):
        """Um arquivo vazio (0 bytes) não deve ser considerado acessível ou consistente."""
        db_path = os.path.join(tmp_path, "empty.db")
        # criar arquivo vazio
        open(db_path, "w").close()
        assert os.path.exists(db_path)
        assert os.path.getsize(db_path) == 0
        report = verify_database_integrity(db_path)
        assert report["database_exists"] is True
        assert report["database_accessible"] is False
        assert report["data_consistent"] is False
        assert not report["is_valid"]
        assert report["needs_creation"] is True


class TestDataValidation:
    """Testes para validação de dados."""

    def test_validate_empty_dataframe(self):
        """Testa validação de DataFrame vazio."""
        df = pd.DataFrame()
        report = validate_dataframe_before_insert(df)

        assert report["is_valid"]
        assert report["row_count"] == 0
        assert report["table_name"] == "ssa_table"
        assert len(report["warnings"]) > 0
        assert "vazio" in str(report["warnings"])
        assert "_invalid_row_seen" not in report

    def test_validate_valid_dataframe(self):
        """Testa validação de DataFrame válido."""
        df = pd.DataFrame(
            {
                "numero_ssa": [202312345, 202398765],
                "situacao": ["Pendente", "Executada"],
                "data_cadastro": ["2023-12-01 10:00:00", "2023-12-02 15:30:00"],
                "descricao_ssa": ["Teste 1", "Teste 2"],
            }
        )

        report = validate_dataframe_before_insert(df)

        assert report["is_valid"]
        assert report["row_count"] == TOTAL_VALID_ROWS


class TestDatabaseMaintenance:
    """Testes para manutencao e analise estrutural do banco."""

    def test_analyze_table_structure_counts_schema_identifier_with_punctuation(
        self,
        tmp_path,
    ):
        """Coluna vinda do schema deve ser contada com escape seguro."""
        db_path = os.path.join(tmp_path, "maintenance_invalid_identifier.db")
        conn = sqlite3.connect(db_path)
        conn.execute('CREATE TABLE ssas (numero_ssa INTEGER, "bad-name" TEXT)')
        conn.execute(
            'INSERT INTO ssas (numero_ssa, "bad-name") VALUES (?, ?)',
            (1, "abc"),
        )
        conn.commit()
        conn.close()

        analyzer = DatabaseAnalyzer(db_path)
        report = analyzer.analyze_table_structure()

        assert report["column_counts"]["bad-name"] == 1

    def test_analyze_table_structure_uses_canonical_table_without_legacy_alias(
        self,
        tmp_path,
    ):
        db_path = os.path.join(tmp_path, "maintenance_canonical_only.db")
        conn = sqlite3.connect(db_path)
        conn.execute('CREATE TABLE ssa_table (numero_ssa TEXT, "bad-name" TEXT)')
        conn.execute(
            'INSERT INTO ssa_table (numero_ssa, "bad-name") VALUES (?, ?)',
            ("202512345", "abc"),
        )
        conn.commit()
        conn.close()

        analyzer = DatabaseAnalyzer(db_path)
        report = analyzer.analyze_table_structure()

        assert report["column_counts"]["numero_ssa"] == 1
        assert report["column_counts"]["bad-name"] == 1

    def test_analyze_table_structure_accepts_legacy_view_for_read_only_analysis(
        self,
        tmp_path,
    ):
        db_path = os.path.join(tmp_path, "maintenance_view_only_analysis.db")
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE raw_ssa (numero_ssa TEXT, descricao_ssa TEXT)")
        conn.execute(
            "INSERT INTO raw_ssa (numero_ssa, descricao_ssa) VALUES (?, ?)",
            ("202512345", "Descricao"),
        )
        conn.execute("CREATE VIEW ssas AS SELECT * FROM raw_ssa")
        conn.commit()
        conn.close()

        analyzer = DatabaseAnalyzer(db_path)
        report = analyzer.analyze_table_structure()

        assert report["column_counts"]["numero_ssa"] == 1
        assert report["column_counts"]["descricao_ssa"] == 1

    def test_analyze_table_structure_escapes_schema_identifier_with_quote(
        self,
        tmp_path,
    ):
        """Schema-derived identifiers must be escaped before dynamic SQL."""
        malicious_col = 'bad"; DROP TABLE ssas; --'
        quoted_col = malicious_col.replace('"', '""')
        db_path = os.path.join(tmp_path, "maintenance_quoted_identifier.db")
        conn = sqlite3.connect(db_path)
        conn.execute(f'CREATE TABLE ssas (numero_ssa INTEGER, "{quoted_col}" TEXT)')
        conn.execute(
            f'INSERT INTO ssas (numero_ssa, "{quoted_col}") VALUES (?, ?)',
            (1, "abc"),
        )
        conn.commit()
        conn.close()

        analyzer = DatabaseAnalyzer(db_path)
        report = analyzer.analyze_table_structure()

        assert report["column_counts"][malicious_col] == 1

    def test_analyze_table_structure_counts_legacy_numero_ssa_column(self, tmp_path):
        legacy_numero = "N\u00famero da SSA"
        db_path = os.path.join(tmp_path, "maintenance_legacy_identifier.db")
        conn = sqlite3.connect(db_path)
        conn.execute(f'CREATE TABLE ssas (numero_ssa TEXT, "{legacy_numero}" TEXT)')
        conn.executemany(
            f'INSERT INTO ssas (numero_ssa, "{legacy_numero}") VALUES (?, ?)',
            [("", "2025-12345"), ("202512346", "")],
        )
        conn.commit()
        conn.close()

        analyzer = DatabaseAnalyzer(db_path)
        report = analyzer.analyze_table_structure()

        assert report["column_counts"][legacy_numero] == 1
        assert report["duplicated_groups"]["numero_ssa"][0]["is_legacy"] is False
        assert any(
            col["name"] == legacy_numero and col["is_legacy"] is True
            for col in report["duplicated_groups"]["numero_ssa"]
        )

    def test_analyze_table_structure_treats_whitespace_as_empty(self, tmp_path):
        db_path = os.path.join(tmp_path, "maintenance_whitespace_counts.db")
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE ssas (numero_ssa TEXT, descricao_ssa TEXT)")
        conn.executemany(
            "INSERT INTO ssas (numero_ssa, descricao_ssa) VALUES (?, ?)",
            [("202512345", " "), ("202512346", "Descricao")],
        )
        conn.commit()
        conn.close()

        analyzer = DatabaseAnalyzer(db_path)
        report = analyzer.analyze_table_structure()

        assert report["column_counts"]["descricao_ssa"] == 1

    def test_create_backup_uses_collision_resistant_name(self, tmp_path):
        db_path = tmp_path / "maintenance_backup.db"
        with sqlite3.connect(db_path) as conn:
            conn.execute("CREATE TABLE ssas (numero_ssa TEXT)")
        analyzer = DatabaseAnalyzer(str(db_path))

        backup_a = analyzer.create_backup(str(tmp_path / "backups"))
        backup_b = analyzer.create_backup(str(tmp_path / "backups"))

        assert backup_a != backup_b
        assert os.path.exists(backup_a)
        assert os.path.exists(backup_b)

    def test_sanity_check_prefers_normalized_numero_ssa_when_legacy_is_blank(
        self,
        tmp_path,
    ):
        legacy_numero = "N\u00famero da SSA"
        db_path = os.path.join(tmp_path, "maintenance_numero_coalesce.db")
        conn = sqlite3.connect(db_path)
        conn.execute(f'CREATE TABLE ssas (numero_ssa TEXT, "{legacy_numero}" TEXT)')
        conn.executemany(
            f'INSERT INTO ssas (numero_ssa, "{legacy_numero}") VALUES (?, ?)',
            [("202512345", ""), ("202512346", "")],
        )
        conn.commit()
        conn.close()

        analyzer = DatabaseAnalyzer(db_path)
        report = analyzer.perform_sanity_check()

        assert report["issues"]["missing_numero_ssa"] == []
        assert report["issues"]["duplicate_numbers"] == {}

    def test_sanity_check_uses_canonical_table_without_legacy_alias(self, tmp_path):
        db_path = os.path.join(tmp_path, "maintenance_sanity_canonical_only.db")
        conn = sqlite3.connect(db_path)
        conn.execute(
            """
            CREATE TABLE ssa_table (
                numero_ssa TEXT,
                descricao_ssa TEXT,
                setor_emissor TEXT
            )
            """
        )
        conn.execute(
            """
            INSERT INTO ssa_table (numero_ssa, descricao_ssa, setor_emissor)
            VALUES (?, ?, ?)
            """,
            ("202512345", "Descricao", "AREA"),
        )
        conn.commit()
        conn.close()

        analyzer = DatabaseAnalyzer(db_path)
        report = analyzer.perform_sanity_check()

        assert report["total_records"] == 1
        assert report["summary"]["missing_numero_ssa"] == 0
        assert report["summary"]["missing_descricao"] == 0

    def test_sanity_check_reads_canonical_view_for_read_only_analysis(self, tmp_path):
        db_path = os.path.join(tmp_path, "maintenance_sanity_canonical_view.db")
        conn = sqlite3.connect(db_path)
        conn.execute(
            """
            CREATE TABLE source_rows (
                numero_ssa TEXT,
                descricao_ssa TEXT,
                setor_emissor TEXT
            )
            """
        )
        conn.execute(
            """
            INSERT INTO source_rows (numero_ssa, descricao_ssa, setor_emissor)
            VALUES (?, ?, ?)
            """,
            ("202512345", "Descricao", "AREA"),
        )
        conn.execute("CREATE VIEW ssa_table AS SELECT * FROM source_rows")
        conn.commit()
        conn.close()

        analyzer = DatabaseAnalyzer(db_path)
        report = analyzer.perform_sanity_check()

        assert report["total_records"] == 1
        assert report["summary"]["missing_numero_ssa"] == 0

    def test_sanity_check_keeps_duplicate_numbers_across_chunks(self, tmp_path):
        db_path = os.path.join(tmp_path, "maintenance_sanity_chunk_duplicates.db")
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE ssa_table (numero_ssa TEXT)")
        rows = [
            ("202512345" if index in (1, 5001) else str(202600000 + index),)
            for index in range(5002)
        ]
        conn.executemany("INSERT INTO ssa_table (numero_ssa) VALUES (?)", rows)
        conn.commit()
        conn.close()

        analyzer = DatabaseAnalyzer(db_path)
        report = analyzer.perform_sanity_check()

        assert report["total_records"] == 5002
        assert report["issues"]["duplicate_numbers"] == {"202512345": 2}
        assert report["summary"]["duplicate_numbers"] == 2

    def test_sanity_check_counts_duplicate_numbers_after_normalization(self, tmp_path):
        db_path = os.path.join(tmp_path, "maintenance_sanity_normalized_duplicates.db")
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE ssa_table (numero_ssa TEXT)")
        conn.executemany(
            "INSERT INTO ssa_table (numero_ssa) VALUES (?)",
            [("2025-12345",), ("202512345",)],
        )
        conn.commit()
        conn.close()

        analyzer = DatabaseAnalyzer(db_path)
        report = analyzer.perform_sanity_check()

        assert report["issues"]["duplicate_numbers"] == {"202512345": 2}
        assert report["summary"]["duplicate_numbers"] == 2

    def test_sanity_check_excludes_invalid_numero_from_duplicate_count(self, tmp_path):
        db_path = os.path.join(tmp_path, "maintenance_sanity_invalid_duplicate.db")
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE ssa_table (numero_ssa TEXT)")
        conn.executemany(
            "INSERT INTO ssa_table (numero_ssa) VALUES (?)",
            [("202512345",), ("ABC202512345XYZ",), ("202512345",)],
        )
        conn.commit()
        conn.close()

        analyzer = DatabaseAnalyzer(db_path)
        report = analyzer.perform_sanity_check()

        assert report["issues"]["duplicate_numbers"] == {"202512345": 2}
        assert report["summary"]["duplicate_numbers"] == 2

    def test_sanity_check_uses_legacy_numero_ssa_when_normalized_is_blank(
        self,
        tmp_path,
    ):
        legacy_numero = "N\u00famero da SSA"
        db_path = os.path.join(tmp_path, "maintenance_numero_legacy_fallback.db")
        conn = sqlite3.connect(db_path)
        conn.execute(f'CREATE TABLE ssas (numero_ssa TEXT, "{legacy_numero}" TEXT)')
        conn.executemany(
            f'INSERT INTO ssas (numero_ssa, "{legacy_numero}") VALUES (?, ?)',
            [("", "202512345"), ("", "202512346")],
        )
        conn.commit()
        conn.close()

        analyzer = DatabaseAnalyzer(db_path)
        report = analyzer.perform_sanity_check()

        assert report["issues"]["missing_numero_ssa"] == []
        assert report["issues"]["duplicate_numbers"] == {}

    def test_sanity_check_empty_records_treats_blank_strings_as_empty(
        self,
        tmp_path,
    ):
        legacy_numero = "N\u00famero da SSA"
        db_path = os.path.join(tmp_path, "maintenance_blank_empty_records.db")
        conn = sqlite3.connect(db_path)
        conn.execute(
            f"""
            CREATE TABLE ssas (
                numero_ssa TEXT,
                "{legacy_numero}" TEXT,
                descricao_ssa TEXT,
                setor_emissor TEXT
            )
            """
        )
        conn.executemany(
            f"""
            INSERT INTO ssas (numero_ssa, "{legacy_numero}", descricao_ssa, setor_emissor)
            VALUES (?, ?, ?, ?)
            """,
            [
                ("", "", " ", ""),
                ("", "202512345", "", ""),
            ],
        )
        conn.commit()
        conn.close()

        analyzer = DatabaseAnalyzer(db_path)
        report = analyzer.perform_sanity_check()

        assert report["issues"]["empty_records"] == [0]
        assert report["summary"]["empty_records"] == 1
        assert report["issues"]["missing_descricao"] == [0, 1]
        assert report["issues"]["missing_area_emissora"] == [0, 1]

    def test_migrate_duplicate_columns_moves_all_legacy_sources_once(
        self,
        tmp_path,
        monkeypatch,
    ):
        db_path = os.path.join(tmp_path, "maintenance_multi_legacy.db")
        conn = sqlite3.connect(db_path)
        conn.execute(
            """
            CREATE TABLE ssas (
                numero_ssa TEXT,
                legacy_numero_a TEXT,
                legacy_numero_b TEXT
            )
            """
        )
        conn.executemany(
            """
            INSERT INTO ssas (numero_ssa, legacy_numero_a, legacy_numero_b)
            VALUES (?, ?, ?)
            """,
            [
                ("", "2025-12345", ""),
                ("", "", "202500046"),
                ("202500047", "202500048", ""),
            ],
        )
        conn.commit()
        conn.close()

        migrator = DatabaseMigrator(db_path)
        monkeypatch.setattr(
            migrator.analyzer,
            "create_backup",
            lambda: str(tmp_path / "backup.db"),
        )
        monkeypatch.setattr(
            migrator.analyzer,
            "analyze_table_structure",
            lambda: {
                "duplicated_groups": {
                    "numero_ssa": [
                        {"name": "numero_ssa", "count": 1, "is_legacy": False},
                        {"name": "legacy_numero_a", "count": 2, "is_legacy": True},
                        {"name": "legacy_numero_b", "count": 1, "is_legacy": True},
                    ]
                }
            },
        )

        result = migrator.migrate_duplicate_columns(dry_run=False)

        assert result["backup_created"].endswith("backup.db")
        assert [plan["records_to_migrate"] for plan in result["migration_plan"]] == [
            1,
            1,
        ]
        assert result["migration_stats"]["updated_rows"] == 2
        assert result["migration_stats"]["skipped_invalid_records"] == 0
        with sqlite3.connect(db_path) as check_conn:
            rows = check_conn.execute(
                "SELECT numero_ssa, legacy_numero_a, legacy_numero_b FROM ssas ORDER BY rowid"
            ).fetchall()
        assert rows == [
            ("202512345", "2025-12345", ""),
            ("202500046", "", "202500046"),
            ("202500047", "202500048", ""),
        ]

    def test_migrate_duplicate_columns_treats_whitespace_target_as_empty(
        self,
        tmp_path,
        monkeypatch,
    ):
        db_path = os.path.join(tmp_path, "maintenance_whitespace_target.db")
        conn = sqlite3.connect(db_path)
        conn.execute(
            """
            CREATE TABLE ssas (
                numero_ssa TEXT,
                legacy_numero TEXT
            )
            """
        )
        conn.execute(
            "INSERT INTO ssas (numero_ssa, legacy_numero) VALUES (?, ?)",
            ("   ", "2025-12345"),
        )
        conn.commit()
        conn.close()

        migrator = DatabaseMigrator(db_path)
        monkeypatch.setattr(
            migrator.analyzer,
            "create_backup",
            lambda: str(tmp_path / "backup.db"),
        )
        monkeypatch.setattr(
            migrator.analyzer,
            "analyze_table_structure",
            lambda: {
                "duplicated_groups": {
                    "numero_ssa": [
                        {"name": "numero_ssa", "count": 0, "is_legacy": False},
                        {"name": "legacy_numero", "count": 1, "is_legacy": True},
                    ]
                }
            },
        )

        result = migrator.migrate_duplicate_columns(dry_run=False)

        assert result["migration_plan"][0]["records_to_migrate"] == 1
        assert result["migration_stats"]["updated_rows"] == 1
        with sqlite3.connect(db_path) as check_conn:
            stored = check_conn.execute("SELECT numero_ssa FROM ssas").fetchone()[0]
        assert stored == "202512345"

    def test_migrate_duplicate_columns_skips_invalid_numero_ssa_values(
        self,
        tmp_path,
        monkeypatch,
    ):
        db_path = os.path.join(tmp_path, "maintenance_invalid_legacy_value.db")
        conn = sqlite3.connect(db_path)
        conn.execute(
            """
            CREATE TABLE ssas (
                numero_ssa TEXT,
                legacy_numero TEXT
            )
            """
        )
        conn.execute(
            "INSERT INTO ssas (numero_ssa, legacy_numero) VALUES (?, ?)",
            ("", "ABC202512345XYZ"),
        )
        conn.commit()
        conn.close()

        migrator = DatabaseMigrator(db_path)
        monkeypatch.setattr(
            migrator.analyzer,
            "create_backup",
            lambda: str(tmp_path / "backup.db"),
        )
        monkeypatch.setattr(
            migrator.analyzer,
            "analyze_table_structure",
            lambda: {
                "duplicated_groups": {
                    "numero_ssa": [
                        {"name": "numero_ssa", "count": 0, "is_legacy": False},
                        {"name": "legacy_numero", "count": 1, "is_legacy": True},
                    ]
                }
            },
        )

        result = migrator.migrate_duplicate_columns(dry_run=False)

        assert result["migration_stats"]["updated_rows"] == 0
        assert result["migration_stats"]["skipped_invalid_records"] == 1
        assert result["migration_stats"]["skipped_invalid_numero_ssa"] == 1
        with sqlite3.connect(db_path) as check_conn:
            stored = check_conn.execute("SELECT numero_ssa FROM ssas").fetchone()[0]
        assert stored == ""

    def test_migrate_duplicate_columns_dry_run_does_not_create_backup(
        self,
        tmp_path,
        monkeypatch,
    ):
        db_path = os.path.join(tmp_path, "maintenance_dry_run.db")
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE ssas (numero_ssa TEXT, legacy_numero TEXT)")
        conn.execute(
            "INSERT INTO ssas (numero_ssa, legacy_numero) VALUES (?, ?)",
            ("", "202512345"),
        )
        conn.commit()
        conn.close()

        migrator = DatabaseMigrator(db_path)

        def _fail_backup():
            raise AssertionError("dry-run must not create backup")

        monkeypatch.setattr(migrator.analyzer, "create_backup", _fail_backup)
        monkeypatch.setattr(
            migrator.analyzer,
            "analyze_table_structure",
            lambda: {
                "duplicated_groups": {
                    "numero_ssa": [
                        {"name": "numero_ssa", "count": 0, "is_legacy": False},
                        {"name": "legacy_numero", "count": 1, "is_legacy": True},
                    ]
                }
            },
        )

        result = migrator.migrate_duplicate_columns(dry_run=True)

        assert result["backup_created"] is None
        assert result["migration_plan"][0]["records_to_migrate"] == 1

    def test_migrate_duplicate_columns_dry_run_uses_canonical_table(self, tmp_path):
        legacy_numero = "N\u00famero da SSA"
        db_path = os.path.join(tmp_path, "maintenance_migrate_canonical_only.db")
        conn = sqlite3.connect(db_path)
        conn.execute(f'CREATE TABLE ssa_table (numero_ssa TEXT, "{legacy_numero}" TEXT)')
        conn.execute(
            f'INSERT INTO ssa_table (numero_ssa, "{legacy_numero}") VALUES (?, ?)',
            ("", "202512345"),
        )
        conn.commit()
        conn.close()

        migrator = DatabaseMigrator(db_path)
        result = migrator.migrate_duplicate_columns(dry_run=True)

        assert result["backup_created"] is None
        assert result["migration_plan"][0]["source"] == legacy_numero
        assert result["migration_plan"][0]["target"] == "numero_ssa"
        assert result["migration_plan"][0]["records_to_migrate"] == 1

    def test_migrate_duplicate_columns_updates_canonical_table_behind_legacy_view(
        self,
        tmp_path,
        monkeypatch,
    ):
        legacy_numero = "N\u00famero da SSA"
        db_path = os.path.join(tmp_path, "maintenance_migrate_view_alias.db")
        conn = sqlite3.connect(db_path)
        conn.execute(f'CREATE TABLE ssa_table (numero_ssa TEXT, "{legacy_numero}" TEXT)')
        conn.execute(
            f'INSERT INTO ssa_table (numero_ssa, "{legacy_numero}") VALUES (?, ?)',
            ("", "202512345"),
        )
        conn.execute("CREATE VIEW ssas AS SELECT * FROM ssa_table")
        conn.commit()
        conn.close()

        migrator = DatabaseMigrator(db_path)
        monkeypatch.setattr(
            migrator.analyzer,
            "create_backup",
            lambda: str(tmp_path / "backup.db"),
        )

        result = migrator.migrate_duplicate_columns(dry_run=False)

        assert result["migration_stats"]["updated_rows"] == 1
        with sqlite3.connect(db_path) as check_conn:
            stored = check_conn.execute(
                "SELECT numero_ssa FROM ssa_table"
            ).fetchone()[0]
        assert stored == "202512345"

    def test_perform_sanity_check_uses_central_dayfirst_date_parser(self, tmp_path):
        db_path = os.path.join(tmp_path, "maintenance_dayfirst.db")
        conn = sqlite3.connect(db_path)
        conn.execute(
            """
            CREATE TABLE ssas (
                numero_ssa TEXT,
                data_cadastro TEXT,
                descricao_ssa TEXT,
                setor_emissor TEXT
            )
            """
        )
        conn.executemany(
            """
            INSERT INTO ssas (numero_ssa, data_cadastro, descricao_ssa, setor_emissor)
            VALUES (?, ?, ?, ?)
            """,
            [
                ("202512345", "01/12/2025 10:00", "Descricao", "AREA"),
                ("202512346", "not-a-date", "Descricao", "AREA"),
            ],
        )
        conn.commit()
        conn.close()

        analyzer = DatabaseAnalyzer(db_path)
        report = analyzer.perform_sanity_check()

        assert report["summary"]["invalid_dates"] == 1
        assert report["issues"]["invalid_dates"] == [1]

    def test_perform_sanity_check_coalesces_location_columns(self, tmp_path):
        db_path = os.path.join(tmp_path, "maintenance_location_columns.db")
        conn = sqlite3.connect(db_path)
        conn.execute(
            """
            CREATE TABLE ssas (
                numero_ssa TEXT,
                localizacao_codigo TEXT,
                descricao_localizacao TEXT
            )
            """
        )
        conn.executemany(
            """
            INSERT INTO ssas (
                numero_ssa,
                localizacao_codigo,
                descricao_localizacao
            )
            VALUES (?, ?, ?)
            """,
            [
                ("202512345", "", "Sala 1"),
                ("202512346", "A01", ""),
                ("202512347", "", ""),
            ],
        )
        conn.commit()
        conn.close()

        analyzer = DatabaseAnalyzer(db_path)
        report = analyzer.perform_sanity_check()

        assert report["issues"]["missing_localizacao"] == [2]
        assert report["summary"]["missing_localizacao"] == 1

    def test_validate_invalid_ssa_numbers(self):
        """Testa validação com números SSA inválidos."""
        df = pd.DataFrame(
            {
                "numero_ssa": [
                    123,
                    "invalid",
                    None,
                    202312345,
                ],  # Mistura de válidos e inválidos
                "situacao": ["Pendente", "Executada", "Teste", "Ok"],
                "data_cadastro": [
                    "2023-12-01",
                    "2023-12-02",
                    "2023-12-03",
                    "2023-12-04",
                ],
            }
        )

        report = validate_dataframe_before_insert(df)

        # Ainda deve ser considerado válido (só avisos)
        assert report["is_valid"]
        assert len(report["warnings"]) > 0
        assert "invalidos" in str(report["warnings"])
        assert len(report["invalid_rows"]) > 0

    def test_validate_rejects_numero_ssa_with_letters_under_storage_rules(self):
        df = pd.DataFrame(
            {
                "numero_ssa": ["ABC202512345XYZ", "202512346"],
                "situacao": ["Pendente", "Executada"],
                "data_cadastro": ["2025-01-01 10:00:00", "2025-01-02 10:00:00"],
                "descricao_ssa": ["Com letras", "Valida"],
            }
        )

        report = validate_dataframe_before_insert(df)

        assert report["is_valid"] is True
        assert "invalidos" in str(report["warnings"])
        assert 0 in report["invalid_rows"]
        assert report["invalid_by_column"]["numero_ssa"] == [0]

    def test_validate_invalid_rows_has_no_duplicate_indexes(self):
        """Garante que invalid_rows nao repete indice para numero_ssa ausente."""
        df = pd.DataFrame(
            {
                "numero_ssa": [None, 202312345],
                "situacao": ["Pendente", "Executada"],
                "data_cadastro": ["2023-12-01 10:00:00", "2023-12-02 15:30:00"],
            }
        )

        report = validate_dataframe_before_insert(df)

        assert 0 in report["invalid_rows"]
        assert len(report["invalid_rows"]) == len(set(report["invalid_rows"]))
        assert "_invalid_row_seen" not in report

    def test_validate_invalid_dates(self):
        """Testa validacao com datas invalidas."""
        df = pd.DataFrame(
            {
                "numero_ssa": [202312345, 202398765],
                "situacao": ["Pendente", "Executada"],
                "data_cadastro": ["invalid-date", "2023-99-99"],
                "descricao_ssa": ["Teste 1", "Teste 2"],
            }
        )

        report = validate_dataframe_before_insert(df)

        assert report["is_valid"]  # Avisos, não erros críticos
        assert len(report["warnings"]) > 0
        assert "datas invalidas" in str(report["warnings"])

    def test_validate_date_column_accepts_central_parser_result(self, monkeypatch):
        df = pd.DataFrame(
            {
                "numero_ssa": [202312345],
                "situacao": ["Pendente"],
                "data_cadastro": ["01/12/2023 10:00"],
                "descricao_ssa": ["Teste 1"],
            }
        )

        monkeypatch.setattr(
            database_validation,
            "parse_any_date",
            lambda _value: "2023-12-01 10:00:00",
        )

        report = validate_dataframe_before_insert(df)

        assert report["is_valid"] is True
        assert not any("datas" in warning for warning in report["warnings"])

    def test_validate_date_column_failure_preserves_exception_cause(self, monkeypatch):
        """Falha interna no parsing deve preservar a causa no warning da coluna."""
        df = pd.DataFrame(
            {
                "numero_ssa": [202312345],
                "situacao": ["Pendente"],
                "data_cadastro": ["2023-12-01 10:00:00"],
                "descricao_ssa": ["Teste 1"],
            }
        )

        def _explode(*_args, **_kwargs):
            raise RuntimeError("forced parse crash")

        monkeypatch.setattr(database_validation, "parse_any_date", _explode)

        report = validate_dataframe_before_insert(df)

        assert report["is_valid"] is True
        assert any(
            "Falha ao validar datas em 'data_cadastro' (RuntimeError): forced parse crash"
            in warning
            for warning in report["warnings"]
        )

    def test_validate_duplicate_ssa_exact_rows(self):
        """Duplicidade literal deve ser classificada separadamente."""
        df = pd.DataFrame(
            {
                "numero_ssa": [202205845, 202205845],
                "situacao": ["STE", "STE"],
                "data_cadastro": ["2022-04-13 10:11:15", "2022-04-13 10:11:15"],
                "descricao_ssa": ["Descricao identica", "Descricao identica"],
            }
        )

        report = validate_dataframe_before_insert(df)

        rules = {violation["rule"] for violation in report["violations"]}
        assert "duplicate_numero_ssa_exact" in rules
        assert "duplicate_numero_ssa_conflict" not in rules
        assert "duplicados identicos" in str(report["warnings"])

    def test_validate_duplicate_ssa_conflicting_rows(self):
        """Duplicidade com payload diferente deve seguir como conflito."""
        df = pd.DataFrame(
            {
                "numero_ssa": [202205845, 202205845],
                "situacao": ["STE", "APG"],
                "data_cadastro": ["2022-04-13 10:11:15", "2022-04-13 10:11:15"],
                "descricao_ssa": ["Descricao identica", "Descricao alterada"],
            }
        )

        report = validate_dataframe_before_insert(df)

        rules = {violation["rule"] for violation in report["violations"]}
        assert "duplicate_numero_ssa_conflict" in rules
        assert "duplicate_numero_ssa_exact" not in rules
        assert "duplicados conflitantes" in str(report["warnings"])

    def test_validate_duplicate_ssa_exact_rows_with_unhashable_payload(self):
        """Payload com lista nao deve quebrar validacao de duplicidade exata."""
        df = pd.DataFrame(
            {
                "numero_ssa": [202205845, 202205845],
                "situacao": ["STE", "STE"],
                "data_cadastro": ["2022-04-13 10:11:15", "2022-04-13 10:11:15"],
                "descricao_ssa": ["Descricao identica", "Descricao identica"],
                "tags": [["A", "B"], ["A", "B"]],
            }
        )

        report = validate_dataframe_before_insert(df)

        rules = {violation["rule"] for violation in report["violations"]}
        assert "duplicate_numero_ssa_exact" in rules
        assert "duplicate_numero_ssa_conflict" not in rules

    def test_validate_duplicate_ssa_uses_canonical_storage_key(self):
        df = pd.DataFrame(
            {
                "numero_ssa": ["2025-12345", "202512345"],
                "situacao": ["STE", "APG"],
                "data_cadastro": ["2022-04-13 10:11:15", "2022-04-13 10:11:15"],
                "descricao_ssa": ["Descricao 1", "Descricao 2"],
            }
        )

        report = validate_dataframe_before_insert(df)

        rules = {violation["rule"] for violation in report["violations"]}
        assert "duplicate_numero_ssa_conflict" in rules

    def test_validate_missing_data_cadastro_exceptions_keep_non_allowed_invalid(self):
        """SCC/ADI/ASE sem data sao permitidos, mas status fora da lista seguem invalidos."""
        df = pd.DataFrame(
            {
                "numero_ssa": [202222569, 202214992, 202500001, 202500002],
                "situacao": ["SCC", "ADI", "ASE", "APG"],
                "data_cadastro": [None, None, None, None],
                "descricao_ssa": ["Caso SCC", "Caso ADI", "Caso ASE", "Caso APG"],
            }
        )

        report = validate_dataframe_before_insert(df)

        assert report["is_valid"] is False
        assert "Coluna 'data_cadastro' possui 1 valores ausentes" in report["issues"]
        assert report["invalid_by_column"]["data_cadastro"] == [3]

    def test_validate_missing_required_column_reports_violation(self):
        """Ausencia de coluna obrigatoria deve gerar issue e violation estruturada."""
        df = pd.DataFrame(
            {
                "numero_ssa": [202500100],
                "situacao": ["APV"],
                "descricao_ssa": ["Sem data de cadastro"],
            }
        )

        report = validate_dataframe_before_insert(df)

        assert report["is_valid"] is False
        assert (
            "Coluna obrigatoria 'data_cadastro' ausente no DataFrame"
            in report["issues"]
        )
        rules = {violation["rule"] for violation in report["violations"]}
        assert "missing_column_data_cadastro" in rules

    def test_validate_sets_structured_error_details_on_unexpected_exception(
        self, monkeypatch
    ):
        """Falhas inesperadas devem preencher bloco error_details no report."""
        df = pd.DataFrame(
            {
                "numero_ssa": [202500200],
                "situacao": ["APV"],
                "data_cadastro": ["2025-01-01 00:00:00"],
            }
        )

        def _explode(*_args, **_kwargs):
            raise RuntimeError("forced validation crash")

        monkeypatch.setattr(database_validation, "_validate_required_columns", _explode)
        report = validate_dataframe_before_insert(df)

        assert report["is_valid"] is False
        assert report["error_details"]["type"] == "RuntimeError"
        assert "forced validation crash" in report["error_details"]["message"]
        assert "_invalid_row_seen" not in report


class TestDatabaseRepair:
    """Testes para reparo de banco de dados."""

    def test_repair_nonexistent_database(self, tmp_path):
        """Reparo deve criar banco inexistente usando schema informado."""
        db_path = os.path.join(tmp_path, "new.db")
        schema_path = os.path.join(tmp_path, "schema.sql")

        _write_runtime_schema(schema_path, "ssas")

        result = repair_database_if_needed(db_path, schema_path, table_name="ssas")

        assert result is True
        assert os.path.exists(db_path)

        # Confirma integridade do banco criado
        report = verify_database_integrity(db_path, table_name="ssas")
        assert report["is_valid"] is True
        assert report["table_exists"] is True

    def test_repair_empty_file_database_recreates_schema(self, tmp_path):
        """Arquivo SQLite vazio deve seguir o caminho de recriacao, nao de restore."""
        db_path = os.path.join(tmp_path, "empty_repair.db")
        schema_path = os.path.join(tmp_path, "schema.sql")

        _write_runtime_schema(schema_path, "ssas")

        Path(db_path).touch()
        assert os.path.getsize(db_path) == 0

        result = repair_database_if_needed(db_path, schema_path, table_name="ssas")

        assert result is True
        report = verify_database_integrity(db_path, table_name="ssas")
        assert report["is_valid"] is True
        assert report["table_exists"] is True

    def test_repair_adds_arquivo_origem_when_schema_is_otherwise_valid(self, tmp_path):
        """Reparo deve adicionar coluna auxiliar ausente fora da verificacao."""
        db_path = os.path.join(tmp_path, "repair_missing_column.db")
        schema_path = os.path.join(tmp_path, "schema.sql")

        _write_runtime_schema(
            schema_path,
            optional_columns=False,
        )

        initialize_database(db_path, schema_path)

        report_before = verify_database_integrity(db_path, table_name="ssa_table")
        assert "arquivo_origem" not in query_db(db_path, "ssa_table").columns
        assert any("arquivo_origem" in warning for warning in report_before["warnings"])

        result = repair_database_if_needed(db_path, schema_path, table_name="ssa_table")

        assert result is True
        assert "arquivo_origem" in query_db(db_path, "ssa_table").columns

    def test_verify_missing_required_columns_exposes_repair_metadata(self, tmp_path):
        """Schema drift de colunas obrigatorias deve aparecer explicitamente no report."""
        db_path = os.path.join(tmp_path, "missing_required_report.db")
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                _runtime_schema_sql(
                    missing=frozenset({"situacao", "data_cadastro"})
                )
            )

        report = verify_database_integrity(db_path, table_name="ssa_table")

        assert report["is_valid"] is False
        assert sorted(report["missing_required_columns"]) == [
            "data_cadastro",
            "situacao",
        ]
        assert report["repair_suggestion"] is not None

    def test_repair_refuses_required_column_without_safe_mapping(self, tmp_path):
        """Reparo nao deve criar coluna obrigatoria vazia e declarar sucesso."""
        db_path = os.path.join(tmp_path, "repair_missing_required.db")
        schema_path = os.path.join(tmp_path, "schema.sql")
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                _runtime_schema_sql(missing=frozenset({"data_cadastro"}))
            )
        _write_runtime_schema(schema_path)

        result = repair_database_if_needed(db_path, schema_path, table_name="ssa_table")

        assert result is False
        with sqlite3.connect(db_path) as conn:
            columns = {row[1] for row in conn.execute("PRAGMA table_info(ssa_table)")}
        assert "data_cadastro" not in columns

    def test_repair_renames_legacy_status_without_losing_value(self, tmp_path):
        """A unica migracao automatica obrigatoria preserva o valor funcional."""
        db_path = os.path.join(tmp_path, "repair_legacy_status.db")
        schema_path = os.path.join(tmp_path, "schema.sql")
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                _runtime_schema_sql(legacy_status=True, optional_columns=False)
            )
            conn.execute(
                "INSERT INTO ssa_table (numero_ssa, status, data_cadastro) "
                "VALUES ('202600001', 'STE', '2026-01-02 03:04:05')"
            )
        _write_runtime_schema(schema_path)

        result = repair_database_if_needed(db_path, schema_path, table_name="ssa_table")

        assert result is True
        with sqlite3.connect(db_path) as conn:
            row = conn.execute(
                "SELECT situacao FROM ssa_table WHERE numero_ssa='202600001'"
            ).fetchone()
            columns = {item[1] for item in conn.execute("PRAGMA table_info(ssa_table)")}
        assert row == ("STE",)
        assert "status" not in columns
        assert {"situacao", "arquivo_origem", "data_planilha"} <= columns

    def test_repair_nonexistent_database_avoids_false_warning(self, tmp_path, caplog):
        """Banco ausente em bootstrap nao deve logar warning generico de problema."""
        db_path = os.path.join(tmp_path, "new_bootstrap.db")
        schema_path = os.path.join(tmp_path, "schema.sql")

        _write_runtime_schema(schema_path, "ssas")

        caplog.set_level("INFO")
        result = repair_database_if_needed(db_path, schema_path, table_name="ssas")

        assert result is True
        assert "Problemas detectados no banco" not in caplog.text
        assert "Banco ausente em bootstrap" in caplog.text

    def test_repair_valid_database(self, tmp_path):
        """Testa reparo de banco já válido."""
        db_path = os.path.join(tmp_path, "valid.db")
        schema_path = os.path.join(tmp_path, "schema.sql")

        # Criar schema e banco válido (com colunas obrigatórias)
        _write_runtime_schema(schema_path, "ssas")

        initialize_database(db_path, schema_path)

        # Reparo deve retornar True (sem fazer nada) usando tabela 'ssas'
        result = repair_database_if_needed(db_path, schema_path, table_name="ssas")

        assert result is True

    def test_corrupt_database_without_snapshot_is_left_untouched(self, tmp_path):
        db_path = Path(tmp_path) / "corrupt_without_snapshot.db"
        schema_path = Path(tmp_path) / "schema.sql"
        db_path.write_bytes(b"not a sqlite database")
        original = db_path.read_bytes()
        _write_runtime_schema(str(schema_path))

        result = repair_database_if_needed(
            str(db_path), str(schema_path), table_name="ssa_table"
        )

        assert result is False
        assert db_path.read_bytes() == original

    def test_snapshot_includes_active_wal_and_auxiliary_objects(self, tmp_path):
        db_path = Path(tmp_path) / "active_wal.db"
        schema_path = Path(tmp_path) / "schema.sql"
        _write_runtime_schema(str(schema_path))
        initialize_database(str(db_path), str(schema_path))

        with sqlite3.connect(db_path) as writer:
            writer.execute("PRAGMA journal_mode=WAL")
            writer.execute("PRAGMA wal_autocheckpoint=0")
            writer.execute("CREATE TABLE aux_history (value TEXT)")
            writer.execute("INSERT INTO aux_history VALUES ('preserved')")
            writer.execute(
                "INSERT INTO ssa_table (numero_ssa, situacao, data_cadastro) "
                "VALUES ('202600010', 'STE', '2026-01-02 03:04:05')"
            )
            writer.commit()
            assert Path(f"{db_path}-wal").exists()

            snapshot = database_integrity_module._create_integrity_snapshot(
                str(db_path), force=True
            )

        assert snapshot is not None
        with sqlite3.connect(snapshot) as conn:
            assert conn.execute("PRAGMA integrity_check").fetchone() == ("ok",)
            assert conn.execute("SELECT value FROM aux_history").fetchone() == (
                "preserved",
            )
            assert conn.execute("SELECT COUNT(*) FROM ssa_table").fetchone() == (1,)

    def test_corrupt_database_restores_complete_valid_snapshot(self, tmp_path):
        db_path = Path(tmp_path) / "restore_complete.db"
        schema_path = Path(tmp_path) / "schema.sql"
        _write_runtime_schema(str(schema_path))
        initialize_database(str(db_path), str(schema_path))
        with closing(sqlite3.connect(db_path)) as conn:
            conn.execute("CREATE TABLE aux_history (value TEXT)")
            conn.execute("CREATE TABLE aux_audit (value TEXT)")
            conn.execute("CREATE INDEX aux_history_value ON aux_history(value)")
            conn.execute(
                "CREATE TRIGGER aux_history_audit AFTER INSERT ON aux_history "
                "BEGIN INSERT INTO aux_audit VALUES (NEW.value); END"
            )
            conn.execute("CREATE VIEW aux_history_view AS SELECT value FROM aux_history")
            conn.execute("INSERT INTO aux_history VALUES ('kept')")
            conn.execute(
                "INSERT INTO ssa_table (numero_ssa, situacao, data_cadastro) "
                "VALUES ('202600011', 'STE', '2026-01-02 03:04:05')"
            )
            conn.commit()

        snapshot = database_integrity_module._create_integrity_snapshot(
            str(db_path), force=True
        )
        assert snapshot is not None
        db_path.write_bytes(b"corrupted after snapshot")

        result = repair_database_if_needed(
            str(db_path), str(schema_path), table_name="ssa_table"
        )

        assert result is True
        with sqlite3.connect(db_path) as conn:
            assert conn.execute("PRAGMA integrity_check").fetchone() == ("ok",)
            assert conn.execute("SELECT value FROM aux_history").fetchone() == ("kept",)
            assert conn.execute("SELECT value FROM aux_audit").fetchone() == ("kept",)
            assert conn.execute("SELECT value FROM aux_history_view").fetchone() == (
                "kept",
            )
            assert conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' "
                "AND name='aux_history_value'"
            ).fetchone() == ("aux_history_value",)
            assert conn.execute(
                "SELECT name FROM sqlite_master WHERE type='trigger' "
                "AND name='aux_history_audit'"
            ).fetchone() == ("aux_history_audit",)
            assert conn.execute("SELECT COUNT(*) FROM ssa_table").fetchone() == (1,)

    @pytest.mark.parametrize("failure_point", ["sidecar", "primary_replace"])
    def test_restore_failure_never_leaves_primary_path_absent(
        self, tmp_path, monkeypatch, failure_point
    ):
        db_path = Path(tmp_path) / f"restore_failure_{failure_point}.db"
        schema_path = Path(tmp_path) / "schema.sql"
        _write_runtime_schema(str(schema_path))
        initialize_database(str(db_path), str(schema_path))
        snapshot = database_integrity_module._create_integrity_snapshot(
            str(db_path), force=True
        )
        assert snapshot is not None
        original = b"corrupt-primary-must-remain"
        db_path.write_bytes(original)
        wal_path = Path(f"{db_path}-wal")
        shm_path = Path(f"{db_path}-shm")
        wal_path.write_bytes(b"wal-bundle")
        shm_path.write_bytes(b"shm-bundle")
        real_replace = database_integrity_module._replace_file_with_retry

        def _inject_failure(source, target):
            source_path = Path(source)
            target_path = Path(target)
            if failure_point == "sidecar" and source_path == shm_path:
                raise OSError("forced sidecar move failure")
            if (
                failure_point == "primary_replace"
                and target_path == db_path.resolve()
                and source_path.suffix == ".tmp"
            ):
                raise OSError("forced primary replace failure")
            real_replace(source, target)

        monkeypatch.setattr(
            database_integrity_module,
            "_replace_file_with_retry",
            _inject_failure,
        )

        restored = database_integrity_module._restore_latest_valid_snapshot(
            str(db_path), "ssa_table"
        )

        assert restored is False
        assert db_path.read_bytes() == original
        assert wal_path.read_bytes() == b"wal-bundle"
        assert shm_path.read_bytes() == b"shm-bundle"

    def test_integrity_snapshot_retention_is_bounded(self, tmp_path):
        db_path = Path(tmp_path) / "bounded.db"
        schema_path = Path(tmp_path) / "schema.sql"
        _write_runtime_schema(str(schema_path))
        initialize_database(str(db_path), str(schema_path))

        for _ in range(4):
            assert database_integrity_module._create_integrity_snapshot(
                str(db_path), force=True
            )

        assert len(database_integrity_module._snapshot_paths(str(db_path))) == 2

    @pytest.mark.parametrize(
        ("first_name", "second_name"),
        [
            ("same.db", "same.sqlite"),
            ("same[1].db", "same1.db"),
            ("same.db", "same.db.integrity_shadow"),
        ],
    )
    def test_snapshot_namespace_uses_literal_complete_database_filename(
        self, tmp_path, first_name, second_name
    ):
        first_db = Path(tmp_path) / first_name
        second_db = Path(tmp_path) / second_name
        schema_path = Path(tmp_path) / "schema.sql"
        _write_runtime_schema(str(schema_path))
        for db_path, numero in (
            (first_db, "202600021"),
            (second_db, "202600022"),
        ):
            initialize_database(str(db_path), str(schema_path))
            with closing(sqlite3.connect(db_path)) as conn:
                conn.execute(
                    "INSERT INTO ssa_table (numero_ssa, situacao, data_cadastro) "
                    "VALUES (?, 'STE', '2026-01-02 03:04:05')",
                    (numero,),
                )
                conn.commit()
            assert database_integrity_module._create_integrity_snapshot(
                str(db_path), force=True
            )

        assert set(database_integrity_module._snapshot_paths(str(first_db))).isdisjoint(
            database_integrity_module._snapshot_paths(str(second_db))
        )
        first_db.write_bytes(b"corrupt first database only")

        assert repair_database_if_needed(
            str(first_db), str(schema_path), table_name="ssa_table"
        )
        with closing(sqlite3.connect(first_db)) as conn:
            restored_numero = conn.execute(
                "SELECT numero_ssa FROM ssa_table"
            ).fetchone()
        assert restored_numero == ("202600021",)

    def test_restore_waits_for_writer_and_preserves_committed_state_forensics(
        self, tmp_path
    ):
        db_path = Path(tmp_path) / "concurrent_restore.db"
        schema_path = Path(tmp_path) / "schema.sql"
        _write_runtime_schema(str(schema_path))
        initialize_database(str(db_path), str(schema_path))
        with closing(sqlite3.connect(db_path)) as conn:
            conn.execute(
                "INSERT INTO ssa_table (numero_ssa, situacao, data_cadastro) "
                "VALUES ('202600031', 'STE', '2026-01-02 03:04:05')"
            )
            conn.commit()
        assert database_integrity_module._create_integrity_snapshot(
            str(db_path), force=True
        )

        writer_committed = threading.Event()
        release_writer = threading.Event()
        restore_finished = threading.Event()
        restore_result: list[bool] = []

        def _writer() -> None:
            with database_writer_lock(str(db_path)):
                with closing(sqlite3.connect(db_path)) as conn:
                    conn.execute(
                        "INSERT INTO ssa_table "
                        "(numero_ssa, situacao, data_cadastro) "
                        "VALUES ('202600032', 'SPG', '2026-01-02 03:04:05')"
                    )
                    conn.commit()
                writer_committed.set()
                release_writer.wait(timeout=5)

        def _restore() -> None:
            restore_result.append(
                database_integrity_module._restore_latest_valid_snapshot(
                    str(db_path), "ssa_table"
                )
            )
            restore_finished.set()

        writer_thread = threading.Thread(target=_writer)
        restore_thread = threading.Thread(target=_restore)
        writer_thread.start()
        assert writer_committed.wait(timeout=5)
        restore_thread.start()
        assert restore_finished.wait(timeout=0.2) is False
        release_writer.set()
        writer_thread.join(timeout=5)
        restore_thread.join(timeout=5)

        assert restore_result == [True]
        with closing(sqlite3.connect(db_path)) as conn:
            restored_rows = conn.execute(
                "SELECT numero_ssa FROM ssa_table ORDER BY numero_ssa"
            ).fetchall()
        assert restored_rows == [("202600031",)]
        forensic = database_integrity_module._backup_paths(str(db_path), "corrupt")
        assert len(forensic) == 1
        with closing(sqlite3.connect(forensic[0])) as conn:
            forensic_rows = conn.execute(
                "SELECT numero_ssa FROM ssa_table ORDER BY numero_ssa"
            ).fetchall()
        assert forensic_rows == [("202600031",), ("202600032",)]

    def test_snapshot_interval_uses_snapshot_creation_time(self, tmp_path):
        db_path = Path(tmp_path) / "old_source.db"
        schema_path = Path(tmp_path) / "schema.sql"
        _write_runtime_schema(str(schema_path))
        initialize_database(str(db_path), str(schema_path))
        old_time = time.time() - (30 * 24 * 60 * 60)
        os.utime(db_path, (old_time, old_time))

        first = database_integrity_module._create_integrity_snapshot(str(db_path))
        second = database_integrity_module._create_integrity_snapshot(str(db_path))

        assert first is not None
        assert second == first
        assert len(database_integrity_module._snapshot_paths(str(db_path))) == 1

    def test_disposable_full_rescan_candidate_does_not_create_snapshot(self, tmp_path):
        db_path = Path(tmp_path) / "test.db.full_rescan_candidate_run123"
        schema_path = Path(tmp_path) / "schema.sql"
        _write_runtime_schema(str(schema_path))
        initialize_database(str(db_path), str(schema_path))

        snapshot = database_integrity_module._create_integrity_snapshot(
            str(db_path), force=True
        )

        assert snapshot is None
        assert database_integrity_module._snapshot_paths(str(db_path)) == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
