# main.py (v8.0 - Arquitetura Refatorada)
import os
import sys

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

from interface.cli import start_cli_loop
from core.app_logic import run_importer_logic

# --- Configurações ---
DOCS_ENTRADA = 'docs_entrada'
DOCS_SAIDA = 'docs_saida'
DATA_DIR = 'data'
CONFIG_DIR = 'config'
DB_PATH = os.path.join(DATA_DIR, 'ssas.db')
TABLE_NAME = 'ssa'

def ensure_project_structure():
    """Verifica e cria a estrutura de pastas do projeto."""
    required_dirs = [DOCS_ENTRADA, DOCS_SAIDA, DATA_DIR, CONFIG_DIR, 'core', 'utils', 'tests']
    for directory in required_dirs:
        if not os.path.exists(directory):
            print(f"AVISO: Pasta '{directory}' não encontrada. Criando...")
            os.makedirs(directory)
    
    for pkg_dir in ['core', 'utils', 'exportacao', 'armazenamento', 'config', 'extracao', 'interface', 'tests']:
        init_path = os.path.join(pkg_dir, '__init__.py')
        if not os.path.exists(init_path):
            try:
                open(init_path, 'a').close()
            except OSError:
                pass
    print("Estrutura de pastas verificada.")

def main():
    """Função principal que orquestra a aplicação."""
    print("--- Iniciando SSA Consulta Rápida (v13.0 - Core Refatorado) ---")
    
    force_rescan = '--rescan' in sys.argv
    
    ensure_project_structure()
    
    # A lógica de importação agora vive no core
    run_importer_logic(
        docs_dir=DOCS_ENTRADA,
        data_dir=DATA_DIR,
        db_path=DB_PATH,
        table_name=TABLE_NAME,
        force_rescan=force_rescan
    )
    
    # Inicia a interface do usuário
    start_cli_loop(
        db_path=DB_PATH,
        table_name=TABLE_NAME,
        output_dir=DOCS_SAIDA
    )

if __name__ == "__main__":
    main()
