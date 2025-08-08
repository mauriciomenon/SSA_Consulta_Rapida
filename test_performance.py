#!/usr/bin/env python3
"""
Teste rápido de performance dos filtros
"""

import subprocess
import time
import sys

def test_filter_performance():
    print("=== TESTE DE PERFORMANCE DOS FILTROS ===")
    
    # Comandos para testar
    commands = [
        "svp",       # Filtro que deve ser rápido agora
        "1",         # Opção para mostrar primeiros 50
        "-q"         # Sair
    ]
    
    try:
        start_time = time.time()
        
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
        stdout, stderr = process.communicate(input=input_data, timeout=30)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        print(f"Tempo total de execução: {total_time:.2f} segundos")
        print("\n=== ÚLTIMA PARTE DA SAÍDA ===")
        lines = stdout.split('\n')
        for line in lines[-20:]:  # Últimas 20 linhas
            if line.strip():
                print(line)
                
        # Analisa se encontrou registros
        if "registros em" in stdout:
            import re
            matches = re.findall(r'(\d+) registros em ([\d.]+) segundos', stdout)
            if matches:
                records, filter_time = matches[0]
                print(f"\n✅ Filtro processou {records} registros em {filter_time}s")
                return float(filter_time) < 2.0  # Deve ser menos que 2 segundos
        
        return False
        
    except subprocess.TimeoutExpired:
        print("❌ TIMEOUT: Processo demorou mais de 30 segundos")
        process.kill()
        return False
    except Exception as e:
        print(f"❌ ERRO: {e}")
        return False

if __name__ == "__main__":
    success = test_filter_performance()
    print(f"\n{'✅ Performance OK!' if success else '❌ Performance ruim!'}")
    sys.exit(0 if success else 1)
