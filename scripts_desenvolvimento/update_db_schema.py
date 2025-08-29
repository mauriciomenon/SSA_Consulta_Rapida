#!/usr/bin/env python3
"""
Script para adicionar as colunas necessárias ao banco principal
"""

import sqlite3
import os

def update_database_schema():
    db_path = 'data/ssas.db'
    
    if not os.path.exists(db_path):
        print(f"❌ Banco de dados não encontrado: {db_path}")
        return False
    
    print("🔧 Adicionando colunas ao banco principal...")
    
    # Colunas que precisam ser adicionadas
    new_columns = [
        'registros_espera TEXT',
        'num_reprobaciones INTEGER', 
        'situacao_espera TEXT',
        'numero_desvios INTEGER',
        'ate TEXT',
        'justificativa TEXT',
        'total_tempo_tex_executada TEXT',
        'parciais TEXT',
        'situacao_da_parcial TEXT'
    ]
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verificar total de registros antes
        cursor.execute('SELECT COUNT(*) FROM ssas')
        records_before = cursor.fetchone()[0]
        print(f"📊 Registros antes da atualização: {records_before}")
        
        # Adicionar cada coluna
        for column_def in new_columns:
            column_name = column_def.split()[0]
            try:
                cursor.execute(f'ALTER TABLE ssas ADD COLUMN {column_def}')
                print(f"  ✅ Adicionada: {column_name}")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e):
                    print(f"  ⚠️  Já existe: {column_name}")
                else:
                    print(f"  ❌ Erro em {column_name}: {e}")
        
        conn.commit()
        
        # Verificar total de registros depois
        cursor.execute('SELECT COUNT(*) FROM ssas')
        records_after = cursor.fetchone()[0]
        print(f"📊 Registros após atualização: {records_after}")
        
        # Verificar estrutura final
        cursor.execute('PRAGMA table_info(ssas)')
        columns = cursor.fetchall()
        print(f"📋 Total de colunas: {len(columns)}")
        
        conn.close()
        
        if records_before == records_after:
            print("✅ Atualização concluída com sucesso - dados preservados!")
            return True
        else:
            print("❌ ERRO: Perda de dados detectada!")
            return False
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

if __name__ == "__main__":
    success = update_database_schema()
    if success:
        print("\n🎉 Banco atualizado! Agora pode executar --rescan sem erros.")
    else:
        print("\n💥 Falha na atualização. Verifique o backup.")
