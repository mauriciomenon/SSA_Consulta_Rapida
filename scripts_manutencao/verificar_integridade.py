#!/usr/bin/env python3
"""
Verificação rápida de integridade do banco após importação
"""
import sqlite3
import sys

def verificar_integridade():
    print("🔍 VERIFICAÇÃO DE INTEGRIDADE PÓS-IMPORTAÇÃO")
    print("=" * 60)
    
    try:
        conn = sqlite3.connect('data/ssas.db')
        cursor = conn.cursor()
        
        # Verificações básicas
        total = cursor.execute("SELECT COUNT(*) FROM ssas").fetchone()[0]
        unicos = cursor.execute("SELECT COUNT(DISTINCT numero_ssa) FROM ssas").fetchone()[0]
        nulls_ssa = cursor.execute("SELECT COUNT(*) FROM ssas WHERE numero_ssa IS NULL").fetchone()[0]
        vazios_desc = cursor.execute("SELECT COUNT(*) FROM ssas WHERE descricao_ssa IS NULL OR descricao_ssa = ''").fetchone()[0]
        
        print(f"📊 Total de registros: {total}")
        print(f"🔑 Registros únicos por numero_ssa: {unicos}")
        print(f"❌ Registros com numero_ssa NULL: {nulls_ssa}")
        print(f"❌ Registros sem descrição: {vazios_desc}")
        
        # Amostra de dados
        print("\n📋 AMOSTRA DOS DADOS:")
        amostras = cursor.execute("SELECT numero_ssa, situacao, descricao_ssa FROM ssas LIMIT 5").fetchall()
        for ssa, situacao, desc in amostras:
            desc_preview = (desc[:50] + "...") if desc and len(desc) > 50 else (desc or "N/A")
            print(f"  SSA {ssa}: {situacao} - {desc_preview}")
        
        # Verificar situações
        print("\n📈 SITUAÇÕES ENCONTRADAS:")
        situacoes = cursor.execute("SELECT situacao, COUNT(*) FROM ssas GROUP BY situacao ORDER BY COUNT(*) DESC LIMIT 10").fetchall()
        for sit, count in situacoes:
            print(f"  {sit}: {count} registros")
        
        conn.close()
        
        # Status geral
        duplicatas = total - unicos
        print(f"\n✅ RESULTADO GERAL:")
        print(f"  - Zero duplicatas: {'✅ SIM' if duplicatas == 0 else '❌ NÃO - ' + str(duplicatas) + ' duplicatas'}")
        print(f"  - Dados válidos: {'✅ SIM' if nulls_ssa == 0 else '⚠️ ' + str(nulls_ssa) + ' registros sem numero_ssa'}")
        print(f"  - Importação: {'✅ SUCESSO' if total > 0 else '❌ FALHOU'}")
        
        return total > 0 and duplicatas == 0
        
    except Exception as e:
        print(f"❌ ERRO na verificação: {e}")
        return False

if __name__ == "__main__":
    sucesso = verificar_integridade()
    sys.exit(0 if sucesso else 1)
