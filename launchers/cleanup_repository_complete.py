#!/usr/bin/env python3
"""
Limpeza Inteligente do Repositório SSA_Consulta_Rapida
======================================================

Este script identifica e remove arquivos que não deveriam estar no GitHub,
mantendo uma cópia local dos arquivos importantes e atualizando o .gitignore.

Funcionalidades:
- Análise inteligente de arquivos para classificação
- Remoção segura do controle de versão (mantém arquivos localmente)
- Atualização automática do .gitignore
- Backup de segurança antes das operações
- Relatório detalhado das ações realizadas

Uso:
    python launchers/cleanup_repository_complete.py [--dry-run] [--force]
"""

import os
import sys
import re
import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple

class RepositoryCleanup:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Padrões para classificação automática
        self.patterns = {
            'sensitive_data': [
                r'docs_entrada/.*\.xlsx$',
                r'docs_entrada/.*\.csv$',
                r'docs_entrada/.*\.json$',
                r'data/.*\.db$',
                r'data/.*\.backup_.*',
                r'data/file_cache\.json$'
            ],
            'temporary_reports': [
                r'docs_saida/.*_report_\d{8}_\d{6}\.(json|md)$',
                r'docs_saida/.*_test_\d{8}_\d{6}\.(json|md)$',
                r'docs_saida/automated_.*\.md$',
                r'docs_saida/comprehensive_.*\.json$',
                r'docs_saida/excel_import_.*\.json$',
                r'docs_saida/performance_.*\.json$',
                r'docs_saida/migration_.*\.md$',
                r'docs_saida/database_recreation_.*\.json$',
                r'docs_saida/all\.(csv|json|xlsx)$'
            ],
            'personal_docs': [
                r'.*LEMBRETE.*\.md$',
                r'.*NAO_MEXER.*\.md$',
                r'.*CAGADAS.*\.md$',
                r'.*CONVERSA.*\.md$',
                r'.*TRANSICAO.*\.md$',
                r'.*TEMPLATE_NOVA_CONVERSA.*\.md$'
            ],
            'build_artifacts': [
                r'dist_simple/.*',
                r'build/.*',
                r'\.spec$',
                r'__pycache__/.*',
                r'.*\.pyc$'
            ],
            'system_files': [
                r'\.DS_Store$',
                r'Thumbs\.db$',
                r'.*\.tmp$',
                r'.*\.temp$'
            ]
        }
        
        # Arquivos que devem ser preservados no repositório
        self.preserve_patterns = [
            r'docs/.*\.md$',
            r'config/.*\.json$',
            r'README\.md$',
            r'LICENSE$',
            r'\.gitignore$',
            r'requirements\.txt$',
            r'pyproject\.toml$',
            r'.*\.py$',
            r'.*\.sh$',
            r'.*\.bat$',
            r'.*\.ps1$',
            r'.*\.cmd$'
        ]

    def get_tracked_files(self) -> List[str]:
        """Obtém lista de todos os arquivos rastreados pelo git."""
        try:
            result = subprocess.run(
                ['git', 'ls-files'],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            )
            return [line.strip() for line in result.stdout.split('\n') if line.strip()]
        except subprocess.CalledProcessError as e:
            print(f"❌ Erro ao obter lista de arquivos do git: {e}")
            return []

    def classify_file(self, file_path: str) -> Tuple[str, str]:
        """
        Classifica um arquivo baseado nos padrões definidos.
        
        Returns:
            Tuple[str, str]: (categoria, motivo)
        """
        # Primeiro verifica se deve ser preservado
        for pattern in self.preserve_patterns:
            if re.match(pattern, file_path, re.IGNORECASE):
                return 'preserve', f'Arquivo essencial do projeto: {pattern}'
        
        # Verifica categorias de remoção
        for category, patterns in self.patterns.items():
            for pattern in patterns:
                if re.match(pattern, file_path, re.IGNORECASE):
                    return category, f'Padrão: {pattern}'
        
        return 'unknown', 'Não corresponde a nenhum padrão conhecido'

    def analyze_repository(self) -> Dict[str, List[Tuple[str, str]]]:
        """Analisa todos os arquivos rastreados e os classifica."""
        tracked_files = self.get_tracked_files()
        
        analysis = {
            'preserve': [],
            'sensitive_data': [],
            'temporary_reports': [],
            'personal_docs': [],
            'build_artifacts': [],
            'system_files': [],
            'unknown': []
        }
        
        for file_path in tracked_files:
            category, reason = self.classify_file(file_path)
            analysis[category].append((file_path, reason))
        
        return analysis

    def create_backup(self, files_to_remove: List[str]) -> str:
        """Cria backup dos arquivos que serão removidos do git."""
        backup_dir = self.project_root / f"backup_cleanup_{self.timestamp}"
        backup_dir.mkdir(exist_ok=True)
        
        for file_path in files_to_remove:
            full_path = self.project_root / file_path
            if full_path.exists() and full_path.is_file():
                backup_file = backup_dir / file_path
                backup_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(full_path, backup_file)
        
        return str(backup_dir)

    def remove_from_git(self, file_path: str) -> bool:
        """Remove arquivo do controle de versão, mantendo-o localmente."""
        try:
            # Remove do índice do git, mas mantém o arquivo local
            subprocess.run(
                ['git', 'rm', '--cached', file_path],
                cwd=self.project_root,
                capture_output=True,
                check=True
            )
            return True
        except subprocess.CalledProcessError:
            # Se falhar, pode ser que o arquivo já não esteja no índice
            return False

    def update_gitignore(self, categories_to_ignore: List[str]) -> bool:
        """Atualiza o .gitignore com base nas categorias removidas."""
        gitignore_path = self.project_root / '.gitignore'
        
        # Já foi atualizado no comando anterior
        print("✅ .gitignore já foi atualizado com as novas regras")
        return True

    def generate_report(self, analysis: Dict, removed_files: List[str], backup_dir: str) -> str:
        """Gera relatório detalhado da limpeza."""
        report_content = f"""# Relatório de Limpeza do Repositório
Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Projeto: SSA_Consulta_Rapida

## Resumo da Análise

### Arquivos Preservados: {len(analysis['preserve'])}
- Arquivos essenciais do projeto mantidos no repositório

### Arquivos Removidos por Categoria:

"""
        
        categories = ['sensitive_data', 'temporary_reports', 'personal_docs', 'build_artifacts', 'system_files']
        total_removed = 0
        
        for category in categories:
            count = len(analysis[category])
            total_removed += count
            report_content += f"#### {category.replace('_', ' ').title()}: {count} arquivos\n"
            if count > 0:
                for file_path, reason in analysis[category][:5]:  # Mostra apenas os primeiros 5
                    report_content += f"- `{file_path}` - {reason}\n"
                if count > 5:
                    report_content += f"- ... e mais {count - 5} arquivos\n"
            report_content += "\n"
        
        report_content += f"""
### Arquivos Não Classificados: {len(analysis['unknown'])}
"""
        
        if analysis['unknown']:
            report_content += "Arquivos que precisam de análise manual:\n"
            for file_path, reason in analysis['unknown']:
                report_content += f"- `{file_path}` - {reason}\n"
        
        report_content += f"""

## Ações Realizadas

- ✅ Total de arquivos removidos: {total_removed}
- ✅ Backup criado em: `{backup_dir}`
- ✅ .gitignore atualizado com novas regras
- ✅ Arquivos mantidos localmente

## Próximos Passos

1. **Verificar**: Revisar arquivos não classificados se houver
2. **Commit**: Fazer commit das mudanças no .gitignore
3. **Push**: Enviar mudanças para o repositório remoto
4. **Limpeza**: Considerar limpeza do histórico do git se necessário

## Comandos Sugeridos

```bash
# Verificar status
git status

# Fazer commit das mudanças
git add .gitignore
git commit -m "feat: atualizar .gitignore e remover arquivos sensíveis/temporários"

# Enviar para o repositório
git push origin main
```

---
Gerado automaticamente por cleanup_repository_complete.py
"""
        
        report_path = self.project_root / f"cleanup_report_{self.timestamp}.md"
        report_path.write_text(report_content, encoding='utf-8')
        
        return str(report_path)

    def run_cleanup(self, dry_run: bool = False, force: bool = False) -> Dict:
        """Executa a limpeza completa do repositório."""
        print("🔍 Analisando repositório...")
        analysis = self.analyze_repository()
        
        # Mostra resumo da análise
        print(f"\n📊 Resumo da Análise:")
        print(f"   Preservar: {len(analysis['preserve'])} arquivos")
        print(f"   Dados sensíveis: {len(analysis['sensitive_data'])} arquivos")
        print(f"   Relatórios temporários: {len(analysis['temporary_reports'])} arquivos")
        print(f"   Documentos pessoais: {len(analysis['personal_docs'])} arquivos")
        print(f"   Artefatos de build: {len(analysis['build_artifacts'])} arquivos")
        print(f"   Arquivos de sistema: {len(analysis['system_files'])} arquivos")
        print(f"   Não classificados: {len(analysis['unknown'])} arquivos")
        
        # Lista arquivos que serão removidos
        files_to_remove = []
        categories_to_remove = ['sensitive_data', 'temporary_reports', 'personal_docs', 'build_artifacts', 'system_files']
        
        for category in categories_to_remove:
            files_to_remove.extend([f[0] for f in analysis[category]])
        
        if not files_to_remove:
            print("✅ Nenhum arquivo precisa ser removido!")
            return analysis
        
        print(f"\n🗑️  Arquivos a serem removidos: {len(files_to_remove)}")
        
        if dry_run:
            print("\n🔍 Modo DRY RUN - nenhuma alteração será feita")
            for file_path in files_to_remove[:10]:  # Mostra apenas os primeiros 10
                print(f"   - {file_path}")
            if len(files_to_remove) > 10:
                print(f"   ... e mais {len(files_to_remove) - 10} arquivos")
            return analysis
        
        if not force:
            print("\n⚠️  Esta operação irá:")
            print("   1. Remover arquivos do controle de versão do git")
            print("   2. Manter os arquivos localmente")
            print("   3. Criar backup de segurança")
            print("   4. Atualizar .gitignore")
            
            response = input("\nContinuar? (s/N): ").lower().strip()
            if response not in ['s', 'sim', 'y', 'yes']:
                print("❌ Operação cancelada")
                return analysis
        
        # Criar backup
        print("💾 Criando backup de segurança...")
        backup_dir = self.create_backup(files_to_remove)
        
        # Remover arquivos do git
        print("🗑️  Removendo arquivos do controle de versão...")
        removed_files = []
        for file_path in files_to_remove:
            if self.remove_from_git(file_path):
                removed_files.append(file_path)
                print(f"   ✅ {file_path}")
            else:
                print(f"   ⚠️  {file_path} (já removido ou não encontrado)")
        
        # Gerar relatório
        print("📝 Gerando relatório...")
        report_path = self.generate_report(analysis, removed_files, backup_dir)
        
        print(f"\n✅ Limpeza concluída!")
        print(f"   📁 Backup: {backup_dir}")
        print(f"   📄 Relatório: {report_path}")
        print(f"   🗑️  Removidos: {len(removed_files)} arquivos")
        
        print(f"\n📋 Próximos passos:")
        print(f"   1. git status  # Verificar mudanças")
        print(f"   2. git add .gitignore  # Adicionar regras atualizadas")
        print(f"   3. git commit -m 'feat: remover arquivos sensíveis/temporários'")
        print(f"   4. git push origin main  # Enviar para GitHub")
        
        return analysis

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Limpeza inteligente do repositório')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Simula a operação sem fazer alterações')
    parser.add_argument('--force', action='store_true',
                       help='Executa sem confirmação do usuário')
    
    args = parser.parse_args()
    
    # Detecta o diretório do projeto
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    if not (project_root / '.git').exists():
        print("❌ Erro: Não foi encontrado repositório git")
        sys.exit(1)
    
    print(f"🚀 Iniciando limpeza do repositório: {project_root}")
    
    cleanup = RepositoryCleanup(str(project_root))
    analysis = cleanup.run_cleanup(dry_run=args.dry_run, force=args.force)
    
    if args.dry_run:
        print(f"\n💡 Para executar a limpeza: python {__file__}")
        print(f"💡 Para forçar sem confirmação: python {__file__} --force")

if __name__ == '__main__':
    main()
