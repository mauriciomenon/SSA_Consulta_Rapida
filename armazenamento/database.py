# armazenamento/database.py 20250725 161500 (v2.1 - Boas Praticas Confirmadas)
"""
Módulo para interação com o banco de dados SQLite.

Responsável por criar tabelas, inserir DataFrames e consultar dados.
"""

import sqlite3
import pandas as pd
import os
import logging
from contextlib import contextmanager
import re
from datetime import datetime
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# --- Gerenciamento de Conexão ---

# Nome do arquivo de schema (exposto para testes)
schema_file = 'schema.sql'

@contextmanager
def get_db_connection(db_path: str):
    """
    Gerenciador de contexto para obter uma conexão com o banco de dados.

    Args:
        db_path (str): Caminho para o arquivo do banco de dados SQLite.

    Yields:
        sqlite3.Connection: Uma conexão ativa com o banco de dados.
    """
    conn = None
    try:
        # Verifica se o diretório do DB existe
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
            
        conn = sqlite3.connect(db_path)
        # Configurações recomendadas para performance e segurança
        conn.execute("PRAGMA foreign_keys = ON") # Se estiver usando FKs
        yield conn
    except sqlite3.Error as e:
        logger.error(f"Erro de banco de dados: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

# --- Funções de Banco de Dados ---

# armazenamento/database.py

def initialize_database(db_path: str, schema_file: str = 'schema.sql'):
    """
    Inicializa o banco de dados aplicando o schema SQL informado.

    Args:
        db_path: Caminho para o arquivo SQLite a ser criado/alterado.
        schema_file: Caminho para o arquivo .sql do schema. Pode ser absoluto ou relativo.
            - Se relativo e existir no diretório atual, será usado.
            - Caso não exista no CWD, será buscado em <raiz_projeto>/config/<schema_file>.

    Returns:
        True em caso de sucesso.

    Raises:
        FileNotFoundError: Se o arquivo de schema não for encontrado.
        Exception: Erros ao aplicar o schema serão propagados.
    """
    # Resolve o caminho do schema respeitando o parâmetro
    # 1) Se for absoluto, deve existir; caso contrário, erro imediato
    if os.path.isabs(schema_file):
        if not os.path.exists(schema_file):
            raise FileNotFoundError(f"Arquivo de schema absoluto não encontrado: '{schema_file}'")
        schema_path = schema_file
    else:
        # 2) Relativo: primeiro tenta no CWD
        if os.path.exists(schema_file):
            schema_path = schema_file
        else:
            # 3) Fallback para <project_root>/config/<basename>
            current_file_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_file_dir)
            candidate = os.path.join(project_root, 'config', os.path.basename(schema_file))
            if os.path.exists(candidate):
                schema_path = candidate
            else:
                # Log auxiliar com conteúdo de config, se houver
                config_dir = os.path.join(project_root, 'config')
                if os.path.isdir(config_dir):
                    try:
                        logger.info(f"Conteúdo da pasta config: {os.listdir(config_dir)}")
                    except Exception:
                        pass
                raise FileNotFoundError(
                    f"Arquivo de schema não encontrado. Tentativas: '\n"
                    f"- relativo ao CWD: {os.path.abspath(schema_file)}\n"
                    f"- em config do projeto: {candidate}"
                )

    logger.info(f"Aplicando schema a partir de: '{schema_path}'")
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema_sql = f.read()

    with get_db_connection(db_path) as conn:
        conn.executescript(schema_sql)
        conn.commit()

    logger.info("Banco de dados inicializado com sucesso.")
    return True

def query_db(db_path: str, table_name: str, query: str = "", params: tuple = ()) -> pd.DataFrame:
    """
    Consulta o banco de dados e retorna um DataFrame.

    Args:
        db_path (str): Caminho para o banco de dados.
        table_name (str): Nome da tabela (usado se `query` estiver vazio).
        query (str, optional): Query SQL customizada. Se vazia, seleciona tudo da tabela.
        params (tuple, optional): Parâmetros para a query.

    Returns:
        pd.DataFrame: Resultado da consulta.
    """
    if not query:
        query = f"SELECT * FROM {table_name}"

    logger.debug(f"Executando consulta: {query} com params: {params}")
    try:
        with get_db_connection(db_path) as conn:
            # pd.read_sql_query é ótimo para SELECTs
            df = pd.read_sql_query(query, conn, params=params)
        logger.debug(f"Consulta retornou {len(df)} linhas.")
        return df
    except Exception as e:
        logger.error(f"Erro ao executar consulta '{query}': {e}")
        # Retorna DataFrame vazio em caso de erro
        return pd.DataFrame()

def insert_dataframe_to_db(df: pd.DataFrame, db_path: str, table_name: str, if_exists: str = 'append') -> bool:
    """
    Insere um DataFrame em uma tabela do banco de dados.

    Args:
        df (pd.DataFrame): O DataFrame a ser inserido.
        db_path (str): Caminho para o banco de dados.
        table_name (str): Nome da tabela de destino.
        if_exists (str): O que fazer se a tabela já existir ('fail', 'replace', 'append').

    Returns:
        bool: True se a inserção foi bem-sucedida, False caso contrário.
    """
    if df.empty:
        logger.warning("DataFrame vazio fornecido para inserção. Nada a fazer.")
        return True

    logger.debug(f"Inserindo {len(df)} linhas no banco de dados '{db_path}', tabela '{table_name}'...")
    try:
        # Normaliza coluna numero_ssa se existir
        if 'numero_ssa' in df.columns:
            df = df.copy()
            df['numero_ssa'] = df['numero_ssa'].apply(_normalize_numero_ssa_value)
        with get_db_connection(db_path) as conn:
            # Para arquivos grandes, usar chunksize para evitar "too many SQL variables"
            batch_size = min(500, max(1, 999 // len(df.columns))) if len(df.columns) > 0 else 500
            
            # Garantir que o DataFrame tem índices únicos antes da inserção
            # Solução mais agressiva para resolver problema de índices duplicados
            df = df.copy().reset_index(drop=True)
            
            # Verificar se ainda há problema com índices
            if df.index.has_duplicates:
                logger.warning("Detectados índices duplicados, forçando reindexação")
                df = df.reset_index(drop=True)
            
            # to_sql é o método recomendado do Pandas
            # index=False evita inserir a coluna de índice do DataFrame
            # chunksize divide em lotes menores para evitar limite de variáveis SQL
            # Removendo method='multi' que pode estar causando problemas com índices
            df.to_sql(table_name, conn, if_exists=if_exists, index=False, chunksize=batch_size)
            conn.commit()
        logger.info(f"{len(df)} linhas inseridas com sucesso na tabela '{table_name}'.")
        return True
    except Exception as e:
        logger.error(f"Falha ao inserir dados na tabela '{table_name}': {e}")
        return False


def reset_database(db_path: str, mode: str = 'table', table_name: str = 'ssas', schema_path: str | None = None) -> bool:
    """Reseta o banco de dados.

    - mode = 'file': remove o arquivo de banco por completo (se existir).
    - mode = 'table': recria somente a tabela alvo usando o schema.
    """
    try:
        if mode == 'file':
            if os.path.exists(db_path):
                os.remove(db_path)
            return True
        elif mode == 'table':
            # Reaplica o schema
            if schema_path is None:
                schema_path = schema_file  # usa padrão e resolução em initialize_database
            initialize_database(db_path, schema_path)
            return True
        else:
            logger.error(f"Modo de reset desconhecido: {mode}")
            return False
    except Exception as e:
        logger.error(f"Falha ao resetar database ({mode}): {e}")
        return False


def ensure_indexes(db_path: str, table_name: str = 'ssas') -> bool:
    """Garante índices úteis para consultas comuns."""
    try:
        with get_db_connection(db_path) as conn:
            cur = conn.cursor()
            # Descobre colunas existentes para evitar erros ao criar índices
            cur.execute(f"PRAGMA table_info({table_name})")
            cols_info = cur.fetchall() or []
            existing_cols = {row[1] for row in cols_info}  # nome da coluna na posição 1

            # Índices candidatos e suas colunas
            candidate_indexes = [
                (f"idx_{table_name}_numero_ssa", "numero_ssa"),
                (f"idx_{table_name}_setor_executor", "setor_executor"),
                (f"idx_{table_name}_semana_cadastro", "semana_cadastro"),
                (f"idx_{table_name}_situacao", "situacao"),
            ]

            for idx_name, col in candidate_indexes:
                if col in existing_cols:
                    cur.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table_name} ({col})")
            conn.commit()
        return True
    except Exception as e:
        logger.error(f"Erro criando índices: {e}")
        return False


def insert_dataframe_with_smart_upsert(df: pd.DataFrame, db_path: str, table_name: str = 'ssas') -> bool:
    """Insere DataFrame com upsert inteligente por numero_ssa."""
    if df is None or df.empty:
        return True

    try:
        # CORREÇÃO RADICAL: Recriar DataFrame completamente para evitar problemas de índice
        work = pd.DataFrame(df.values, columns=df.columns)
        work = work.reset_index(drop=True)
        
        # Normalizar numero_ssa
        if 'numero_ssa' in work.columns:
            work['numero_ssa'] = work['numero_ssa'].apply(_normalize_numero_ssa_value)

        # Converter TODAS as colunas de data para string antes da inserção
        date_columns = ['data_cadastro', 'prazo_limite', 'data_limite', 'desde', 'desde_1']
        def convert_date_to_string(s) -> Optional[str]:
            try:
                if pd.isna(s) or s is None or s == '':
                    return None
                dt = pd.to_datetime(s, errors='coerce', dayfirst=True)
                if pd.isna(dt):
                    return None
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            except Exception:
                return None
        
        # Aplicar conversão para todas as colunas de data de forma segura
        for col in date_columns:
            if col in work.columns:
                try:
                    # Correção: aplicar na série completa sem usar .loc que pode ter problemas com índices duplicados
                    work[col] = [convert_date_to_string(x) for x in work[col]]
                except Exception as e:
                    logger.warning(f"Erro ao converter coluna {col}: {e}")
                    continue

        # Separar linhas com e sem numero_ssa com índices completamente limpos
        if 'numero_ssa' in work.columns:
            has_ssa_mask = work['numero_ssa'].notna()
            
            # Criar DataFrames separados garantindo índices únicos
            if has_ssa_mask.any():
                has_ssa_rows = []
                for idx in work[has_ssa_mask].index:
                    has_ssa_rows.append(work.loc[idx].values)
                has_ssa = pd.DataFrame(has_ssa_rows, columns=work.columns) if has_ssa_rows else pd.DataFrame()
            else:
                has_ssa = pd.DataFrame()
                
            if (~has_ssa_mask).any():
                no_ssa_rows = []
                for idx in work[~has_ssa_mask].index:
                    no_ssa_rows.append(work.loc[idx].values)
                no_ssa = pd.DataFrame(no_ssa_rows, columns=work.columns) if no_ssa_rows else pd.DataFrame()
            else:
                no_ssa = pd.DataFrame()
        else:
            has_ssa = pd.DataFrame()
            work_rows = []
            for idx in work.index:
                work_rows.append(work.loc[idx].values)
            no_ssa = pd.DataFrame(work_rows, columns=work.columns) if work_rows else pd.DataFrame()

        with get_db_connection(db_path) as conn:
            # Verificar se tabela existe, se não, garantir que seja criada na primeira inserção
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", [table_name])
            table_exists = cursor.fetchone() is not None
            
            # Inserir registros sem SSA (append direto)
            if not no_ssa.empty:
                if_exists_mode = 'append' if table_exists else 'replace'
                no_ssa.to_sql(table_name, conn, if_exists=if_exists_mode, index=False, chunksize=500)
                logger.info(f"Inseridos {len(no_ssa)} registros sem numero_ssa")
                table_exists = True  # Agora existe

            # Para registros com SSA, fazer upsert manual em lotes
            if not has_ssa.empty:
                # Se tabela não existe ainda, criar com primeira inserção
                if not table_exists:
                    # Usar primeira linha para criar a tabela
                    first_row = has_ssa.iloc[0:1].copy()
                    first_row.to_sql(table_name, conn, if_exists='replace', index=False)
                    table_exists = True
                    logger.info("Tabela criada com primeiro registro")
                
                # Processar em chunks para evitar "too many SQL variables"
                chunk_size = 100
                total_inserted = 0
                
                for i in range(0, len(has_ssa), chunk_size):
                    chunk = has_ssa.iloc[i:i+chunk_size].copy()
                    
                    # Para cada registro no chunk, verificar se existe e decidir se insere/atualiza
                    for _, row in chunk.iterrows():
                        numero_ssa = row['numero_ssa']
                        
                        # Verificar se já existe
                        existing = pd.read_sql_query(
                            f"SELECT * FROM {table_name} WHERE numero_ssa = ?",
                            conn, params=[numero_ssa]
                        )
                        
                        if existing.empty:
                            # Não existe, inserir
                            row_df = pd.DataFrame([row.values], columns=row.index)
                            row_df.to_sql(table_name, conn, if_exists='append', index=False)
                            total_inserted += 1
                        else:
                            # Existe, comparar datas e decidir
                            existing_date = existing.iloc[0].get('data_cadastro')
                            new_date = row.get('data_cadastro')
                            
                            # Converter datas para string para comparação segura
                            try:
                                if pd.isna(existing_date) or existing_date is None:
                                    existing_date_str = None
                                else:
                                    existing_date_str = str(existing_date)
                                    
                                if pd.isna(new_date) or new_date is None:
                                    new_date_str = None
                                else:
                                    new_date_str = str(new_date)
                            except:
                                existing_date_str = None
                                new_date_str = None
                            
                            # Se nova data é mais recente ou se não há data, atualizar
                            should_update = False
                            if new_date_str and not existing_date_str:
                                should_update = True
                            elif new_date_str and existing_date_str and new_date_str >= existing_date_str:
                                should_update = True
                            elif not new_date_str and not existing_date_str:
                                should_update = True  # Empate, prefere novo
                            
                            if should_update:
                                # Deletar antigo e inserir novo
                                conn.execute(f"DELETE FROM {table_name} WHERE numero_ssa = ?", [numero_ssa])
                                row_df = pd.DataFrame([row.values], columns=row.index)
                                row_df.to_sql(table_name, conn, if_exists='append', index=False)
                                total_inserted += 1
                
                logger.info(f"Processados {total_inserted} registros com numero_ssa via upsert")
            
            conn.commit()
        
        logger.info(f"Inserção completada com sucesso")
        return True
        
    except Exception as e:
        logger.error(f"Falha na inserção: {e}")
        return False


def _normalize_numero_ssa_value(v) -> int | None:
    """Normaliza um valor de numero_ssa para inteiro.

    Regras para SSAs de 9 dígitos (YYYYNNNNN):
    - Remove tudo que não seja dígito
    - Se vazio após limpeza: None
    - Valida se tem formato correto de ano (2019-2050) + 5 dígitos
    - Rejeita se não está no formato correto
    - Converte para int
    """
    try:
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return None
        s = re.sub(r"\D", "", str(v))
        if not s:
            return None
        
        # NÃO remover zeros à esquerda - SSAs podem começar com zeros válidos!
        
        # Validar formato: deve ter exatamente 9 dígitos
        if len(s) != 9:
            logger.warning(f"SSA inválido - deve ter 9 dígitos: '{s}' (original: '{v}')")
            return None
            
        # Validar ano (primeiros 4 dígitos): deve estar entre 2019-2050
        ano_str = s[:4]
        try:
            ano = int(ano_str)
            if not (2019 <= ano <= 2050):
                logger.warning(f"SSA inválido - ano fora do range 2019-2050: '{s}' (ano: {ano})")
                return None
        except ValueError:
            logger.warning(f"SSA inválido - ano não numérico: '{s}'")
            return None
            
        # Converter para int
        return int(s)
        
    except Exception as e:
        logger.warning(f"Erro ao normalizar numero_ssa '{v}': {e}")
        return None


def normalize_numero_ssa_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Retorna uma cópia do DataFrame com coluna numero_ssa normalizada (se existir)."""
    if 'numero_ssa' not in df.columns:
        return df
    out = df.copy()
    values = out['numero_ssa'].tolist()
    normalized = [ _normalize_numero_ssa_value(v) for v in values ]
    out['numero_ssa'] = pd.Series(normalized, dtype='object')
    return out


def normalize_numero_ssa(value) -> str | None:
    """Normaliza numero_ssa para formato de exibição consistente.

    Regras para SSAs de 9 dígitos (YYYYNNNNN):
    - None/"" -> None
    - Remove caracteres não numéricos
    - Se tem 7 dígitos começando com 21-25: prefixa "20" (anos 2021-2025)
    - Se < 9 dígitos (outros casos): completa com zeros à esquerda até 9 dígitos
    - Se >= 9 dígitos: usa os primeiros 9 dígitos
    - Retorna como string
    """
    if value is None:
        return None
    s = re.sub(r"\D", "", str(value))
    if not s:
        return None
    
    # Remover zeros à esquerda apenas se necessário
    s = s.lstrip('0')
    if not s:  # Se ficou vazio, era só zeros
        return None
        
    # CORREÇÃO ESPECÍFICA: Se tem 7 dígitos começando com 21-25, prefixa "20"
    if len(s) == 7 and s.startswith(('21', '22', '23', '24', '25')):
        s = "20" + s
    # Se tem menos de 9 dígitos (outros casos), completar com zeros à esquerda
    elif len(s) < 9:
        s = s.zfill(9)
    # Se tem mais de 9 dígitos, usar apenas os primeiros 9
    elif len(s) > 9:
        s = s[:9]
    
    return s


# --- Funções de Verificação e Integridade do Banco ---

def verify_database_integrity(db_path: str, table_name: str = 'ssa_table') -> Dict[str, Any]:
    """
    Verifica a integridade do banco de dados e retorna relatório detalhado.
    
    Args:
        db_path: Caminho para o arquivo do banco de dados
        table_name: Nome da tabela principal a verificar
        
    Returns:
        Dict com status da verificação e detalhes dos problemas encontrados
    """
    verification_report = {
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
        'needs_creation': False
    }
    
    try:
        # 1. Verificar se o arquivo do banco existe
        if not os.path.exists(db_path):
            verification_report['issues'].append(f"Arquivo do banco de dados não encontrado: {db_path}")
            verification_report['is_valid'] = True  # CORREÇÃO: banco inexistente é válido para criação
            verification_report['needs_creation'] = True
            return verification_report
        
        verification_report['database_exists'] = True
        
        # 2. Verificar permissões de arquivo
        try:
            if not os.access(db_path, os.R_OK | os.W_OK):
                verification_report['issues'].append(f"Permissões insuficientes para o banco: {db_path}")
                verification_report['is_valid'] = False
            else:
                verification_report['file_permissions_ok'] = True
        except Exception as e:
            verification_report['issues'].append(f"Erro ao verificar permissões: {e}")
            verification_report['is_valid'] = False
        
        # 3. Verificar espaço em disco
        try:
            db_dir = os.path.dirname(db_path) or '.'
            statvfs = os.statvfs(db_dir) if hasattr(os, 'statvfs') else None
            if statvfs:
                free_space_gb = (statvfs.f_frsize * statvfs.f_bavail) / (1024**3)
                if free_space_gb < 0.1:  # Menos de 100MB disponível
                    verification_report['warnings'].append(f"Pouco espaço em disco: {free_space_gb:.2f}GB disponível")
                else:
                    verification_report['disk_space_sufficient'] = True
            else:
                # Windows - usar shutil
                import shutil
                free_space_gb = shutil.disk_usage(db_dir).free / (1024**3)
                if free_space_gb < 0.1:
                    verification_report['warnings'].append(f"Pouco espaço em disco: {free_space_gb:.2f}GB disponível")
                else:
                    verification_report['disk_space_sufficient'] = True
        except Exception as e:
            verification_report['warnings'].append(f"Não foi possível verificar espaço em disco: {e}")
        
        # 4. Verificar acessibilidade do banco
        try:
            with get_db_connection(db_path) as conn:
                # Testar uma operação simples
                conn.execute("SELECT 1").fetchone()
                verification_report['database_accessible'] = True
        except Exception as e:
            verification_report['issues'].append(f"Banco de dados não acessível: {e}")
            verification_report['is_valid'] = False
            return verification_report
        
        # 5. Verificar se a tabela principal existe
        try:
            with get_db_connection(db_path) as conn:
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=?", 
                    (table_name,)
                )
                if cursor.fetchone():
                    verification_report['table_exists'] = True
                else:
                    verification_report['issues'].append(f"Tabela '{table_name}' não encontrada")
                    verification_report['is_valid'] = False
        except Exception as e:
            verification_report['issues'].append(f"Erro ao verificar tabela: {e}")
            verification_report['is_valid'] = False
        
        # 6. Verificar schema da tabela (colunas obrigatórias)
        if verification_report['table_exists']:
            try:
                required_columns = ['numero_ssa', 'situacao', 'data_cadastro', 'descricao_ssa']
                with get_db_connection(db_path) as conn:
                    cursor = conn.execute(f"PRAGMA table_info({table_name})")
                    existing_columns = [row[1] for row in cursor.fetchall()]
                    
                    missing_columns = [col for col in required_columns if col not in existing_columns]
                    if missing_columns:
                        verification_report['issues'].append(f"Colunas obrigatórias ausentes: {missing_columns}")
                        verification_report['is_valid'] = False
                    else:
                        verification_report['schema_valid'] = True
            except Exception as e:
                verification_report['issues'].append(f"Erro ao verificar schema: {e}")
                verification_report['is_valid'] = False
        
        # 7. Verificar integridade SQLite
        try:
            with get_db_connection(db_path) as conn:
                cursor = conn.execute("PRAGMA integrity_check")
                integrity_result = cursor.fetchone()
                if integrity_result and integrity_result[0] != 'ok':
                    verification_report['issues'].append(f"Falha na verificação de integridade SQLite: {integrity_result[0]}")
                    verification_report['is_valid'] = False
                else:
                    verification_report['data_consistent'] = True
        except Exception as e:
            verification_report['issues'].append(f"Erro ao verificar integridade SQLite: {e}")
            verification_report['is_valid'] = False
        
        logger.info(f"Verificação de integridade concluída. Status: {'✓ Válido' if verification_report['is_valid'] else '✗ Problemas encontrados'}")
        
    except Exception as e:
        verification_report['issues'].append(f"Erro inesperado na verificação: {e}")
        verification_report['is_valid'] = False
        logger.error(f"Erro na verificação de integridade: {e}")
    
    return verification_report


def validate_dataframe_before_insert(df: pd.DataFrame, table_name: str = 'ssas') -> Dict[str, Any]:
    """
    Valida um DataFrame antes da inserção no banco de dados.
    
    Args:
        df: DataFrame a ser validado
        table_name: Nome da tabela de destino
        
    Returns:
        Dict com resultado da validação e problemas encontrados
    """
    validation_report = {
        'is_valid': True,
        'issues': [],
        'warnings': [],
        'row_count': len(df),
        'invalid_rows': [],
        'fixed_rows': 0
    }
    
    try:
        if df.empty:
            validation_report['warnings'].append("DataFrame vazio - nada para validar")
            return validation_report
        
        # 1. Verificar colunas críticas
        critical_columns = ['numero_ssa', 'situacao']
        for col in critical_columns:
            if col in df.columns:
                null_count = df[col].isnull().sum()
                if null_count > 0:
                    validation_report['warnings'].append(f"Coluna '{col}' tem {null_count} valores nulos")
        
        # 2. Validar números SSA
        if 'numero_ssa' in df.columns:
            invalid_ssa_mask = df['numero_ssa'].apply(lambda x: _normalize_numero_ssa_value(x) is None if pd.notna(x) else True)
            invalid_ssa_count = invalid_ssa_mask.sum()
            
            if invalid_ssa_count > 0:
                validation_report['warnings'].append(f"{invalid_ssa_count} números SSA inválidos encontrados")
                # Marcar linhas com SSA inválido
                invalid_indices = df[invalid_ssa_mask].index.tolist()
                validation_report['invalid_rows'].extend(invalid_indices)
        
        # 3. Validar datas
        date_columns = ['data_cadastro', 'prazo_limite', 'data_limite']
        for col in date_columns:
            if col in df.columns:
                invalid_dates = 0
                for idx, value in df[col].items():
                    if pd.notna(value) and value != '':
                        try:
                            pd.to_datetime(value, errors='raise', dayfirst=True)
                        except:
                            invalid_dates += 1
                            if idx not in validation_report['invalid_rows']:
                                validation_report['invalid_rows'].append(idx)
                
                if invalid_dates > 0:
                    validation_report['warnings'].append(f"Coluna '{col}' tem {invalid_dates} datas inválidas")
        
        # 4. Verificar duplicatas por numero_ssa
        if 'numero_ssa' in df.columns:
            valid_ssa_df = df[df['numero_ssa'].notna()]
            if not valid_ssa_df.empty:
                duplicated_ssa = valid_ssa_df.duplicated(subset=['numero_ssa'], keep=False)
                duplicate_count = duplicated_ssa.sum()
                
                if duplicate_count > 0:
                    validation_report['warnings'].append(f"{duplicate_count} números SSA duplicados encontrados")
        
        # 5. Verificar tamanhos de string (evitar truncamento)
        text_columns = ['descricao_ssa', 'descricao_execucao', 'solicitante']
        for col in text_columns:
            if col in df.columns:
                long_values = df[col].astype(str).str.len() > 1000  # Limite arbitrário
                long_count = long_values.sum()
                
                if long_count > 0:
                    validation_report['warnings'].append(f"Coluna '{col}' tem {long_count} valores muito longos (>1000 chars)")
        
        # Considerar válido mesmo com warnings (apenas issues críticos invalidam)
        if not validation_report['issues']:
            validation_report['is_valid'] = True
            
        logger.info(f"Validação concluída: {validation_report['row_count']} linhas, "
                   f"{len(validation_report['issues'])} problemas críticos, "
                   f"{len(validation_report['warnings'])} avisos")
        
    except Exception as e:
        validation_report['issues'].append(f"Erro na validação: {e}")
        validation_report['is_valid'] = False
        logger.error(f"Erro na validação do DataFrame: {e}")
    
    return validation_report


def repair_database_if_needed(db_path: str, schema_file: str = 'schema.sql', table_name: str = 'ssa_table') -> bool:
    """
    Tenta reparar o banco de dados se problemas forem detectados.
    
    Args:
        db_path: Caminho para o banco de dados
        schema_file: Arquivo de schema para recriação se necessário
        table_name: Nome da tabela para verificação
        
    Returns:
        True se reparo foi bem-sucedido ou não necessário
    """
    logger.info("Iniciando verificação e reparo do banco de dados...")
    
    try:
        # Verificar integridade
        integrity_report = verify_database_integrity(db_path, table_name)
        
        if integrity_report['is_valid']:
            logger.info("Banco de dados íntegro - nenhum reparo necessário")
            return True
        
        logger.warning(f"Problemas detectados no banco: {integrity_report['issues']}")
        
        # Tentar reparos básicos
        repaired = False
        
        # 1. Se banco não existe, criar novo
        if not integrity_report['database_exists']:
            logger.info("Criando novo banco de dados...")
            initialize_database(db_path, schema_file)
            repaired = True
        
        # 2. Se tabela não existe, recriar schema
        elif not integrity_report['table_exists']:
            logger.info("Recriando schema do banco...")
            initialize_database(db_path, schema_file)
            repaired = True
        
        # 3. Se há problemas de integridade SQLite, tentar backup/restore
        elif not integrity_report['data_consistent']:
            logger.warning("Detectada corrupção no banco - tentando backup/restore...")
            backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            try:
                # Fazer backup do que for possível
                import shutil
                shutil.copy2(db_path, backup_path)
                logger.info(f"Backup criado em: {backup_path}")
                
                # Tentar extrair dados válidos
                with get_db_connection(db_path) as conn:
                    try:
                        df_backup = pd.read_sql_query("SELECT * FROM ssas", conn)
                        if not df_backup.empty:
                            # Recriar banco limpo
                            os.remove(db_path)
                            initialize_database(db_path, schema_file)
                            
                            # Reinserir dados
                            success = insert_dataframe_with_smart_upsert(df_backup, db_path)
                            if success:
                                logger.info("Dados restaurados com sucesso após correção de corrupção")
                                repaired = True
                    except Exception as e:
                        logger.error(f"Não foi possível extrair dados do banco corrompido: {e}")
            except Exception as e:
                logger.error(f"Falha no processo de backup/restore: {e}")
        
        # Verificar se reparo foi bem-sucedido
        if repaired:
            final_check = verify_database_integrity(db_path)
            if final_check['is_valid']:
                logger.info("✓ Reparo do banco de dados concluído com sucesso")
                return True
            else:
                logger.error("✗ Reparo falhou - problemas persistem")
                return False
        else:
            logger.error("Nenhum reparo foi possível para os problemas detectados")
            return False
            
    except Exception as e:
        logger.error(f"Erro durante tentativa de reparo: {e}")
        return False
