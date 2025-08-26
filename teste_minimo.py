print("Inicio do teste")

try:
    print("Importando pandas...")
    import pandas as pd
    print("Pandas OK")
    
    print("Tentando ler Excel...")
    # Usar o arquivo que sabemos que existe
    df = pd.read_excel("docs_entrada/Todas as SSAs - 15-08-2025_0431PM.xlsx")
    print(f"Excel lido: {len(df)} linhas")
    
except Exception as e:
    print(f"Erro: {e}")

print("Fim do teste")
