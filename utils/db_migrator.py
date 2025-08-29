# utils/db_migrator.py
"""
Sistema de migração segura do banco de dados SSA.

Migra dados de colunas duplicadas para versões padronizadas,
criando um novo banco otimizado mantendo todos os dados.
"""

import os
import sys
import sqlite3
import pandas as pd
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Adicionar diretório raiz ao path para imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db_maintenance import DatabaseAnalyzer, DatabaseMaintenanceError

logger = logging.getLogger(__name__)

class SafeDatabaseMigrator:
    """Executa migração completa e segura do banco de dados."""
    
    def __init__(self, source_db: str, target_db: Optional[str] = None):
        self.source_db = source_db
        self.target_db = target_db or source_db.replace('.db', '_migrated.db')
        self.analyzer = DatabaseAnalyzer(source_db)
        
    def execute_full_migration(self, schema_file: str = "config/schema_optimized.sql") -> Dict[str, any]:
        """Executa migração completa do banco de dados."""
        migration_log = {
            "start_time": datetime.now(),
            "source_db": self.source_db,
            "target_db": self.target_db,
            "backup_created": None,
            "steps_completed": [],
            "errors": [],
            "success": False
        }
        
        try:
            # 1. Criar backup do banco original
            logger.info("Criando backup do banco original...")
            backup_path = self.analyzer.create_backup()
            migration_log["backup_created"] = backup_path
            migration_log["steps_completed"].append("backup_created")
            
            # 2. Analisar dados existentes
            logger.info("Analisando estrutura de dados...")
            structure_analysis = self.analyzer.analyze_table_structure()
            migration_log["steps_completed"].append("structure_analyzed")
            
            # 3. Criar novo banco com schema otimizado
            logger.info(f"Criando novo banco: {self.target_db}")
            self._create_optimized_database(schema_file)
            migration_log["steps_completed"].append("new_database_created")
            
            # 4. Migrar dados consolidando colunas duplicadas
            logger.info("Migrando dados com consolidação...")
            migration_stats = self._migrate_data_with_consolidation(structure_analysis)
            migration_log["migration_stats"] = migration_stats
            migration_log["steps_completed"].append("data_migrated")
            
            # 5. Verificar integridade dos dados migrados
            logger.info("Verificando integridade dos dados migrados...")
            integrity_check = self._verify_migration_integrity()
            migration_log["integrity_check"] = integrity_check
            migration_log["steps_completed"].append("integrity_verified")
            
            # 6. Aplicar índices otimizados
            logger.info("Aplicando índices otimizados...")
            self._apply_optimized_indexes()
            migration_log["steps_completed"].append("indexes_applied")
            
            migration_log["success"] = True
            migration_log["end_time"] = datetime.now()
            migration_log["duration"] = str(migration_log["end_time"] - migration_log["start_time"])
            
            logger.info("Migração concluída com sucesso!")
            return migration_log
            
        except Exception as e:
            error_msg = f"Erro durante migração: {e}"
            logger.error(error_msg)
            migration_log["errors"].append(error_msg)
            migration_log["success"] = False
            migration_log["end_time"] = datetime.now()
            return migration_log
    
    def _create_optimized_database(self, schema_file: str) -> None:
        """Cria novo banco com schema otimizado."""
        if not os.path.exists(schema_file):
            raise DatabaseMaintenanceError(f"Arquivo de schema não encontrado: {schema_file}")
        
        # Remover banco target se existir
        if os.path.exists(self.target_db):
            os.remove(self.target_db)
        
        # Criar novo banco com schema otimizado
        with open(schema_file, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        
        with sqlite3.connect(self.target_db) as conn:
            conn.executescript(schema_sql)
            conn.commit()
        
        logger.info(f"Banco otimizado criado: {self.target_db}")
    
    def _migrate_data_with_consolidation(self, structure_analysis: Dict) -> Dict[str, int]:
        """Migra dados consolidando colunas duplicadas."""
        # Mapear colunas duplicadas para suas versões consolidadas
        column_mapping = {
            "Número da SSA": "numero_ssa",
            "Semana de Cadastro": "semana_cadastro",
            "Descrição Execução": "descricao_execucao",
            "Responsável na Programação": "responsavel_programacao",
            "Responsável na Execução": "responsavel_execucao",
            "Grau de Prioridade Emissão": "grau_prioridade_emissao",
            "Grau de Prioridade Planejamento": "grau_prioridade_planejamento"
        }
        
        # Ler todos os dados do banco original
        with sqlite3.connect(self.source_db) as source_conn:
            df_original = pd.read_sql_query("SELECT * FROM ssas", source_conn)
        
        logger.info(f"Lidos {len(df_original)} registros do banco original")
        
        # Consolidar dados das colunas duplicadas
        df_consolidated = df_original.copy()
        
        migration_stats = {"consolidated_columns": 0, "records_processed": len(df_original)}
        
        for source_col, target_col in column_mapping.items():
            if source_col in df_consolidated.columns and target_col in df_consolidated.columns:
                # Consolidar dados: priorizar coluna com espaços (mais dados)
                mask_empty_target = df_consolidated[target_col].isna() | (df_consolidated[target_col] == "")
                mask_has_source = df_consolidated[source_col].notna() & (df_consolidated[source_col] != "")
                
                # Atualizar target onde está vazio mas source tem dados
                update_mask = mask_empty_target & mask_has_source
                df_consolidated.loc[update_mask, target_col] = df_consolidated.loc[update_mask, source_col]
                
                # Onde ambos têm dados, priorizar source (versão com espaços)
                both_have_data = ~mask_empty_target & mask_has_source
                df_consolidated.loc[both_have_data, target_col] = df_consolidated.loc[both_have_data, source_col]
                
                updated_count = update_mask.sum() + both_have_data.sum()
                logger.info(f"Consolidados {updated_count} registros: '{source_col}' -> '{target_col}'")
                migration_stats["consolidated_columns"] += 1
                
                # Remover coluna original (com espaços)
                df_consolidated = df_consolidated.drop(columns=[source_col])
        
        # Remover colunas que não estão no schema otimizado
        target_columns = self._get_target_schema_columns()
        df_final = df_consolidated[[col for col in df_consolidated.columns if col in target_columns]]
        
        # Inserir dados consolidados no novo banco
        with sqlite3.connect(self.target_db) as target_conn:
            df_final.to_sql("ssas", target_conn, if_exists="append", index=False)
            target_conn.commit()
        
        migration_stats["final_columns"] = len(df_final.columns)
        migration_stats["records_migrated"] = len(df_final)
        
        logger.info(f"Migrados {len(df_final)} registros para o banco otimizado")
        return migration_stats
    
    def _get_target_schema_columns(self) -> List[str]:
        """Obtém lista de colunas do schema otimizado."""
        with sqlite3.connect(self.target_db) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(ssas)")
            columns_info = cursor.fetchall()
            return [col[1] for col in columns_info]
    
    def _verify_migration_integrity(self) -> Dict[str, any]:
        """Verifica integridade dos dados migrados."""
        # Verificar contagem de registros
        with sqlite3.connect(self.source_db) as source_conn:
            source_count = pd.read_sql_query("SELECT COUNT(*) as count FROM ssas", source_conn).iloc[0]['count']
        
        with sqlite3.connect(self.target_db) as target_conn:
            target_count = pd.read_sql_query("SELECT COUNT(*) as count FROM ssas", target_conn).iloc[0]['count']
        
        # Verificar dados essenciais
        with sqlite3.connect(self.target_db) as target_conn:
            df_target = pd.read_sql_query("SELECT * FROM ssas", target_conn)
        
        # Verificar se colunas essenciais têm dados
        essential_checks = {}
        essential_columns = ["numero_ssa", "semana_cadastro", "descricao_execucao"]
        
        for col in essential_columns:
            if col in df_target.columns:
                non_null_count = df_target[col].notna().sum()
                total_count = len(df_target)
                essential_checks[col] = {
                    "non_null_count": non_null_count,
                    "percentage": (non_null_count / total_count * 100) if total_count > 0 else 0
                }
        
        integrity_result = {
            "source_records": source_count,
            "target_records": target_count,
            "records_match": source_count == target_count,
            "essential_columns_check": essential_checks,
            "migration_success": source_count == target_count and all(
                check["non_null_count"] > 0 for check in essential_checks.values()
            )
        }
        
        return integrity_result
    
    def _apply_optimized_indexes(self) -> None:
        """Aplica índices otimizados já definidos no schema."""
        # Os índices já foram criados no schema, mas podemos forçar uma reindexação
        with sqlite3.connect(self.target_db) as conn:
            conn.execute("REINDEX")
            conn.commit()
        
        logger.info("Índices otimizados aplicados")
    
    def replace_original_database(self, confirm: bool = False) -> bool:
        """Substitui o banco original pelo migrado (CUIDADO!)."""
        if not confirm:
            logger.warning("Substituição do banco original não confirmada. Use confirm=True para executar.")
            return False
        
        if not os.path.exists(self.target_db):
            raise DatabaseMaintenanceError("Banco migrado não encontrado")
        
        try:
            # Criar backup adicional antes da substituição
            backup_path = self.analyzer.create_backup()
            logger.info(f"Backup adicional criado: {backup_path}")
            
            # Substituir arquivo original
            os.replace(self.target_db, self.source_db)
            logger.info(f"Banco original substituído por versão migrada")
            return True
            
        except Exception as e:
            raise DatabaseMaintenanceError(f"Erro ao substituir banco original: {e}")
    
    def generate_migration_report(self, migration_log: Dict, output_file: str = None) -> str:
        """Gera relatório detalhado da migração."""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"docs_saida/migration_report_{timestamp}.md"
        
        # Criar diretório se não existir
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        
        content = f"""# Relatório de Migração do Banco de Dados SSA

**Data da Migração:** {migration_log.get('start_time', 'N/A')}  
**Duração:** {migration_log.get('duration', 'N/A')}  
**Status:** {'✅ Sucesso' if migration_log.get('success') else '❌ Falha'}

## Detalhes da Migração

**Banco Original:** {migration_log.get('source_db')}  
**Banco Migrado:** {migration_log.get('target_db')}  
**Backup Criado:** {migration_log.get('backup_created')}

## Passos Executados

"""
        
        for step in migration_log.get('steps_completed', []):
            content += f"- ✅ {step.replace('_', ' ').title()}\n"
        
        if migration_log.get('errors'):
            content += "\n## Erros Encontrados\n\n"
            for error in migration_log['errors']:
                content += f"- ❌ {error}\n"
        
        # Estatísticas de migração
        if 'migration_stats' in migration_log:
            stats = migration_log['migration_stats']
            content += f"""
## Estatísticas de Migração

- **Registros Processados:** {stats.get('records_processed', 0)}
- **Registros Migrados:** {stats.get('records_migrated', 0)}
- **Colunas Consolidadas:** {stats.get('consolidated_columns', 0)}
- **Colunas Finais:** {stats.get('final_columns', 0)}
"""
        
        # Verificação de integridade
        if 'integrity_check' in migration_log:
            integrity = migration_log['integrity_check']
            content += f"""
## Verificação de Integridade

- **Registros Origem:** {integrity.get('source_records', 0)}
- **Registros Destino:** {integrity.get('target_records', 0)}
- **Registros Coincidem:** {'✅ Sim' if integrity.get('records_match') else '❌ Não'}
- **Migração Bem-sucedida:** {'✅ Sim' if integrity.get('migration_success') else '❌ Não'}

### Verificação de Colunas Essenciais
"""
            
            for col, check in integrity.get('essential_columns_check', {}).items():
                percentage = check.get('percentage', 0)
                content += f"- **{col}:** {check.get('non_null_count', 0)} registros ({percentage:.1f}%)\n"
        
        content += """
## Próximos Passos

1. **Validar Funcionamento:** Testar CLI e GUI com novo banco
2. **Atualizar Configurações:** Sincronizar mapeamentos se necessário
3. **Substituir Original:** Executar replace_original_database() se tudo estiver OK
4. **Limpeza:** Remover arquivos temporários e backups antigos

---
*Relatório gerado automaticamente pelo sistema de migração de banco de dados.*
"""
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Relatório de migração salvo: {output_file}")
        return output_file


def main():
    """Função principal para executar migração completa."""
    db_path = "data/ssas.db"
    
    if not os.path.exists(db_path):
        print(f"Banco de dados não encontrado: {db_path}")
        return
    
    try:
        # Executar migração
        migrator = SafeDatabaseMigrator(db_path)
        
        print("Iniciando migração completa do banco de dados...")
        print("⚠️  Esta operação criará um backup e um novo banco migrado.")
        
        # Executar migração
        migration_log = migrator.execute_full_migration()
        
        # Gerar relatório
        report_file = migrator.generate_migration_report(migration_log)
        
        if migration_log["success"]:
            print(f"\n✅ Migração concluída com sucesso!")
            print(f"📁 Banco migrado: {migration_log['target_db']}")
            print(f"📄 Relatório: {report_file}")
            print(f"💾 Backup: {migration_log['backup_created']}")
            
            # Verificação de integridade
            integrity = migration_log.get('integrity_check', {})
            if integrity.get('migration_success'):
                print("\n✅ Verificação de integridade: PASSOU")
                print("\n⚠️  Para substituir o banco original, execute:")
                print("   migrator.replace_original_database(confirm=True)")
            else:
                print("\n❌ Verificação de integridade: FALHOU")
                print("   Verifique o relatório antes de prosseguir")
        else:
            print(f"\n❌ Migração falhou!")
            print(f"📄 Relatório com erros: {report_file}")
            
    except Exception as e:
        print(f"Erro durante migração: {e}")


if __name__ == "__main__":
    main()
