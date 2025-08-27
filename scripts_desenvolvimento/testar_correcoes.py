#!/usr/bin/env python3
"""
Script de teste para verificar as correções implementadas.
"""

import sys
import os
import subprocess

def test_main_help():
    """Testa se o main.py --help funciona."""
    print("🧪 Testando main.py --help...")
    try:
        result = subprocess.run([sys.executable, "main.py", "--help"], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ main.py --help funciona!")
            print(f"Argumentos disponíveis encontrados: {len(result.stdout.split('--'))}")
            return True
        else:
            print(f"❌ Erro ao executar main.py --help: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Exceção ao testar main.py: {e}")
        return False

def test_gerenciar_banco():
    """Testa o script de gerenciamento do banco."""
    print("🧪 Testando gerenciar_banco.py...")
    try:
        result = subprocess.run([sys.executable, "scripts_manutencao/gerenciar_banco.py", "status"], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ gerenciar_banco.py funciona!")
            return True
        else:
            print(f"❌ Erro ao executar gerenciar_banco.py: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Exceção ao testar gerenciar_banco.py: {e}")
        return False

def test_requirements():
    """Verifica se o requirements.txt está bem formado."""
    print("🧪 Testando requirements.txt...")
    try:
        with open("requirements.txt", "r") as f:
            content = f.read()
        
        # Conta linhas de dependências (ignora comentários e linhas vazias)
        deps = [line.strip() for line in content.split('\n') 
                if line.strip() and not line.strip().startswith('#')]
        
        print(f"✅ requirements.txt contém {len(deps)} dependências!")
        print("📦 Principais dependências encontradas:")
        for dep in deps[:5]:  # Mostra as primeiras 5
            print(f"  - {dep}")
        if len(deps) > 5:
            print(f"  ... e mais {len(deps)-5} dependências")
        return True
    except Exception as e:
        print(f"❌ Erro ao ler requirements.txt: {e}")
        return False

def main():
    """Executa todos os testes."""
    print("🔍 Executando testes de verificação...")
    print("=" * 50)
    
    tests = [
        test_requirements,
        test_gerenciar_banco,
        test_main_help,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Erro no teste {test.__name__}: {e}")
            results.append(False)
        print("-" * 30)
    
    # Resumo
    passed = sum(results)
    total = len(results)
    
    print("📊 RESUMO DOS TESTES:")
    print(f"✅ Passou: {passed}/{total}")
    print(f"❌ Falhou: {total-passed}/{total}")
    
    if passed == total:
        print("🎉 Todos os testes passaram!")
        return 0
    else:
        print("⚠️  Alguns testes falharam.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
