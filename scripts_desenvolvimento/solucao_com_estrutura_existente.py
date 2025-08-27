#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎯 SOLUÇÃO DEFINITIVA RESPEITANDO A ESTRUTURA EXISTENTE
Usa os mapeamentos e extractors existentes do sistema
"""

import sqlite3
import pandas as pd
import os
import shutil
from pathlib import Path
import logging
from typing import Dict, Any, Optional

# IMPORTAR MÓDULOS EXISTENTES DO SISTEMA
from extracao.extractor import extract_data_from_excel
from armazenamento.database import insert_dataframe_with_smart_upsert

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def limpar_banco_completamente(db_path: str = 'data/ssas.db'):
    """Limpa banco completamente usando estrutura existente"""
    print("🔥 LIMPEZA COMPLETA DO BANCO")
    print("=" * 50)
    
    try:
        backup_path = 'data/backup_antes_solucao_estrutura_existente.db'
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

def importar_arquivo_usando_extractor(file_path: Path) -> bool:
    """Importa arquivo Excel usando o extractor existente do sistema"""
    try:
        print(f"📂 Importando: {file_path.name}")
        
        # USAR O EXTRACTOR EXISTENTE que já faz todo o mapeamento correto
        df = extract_data_from_excel(str(file_path))
        
        if df is None:
            print(f"❌ Falha na extração do arquivo: {file_path.name}")
            return False
        
        if df.empty:
            print(f"⚠️ Arquivo vazio após extração: {file_path.name}")
            return True
        
        print(f"📊 Extraídos {len(df)} registros com colunas: {list(df.columns)}")
        
        # USAR O UPSERT EXISTENTE que já trata duplicatas corretamente
        success = insert_dataframe_with_smart_upsert(df, 'data/ssas.db')
        
        if success:
            print(f"✅ {file_path.name} - SUCESSO: {len(df)} registros")
        else:
            print(f"❌ {file_path.name} - FALHOU na inserção")
        
        return success
        
    except Exception as e:
        print(f"❌ ERRO ao importar {file_path.name}: {e}")
        logger.error(f"Erro detalhado ao importar {file_path.name}: {e}", exc_info=True)
        return False

def executar_importacao_usando_sistema_existente():
    """Executa importação usando toda a infraestrutura existente"""
    docs_dir = Path('docs_entrada')
    
    print("🎯 IMPORTAÇÃO USANDO SISTEMA EXISTENTE")
    print("=" * 60)
    print("✅ Usando extractor.py para mapeamento de colunas")
    print("✅ Usando database.py para upsert inteligente")  
    print("✅ Respeitando config/column_mappings.json")
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
            if importar_arquivo_usando_extractor(arquivo):
                sucessos += 1
            else:
                falhas += 1
                
            # Log de progresso
            total_processados = sucessos + falhas
            print(f"📈 Progresso: {total_processados}/{len(excel_files)} ({(total_processados/len(excel_files)*100):.1f}%)")
            
        except Exception as e:
            print(f"❌ {arquivo.name} - EXCEÇÃO: {e}")
            logger.error(f"Exceção ao processar {arquivo.name}: {e}", exc_info=True)
            falhas += 1
    
    print("\n📊 RESULTADO FINAL:")
    print(f"✅ Sucessos: {sucessos}")
    print(f"❌ Falhas: {falhas}")
    print(f"📁 Total: {len(excel_files)}")
    print(f"📈 Taxa de sucesso: {(sucessos/len(excel_files)*100):.1f}%")
    
    if sucessos > 0:
        try:
            with sqlite3.connect('data/ssas.db') as conn:
                total = conn.execute("SELECT COUNT(*) FROM ssas").fetchone()[0]
                print(f"🎯 Total no banco: {total:,} registros")
                
                # Verificar alguns registros de amostra
                sample = conn.execute("SELECT numero_ssa, situacao, descricao_ssa FROM ssas LIMIT 3").fetchall()
                print(f"📋 Amostra dos dados:")
                for row in sample:
                    print(f"   SSA {row[0]}: {row[1]} - {row[2][:50] if row[2] else 'N/A'}...")
        except Exception as e:
            print(f"⚠️ Erro ao verificar dados finais: {e}")
        
        return True
    else:
        print("❌ Falha total na importação")
        return False

def main():
    """Função principal respeitando estrutura existente"""
    print("🎯 SOLUÇÃO DEFINITIVA COM ESTRUTURA EXISTENTE")
    print("=" * 70)
    print("🔧 Corrigindo problemas RESPEITANDO a arquitetura atual:")
    print("1. ✅ Usando extracao/extractor.py existente")
    print("2. ✅ Usando armazenamento/database.py existente")
    print("3. ✅ Respeitando config/column_mappings.json")
    print("4. ✅ Mantendo logging e tratamento de erros")
    print("5. ✅ Limpeza inicial + importação completa")
    print("=" * 70)
    
    # 1. Limpar banco
    if not limpar_banco_completamente():
        print("❌ FALHA na limpeza do banco")
        return False
    
    # 2. Importar usando sistema existente
    if not executar_importacao_usando_sistema_existente():
        print("❌ FALHA na importação")
        return False
    
    print("\n🎉 SOLUÇÃO IMPLEMENTADA COM SUCESSO!")
    print("🔥 Sistema SSA corrigido usando a estrutura existente!")
    print("📋 Todos os mapeamentos e funcionalidades preservados!")
    return True

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️ Interrompido pelo usuário")
    except Exception as e:
        print(f"\n💥 ERRO CRÍTICO: {e}")
        logger.error(f"Erro crítico na execução: {e}", exc_info=True)
        import traceback
        traceback.print_exc()
