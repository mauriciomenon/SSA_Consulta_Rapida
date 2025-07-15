# setup_database.py
import sqlite3
import os

# Define o caminho para a pasta de dados e o arquivo do banco de dados
DATA_DIR = 'data'
DB_FILE = os.path.join(DATA_DIR, 'ssas.db')

# Garante que a pasta de dados exista
os.makedirs(DATA_DIR, exist_ok=True)

# Conecta ao banco de dados (será criado se não existir)
conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()

# SQL para criar a tabela (usa IF NOT EXISTS para ser seguro de re-executar)
create_table_sql = """
CREATE TABLE IF NOT EXISTS ssa (
    "Número da SSA" TEXT,
    "Localização" TEXT,
    "Setor Emissor" TEXT,
    "Setor Executor" TEXT,
    "Descrição da SSA" TEXT,
    "Descrição da Execução" TEXT
);
"""
cursor.execute(create_table_sql)

# Limpa a tabela antes de inserir para evitar duplicatas em re-execuções
cursor.execute("DELETE FROM ssa;")

# Dados a serem inseridos
ssas_data = [
    ('2025001', 'U01', 'IEE3', 'MEL4', 'Verificar ruído estranho no motor principal.', 'Ruído era causado por um parafuso solto. Parafuso reapertado.'),
    ('2025002', 'U02', 'SMM1', 'MEL4', 'Painel de controle não responde.', 'Reiniciado o sistema de controle. Problema resolvido.'),
    ('2025003', 'U01', 'IEE3', 'SVP-07', 'Vazamento de óleo identificado na base.', 'Análise pendente. Necessário investigar a causa do vazamento.'),
    ('2025004', 'U03', 'IEE3', 'MEL4', 'Luz de alerta piscando intermitentemente.', 'Nenhuma anomalia encontrada nos logs. Monitorar.')
]

# Insere os dados
cursor.executemany("INSERT INTO ssa VALUES (?, ?, ?, ?, ?, ?)", ssas_data)

# Salva as mudanças e fecha a conexão
conn.commit()
conn.close()

print(f"Banco de dados '{DB_FILE}' criado e populado com sucesso.")
