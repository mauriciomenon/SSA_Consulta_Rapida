#!/usr/bin/env python3
"""
Análise detalhada da qualidade dos dados após importação
"""
import sqlite3
import pandas as pd

def analisar_qualidade_dados():
    print("🔍 ANÁLISE DETALHADA DE QUALIDADE DOS DADOS")
    print("=" * 60)
    
    conn = sqlite3.connect('data/ssas.db')
    
    # 1. Verificar estrutura das colunas
    print("\n📋 ESTRUTURA DAS COLUNAS:")
    colunas = conn.execute("PRAGMA table_info(ssas)").fetchall()
    for col in colunas[:10]:  # Primeiras 10 colunas
        print(f"  {col[1]} ({col[2]})")
    if len(colunas) > 10:
        print(f"  ... e mais {len(colunas) - 10} colunas")
    
    # 2. Campos obrigatórios
    print("\n🔑 CAMPOS OBRIGATÓRIOS:")
    obrigatorios = {
        'numero_ssa': 'SELECT COUNT(*) FROM ssas WHERE numero_ssa IS NULL OR numero_ssa = ""',
        'situacao': 'SELECT COUNT(*) FROM ssas WHERE situacao IS NULL OR situacao = ""',
        'descricao_ssa': 'SELECT COUNT(*) FROM ssas WHERE descricao_ssa IS NULL OR descricao_ssa = ""'
    }
    
    for campo, query in obrigatorios.items():
        vazios = conn.execute(query).fetchone()[0]
        status = "✅ OK" if vazios == 0 else f"⚠️ {vazios} vazios"
        print(f"  {campo}: {status}")
    
    # 3. Análise de situações
    print("\n📊 DISTRIBUIÇÃO POR SITUAÇÃO:")
    situacoes = conn.execute("""
        SELECT situacao, COUNT(*) as total,
               ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM ssas), 2) as percentual
        FROM ssas 
        GROUP BY situacao 
        ORDER BY total DESC
    """).fetchall()
    
    for sit, total, perc in situacoes:
        print(f"  {sit}: {total} ({perc}%)")
    
    # 4. Análise temporal
    print("\n📅 ANÁLISE TEMPORAL:")
    try:
        temporal = conn.execute("""
            SELECT 
                COUNT(CASE WHEN data_cadastro IS NOT NULL AND data_cadastro != '' THEN 1 END) as com_data,
                COUNT(CASE WHEN semana_cadastro IS NOT NULL AND semana_cadastro != '' THEN 1 END) as com_semana,
                COUNT(*) as total
            FROM ssas
        """).fetchone()
        
        print(f"  Registros com data_cadastro: {temporal[0]} ({temporal[0]/temporal[2]*100:.1f}%)")
        print(f"  Registros com semana_cadastro: {temporal[1]} ({temporal[1]/temporal[2]*100:.1f}%)")
    except Exception as e:
        print(f"  ⚠️ Erro na análise temporal: {e}")
    
    # 5. Setores mais ativos
    print("\n🏢 SETORES MAIS ATIVOS:")
    try:
        setores = conn.execute("""
            SELECT setor_emissor, COUNT(*) as total
            FROM ssas 
            WHERE setor_emissor IS NOT NULL AND setor_emissor != ''
            GROUP BY setor_emissor 
            ORDER BY total DESC 
            LIMIT 10
        """).fetchall()
        
        for setor, total in setores:
            print(f"  {setor}: {total} SSAs")
    except Exception as e:
        print(f"  ⚠️ Erro na análise de setores: {e}")
    
    # 6. Verificar duplicatas potenciais
    print("\n🔍 ANÁLISE DE DUPLICATAS:")
    try:
        duplicatas_desc = conn.execute("""
            SELECT descricao_ssa, COUNT(*) as total
            FROM ssas 
            WHERE descricao_ssa IS NOT NULL AND descricao_ssa != ''
            GROUP BY descricao_ssa 
            HAVING COUNT(*) > 1
            ORDER BY total DESC 
            LIMIT 5
        """).fetchall()
        
        if duplicatas_desc:
            print("  ⚠️ Descrições duplicadas encontradas:")
            for desc, total in duplicatas_desc:
                desc_short = (desc[:50] + "...") if len(desc) > 50 else desc
                print(f"    {total}x: {desc_short}")
        else:
            print("  ✅ Nenhuma descrição duplicada encontrada")
    except Exception as e:
        print(f"  ⚠️ Erro na análise de duplicatas: {e}")
    
    conn.close()
    print("\n✅ ANÁLISE DE QUALIDADE CONCLUÍDA")

if __name__ == "__main__":
    analisar_qualidade_dados()
