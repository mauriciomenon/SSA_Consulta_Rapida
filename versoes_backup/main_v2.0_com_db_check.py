# main.py 20250725 100000 (v2.0 - Refatorado com argparse, logging, função main)
"""
Ponto de entrada da aplicação de Consulta Rápida de SSAs.

Orquestra a preparação do ambiente, verificação de arquivos, importação de dados
e inicialização da interface de linha de comando.
"""

import os
import sys
import argparse
import socket
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
import sqlite3
import shutil
import glob

logger = logging.getLogger("ssa")
logger.setLevel(logging.DEBUG)
_logging_configured = False

def _configure_logging(project_root: str, level_console: int = logging.WARNING, level_file: int = logging.INFO):
    global _logging_configured
    if _logging_configured:
        return
    logs_dir = os.path.join(project_root, 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    # File handler (INFO+), rotating 1MB, keep 1 backup (total 2 files)
    file_handler = RotatingFileHandler(
        filename=os.path.join(logs_dir, 'ssa.log'),
        maxBytes=1_000_000,
        backupCount=1,
        encoding='utf-8'
    )
    file_handler.setLevel(level_file)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s'))
    # Console handler (WARNING+ by default) on root only to keep CLI clean
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level_console)
    console_handler.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
    # Attach file handler to package logger
    logger.addHandler(file_handler)
    # Attach console handler only to root, avoid duplicates and keep console quiet
    root_logger = logging.getLogger()
    # Prevent adding multiple equal handlers if called twice in interactive sessions
    existing_console = any(isinstance(h, logging.StreamHandler) for h in root_logger.handlers)
    if not existing_console:
        root_logger.addHandler(console_handler)
    # Root level conservative
    if root_logger.level == logging.NOTSET:
        root_logger.setLevel(logging.WARNING)
    # Ensure our logger propagates to root for console warnings/errors
    logger.propagate = True
    _logging_configured = True

def check_and_restore_database(db_path):
    """
    Verifica se o banco de dados está vazio ou corrompido e restaura um backup se necessário.
    
    Args:
        db_path (str): Caminho para o arquivo de banco de dados
        
    Returns:
        bool: True se o banco está válido ou foi restaurado com sucesso
    """
    try:
        # Verifica se o arquivo existe e tem tamanho adequado
        if not os.path.exists(db_path):
            logger.warning(f"Banco de dados não encontrado: {db_path}")
            return _restore_database_from_backup(db_path)
        
        # Verifica tamanho do arquivo (considera vazio se < 32KB)
        file_size = os.path.getsize(db_path)
        if file_size < 32768:  # 32KB
            logger.warning(f"Banco de dados muito pequeno ({file_size} bytes), possivelmente corrompido")
            return _restore_database_from_backup(db_path)
        
        # Verifica se consegue conectar e se tem a tabela ssas
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='ssas'")
                if cursor.fetchone()[0] == 0:
                    logger.warning("Tabela 'ssas' não encontrada no banco de dados")
                    return _restore_database_from_backup(db_path)
                
                # Verifica se a tabela tem dados
                cursor.execute("SELECT COUNT(*) FROM ssas")
                row_count = cursor.fetchone()[0]
                if row_count == 0:
                    logger.warning("Banco de dados está vazio (0 registros)")
                    return _restore_database_from_backup(db_path)
                
                logger.info(f"Banco de dados válido: {file_size} bytes, {row_count} registros")
                return True
                
        except sqlite3.Error as e:
            logger.error(f"Erro ao verificar banco de dados: {e}")
            return _restore_database_from_backup(db_path)
            
    except Exception as e:
        logger.error(f"Erro na verificação do banco: {e}")
        return False

def _restore_database_from_backup(db_path):
    """
    Restaura o banco de dados a partir do melhor backup disponível.
    
    Args:
        db_path (str): Caminho para o arquivo de banco de dados
        
    Returns:
        bool: True se a restauração foi bem-sucedida
    """
    try:
        project_root = os.path.dirname(os.path.dirname(db_path))
        backup_dir = os.path.join(project_root, 'data', 'historico_backups')
        
        if not os.path.exists(backup_dir):
            logger.error("Pasta de backups históricos não encontrada")
            return False
        
        # Lista todos os backups .db e ordena por tamanho (maiores primeiro)
        backup_files = glob.glob(os.path.join(backup_dir, '*.db'))
        if not backup_files:
            logger.error("Nenhum backup encontrado")
            return False
        
        # Ordena por tamanho decrescente para pegar o maior backup
        backup_files.sort(key=lambda x: os.path.getsize(x), reverse=True)
        
        for backup_file in backup_files:
            backup_size = os.path.getsize(backup_file)
            if backup_size < 32768:  # Ignora backups muito pequenos
                continue
                
            try:
                # Testa se o backup é válido
                with sqlite3.connect(backup_file) as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='ssas'")
                    if cursor.fetchone()[0] == 0:
                        continue
                    
                    cursor.execute("SELECT COUNT(*) FROM ssas")
                    row_count = cursor.fetchone()[0]
                    if row_count == 0:
                        continue
                
                # Backup é válido, restaura
                logger.info(f"Restaurando banco de {os.path.basename(backup_file)} ({backup_size} bytes, {row_count} registros)")
                
                # Faz backup do arquivo corrompido se existir
                if os.path.exists(db_path):
                    corrupted_backup = f"{db_path}.corrupted_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    shutil.move(db_path, corrupted_backup)
                    logger.info(f"Arquivo corrompido salvo como: {os.path.basename(corrupted_backup)}")
                
                # Copia o backup válido
                shutil.copy2(backup_file, db_path)
                logger.info("Banco de dados restaurado com sucesso")
                return True
                
            except sqlite3.Error:
                continue  # Tenta próximo backup
                
        logger.error("Nenhum backup válido encontrado")
        return False
        
    except Exception as e:
        logger.error(f"Erro ao restaurar backup: {e}")
        return False

# Adiciona o diretório raiz do projeto ao sys.path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from utils import setup_project_structure
from core.app_logic import run_importer_logic
from interface.cli import start_cli_loop
from core.config_manager import ensure_default_settings
from utils.version import get_app_version

APP_VERSION = get_app_version()

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
    # Suporta --rescan como alias histórico de --force-rescan
    parser.add_argument(
        '--force-rescan', '--rescan',
        dest='force_rescan',
        action='store_true',
        help='Força a reimportação de todos os arquivos Excel, ignorando o cache.'
    )
    parser.add_argument(
        '--gui',
        action='store_true',
        help='Inicia a interface gráfica (GUI) em vez da CLI.'
    )
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        default='INFO',
        help='Define o nível de detalhe dos logs (padrão: INFO)'
    )
    # Permite que argparse use `cli_args` para testes
    args = parser.parse_args(cli_args) if cli_args is not None else parser.parse_args()
    
    # Configura logging (arquivo + console) e nível
    _configure_logging(project_root)
    logger.setLevel(getattr(logging, args.log_level))

    # Banner amigável sem prefixos de log
    print(f"Pesquisa Rápida de SSAs {APP_VERSION}")

    try:
        # --- 1. Preparação do Ambiente ---
        logger.debug("Verificando/criando estrutura de pastas...")
        setup_project_structure.setup_dirs()
        logger.info("Estrutura de pastas verificada.")

        # --- 2. Configuração ---
        logger.debug("Garantindo configurações padrão...")
        ensure_default_settings()
        logger.debug("Configurações padrão verificadas.")

        # --- 3. Importação de Dados (APENAS se solicitado) ---
        # Determina se a reimportação é forçada
        force_import = args.force_rescan
        if force_import:
            logger.info(f"Iniciando processo de importação (force_rescan={force_import})...")
            db_updated = run_importer_logic(force_import=force_import)
            if db_updated:
                logger.info("Banco de dados atualizado com sucesso.")
            else:
                logger.info("Nenhum novo ou modificado relatório encontrado.")
        else:
            logger.debug("Pulando importação (use --force-rescan para reimportar)")

        # --- 4. Início da Interface ---
        db_path = os.path.join(project_root, 'data', 'ssas.db')
        table_name = 'ssas'
        
        # Verifica integridade do banco e restaura backup se necessário
        if not check_and_restore_database(db_path):
            logger.error("Falha ao verificar/restaurar banco de dados. Encerrando aplicação.")
            sys.exit(1)
        
        if args.gui:
            logger.info("Iniciando interface gráfica (GUI)...")
            try:
                # Import tardio para evitar dependência obrigatória em ambientes sem PyQt6
                from gui.gui_ssa import SSAMainWindow
                from PyQt6.QtWidgets import QApplication
            except Exception as e:
                logger.error(f"Falha ao iniciar GUI: {e}")
                logger.info("Recuando para CLI.")
                start_cli_loop(db_path, table_name)
                return

            try:
                # Guarda de instância única da GUI via socket local
                # Se a porta estiver ocupada, assume GUI já em execução
                SINGLE_INSTANCE_PORT = 51234
                single_instance_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    single_instance_sock.bind(("127.0.0.1", SINGLE_INSTANCE_PORT))
                    single_instance_sock.listen(1)
                except OSError:
                    logger.warning("Outra instância da GUI já está em execução. Encerrando esta execução.")
                    print("Já existe uma janela da GUI aberta. Use-a ou feche-a antes de abrir outra.")
                    return
                app = QApplication(sys.argv)
                window = SSAMainWindow()
                window.show()
                # Executa o loop de eventos
                app.exec()
                # Fecha o socket da guarda ao sair
                try:
                    single_instance_sock.close()
                except Exception:
                    pass
            except Exception as e:
                logger.error(f"Falha ao criar/mostrar janela da GUI: {e}")
                logger.info("Recuando para CLI.")
                start_cli_loop(db_path, table_name)
        else:
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
