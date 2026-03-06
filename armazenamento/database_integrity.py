"""Funcoes de verificacao e reparo extraidas de `database.py`.

Publicadas novamente atraves de `database` para compatibilidade.

CIRCULAR DEPENDENCY MITIGATION:
This module is imported lazily by database.py (inside functions). This module imports
from database.py using lazy imports (inside functions) to avoid circular import errors.
All imports from database.py must be lazy (inside functions).
DO NOT add top-level imports from database.py.
"""
# Last modified: 2025-10-29T11:05:00 (circular import documentation)
from __future__ import annotations

import logging
from .identifier_utils import is_valid_identifier
import os
import shutil
from datetime import datetime
from typing import Any
import pandas as pd

# Lazy imports from database.py to avoid circular dependency (see lines 82, 100, 117, etc.)

logger = logging.getLogger(__name__)

MIN_FREE_SPACE_GB_WARN = 0.1


def verify_database_integrity(
    db_path: str,
    table_name: str = 'ssas',
) -> dict[str, Any]:  # noqa: PLR0912, PLR0915
    report: dict[str, Any] = {
        'is_valid': True,
        'issues': [],
        'warnings': [],
        'database_exists': False,
        'database_accessible': False,
        'table_exists': False,
        'schema_valid': False,
        'data_consistent': False,
        'disk_space_sufficient': False,
        'file_permissions_ok': False,
        'needs_creation': False,
    }
    try:
        if not os.path.exists(db_path):
            # Mensagem com acento para alinhar aos testes e melhorar UX
            report['issues'].append(f"Arquivo do banco de dados não encontrado: {db_path}")
            report['needs_creation'] = True
            report['is_valid'] = False
            return report
        report['database_exists'] = True
        # Tamanho do arquivo
        try:
            if os.path.getsize(db_path) == 0:
                report['issues'].append(
                    "Arquivo de banco encontrado mas vazio (0 bytes) - invalido"
                )
                report['is_valid'] = False
                return report
        except Exception as e:  # pragma: no cover
            report['warnings'].append(f"Falha ao obter tamanho do arquivo: {e}")
        # Permissoes
        try:
            if not os.access(db_path, os.R_OK | os.W_OK):
                report['issues'].append(f"Permissoes insuficientes para o banco: {db_path}")
                report['is_valid'] = False
            else:
                report['file_permissions_ok'] = True
        except Exception as e:
            report['issues'].append(f"Erro ao verificar permissoes: {e}")
            report['is_valid'] = False
        # Espaco em disco
        try:
            db_dir = os.path.dirname(db_path) or '.'
            statvfs = os.statvfs(db_dir) if hasattr(os, 'statvfs') else None
            if statvfs:
                free_space_gb = (statvfs.f_frsize * statvfs.f_bavail) / (1024 ** 3)
            else:
                free_space_gb = shutil.disk_usage(db_dir).free / (1024 ** 3)
            if free_space_gb >= MIN_FREE_SPACE_GB_WARN:
                report['disk_space_sufficient'] = True
            else:
                report['warnings'].append(
                    f"Pouco espaco em disco: {free_space_gb:.2f}GB disponivel"
                )
        except Exception as e:
            report['warnings'].append(f"Nao foi possivel verificar espaco em disco: {e}")
        # PRAGMA integrity_check
        try:
            from .database import get_db_connection  # lazy
            with get_db_connection(db_path) as conn:
                cursor = conn.execute("PRAGMA integrity_check")
                integrity_result = cursor.fetchone()
                if not integrity_result or integrity_result[0] != 'ok':
                    report['issues'].append(
                        f"Falha na verificacao de integridade SQLite: {integrity_result}"
                    )
                    report['is_valid'] = False
                    return report
                report['database_accessible'] = True
                report['data_consistent'] = True
        except Exception as e:
            report['issues'].append(f"Banco de dados nao acessivel: {e}")
            report['is_valid'] = False
            return report
        # Tabela existe?
        try:
            from .database import get_db_connection  # lazy
            with get_db_connection(db_path) as conn:
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                    (table_name,),
                )
                if cursor.fetchone():
                    report['table_exists'] = True
                else:
                    report['issues'].append(f"Tabela '{table_name}' nao encontrada")
                    report['is_valid'] = False
        except Exception as e:
            report['issues'].append(f"Erro ao verificar tabela: {e}")
            report['is_valid'] = False
        if report['table_exists']:
            try:
                required_columns = ['numero_ssa', 'situacao', 'data_cadastro', 'descricao_ssa']
                from .database import get_db_connection  # lazy
                with get_db_connection(db_path) as conn:
                    if not is_valid_identifier(table_name):
                        raise ValueError(f"Invalid SQL identifier: {table_name}")
                    cursor = conn.execute(f"PRAGMA table_info({table_name})")  # noqa: S608
                    existing_columns = [row[1] for row in cursor.fetchall()]
                if 'arquivo_origem' not in existing_columns:
                    try:
                        from .database import ensure_column_exists  # lazy
                        if ensure_column_exists(db_path, table_name, 'arquivo_origem', 'TEXT'):
                            existing_columns.append('arquivo_origem')
                    except Exception:
                        report['warnings'].append("Coluna 'arquivo_origem' ausente; nao foi possivel adiciona-la automaticamente.")
                missing = [c for c in required_columns if c not in existing_columns]
                if missing:
                    report['issues'].append(f"Colunas obrigatorias ausentes: {missing}")
                    report['is_valid'] = False
                else:
                    report['schema_valid'] = True
            except Exception as e:
                report['issues'].append(f"Erro ao verificar schema: {e}")
                report['is_valid'] = False
        status_text = " Valido" if report['is_valid'] else " Problemas encontrados"
        logger.info("Verificacao de integridade concluida. Status: %s", status_text)
    except Exception as e:  # pragma: no cover
        report['issues'].append(f"Erro inesperado na verificacao: {e}")
        report['is_valid'] = False
    return report


def repair_database_if_needed(
    db_path: str,
    schema_file: str = 'schema.sql',
    table_name: str = 'ssas',
) -> bool:  # noqa: PLR0912
    logger.info("Iniciando verificacao e reparo do banco de dados...")
    try:
        integrity_report = verify_database_integrity(db_path, table_name)
        if integrity_report['is_valid']:
            logger.info("Banco de dados integro - nenhum reparo necessario")
            return True
        logger.warning("Problemas detectados no banco: %s", integrity_report['issues'])
        repaired = False
        if not integrity_report['database_exists']:
            logger.info("Criando novo banco de dados...")
            from .database import initialize_database  # lazy
            initialize_database(db_path, schema_file)
            repaired = True
        elif not integrity_report['table_exists']:
            logger.info("Recriando schema do banco...")
            from .database import initialize_database  # lazy
            initialize_database(db_path, schema_file)
            repaired = True
        elif not integrity_report['data_consistent']:
            logger.warning("Detectada corrupcao no banco - tentando backup/restore...")
            backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            try:
                shutil.copy2(db_path, backup_path)
                logger.info("Backup criado em: %s", backup_path)
                from .database import get_db_connection, initialize_database  # lazy
                from . import database_upsert_logic as _up
                with get_db_connection(db_path) as conn:
                    try:
                        df_backup = pd.read_sql_query("SELECT * FROM ssas", conn)
                        if not df_backup.empty:
                            os.remove(db_path)
                            initialize_database(db_path, schema_file)
                            if _up.insert_dataframe_with_smart_upsert_impl(df_backup, db_path, 'ssas'):
                                logger.info("Dados restaurados com sucesso apos correcao")
                                repaired = True
                    except Exception as e:  # pragma: no cover
                        logger.error("Nao foi possivel extrair dados do banco corrompido: %s", e)
            except Exception as e:  # pragma: no cover
                logger.error("Falha no processo de backup/restore: %s", e)
        if repaired:
            final_check = verify_database_integrity(db_path, table_name)
            if final_check['is_valid']:
                logger.info("Reparo do banco de dados concluido com sucesso")
                return True
            logger.error("Reparo falhou - problemas persistem")
            return False
        logger.error("Nenhum reparo foi possivel para os problemas detectados")
        return False
    except Exception as e:  # pragma: no cover
        logger.error("Erro durante tentativa de reparo: %s", e)
        return False
