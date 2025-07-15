# main.py
import os
import sys
from interface.cli import start_cli_loop

# --- Configurações ---
DB_PATH = os.path.join('data', 'ssas.db')
TABLE_NAME = 'ssa'

def main():
    """Função principal que inicia a aplicação."""
    # Aqui podemos adicionar a lógica de verificar se o DB existe,
    # se o usuário quer re-importar, etc. Por enquanto, vamos direto para a CLI.
    
    # Inicia a interface de consulta
    start_cli_loop(db_path=DB_PATH, table_name=TABLE_NAME)

if __name__ == "__main__":
    main()
