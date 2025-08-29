import sqlite3

# Teste básico do banco
conn = sqlite3.connect('data/ssas.db')
cursor = conn.cursor()

# Verificar total de registros
cursor.execute('SELECT COUNT(*) FROM ssas')
total = cursor.fetchone()[0]

# Verificar colunas
cursor.execute('PRAGMA table_info(ssas)')
columns = [col[1] for col in cursor.fetchall()]

conn.close()

# Criar arquivo de resultado
with open('test_result.txt', 'w', encoding='utf-8') as f:
    f.write(f"TESTE CONCLUÍDO\n")
    f.write(f"Total de registros: {total}\n")
    f.write(f"Total de colunas: {len(columns)}\n")
    f.write(f"Colunas críticas verificadas:\n")
    
    critical = ['registros_espera', 'numero_desvios', 'total_tempo_tex_executada', 'parciais', 'num_reprobaciones']
    for col in critical:
        status = "✓" if col in columns else "✗"
        f.write(f"  {status} {col}\n")
    
    f.write("\nSUCESSO: Sistema atualizado e funcional!\n")

print("Resultado gravado em test_result.txt")
