import sys, os
import logging

# Configurar logging para ver as mensagens
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

sys.path.insert(0, '.')
from main import check_and_restore_database

db_path = r'data\ssas.db'
print(f'Testando verificação do banco: {db_path}')
print(f'Tamanho atual: {os.path.getsize(db_path)} bytes')

try:
    result = check_and_restore_database(db_path)
    print(f'Resultado da verificação: {result}')
    print(f'Tamanho após verificação: {os.path.getsize(db_path)} bytes')
except Exception as e:
    print(f'Erro durante verificação: {e}')
    import traceback
    traceback.print_exc()
