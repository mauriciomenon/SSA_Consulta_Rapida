#!/usr/bin/env python3
# teste_integracao_otimizada.py
"""
Teste rápido da integração da importação otimizada com o main.py
"""

import subprocess
import sys
import time

def run_command(cmd, description):
    """Executa um comando e mostra o resultado."""
    print(f"\n🔍 {description}")
    print(f"Comando: {cmd}")
    print("-" * 40)
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✅ Sucesso!")
            if result.stdout:
                print("Saída:")
                print(result.stdout[:500] + ("..." if len(result.stdout) > 500 else ""))
        else:
            print("❌ Erro!")
            if result.stderr:
                print("Erro:")
                print(result.stderr[:300])
                
    except subprocess.TimeoutExpired:
        print("⏱️ Timeout (comando demorou mais que 10s)")
    except Exception as e:
        print(f"❌ Exceção: {e}")

def main():
    print("🧪 TESTE DE INTEGRAÇÃO - IMPORTAÇÃO OTIMIZADA")
    print("=" * 60)
    
    # Teste 1: Help do main.py
    run_command("python main.py --help", "Testando help do main.py")
    
    # Teste 2: Verificar se arquivos estão nas pastas corretas
    print(f"\n📁 VERIFICAÇÃO DE ORGANIZAÇÃO DOS ARQUIVOS")
    print("-" * 45)
    
    import os
    
    arquivos_esperados = {
        "scripts_manutencao/parar_importacao_e_diagnostico.py": "Diagnóstico",
        "scripts_desenvolvimento/monitor_importacao.py": "Monitor",
        "scripts_desenvolvimento/otimizacao_importacao_rapida.py": "Otimização standalone",
        "armazenamento/database_optimized.py": "Módulo otimizado",
        "RELATORIO_OTIMIZACAO_IMPORTACAO.md": "Relatório (raiz)"
    }
    
    for arquivo, descricao in arquivos_esperados.items():
        if os.path.exists(arquivo):
            print(f"✅ {descricao}: {arquivo}")
        else:
            print(f"❌ {descricao}: {arquivo} - NÃO ENCONTRADO")
    
    # Teste 3: Estatísticas rápidas
    run_command("python scripts_desenvolvimento/monitor_importacao.py stats", 
                "Testando estatísticas do banco")
    
    # Teste 4: Teste simples de importação (sem force-rescan para ser rápido)
    run_command("python main.py --log-level INFO", 
                "Testando main.py normal (sem reimportação)")
    
    print(f"\n🎯 RESUMO DOS TESTES")
    print("=" * 25)
    print("✅ Se todos os testes passaram, a integração está funcionando!")
    print("✅ Use: python main.py --optimized --force-rescan para importação rápida")
    print("✅ Scripts organizados nas pastas corretas")
    print("✅ Documentação mantida na raiz")

if __name__ == "__main__":
    main()
