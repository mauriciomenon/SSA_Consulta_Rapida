import pandas as pd

# Teste simples de um arquivo para ver formato das SSAs
try:
    print("Testando formato original das SSAs...")
    
    # Tentar ler o arquivo maior
    df = pd.read_excel(r"docs_entrada\Todas as SSAs - 15-08-2025_0431PM.xlsx", header=1, nrows=5)
    
    # Procurar coluna de SSA
    cols_ssa = [col for col in df.columns if 'ssa' in str(col).lower() or 'número' in str(col).lower()]
    print(f"Colunas SSA encontradas: {cols_ssa}")
    
    if cols_ssa:
        col_ssa = cols_ssa[0]
        print(f"Usando coluna: {col_ssa}")
        
        ssas = df[col_ssa].dropna().head(5)
        print("SSAs originais no Excel:")
        for i, ssa in enumerate(ssas):
            if pd.notna(ssa):
                # Tentar diferentes interpretações
                ssa_str = str(ssa)
                ssa_int = int(float(ssa)) if str(ssa).replace('.', '').isdigit() else ssa
                print(f"  [{i+1}] {ssa} -> str: '{ssa_str}' -> int: {ssa_int} -> dígitos: {len(str(ssa_int))}")
    
except Exception as e:
    print(f"ERRO: {e}")

print("Teste concluido")
