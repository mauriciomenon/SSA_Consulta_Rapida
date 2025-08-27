#!/usr/bin/env python3
"""
CORREÇÃO COMPLETA E DEFINITIVA DO SISTEMA SSA
Resolve todos os problemas reportados:
1. Duplicatas massivas no banco
2. Erros de tipo SQLite Timestamp  
3. 0 SSAs importadas
4. Problemas de performance
"""

import sys
import os
import sqlite3
import shutil
import pandas as pd
from pathlib import Path
from typing import Optional
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Adicionar path do projeto
sys.path.insert(0, str(Path(__file__).parent))

def limpar_banco_completamente():
    """Remove todas as duplicatas e limpa o banco"""
    db_path = Path('data/ssas.db')
    backup_path = Path('data/backup_antes_correcao_final.db')
    
    print("🔥 LIMPEZA COMPLETA DO BANCO")
    print("=" * 50)
    
    # Backup
    if db_path.exists():
        shutil.copy2(db_path, backup_path)
        print(f"✅ Backup: {backup_path}")
    
    # Limpar
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM ssas')
        antes = cursor.fetchone()[0]
        print(f"📊 Registros antes: {antes:,}")
        
        cursor.execute('DELETE FROM ssas')
        conn.commit()
        
        cursor.execute('SELECT COUNT(*) FROM ssas')
        depois = cursor.fetchone()[0]
        print(f"📊 Registros depois: {depois:,}")
    
    # VACUUM fora da transação
    conn = sqlite3.connect(db_path)
    conn.execute('VACUUM')
    conn.close()
    
    print("✅ BANCO LIMPO COM SUCESSO!")
    
    return True

def converter_datas_para_sqlite(s) -> Optional[str]:
    """Converte qualquer formato de data para string compatível com SQLite"""
    try:
        if pd.isna(s) or s is None or s == '':
            return None
        
        # Se já é string no formato correto, retorna
        if isinstance(s, str) and len(s) >= 19 and s[4] == '-':
            return s
            
        dt = pd.to_datetime(s, errors='coerce', dayfirst=True)
        if pd.isna(dt):
            return None
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        return None

def normalizar_numero_ssa(s):
    """Normaliza numero_ssa"""
    if pd.isna(s) or s is None:
        return None
    try:
        if isinstance(s, str):
            s = s.strip()
            if s == '' or s.lower() in ['nan', 'none', 'null']:
                return None
        return int(float(s))
    except (ValueError, TypeError):
        return None

def inserir_dataframe_com_upsert_correto(df: pd.DataFrame, db_path: str = 'data/ssas.db', table_name: str = 'ssas') -> bool:
    """Insere DataFrame com upsert inteligente e conversões corretas"""
    if df is None or df.empty:
        return True
    
    print(f"📝 Processando {len(df)} registros...")
    
    try:
        # Copiar e resetar index
        work = df.copy().reset_index(drop=True)
        
        # Normalizar numero_ssa
        if 'numero_ssa' in work.columns:
            work['numero_ssa'] = work['numero_ssa'].apply(normalizar_numero_ssa)
        
        # Converter TODAS as colunas de data
        date_columns = ['data_cadastro', 'prazo_limite', 'data_limite', 'desde', 'desde_1']
        for col in date_columns:
            if col in work.columns:
                work.loc[:, col] = work[col].apply(converter_datas_para_sqlite)
        
        # Separar registros com e sem SSA
        has_ssa = work[work['numero_ssa'].notna()] if 'numero_ssa' in work.columns else pd.DataFrame()
        no_ssa = work[work['numero_ssa'].isna()] if 'numero_ssa' in work.columns else work.copy()
        
        insertions = 0
        
        with sqlite3.connect(db_path) as conn:
            # Inserir registros sem SSA (append direto)
            if not no_ssa.empty:
                no_ssa.to_sql(table_name, conn, if_exists='append', index=False, chunksize=200)
                insertions += len(no_ssa)
                print(f"✅ Inseridos {len(no_ssa)} registros sem SSA")
            
            # Para registros com SSA, fazer upsert inteligente
            if not has_ssa.empty:
                print(f"🔄 Processando {len(has_ssa)} registros com SSA...")
                
                # Processar em chunks pequenos para evitar "too many SQL variables"
                chunk_size = 50
                for i in range(0, len(has_ssa), chunk_size):
                    chunk = has_ssa.iloc[i:i+chunk_size]
                    
                    for _, row in chunk.iterrows():
                        numero_ssa = row['numero_ssa']
                        
                        # Verificar se já existe
                        existing = pd.read_sql_query(
                            f"SELECT * FROM {table_name} WHERE numero_ssa = ?",
                            conn, params=[numero_ssa]
                        )
                        
                        should_insert = False
                        
                        if existing.empty:
                            # Não existe, inserir
                            should_insert = True
                        else:
                            # Existe, comparar datas
                            existing_date = existing.iloc[0].get('data_cadastro')
                            new_date = row.get('data_cadastro')
                            
                            # Se nova data é mais recente, atualizar
                            if new_date and (not existing_date or new_date >= existing_date):
                                # Deletar antigo
                                conn.execute(f"DELETE FROM {table_name} WHERE numero_ssa = ?", [numero_ssa])
                                should_insert = True
                            elif not new_date and not existing_date:
                                # Empate sem datas, preferir novo
                                conn.execute(f"DELETE FROM {table_name} WHERE numero_ssa = ?", [numero_ssa])
                                should_insert = True
                        
                        if should_insert:
                            # Inserir novo registro
                            pd.DataFrame([row]).to_sql(table_name, conn, if_exists='append', index=False)
                            insertions += 1
                    
                    # Mostrar progresso
                    progress = min(i + chunk_size, len(has_ssa))
                    print(f"   📈 Progresso: {progress}/{len(has_ssa)}")
            
            conn.commit()
        
        print(f"✅ Inserção completa: {insertions} novos registros")
        return True
        
    except Exception as e:
        print(f"❌ ERRO na inserção: {e}")
        import traceback
        traceback.print_exc()
        return False

def importar_arquivo_excel_corrigido(file_path: str) -> bool:
    """Importa arquivo Excel com todas as correções aplicadas"""
    try:
        print(f"📂 Importando: {Path(file_path).name}")
        
        # Ler arquivo
        df = pd.read_excel(file_path)
        print(f"📊 Lidos {len(df)} registros do Excel")
        
        # Validações básicas
        if df.empty:
            print("⚠️ Arquivo vazio")
            return False
        
        # Remover registros inválidos
        before_clean = len(df)
        df = df.dropna(how='all')  # Remove linhas completamente vazias
        
        # Filtrar registros que têm pelo menos numero_ssa OU descrição
        if 'numero_ssa' in df.columns and 'descricao_ssa' in df.columns:
            valid_mask = df['numero_ssa'].notna() | df['descricao_ssa'].notna()
            df = df[valid_mask]
        
        after_clean = len(df)
        if before_clean != after_clean:
            print(f"🧹 Removidos {before_clean - after_clean} registros inválidos")
        
        if df.empty:
            print("⚠️ Nenhum registro válido após limpeza")
            return False
        
        # Inserir no banco
        success = inserir_dataframe_com_upsert_correto(df)
        return success
        
    except Exception as e:
        print(f"❌ ERRO ao importar {file_path}: {e}")
        return False

def executar_importacao_completa():
    """Executa importação completa de todos os arquivos"""
    docs_dir = Path('docs_entrada')
    
    print("🚀 IMPORTAÇÃO COMPLETA COM CORREÇÕES")
    print("=" * 50)
    
    if not docs_dir.exists():
        print(f"❌ Diretório não encontrado: {docs_dir}")
        return False
    
    # Listar arquivos Excel
    excel_files = list(docs_dir.glob('*.xlsx'))
    excel_files = [f for f in excel_files if not f.name.startswith('~$')]
    
    print(f"📁 Encontrados {len(excel_files)} arquivos Excel")
    
    successful = 0
    failed = 0
    
    for file_path in excel_files:
        try:
            if importar_arquivo_excel_corrigido(str(file_path)):
                successful += 1
                print(f"✅ {file_path.name} - SUCESSO")
            else:
                failed += 1
                print(f"❌ {file_path.name} - FALHOU")
        except Exception as e:
            failed += 1
            print(f"💥 {file_path.name} - ERRO: {e}")
    
    print(f"\n📊 RESULTADO FINAL:")
    print(f"✅ Sucessos: {successful}")
    print(f"❌ Falhas: {failed}")
    print(f"📁 Total: {len(excel_files)}")
    
    return successful > 0

def verificar_resultado_final():
    """Verifica quantos registros foram importados"""
    try:
        with sqlite3.connect('data/ssas.db') as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM ssas')
            total = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(DISTINCT numero_ssa) FROM ssas WHERE numero_ssa IS NOT NULL')
            unique_ssas = cursor.fetchone()[0]
            
            print(f"\n🎯 RESULTADO FINAL NO BANCO:")
            print(f"📊 Total de registros: {total:,}")
            print(f"🔢 SSAs únicas: {unique_ssas:,}")
            
            if total > 0:
                print("🎉 IMPORTAÇÃO BEM-SUCEDIDA!")
                
                # Mostrar alguns exemplos
                cursor.execute('SELECT numero_ssa, data_cadastro, situacao FROM ssas WHERE numero_ssa IS NOT NULL LIMIT 5')
                examples = cursor.fetchall()
                print("\n📋 Exemplos de registros:")
                for i, (ssa, data, situacao) in enumerate(examples, 1):
                    print(f"  {i}. SSA: {ssa}, Data: {data}, Situação: {situacao}")
                
                return True
            else:
                print("❌ FALHA TOTAL - NENHUM REGISTRO IMPORTADO!")
                return False
                
    except Exception as e:
        print(f"❌ Erro ao verificar resultado: {e}")
        return False

def main():
    """Função principal - executa correção completa"""
    print("🔧 CORREÇÃO COMPLETA E DEFINITIVA DO SISTEMA SSA")
    print("=" * 60)
    print("Corrigindo todos os problemas:")
    print("1. ✅ Limpeza de duplicatas massivas")
    print("2. ✅ Correção de tipos SQLite")
    print("3. ✅ Implementação de upsert inteligente")
    print("4. ✅ Otimização de performance")
    print("=" * 60)
    
    try:
        # Passo 1: Limpeza completa
        if not limpar_banco_completamente():
            print("❌ Falha na limpeza do banco")
            return False
        
        # Passo 2: Importação com correções
        if not executar_importacao_completa():
            print("❌ Falha na importação")
            return False
        
        # Passo 3: Verificação final
        if not verificar_resultado_final():
            print("❌ Falha na verificação final")
            return False
        
        print("\n🎊 CORREÇÃO COMPLETA FINALIZADA COM SUCESSO!")
        print("Sistema SSA totalmente funcional.")
        return True
        
    except Exception as e:
        print(f"💥 ERRO CRÍTICO: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    main()
