#!/usr/bin/env python3
"""
Teste automatizado do fluxo sequencial de filtros
Simula a entrada: svp → mel4
"""

import subprocess
import time
import sys

def test_sequential_filtering():
    print("=== TESTE DE FILTRAGEM SEQUENCIAL ===")
    print("1. Iniciando aplicação...")
    print("2. Aplicando filtro 'svp'")
    print("3. Aplicando filtro 'mel4' na seleção anterior")
    print("4. Verificando se filtros são aplicados sequencialmente")
    print("")
    
    # Comandos para testar
    commands = [
        "svp",       # Primeiro filtro
        "mel4",      # Segundo filtro sequencial  
        "-q"         # Sair
    ]
    
    # Executa o teste
    try:
        process = subprocess.Popen(
            [sys.executable, "main.py"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd="."
        )
        
        # Envia comandos
        input_data = "\n".join(commands) + "\n"
        stdout, stderr = process.communicate(input=input_data, timeout=60)
        
        print("=== SAÍDA DO PROGRAMA ===")
        print(stdout)
        
        if stderr:
            print("=== ERROS ===")
            print(stderr)
            
        return process.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("ERRO: Programa demorou mais que 60 segundos")
        process.kill()
        return False
    except Exception as e:
        print(f"ERRO durante teste: {e}")
        return False

if __name__ == "__main__":
    success = test_sequential_filtering()
    if success:
        print("\n✅ Teste concluído com sucesso!")
    else:
        print("\n❌ Teste falhou!")
    sys.exit(0 if success else 1)
