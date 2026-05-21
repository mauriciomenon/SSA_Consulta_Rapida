#!/usr/bin/env python3
# tests/test_database_verification.py
"""
Testes para as novas funcionalidades de verificação e integridade do banco de dados.
"""

import os
import sqlite3
from pathlib import Path

import pandas as pd
import pytest

import armazenamento.database_integrity as database_integrity_module
import armazenamento.database_upsert_logic as database_upsert_logic
import armazenamento.database_validation as database_validation
from armazenamento.database import (
    ensure_column_exists,
    initialize_database,
    query_db,
    repair_database_if_needed,
    validate_dataframe_before_insert,
    verify_database_integrity,
)
from utils.db_maintenance import DatabaseAnalyzer, DatabaseMigrator

TOTAL_VALID_ROWS = 2  # Constante para evitar magic numbers


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

        # Criar schema mínimo
        with open(schema_path, "w") as f:
            f.write("""
            CREATE TABLE IF NOT EXISTS ssas (
                numero_ssa INTEGER,
                situacao TEXT,
                data_cadastro TEXT,
                descricao_ssa TEXT
            );
            """)

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
        conn = sqlite3.connect(db_path)
        conn.execute(
            """
            CREATE TABLE ssa_table (
                numero_ssa INTEGER,
                situacao TEXT,
                data_cadastro TEXT,
                descricao_ssa TEXT
            )
            """
        )
        conn.commit()
        conn.close()

        report = verify_database_integrity(db_path, table_name="ssas")

        assert report["is_valid"] is True
        assert report["table_name"] == "ssa_table"
        assert report["table_exists"] is True

    def test_verify_prefers_table_over_view_when_both_exist(self, tmp_path):
        """Quando alias existe como view e tabela canonica existe, deve priorizar tabela."""
        db_path = os.path.join(tmp_path, "prefer_table_over_view.db")
        conn = sqlite3.connect(db_path)
        conn.execute(
            """
            CREATE TABLE ssa_table (
                numero_ssa INTEGER,
                situacao TEXT,
                data_cadastro TEXT,
                descricao_ssa TEXT
            )
            """
        )
        conn.execute("CREATE VIEW ssas AS SELECT * FROM ssa_table")
        conn.commit()
        conn.close()

        report = verify_database_integrity(db_path, table_name="ssas")

        assert report["is_valid"] is True
        assert report["table_name"] == "ssa_table"
        assert report["table_exists"] is True

    def test_verify_view_only_alias_is_accepted(self, tmp_path):
        """Quando so existe uma view compativel, o report nao deve falhar por falso negativo."""
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

        assert report["is_valid"] is True
        assert report["table_name"] == "ssas"
        assert report["table_exists"] is True

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

        # Criar schema
        with open(schema_path, "w") as f:
            f.write("""
            CREATE TABLE IF NOT EXISTS ssas (
                numero_ssa INTEGER,
                situacao TEXT,
                data_cadastro TEXT,
                descricao_ssa TEXT
            );
            """)

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

        with open(schema_path, "w") as f:
            f.write("""
            CREATE TABLE IF NOT EXISTS ssas (
                numero_ssa INTEGER,
                situacao TEXT,
                data_cadastro TEXT,
                descricao_ssa TEXT
            );
            """)

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

        with open(schema_path, "w") as f:
            f.write("""
            CREATE TABLE IF NOT EXISTS ssa_table (
                numero_ssa INTEGER,
                situacao TEXT,
                data_cadastro TEXT,
                descricao_ssa TEXT
            );
            """)

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
                """
                CREATE TABLE ssa_table (
                    numero_ssa INTEGER,
                    descricao_ssa TEXT
                )
                """
            )
            conn.commit()

        report = verify_database_integrity(db_path, table_name="ssa_table")

        assert report["is_valid"] is False
        assert sorted(report["missing_required_columns"]) == [
            "data_cadastro",
            "situacao",
        ]
        assert report["repair_suggestion"] is not None

    def test_repair_adds_missing_required_columns_when_table_exists(self, tmp_path):
        """Reparo minimo deve adicionar colunas obrigatorias ausentes quando a tabela ja existe."""
        db_path = os.path.join(tmp_path, "repair_missing_required.db")
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                """
                CREATE TABLE ssa_table (
                    numero_ssa INTEGER,
                    descricao_ssa TEXT
                )
                """
            )
            conn.commit()

        schema_path = os.path.join(tmp_path, "schema.sql")
        with open(schema_path, "w") as f:
            f.write(
                """
                CREATE TABLE IF NOT EXISTS ssa_table (
                    numero_ssa INTEGER,
                    situacao TEXT,
                    data_cadastro TEXT,
                    descricao_ssa TEXT
                );
                """
            )

        result = repair_database_if_needed(db_path, schema_path, table_name="ssa_table")

        assert result is True
        columns = query_db(db_path, "ssa_table").columns.tolist()
        assert "situacao" in columns
        assert "data_cadastro" in columns

    def test_repair_adds_required_and_optional_columns_in_single_pass(self, tmp_path):
        """Reparo unico deve resolver faltas obrigatorias e opcionais no mesmo ciclo."""
        db_path = os.path.join(tmp_path, "repair_missing_required_and_optional.db")
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                """
                CREATE TABLE ssa_table (
                    numero_ssa INTEGER,
                    descricao_ssa TEXT
                )
                """
            )
            conn.commit()

        schema_path = os.path.join(tmp_path, "schema.sql")
        with open(schema_path, "w") as f:
            f.write(
                """
                CREATE TABLE IF NOT EXISTS ssa_table (
                    numero_ssa INTEGER,
                    situacao TEXT,
                    data_cadastro TEXT,
                    descricao_ssa TEXT
                );
                """
            )

        result = repair_database_if_needed(db_path, schema_path, table_name="ssa_table")

        assert result is True
        columns = query_db(db_path, "ssa_table").columns.tolist()
        assert "situacao" in columns
        assert "data_cadastro" in columns
        assert "arquivo_origem" in columns
        assert "data_planilha" in columns
        report = verify_database_integrity(db_path, table_name="ssa_table")
        assert report["missing_optional_columns"] == []

    def test_repair_nonexistent_database_avoids_false_warning(self, tmp_path, caplog):
        """Banco ausente em bootstrap nao deve logar warning generico de problema."""
        db_path = os.path.join(tmp_path, "new_bootstrap.db")
        schema_path = os.path.join(tmp_path, "schema.sql")

        with open(schema_path, "w") as f:
            f.write("""
            CREATE TABLE IF NOT EXISTS ssas (
                numero_ssa INTEGER,
                situacao TEXT,
                data_cadastro TEXT,
                descricao_ssa TEXT
            );
            """)

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
        with open(schema_path, "w") as f:
            f.write("""
            CREATE TABLE IF NOT EXISTS ssas (
                numero_ssa INTEGER,
                situacao TEXT,
                data_cadastro TEXT,
                descricao_ssa TEXT
            );
            """)

        initialize_database(db_path, schema_path)

        # Reparo deve retornar True (sem fazer nada) usando tabela 'ssas'
        result = repair_database_if_needed(db_path, schema_path, table_name="ssas")

        assert result is True

    def test_repair_failed_restore_preserves_original_database(
        self, tmp_path, monkeypatch
    ):
        """Falha no restore nao deve apagar o banco original antes da substituicao segura."""
        db_path = os.path.join(tmp_path, "restore_preserves_original.db")
        schema_path = os.path.join(tmp_path, "schema.sql")

        with open(schema_path, "w") as f:
            f.write("""
            CREATE TABLE IF NOT EXISTS ssa_table (
                numero_ssa INTEGER,
                situacao TEXT,
                data_cadastro TEXT,
                descricao_ssa TEXT
            );
            """)

        initialize_database(db_path, schema_path)
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                """
                INSERT INTO ssa_table (numero_ssa, situacao, data_cadastro, descricao_ssa)
                VALUES (?, ?, ?, ?)
                """,
                (202312345, "STE", "2023-12-01 10:00:00", "Original"),
            )
            conn.commit()

        monkeypatch.setattr(
            database_integrity_module,
            "verify_database_integrity",
            lambda *_args, **_kwargs: {
                "is_valid": False,
                "issues": ["forced corruption"],
                "warnings": [],
                "database_exists": True,
                "database_accessible": True,
                "table_exists": True,
                "schema_valid": True,
                "data_consistent": False,
                "disk_space_sufficient": True,
                "file_permissions_ok": True,
                "needs_creation": False,
                "missing_optional_columns": [],
                "table_name": "ssa_table",
            },
        )
        monkeypatch.setattr(
            database_upsert_logic,
            "insert_dataframe_with_smart_upsert_impl",
            lambda *_args, **_kwargs: False,
        )

        result = repair_database_if_needed(db_path, schema_path, table_name="ssa_table")

        assert result is False
        with sqlite3.connect(db_path) as conn:
            row_count = conn.execute("SELECT COUNT(*) FROM ssa_table").fetchone()[0]
        assert row_count == 1

    def test_repair_restores_backup_when_final_validation_fails(
        self, tmp_path, monkeypatch
    ):
        db_path = os.path.join(tmp_path, "restore_after_final_failure.db")
        schema_path = os.path.join(tmp_path, "schema.sql")

        with open(schema_path, "w") as f:
            f.write("""
            CREATE TABLE IF NOT EXISTS ssa_table (
                numero_ssa INTEGER,
                situacao TEXT,
                data_cadastro TEXT,
                descricao_ssa TEXT
            );
            """)

        initialize_database(db_path, schema_path)
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                """
                INSERT INTO ssa_table (numero_ssa, situacao, data_cadastro, descricao_ssa)
                VALUES (?, ?, ?, ?)
                """,
                (202312347, "STE", "2023-12-03 10:00:00", "Original final"),
            )
            conn.commit()

        calls = {"db_path": 0}

        def _fake_verify(path, table_name="ssa_table"):
            if path == db_path:
                calls["db_path"] += 1
                return {
                    "is_valid": False,
                    "issues": ["forced final validation failure"],
                    "warnings": [],
                    "database_exists": True,
                    "database_accessible": True,
                    "table_exists": True,
                    "schema_valid": True,
                    "data_consistent": False,
                    "disk_space_sufficient": True,
                    "file_permissions_ok": True,
                    "needs_creation": False,
                    "missing_optional_columns": [],
                    "table_name": table_name,
                }
            return {
                "is_valid": True,
                "issues": [],
                "warnings": [],
                "database_exists": True,
                "database_accessible": True,
                "table_exists": True,
                "schema_valid": True,
                "data_consistent": True,
                "disk_space_sufficient": True,
                "file_permissions_ok": True,
                "needs_creation": False,
                "missing_optional_columns": [],
                "table_name": table_name,
            }

        monkeypatch.setattr(
            database_integrity_module,
            "verify_database_integrity",
            _fake_verify,
        )
        monkeypatch.setattr(
            database_upsert_logic,
            "insert_dataframe_with_smart_upsert_impl",
            lambda *_args, **_kwargs: True,
        )

        result = repair_database_if_needed(db_path, schema_path, table_name="ssa_table")

        assert result is False
        with sqlite3.connect(db_path) as conn:
            row = conn.execute(
                "SELECT descricao_ssa FROM ssa_table WHERE numero_ssa = ?",
                (202312347,),
            ).fetchone()
        assert row == ("Original final",)

    def test_repair_prefers_restore_flow_before_reinitialize_when_corrupted(
        self, tmp_path, monkeypatch
    ):
        """Caminho de corrupcao nao deve reusar initialize_database diretamente no banco original."""
        db_path = os.path.join(tmp_path, "corrupted_prefers_restore.db")
        schema_path = os.path.join(tmp_path, "schema.sql")

        with open(schema_path, "w") as f:
            f.write(
                """
                CREATE TABLE IF NOT EXISTS ssa_table (
                    numero_ssa INTEGER,
                    situacao TEXT,
                    data_cadastro TEXT,
                    descricao_ssa TEXT
                );
                """
            )

        initialize_database(db_path, schema_path)
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                """
                INSERT INTO ssa_table (numero_ssa, situacao, data_cadastro, descricao_ssa)
                VALUES (?, ?, ?, ?)
                """,
                (202312346, "STE", "2023-12-02 11:00:00", "Restore branch"),
            )
            conn.commit()

        real_verify = database_integrity_module.verify_database_integrity
        calls = {"count": 0}

        def _fake_verify(path, table_name="ssa_table"):
            if path == db_path and calls["count"] == 0:
                calls["count"] += 1
                return {
                    "is_valid": False,
                    "issues": ["forced corruption branch"],
                    "warnings": [],
                    "database_exists": True,
                    "database_accessible": False,
                    "table_exists": False,
                    "schema_valid": False,
                    "data_consistent": False,
                    "disk_space_sufficient": True,
                    "file_permissions_ok": True,
                    "needs_creation": False,
                    "missing_required_columns": [],
                    "missing_optional_columns": [],
                    "repair_suggestion": None,
                    "table_name": "ssa_table",
                }
            return real_verify(path, table_name=table_name)

        initialize_calls: list[str] = []

        def _guarded_initialize(path, schema):
            initialize_calls.append(path)
            assert path != db_path
            return initialize_database(path, schema)

        monkeypatch.setattr(
            database_integrity_module, "verify_database_integrity", _fake_verify
        )
        monkeypatch.setattr(
            "armazenamento.database.initialize_database", _guarded_initialize
        )

        result = repair_database_if_needed(db_path, schema_path, table_name="ssa_table")

        assert result in (True, False)
        assert any(path != db_path for path in initialize_calls)
        assert all(path != db_path for path in initialize_calls)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
