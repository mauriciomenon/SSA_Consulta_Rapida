# utils/file_metadata.py
"""
Utilitários para extrair metadados de arquivos Excel, incluindo data/hora dos nomes dos arquivos.
"""

import re
import os
import logging
from datetime import datetime
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

def extract_datetime_from_filename(filename: str) -> Optional[datetime]:
    """
    Extrai data e hora do nome do arquivo Excel.
    
    Formatos suportados:
    - Todas as SSAs - 15-07-2025_0143PM (2).xlsx
    - IEE3_Emissor__202401_20250715_Todas as SSAs - 15-07-2025_1033AM.xlsx
    - SSAs Executadas_15-07-2025_0239PM.xlsx
    
    Args:
        filename (str): Nome do arquivo
        
    Returns:
        Optional[datetime]: Objeto datetime se conseguir extrair, None caso contrário
    """
    # Remove a extensão
    base_name = os.path.splitext(filename)[0]
    
    # Padrão regex para capturar dd-mm-YYYY_HHminminAM/PM
    # Exemplos: 15-07-2025_0143PM, 15-07-2025_1033AM
    pattern = r'(\d{2})-(\d{2})-(\d{4})_(\d{2})(\d{2})(AM|PM)'
    
    match = re.search(pattern, base_name)
    if match:
        day, month, year, hour, minute, ampm = match.groups()
        
        try:
            # Converte para inteiros
            day = int(day)
            month = int(month)
            year = int(year)
            hour = int(hour)
            minute = int(minute)
            
            # Converte formato 12h para 24h
            if ampm.upper() == 'PM' and hour != 12:
                hour += 12
            elif ampm.upper() == 'AM' and hour == 12:
                hour = 0
                
            # Cria o objeto datetime
            dt = datetime(year, month, day, hour, minute)
            logger.debug(f"Data extraída de '{filename}': {dt.isoformat()}")
            return dt
            
        except ValueError as e:
            logger.warning(f"Erro ao converter data do arquivo '{filename}': {e}")
            return None
    else:
        logger.warning(f"Formato de data não reconhecido no arquivo '{filename}'")
        return None

def get_file_metadata(file_path: str) -> Tuple[str, Optional[str], str]:
    """
    Extrai metadados completos do arquivo para controle de versões.
    
    Args:
        file_path (str): Caminho completo do arquivo
        
    Returns:
        Tuple[str, Optional[str], str]: (nome_arquivo, data_arquivo_iso, data_importacao_iso)
    """
    filename = os.path.basename(file_path)
    
    # Extrai data/hora do nome do arquivo
    file_datetime = extract_datetime_from_filename(filename)
    file_datetime_iso = file_datetime.isoformat() if file_datetime else None
    
    # Data/hora atual da importação
    import_datetime_iso = datetime.now().isoformat()
    
    logger.debug(f"Metadados do arquivo '{filename}': data_arquivo={file_datetime_iso}, data_importacao={import_datetime_iso}")
    
    return filename, file_datetime_iso, import_datetime_iso

def should_update_ssa(
    existing_file_date: Optional[str], 
    new_file_date: Optional[str]
) -> bool:
    """
    Determina se uma SSA deve ser atualizada baseado nas datas dos arquivos.
    
    Args:
        existing_file_date (Optional[str]): Data ISO do arquivo existente no DB
        new_file_date (Optional[str]): Data ISO do novo arquivo
        
    Returns:
        bool: True se deve atualizar, False caso contrário
    """
    # Se não temos data do arquivo existente, sempre atualiza
    if not existing_file_date:
        logger.debug("Arquivo existente sem data - atualizando")
        return True
    
    # Se não temos data do novo arquivo, não atualiza
    if not new_file_date:
        logger.debug("Novo arquivo sem data - não atualizando")
        return False
    
    try:
        existing_dt = datetime.fromisoformat(existing_file_date)
        new_dt = datetime.fromisoformat(new_file_date)
        
        should_update = new_dt > existing_dt
        logger.debug(f"Comparação de datas: existente={existing_dt}, novo={new_dt}, atualizar={should_update}")
        return should_update
        
    except ValueError as e:
        logger.warning(f"Erro ao comparar datas: {e}")
        # Em caso de erro, atualiza por segurança
        return True

# Função para testar a extração de datas
def test_date_extraction():
    """Função de teste para validar a extração de datas."""
    test_files = [
        "Todas as SSAs - 15-07-2025_0143PM (2).xlsx",
        "IEE3_Emissor__202401_20250715_Todas as SSAs - 15-07-2025_1033AM.xlsx", 
        "SSAs Executadas_15-07-2025_0239PM.xlsx",
        "Consulta SSA - 14-07-2025_0343PM.xlsx",
        "Pendentes de Execução_15-07-2025_0223PM.xlsx"
    ]
    
    print("=== Teste de Extração de Datas ===")
    for filename in test_files:
        dt = extract_datetime_from_filename(filename)
        print(f"{filename:<60} -> {dt.isoformat() if dt else 'FALHA'}")

if __name__ == "__main__":
    # Executa teste se chamado diretamente
    test_date_extraction()
