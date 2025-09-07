#!/usr/bin/env python3
"""
Script de teste completo para builds v3.10
Testa CLI, GUI e detecta problemas
"""

import os
import sys
import subprocess
import json
import time
from pathlib import Path

def log(msg, level="INFO"):
    """Log formatado"""
    timestamp = time.strftime("%H:%M:%S")
    print(f"[{timestamp}] {level}: {msg}")

def run_command(cmd, timeout=30):
    """Executa comando com timeout"""
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=timeout
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Timeout"

def detect_platform():
    """Detecta plataforma atual"""
    import platform
    system = platform.system().lower()
    arch = platform.machine().lower()
    
    if system == "darwin":
        if "arm" in arch or "aarch64" in arch:
            return "macos_arm64"
        else:
            return "macos_x64"
    elif system == "windows":
        return "windows_amd64"
    elif system == "linux":
        return "debian_amd64"
    else:
        return "unknown"

def test_build_system():
    """Testa sistema de build"""
    log("=== TESTE DO SISTEMA DE BUILD ===")
    
    platform = detect_platform()
    log(f"Plataforma detectada: {platform}")
    
    # Verificar arquivos essenciais
    essential_files = [
        "launchers/build_multiplatform.py",
        "launchers/cli_entry.py", 
        "launchers/gui_entry.py",
        f"launchers/platforms/{platform}/build_config.json",
        f"launchers/platforms/{platform}/requirements.txt"
    ]
    
    missing_files = []
    for file in essential_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        log(f"ERRO: Arquivos essenciais faltando: {missing_files}", "ERROR")
        return False
    
    log("✅ Todos os arquivos essenciais presentes")
    return True

def test_cli_build():
    """Testa build do CLI"""
    log("=== TESTE BUILD CLI ===")
    
    # Build CLI
    log("Construindo CLI...")
    success, stdout, stderr = run_command(
        "python launchers/build_multiplatform.py --apps cli", 
        timeout=300
    )
    
    if not success:
        log(f"ERRO no build CLI: {stderr}", "ERROR")
        return False
    
    log("✅ CLI construído com sucesso")
    
    # Verificar executável
    platform = detect_platform()
    cli_path = f"launchers/dist/{platform}/SSA_CLI_v3.10_{platform}/SSA_CLI_v3.10_{platform}"
    
    if not os.path.exists(cli_path):
        log(f"ERRO: Executável CLI não encontrado em {cli_path}", "ERROR")
        return False
    
    log("✅ Executável CLI encontrado")
    
    # Testar execução
    log("Testando execução do CLI...")
    success, stdout, stderr = run_command(f'"{cli_path}" --help', timeout=10)
    
    if not success:
        log(f"ERRO na execução CLI: {stderr}", "ERROR")
        return False
    
    log("✅ CLI executa corretamente")
    return True

def test_gui_build():
    """Testa build da GUI"""
    log("=== TESTE BUILD GUI ===")
    
    # Build GUI
    log("Construindo GUI...")
    success, stdout, stderr = run_command(
        "python launchers/build_multiplatform.py --apps gui",
        timeout=300
    )
    
    if not success:
        log(f"ERRO no build GUI: {stderr}", "ERROR")
        return False
    
    log("✅ GUI construída com sucesso")
    
    # Verificar executável
    platform = detect_platform()
    
    if platform == "macos_arm64":
        gui_path = f"launchers/dist/{platform}/SSA_GUI_v3.10_{platform}.app/Contents/MacOS/SSA_GUI_v3.10_{platform}"
    else:
        gui_path = f"launchers/dist/{platform}/SSA_GUI_v3.10_{platform}/SSA_GUI_v3.10_{platform}"
    
    if not os.path.exists(gui_path):
        log(f"ERRO: Executável GUI não encontrado em {gui_path}", "ERROR")
        return False
    
    log("✅ Executável GUI encontrado")
    
    # Testar importação (sem abrir janela)
    log("Testando imports da GUI...")
    test_script = f'''
import sys
sys.path.insert(0, "/Users/menon/git/SSA_Consulta_Rapida")
try:
    from gui.gui_ssa import SSAMainWindow
    print("✅ Import GUI principal OK")
except Exception as e:
    print(f"❌ Erro import GUI: {{e}}")
    sys.exit(1)
'''
    
    success, stdout, stderr = run_command(f'python -c "{test_script}"')
    if not success:
        log(f"ERRO: Imports da GUI falharam: {stderr}", "ERROR")
        return False
    
    log("✅ Imports da GUI funcionam")
    return True

def test_module_dependencies():
    """Testa dependências de módulos"""
    log("=== TESTE DEPENDÊNCIAS MÓDULOS ===")
    
    critical_modules = [
        "PyQt6", "pandas", "openpyxl", "sqlite3", 
        "secrets", "hashlib", "uuid", "datetime"
    ]
    
    failed_modules = []
    for module in critical_modules:
        try:
            __import__(module)
            log(f"✅ {module}")
        except ImportError as e:
            log(f"❌ {module}: {e}", "ERROR")
            failed_modules.append(module)
    
    if failed_modules:
        log(f"ERRO: Módulos faltando: {failed_modules}", "ERROR")
        return False
    
    log("✅ Todos os módulos críticos disponíveis")
    return True

def generate_test_report():
    """Gera relatório de teste"""
    log("=== GERANDO RELATÓRIO ===")
    
    platform = detect_platform()
    
    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "platform": platform,
        "tests": {},
        "build_info": {}
    }
    
    # Teste sistema de build
    report["tests"]["build_system"] = test_build_system()
    
    # Teste módulos
    report["tests"]["modules"] = test_module_dependencies()
    
    # Teste CLI
    report["tests"]["cli_build"] = test_cli_build()
    
    # Teste GUI
    report["tests"]["gui_build"] = test_gui_build()
    
    # Informações de build
    if os.path.exists(f"launchers/dist/{platform}/build_manifest.json"):
        with open(f"launchers/dist/{platform}/build_manifest.json", 'r') as f:
            report["build_info"] = json.load(f)
    
    # Salvar relatório
    os.makedirs("launchers/test_reports", exist_ok=True)
    report_file = f"launchers/test_reports/test_report_{platform}_{int(time.time())}.json"
    
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    log(f"Relatório salvo: {report_file}")
    
    # Resumo
    total_tests = len(report["tests"])
    passed_tests = sum(1 for result in report["tests"].values() if result)
    
    log("=== RESUMO DOS TESTES ===")
    log(f"Total: {total_tests}")
    log(f"Passou: {passed_tests}")
    log(f"Falhou: {total_tests - passed_tests}")
    
    if passed_tests == total_tests:
        log("🎉 TODOS OS TESTES PASSARAM!", "SUCCESS")
        return True
    else:
        log("❌ ALGUNS TESTES FALHARAM!", "ERROR")
        return False

def main():
    """Executa todos os testes"""
    log("INICIANDO TESTES COMPLETOS v3.10")
    
    if not os.path.exists("launchers/build_multiplatform.py"):
        log("ERRO: Execute no diretório raiz do projeto", "ERROR")
        sys.exit(1)
    
    success = generate_test_report()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
