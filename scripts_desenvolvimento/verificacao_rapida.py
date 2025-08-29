#!/usr/bin/env python3
# verificacao_rapida.py - Script de diagnóstico rápido
"""
Script para verificação rápida do status do sistema SSA Consulta Rápida.
Execute este script para diagnóstico inicial de problemas.
"""

import os
import sys
import sqlite3
from pathlib import Path

def main():
    print("🔍 VERIFICAÇÃO RÁPIDA - SSA Consulta Rápida v3.0.7")
    print("=" * 60)
    
    # Verificar estrutura básica
    print("\n📁 ESTRUTURA DE PASTAS:")
    pastas_essenciais = [
        "armazenamento", "core", "extracao", "gui", "interface", 
        "config", "data", "docs_entrada", "docs_saida"
    ]
    
    for pasta in pastas_essenciais:
        if Path(pasta).exists():
            print(f"  ✅ {pasta}/")
        else:
            print(f"  ❌ {pasta}/ - AUSENTE!")
    
    # Verificar arquivos críticos
    print("\n📄 ARQUIVOS CRÍTICOS:")
    arquivos_criticos = [
        "main.py", "config/column_mappings.json", 
        "armazenamento/database.py", "extracao/extractor.py"
    ]
    
    for arquivo in arquivos_criticos:
        if Path(arquivo).exists():
            print(f"  ✅ {arquivo}")
        else:
            print(f"  ❌ {arquivo} - AUSENTE!")
    
    # Verificar banco de dados
    print("\n💾 BANCO DE DADOS:")
    db_path = Path("data/ssas.db")
    if db_path.exists():
        size_mb = db_path.stat().st_size / (1024 * 1024)
        print(f"  ✅ ssas.db ({size_mb:.1f} MB)")
        
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM ssas")
            total = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(DISTINCT numero_ssa) FROM ssas WHERE numero_ssa IS NOT NULL")
            unique = cursor.fetchone()[0]
            conn.close()
            
            print(f"  📊 Total de registros: {total}")
            print(f"  🔢 SSAs únicas: {unique}")
            
            if total == unique:
                print(f"  ✅ Sem duplicatas")
            else:
                print(f"  ⚠️ Possíveis duplicatas: {total - unique}")
                
        except Exception as e:
            print(f"  ❌ Erro ao acessar banco: {e}")
    else:
        print("  ❌ ssas.db - AUSENTE!")
    
    # Verificar arquivos de entrada
    print("\n📥 ARQUIVOS DE ENTRADA:")
    docs_entrada = Path("docs_entrada")
    if docs_entrada.exists():
        arquivos_excel = list(docs_entrada.glob("*.xlsx"))
        arquivos_validos = [f for f in arquivos_excel if not f.name.startswith("~")]
        print(f"  📁 Total de arquivos: {len(arquivos_validos)}")
        if len(arquivos_validos) > 0:
            print(f"  📄 Primeiro arquivo: {arquivos_validos[0].name}")
            print(f"  📄 Último arquivo: {arquivos_validos[-1].name}")
    else:
        print("  ❌ Pasta docs_entrada/ - AUSENTE!")
    
    # Verificar logs recentes
    print("\n📝 LOGS:")
    logs_path = Path("logs")
    if logs_path.exists():
        log_files = list(logs_path.glob("*.log"))
        if log_files:
            latest_log = max(log_files, key=lambda f: f.stat().st_mtime)
            print(f"  📄 Log mais recente: {latest_log.name}")
        else:
            print("  ⚠️ Nenhum arquivo de log encontrado")
    else:
        print("  ❌ Pasta logs/ - AUSENTE!")
    
    print("\n" + "=" * 60)
    print("✅ Verificação concluída!")
    print("\n🔧 PRÓXIMOS PASSOS RECOMENDADOS:")
    print("1. Se há problemas, leia ESTRUTURA_PROJETO.md")
    print("2. Para importação com erros, execute:")
    print("   python scripts_desenvolvimento/test_import_verification.py")
    print("3. Para uso normal:")
    print("   python main.py")

if __name__ == "__main__":
    main()
