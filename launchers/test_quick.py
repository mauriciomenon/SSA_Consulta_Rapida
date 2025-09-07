#!/usr/bin/env python3
"""
Teste rápido dos executáveis existentes
"""

import os
import subprocess
import time

def log(msg, level="INFO"):
    print(f"[{time.strftime('%H:%M:%S')}] {level}: {msg}")

def test_existing_executables():
    """Testa executáveis já construídos"""
    log("=== TESTE EXECUTÁVEIS EXISTENTES ===")
    
    platform = "macos_arm64"
    base_path = f"launchers/dist/{platform}"
    
    # Verificar CLI
    cli_path = f"{base_path}/SSA_CLI_v3.10_{platform}/SSA_CLI_v3.10_{platform}"
    log(f"Verificando CLI: {cli_path}")
    
    if os.path.exists(cli_path):
        log("✅ CLI encontrado")
        # Testar execução
        try:
            result = subprocess.run([cli_path, "--help"], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                log("✅ CLI executa corretamente")
            else:
                log(f"❌ CLI erro: {result.stderr}")
        except Exception as e:
            log(f"❌ CLI erro execução: {e}")
    else:
        log("❌ CLI não encontrado")
    
    # Verificar GUI
    gui_path = f"{base_path}/SSA_GUI_v3.10_{platform}.app/Contents/MacOS/SSA_GUI_v3.10_{platform}"
    log(f"Verificando GUI: {gui_path}")
    
    if os.path.exists(gui_path):
        log("✅ GUI encontrada")
        # Testar se não dá erro de import
        try:
            result = subprocess.run([gui_path], 
                                  capture_output=True, text=True, timeout=2)
            # Se não deu erro de módulo, está funcionando
            if "No module named" not in result.stderr:
                log("✅ GUI imports OK")
            else:
                log(f"❌ GUI erro módulo: {result.stderr}")
        except subprocess.TimeoutExpired:
            log("✅ GUI iniciou (timeout normal para GUI)")
        except Exception as e:
            log(f"❌ GUI erro: {e}")
    else:
        log("❌ GUI não encontrada")

def test_imports():
    """Testa imports críticos"""
    log("=== TESTE IMPORTS ===")
    
    try:
        from gui.gui_ssa import SSAMainWindow
        log("✅ GUI principal importa OK")
    except Exception as e:
        log(f"❌ GUI principal erro: {e}")
        
    try:
        from gui.gui_ssa_poc import SSAMainWindow as POCWindow
        log("✅ GUI POC importa OK")
    except Exception as e:
        log(f"❌ GUI POC erro: {e}")

def list_dist_contents():
    """Lista conteúdo da pasta dist"""
    log("=== CONTEÚDO DIST ===")
    
    dist_path = "launchers/dist/macos_arm64"
    if os.path.exists(dist_path):
        for item in os.listdir(dist_path):
            log(f"📁 {item}")
    else:
        log("❌ Pasta dist não existe")

def main():
    log("TESTE RÁPIDO v3.10")
    list_dist_contents()
    test_imports()
    test_existing_executables()
    log("=== FIM DOS TESTES ===")

if __name__ == "__main__":
    main()
