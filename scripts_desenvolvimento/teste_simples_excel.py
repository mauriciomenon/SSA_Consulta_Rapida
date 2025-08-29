import pandas as pd

print("Teste simples de arquivo problematico...")

try:
    arquivo = r"c:\Users\menon\git\SSA_Consulta_Rapida\docs_entrada\Em Execução_15-08-2025_0416PM.xlsx"
    df = pd.read_excel(arquivo, header=1)
    print(f"Sucesso! Linhas: {len(df)}, Colunas: {len(df.columns)}")
    
    # Verificar indices duplicados
    if df.index.duplicated().any():
        print(f"PROBLEMA: {df.index.duplicated().sum()} indices duplicados")
    else:
        print("Indices OK")
        
except Exception as e:
    print(f"ERRO: {e}")
    
print("Teste concluido")
