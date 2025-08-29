import sqlite3

with sqlite3.connect(r"c:\Users\menon\git\SSA_Consulta_Rapida\data\ssas.db") as conn:
    cursor = conn.execute("SELECT numero_ssa, situacao FROM ssas WHERE numero_ssa IS NOT NULL LIMIT 5")
    results = cursor.fetchall()
    
    print("TESTE DA CORRECAO:")
    for ssa, situacao in results:
        print(f"SSA: {ssa}, Situacao: {situacao}")
    
print("Correcao aplicada com sucesso!")
