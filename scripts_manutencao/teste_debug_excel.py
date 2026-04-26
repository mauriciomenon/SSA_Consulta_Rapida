try:
    import pandas as pd

    print("1. Pandas importado")

    import openpyxl  # noqa: F401

    print("2. Openpyxl importado")

    arquivo = r"c:\Users\menon\git\SSA_Consulta_Rapida\docs_entrada\Em Execução_15-08-2025_0416PM.xlsx"
    print(f"3. Tentando ler: {arquivo}")

    df = pd.read_excel(arquivo, header=1)
    print(f"4. SUCESSO! {len(df)} linhas, {len(df.columns)} colunas")

except ImportError as e:
    print(f"ERRO IMPORT: {e}")
except FileNotFoundError as e:
    print(f"ARQUIVO NAO ENCONTRADO: {e}")
except Exception as e:
    print(f"ERRO GERAL: {e}")
    import traceback

    traceback.print_exc()

print("FIM DO TESTE")
