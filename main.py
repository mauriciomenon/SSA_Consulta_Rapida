# main.py
import sys
import os
import logging
import argparse

# Adiciona o diretório raiz ao sys.path para garantir que todos os módulos sejam encontrados
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Importa os componentes principais do sistema
from utils.setup_project_structure import setup_dirs
from core.app_logic import run_importer_logic
from armazenamento.database import query_db, initialize_database
from core.config_manager import load_settings

def main():
    """Função principal que orquestra a aplicação."""
    # Configuração de Logging (pode ser movida para um utils/logger.py)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Argumentos da linha de comando
    parser = argparse.ArgumentParser(description="Consulta Rápida de SSAs.")
    parser.add_argument("--gui", action="store_true", help="Inicia a interface gráfica (GUI).")
    parser.add_argument("--rescan", action="store_true", help="Força a reimportação de todos os arquivos.")
    args = parser.parse_args()

    print("=" * 50)
    print("  Iniciando Consulta Rápida de SSAs")
    print("=" * 50)

    # 1. Garante que a estrutura de pastas exista
    setup_dirs()

    # 2. Caminhos e Configurações
    db_path = os.path.join('data', 'ssas.db')
    schema_path = os.path.join('config', 'schema.sql')
    
    # 3. Inicializa o banco de dados se não existir
    if not os.path.exists(db_path):
        print("Banco de dados não encontrado. Inicializando...")
        try:
            # Nota: a função initialize_database no seu código atual tem uma lógica
            # de path hardcoded. Ela deve funcionar, mas o ideal seria torná-la
            # mais flexível. Por agora, vamos usá-la como está.
            initialize_database(db_path, schema_path)
        except FileNotFoundError as e:
             logging.error(f"ERRO CRÍTICO: {e}. Verifique se 'config/schema.sql' existe.")
             sys.exit(1)
        except Exception as e:
            logging.error(f"Falha ao inicializar o banco de dados: {e}")
            sys.exit(1)

    # 4. Roda o importador de dados
    print("Verificando por novos relatórios para importar...")
    try:
        run_importer_logic(force_import=args.rescan)
    except Exception as e:
        logging.error(f"Ocorreu um erro durante a importação: {e}")
        # Decide se continua ou não. Por ora, vamos continuar com os dados existentes.

    # 5. Carrega os dados do DB para a memória
    print("Carregando dados do banco...")
    try:
        all_data_df = query_db(db_path, 'ssas')
        settings = load_settings()
        display_map = settings.get('display_mappings', {})
    except Exception as e:
        logging.error(f"Não foi possível carregar dados ou configurações: {e}")
        sys.exit(1)

    # 6. Inicia a interface escolhida
    if args.gui:
        print("Iniciando interface gráfica...")
        # Importações da GUI aqui para não carregar PyQt6 desnecessariamente no CLI
        from PyQt6.QtWidgets import QApplication
        from gui.app_gui import AppGuiWindow
        
        app = QApplication(sys.argv)
        window = AppGuiWindow(all_data_df, display_map)
        window.show()
        sys.exit(app.exec())
    else:
        print("Iniciando interface de linha de comando...")
        from interface.cli import start_cli_loop
        output_dir = os.path.join(project_root, 'docs_saida')
        start_cli_loop(all_data_df, display_map, output_dir)

if __name__ == "__main__":
    main()