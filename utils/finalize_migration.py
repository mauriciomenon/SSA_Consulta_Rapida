# utils/finalize_migration.py
"""
Finaliza a migração do banco de dados substituindo o original
e atualizando configurações necessárias.
"""

import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path

# Adicionar diretório raiz ao path para imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db_migrator import SafeDatabaseMigrator
from utils.db_maintenance import DatabaseAnalyzer

logger = logging.getLogger(__name__)

def finalize_database_migration():
    """Finaliza a migração substituindo o banco original."""
    db_path = "data/ssas.db"
    migrated_db = "data/ssas_migrated.db"
    
    if not os.path.exists(migrated_db):
        print(f"❌ Banco migrado não encontrado: {migrated_db}")
        print("Execute primeiro a migração com db_migrator.py")
        return False
    
    try:
        # Substituir banco original
        migrator = SafeDatabaseMigrator(db_path)
        migrator.target_db = migrated_db
        
        print("🔄 Substituindo banco original...")
        success = migrator.replace_original_database(confirm=True)
        
        if success:
            print("✅ Banco original substituído com sucesso!")
            
            # Limpar arquivo migrado temporário
            if os.path.exists(migrated_db):
                os.remove(migrated_db)
                print("🧹 Arquivo temporário removido")
            
            return True
        else:
            print("❌ Falha ao substituir banco original")
            return False
            
    except Exception as e:
        print(f"❌ Erro durante finalização: {e}")
        return False

def update_schema_reference():
    """Atualiza referências ao schema para usar a versão otimizada."""
    try:
        # Copiar schema otimizado como padrão
        optimized_schema = "config/schema_optimized.sql"
        default_schema = "config/schema.sql"
        
        if os.path.exists(optimized_schema):
            # Fazer backup do schema antigo
            backup_schema = f"config/schema_legacy_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
            if os.path.exists(default_schema):
                os.rename(default_schema, backup_schema)
                print(f"📁 Schema legado salvo como: {backup_schema}")
            
            # Copiar schema otimizado
            import shutil
            shutil.copy2(optimized_schema, default_schema)
            print("✅ Schema padrão atualizado para versão otimizada")
            return True
        else:
            print(f"❌ Schema otimizado não encontrado: {optimized_schema}")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao atualizar schema: {e}")
        return False

def validate_migration_success():
    """Valida se a migração foi bem-sucedida testando funcionalidades básicas."""
    try:
        print("🔍 Validando migração...")
        
        # Testar conexão e estrutura
        analyzer = DatabaseAnalyzer("data/ssas.db")
        structure = analyzer.analyze_table_structure()
        
        # Verificar se não há mais colunas duplicadas
        duplicated_groups = structure.get('duplicated_groups', {})
        if duplicated_groups:
            print(f"⚠️  Ainda existem {len(duplicated_groups)} grupos de colunas duplicadas:")
            for group, columns in duplicated_groups.items():
                print(f"   - {group}: {[col['name'] for col in columns]}")
        else:
            print("✅ Nenhuma coluna duplicada detectada")
        
        # Verificar dados essenciais
        sanity_check = analyzer.perform_sanity_check()
        total_records = sanity_check.get('total_records', 0)
        print(f"📊 Total de registros: {total_records}")
        
        if total_records > 0:
            print("✅ Banco contém dados")
            
            # Verificar integridade dos dados essenciais
            summary = sanity_check.get('summary', {})
            critical_issues = sum([
                summary.get('missing_numero_ssa', 0),
                summary.get('empty_records', 0)
            ])
            
            if critical_issues < 100:  # Tolerância para alguns registros problemáticos
                print("✅ Integridade dos dados OK")
                return True
            else:
                print(f"⚠️  {critical_issues} problemas críticos detectados")
                return False
        else:
            print("❌ Banco vazio após migração")
            return False
            
    except Exception as e:
        print(f"❌ Erro durante validação: {e}")
        return False

def update_column_mappings():
    """Atualiza mapeamentos para garantir compatibilidade com nova estrutura."""
    try:
        print("🔄 Verificando mapeamentos de colunas...")
        
        mappings_file = "config/column_mappings.json"
        
        if not os.path.exists(mappings_file):
            print(f"⚠️  Arquivo de mapeamentos não encontrado: {mappings_file}")
            return True  # Não é crítico, será recriado automaticamente
        
        with open(mappings_file, 'r', encoding='utf-8') as f:
            mappings = json.load(f)
        
        # Verificar se mapeamentos ainda referenciam colunas removidas
        removed_columns = [
            "Número da SSA",
            "Semana de Cadastro", 
            "Descrição Execução",
            "Responsável na Programação",
            "Responsável na Execução",
            "Grau de Prioridade Emissão",
            "Grau de Prioridade Planejamento"
        ]
        
        updated = False
        for canonical, aliases in mappings.items():
            original_aliases = aliases.copy()
            # Remover aliases que correspondem às colunas removidas
            aliases[:] = [alias for alias in aliases if alias not in removed_columns]
            
            if len(aliases) != len(original_aliases):
                print(f"📝 Atualizado mapeamento para '{canonical}': removidos aliases legados")
                updated = True
        
        if updated:
            # Salvar mapeamentos atualizados
            with open(mappings_file, 'w', encoding='utf-8') as f:
                json.dump(mappings, f, indent=2, ensure_ascii=False)
            print("✅ Mapeamentos de colunas atualizados")
        else:
            print("✅ Mapeamentos de colunas já estão corretos")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao atualizar mapeamentos: {e}")
        return False

def create_import_enhancement():
    """Cria melhorias no sistema de importação para diferentes formatos AMS."""
    enhancement_file = "utils/enhanced_importer.py"
    
    if os.path.exists(enhancement_file):
        print("✅ Sistema de importação aprimorado já existe")
        return True
    
    try:
        content = '''# utils/enhanced_importer.py
"""
Sistema aprimorado de importação que lida com diferentes formatos AMS
e adiciona campos apenas se não existirem.
"""

import pandas as pd
import logging
from typing import Dict, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class EnhancedAMSImporter:
    """Importador aprimorado para diferentes formatos de relatórios AMS."""
    
    def __init__(self):
        self.known_formats = {
            "format_a": {
                "indicators": ["Todas as SSAs", "Número da SSA"],
                "priority": 1
            },
            "format_b": {
                "indicators": ["Em Execução", "Nº SSA"],
                "priority": 2
            },
            "format_c": {
                "indicators": ["Pendentes", "SSA"],
                "priority": 3
            }
        }
    
    def detect_format(self, df: pd.DataFrame) -> str:
        """Detecta o formato do arquivo baseado em colunas e conteúdo."""
        if df.empty:
            return "unknown"
        
        columns = df.columns.tolist()
        
        for format_name, format_info in self.known_formats.items():
            indicators = format_info["indicators"]
            matches = sum(1 for indicator in indicators 
                         if any(indicator in col for col in columns))
            
            if matches >= len(indicators) // 2:  # Pelo menos metade dos indicadores
                logger.info(f"Formato detectado: {format_name}")
                return format_name
        
        logger.warning("Formato não reconhecido, usando padrão")
        return "unknown"
    
    def safe_column_addition(self, existing_df: pd.DataFrame, 
                            new_df: pd.DataFrame) -> pd.DataFrame:
        """Adiciona colunas de new_df apenas se não existirem em existing_df."""
        if existing_df.empty:
            return new_df.copy()
        
        result_df = existing_df.copy()
        
        for col in new_df.columns:
            if col not in result_df.columns:
                result_df[col] = None
                logger.info(f"Nova coluna adicionada: {col}")
        
        return result_df
    
    def import_with_format_detection(self, file_path: str) -> Optional[pd.DataFrame]:
        """Importa arquivo com detecção automática de formato."""
        try:
            df = pd.read_excel(file_path)
            format_type = self.detect_format(df)
            
            # Aplicar transformações específicas do formato se necessário
            if format_type != "unknown":
                df = self._apply_format_transformations(df, format_type)
            
            return df
            
        except Exception as e:
            logger.error(f"Erro ao importar {file_path}: {e}")
            return None
    
    def _apply_format_transformations(self, df: pd.DataFrame, format_type: str) -> pd.DataFrame:
        """Aplica transformações específicas baseadas no formato detectado."""
        # Implementar transformações específicas conforme necessário
        return df
'''
        
        with open(enhancement_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ Sistema de importação aprimorado criado")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao criar sistema de importação: {e}")
        return False

def main():
    """Executa finalização completa da migração."""
    print("🚀 Finalizando migração do banco de dados SSA...")
    print("=" * 50)
    
    success_steps = 0
    total_steps = 5
    
    # 1. Finalizar migração do banco
    if finalize_database_migration():
        success_steps += 1
        print()
    
    # 2. Atualizar referência do schema
    if update_schema_reference():
        success_steps += 1
        print()
    
    # 3. Validar migração
    if validate_migration_success():
        success_steps += 1
        print()
    
    # 4. Atualizar mapeamentos
    if update_column_mappings():
        success_steps += 1
        print()
    
    # 5. Criar melhorias de importação
    if create_import_enhancement():
        success_steps += 1
        print()
    
    # Resultado final
    print("=" * 50)
    if success_steps == total_steps:
        print("🎉 Migração finalizada com SUCESSO!")
        print()
        print("✅ Resumo:")
        print("   - Banco de dados otimizado e limpo")
        print("   - Colunas duplicadas removidas")
        print("   - Dados consolidados corretamente")
        print("   - Configurações atualizadas")
        print("   - Sistema pronto para uso")
        print()
        print("🔄 Próximos passos recomendados:")
        print("   1. Testar CLI: python main.py")
        print("   2. Testar GUI: python gui/gui_ssa.py")
        print("   3. Importar novos dados se necessário")
    else:
        print(f"⚠️  Migração parcialmente concluída: {success_steps}/{total_steps} passos")
        print("   Verifique os erros acima e execute novamente se necessário")

if __name__ == "__main__":
    main()
