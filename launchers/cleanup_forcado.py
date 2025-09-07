#!/usr/bin/env python3
"""
Limpeza Forcada - Remove arquivos do git sem confirmacao
"""

import subprocess
from pathlib import Path

def run_git_rm(file_path, project_root):
    """Remove arquivo do git, ignora erros."""
    try:
        subprocess.run(
            ['git', 'rm', '--cached', file_path],
            cwd=project_root,
            capture_output=True,
            check=True
        )
        return True
    except:
        return False

def main():
    project_root = Path(__file__).parent.parent
    
    # Lista de arquivos para remover
    files_to_remove = [
        "data/file_cache.json",
        "docs_saida/all.csv",
        "docs_saida/all.json", 
        "docs_saida/all.xlsx",
        "docs_saida/automated_tests_report_20250825_141625.md",
        "docs_saida/comprehensive_test_report_20250825_132739.json",
        "docs_saida/comprehensive_test_report_20250825_132739.md",
        "docs_saida/comprehensive_test_report_20250825_141643.json",
        "docs_saida/comprehensive_test_report_20250825_141643.md",
        "docs_saida/database_recreation_report_20250825_141502.json",
        "docs_saida/database_recreation_report_20250825_141502.md",
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
        "docs_saida/migration_report_20250825_122848.md",
        "docs_saida/performance_tests_20250825_141534.json"
    ]
    
    print(f"Removendo {len(files_to_remove)} arquivos do git...")
    
    removed = 0
    for file_path in files_to_remove:
        if run_git_rm(file_path, project_root):
            print(f"OK: {file_path}")
            removed += 1
        else:
            print(f"SKIP: {file_path}")
    
    print(f"\nRemovidos: {removed} arquivos")
    print("Execute: git status")

if __name__ == '__main__':
    main()
