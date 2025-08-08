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
from utils import data_validation
from exportacao.scheduled_exporter import ScheduledExporter

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
# Validação de dados
            validation_messages = data_validation.validate_ssa_data(df)
            for message in validation_messages:
                logger.info(f"Validação para '{file_path}': {message}")
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
    Os termos são procurados em todas as colunas de texto do DataFrame.
    Versão otimizada para uso de memória e performance.

    Args:
        df (pd.DataFrame): O DataFrame a ser filtrado.
        search_terms (list): Uma lista de strings para buscar.

    Returns:
        pd.DataFrame: Um novo DataFrame contendo apenas as linhas que
                      correspondem aos critérios de busca.
    """
    if not search_terms or df.empty:
        return df

    # Limpar termos de busca (remover espaços, termos vazios)
    clean_terms = [term.strip().lower() for term in search_terms if term.strip()]
    
    if not clean_terms:
        return df
        
    try:
        # Seleciona apenas colunas que são strings (object) ou categorias para otimizar
        str_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
        
        if not str_cols:
            logger.warning("Nenhuma coluna de texto encontrada para busca")
            return df
        
        # Inicializa o índice com todos os registros
        # Usamos uma abordagem de filtro progressivo, que é mais eficiente em memória
        matching_indices = set(range(len(df)))
        
        # Para cada termo, filtramos o conjunto de índices
        for term in clean_terms:
            if not term:  # Pula termos vazios
                continue
                
            term_lower = term  # já está em minúsculas
            
            # Para cada termo, encontramos os índices que correspondem em qualquer coluna
            term_matching_indices = set()
            
            for col in str_cols:
                try:
                    # Iteração otimizada para uso de memória - processa cada coluna separadamente
                    # e não cria máscaras intermediárias para todo o DataFrame
                    col_series = df[col].astype(str).str.lower()
                    for idx in matching_indices:  # Só procurar nos índices ainda válidos
                        try:
                            if term_lower in col_series.iloc[idx]:
                                term_matching_indices.add(idx)
                        except:
                            continue
                except Exception as col_err:
                    logger.warning(f"Erro ao processar coluna {col}: {col_err}")
                    continue
                    
                # Otimização: se já encontramos todas as linhas atuais para este termo,
                # não precisamos verificar mais colunas
                if term_matching_indices == matching_indices:
                    break
                    
            # Atualiza o conjunto de índices correspondentes para a interseção
            # de índices que correspondem a todos os termos até agora
            matching_indices = term_matching_indices
            
            # Se não há mais registros correspondentes, podemos parar
            if not matching_indices:
                break
        
        # Cria o DataFrame filtrado usando os índices encontrados
        result_df = df.iloc[sorted(matching_indices)] if matching_indices else df.iloc[0:0]
        logger.debug(f"Filtro aplicado com {len(result_df)} resultados encontrados.")
        return result_df
    except Exception as e:
        logger.error(f"Erro ao aplicar filtro: {e}", exc_info=True)
        # Em caso de erro, tenta a abordagem anterior, mais simples
        try:
            # Cria uma máscara booleana inicialmente falsa
            mask = pd.Series([False] * len(df), dtype=bool)
            
            # Para cada termo de busca, verifica se ele está presente em qualquer coluna de texto
            for term in clean_terms:
                term_mask = pd.Series([False] * len(df))
                for col in str_cols:
                    col_mask = df[col].astype(str).str.lower().str.contains(term, na=False, regex=False)
                    term_mask = term_mask | col_mask
                mask = mask | term_mask
                
            return df[mask]
        except:
            # Se ambos os métodos falharem, retorna o DataFrame original
            logger.error("Método alternativo de filtro também falhou, retornando dados originais")
            return df
def advanced_filter_dataframe(df: pd.DataFrame, filters: dict) -> pd.DataFrame:
    """
    Filtra um DataFrame com base em critérios avançados.
    
    Args:
        df (pd.DataFrame): O DataFrame a ser filtrado.
        filters (dict): Dicionário com critérios de filtro.
        
    Returns:
        pd.DataFrame: DataFrame filtrado.
    """
    if df.empty or not filters:
        return df
    
    try:
        filtered_df = df.copy()
        
        # Filtro por texto (termos de busca)
        if 'search_terms' in filters and filters['search_terms']:
            filtered_df = filter_dataframe(filtered_df, filters['search_terms'])
        
        # Filtro por setor executor
        if 'setor_executor' in filters and filters['setor_executor']:
            executor_filter = filters['setor_executor']
            if 'setor_executor' in filtered_df.columns:
                filtered_df = filtered_df[
                    filtered_df['setor_executor'].astype(str).str.contains(executor_filter, case=False, na=False)
                ]
        
        # Filtro por situação
        if 'situacao' in filters and filters['situacao']:
            situacao_filter = filters['situacao']
            if 'situacao' in filtered_df.columns:
                filtered_df = filtered_df[
                    filtered_df['situacao'].astype(str).str.contains(situacao_filter, case=False, na=False)
                ]
        
        # Filtro por data (data de cadastro)
        if 'data_inicio' in filters and filters['data_inicio']:
            if 'data_cadastro' in filtered_df.columns:
                # Converter para datetime
                filtered_df['data_cadastro'] = pd.to_datetime(filtered_df['data_cadastro'], errors='coerce')
                data_inicio = pd.to_datetime(filters['data_inicio'])
                filtered_df = filtered_df[filtered_df['data_cadastro'] >= data_inicio]
        
        if 'data_fim' in filters and filters['data_fim']:
            if 'data_cadastro' in filtered_df.columns:
                # Converter para datetime
                filtered_df['data_cadastro'] = pd.to_datetime(filtered_df['data_cadastro'], errors='coerce')
                data_fim = pd.to_datetime(filters['data_fim'])
                filtered_df = filtered_df[filtered_df['data_cadastro'] <= data_fim]
        
        logger.debug(f"Filtro avançado aplicado com {len(filtered_df)} resultados encontrados.")
        return filtered_df
    except Exception as e:
        logger.error(f"Erro ao aplicar filtro avançado: {e}")
        # Em caso de erro, retorna o DataFrame original
        return df
def run_scheduled_exports(df: pd.DataFrame, display_map: dict):
    """
    Executa as exportações agendadas.
    
    Args:
        df (pd.DataFrame): DataFrame com os dados a serem exportados.
        display_map (dict): Mapeamento de colunas para exibição.
    """
    try:
        scheduled_exporter = ScheduledExporter()
        scheduled_exporter.run_scheduled_exports(df, display_map)
        logger.info("Exportações agendadas verificadas e executadas conforme necessário.")
    except Exception as e:
        logger.error(f"Erro ao executar exportações agendadas: {e}")