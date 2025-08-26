#!/usr/bin/env python3
"""
SOLUÇÃO DIRETA SEM PANDAS - USANDO APENAS PYTHON NATIVO
"""
import sqlite3
import json
import csv
import os

print("🔧 SOLUÇÃO DIRETA - SEM PANDAS")
print("=" * 40)

def limpar_banco():
    """Limpa banco usando SQLite direto"""
    try:
        with sqlite3.connect('data/ssas.db') as conn:
            # Backup simples
            os.system('copy data\\ssas.db data\\backup_sqlite_direto.db')
            
            # Contar antes
            count = conn.execute("SELECT COUNT(*) FROM ssas").fetchone()[0]
            print(f"📊 Registros antes: {count}")
            
            # Limpar
            conn.execute("DELETE FROM ssas")
            conn.commit()
            
            # Contar depois
            count = conn.execute("SELECT COUNT(*) FROM ssas").fetchone()[0]
            print(f"📊 Registros depois: {count}")
            
            print("✅ Banco limpo com SQLite direto!")
            return True
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

def verificar_schema():
    """Verifica schema da tabela"""
    try:
        with sqlite3.connect('data/ssas.db') as conn:
            schema = conn.execute("PRAGMA table_info(ssas)").fetchall()
            print("📋 Schema da tabela ssas:")
            for col in schema:
                print(f"   {col[1]} ({col[2]})")
            return True
    except Exception as e:
        print(f"❌ Erro ao verificar schema: {e}")
        return False

if __name__ == "__main__":
    print("Verificando schema...")
    verificar_schema()
    
    print("\nLimpando banco...")
    limpar_banco()
    
    print("\n✅ CONCLUÍDO!")
