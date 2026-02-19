#!/usr/bin/env python3
# tests/test_database_verification.py
"""
Testes para as novas funcionalidades de verificação e integridade do banco de dados.
"""

import os

import pandas as pd
import pytest

from armazenamento.database import (
    initialize_database,
    repair_database_if_needed,
    validate_dataframe_before_insert,
    verify_database_integrity,
)

TOTAL_VALID_ROWS = 2  # Constante para evitar magic numbers


class TestDatabaseVerification:  # noqa: D101
    """Testes para verificação de integridade do banco."""

    def test_verify_nonexistent_database(self):
        """No modelo atual, banco inexistente é considerado válido para criação."""
        fake_path = "/path/that/does/not/exist/fake.db"
        report = verify_database_integrity(fake_path)

        assert report['is_valid']  # válido para criação
        assert not report['database_exists']
        assert report.get('needs_creation') is True
        assert len(report['issues']) > 0
        assert "não encontrado" in str(report['issues'])

    def test_verify_valid_database(self, tmp_path):
        """Testa verificação de banco válido."""
        # Criar banco temporário válido
        db_path = os.path.join(tmp_path, 'test.db')
        schema_path = os.path.join(tmp_path, 'schema.sql')

        # Criar schema mínimo
        with open(schema_path, 'w') as f:
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
        report = verify_database_integrity(db_path, table_name='ssas')

        assert report['is_valid']
        assert report['database_exists']
        assert report['database_accessible']
        assert report['table_exists']
        assert report['schema_valid']

    def test_verify_corrupted_database(self, tmp_path):
        """Testa verificação de banco corrompido."""
        # Criar arquivo corrompido (não é SQLite válido)
        db_path = os.path.join(tmp_path, 'corrupted.db')
        with open(db_path, 'w') as f:
            f.write("This is not a valid SQLite file")

        report = verify_database_integrity(db_path)

        assert not report['is_valid']
        assert report['database_exists']
        assert not report['database_accessible']

    def test_verify_empty_file_database(self, tmp_path):
        """Um arquivo vazio (0 bytes) não deve ser considerado acessível ou consistente."""
        db_path = os.path.join(tmp_path, 'empty.db')
        # criar arquivo vazio
        open(db_path, 'w').close()
        assert os.path.exists(db_path)
        assert os.path.getsize(db_path) == 0
        report = verify_database_integrity(db_path)
        assert report['database_exists'] is True
        assert report['database_accessible'] is False
        assert report['data_consistent'] is False
        assert not report['is_valid']


class TestDataValidation:
    """Testes para validação de dados."""

    def test_validate_empty_dataframe(self):
        """Testa validação de DataFrame vazio."""
        df = pd.DataFrame()
        report = validate_dataframe_before_insert(df)

        assert report['is_valid']
        assert report['row_count'] == 0
        assert len(report['warnings']) > 0
        assert "vazio" in str(report['warnings'])

    def test_validate_valid_dataframe(self):
        """Testa validação de DataFrame válido."""
        df = pd.DataFrame({
            'numero_ssa': [202312345, 202398765],
            'situacao': ['Pendente', 'Executada'],
            'data_cadastro': ['2023-12-01 10:00:00', '2023-12-02 15:30:00'],
            'descricao_ssa': ['Teste 1', 'Teste 2']
        })

        report = validate_dataframe_before_insert(df)

        assert report['is_valid']
        assert report['row_count'] == TOTAL_VALID_ROWS
        assert len(report['issues']) == 0

    def test_validate_invalid_ssa_numbers(self):
        """Testa validação com números SSA inválidos."""
        df = pd.DataFrame({
            'numero_ssa': [123, 'invalid', None, 202312345],  # Mistura de válidos e inválidos
            'situacao': ['Pendente', 'Executada', 'Teste', 'Ok'],
            'data_cadastro': ['2023-12-01', '2023-12-02', '2023-12-03', '2023-12-04']
        })

        report = validate_dataframe_before_insert(df)

        # Ainda deve ser considerado válido (só avisos)
        assert report['is_valid']
        assert len(report['warnings']) > 0
        assert "inválidos" in str(report['warnings'])
        assert len(report['invalid_rows']) > 0

    def test_validate_invalid_rows_has_no_duplicate_indexes(self):
        """Garante que invalid_rows nao repete indice para numero_ssa ausente."""
        df = pd.DataFrame({
            'numero_ssa': [None, 202312345],
            'situacao': ['Pendente', 'Executada'],
            'data_cadastro': ['2023-12-01 10:00:00', '2023-12-02 15:30:00'],
        })

        report = validate_dataframe_before_insert(df)

        assert report['invalid_rows'] == [0]

    def test_validate_invalid_dates(self):
        """Testa validação com datas inválidas."""
        df = pd.DataFrame({
            'numero_ssa': [202312345, 202398765],
            'situacao': ['Pendente', 'Executada'],
            'data_cadastro': ['invalid-date', '2023-99-99'],  # Datas inválidas
            'descricao_ssa': ['Teste 1', 'Teste 2']
        })

        report = validate_dataframe_before_insert(df)

        assert report['is_valid']  # Avisos, não erros críticos
        assert len(report['warnings']) > 0
        assert "datas inválidas" in str(report['warnings'])


class TestDatabaseRepair:
    """Testes para reparo de banco de dados."""

    def test_repair_nonexistent_database(self, tmp_path):
        """No modelo atual, reparo não cria banco inexistente automaticamente."""
        db_path = os.path.join(tmp_path, 'new.db')
        schema_path = os.path.join(tmp_path, 'schema.sql')

        # Criar schema
        with open(schema_path, 'w') as f:
            f.write("""
            CREATE TABLE IF NOT EXISTS ssas (
                numero_ssa INTEGER,
                situacao TEXT,
                data_cadastro TEXT,
                descricao_ssa TEXT
            );
            """)

        # Mesmo com schema disponível, lógica atual considera inexistente como "válido para criação"
        result = repair_database_if_needed(db_path, schema_path, table_name='ssas')

        assert result is True
        assert not os.path.exists(db_path)  # não cria automaticamente

        # Confirma estado de "needs_creation"
        report = verify_database_integrity(db_path, table_name='ssas')
        assert report['is_valid']
        assert report.get('needs_creation') is True

    def test_repair_valid_database(self, tmp_path):
        """Testa reparo de banco já válido."""
        db_path = os.path.join(tmp_path, 'valid.db')
        schema_path = os.path.join(tmp_path, 'schema.sql')

        # Criar schema e banco válido (com colunas obrigatórias)
        with open(schema_path, 'w') as f:
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
        result = repair_database_if_needed(db_path, schema_path, table_name='ssas')

        assert result is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
