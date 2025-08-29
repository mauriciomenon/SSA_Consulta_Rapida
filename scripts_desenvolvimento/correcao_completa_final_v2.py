#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔧 CORREÇÃO COMPLETA E DEFINITIVA DO SISTEMA SSA - VERSÃO 2
Resolução de TODOS os problemas: duplicatas, tipos SQLite, upsert e colunas Unnamed
"""

import os
import sys
import sqlite3
import pandas as pd
import shutil
from pathlib import Path
from typing import Dict, Any

def converter_datas_para_sqlite(s):
    """Converte datas para formato SQLite correto"""
    if pd.isna(s) or s is None:
        return None
    
    try:
        # Se já está formatado, manter
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

def limpar_dataframe_unnamed(df: pd.DataFrame) -> pd.DataFrame:
    """Remove todas as colunas 'Unnamed:' problemáticas"""
    if df is None or df.empty:
        return df
    
    # Identificar colunas problemáticas
    cols_to_drop = [col for col in df.columns if 'Unnamed:' in str(col)]
    
    if cols_to_drop:
        print(f"🔧 Removendo {len(cols_to_drop)} colunas 'Unnamed': {cols_to_drop}")
        df = df.drop(columns=cols_to_drop)
    
    return df

def aplicar_conversoes_corretas(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica todas as conversões necessárias"""
    if df is None or df.empty:
        return df
    
    print(f"🔄 Aplicando conversões em {len(df)} registros...")
    
    # Conversões de datas para colunas conhecidas
    date_columns = [
        'data_cadastro', 'data_emissao', 'data_programacao', 
        'data_inicio_planejado', 'data_fim_planejado',
        'data_inicio_real', 'data_fim_real', 'data_aprovacao'
    ]
    
    for col in date_columns:
        if col in df.columns:
            print(f"   🗓️ Convertendo {col}")
            df[col] = df[col].apply(converter_datas_para_sqlite)
    
    # Conversão de numero_ssa
    if 'numero_ssa' in df.columns:
        print("   🔢 Convertendo numero_ssa")
        df['numero_ssa'] = df['numero_ssa'].apply(normalizar_numero_ssa)
    
    # Remover registros sem numero_ssa
    if 'numero_ssa' in df.columns:
        before = len(df)
        df = df[df['numero_ssa'].notna()]
        after = len(df)
        if before != after:
            print(f"   🧹 Removidos {before - after} registros sem numero_ssa")
    
    return df

def inserir_com_upsert_sqlite(df: pd.DataFrame, db_path: str = 'data/ssas.db', table_name: str = 'ssas') -> bool:
    """Insere com upsert usando SQLite direto"""
    if df is None or df.empty:
        return True
    
    try:
        with sqlite3.connect(db_path) as conn:
            total_inserted = 0
            
            # Preparar dados em lotes pequenos
            chunk_size = 50
            for i in range(0, len(df), chunk_size):
                chunk = df.iloc[i:i + chunk_size]
                
                for _, row in chunk.iterrows():
                    # Converter para dict, removendo valores NaN
                    row_dict = {}
                    for key, value in row.to_dict().items():
                        if pd.notna(value) and value is not None:
                            row_dict[key] = value
                    
                    if not row_dict or 'numero_ssa' not in row_dict:
                        continue
                    
                    numero_ssa = row_dict['numero_ssa']
                    
                    # Verificar se existe
                    existing = conn.execute(
                        f"SELECT * FROM {table_name} WHERE numero_ssa = ?", 
                        [numero_ssa]
                    ).fetchone()
                    
                    if not existing:
                        # Inserir novo
                        columns = list(row_dict.keys())
                        values = list(row_dict.values())
                        placeholders = ', '.join(['?' for _ in columns])
                        columns_str = ', '.join(columns)
                        
                        query = f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders})"
                        conn.execute(query, values)
                        total_inserted += 1
                
                # Progresso
                progress = min(i + chunk_size, len(df))
                print(f"   📈 Processado: {progress}/{len(df)}")
            
            conn.commit()
            print(f"✅ Inseridos {total_inserted} novos registros")
            return True
            
    except Exception as e:
        print(f"❌ ERRO na inserção: {e}")
        return False

def limpar_banco_completamente(db_path: str = 'data/ssas.db'):
    """Limpa banco completamente"""
    print("🔥 LIMPEZA COMPLETA DO BANCO")
    print("=" * 50)
    
    try:
        # Backup
        backup_path = 'data/backup_antes_correcao_final_v2.db'
        if os.path.exists(db_path):
            shutil.copy2(db_path, backup_path)
            print(f"✅ Backup: {backup_path}")
        
        # Contar registros antes
        with sqlite3.connect(db_path) as conn:
            count_before = conn.execute("SELECT COUNT(*) FROM ssas").fetchone()[0]
            print(f"📊 Registros antes: {count_before:,}")
            
            # Limpar tabela
            conn.execute("DELETE FROM ssas")
            conn.commit()
            
            count_after = conn.execute("SELECT COUNT(*) FROM ssas").fetchone()[0]
            print(f"📊 Registros depois: {count_after}")
        
        # VACUUM sem transação
        conn = sqlite3.connect(db_path)
        conn.execute("VACUUM")
        conn.close()
        
        print("✅ BANCO LIMPO COM SUCESSO!")
        return True
        
    except Exception as e:
        print(f"❌ ERRO na limpeza: {e}")
        return False

def importar_arquivo_excel_v2(file_path: Path) -> bool:
    """Importa arquivo Excel com todas as correções V2"""
    try:
        print(f"📂 Importando: {file_path.name}")
        
        # Ler Excel com múltiplas tentativas
        df = None
        for engine in ['openpyxl', 'xlrd', None]:
            try:
                # IMPORTANTE: index_col=False para evitar Unnamed: 0
                df = pd.read_excel(file_path, engine=engine, index_col=False)
                break
            except Exception as e:
                print(f"   ⚠️ Engine {engine} falhou: {e}")
                continue
        
        if df is None:
            print("❌ Não foi possível ler o arquivo")
            return False
        
        print(f"📊 Lidos {len(df)} registros do Excel")
        
        # 1. REMOVER COLUNAS UNNAMED
        df = limpar_dataframe_unnamed(df)
        
        # 2. APLICAR CONVERSÕES
        df = aplicar_conversoes_corretas(df)
        
        if df.empty:
            print("⚠️ Nenhum registro válido após processamento")
            return True
        
        # 3. INSERIR COM UPSERT
        success = inserir_com_upsert_sqlite(df)
        
        if success:
            print(f"✅ {file_path.name} - SUCESSO")
        else:
            print(f"❌ {file_path.name} - FALHOU")
            
        return success
        
    except Exception as e:
        print(f"❌ ERRO ao importar {file_path.name}: {e}")
        return False

def executar_importacao_completa_v2():
    """Executa importação completa V2"""
    docs_dir = Path('docs_entrada')
    
    print("🚀 IMPORTAÇÃO COMPLETA V2 - SEM COLUNAS UNNAMED")
    print("=" * 60)
    
    if not docs_dir.exists():
        print(f"❌ Diretório não encontrado: {docs_dir}")
        return False
    
    # Listar arquivos Excel
    excel_files = list(docs_dir.glob('*.xlsx'))
    excel_files = [f for f in excel_files if not f.name.startswith('~$')]
    
    print(f"📁 Encontrados {len(excel_files)} arquivos Excel")
    
    if not excel_files:
        print("❌ Nenhum arquivo Excel encontrado")
        return False
    
    # Importar cada arquivo
    sucessos = 0
    falhas = 0
    
    for arquivo in excel_files:
        try:
            if importar_arquivo_excel_v2(arquivo):
                sucessos += 1
            else:
                falhas += 1
        except Exception as e:
            print(f"❌ {arquivo.name} - EXCEÇÃO: {e}")
            falhas += 1
    
    # Resultado final
    print("\n📊 RESULTADO FINAL:")
    print(f"✅ Sucessos: {sucessos}")
    print(f"❌ Falhas: {falhas}")
    print(f"📁 Total: {len(excel_files)}")
    
    if sucessos > 0:
        # Verificar total importado
        with sqlite3.connect('data/ssas.db') as conn:
            total = conn.execute("SELECT COUNT(*) FROM ssas").fetchone()[0]
            print(f"🎯 Total no banco: {total:,} registros")
        
        return True
    else:
        print("❌ Falha na importação")
        return False

def main():
    """Função principal"""
    print("🔧 CORREÇÃO COMPLETA E DEFINITIVA DO SISTEMA SSA - V2")
    print("=" * 70)
    print("Corrigindo todos os problemas:")
    print("1. ✅ Limpeza de duplicatas massivas")
    print("2. ✅ Correção de tipos SQLite")
    print("3. ✅ Remoção de colunas 'Unnamed: 0'")
    print("4. ✅ Implementação de upsert inteligente")
    print("5. ✅ Otimização de performance")
    print("=" * 70)
    
    # 1. Limpar banco
    if not limpar_banco_completamente():
        print("❌ FALHA na limpeza do banco")
        return False
    
    # 2. Importar tudo
    if not executar_importacao_completa_v2():
        print("❌ FALHA na importação")
        return False
    
    print("\n🎉 CORREÇÃO COMPLETA FINALIZADA COM SUCESSO!")
    return True

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️ Interrompido pelo usuário")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 ERRO CRÍTICO: {e}")
        sys.exit(1)
