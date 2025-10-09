#!/usr/bin/env python3
# main.py
"""
Ponto de entrada da aplicacao de Consulta Rapida de SSAs.

Inicializa logging, processa argumentos de linha de comando
e inicia a interface CLI ou GUI conforme as opcoes fornecidas.
"""

import argparse
import logging
import os
import shutil
import socket
import subprocess
import sys
from logging.handlers import RotatingFileHandler
from typing import Optional

logger = logging.getLogger("ssa")
# Logger level will be set by argument parsing - do not hardcode DEBUG
_logging_configured = False


def _load_external_run_importer(project_root: str):
    """
    Try to load run_importer_logic from extracao.extractor, if available.

    Returns:
        callable | None: External implementation (if provided), otherwise None.
    """
    try:
        import importlib.util

        spec = importlib.util.find_spec("extracao.extractor")
        if not spec or not spec.loader:
            logger.debug("DIAGNOSTICO: extracao.extractor nao encontrado.")
            return None

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        candidate = getattr(module, "run_importer_logic", None)
        if callable(candidate):
            logger.info("DIAGNOSTICO: usando run_importer_logic de extracao.extractor.")
            return candidate

        logger.info(
            "DIAGNOSTICO: extracao.extractor presente, mas sem run_importer_logic; "
            "mantendo implementacao de core.app_logic."
        )
        return None
    except Exception as exc:  # noqa: BLE001
        logger.debug(
            "DIAGNOSTICO: nao foi possivel utilizar extracao.extractor (%s); mantendo core.app_logic.",
            exc,
            exc_info=True,
        )
        return None


class SafeRawTextHelpFormatter(argparse.RawTextHelpFormatter):
    """RawTextHelpFormatter que tolera % literais nos textos."""

    def _expand_help(self, action):
        help_text = action.help
        if help_text is None:
            return None
        try:
            return super()._expand_help(action)
        except (KeyError, ValueError):
            return help_text


def _configure_logging(project_root: str, level_console: int = logging.WARNING, level_file: int = logging.INFO, use_robust_system: bool = True):
    """Configura sistema de logging (robusto ou legado)."""
    global _logging_configured
    if _logging_configured:
        return
    
    # LOGS DE DIAGNOSTICO DE CONFIGURACAO DE LOGGING
    print(f"DIAGNOSTICO: Iniciando configuracao de logging em {project_root}")
    print(f"DIAGNOSTICO: use_robust_system = {use_robust_system}")
    print(f"DIAGNOSTICO: Nivel console = {level_console}, Nivel arquivo = {level_file}")
    
    if use_robust_system:
        # Usa o sistema de logging robusto
        robust_path = os.path.join(project_root, 'utils', 'robust_logging.py')
        print(f"DIAGNOSTICO: Verificando arquivo de logging robusto em: {robust_path}")
        print(f"DIAGNOSTICO: Arquivo existe: {os.path.exists(robust_path)}")
        
        # DIAGNOSTICO DETALHADO: Verificacao do modulo de logging robusto
        if os.path.exists(robust_path):
            file_stat = os.stat(robust_path)
            print(f"DIAGNOSTICO: Permissoes do arquivo robust_logging.py: {oct(file_stat.st_mode)}")
            print(f"DIAGNOSTICO: Tamanho do arquivo robust_logging.py: {file_stat.st_size} bytes")
            
            # Verificar se utils esta no sys.path
            utils_path = os.path.join(project_root, 'utils')
            print(f"DIAGNOSTICO: Diretorio utils no sys.path: {utils_path in sys.path}")
            
            # Listar arquivos no diretorio utils
            if os.path.exists(utils_path):
                print(f"DIAGNOSTICO: Arquivos em utils/: {os.listdir(utils_path)}")
        
        try:
            print("DIAGNOSTICO: Tentando importar utils.robust_logging...")
            
            # Verificar se o modulo pode ser encontrado
            import importlib.util
            spec = importlib.util.find_spec('utils.robust_logging')
            print(f"DIAGNOSTICO: Espec para 'utils.robust_logging': {spec}")
            
            if spec:
                print(f"DIAGNOSTICO: Localizacao do modulo utils.robust_logging: {spec.origin}")
            
            from utils.robust_logging import setup_logging
            print("DIAGNOSTICO: Importacao de utils.robust_logging bem-sucedida")
            
            # Verificar se a funcao existe
            print(f"DIAGNOSTICO: setup_logging e callable: {callable(setup_logging)}")
            
            setup_logging()
            logger.info("Sistema de logging robusto inicializado", extra={'component': 'main'})
            print("DIAGNOSTICO: Sistema de logging robusto configurado com sucesso")
            _logging_configured = True
            return
        except ImportError as e:
            print(f"Sistema robusto indisponivel, usando legado: {e}")
            print(f"DIAGNOSTICO: Tipo do erro: {type(e).__name__}")
            print(f"DIAGNOSTICO: Modulo que causou o erro: {getattr(e, 'name', 'desconhecido')}")
            print(f"DIAGNOSTICO: Detalhes do erro: {e}")
            
            # Verificar dependencias do logging robusto
            print("DIAGNOSTICO: Verificando dependencias do logging robusto...")
            try:
                import json
                print("DIAGNOSTICO: json disponivel")
            except ImportError as je:
                print(f"DIAGNOSTICO: json NAO disponivel: {je}")
                
            try:
                import threading
                print("DIAGNOSTICO: threading disponivel")
            except ImportError as te:
                print(f"DIAGNOSTICO: threading NAO disponivel: {te}")
    
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
    # CORRECAO: Declarar project_root como global para evitar UnboundLocalError
    global project_root
    """
    # LOGS DE DIAGNOSTICO DE IMPORTACAO
    logger.info("DIAGNOSTICO: Iniciando funcao main()")
    
    # CORRECAO: Importar sys no inicio da funcao para evitar UnboundLocalError
    import sys
    
    # DIAGNOSTICO: Verificar escopo da variavel sys
    logger.info("DIAGNOSTICO: Verificando escopo da variavel sys...")
    logger.info("DIAGNOSTICO: sys disponivel no escopo global: %s", 'sys' in globals())
    logger.info("DIAGNOSTICO: sys disponivel no escopo local: %s", 'sys' in locals())
    logger.info("DIAGNOSTICO: sys.argv disponivel: %s", hasattr(sys, 'argv'))
    
    # Verificar se sys esta no escopo global
    logger.info("DIAGNOSTICO: sys importado localmente: %s", hasattr(sys, 'argv'))
    
    # LOGS DE DIAGNOSTICO DE ESTRUTURA DE DIRETORIOS
    logger.info("DIAGNOSTICO: Verificando estrutura de diretorios do projeto...")
    logger.info("DIAGNOSTICO: Diretorio raiz do projeto: %s", project_root)
    logger.info("DIAGNOSTICO: sys.path atual: %s", sys.path)
    
    # Verificar estrutura de diretorios
    import os
    extracao_root = os.path.join(project_root, 'extracao')
    extracao_core = os.path.join(project_root, 'core', 'extracao')
    
    logger.info("DIAGNOSTICO: Diretorio extracao (raiz): %s", extracao_root)
    logger.info("DIAGNOSTICO: Diretorio extracao (core): %s", extracao_core)
    logger.info("DIAGNOSTICO: Diretorio extracao (raiz) existe: %s", os.path.exists(extracao_root))
    logger.info("DIAGNOSTICO: Diretorio extracao (core) existe: %s", os.path.exists(extracao_core))
    
    # Listar conteudo dos diretorios
    if os.path.exists(extracao_root):
        logger.info("DIAGNOSTICO: Conteudo de extracao (raiz): %s", os.listdir(extracao_root))
    if os.path.exists(extracao_core):
        logger.info("DIAGNOSTICO: Conteudo de extracao (core): %s", os.listdir(extracao_core))
    
    # Verificar arquivo extractor.py em ambos os locais
    extractor_root = os.path.join(extracao_root, 'extractor.py')
    extractor_core = os.path.join(extracao_core, 'extractor.py')
    
    logger.info("DIAGNOSTICO: Arquivo extractor.py (raiz): %s", extractor_root)
    logger.info("DIAGNOSTICO: Arquivo extractor.py (core): %s", extractor_core)
    logger.info("DIAGNOSTICO: Arquivo extractor.py (raiz) existe: %s", os.path.exists(extractor_root))
    logger.info("DIAGNOSTICO: Arquivo extractor.py (core) existe: %s", os.path.exists(extractor_core))
    
    # Verificar permissoes
    if os.path.exists(extractor_root):
        logger.info("DIAGNOSTICO: Permissoes do arquivo extractor.py (raiz): %s", oct(os.stat(extractor_root).st_mode))
    if os.path.exists(extractor_core):
        logger.info("DIAGNOSTICO: Permissoes do arquivo extractor.py (core): %s", oct(os.stat(extractor_core).st_mode))
    
    APP_VERSION = get_app_version()

    parser = argparse.ArgumentParser(
        description=f"Consulta Rapida de SSAs v{APP_VERSION}",
        formatter_class=SafeRawTextHelpFormatter,
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

         DIFERENCAS 
         --force-rescan: Nome atual, recomendado                  
         --rescan:       Alias para compatibilidade (mesmo efeito)
        

        COMPORTAMENTO:
         Ignora arquivo de controle de importacao (.last_import)
         Processa todos os arquivos Excel novamente
         Detecta e importa mudancas, adicoes e remocoes
         Util quando arquivos foram modificados manualmente

        EXEMPLO: python main.py --force-rescan'''
    )

    parser.add_argument(
        '--optimized',
        action='store_true',
        help='''DEPRECATED: Modo otimizado agora e PADRAO. Use --standard para modo legado.

         AVISO: MODO OTIMIZADO JA E PADRAO 
         Esta flag nao e mais necessaria - modo otimizado        
         e ativado automaticamente para melhor performance.      
                                                                  
         Use --standard se precisar do modo legado por           
         compatibilidade ou debugging especifico.                
        '''
    )

    parser.add_argument(
        '--standard',
        action='store_true',
        help='''Ativa modo LEGADO/PADRAO (mais lento, melhor para debugging).

         MODO LEGADO/DEBUG 
         CARACTERISTICAS                                          
            Operacoes linha por linha (mais lento)              
            Logs mais detalhados para debugging                 
            Verificacoes adicionais de integridade              
            Melhor para analise de problemas                    
                                                                  
         QUANDO USAR                                              
            Debugging de problemas de importacao                
            Analise detalhada de erros                          
            Compatibilidade com sistemas antigos               
            Desenvolvimento e testes                            
        

        AVISO: Ate 90% mais lento que o modo padrao otimizado.

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
         Interface visual amigavel com PyQt6
         Filtros em tempo real com debounce
         Exibicao em tabela com ordenacao por colunas
         Protecao contra multiplas instancias
         Tooltips explicativos nos controles

        Exemplo: python main.py --gui'''
    )

    parser.add_argument(
        '--streamlit', '--web',
        dest='launch_streamlit',
        action='store_true',
        help='''Inicia a interface web (Streamlit) em segundo plano.

        CARACTERISTICAS:
         Interface moderna acessivel via navegador
         Filtros rapidos com sintaxe equivalente a CLI
         Indicadores resumidos e opcao de consulta a API

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
         Backup automatico e criado antes da operacao
         Remove todos os dados existentes
         Recria estrutura limpa das tabelas
         Nao importa novos dados automaticamente

        Exemplo: python main.py --reset-db'''
    )

    parser.add_argument(
        '--clean-data',
        action='store_true',
        help='''Limpa e sanitiza a pasta data (remove backups antigos).

        LIMPEZA REALIZADA:
         Remove backups mais antigos que 30 dias
         Organiza arquivos de log antigos
         Verifica integridade dos arquivos restantes
         Exibe relatorio de espaco liberado

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
    # LOGS DE DIAGNOSTICO DE ARGUMENTOS
    logger.info("DIAGNOSTICO: Processando argumentos de linha de comando")
    logger.info("DIAGNOSTICO: cli_args fornecido: %s", cli_args is not None)
    logger.info("DIAGNOSTICO: sys.argv disponivel: %s", hasattr(sys, 'argv'))
    
    if hasattr(sys, 'argv'):
        logger.info("DIAGNOSTICO: sys.argv[1:]: %s", sys.argv[1:])
    else:
        logger.error("DIAGNOSTICO: sys.argv nao esta disponivel!")
    
    raw_args = cli_args if cli_args is not None else sys.argv[1:]
    backfill_args: list[str] = []
    if '--' in raw_args:
        split_idx = raw_args.index('--')
        main_args = raw_args[:split_idx]
        backfill_args = raw_args[split_idx + 1:]
    else:
        main_args = raw_args
    
    logger.info("DIAGNOSTICO: raw_args: %s", raw_args)
    logger.info("DIAGNOSTICO: main_args: %s", main_args)
    logger.info("DIAGNOSTICO: backfill_args: %s", backfill_args)

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
        # Imports dinamicos para evitar problemas
        try:
            logger.info("DIAGNOSTICO: Tentando importar modulos...")
            
            # Testar importacao individualmente
            try:
                from core.app_logic import run_importer_logic
                logger.info("DIAGNOSTICO: Importacao de core.app_logic bem sucedida")
            except ImportError as e:
                logger.error("DIAGNOSTICO: Falha ao importar core.app_logic: %s", e)
                
            try:
                from core.config_manager import ensure_default_settings
                logger.info("DIAGNOSTICO: Importacao de core.config_manager bem sucedida")
            except ImportError as e:
                logger.error("DIAGNOSTICO: Falha ao importar core.config_manager: %s", e)
                
            try:
                from interface.cli import start_cli_loop
                logger.info("DIAGNOSTICO: Importacao de interface.cli bem sucedida")
            except ImportError as e:
                logger.error("DIAGNOSTICO: Falha ao importar interface.cli: %s", e)
                
            try:
                from utils import setup_project_structure
                logger.info("DIAGNOSTICO: Importacao de utils.setup_project_structure bem sucedida")
            except ImportError as e:
                logger.error("DIAGNOSTICO: Falha ao importar utils.setup_project_structure: %s", e)
                
            # Tentar importar todos juntos
            from core.app_logic import run_importer_logic
            from core.config_manager import ensure_default_settings
            from interface.cli import start_cli_loop
            from utils import setup_project_structure
            logger.info("DIAGNOSTICO: Todas as importacoes bem sucedidas")
            
        except ImportError as e:
            logger.error("DIAGNOSTICO: Falha critica nas importacoes: %s", e)
            print(f" Aviso: Alguns modulos nao puderam ser carregados: {e}")
            print("Sistema funcionando em modo limitado.")
            return

        # --- Operacoes Especiais ---
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

        # --- 1. Preparacao do Ambiente ---
        logger.debug("Verificando/criando estrutura de pastas...")
        logger.info("DIAGNOSTICO: Iniciando preparacao do ambiente...")
        
        # LOGS DE DIAGNOSTICO ADICIONAIS
        logger.info("DIAGNOSTICO: Caminho do projeto: %s", project_root)
        logger.info("DIAGNOSTICO: Diretorio atual: %s", os.getcwd())
        logger.info("DIAGNOSTICO: sys.path: %s", sys.path)
        
        # Verificar diretorios importantes
        data_dir = os.path.join(project_root, 'data')
        docs_dir = os.path.join(project_root, 'docs_entrada')
        config_dir = os.path.join(project_root, 'config')
        core_dir = os.path.join(project_root, 'core')
        armazenamento_dir = os.path.join(core_dir, 'armazenamento')
        extracao_dir = os.path.join(core_dir, 'extracao')
        
        logger.info("DIAGNOSTICO: Verificando diretorios...")
        logger.info("DIAGNOSTICO: data_dir existe: %s", os.path.exists(data_dir))
        logger.info("DIAGNOSTICO: docs_dir existe: %s", os.path.exists(docs_dir))
        logger.info("DIAGNOSTICO: config_dir existe: %s", os.path.exists(config_dir))
        logger.info("DIAGNOSTICO: core_dir existe: %s", os.path.exists(core_dir))
        logger.info("DIAGNOSTICO: armazenamento_dir existe: %s", os.path.exists(armazenamento_dir))
        logger.info("DIAGNOSTICO: extracao_dir existe: %s", os.path.exists(extracao_dir))
        
        # Listar arquivos nos diretorios importantes
        if os.path.exists(data_dir):
            logger.info("DIAGNOSTICO: Arquivos em data/: %s", os.listdir(data_dir))
        if os.path.exists(docs_dir):
            logger.info("DIAGNOSTICO: Arquivos em docs_entrada/: %s", os.listdir(docs_dir))
        if os.path.exists(config_dir):
            logger.info("DIAGNOSTICO: Arquivos em config/: %s", os.listdir(config_dir))
        if os.path.exists(core_dir):
            logger.info("DIAGNOSTICO: Arquivos em core/: %s", os.listdir(core_dir))
        if os.path.exists(armazenamento_dir):
            logger.info("DIAGNOSTICO: Arquivos em core/armazenamento/: %s", os.listdir(armazenamento_dir))
        if os.path.exists(extracao_dir):
            logger.info("DIAGNOSTICO: Arquivos em core/extracao/: %s", os.listdir(extracao_dir))
        
        # Verificar arquivos especificos que causam problemas
        database_py = os.path.join(armazenamento_dir, 'database.py')
        extractor_py = os.path.join(extracao_dir, 'extractor.py')
        
        logger.info("DIAGNOSTICO: database.py existe: %s", os.path.exists(database_py))
        logger.info("DIAGNOSTICO: extractor.py existe: %s", os.path.exists(extractor_py))
        
        # Verificar arquivos alternativos
        database_optimized = os.path.join(armazenamento_dir, 'database_optimized.py')
        logger.info("DIAGNOSTICO: database_optimized.py existe: %s", os.path.exists(database_optimized))
        
        # Verificar arquivos de init nos diretorios
        armazenamento_init = os.path.join(armazenamento_dir, '__init__.py')
        extracao_init = os.path.join(extracao_dir, '__init__.py')
        
        logger.info("DIAGNOSTICO: armazenamento/__init__.py existe: %s", os.path.exists(armazenamento_init))
        logger.info("DIAGNOSTICO: extracao/__init__.py existe: %s", os.path.exists(extracao_init))
        
        # Verificar variaveis de ambiente importantes
        logger.info("DIAGNOSTICO: Variaveis de ambiente:")
        logger.info("DIAGNOSTICO: SSA_DB_PATH: %s", os.environ.get('SSA_DB_PATH'))
        logger.info("DIAGNOSTICO: SSA_TABLE_NAME: %s", os.environ.get('SSA_TABLE_NAME'))
        logger.info("DIAGNOSTICO: PYTHONPATH: %s", os.environ.get('PYTHONPATH'))
        
        setup_project_structure.setup_dirs()
        logger.info("Estrutura de pastas verificada.")
        logger.info("DIAGNOSTICO: Preparacao do ambiente concluida com sucesso.")

        # --- 2. Configuracao ---
        logger.debug("Garantindo configuracoes padrao...")
        logger.info("DIAGNOSTICO: Iniciando configuracao do sistema...")
        try:
            ensure_default_settings()
            logger.debug("Configuracoes padrao verificadas.")
            logger.info("DIAGNOSTICO: Configuracao do sistema concluida com sucesso.")
        except Exception as e:
            logger.error(f"DIAGNOSTICO: Falha na configuracao do sistema: {e}")
            raise

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

        # --- 3. Importacao de Dados (fluxo normal) ---
        # Determina se a reimportacao e forcada e se deve usar versao otimizada
        force_import = args.force_rescan
        
        # MUDANCA: Modo otimizado agora e PADRAO (exceto se --standard for usado)
        use_optimized = not args.standard
        
        # Aviso de depreciacao se --optimized for usado
        if args.optimized:
            logger.warning("  Flag --optimized e deprecated: modo otimizado ja e padrao. Use --standard para modo legado.")

        # Ativar importacao otimizada (agora padrao)
        if use_optimized:
            logger.info(" Modo de importacao OTIMIZADA ativo (padrao)")
            logger.info("DIAGNOSTICO: Tentando importar enable_optimized_import de armazenamento.database_optimized")
            
            # Testar caminho absoluto
            import sys
            import os
            current_project_root = project_root
            optimized_path = os.path.join(current_project_root, 'armazenamento', 'database_optimized.py')
            logger.info(f"DIAGNOSTICO: Caminho absoluto do modulo otimizado: {optimized_path}")
            logger.info(f"DIAGNOSTICO: Arquivo existe: {os.path.exists(optimized_path)}")
            
            # DIAGNOSTICO DETALHADO: Verificacao do modulo otimizado
            logger.info("DIAGNOSTICO: Verificando disponibilidade do modo otimizado...")
            
            # Verificar se o arquivo existe
            import os
            optimized_file_path = os.path.join(current_project_root, 'armazenamento', 'database_optimized.py')
            logger.info("DIAGNOSTICO: Caminho do arquivo otimizado: %s", optimized_file_path)
            logger.info("DIAGNOSTICO: Arquivo otimizado existe: %s", os.path.exists(optimized_file_path))
            
            if os.path.exists(optimized_file_path):
                # Verificar permissoes
                file_stat = os.stat(optimized_file_path)
                logger.info("DIAGNOSTICO: Permissoes do arquivo otimizado: %s", oct(file_stat.st_mode))
                logger.info("DIAGNOSTICO: Tamanho do arquivo otimizado: %d bytes", file_stat.st_size)
                
                # Verificar se o diretorio armazenamento esta no sys.path
                armazenamento_path = os.path.join(current_project_root, 'armazenamento')
                logger.info("DIAGNOSTICO: Diretorio armazenamento no sys.path: %s", armazenamento_path in sys.path)
                
                # Listar arquivos no diretorio armazenamento
                if os.path.exists(armazenamento_path):
                    logger.info("DIAGNOSTICO: Arquivos em armazenamento/: %s", os.listdir(armazenamento_path))
            
            try:
                # Tentar importar o modulo completo primeiro
                logger.info("DIAGNOSTICO: Tentando importar armazenamento.database_optimized...")
                import armazenamento.database_optimized
                logger.info("DIAGNOSTICO: Importacao do modulo completo bem-sucedida")
                
                # Verificar se a funcao existe no modulo
                logger.info("DIAGNOSTICO: Verificando se enable_optimized_import existe no modulo...")
                if hasattr(armazenamento.database_optimized, 'enable_optimized_import'):
                    logger.info("DIAGNOSTICO: Funcao enable_optimized_import encontrada")
                    
                    from armazenamento.database_optimized import enable_optimized_import
                    logger.info("DIAGNOSTICO: Importacao de enable_optimized_import bem-sucedida")
                    
                    enable_optimized_import()
                    logger.info("DIAGNOSTICO: enable_optimized_import() executado com sucesso")
                else:
                    logger.error("DIAGNOSTICO: Funcao enable_optimized_import NAO encontrada no modulo")
                    logger.warning("Modo otimizado nao disponivel, recorrendo ao modo legado")
                    use_optimized = False
                    
            except ImportError as e:
                logger.error(f"DIAGNOSTICO: Falha ao importar enable_optimized_import: {e}")
                logger.error(f"DIAGNOSTICO: Tipo do erro: {type(e).__name__}")
                logger.error(f"DIAGNOSTICO: Modulo que causou o erro: {getattr(e, 'name', 'desconhecido')}")
                logger.warning("Modo otimizado nao disponivel, recorrendo ao modo legado")
                use_optimized = False
            except Exception as e:
                logger.error(f"DIAGNOSTICO: Erro ao executar enable_optimized_import: {e}")
                logger.error(f"DIAGNOSTICO: Tipo do erro: {type(e).__name__}")
                logger.warning("Modo otimizado falhou, recorrendo ao modo legado")
                use_optimized = False
        else:
            logger.info("DIAGNOSTICO: Usando modo LEGADO/DEBUG (--standard ativo)")

        logger.info(f"Iniciando processo de importacao (force_rescan={force_import}, optimized={use_optimized})...")
        logger.info("DIAGNOSTICO: Verificando implementacao externa de run_importer_logic")
        external_run = _load_external_run_importer(project_root)
        if external_run is not None:
            run_importer_logic = external_run  # noqa: PLW0603

        try:
            logger.info("DIAGNOSTICO: Executando run_importer_logic...")
            db_updated = run_importer_logic(force_import=force_import)
            logger.info("DIAGNOSTICO: Importacao de dados concluida. Resultado: db_updated=%s", db_updated)
        except Exception as e:
            logger.error(f"DIAGNOSTICO: Falha critica na importacao de dados: {e}")
            logger.error("DIAGNOSTICO: Este e o ponto mais critico do processo. Verifique:")
            logger.error("  1. Existencia e permissoes da pasta 'data'")
            logger.error("  2. Conexao com o banco de dados")
            logger.error("  3. Arquivos Excel na pasta de entrada")
            logger.error("  4. Memoria disponivel do sistema")
            raise

        # Desativar importacao otimizada apos uso
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
            logger.info("DIAGNOSTICO: Banco de dados foi atualizado. Verifique se os dados estao acessiveis.")
        else:
            logger.info("Nenhum novo ou modificado relatorio encontrado.")
            logger.info("DIAGNOSTICO: Nenhum novo relatorio encontrado. Isso pode ser normal ou indicar problemas.")
            logger.info("DIAGNOSTICO: Verifique se ha arquivos Excel na pasta de entrada e se eles contem dados validos.")

        # --- 4. Inicio da Interface ---
        # Respeita variaveis de ambiente para facilitar testes e integracao
        # Exemplos:
        #   SSA_DB_PATH=C:\\tmp\\test_ssas.db  SSA_TABLE_NAME=ssas  python main.py --log-level INFO
        db_path = os.environ.get('SSA_DB_PATH') or os.path.join(project_root, 'data', 'ssas.db')
        table_name = os.environ.get('SSA_TABLE_NAME') or 'ssa_table'
        logger.info(f"Usando base: {db_path} (tabela: {table_name})")
        logger.info("DIAGNOSTICO: Verificando acesso ao banco de dados...")
        logger.info("DIAGNOSTICO: Caminho do banco: %s", db_path)
        logger.info("DIAGNOSTICO: Nome da tabela: %s", table_name)
        logger.info("DIAGNOSTICO: Verificando se o arquivo do banco existe...")
        if os.path.exists(db_path):
            logger.info("DIAGNOSTICO: Arquivo do banco encontrado.")
            file_size = os.path.getsize(db_path)
            logger.info("DIAGNOSTICO: Tamanho do arquivo do banco: %d bytes", file_size)
        else:
            logger.warning("DIAGNOSTICO: Arquivo do banco NAO encontrado. Isso pode indicar que a importacao falhou.")

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
                except Exception as e:
                    logger.warning(f"Falha ao fechar socket de instancia unica: {e}")
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
