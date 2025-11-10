# ==============================================================================
# REFERENCE FILE - NOT USED IN PRODUCTION
# ==============================================================================
# Status: Historical snapshot frozen at v3.1
# Created: 2025-09-22 (commit f61d396)
# Purpose: Reference for comparing logic evolution and porting removed behaviors
#
# This file is a frozen copy of core/app_logic.py from v3.1.
# It is NOT imported by any production code.
# The active version is core/app_logic.py
#
# Use cases:
# - Understanding what changed between v3.1 and current version
# - A/B comparison of orchestration logic
# - Recovering specific functionality if needed
#
# DO NOT import this file in production code.
# ==============================================================================

# core/app_logic.py 20250725 103000 (v3.1 - Refatorado, Excecoes, Logging)
"""
Logica central da aplicacao para importacao e atualizacao do banco de dados.

Coordena a verificacao de arquivos modificados, a extracao de dados,
a atualizacao do banco de dados SQLite e o gerenciamento do cache.
"""

import os
import sys
import logging
import pandas as pd
import re
from typing import List, Dict, Any

# Adiciona o diretorio raiz do projeto ao sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils import caching  # noqa: E402
from extracao import extractor  # noqa: E402
from armazenamento import database  # noqa: E402

# Configura logger especifico para este modulo
logger = logging.getLogger(__name__)

# --- Excecoes Personalizadas ---


class ImporterError(Exception):
    """Excecao base para erros no processo de importacao."""
    pass


class CacheError(ImporterError):
    """Erro relacionado ao sistema de cache."""
    pass


class ExtractionError(ImporterError):
    """Erro durante a extracao de dados de um arquivo."""
    pass


class DatabaseError(ImporterError):
    """Erro durante operacoes no banco de dados."""
    pass


class DatabaseConnectionError(DatabaseError):
    """Erro de conexao com o banco de dados."""
    pass


class DatabaseCorruptionError(DatabaseError):
    """Erro indicando corrupcao no banco de dados."""
    pass


class DatabaseSchemaError(DatabaseError):
    """Erro relacionado ao schema do banco de dados."""
    pass


class DatabaseSpaceError(DatabaseError):
    """Erro de espaco insuficiente em disco."""
    pass


class DataValidationError(ImporterError):
    """Erro de validacao de dados antes da insercao."""
    pass


# --- Funcoes Auxiliares Refatoradas ---

def _get_files_to_process(docs_dir: str, cache_file: str, force_import: bool) -> List[str]:
    """
    Determina quais arquivos precisam ser processados.

    Args:
        docs_dir (str): Diretorio de entrada dos arquivos Excel.
        cache_file (str): Caminho para o arquivo de cache.
        force_import (bool): Se True, forca o reprocessamento de todos os arquivos.

    Returns:
        List[str]: Lista de caminhos completos para os arquivos que precisam ser processados.

    Raises:
        CacheError: Se houver um problema ao acessar ou ler o arquivo de cache.
    """
    try:
        if force_import:
            logger.info("Modo 'force_import' ativado. Todos os arquivos serao reprocessados.")
            all_files = caching.get_all_xlsx_files(docs_dir)
            return all_files

        # Verifica se o cache existe
        if not os.path.exists(cache_file):
            logger.info("Arquivo de cache nao encontrado. Todos os arquivos serao processados.")
            all_files = caching.get_all_xlsx_files(docs_dir)
            return all_files

        # Compara arquivos usando o cache
        files_to_process = caching.get_files_to_process(docs_dir, cache_file)
        logger.debug(f"Arquivos identificados para processamento: {len(files_to_process)}")
        return files_to_process

    except Exception as e:
        logger.error(f"Erro ao determinar arquivos para processamento: {e}")
        raise CacheError(f"Falha na verificacao de arquivos: {e}") from e


def _import_single_file(file_path: str, db_path: str, table_name: str) -> bool:
    """
    Importa um unico arquivo Excel para o banco de dados.

    Args:
        file_path (str): Caminho completo para o arquivo Excel.
        db_path (str): Caminho para o banco de dados SQLite.
        table_name (str): Nome da tabela no banco de dados.

    Returns:
        bool: True se a importacao foi bem-sucedida, False caso contrario.

    Raises:
        ExtractionError: Se houver falha na extracao.
        DatabaseError: Se houver falha na insercao no DB.
    """
    logger.info(f"Iniciando importacao de '{file_path}'...")
    try:
        df = extractor.extract_data_from_excel(file_path)
        if df is not None and not df.empty:
            # NOVA: Validar dados antes da insercao
            logger.info(f"Validando dados extraidos de '{file_path}'...")
            validation_report = database.validate_dataframe_before_insert(df, table_name)

            # Log de avisos de validacao
            if validation_report['warnings']:
                for warning in validation_report['warnings']:
                    logger.warning(f"Validacao - {warning}")

            # Se ha problemas criticos, pode escolher entre falhar ou continuar
            if not validation_report['is_valid']:
                critical_issues = validation_report['issues']
                logger.error(f"Dados com problemas criticos em '{file_path}': {critical_issues}")

                # Para problemas criticos de validacao, pode escolher:
                # Opcao 1: Falhar imediatamente
                # raise DataValidationError(f"Dados invalidos: {critical_issues}")

                # Opcao 2: Tentar inserir mesmo assim (atual)
                logger.warning("Tentando insercao apesar dos problemas criticos...")
            else:
                logger.info(
                    "✓ Dados validados: %s linhas prontas para insercao",
                    validation_report['row_count'],
                )

            # CORRECAO CRITICA: Usar smart_upsert para evitar duplicatas
            success = database.insert_dataframe_with_smart_upsert(df, db_path, table_name)
            if success:
                logger.info(f"Importacao de '{file_path}' concluida com sucesso (sem duplicatas).")
                return True
            else:
                logger.error(f"Falha ao inserir dados de '{file_path}' no banco de dados.")
                raise DatabaseError(f"Erro ao inserir dados do arquivo {file_path}")
        else:
            logger.warning(f"Nenhum dado valido extraido de '{file_path}'. Pulando.")
            return True  # Nao e um erro critico, apenas nao ha dados
    except extractor.ExtractionError:
        # Re-levanta erros especificos de extracao
        raise
    except Exception as e:
        logger.error(f"Erro inesperado ao importar '{file_path}': {e}")
        raise ExtractionError(f"Erro ao importar {file_path}") from e


def _update_cache_after_import(
    processed_files: List[str],
    cache_file: str,
    docs_dir: str
) -> None:
    """
    Atualiza o arquivo de cache apos uma importacao bem-sucedida.

    Args:
        processed_files (List[str]): Lista de arquivos processados com sucesso.
        cache_file (str): Caminho para o arquivo de cache.
        docs_dir (str): Diretorio de entrada dos arquivos Excel.

    Raises:
        CacheError: Se houver falha ao atualizar o cache.
    """
    logger.debug("Atualizando cache...")
    try:
        # Atualiza o cache apenas para os arquivos processados com sucesso
        caching.update_cache_for_files(processed_files, cache_file)
        logger.info("Cache atualizado com sucesso.")
    except Exception as e:
        logger.error(f"Erro ao atualizar o cache: {e}")
        raise CacheError("Falha ao atualizar o cache apos importacao.") from e


# --- Funcao Principal Refatorada ---


def run_importer_logic(
    docs_dir: str = 'docs_entrada',
    data_dir: str = 'data',
    db_name: str = 'ssas.db',
    table_name: str = 'ssa_table',
    force_import: bool = False
) -> bool:
    """
    Executa a logica principal de importacao de dados.

    Args:
        docs_dir (str): Diretorio de entrada dos arquivos Excel.
        data_dir (str): Diretorio para armazenamento do banco de dados e cache.
        db_name (str): Nome do arquivo do banco de dados SQLite.
        table_name (str): Nome da tabela no banco de dados.
        force_import (bool): Se True, forca a reimportacao de todos os arquivos.

    Returns:
        bool: True se o banco de dados foi atualizado, False caso contrario.
    """
    logger.info("=== Iniciando processo de importacao ===")

    # --- Configuracao de Caminhos ---
    docs_dir = os.path.join(project_root, docs_dir)
    data_dir = os.path.join(project_root, data_dir)
    db_path = os.path.join(data_dir, db_name)
    cache_file = os.path.join(data_dir, 'file_cache.json')

    try:
        # --- 0. Verificar e reparar integridade do banco de dados ---
        logger.info("Verificando integridade do banco de dados...")

        # Criar diretorio de dados se nao existir
        os.makedirs(data_dir, exist_ok=True)

        # Verificar e reparar banco se necessario
        if not database.repair_database_if_needed(db_path, table_name=table_name):
            logger.error("Falha critica: nao foi possivel garantir integridade do banco de dados")
            raise DatabaseCorruptionError("Banco de dados inacessivel ou corrompido")

        # Verificacao adicional de integridade
        integrity_report = database.verify_database_integrity(db_path, table_name)
        if not integrity_report['is_valid']:
            # Classificar tipo de erro baseado no relatorio
            issues = integrity_report['issues']

            if not integrity_report['database_accessible']:
                raise DatabaseConnectionError(f"Banco de dados inacessivel: {issues}")
            elif not integrity_report['table_exists'] or not integrity_report['schema_valid']:
                raise DatabaseSchemaError(f"Problemas de schema: {issues}")
            elif not integrity_report['data_consistent']:
                raise DatabaseCorruptionError(f"Dados corrompidos: {issues}")
            elif not integrity_report['disk_space_sufficient']:
                raise DatabaseSpaceError(f"Espaco em disco insuficiente: {issues}")
            else:
                raise DatabaseError(f"Problemas gerais no banco: {issues}")

        # Log de avisos se houver
        if integrity_report['warnings']:
            for warning in integrity_report['warnings']:
                logger.warning(f"Aviso do banco: {warning}")

        logger.info("✓ Integridade do banco de dados verificada")

        # --- 1. Determinar arquivos a serem processados ---
        files_to_process = _get_files_to_process(docs_dir, cache_file, force_import)

        if not files_to_process:
            logger.info("Nenhum arquivo novo ou modificado encontrado para processamento.")
            return False

        logger.info(f"{len(files_to_process)} arquivo(s) identificado(s) para importacao.")

        # --- 2. Processar cada arquivo ---
        successfully_processed_files = []
        critical_errors = []

        for file_path in files_to_process:
            base_name = os.path.basename(file_path)
            if base_name.startswith('~$'):
                logger.info("Ignorando arquivo temporario '%s'", base_name)
                continue
            try:
                if _import_single_file(file_path, db_path, table_name):
                    successfully_processed_files.append(file_path)
            except DatabaseConnectionError as e:
                # Erro de conexao - provavelmente fatal para todos os arquivos
                logger.error(f"Erro de conexao com banco ao processar '{file_path}': {e}")
                logger.error("Interrompendo processamento devido a falha de conexao")
                critical_errors.append(('connection', file_path, str(e)))
                break  # Para todo o processamento
            except DatabaseCorruptionError as e:
                # Corrupcao - tentar reparo e continuar
                logger.error(f"Corrupcao detectada ao processar '{file_path}': {e}")
                logger.info("Tentando reparo automatico do banco...")
                if database.repair_database_if_needed(db_path, table_name=table_name):
                    logger.info("Reparo bem-sucedido, continuando processamento...")
                    critical_errors.append(('corruption_repaired', file_path, str(e)))
                    continue  # Tenta processar novamente apos reparo
                else:
                    logger.error("Falha no reparo automatico")
                    critical_errors.append(('corruption_failed', file_path, str(e)))
                    break  # Para todo o processamento
            except DatabaseSpaceError as e:
                # Espaco insuficiente - provavelmente fatal
                logger.error(f"Espaco em disco insuficiente ao processar '{file_path}': {e}")
                critical_errors.append(('space', file_path, str(e)))
                break  # Para todo o processamento
            except DatabaseSchemaError as e:
                # Problema de schema - tentar recriar
                logger.error(f"Erro de schema ao processar '{file_path}': {e}")
                logger.info("Tentando recriacao do schema...")
                if database.initialize_database(db_path):
                    logger.info("Schema recriado, continuando processamento...")
                    critical_errors.append(('schema_repaired', file_path, str(e)))
                    continue  # Tenta processar novamente
                else:
                    logger.error("Falha na recriacao do schema")
                    critical_errors.append(('schema_failed', file_path, str(e)))
                    break
            except DataValidationError as e:
                # Dados invalidos - continua com proximo arquivo
                logger.warning(f"Dados invalidos em '{file_path}': {e}. Pulando arquivo...")
                critical_errors.append(('validation', file_path, str(e)))
                continue
            except ExtractionError as e:
                # Erro de extracao - continua com proximo arquivo
                logger.warning(f"Erro de extracao em '{file_path}': {e}. Pulando arquivo...")
                critical_errors.append(('extraction', file_path, str(e)))
                continue
            except DatabaseError as e:
                # Erro generico de banco - log e continua
                logger.error(f"Erro de banco ao processar '{file_path}': {e}. Continuando...")
                critical_errors.append(('database_generic', file_path, str(e)))
                continue
            except Exception as e:
                # Erro inesperado - log e continua
                logger.error(f"Erro inesperado ao processar '{file_path}': {e}. Continuando...")
                critical_errors.append(('unexpected', file_path, str(e)))
                continue

        # Log de resumo de erros
        if critical_errors:
            logger.warning(f"Processamento concluido com {len(critical_errors)} erro(s):")
            for error_type, file_path, message in critical_errors:
                logger.warning(f"  - {error_type}: {os.path.basename(file_path)} -> {message}")

        # --- 3. Atualizar cache apenas se houve sucesso ---
        if successfully_processed_files:
            _update_cache_after_import(successfully_processed_files, cache_file, docs_dir)
            logger.info("=== Processo de importacao concluido com atualizacoes ===")
            return True
        else:
            logger.info("Nenhum arquivo foi processado com sucesso.")
            return False

    except ImporterError:
        # Re-levanta excecoes personalizadas
        raise
    except Exception as e:
        logger.critical(f"Erro inesperado no processo de importacao: {e}", exc_info=True)
        raise ImporterError("Erro critico no processo de importacao.") from e


def parse_search_terms(
    search_terms: List[str],
    default_mode: str = 'contains',
) -> List[Dict[str, Any]]:
    """
    Converte termos brutos em uma estrutura padronizada com modo e polaridade.

    Modos aceitos por termo:
    - contem (padrao): foo
    - comeca com: ^foo
    - termina com: foo$
    - igual: =foo
    - regex: ~foo.*bar
    Negativo: prefixar ! (ou -) antes do termo (ex.: !^adm, !=fechado, !$2025, !~regex)

    Conectivos aceitos (case-insensitive):
    - OU / OR / || (agrupa condicoes como disjuncao)
    - E / AND / && (tratado como conjuncao implicita)
    """
    parsed: List[Dict[str, Any]] = []
    if not search_terms:
        return parsed
    if not isinstance(search_terms, list):
        return parsed

    def _tokenize_inputs(raw_terms: List[str]) -> List[str]:
        tokens: List[str] = []
        pattern = re.compile(r'(?i)(\|\||&&|\bOU\b|\bOR\b|\bAND\b|\bE\b|(?<=\S)[vV](?=\S))')
        for raw in raw_terms:
            if not isinstance(raw, str):
                continue
            normalized = raw.replace(',', ' AND ')
            normalized = normalized.replace('∨', ' OR ').replace('∧', ' AND ')
            parts = pattern.split(normalized)
            for part in parts:
                if not part:
                    continue
                piece = part.strip()
                if piece:
                    tokens.append(piece)
        return tokens

    def _split_segments(tokens: List[str]) -> List[List[str]]:
        segments: List[List[str]] = []
        current: List[str] = []
        for token in tokens:
            lower = token.lower()
            if lower in {'or', 'ou', '||', '∨', 'v'}:
                if current:
                    segments.append(current)
                    current = []
                continue
            if lower in {'and', 'e', '&&', '∧', '^'}:
                continue
            current.append(token)
        if current:
            segments.append(current)
        if not segments:
            segments.append([])
        return segments

    tokens = _tokenize_inputs(search_terms)
    segments = _split_segments(tokens)

    allowed_modes = {'contains', 'prefix', 'suffix', 'exact', 'regex'}
    fallback_mode = default_mode if default_mode in allowed_modes else 'contains'

    for group_index, segment in enumerate(segments):
        if not segment:
            continue
        for raw in segment:
            if not isinstance(raw, str):
                continue
            t = raw.strip()
            if not t:
                continue
            negative = False
            if (t.startswith('!') or t.startswith('-')) and len(t) > 1:
                negative = True
                t = t[1:]
            mode = fallback_mode
            value = t
            if t.startswith('~') and len(t) > 1:
                mode = 'regex'
                value = t[1:]
            elif t.startswith('=') and len(t) > 1:
                mode = 'exact'
                value = t[1:]
            elif t.startswith('$') and len(t) > 1:
                mode = 'suffix'
                value = t[1:]
            elif fallback_mode != 'regex' and t.startswith('^') and len(t) > 1:
                mode = 'prefix'
                value = t[1:]
            elif fallback_mode != 'regex' and t.endswith('$') and len(t) > 1:
                mode = 'suffix'
                value = t[:-1]
            parsed.append({
                'raw': raw,
                'mode': mode,
                'value': value,
                'negative': negative,
                'group': group_index,
            })
    return parsed


def filter_dataframe(df: pd.DataFrame, search_terms: list) -> pd.DataFrame:
    """
    Filtra um DataFrame com base em uma lista de termos de busca (strings) ou
    termos ja parseados por parse_search_terms(). Busca em todas as colunas de texto.

    Modos por termo: contem (padrao), comeca (^), termina ($), igual (=), regex (~),
    com suporte a negativos (! ou -).
    """
    if df is None or df.empty or not search_terms:
        return df

    # Extrai colunas de texto base para buscas (sem lower; usaremos case=False nos metodos)
    base_str_df = df.select_dtypes(include=['object']).astype(str)
    if base_str_df.shape[1] == 0:
        # Sem colunas de texto, nao ha onde buscar: retorna o proprio df
        return df

    # Permite tanto termos brutos (str) quanto parseados (dict)
    if search_terms and isinstance(search_terms[0], dict):
        terms = search_terms  # ja parseados
    else:
        terms = parse_search_terms(search_terms)

    grouped_terms: Dict[int, List[Dict[str, Any]]] = {}
    for term in terms:
        group_idx = term.get('group')
        if group_idx is None:
            group_idx = 0
        grouped_terms.setdefault(int(group_idx), []).append(term)

    if not grouped_terms:
        return df

    def _mask_for_term(term: Dict[str, Any]) -> pd.Series:
        mode = term.get('mode', 'contains')
        value = term.get('value', '') or ''

        def _contains(pattern: str, *, regex: bool) -> pd.Series:
            return base_str_df.apply(
                lambda col: col.str.contains(pattern, case=False, na=False, regex=regex)
            ).any(axis=1)

        if mode == 'contains':
            return _contains(value, regex=False)
        if mode == 'prefix':
            pattern = f"^{re.escape(value)}"
            return _contains(pattern, regex=True)
        if mode == 'suffix':
            pattern = f"{re.escape(value)}$"
            return _contains(pattern, regex=True)
        if mode == 'exact':
            pattern = f"^{re.escape(value)}$"
            return _contains(pattern, regex=True)
        if mode == 'regex':
            try:
                return _contains(value, regex=True)
            except re.error:
                return _contains(value, regex=False)
        return _contains(value, regex=False)

    final_mask = pd.Series(False, index=df.index)

    for group_terms in grouped_terms.values():
        if not group_terms:
            continue
        group_mask = pd.Series(True, index=df.index)
        positives = [t for t in group_terms if not t.get('negative')]
        negatives = [t for t in group_terms if t.get('negative')]

        for term in positives:
            group_mask = group_mask & _mask_for_term(term)

        for term in negatives:
            group_mask = group_mask & (~_mask_for_term(term))

        final_mask = final_mask | group_mask

    if final_mask.any():
        return df[final_mask]
    return df.iloc[0:0] if grouped_terms else df


def import_files_to_database(
    docs_dir: str,
    db_path: str = "data/ssas.db",
    force_import: bool = False,
) -> bool:
    """
    Importa arquivos de um diretorio para o banco de dados.

    Args:
        docs_dir: Diretorio contendo arquivos Excel
        db_path: Caminho para o banco de dados
        force_import: Se True, forca reimportacao de todos os arquivos

    Returns:
        bool: True se importacao foi bem-sucedida
    """
    try:
        # Extrair diretorio e nome do banco
        data_dir = os.path.dirname(db_path)
        db_name = os.path.basename(db_path)

        # Criar diretorio de dados se nao existir
        os.makedirs(data_dir, exist_ok=True)

        # Executar logica de importacao
        success = run_importer_logic(
            docs_dir=docs_dir,
            data_dir=data_dir,
            db_name=db_name,
            table_name="ssas",
            force_import=force_import
        )

        return success

    except Exception as e:
        logger.error(f"Erro na importacao de arquivos: {e}")
        return False


def get_filtered_data(
    db_path: str = "data/ssas.db",
    filters: Dict[str, Any] | None = None,
) -> pd.DataFrame:
    """
    Obtem dados filtrados do banco de dados.

    Args:
        db_path: Caminho para o banco de dados
        filters: Dicionario com filtros a aplicar

    Returns:
        DataFrame com dados filtrados
    """
    try:
        # Conectar ao banco e obter dados
        with database.get_db_connection(db_path) as conn:
            query = "SELECT * FROM ssas"
            df = pd.read_sql_query(query, conn)

        # Aplicar filtros se fornecidos
        if filters:
            for column, value in filters.items():
                if column in df.columns and value is not None:
                    # Aplicar filtro case-insensitive
                    df = df[df[column].astype(str).str.contains(str(value), case=False, na=False)]

        return df

    except Exception as e:
        logger.error(f"Erro ao obter dados filtrados: {e}")
        return pd.DataFrame()  # Retorna DataFrame vazio em caso de erro
