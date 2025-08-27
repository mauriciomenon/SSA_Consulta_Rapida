#!/usr/bin/env python3
print("🔧 TESTE DE EXECUÇÃO")
print("=" * 30)

try:
    import pandas as pd
    print("✅ Pandas OK")
    
    import sqlite3
    print("✅ SQLite3 OK")
    
    from pathlib import Path
    print("✅ Path OK")
    
    # Testar diretórios
    docs_dir = Path('docs_entrada')
    print(f"📁 docs_entrada existe: {docs_dir.exists()}")
    
    if docs_dir.exists():
        excel_files = list(docs_dir.glob('*.xlsx'))
        print(f"📊 Arquivos Excel: {len(excel_files)}")
    
    data_dir = Path('data')
    print(f"📁 data existe: {data_dir.exists()}")
    
    # Testar conexão SQLite
    db_path = 'data/ssas.db'
    if os.path.exists(db_path):
        with sqlite3.connect(db_path) as conn:
            count = conn.execute("SELECT COUNT(*) FROM ssas").fetchone()[0]
            print(f"🗄️ Registros no banco: {count}")
    
    print("✅ TESTE COMPLETO COM SUCESSO!")
    
except Exception as e:
    print(f"❌ ERRO: {e}")
    import traceback
    traceback.print_exc()
