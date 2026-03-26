#!/usr/bin/env python3
# tests/test_database_verification.py
"""
Testes para as novas funcionalidades de verificação e integridade do banco de dados.
"""

import os
import sqlite3

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

TOTAL_VALID_ROWS = 2  # Constante para evitar magic numbers


class TestDatabaseVerification:  # noqa: D101
    """Testes para verificação de integridade do banco."""

    def test_ensure_column_exists_no_error_when_table_absent(self, tmp_path, caplog):
        """Nao deve logar erro quando a tabela ainda nao existe no bootstrap."""
        db_path = os.path.join(tmp_path, "no_table_yet.db")

        added = ensure_column_exists(db_path, "ssa_table", "arquivo_origem", "TEXT")

        assert added is False
        assert "Falha ao garantir coluna" not in caplog.text

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
        assert len(report["issues"]) == 0

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
        assert "inválidos" in str(report["warnings"])
        assert len(report["invalid_rows"]) > 0

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

    def test_validate_invalid_dates(self):
        """Testa validação com datas inválidas."""
        df = pd.DataFrame(
            {
                "numero_ssa": [202312345, 202398765],
                "situacao": ["Pendente", "Executada"],
                "data_cadastro": ["invalid-date", "2023-99-99"],  # Datas inválidas
                "descricao_ssa": ["Teste 1", "Teste 2"],
            }
        )

        report = validate_dataframe_before_insert(df)

        assert report["is_valid"]  # Avisos, não erros críticos
        assert len(report["warnings"]) > 0
        assert "datas inválidas" in str(report["warnings"])

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
