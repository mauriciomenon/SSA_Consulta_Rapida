#!/usr/bin/env python3
"""Script para testar a importação corrigida"""

import sys
import os
import sqlite3
import shutil
from pathlib import Path

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent))

from armazenamento.database import get_db_connection
from core.app_logic import import_excel_file

def main():
    """Teste de importação"""
    print("🧪 TESTE DE IMPORTAÇÃO CORRIGIDA")
    print("=" * 50)
    
    # Limpar banco primeiro
    db_path = Path('data/ssas.db')
    backup_path = Path('data/ssas_backup_teste.db')
    
    # Fazer backup
    if db_path.exists():
        shutil.copy2(db_path, backup_path)
        print(f"✅ Backup criado: {backup_path}")
    
    # Limpar banco
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM ssas')
        count_before = cursor.fetchone()[0]
        print(f"📊 Registros antes: {count_before:,}")
        
        cursor.execute('DELETE FROM ssas')
        cursor.execute('VACUUM')
        conn.commit()
        print("🗑️  Banco limpo")
    
    # Testar importação com um arquivo pequeno
    test_file = Path('docs_entrada/Em Execução_15-08-2025_0416PM.xlsx')
    if test_file.exists():
        print(f"\n📂 Testando importação: {test_file.name}")
        
        try:
            result = import_excel_file(str(test_file))
            print(f"✅ Resultado da importação: {result}")
            
            # Verificar resultado
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM ssas')
                count_after = cursor.fetchone()[0]
                print(f"📊 Registros após importação: {count_after:,}")
                
                if count_after > 0:
                    cursor.execute('SELECT numero_ssa, data_cadastro FROM ssas LIMIT 5')
                    rows = cursor.fetchall()
                    print("\n📋 Primeiros registros:")
                    for i, (ssa, data) in enumerate(rows, 1):
                        print(f"  {i}. SSA: {ssa}, Data: {data}")
                    
                    print("🎉 SUCESSO! Importação funcionou!")
                else:
                    print("❌ FALHOU! Nenhum registro importado")
        
        except Exception as e:
            print(f"❌ ERRO na importação: {e}")
    else:
        print(f"❌ Arquivo de teste não encontrado: {test_file}")

if __name__ == "__main__":
    main()
