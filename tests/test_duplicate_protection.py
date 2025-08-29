"""
Teste das correções de duplicatas
"""
import os
import tempfile
import shutil
from core.app_logic import import_single_file

def test_duplicate_protection():
    """Testa se as proteções contra duplicatas estão funcionando"""
    
    print("🧪 TESTE DE PROTEÇÃO CONTRA DUPLICATAS")
    print("=" * 50)
    
    # Fazer backup do banco atual
    original_db = "data/ssas.db"
    backup_db = "data/ssas_test_backup.db"
    shutil.copy2(original_db, backup_db)
    print(f"✅ Backup criado: {backup_db}")
    
    try:
        # Contar registros antes
        import sqlite3
        conn = sqlite3.connect(original_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM ssas")
        count_before = cursor.fetchone()[0]
        conn.close()
        
        print(f"\n📊 Registros antes: {count_before:,}")
        
        # Tentar importar o mesmo arquivo duas vezes
        test_file = "docs_entrada/SSAs Pendentes com Execução Parcial_15-08-2025_0416PM.xlsx"
        
        if os.path.exists(test_file):
            print(f"\n🔄 Primeira importação de: {os.path.basename(test_file)}")
            result1 = import_single_file(test_file, original_db)
            
            # Contar após primeira importação
            conn = sqlite3.connect(original_db)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM ssas")
            count_after_1 = cursor.fetchone()[0]
            conn.close()
            
            print(f"   Resultado: {'✅ Sucesso' if result1 else '❌ Falha'}")
            print(f"   Registros após 1ª: {count_after_1:,} (+{count_after_1 - count_before})")
            
            print(f"\n🔄 Segunda importação (teste de duplicata)...")
            result2 = import_single_file(test_file, original_db)
            
            # Contar após segunda importação
            conn = sqlite3.connect(original_db)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM ssas")
            count_after_2 = cursor.fetchone()[0]
            conn.close()
            
            print(f"   Resultado: {'✅ Sucesso' if result2 else '❌ Falha'}")
            print(f"   Registros após 2ª: {count_after_2:,} (+{count_after_2 - count_after_1})")
            
            # Verificar se duplicatas foram evitadas
            if count_after_2 == count_after_1:
                print(f"\n✅ TESTE PASSOU: Nenhuma duplicata criada!")
            else:
                print(f"\n❌ TESTE FALHOU: {count_after_2 - count_after_1} registros duplicados criados")
        
        else:
            print(f"\n⚠️ Arquivo de teste não encontrado: {test_file}")
        
    except Exception as e:
        print(f"\n❌ Erro durante teste: {e}")
    
    finally:
        # Restaurar backup
        shutil.copy2(backup_db, original_db)
        os.remove(backup_db)
        print(f"\n🔄 Banco restaurado do backup")
    
    print(f"\n" + "=" * 50)
    print("🧪 Teste concluído!")

if __name__ == "__main__":
    test_duplicate_protection()
