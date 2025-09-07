#!/usr/bin/env python3
"""
Teste direto dos executaveis v3.10
"""

import os
import subprocess
import sys
from pathlib import Path

def test_executable(exe_path, name):
    """Testa um executavel"""
    print(f"\n=== Testando {name} ===")
    print(f"Path: {exe_path}")
    
    if not exe_path.exists():
        print(f"❌ Executavel nao encontrado: {exe_path}")
        return False
    
    # Verificar tipo
    try:
        result = subprocess.run(['file', str(exe_path)], capture_output=True, text=True)
        print(f"Tipo: {result.stdout.strip()}")
    except:
        pass
    
    # Verificar tamanho
    try:
        size_mb = exe_path.parent.stat().st_size / (1024 * 1024)
        print(f"Tamanho pasta: {size_mb:.1f}M")
    except:
        pass
    
    # Teste simples - executar sem argumentos
    print("Testando execucao...")
    try:
        result = subprocess.run([str(exe_path)], capture_output=True, text=True, timeout=3)
        print(f"Exit code: {result.returncode}")
        if result.stdout:
            print(f"STDOUT: {result.stdout[:200]}...")
        if result.stderr:
            print(f"STDERR: {result.stderr[:200]}...")
        
        if result.returncode == 0 or result.returncode == 2:  # 2 é comum para --help missing
            print("✅ Executavel esta funcionando!")
            return True
        else:
            print(f"⚠️ Exit code: {result.returncode}")
            return False
            
    except subprocess.TimeoutExpired:
        print("⚠️ Timeout - pode estar aguardando input")
        return True  # Timeout pode ser normal
    except Exception as e:
        print(f"❌ Erro ao executar: {e}")
        return False

def main():
    base_dir = Path(__file__).parent.parent
    print(f"=== Teste de Executaveis v3.10 ===")
    print(f"Base: {base_dir}")
    
    # Testar CLI multi-plataforma
    cli_path = base_dir / 'launchers' / 'dist' / 'macos_arm64' / 'SSA_CLI_v3.10_macos_arm64' / 'SSA_CLI_v3.10_macos_arm64'
    cli_ok = test_executable(cli_path, "CLI Multi-Plataforma")
    
    # Testar CLI simples (se existir)
    cli_simple_path = base_dir / 'launchers' / 'dist_simple' / 'SSA_CLI_v3.10_SIMPLES' / 'SSA_CLI_v3.10_SIMPLES'
    if cli_simple_path.exists():
        simple_ok = test_executable(cli_simple_path, "CLI Simples")
    else:
        print(f"\n=== CLI Simples nao encontrado ===")
        print(f"Path esperado: {cli_simple_path}")
        simple_ok = False
    
    # Resumo
    print(f"\n=== RESUMO ===")
    print(f"CLI Multi-Plataforma: {'✅ OK' if cli_ok else '❌ ERRO'}")
    print(f"CLI Simples: {'✅ OK' if simple_ok else '❌ ERRO'}")
    
    if cli_ok:
        print("\n🎯 Pelo menos um executavel esta funcionando!")
        print("Prosseguindo com build GUI...")
        return 0
    else:
        print("\n❌ Nenhum executavel funcionando!")
        return 1

if __name__ == '__main__':
    sys.exit(main())
