# utils/data_validation.py
"""
Módulo para validação e verificação de qualidade dos dados.
"""

import pandas as pd
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

def check_data_quality(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Verifica a qualidade dos dados em um DataFrame.
    
    Args:
        df (pd.DataFrame): DataFrame para verificar a qualidade.
        
    Returns:
        Dict[str, Any]: Dicionário com informações sobre a qualidade dos dados.
    """
    if df.empty:
        return {
            "total_rows": 0,
            "total_columns": 0,
            "missing_data": {},
            "duplicate_rows": 0,
            "data_types": {}
        }
    
    # Verificar dados faltantes
    missing_data = df.isnull().sum().to_dict()
    
    # Verificar linhas duplicadas
    duplicate_rows = df.duplicated().sum()
    
    # Verificar tipos de dados
    data_types = df.dtypes.astype(str).to_dict()
    
    # Verificar valores únicos em colunas importantes
    unique_counts = {}
    for col in df.columns:
        unique_counts[col] = df[col].nunique()
    
    quality_report = {
        "total_rows": len(df),
        "total_columns": len(df.columns),
        "missing_data": missing_data,
        "duplicate_rows": duplicate_rows,
        "data_types": data_types,
        "unique_counts": unique_counts
    }
    
    logger.info(f"Relatório de qualidade gerado: {quality_report['total_rows']} linhas, {quality_report['total_columns']} colunas")
    return quality_report

def validate_ssa_data(df: pd.DataFrame) -> List[str]:
    """
    Valida dados específicos de SSAs.
    
    Args:
        df (pd.DataFrame): DataFrame com dados de SSAs.
        
    Returns:
        List[str]: Lista de mensagens de validação.
    """
    validation_messages = []
    
    if df.empty:
        validation_messages.append("DataFrame vazio - nenhuma validação realizada")
        return validation_messages
    
    # Verificar colunas obrigatórias
    required_columns = ['numero_ssa', 'situacao', 'descricao_ssa']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        validation_messages.append(f"Colunas obrigatórias ausentes: {missing_columns}")
    
    # Verificar números de SSA válidos
    if 'numero_ssa' in df.columns:
        invalid_ssas = df[df['numero_ssa'].isnull() | (df['numero_ssa'] <= 0)]
        if len(invalid_ssas) > 0:
            validation_messages.append(f"{len(invalid_ssas)} SSA(s) com números inválidos")
    
    # Verificar descrições vazias
    if 'descricao_ssa' in df.columns:
        empty_descriptions = df[df['descricao_ssa'].isnull() | (df['descricao_ssa'].astype(str).str.strip() == '')]
        if len(empty_descriptions) > 0:
            validation_messages.append(f"{len(empty_descriptions)} SSA(s) com descrições vazias")
    
    # Verificar datas válidas
    if 'data_cadastro' in df.columns:
        invalid_dates = df[pd.to_datetime(df['data_cadastro'], errors='coerce').isnull() & df['data_cadastro'].notnull()]
        if len(invalid_dates) > 0:
            validation_messages.append(f"{len(invalid_dates)} SSA(s) com datas inválidas")
    
    if not validation_messages:
        validation_messages.append("Validação concluída com sucesso - nenhum problema encontrado")
    
    return validation_messages