import sqlite3

def add_unique_constraints():
    """Adiciona constraints únicos para prevenir duplicatas futuras"""
    
    print("🔧 ADICIONANDO PROTEÇÕES CONTRA DUPLICATAS")
    print("=" * 50)
    
    conn = sqlite3.connect('data/ssas.db')
    cursor = conn.cursor()
    
    try:
        # 1. Criar índice único para numero_ssa (mas permitir NULLs)
        cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_numero_ssa 
        ON ssas(numero_ssa) 
        WHERE numero_ssa IS NOT NULL AND numero_ssa != ''
        """)
        print("✅ Índice único criado para numero_ssa")
        
        # 2. Adicionar trigger para validar campos obrigatórios
        cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS validate_ssa_data
        BEFORE INSERT ON ssas
        FOR EACH ROW
        BEGIN
            -- Validar que pelo menos numero_ssa OU descricao_ssa esteja preenchido
            SELECT CASE
                WHEN (NEW.numero_ssa IS NULL OR NEW.numero_ssa = '') 
                 AND (NEW.descricao_ssa IS NULL OR NEW.descricao_ssa = '')
                THEN RAISE(ABORT, 'SSA deve ter pelo menos numero_ssa ou descricao_ssa preenchido')
            END;
        END;
        """)
        print("✅ Trigger de validação criado")
        
        # 3. Verificar integridade atual
        cursor.execute("SELECT COUNT(*) FROM ssas")
        total = cursor.fetchone()[0]
        
        cursor.execute("""
        SELECT COUNT(*) FROM ssas 
        WHERE (numero_ssa IS NULL OR numero_ssa = '') 
        AND (descricao_ssa IS NULL OR descricao_ssa = '')
        """)
        invalid = cursor.fetchone()[0]
        
        print(f"\n📊 VERIFICAÇÃO:")
        print(f"   Total de registros: {total:,}")
        print(f"   Registros inválidos: {invalid}")
        
        if invalid > 0:
            print(f"   ⚠️ {invalid} registros violam a nova regra (serão rejeitados em futuras inserções)")
        
        conn.commit()
        print("\n✅ Proteções ativadas com sucesso!")
        
    except Exception as e:
        print(f"❌ Erro ao criar proteções: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    add_unique_constraints()
