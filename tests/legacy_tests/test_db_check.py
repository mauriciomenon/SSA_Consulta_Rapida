import sys, os
sys.path.insert(0, '.')
from main import check_and_restore_database

db_path = r'data\ssas.db'
print(f'Testando verificação do banco: {db_path}')
print(f'Tamanho atual: {os.path.getsize(db_path)} bytes')
result = check_and_restore_database(db_path)
print(f'Resultado da verificação: {result}')
print(f'Tamanho após verificação: {os.path.getsize(db_path)} bytes')
