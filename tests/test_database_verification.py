#!/usr/bin/env python3
# tests/test_database_verification.py
"""
Testes para as novas funcionalidades de verificação e integridade do banco de dados.
"""

import pytest
import tempfile
import os
import shutil
import sqlite3
import pandas as pd
from unittest.mock import patch

# Importar funções que queremos testar
from armazenamento.database import (
    verify_database_integrity,
    validate_dataframe_before_insert,
    repair_database_if_needed,
    get_db_connection,
    initialize_database
)

class TestDatabaseVerification:
    """Testes para verificação de integridade do banco."""
    
    def test_verify_nonexistent_database(self):
        """Testa verificação de banco que não existe."""
        fake_path = "/path/that/does/not/exist/fake.db"
        report = verify_database_integrity(fake_path)
        
        assert not report['is_valid']
        assert not report['database_exists']
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
        
        # Verificar integridade
        report = verify_database_integrity(db_path)
        
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
        assert report['row_count'] == 2
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
        """Testa reparo de banco que não existe."""
        db_path = os.path.join(tmp_path, 'new.db')
        schema_path = os.path.join(tmp_path, 'schema.sql')
        
        # Criar schema
        with open(schema_path, 'w') as f:
            f.write("""
            CREATE TABLE IF NOT EXISTS ssas (
                numero_ssa INTEGER,
                situacao TEXT
            );
            """)
        
        # Mockar para usar nosso schema temporário
        with patch('armazenamento.database.schema_file', os.path.basename(schema_path)):
            result = repair_database_if_needed(db_path, schema_path)
        
        assert result is True
        assert os.path.exists(db_path)
        
        # Verificar se banco foi criado corretamente
        with get_db_connection(db_path) as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            assert 'ssas' in tables
    
    def test_repair_valid_database(self, tmp_path):
        """Testa reparo de banco já válido."""
        db_path = os.path.join(tmp_path, 'valid.db')
        schema_path = os.path.join(tmp_path, 'schema.sql')
        
        # Criar schema e banco válido
        with open(schema_path, 'w') as f:
            f.write("""
            CREATE TABLE IF NOT EXISTS ssas (
                numero_ssa INTEGER,
                situacao TEXT
            );
            """)
        
        initialize_database(db_path, schema_path)
        
        # Reparo deve retornar True (sem fazer nada)
        result = repair_database_if_needed(db_path, schema_path)
        
        assert result is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
