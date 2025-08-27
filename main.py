#!/usr/bin/env python3
# main.py 20250827 100000 (v3.0.5+ - Help melhorado, documentação clara)
"""
Ponto de entrada da aplicação de Consulta Rápida de SSAs.

Versão com help melhorado conforme solicitação do usuário:
- Diferença clara entre --force-rescan e --rescan
- Sub-chaves organizadas do --optimized
- Help exibido na inicialização antes do prompt
"""

import os
import sys
import argparse
import socket
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime

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

# Adiciona o diretório raiz do projeto ao sys.path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def get_app_version():
    """Obtém versão da aplicação"""
    try:
        from utils.version import get_app_version as _get_version
        return _get_version()
    except ImportError:
        return "3.0.5+"

def main(cli_args=None):
    """
    Função principal da aplicação com help melhorado.

    Args:
        cli_args (list, optional): Argumentos da linha de comando para testes.
                                   Se None, sys.argv é usado.
    """
    APP_VERSION = get_app_version()
    
    parser = argparse.ArgumentParser(
        description=f"Consulta Rápida de SSAs v{APP_VERSION}",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
╔═══════════════════════════════════════════════════════════════╗
║                    EXEMPLOS DE USO                           ║
╠═══════════════════════════════════════════════════════════════╣
║ Modo padrão:        python main.py                           ║
║ Modo otimizado:     python main.py --optimized               ║
║ Interface gráfica:  python main.py --gui                     ║
║ Reset de banco:     python main.py --reset-db                ║
║ Limpeza de dados:   python main.py --clean-data              ║
║ Reimportar tudo:    python main.py --force-rescan            ║
║ Otimizado + rescan: python main.py --optimized --force-rescan║
╚═══════════════════════════════════════════════════════════════╝

Para mais informações, consulte: README.md e GUIA_MODO_OPTIMIZED.md
"""
    )
    
    # Suporta --rescan como alias histórico de --force-rescan
    parser.add_argument(
        '--force-rescan', '--rescan',
        dest='force_rescan',
        action='store_true',
        help='''Força a reimportação de todos os arquivos Excel, ignorando o cache.
        
        ┌─ DIFERENÇAS ─────────────────────────────────────────────┐
        │ --force-rescan: Nome atual recomendado (mais explícito)  │
        │ --rescan:       Alias para compatibilidade (mesmo efeito)│
        └──────────────────────────────────────────────────────────┘
        
        COMPORTAMENTO:
        • Ignora arquivo de controle de importação (.last_import)
        • Processa todos os arquivos Excel novamente
        • Detecta e importa mudanças, adições e remoções
        • Útil quando arquivos foram modificados manualmente
        
        EXEMPLO: python main.py --force-rescan'''
    )
    
    parser.add_argument(
        '--optimized',
        action='store_true',
        help='''Ativa modo de importação OTIMIZADA (até 90%% mais rápido).

        ┌─ OTIMIZAÇÕES APLICADAS ──────────────────────────────────┐
        │ PERFORMANCE                                              │
        │   • Operações em lote (batch operations)                │
        │   • Buffer de memória aumentado                         │
        │   • Paralelização de operações                          │
        │                                                          │
        │ BANCO DE DADOS                                           │
        │   • Configurações otimizadas do SQLite                  │
        │   • Transações em lote                                  │
        │   • Índices temporários para importação                 │
        │                                                          │
        │ PROCESSAMENTO                                            │
        │   • Cache inteligente de arquivos                       │
        │   • Processamento sequencial otimizado                  │
        │   • Menos verificações redundantes                      │
        └──────────────────────────────────────────────────────────┘
        
        RESULTADOS ESPERADOS:
        • Arquivos pequenos (<5MB): 30-50%% mais rápido
        • Arquivos médios (5-20MB): 60-80%% mais rápido  
        • Arquivos grandes (>20MB): 80-90%% mais rápido
        
        RECOMENDADO PARA:
        • Importação de grandes volumes de dados
        • Execução em lote ou automatizada
        • Quando a importação padrão está lenta
        
        EXEMPLOS:
        python main.py --optimized
        python main.py --optimized --force-rescan
        
        Para detalhes técnicos, consulte: GUIA_MODO_OPTIMIZED.md'''
    )
    
    parser.add_argument(
        '--gui',
        action='store_true',
        help='''Inicia a interface gráfica (GUI) em vez da CLI.
        
        RECURSOS DA GUI:
        • Interface visual amigável com PyQt6
        • Filtros em tempo real com debounce
        • Exibição em tabela com ordenação por colunas
        • Proteção contra múltiplas instâncias
        • Tooltips explicativos nos controles
        
        EXEMPLO: python main.py --gui'''
    )
    
    parser.add_argument(
        '--reset-db',
        action='store_true',
        help='''Zera o banco de dados e cria apenas a estrutura (sem importar dados).
        
        OPERAÇÃO DESTRUTIVA:
        • Backup automático é criado antes da operação
        • Remove todos os dados existentes
        • Recria estrutura limpa das tabelas
        • Não importa novos dados automaticamente
        
        EXEMPLO: python main.py --reset-db'''
    )
    
    parser.add_argument(
        '--clean-data',
        action='store_true',
        help='''Limpa e sanitiza a pasta data (remove backups antigos).
        
        LIMPEZA REALIZADA:
        • Remove backups mais antigos que 30 dias
        • Organiza arquivos de log antigos
        • Verifica integridade dos arquivos restantes
        • Exibe relatório de espaço liberado
        
        EXEMPLO: python main.py --clean-data'''
    )
    
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        default='INFO',
        help='Define o nível de detalhe dos logs (padrão: INFO)'
    )
    
    # Parse dos argumentos - argparse automaticamente lida com --help
    args = parser.parse_args(cli_args) if cli_args is not None else parser.parse_args()
    
    # Configura logging
    _configure_logging(project_root)
    try:
        logger.setLevel(getattr(logging, args.log_level))
    except:
        logger.setLevel(logging.INFO)

    # Banner inicial
    print(f"Pesquisa Rápida de SSAs {APP_VERSION}")

    try:
        # Imports dinâmicos para evitar problemas
        try:
            from utils import setup_project_structure
            from core.app_logic import run_importer_logic
            from interface.cli import start_cli_loop
            from core.config_manager import ensure_default_settings
        except ImportError as e:
            print(f"⚠️ Aviso: Alguns módulos não puderam ser carregados: {e}")
            print("Sistema funcionando em modo limitado.")
            return

        # --- Operações Especiais ---
        if args.reset_db:
            print("Resetando banco de dados...")
            try:
                from scripts_manutencao.gerenciar_banco import reset_database
                reset_database()
                print("Banco de dados resetado com sucesso!")
            except ImportError:
                print("Módulo de gerenciamento de banco não disponível")
            return
        
        if args.clean_data:
            print("Limpando pasta data...")
            try:
                from scripts_manutencao.gerenciar_banco import clean_old_backups, sanitize_data_folder
                clean_old_backups()
                sanitize_data_folder()
                print("Limpeza concluída!")
            except ImportError:
                print("Módulo de gerenciamento de banco não disponível")
            return

        # --- 1. Preparação do Ambiente ---
        logger.debug("Verificando/criando estrutura de pastas...")
        setup_project_structure.setup_dirs()
        logger.info("Estrutura de pastas verificada.")

        # --- 2. Configuração ---
        logger.debug("Garantindo configurações padrão...")
        ensure_default_settings()
        logger.debug("Configurações padrão verificadas.")

        # --- 3. Importação de Dados ---
        # Determina se a reimportação é forçada e se deve usar versão otimizada
        force_import = args.force_rescan
        use_optimized = args.optimized
        
        # Ativar importação otimizada se solicitado
        if use_optimized:
            logger.info("Ativando modo de importação OTIMIZADA...")
            try:
                from armazenamento.database_optimized import enable_optimized_import
                enable_optimized_import()
            except ImportError:
                print("Modo otimizado não disponível, usando modo padrão")
                use_optimized = False
        
        logger.info(f"Iniciando processo de importação (force_rescan={force_import}, optimized={use_optimized})...")
        db_updated = run_importer_logic(force_import=force_import)
        
        # Desativar importação otimizada após uso
        if use_optimized:
            try:
                from armazenamento.database_optimized import disable_optimized_import
                disable_optimized_import()
            except ImportError:
                pass
        
        if db_updated:
            logger.info("Banco de dados atualizado com sucesso.")
        else:
            logger.info("Nenhum novo ou modificado relatório encontrado.")

        # --- 4. Início da Interface ---
        db_path = os.path.join(project_root, 'data', 'ssas.db')
        table_name = 'ssa_table'
        
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
