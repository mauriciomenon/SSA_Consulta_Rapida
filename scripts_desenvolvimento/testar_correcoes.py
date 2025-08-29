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
        ok = (result.returncode == 0)
        print("✅ main.py --help funciona!" if ok else f"❌ Erro ao executar main.py --help: {result.stderr}")
        if ok:
            print(f"Argumentos disponíveis encontrados: {len(result.stdout.split('--'))}")
        return ok
    except Exception as e:
        print(f"❌ Exceção ao testar main.py: {e}")
        return False

def test_gerenciar_banco():
    """Testa o script de gerenciamento do banco."""
    print("🧪 Testando gerenciar_banco.py...")
    try:
        result = subprocess.run([sys.executable, "scripts_manutencao/gerenciar_banco.py", "status"], 
                              capture_output=True, text=True, timeout=10)
        ok = (result.returncode == 0)
        print("✅ gerenciar_banco.py funciona!" if ok else f"❌ Erro ao executar gerenciar_banco.py: {result.stderr}")
        return ok
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
        for dep in deps[:5]:
            print(f"  - {dep}")
        extra = len(deps) - 5
        if extra > 0:
            print(f"  ... e mais {extra} dependências")
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
    
    def _safe_run(t):
        try:
            return t()
        except Exception as e:
            print(f"❌ Erro no teste {t.__name__}: {e}")
            return False
    results = [_safe_run(t) for t in tests]
    print("-" * 30)
    
    # Resumo
    passed = sum(results)
    total = len(results)
    
    print("📊 RESUMO DOS TESTES:")
    print(f"✅ Passou: {passed}/{total}")
    print(f"❌ Falhou: {total-passed}/{total}")
    
    all_ok = (passed == total)
    print("🎉 Todos os testes passaram!" if all_ok else "⚠️  Alguns testes falharam.")
    return 0 if all_ok else 1

if __name__ == "__main__":
    sys.exit(main())
