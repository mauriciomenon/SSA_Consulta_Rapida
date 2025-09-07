#!/usr/bin/env python3
"""
Limpeza de Emergência - Remove dist_simple e outros artefatos temporários
Use este script quando dist_simple ou outros arquivos temporários estiverem 
sendo rastreados indevidamente pelo git.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def main():
    print("🧹 === LIMPEZA DE EMERGÊNCIA ===")
    
    base_dir = Path(__file__).parent.parent
    os.chdir(base_dir)
    
    # 1. Remover dist_simple do filesystem
    dist_simple = base_dir / 'launchers' / 'dist_simple'
    if dist_simple.exists():
        print(f"🗑️  Removendo {dist_simple}")
        shutil.rmtree(dist_simple)
    else:
        print("✅ dist_simple não existe no filesystem")
    
    # 2. Remover dist_simple do git se estiver sendo rastreado
    try:
        result = subprocess.run(['git', 'rm', '-r', '--cached', 'launchers/dist_simple'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("🗑️  Removido dist_simple do git")
        else:
            print("✅ dist_simple não estava sendo rastreado pelo git")
    except Exception as e:
        print(f"ℹ️  Git rm falhou (normal se não estava rastreado): {e}")
    
    # 3. Verificar outros artefatos temporários
    temp_patterns = [
        'launchers/dist/',
        'launchers/build/',
        'launchers/*.spec',
        'build/',
        'dist/',
        '**/__pycache__',
        '**/*.pyc'
    ]
    
    removed_count = 0
    for pattern in temp_patterns:
        for path in base_dir.glob(pattern):
            if path.exists():
                try:
                    if path.is_dir():
                        if 'dist' in str(path) and 'platforms' in str(path):
                            continue  # Preservar builds de plataforma
                        shutil.rmtree(path)
                        print(f"🗑️  Diretório removido: {path}")
                    else:
                        path.unlink()
                        print(f"🗑️  Arquivo removido: {path}")
                    removed_count += 1
                except Exception as e:
                    print(f"⚠️  Erro removendo {path}: {e}")
    
    # 4. Verificar status do git
    try:
        result = subprocess.run(['git', 'status', '--porcelain'], 
                              capture_output=True, text=True)
        if result.stdout.strip():
            print("\\n📋 Arquivos modificados no git:")
            for line in result.stdout.strip().split('\\n'):
                if 'dist_simple' in line:
                    print(f"❌ PROBLEMA: {line}")
                else:
                    print(f"ℹ️  {line}")
        else:
            print("✅ Nenhuma modificação pendente no git")
    except Exception as e:
        print(f"⚠️  Erro verificando git status: {e}")
    
    print(f"\\n🎯 Limpeza concluída: {removed_count} itens removidos")
    print("✅ dist_simple não deveria mais aparecer no git!")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
