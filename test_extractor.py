# test_extractor.py
import os
from extracao.extractor import read_report

# Define o caminho para nosso arquivo de teste na pasta docs
DOCS_DIR = 'docs'
FILE_NAME = 'IEE3_Emissor__202401_20250715_Todas as SSAs - 15-07-2025_1033AM.xlsx'
file_path = os.path.join(DOCS_DIR, FILE_NAME)

print("--- Iniciando teste de extração ---")

# Chama a função que queremos testar
dataframe, columns = read_report(file_path)

# Verifica se a extração foi bem-sucedida
if dataframe is not None and columns is not in None:
    print("\nTeste BEM-SUCEDIDO!")
    print(f"Shape do DataFrame (linhas, colunas): {dataframe.shape}")
    
    print("\nAs 5 primeiras linhas do relatório:")
    print(dataframe.head())

    print("\nMapa de Colunas (Nome -> Posição) gerado:")
    print(columns)
else:
    print("\nTeste FALHOU.")

print("\n--- Fim do teste de extração ---")
