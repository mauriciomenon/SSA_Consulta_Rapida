#!/usr/bin/env python3
# main.py
"""
Ponto de entrada da aplicacao de Consulta Rapida de SSAs.

Inicializa logging, processa argumentos de linha de comando
e inicia a interface CLI ou GUI conforme as opcoes fornecidas.
"""

import os
import sys
import argparse
import socket
import logging
import shutil
import subprocess
from logging.handlers import RotatingFileHandler
from datetime import datetime
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from gui.gui_ssa import SSAMainWindow

logger = logging.getLogger("ssa")
# Logger level will be set by argument parsing - do not hardcode DEBUG
_logging_configured = False

def _configure_logging(project_root: str, level_console: int = logging.WARNING, level_file: int = logging.INFO, use_robust_system: bool = True):
    """Configura sistema de logging (robusto ou legado)."""
    global _logging_configured
    if _logging_configured:
        return
    
    if use_robust_system:
        # Usa o sistema de logging robusto
        try:
            from utils.robust_logging import setup_logging
            setup_logging()
            logger.info("Sistema de logging robusto inicializado", extra={'component': 'main'})
            _logging_configured = True
            return
        except Exception as e:
            print(f"Sistema robusto indisponível, usando legado: {e}")  # Use print antes do logger estar configurado
    
    # Sistema legado (fallback)
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

# Adiciona o diretorio raiz do projeto ao sys.path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def get_app_version():
    """Obtem versao da aplicacao"""
    try:
        from utils.version import get_app_version as _get_version
        return _get_version()
    except ImportError:
        return "3.11+"


def launch_streamlit(project_root: str, port: Optional[int] = None) -> bool:
    """Inicia o aplicativo Streamlit em segundo plano."""
    script_path = os.path.join(project_root, 'streamlit_app.py')
    if not os.path.exists(script_path):
        print("Streamlit app nao encontrado em streamlit_app.py")
        return False
    if not shutil.which('streamlit'):
        print("Streamlit nao encontrado. Instale com: pip install streamlit")
        return False

    cmd = ['streamlit', 'run', script_path, '--server.headless=true']
    if port:
        cmd.append(f'--server.port={port}')

    logs_dir = os.path.join(project_root, 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    log_path = os.path.join(logs_dir, 'streamlit.log')

    try:
        with open(log_path, 'ab') as log_file:
            process = subprocess.Popen(cmd, stdout=log_file, stderr=log_file, cwd=project_root)
        display_port = port or 8501
        print(f"Streamlit iniciado em background (PID {process.pid}). Acesse http://localhost:{display_port}/")
        print(f"Logs: {log_path}")
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"Falha ao iniciar Streamlit: {exc}")
        return False

def main(cli_args=None):
    """
    Funcao principal da aplicacao com help melhorado.

    Args:
        cli_args (list, optional): Argumentos da linha de comando para testes.
                                   Se None, sys.argv e usado.
    """
    APP_VERSION = get_app_version()

    parser = argparse.ArgumentParser(
        description=f"Consulta Rapida de SSAs v{APP_VERSION}",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
EXEMPLOS DE USO
  Modo padrao:        python main.py
  Modo otimizado:     python main.py --optimized
  Interface grafica:  python main.py --gui
  Reset de banco:     python main.py --reset-db
  Limpeza de dados:   python main.py --clean-data
  Reimportar tudo:    python main.py --force-rescan
  Otimizado + rescan: python main.py --optimized --force-rescan

Mais detalhes: README.md e GUIA_MODO_OPTIMIZED.md
"""
    )

    # Suporta --rescan como alias historico de --force-rescan
    parser.add_argument(
        '--force-rescan', '--rescan',
        dest='force_rescan',
        action='store_true',
        help='''Reimporta todos os arquivos Excel ignorando o cache.

        ┌─ DIFERENCAS ─────────────────────────────────────────────┐
        │ --force-rescan: Nome atual, recomendado                  │
        │ --rescan:       Alias para compatibilidade (mesmo efeito)│
        └──────────────────────────────────────────────────────────┘

        COMPORTAMENTO:
        • Ignora arquivo de controle de importacao (.last_import)
        • Processa todos os arquivos Excel novamente
        • Detecta e importa mudancas, adicoes e remocoes
        • Util quando arquivos foram modificados manualmente

        EXEMPLO: python main.py --force-rescan'''
    )

    parser.add_argument(
        '--optimized',
        action='store_true',
        help='''DEPRECATED: Modo otimizado agora é PADRÃO. Use --standard para modo legado.

        ┌─ AVISO: MODO OTIMIZADO JÁ É PADRÃO ─────────────────────┐
        │ Esta flag não é mais necessária - modo otimizado        │
        │ é ativado automaticamente para melhor performance.      │
        │                                                          │
        │ Use --standard se precisar do modo legado por           │
        │ compatibilidade ou debugging específico.                │
        └──────────────────────────────────────────────────────────┘'''
    )

    parser.add_argument(
        '--standard',
        action='store_true',
        help='''Ativa modo LEGADO/PADRÃO (mais lento, melhor para debugging).

        ┌─ MODO LEGADO/DEBUG ──────────────────────────────────────┐
        │ CARACTERÍSTICAS                                          │
        │   • Operações linha por linha (mais lento)              │
        │   • Logs mais detalhados para debugging                 │
        │   • Verificações adicionais de integridade              │
        │   • Melhor para análise de problemas                    │
        │                                                          │
        │ QUANDO USAR                                              │
        │   • Debugging de problemas de importação                │
        │   • Análise detalhada de erros                          │
        │   • Compatibilidade com sistemas antigos               │
        │   • Desenvolvimento e testes                            │
        └──────────────────────────────────────────────────────────┘

        AVISO: Até 90% mais lento que o modo padrão otimizado.

        EXEMPLOS:
        python main.py --standard
        python main.py --standard --force-rescan

        Mais detalhes: GUIA_MODO_OPTIMIZED.md'''
    )

    parser.add_argument(
        '--gui',
        action='store_true',
        help='''Inicia a interface grafica (GUI) em vez da CLI.

        RECURSOS DA GUI:
        • Interface visual amigável com PyQt6
        • Filtros em tempo real com debounce
        • Exibição em tabela com ordenação por colunas
        • Proteção contra múltiplas instâncias
        • Tooltips explicativos nos controles

        Exemplo: python main.py --gui'''
    )

    parser.add_argument(
        '--streamlit', '--web',
        dest='launch_streamlit',
        action='store_true',
        help='''Inicia a interface web (Streamlit) em segundo plano.

        CARACTERISTICAS:
        • Interface moderna acessivel via navegador
        • Filtros rapidos com sintaxe equivalente a CLI
        • Indicadores resumidos e opcao de consulta a API

        Exemplo: python main.py --streamlit'''
    )

    parser.add_argument(
        '--streamlit-port',
        type=int,
        default=8501,
        help='Porta para a interface web (usar em conjunto com --streamlit)'
    )

    parser.add_argument(
        '--reset-db',
        action='store_true',
        help='''Zera o banco de dados e cria apenas a estrutura (sem importar dados).

        Operacao destrutiva:
        • Backup automático é criado antes da operação
        • Remove todos os dados existentes
        • Recria estrutura limpa das tabelas
        • Não importa novos dados automaticamente

        Exemplo: python main.py --reset-db'''
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

        Exemplo: python main.py --clean-data'''
    )

    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        default='INFO',
        help='Define o nivel de detalhe dos logs (padrao: INFO)'
    )

    # Acao principal (processar = comportamento atual, backfill = reprocessar historico via script dedicado)
    parser.add_argument(
        '--acao',
        choices=['processar', 'backfill'],
        default='processar',
        help='Define acao principal: processar (import normal) ou backfill (reprocessar diretorio historico).\n'
             'Uso para backfill com argumentos extras apos -- :\n'
             '  python main.py --acao backfill -- --dir docs_entrada --dry-run --smart-upsert\n'
    )

    # Suporte a passagem de argumentos apos '--' exclusivamente ao backfill
    raw_args = cli_args if cli_args is not None else sys.argv[1:]
    backfill_args: list[str] = []
    if '--' in raw_args:
        split_idx = raw_args.index('--')
        main_args = raw_args[:split_idx]
        backfill_args = raw_args[split_idx + 1:]
    else:
        main_args = raw_args

    # Parse dos argumentos principais
    args = parser.parse_args(main_args)

    # Configura logging
    _configure_logging(project_root)
    try:
        logger.setLevel(getattr(logging, args.log_level))
    except AttributeError:
        logger.setLevel(logging.INFO)

    # Banner inicial
    print(f"Pesquisa Rapida de SSAs {APP_VERSION}")

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
                print("Modulo de gerenciamento de banco nao disponivel")
            return

        if args.clean_data:
            print("Limpando pasta data...")
            try:
                from scripts_manutencao.gerenciar_banco import clean_old_backups, sanitize_data_folder
                clean_old_backups()
                sanitize_data_folder()
                print("Limpeza concluida!")
            except ImportError:
                print("Modulo de gerenciamento de banco nao disponivel")
            return

        # --- 1. Preparação do Ambiente ---
        logger.debug("Verificando/criando estrutura de pastas...")
        setup_project_structure.setup_dirs()
        logger.info("Estrutura de pastas verificada.")

        # --- 2. Configuração ---
        logger.debug("Garantindo configuracoes padrao...")
        ensure_default_settings()
        logger.debug("Configuracoes padrao verificadas.")

        # Se a acao for backfill, executar diretamente o script de backfill e encerrar
        if getattr(args, 'acao', 'processar') == 'backfill':
            logger.info("Acao=backfill selecionada. Encaminhando argumentos ao backfill: %s", backfill_args)
            try:
                from scripts.migracao.backfill_reprocessar import main as backfill_main
            except ModuleNotFoundError:
                # garantir path root
                if project_root not in sys.path:
                    sys.path.insert(0, project_root)
                from scripts.migracao.backfill_reprocessar import main as backfill_main  # type: ignore
            # Executa backfill (retorna exit code int)
            exit_code = backfill_main(backfill_args)
            logger.info("Backfill finalizado (exit_code=%s)", exit_code)
            return

        # --- 3. Importação de Dados (fluxo normal) ---
        # Determina se a reimportação é forçada e se deve usar versão otimizada
        force_import = args.force_rescan
        
        # MUDANÇA: Modo otimizado agora é PADRÃO (exceto se --standard for usado)
        use_optimized = not args.standard
        
        # Aviso de depreciação se --optimized for usado
        if args.optimized:
            logger.warning("⚠️  Flag --optimized é deprecated: modo otimizado já é padrão. Use --standard para modo legado.")

        # Ativar importação otimizada (agora padrão)
        if use_optimized:
            logger.info("✓ Modo de importacao OTIMIZADA ativo (padrão)")
            try:
                from armazenamento.database_optimized import enable_optimized_import
                enable_optimized_import()
            except ImportError:
                logger.warning("Modo otimizado não disponível, recorrendo ao modo legado")
                use_optimized = False
        else:
            logger.info("⚠️  Usando modo LEGADO/DEBUG (--standard ativo)")

        logger.info(f"Iniciando processo de importacao (force_rescan={force_import}, optimized={use_optimized})...")
        db_updated = run_importer_logic(force_import=force_import)

        # Desativar importação otimizada após uso
        if use_optimized:
            try:
                from armazenamento.database_optimized import disable_optimized_import
                disable_optimized_import()
            except ImportError:
                pass
            except Exception as e:
                logger.warning(f"Falha ao desativar modo otimizado: {e}")

        if db_updated:
            logger.info("Banco de dados atualizado com sucesso.")
        else:
            logger.info("Nenhum novo ou modificado relatorio encontrado.")

        # --- 4. Início da Interface ---
        # Respeita variáveis de ambiente para facilitar testes e integração
        # Exemplos:
        #   SSA_DB_PATH=C:\\tmp\\test_ssas.db  SSA_TABLE_NAME=ssas  python main.py --log-level INFO
        db_path = os.environ.get('SSA_DB_PATH') or os.path.join(project_root, 'data', 'ssas.db')
        table_name = os.environ.get('SSA_TABLE_NAME') or 'ssa_table'
        logger.info(f"Usando base: {db_path} (tabela: {table_name})")

        if args.launch_streamlit:
            if args.gui:
                print("Nao combine --gui com --streamlit ao mesmo tempo.")
                return
            launched = launch_streamlit(project_root, port=args.streamlit_port)
            if launched:
                print("Interface web ativa. Pressione CTRL+C quando desejar encerrar este processo.")
            return

        if args.gui:
            logger.info("Iniciando interface grafica (GUI)...")
            try:
                # Import tardio para evitar dependencia obrigatoria em ambientes sem PyQt6
                from gui.gui_ssa import SSAMainWindow
                from PyQt6.QtWidgets import QApplication
            except Exception as e:
                logger.error(f"Falha ao iniciar GUI: {e}")
                logger.info("Recuando para CLI.")
                start_cli_loop(db_path, table_name)
                return

            try:
                # Guarda de instancia unica da GUI via socket local
                # Se a porta estiver ocupada, assume GUI ja em execucao
                SINGLE_INSTANCE_PORT = 51234
                single_instance_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    single_instance_sock.bind(("127.0.0.1", SINGLE_INSTANCE_PORT))
                    single_instance_sock.listen(1)
                except OSError:
                    logger.warning("Outra instancia da GUI ja esta em execucao. Encerrando esta execucao.")
                    print("Ja existe uma janela da GUI aberta. Use-a ou feche-a antes de abrir outra.")
                    return
                app = QApplication(sys.argv)
                window = SSAMainWindow()
                window.show()  # type: ignore[attr-defined]
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
        logger.info("\nOperacao interrompida pelo usuario. Saindo...")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Erro critico na inicializacao: {e}", exc_info=True)
        sys.exit(1)

    logger.info("aplicacao encerrada normalmente.")

if __name__ == "__main__":
    # Permite que o script seja executado diretamente
    main()
