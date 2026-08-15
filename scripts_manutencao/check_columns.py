import sqlite3

print("Iniciando verificação...")
try:
    conn = sqlite3.connect('data/ssas.db')
    cursor = conn.cursor()
    print("Conexão estabelecida")

    # Verificar se as colunas problemáticas existem
    problem_columns = ['registros_espera', 'numero_desvios', 'total_tempo_tex_executada', 'parciais', 'num_reprobaciones']

    cursor.execute('PRAGMA table_info(ssas)')
    columns_info = cursor.fetchall()
    existing_columns = [col[1] for col in columns_info]

    print(f"Total de colunas encontradas: {len(existing_columns)}")

    print('\nVerificação das colunas problemáticas:')
    for col in problem_columns:
        exists = col in existing_columns
        status = "EXISTE" if exists else "FALTA"
        print(f'  {col}: {status}')

    print('\nTodas as colunas no banco:')
    for i, col in enumerate(existing_columns, 1):
        print(f'  {i:2}. {col}')

    conn.close()
    print("\nVerificação concluída!")

except Exception as e:
    print(f"Erro: {e}")
    print(f"Tipo do erro: {type(e)}")
