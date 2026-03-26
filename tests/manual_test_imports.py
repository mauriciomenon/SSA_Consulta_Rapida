import os
import sys

print("Import basico OK")

# Adiciona o diretório raiz do projeto ao sys.path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
print("Path setup OK")

try:
    print("utils.setup_project_structure OK")
except Exception as e:
    print(f"Erro ao importar setup_project_structure: {e}")

try:
    print("core.app_logic.run_importer_logic OK")
except Exception as e:
    print(f"Erro ao importar run_importer_logic: {e}")

try:
    print("interface.cli.start_cli_loop OK")
except Exception as e:
    print(f"Erro ao importar start_cli_loop: {e}")

print("Teste de importações concluído")
