#!/usr/bin/env python3
"""
Build SIMPLIFICADO v3.10 - FUNCIONANDO
Sem complexidades desnecessarias
IMPORTANTE: Este script usa dist_simple que e temporario e NAO deve ir para o git!
"""

import os
import sys
import subprocess
import shutil
import atexit
from pathlib import Path

def cleanup_dist_simple():
    """Funcao para limpar dist_simple ao sair"""
    dist_dir = Path(__file__).parent.parent / 'launchers' / 'dist_simple'
    if dist_dir.exists():
        try:
            shutil.rmtree(dist_dir)
            print(f"🧹 Limpeza automática: {dist_dir} removido")
        except Exception as e:
            print(f"⚠️  Erro na limpeza: {e}")

def main():
    print("=== SSA Consulta Rapida v3.10 - Build Simples ===")
    print("⚠️  AVISO: dist_simple é temporário e será limpo automaticamente!")
    
    # Registrar limpeza automática
    atexit.register(cleanup_dist_simple)
    
    # Diretórios
    base_dir = Path(__file__).parent.parent
    dist_dir = base_dir / 'launchers' / 'dist_simple'
    
    # Limpar build anterior
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    dist_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Base dir: {base_dir}")
    print(f"Dist dir: {dist_dir}")
    
    # Comando PyInstaller simples e FUNCIONAL
    cmd_cli = [
        'pyinstaller',
        '--onedir',
        '--console', 
        '--name', 'SSA_CLI_v3.10_SIMPLES',
        '--distpath', str(dist_dir),
        '--workpath', str(dist_dir / 'temp'),
        '--specpath', str(dist_dir),
        '--paths', str(base_dir),  # IMPORTANTE: path do projeto
        '--add-data', f'{base_dir}/config:config',
        '--add-data', f'{base_dir}/data:data',
        '--hidden-import', 'pandas._libs.tslibs.base',
        '--hidden-import', 'pandas._libs.tslibs.nattype',
        '--hidden-import', 'openpyxl.descriptors.serialisable',
        str(base_dir / 'launchers' / 'cli_entry.py')
    ]
    
    print("\\n=== Executando PyInstaller CLI ===")
    print(f"Comando: {' '.join(cmd_cli)}")
    
    try:
        result = subprocess.run(cmd_cli, cwd=base_dir, check=True, capture_output=True, text=True)
        print("✅ Build CLI concluído com sucesso!")
        
        # Testar executável
        exe_path = dist_dir / 'SSA_CLI_v3.10_SIMPLES' / 'SSA_CLI_v3.10_SIMPLES'
        if exe_path.exists():
            print(f"✅ Executável gerado: {exe_path}")
            
            # Teste básico
            test_cmd = [str(exe_path), '--help']
            test_result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=10)
            
            if test_result.returncode == 0:
                print("✅ Executável testado e FUNCIONANDO!")
                print(f"Tamanho: {exe_path.parent.stat().st_size / (1024*1024):.1f}M")
            else:
                print(f"❌ Teste falhou: {test_result.stderr}")
        else:
            print(f"❌ Executável não encontrado em: {exe_path}")
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro no build: {e}")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        return 1
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        return 1
    
    print("\\n🎯 BUILD SIMPLES COMPLETADO!")
    print("🧹 dist_simple será limpo automaticamente ao sair")
    return 0

if __name__ == '__main__':
    sys.exit(main())
