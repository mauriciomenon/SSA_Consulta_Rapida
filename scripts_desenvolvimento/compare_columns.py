#!/usr/bin/env python3
import sqlite3

# Conectar e obter colunas reais da tabela
conn = sqlite3.connect('ssa_data.db')
cursor = conn.execute("PRAGMA table_info(ssa_table)")
real_columns = [col[1] for col in cursor.fetchall()]
conn.close()

# Colunas da consulta SQL do código
query_columns = [
    'numero_ssa',
    'situacao', 
    'derivada_de',
    'localizacao_codigo',
    'descricao_localizacao',
    'equipamento',
    'semana_cadastro',
    'data_cadastro',
    'descricao_ssa',
    'setor_emissor',
    'setor_executor',
    'solicitante',
    'servico_origem',
    'grau_prioridade_emissao',
    'grau_prioridade_planejamento',
    'execucao_simples',
    'responsavel_programacao',
    'semana_programada',
    'responsavel_execucao',
    'descricao_execucao',
    'id',
    'sistema_origem',
    'prazo_limite',
    'tempo_disponivel',
    'data_limite',
    'tempo_excedido',
    'desde',
    'tempo_total',
    'desde_1',
    'total_tempo_tpe_planejado',
    'total_tempo_tex_planejado',
    'total_tempo_tpo_planejado',
    'total_horas_programadas',
    'execucao_parcial',
    'anomalia',
    'semana_executada',
    'num_reprogramacoes'
]

print("=== ANÁLISE DE COLUNAS ===")
print(f"Colunas na tabela real: {len(real_columns)}")
print(f"Colunas na consulta SQL: {len(query_columns)}")

# Encontrar colunas que estão na consulta mas não na tabela
missing_in_table = [col for col in query_columns if col not in real_columns]
print(f"\n❌ Colunas na consulta que NÃO existem na tabela ({len(missing_in_table)}):")
for col in missing_in_table:
    print(f"  - {col}")

# Encontrar colunas que estão na tabela mas não na consulta
missing_in_query = [col for col in real_columns if col not in query_columns]
print(f"\n⚠️  Colunas na tabela que NÃO estão na consulta ({len(missing_in_query)}):")
for col in missing_in_query:
    print(f"  - {col}")

print(f"\n✅ Colunas que coincidem: {len([col for col in query_columns if col in real_columns])}")
