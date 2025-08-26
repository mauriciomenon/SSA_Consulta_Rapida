#!/usr/bin/env python3
"""
Script rápido para verificar status do banco após --rescan
"""
import sqlite3

def main():
    print("=== VERIFICAÇÃO FINAL PÓS-RESCAN ===")
    
    conn = sqlite3.connect('data/ssas.db')
    c = conn.cursor()
    
    # Contar registros totais
    total = c.execute("SELECT COUNT(*) FROM ssas").fetchone()[0]
    
    # Contar registros únicos
    unique = c.execute("SELECT COUNT(DISTINCT numero_ssa) FROM ssas").fetchone()[0]
    
    print(f"📊 Total de registros no banco: {total}")
    print(f"🔍 Registros únicos por numero_ssa: {unique}")
    
    # Verificar duplicatas
    duplicates = c.execute('''
        SELECT numero_ssa, COUNT(*) 
        FROM ssas 
        GROUP BY numero_ssa 
        HAVING COUNT(*) > 1
    ''').fetchall()
    
    print(f"⚠️  Duplicatas encontradas: {len(duplicates)}")
    
    if duplicates:
        print("❌ AINDA EXISTEM DUPLICATAS!")
        print("Primeiras 5 duplicatas:")
        for i, (ssa, count) in enumerate(duplicates[:5]):
            print(f"  {ssa}: {count} registros")
    else:
        print("✅ NENHUMA DUPLICATA ENCONTRADA!")
        print("🎉 SISTEMA FUNCIONANDO CORRETAMENTE!")
    
    # Status final
    if total == unique:
        print(f"\n🟢 STATUS: SUCESSO - {total} registros únicos mantidos")
    else:
        print(f"\n🔴 STATUS: PROBLEMA - {total - unique} duplicatas ainda existem")
    
    conn.close()

if __name__ == "__main__":
    main()
