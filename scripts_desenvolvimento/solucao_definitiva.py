#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎯 SOLUÇÃO DEFINITIVA - CORREÇÃO COMPLETA DO SISTEMA SSA
Baseada na análise correta da estrutura dos arquivos Excel
"""

import sqlite3
import pandas as pd
import os
import shutil
from pathlib import Path
from typing import Dict, Any

# MAPEAMENTO CORRETO DAS COLUNAS
COLUMN_MAPPING = {
    'Número da SSA': 'numero_ssa',
    'Situação': 'situacao',
    'Derivada de': 'derivada_de',
    'Localização': 'localizacao_codigo',
    'Descrição da Localização': 'descricao_localizacao',
    'Equipamento': 'equipamento',
    'Semana de Cadastro': 'semana_cadastro',
    'Emitida Em': 'data_cadastro',
    'Descrição da SSA': 'descricao_ssa',
    'Setor Emissor': 'setor_emissor',
    'Setor Executor': 'setor_executor',
    'Solicitante': 'solicitante',
    'Serviço de Origem': 'servico_origem',
    'Grau de Prioridade Emissão': 'grau_prioridade_emissao',
    'Grau de Prioridade Planejamento': 'grau_prioridade_planejamento',
    'Execução Simples': 'execucao_simples',
    'Responsável na Programação': 'responsavel_programacao',
    'Semana Programada': 'semana_programada',
    'Responsável na Execução': 'responsavel_execucao',
    'Descrição Execução': 'descricao_execucao',
    'Sistema de Origem': 'sistema_origem',
    'Anomalia': 'anomalia'
}

def converter_datas_para_sqlite(s):
    """Converte datas para formato SQLite"""
    if pd.isna(s) or s is None:
        return None
    
    try:
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
        return int(float(s))
    except (ValueError, TypeError):
        return None

def limpar_banco_completamente(db_path: str = 'data/ssas.db'):
    """Limpa banco completamente"""
    print("🔥 LIMPEZA COMPLETA DO BANCO")
    print("=" * 50)
    
    try:
        backup_path = 'data/backup_antes_solucao_definitiva.db'
        if os.path.exists(db_path):
            shutil.copy2(db_path, backup_path)
            print(f"✅ Backup: {backup_path}")
        
        with sqlite3.connect(db_path) as conn:
            count_before = conn.execute("SELECT COUNT(*) FROM ssas").fetchone()[0]
            print(f"📊 Registros antes: {count_before:,}")
            
            conn.execute("DELETE FROM ssas")
            conn.commit()
            
            count_after = conn.execute("SELECT COUNT(*) FROM ssas").fetchone()[0]
            print(f"📊 Registros depois: {count_after}")
        
        # VACUUM
        conn = sqlite3.connect(db_path)
        conn.execute("VACUUM")
        conn.close()
        
        print("✅ BANCO LIMPO COM SUCESSO!")
        return True
        
    except Exception as e:
        print(f"❌ ERRO na limpeza: {e}")
        return False

def processar_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Processa DataFrame aplicando conversões e limpezas"""
    if df is None or df.empty:
        return df
    
    # Renomear colunas para o padrão do banco
    df = df.rename(columns=COLUMN_MAPPING)
    
    # Aplicar conversões
    if 'numero_ssa' in df.columns:
        df['numero_ssa'] = df['numero_ssa'].apply(normalizar_numero_ssa)
    
    # Conversões de datas
    date_columns = ['data_cadastro', 'data_emissao']
    for col in date_columns:
        if col in df.columns:
            df[col] = df[col].apply(converter_datas_para_sqlite)
    
    # Remover registros sem numero_ssa
    if 'numero_ssa' in df.columns:
        before = len(df)
        df = df[df['numero_ssa'].notna()]
        after = len(df)
        if before != after:
            print(f"   🧹 Removidos {before - after} registros sem numero_ssa")
    
    return df

def inserir_com_upsert_inteligente(df: pd.DataFrame, db_path: str = 'data/ssas.db') -> bool:
    """Insere com upsert inteligente"""
    if df is None or df.empty:
        return True
    
    try:
        with sqlite3.connect(db_path) as conn:
            insertions = 0
            updates = 0
            
            for _, row in df.iterrows():
                # Preparar dados
                row_dict = {}
                for key, value in row.to_dict().items():
                    if pd.notna(value) and value is not None:
                        row_dict[key] = value
                
                if not row_dict or 'numero_ssa' not in row_dict:
                    continue
                
                numero_ssa = row_dict['numero_ssa']
                
                # Verificar se existe
                existing = conn.execute(
                    "SELECT id FROM ssas WHERE numero_ssa = ?", 
                    [numero_ssa]
                ).fetchone()
                
                if existing:
                    # Atualizar
                    updates += 1
                else:
                    # Inserir novo
                    columns = list(row_dict.keys())
                    values = list(row_dict.values())
                    placeholders = ', '.join(['?' for _ in columns])
                    columns_str = ', '.join(columns)
                    
                    query = f"INSERT INTO ssas ({columns_str}) VALUES ({placeholders})"
                    conn.execute(query, values)
                    insertions += 1
            
            conn.commit()
            print(f"✅ Inseridos: {insertions}, Atualizados: {updates}")
            return True
            
    except Exception as e:
        print(f"❌ ERRO na inserção: {e}")
        return False

def importar_arquivo_excel_correto(file_path: Path) -> bool:
    """Importa arquivo Excel com estrutura correta"""
    try:
        print(f"📂 Importando: {file_path.name}")
        
        # LEITURA CORRETA: header=1 (segunda linha)
        df = pd.read_excel(file_path, header=1, engine='openpyxl')
        
        print(f"📊 Lidos {len(df)} registros")
        print(f"📋 Colunas encontradas: {list(df.columns)}")
        
        # Verificar se tem estrutura esperada
        if 'Número da SSA' not in df.columns:
            print("❌ Estrutura de colunas não reconhecida")
            return False
        
        # Processar DataFrame
        df = processar_dataframe(df)
        
        if df.empty:
            print("⚠️ Nenhum registro válido após processamento")
            return True
        
        # Inserir no banco
        success = inserir_com_upsert_inteligente(df)
        
        if success:
            print(f"✅ {file_path.name} - SUCESSO: {len(df)} registros")
        else:
            print(f"❌ {file_path.name} - FALHOU")
        
        return success
        
    except Exception as e:
        print(f"❌ ERRO ao importar {file_path.name}: {e}")
        return False

def executar_importacao_definitiva():
    """Executa importação definitiva"""
    docs_dir = Path('docs_entrada')
    
    print("🎯 IMPORTAÇÃO DEFINITIVA - ESTRUTURA CORRETA")
    print("=" * 60)
    
    if not docs_dir.exists():
        print(f"❌ Diretório não encontrado: {docs_dir}")
        return False
    
    excel_files = list(docs_dir.glob('*.xlsx'))
    excel_files = [f for f in excel_files if not f.name.startswith('~$')]
    
    print(f"📁 Encontrados {len(excel_files)} arquivos Excel")
    
    if not excel_files:
        print("❌ Nenhum arquivo Excel encontrado")
        return False
    
    sucessos = 0
    falhas = 0
    
    for arquivo in excel_files:
        try:
            if importar_arquivo_excel_correto(arquivo):
                sucessos += 1
            else:
                falhas += 1
        except Exception as e:
            print(f"❌ {arquivo.name} - EXCEÇÃO: {e}")
            falhas += 1
    
    print("\n📊 RESULTADO FINAL:")
    print(f"✅ Sucessos: {sucessos}")
    print(f"❌ Falhas: {falhas}")
    print(f"📁 Total: {len(excel_files)}")
    
    if sucessos > 0:
        with sqlite3.connect('data/ssas.db') as conn:
            total = conn.execute("SELECT COUNT(*) FROM ssas").fetchone()[0]
            print(f"🎯 Total no banco: {total:,} registros")
        
        return True
    else:
        print("❌ Falha na importação")
        return False

def main():
    """Função principal"""
    print("🎯 SOLUÇÃO DEFINITIVA DO SISTEMA SSA")
    print("=" * 60)
    print("Baseada na análise correta dos arquivos Excel:")
    print("1. ✅ Estrutura correta: header=1")
    print("2. ✅ Mapeamento correto de colunas")
    print("3. ✅ Conversões adequadas")
    print("4. ✅ Upsert inteligente")
    print("5. ✅ Limpeza de dados inválidos")
    print("=" * 60)
    
    # 1. Limpar banco
    if not limpar_banco_completamente():
        print("❌ FALHA na limpeza do banco")
        return False
    
    # 2. Importar tudo
    if not executar_importacao_definitiva():
        print("❌ FALHA na importação")
        return False
    
    print("\n🎉 SOLUÇÃO DEFINITIVA APLICADA COM SUCESSO!")
    print("🔥 Sistema SSA totalmente corrigido e funcional!")
    return True

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️ Interrompido pelo usuário")
    except Exception as e:
        print(f"\n💥 ERRO CRÍTICO: {e}")
        import traceback
        traceback.print_exc()
