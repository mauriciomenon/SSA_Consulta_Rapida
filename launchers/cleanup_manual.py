#!/usr/bin/env python3
"""
Script de Limpeza Manual - SSA Consulta Rapida
==============================================

Remove manualmente arquivos que nao deveriam estar no GitHub.
Versao simplificada, sem emojis e com execucao direta.
"""

import os
import subprocess
from pathlib import Path

def run_git_command(command, cwd=None):
    """Executa comando git e retorna resultado."""
    try:
        result = subprocess.run(
            command.split(),
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Erro no comando git: {e}")
        return None

def remove_files_from_git():
    """Remove arquivos especificos do controle de versao."""
    project_root = Path(__file__).parent.parent
    
    # Lista de arquivos/pastas para remover
    files_to_remove = [
        # Arquivos de dados sensiveis
        "data/file_cache.json",
        
        # Relatorios temporarios em docs_saida
        "docs_saida/all.csv",
        "docs_saida/all.json", 
        "docs_saida/all.xlsx",
        
        # Arquivos com timestamp
        "docs_saida/automated_tests_report_20250825_141625.md",
        "docs_saida/comprehensive_test_report_20250825_132739.json",
        "docs_saida/comprehensive_test_report_20250825_132739.md",
        "docs_saida/comprehensive_test_report_20250825_141643.json",
        "docs_saida/comprehensive_test_report_20250825_141643.md",
        "docs_saida/database_recreation_report_20250825_141502.json",
        "docs_saida/database_recreation_report_20250825_141502.md",
        
        # Relatorios de excel import
        "docs_saida/excel_import_test_report_20250825_133150.json",
        "docs_saida/excel_import_test_report_20250825_133150.md",
        "docs_saida/excel_import_test_report_20250825_133355.json",
        "docs_saida/excel_import_test_report_20250825_133355.md",
        "docs_saida/excel_import_test_report_20250825_133837.json",
        "docs_saida/excel_import_test_report_20250825_133837.md",
        "docs_saida/excel_import_test_report_20250825_134338.json",
        "docs_saida/excel_import_test_report_20250825_134338.md",
        "docs_saida/excel_import_test_report_20250825_135051.json",
        "docs_saida/excel_import_test_report_20250825_135051.md",
        "docs_saida/excel_import_test_report_20250825_135226.json",
        "docs_saida/excel_import_test_report_20250825_135226.md",
        "docs_saida/excel_import_test_report_20250825_135713.json",
        "docs_saida/excel_import_test_report_20250825_135713.md",
        "docs_saida/excel_import_test_report_20250825_135805.json",
        "docs_saida/excel_import_test_report_20250825_135805.md",
        "docs_saida/excel_import_test_report_20250825_141039.json",
        "docs_saida/excel_import_test_report_20250825_141039.md",
        "docs_saida/excel_import_test_report_20250825_141432.json",
        "docs_saida/excel_import_test_report_20250825_141432.md",
        
        # Outros relatorios temporarios
        "docs_saida/migration_report_20250825_122848.md",
        "docs_saida/performance_tests_20250825_141534.json"
    ]
    
    print(f"Removendo {len(files_to_remove)} arquivos do controle de versao...")
    
    removed_count = 0
    for file_path in files_to_remove:
        full_path = project_root / file_path
        
        # Verifica se arquivo existe localmente
        if full_path.exists():
            print(f"Mantendo local, removendo do git: {file_path}")
        else:
            print(f"Arquivo nao existe: {file_path}")
        
        # Remove do git (mantém local)
        result = run_git_command(f"git rm --cached {file_path}", cwd=project_root)
        if result is not None:
            removed_count += 1
    
    print(f"\nRemovidos {removed_count} arquivos do controle de versao")
    print("Arquivos mantidos localmente para preservar dados")
    
    return removed_count

def main():
    print("Script de Limpeza Manual - SSA Consulta Rapida")
    print("=" * 50)
    
    # Verifica se esta em um repositorio git
    if not Path('.git').exists():
        print("ERRO: Nao foi encontrado repositorio git")
        return
    
    print("ATENCAO: Esta operacao vai:")
    print("1. Remover arquivos do controle de versao do git")
    print("2. Manter os arquivos localmente")
    print("3. Atualizar .gitignore para evitar futuros commits")
    
    resposta = input("\nContinuar? (s/N): ").lower().strip()
    if resposta not in ['s', 'sim', 'y', 'yes']:
        print("Operacao cancelada")
        return
    
    # Remove arquivos do git
    removed_count = remove_files_from_git()
    
    print(f"\nConcluido! {removed_count} arquivos removidos do git")
    print("\nProximos passos:")
    print("1. git status  # Verificar mudancas")
    print("2. git add .gitignore  # Adicionar regras atualizadas") 
    print("3. git commit -m 'feat: remover arquivos temporarios e sensiveis'")
    print("4. git push origin main  # Enviar para GitHub")

if __name__ == '__main__':
    main()
