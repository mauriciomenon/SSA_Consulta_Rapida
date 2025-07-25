# core/app_logic.py 20250725 103000 (v3.1 - Refatorado, Exceções, Logging)
"""
Lógica central da aplicação para importação e atualização do banco de dados.

Coordena a verificação de arquivos modificados, a extração de dados,
a atualização do banco de dados SQLite e o gerenciamento do cache.
"""

import os
import sys
import logging
import pandas as pd
from typing import List, Set

# Adiciona o diretório raiz do projeto ao sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils import caching
from extracao import extractor
from armazenamento import database

# Configura logger específico para este módulo
logger = logging.getLogger(__name__)

# --- Exceções Personalizadas ---

class ImporterError(Exception):
    """Exceção base para erros no processo de importação."""
    pass

class CacheError(ImporterError):
    """Erro relacionado ao sistema de cache."""
    pass

class ExtractionError(ImporterError):
    """Erro durante a extração de dados de um arquivo."""
    pass

class DatabaseError(ImporterError):
    """Erro durante operações no banco de dados."""
    pass

# --- Funções Auxiliares Refatoradas ---

def _get_files_to_process(docs_dir: str, cache_file: str, force_import: bool) -> List[str]:
    """
    Determina quais arquivos precisam ser processados.

    Args:
        docs_dir (str): Diretório de entrada dos arquivos Excel.
        cache_file (str): Caminho para o arquivo de cache.
        force_import (bool): Se True, força o reprocessamento de todos os arquivos.

    Returns:
        List[str]: Lista de caminhos completos para os arquivos que precisam ser processados.

    Raises:
        CacheError: Se houver um problema ao acessar ou ler o arquivo de cache.
    """
    try:
        if force_import:
            logger.info("Modo 'force_import' ativado. Todos os arquivos serão reprocessados.")
            all_files = caching.get_all_xlsx_files(docs_dir)
            return all_files

        # Verifica se o cache existe
        if not os.path.exists(cache_file):
            logger.info("Arquivo de cache não encontrado. Todos os arquivos serão processados.")
            all_files = caching.get_all_xlsx_files(docs_dir)
            return all_files

        # Compara arquivos usando o cache
        files_to_process = caching.get_files_to_process(docs_dir, cache_file)
        logger.debug(f"Arquivos identificados para processamento: {len(files_to_process)}")
        return files_to_process

    except Exception as e:
        logger.error(f"Erro ao determinar arquivos para processamento: {e}")
        raise CacheError(f"Falha na verificação de arquivos: {e}") from e

def _import_single_file(file_path: str, db_path: str, table_name: str) -> bool:
    """
    Importa um único arquivo Excel para o banco de dados.

    Args:
        file_path (str): Caminho completo para o arquivo Excel.
        db_path (str): Caminho para o banco de dados SQLite.
        table_name (str): Nome da tabela no banco de dados.

    Returns:
        bool: True se a importação foi bem-sucedida, False caso contrário.

    Raises:
        ExtractionError: Se houver falha na extração.
        DatabaseError: Se houver falha na inserção no DB.
    """
    logger.info(f"Iniciando importação de '{file_path}'...")
    try:
        df = extractor.extract_data_from_excel(file_path)
        if df is not None and not df.empty:
            success = database.insert_dataframe_to_db(df, db_path, table_name)
            if success:
                logger.info(f"Importação de '{file_path}' concluída com sucesso.")
                return True
            else:
                logger.error(f"Falha ao inserir dados de '{file_path}' no banco de dados.")
                raise DatabaseError(f"Erro ao inserir dados do arquivo {file_path}")
        else:
            logger.warning(f"Nenhum dado válido extraído de '{file_path}'. Pulando.")
            return True # Não é um erro crítico, apenas não há dados
    except extractor.ExtractionError:
        # Re-levanta erros específicos de extração
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
    Atualiza o arquivo de cache após uma importação bem-sucedida.

    Args:
        processed_files (List[str]): Lista de arquivos processados com sucesso.
        cache_file (str): Caminho para o arquivo de cache.
        docs_dir (str): Diretório de entrada dos arquivos Excel.

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
        raise CacheError("Falha ao atualizar o cache após importação.") from e

# --- Função Principal Refatorada ---

def run_importer_logic(
    docs_dir: str = 'docs_entrada',
    data_dir: str = 'data',
    db_name: str = 'ssas.db',
    table_name: str = 'ssas',
    force_import: bool = False
) -> bool:
    """
    Executa a lógica principal de importação de dados.

    Args:
        docs_dir (str): Diretório de entrada dos arquivos Excel.
        data_dir (str): Diretório para armazenamento do banco de dados e cache.
        db_name (str): Nome do arquivo do banco de dados SQLite.
        table_name (str): Nome da tabela no banco de dados.
        force_import (bool): Se True, força a reimportação de todos os arquivos.

    Returns:
        bool: True se o banco de dados foi atualizado, False caso contrário.
    """
    logger.info("=== Iniciando processo de importação ===")
    
    # --- Configuração de Caminhos ---
    docs_dir = os.path.join(project_root, docs_dir)
    data_dir = os.path.join(project_root, data_dir)
    db_path = os.path.join(data_dir, db_name)
    cache_file = os.path.join(data_dir, 'file_cache.json')

    try:
        # --- 1. Determinar arquivos a serem processados ---
        files_to_process = _get_files_to_process(docs_dir, cache_file, force_import)

        if not files_to_process:
            logger.info("Nenhum arquivo novo ou modificado encontrado para processamento.")
            return False

        logger.info(f"{len(files_to_process)} arquivo(s) identificado(s) para importação.")

        # --- 2. Processar cada arquivo ---
        successfully_processed_files = []
        for file_path in files_to_process:
            try:
                if _import_single_file(file_path, db_path, table_name):
                    successfully_processed_files.append(file_path)
            except (ExtractionError, DatabaseError) as e:
                # Loga o erro mas continua com os próximos arquivos
                logger.error(f"Falha crítica ao processar '{file_path}': {e}. Continuando...")
                # Dependendo da política, pode-se decidir parar ou continuar
                # Aqui, optamos por continuar
                continue

        # --- 3. Atualizar cache apenas se houve sucesso ---
        if successfully_processed_files:
            _update_cache_after_import(successfully_processed_files, cache_file, docs_dir)
            logger.info("=== Processo de importação concluído com atualizações ===")
            return True
        else:
            logger.info("Nenhum arquivo foi processado com sucesso.")
            return False

    except ImporterError:
        # Re-levanta exceções personalizadas
        raise
    except Exception as e:
        logger.critical(f"Erro inesperado no processo de importação: {e}", exc_info=True)
        raise ImporterError("Erro crítico no processo de importação.") from e


def filter_dataframe(df: pd.DataFrame, search_terms: list) -> pd.DataFrame:
    """
    Filtra um DataFrame com base em uma lista de termos de busca.
    Os termos sao procurados em todas as colunas de texto do DataFrame.

    Args:
        df (pd.DataFrame): O DataFrame a ser filtrado.
        search_terms (list): Uma lista de strings para buscar.

    Returns:
        pd.DataFrame: Um novo DataFrame contendo apenas as linhas que
                      correspondem aos criterios de busca.
    """
    if not search_terms or df.empty:
        return df

    # Cria uma mascara booleana inicialmente falsa
    mask = pd.Series([False] * len(df), dtype=bool)
    
    # Converte todas as colunas de objeto (strings) para string e torna minusculas
    # para busca case-insensitive
    str_df = df.select_dtypes(include=['object']).astype(str).apply(lambda x: x.str.lower())
    
    # Para cada termo de busca, verifica se ele esta presente em qualquer celula da linha
    for term in search_terms:
        term_lower = term.lower()
        # Verifica em todas as colunas de string
        term_mask = str_df.apply(lambda col: col.str.contains(term_lower, na=False)).any(axis=1)
        # Combina com a mascara geral usando OR (|)
        mask = mask | term_mask
        
    # Retorna o DataFrame filtrado
    return df[mask]