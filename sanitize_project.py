#!/usr/bin/env python3
"""
Script de sanitização e organização do projeto v3.10
"""

import os
import shutil
from pathlib import Path
import time

def log(msg, level="INFO"):
    """Log formatado"""
    timestamp = time.strftime("%H:%M:%S")
    print(f"[{timestamp}] {level}: {msg}")

def clean_pycache(directory):
    """Remove todos os __pycache__ recursivamente"""
    pycache_dirs = []
    for root, dirs, files in os.walk(directory):
        if '__pycache__' in dirs:
            pycache_dirs.append(os.path.join(root, '__pycache__'))
    
    for pycache_dir in pycache_dirs:
        try:
            shutil.rmtree(pycache_dir)
            log(f"Removido: {pycache_dir}")
        except Exception as e:
            log(f"Erro removendo {pycache_dir}: {e}", "ERROR")
    
    return len(pycache_dirs)

def clean_ds_store(directory):
    """Remove todos os .DS_Store recursivamente (macOS)"""
    ds_store_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file == '.DS_Store':
                ds_store_files.append(os.path.join(root, file))
    
    for ds_store_file in ds_store_files:
        try:
            os.remove(ds_store_file)
            log(f"Removido: {ds_store_file}")
        except Exception as e:
            log(f"Erro removendo {ds_store_file}: {e}", "ERROR")
    
    return len(ds_store_files)

def clean_temp_files():
    """Remove arquivos temporários e logs antigos"""
    temp_patterns = [
        'launchers/temp',
        'launchers/logs',
        'logs',
        'build.py',
        'emergency_import.py',
        'check_db_status.py'
    ]
    
    removed_count = 0
    for pattern in temp_patterns:
        path = Path(pattern)
        if path.exists():
            try:
                if path.is_dir():
                    shutil.rmtree(path)
                    log(f"Diretório removido: {path}")
                else:
                    path.unlink()
                    log(f"Arquivo removido: {path}")
                removed_count += 1
            except Exception as e:
                log(f"Erro removendo {path}: {e}", "ERROR")
    
    return removed_count

def organize_docs():
    """Organiza documentação"""
    # Remover documentos duplicados ou obsoletos
    obsolete_docs = [
        'launchers/RELATORIO_FINAL_v3.0.7.md',
        'docs/TRANSICAO_CONVERSA_v3.0.7.md',
        'docs/TRANSICAO_CONVERSA_v3.10.md'
    ]
    
    removed_count = 0
    for doc in obsolete_docs:
        path = Path(doc)
        if path.exists():
            try:
                path.unlink()
                log(f"Doc obsoleto removido: {path}")
                removed_count += 1
            except Exception as e:
                log(f"Erro removendo {doc}: {e}", "ERROR")
    
    return removed_count

def clean_build_artifacts():
    """Remove artefatos de build antigos"""
    build_paths = [
        'launchers/dist_simple/temp',
        'launchers/test_reports',
        'launchers/gui_launcher.py',
        'launchers/gui_launcher.pyw'
    ]
    
    removed_count = 0
    for build_path in build_paths:
        path = Path(build_path)
        if path.exists():
            try:
                if path.is_dir():
                    shutil.rmtree(path)
                    log(f"Build artifact removido: {path}")
                else:
                    path.unlink()
                    log(f"Arquivo build removido: {path}")
                removed_count += 1
            except Exception as e:
                log(f"Erro removendo {build_path}: {e}", "ERROR")
    
    return removed_count

def create_gitignore_updates():
    """Atualiza .gitignore com padrões de limpeza"""
    gitignore_additions = """
# Build artifacts
launchers/dist/
launchers/dist_simple/
launchers/temp/
launchers/logs/
launchers/test_reports/
launchers/platforms/*/venv/
launchers/platforms/*/temp/

# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# macOS
.DS_Store
.AppleDouble
.LSOverride

# Logs
*.log
logs/

# IDE
.vscode/settings.json
.idea/

# Cache
.pytest_cache/
.coverage
htmlcov/
"""
    
    try:
        # Ler .gitignore atual
        gitignore_path = Path('.gitignore')
        current_content = ""
        if gitignore_path.exists():
            current_content = gitignore_path.read_text()
        
        # Adicionar novas regras se não existirem
        if "launchers/dist/" not in current_content:
            with open(gitignore_path, 'a') as f:
                f.write(gitignore_additions)
            log("✅ .gitignore atualizado")
            return True
        else:
            log("📝 .gitignore já atualizado")
            return False
    except Exception as e:
        log(f"Erro atualizando .gitignore: {e}", "ERROR")
        return False

def main():
    """Executa limpeza completa"""
    log("=== INICIANDO SANITIZAÇÃO DO PROJETO ===")
    
    # Limpeza de cache
    pycache_count = clean_pycache(".")
    ds_store_count = clean_ds_store(".")
    log(f"Cache limpo: {pycache_count} __pycache__, {ds_store_count} .DS_Store")
    
    # Limpeza de temporários
    temp_count = clean_temp_files()
    log(f"Arquivos temporários removidos: {temp_count}")
    
    # Organização de docs
    docs_count = organize_docs()
    log(f"Documentos obsoletos removidos: {docs_count}")
    
    # Limpeza de build
    build_count = clean_build_artifacts()
    log(f"Artefatos de build removidos: {build_count}")
    
    # Atualização do .gitignore
    gitignore_updated = create_gitignore_updates()
    
    # Resumo
    total_cleaned = pycache_count + ds_store_count + temp_count + docs_count + build_count
    log("=== RESUMO DA LIMPEZA ===")
    log(f"Total de itens removidos: {total_cleaned}")
    log(f"Cache Python: {pycache_count}")
    log(f"Arquivos macOS: {ds_store_count}")
    log(f"Temporários: {temp_count}")
    log(f"Docs obsoletos: {docs_count}")
    log(f"Build artifacts: {build_count}")
    log(f"GitIgnore: {'Atualizado' if gitignore_updated else 'Já atualizado'}")
    
    log("✅ SANITIZAÇÃO CONCLUÍDA")

if __name__ == "__main__":
    main()
