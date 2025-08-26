#!/bin/env python3
# Script simplificado para testar comandos CLI
import sys
import os

# Adiciona o diretório do projeto ao path
sys.path.insert(0, r'c:\Users\menon\git\SSA_Consulta_Rapida')

# Importa as funções necessárias
from interface.cli_enhancement_manager import enhancement_manager

def simulate_cli_command(command):
    """Simula a execução de um comando CLI"""
    print(f">>> {command}")
    
    if command.lower() in ['status-cli', 'cli-status']:
        print(enhancement_manager.get_status_report())
    elif command.lower() in ['toggle-debug', 'debug']:
        new_state = enhancement_manager.toggle_debug()
        state_str = "ATIVADO" if new_state else "DESATIVADO"
        print(f"🔧 Debug CLI {state_str}")
    elif command.lower() in ['enhanced-on', 'enable-enhanced']:
        enhancement_manager.enable_enhanced_printer()
        print("✅ Enhanced Table Printer ATIVADO")
    elif command.lower() in ['enhanced-off', 'disable-enhanced']:
        enhancement_manager.disable_enhanced_printer()
        print("❌ Enhanced Table Printer DESATIVADO")
    else:
        print(f"Comando '{command}' não reconhecido")
    
    print()

def main():
    print("=== SIMULAÇÃO DOS COMANDOS CLI MELHORADOS ===")
    print()
    
    # Lista de comandos para testar
    commands = [
        'status-cli',
        'toggle-debug', 
        'enhanced-off',
        'enhanced-on',
        'cli-status'
    ]
    
    for cmd in commands:
        simulate_cli_command(cmd)

if __name__ == "__main__":
    main()
