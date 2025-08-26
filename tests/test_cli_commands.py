#!/bin/env python3
# Script de teste para CLI enhanced
import sys
import os

# Adiciona o diretório do projeto ao path
sys.path.insert(0, r'c:\Users\menon\git\SSA_Consulta_Rapida')

# Importa e testa o enhancement manager
from interface.cli_enhancement_manager import enhancement_manager

def test_cli_commands():
    print("=== TESTE DOS COMANDOS CLI ===")
    print()
    
    # Testa status
    print("1. Testando comando status-cli:")
    print(enhancement_manager.get_status_report())
    print()
    
    # Testa toggle debug
    print("2. Testando toggle-debug:")
    debug_state = enhancement_manager.toggle_debug()
    print(f"Debug {'ATIVADO' if debug_state else 'DESATIVADO'}")
    print()
    
    # Testa habilitação/desabilitação do enhanced printer
    print("3. Testando enhanced-off:")
    enhancement_manager.disable_enhanced_printer()
    print("❌ Enhanced Table Printer DESATIVADO")
    print()
    
    print("4. Testando enhanced-on:")
    enhancement_manager.enable_enhanced_printer()
    print("✅ Enhanced Table Printer ATIVADO")
    print()
    
    print("5. Status final:")
    print(enhancement_manager.get_status_report())

if __name__ == "__main__":
    test_cli_commands()
