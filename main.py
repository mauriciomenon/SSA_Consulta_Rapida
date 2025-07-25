# main.py 20250725 100000 (v2.0 - Refatorado com argparse, logging, função main)
"""
Ponto de entrada da aplicação de Consulta Rápida de SSAs.

Orquestra a preparação do ambiente, verificação de arquivos, importação de dados
e inicialização da interface de linha de comando.
"""

import os
import sys
import argparse
import logging
from datetime import datetime

# Configuração básica de logging
# Em produção, poderia ser configurado para salvar em arquivo também
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Adiciona o diretório raiz do projeto ao sys.path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from utils import setup_project_structure
from core.app_logic import run_importer_logic
from interface.cli import start_cli_loop
from core.config_manager import ensure_default_settings

APP_VERSION = "4.0.0"

def main(cli_args=None):
    """
    Função principal da aplicação.

    Args:
        cli_args (list, optional): Argumentos da linha de comando para testes.
                                   Se None, sys.argv é usado.
    """
    parser = argparse.ArgumentParser(
        description=f"Consulta Rápida de SSAs v{APP_VERSION}",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        '--force-rescan',
        action='store_true',
        help='Força a reimportação de todos os arquivos Excel, ignorando o cache.'
    )
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        default='INFO',
        help='Define o nível de detalhe dos logs (padrão: INFO)'
    )
    # Permite que argparse use `cli_args` para testes
    args = parser.parse_args(cli_args) if cli_args is not None else parser.parse_args()
    
    # Atualiza o nível de log com base no argumento
    logger.setLevel(getattr(logging, args.log_level))

    logger.info("=" * 50)
    logger.info(f" Iniciando Consulta Rapida de SSAs {APP_VERSION} ")
    logger.info("=" * 50)

    try:
        # --- 1. Preparação do Ambiente ---
        logger.debug("Verificando/criando estrutura de pastas...")
        setup_project_structure.setup_dirs()
        logger.info("Estrutura de pastas verificada.")

        # --- 2. Configuração ---
        logger.debug("Garantindo configurações padrão...")
        ensure_default_settings()
        logger.debug("Configurações padrão verificadas.")

        # --- 3. Importação de Dados ---
        # Determina se a reimportação é forçada
        force_import = args.force_rescan
        logger.info(f"Iniciando processo de importação (force_rescan={force_import})...")
        db_updated = run_importer_logic(force_import=force_import)
        if db_updated:
            logger.info("Banco de dados atualizado com sucesso.")
        else:
            logger.info("Nenhum novo ou modificado relatório encontrado.")

        # --- 4. Início da CLI ---
        db_path = os.path.join(project_root, 'data', 'ssas.db')
        table_name = 'ssas'
        logger.info("Iniciando interface de linha de comando...")
        start_cli_loop(db_path, table_name)

    except KeyboardInterrupt:
        logger.info("\nOperação interrompida pelo usuário. Saindo...")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Erro crítico na inicialização: {e}", exc_info=True)
        sys.exit(1)

    logger.info("Aplicação encerrada normalmente.")

if __name__ == "__main__":
    # Permite que o script seja executado diretamente
    main()
