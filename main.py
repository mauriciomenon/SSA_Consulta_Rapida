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
    
    # LOGS DE DIAGNÓSTICO DE CONFIGURAÇÃO DE LOGGING
    print(f"DIAGNOSTICO: Iniciando configuração de logging em {project_root}")
    print(f"DIAGNOSTICO: use_robust_system = {use_robust_system}")
    print(f"DIAGNOSTICO: Nível console = {level_console}, Nível arquivo = {level_file}")
    
    if use_robust_system:
        # Usa o sistema de logging robusto
        robust_path = os.path.join(project_root, 'utils', 'robust_logging.py')
        print(f"DIAGNOSTICO: Verificando arquivo de logging robusto em: {robust_path}")
        print(f"DIAGNOSTICO: Arquivo existe: {os.path.exists(robust_path)}")
        
        # DIAGNÓSTICO DETALHADO: Verificação do módulo de logging robusto
        if os.path.exists(robust_path):
            file_stat = os.stat(robust_path)
            print(f"DIAGNOSTICO: Permissões do arquivo robust_logging.py: {oct(file_stat.st_mode)}")
            print(f"DIAGNOSTICO: Tamanho do arquivo robust_logging.py: {file_stat.st_size} bytes")
            
            # Verificar se utils está no sys.path
            utils_path = os.path.join(project_root, 'utils')
            print(f"DIAGNOSTICO: Diretório utils no sys.path: {utils_path in sys.path}")
            
            # Listar arquivos no diretório utils
            if os.path.exists(utils_path):
                print(f"DIAGNOSTICO: Arquivos em utils/: {os.listdir(utils_path)}")
        
        try:
            print("DIAGNOSTICO: Tentando importar utils.robust_logging...")
            
            # Verificar se o módulo pode ser encontrado
            import importlib.util
            spec = importlib.util.find_spec('utils.robust_logging')
            print(f"DIAGNOSTICO: Espec para 'utils.robust_logging': {spec}")
            
            if spec:
                print(f"DIAGNOSTICO: Localização do módulo utils.robust_logging: {spec.origin}")
            
            from utils.robust_logging import setup_logging
            print("DIAGNOSTICO: Importação de utils.robust_logging bem-sucedida")
            
            # Verificar se a função existe
            print(f"DIAGNOSTICO: setup_logging é callable: {callable(setup_logging)}")
            
            setup_logging()
            logger.info("Sistema de logging robusto inicializado", extra={'component': 'main'})
            print("DIAGNOSTICO: Sistema de logging robusto configurado com sucesso")
            _logging_configured = True
            return
        except ImportError as e:
            print(f"Sistema robusto indisponível, usando legado: {e}")
            print(f"DIAGNOSTICO: Tipo do erro: {type(e).__name__}")
            print(f"DIAGNOSTICO: Módulo que causou o erro: {getattr(e, 'name', 'desconhecido')}")
            print(f"DIAGNOSTICO: Detalhes do erro: {e}")
            
            # Verificar dependências do logging robusto
            print("DIAGNOSTICO: Verificando dependências do logging robusto...")
            try:
                import json
                print("DIAGNOSTICO: json disponível")
            except ImportError as je:
                print(f"DIAGNOSTICO: json NÃO disponível: {je}")
                
            try:
                import threading
                print("DIAGNOSTICO: threading disponível")
            except ImportError as te:
                print(f"DIAGNOSTICO: threading NÃO disponível: {te}")
    
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
    # CORREÇÃO: Declarar project_root como global para evitar UnboundLocalError
    global project_root
    """
    # LOGS DE DIAGNÓSTICO DE IMPORTAÇÃO
    logger.info("DIAGNOSTICO: Iniciando função main()")
    
    # CORREÇÃO: Importar sys no início da função para evitar UnboundLocalError
    import sys
    
    # DIAGNÓSTICO: Verificar escopo da variável sys
    logger.info("DIAGNOSTICO: Verificando escopo da variável sys...")
    logger.info("DIAGNOSTICO: sys disponível no escopo global: %s", 'sys' in globals())
    logger.info("DIAGNOSTICO: sys disponível no escopo local: %s", 'sys' in locals())
    logger.info("DIAGNOSTICO: sys.argv disponível: %s", hasattr(sys, 'argv'))
    
    # Verificar se sys está no escopo global
    logger.info("DIAGNOSTICO: sys importado localmente: %s", hasattr(sys, 'argv'))
    
    # LOGS DE DIAGNÓSTICO DE ESTRUTURA DE DIRETÓRIOS
    logger.info("DIAGNOSTICO: Verificando estrutura de diretórios do projeto...")
    logger.info("DIAGNOSTICO: Diretório raiz do projeto: %s", project_root)
    logger.info("DIAGNOSTICO: sys.path atual: %s", sys.path)
    
    # Verificar estrutura de diretórios
    import os
    extracao_root = os.path.join(project_root, 'extracao')
    extracao_core = os.path.join(project_root, 'core', 'extracao')
    
    logger.info("DIAGNOSTICO: Diretório extracao (raiz): %s", extracao_root)
    logger.info("DIAGNOSTICO: Diretório extracao (core): %s", extracao_core)
    logger.info("DIAGNOSTICO: Diretório extracao (raiz) existe: %s", os.path.exists(extracao_root))
    logger.info("DIAGNOSTICO: Diretório extracao (core) existe: %s", os.path.exists(extracao_core))
    
    # Listar conteúdo dos diretórios
    if os.path.exists(extracao_root):
        logger.info("DIAGNOSTICO: Conteúdo de extracao (raiz): %s", os.listdir(extracao_root))
    if os.path.exists(extracao_core):
        logger.info("DIAGNOSTICO: Conteúdo de extracao (core): %s", os.listdir(extracao_core))
    
    # Verificar arquivo extractor.py em ambos os locais
    extractor_root = os.path.join(extracao_root, 'extractor.py')
    extractor_core = os.path.join(extracao_core, 'extractor.py')
    
    logger.info("DIAGNOSTICO: Arquivo extractor.py (raiz): %s", extractor_root)
    logger.info("DIAGNOSTICO: Arquivo extractor.py (core): %s", extractor_core)
    logger.info("DIAGNOSTICO: Arquivo extractor.py (raiz) existe: %s", os.path.exists(extractor_root))
    logger.info("DIAGNOSTICO: Arquivo extractor.py (core) existe: %s", os.path.exists(extractor_core))
    
    # Verificar permissões
    if os.path.exists(extractor_root):
        logger.info("DIAGNOSTICO: Permissões do arquivo extractor.py (raiz): %s", oct(os.stat(extractor_root).st_mode))
    if os.path.exists(extractor_core):
        logger.info("DIAGNOSTICO: Permissões do arquivo extractor.py (core): %s", oct(os.stat(extractor_core).st_mode))
    
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
    # LOGS DE DIAGNÓSTICO DE ARGUMENTOS
    logger.info("DIAGNOSTICO: Processando argumentos de linha de comando")
    logger.info("DIAGNOSTICO: cli_args fornecido: %s", cli_args is not None)
    logger.info("DIAGNOSTICO: sys.argv disponível: %s", hasattr(sys, 'argv'))
    
    if hasattr(sys, 'argv'):
        logger.info("DIAGNOSTICO: sys.argv[1:]: %s", sys.argv[1:])
    else:
        logger.error("DIAGNOSTICO: sys.argv não está disponível!")
    
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
        # Imports dinâmicos para evitar problemas
        try:
            logger.info("DIAGNOSTICO: Tentando importar módulos...")
            
            # Testar importação individualmente
            try:
                from core.app_logic import run_importer_logic
                logger.info("DIAGNOSTICO: Importação de core.app_logic bem sucedida")
            except ImportError as e:
                logger.error("DIAGNOSTICO: Falha ao importar core.app_logic: %s", e)
                
            try:
                from core.config_manager import ensure_default_settings
                logger.info("DIAGNOSTICO: Importação de core.config_manager bem sucedida")
            except ImportError as e:
                logger.error("DIAGNOSTICO: Falha ao importar core.config_manager: %s", e)
                
            try:
                from interface.cli import start_cli_loop
                logger.info("DIAGNOSTICO: Importação de interface.cli bem sucedida")
            except ImportError as e:
                logger.error("DIAGNOSTICO: Falha ao importar interface.cli: %s", e)
                
            try:
                from utils import setup_project_structure
                logger.info("DIAGNOSTICO: Importação de utils.setup_project_structure bem sucedida")
            except ImportError as e:
                logger.error("DIAGNOSTICO: Falha ao importar utils.setup_project_structure: %s", e)
                
            # Tentar importar todos juntos
            from core.app_logic import run_importer_logic
            from core.config_manager import ensure_default_settings
            from interface.cli import start_cli_loop
            from utils import setup_project_structure
            logger.info("DIAGNOSTICO: Todas as importações bem sucedidas")
            
        except ImportError as e:
            logger.error("DIAGNOSTICO: Falha crítica nas importações: %s", e)
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
        logger.info("DIAGNOSTICO: Iniciando preparação do ambiente...")
        
        # LOGS DE DIAGNÓSTICO ADICIONAIS
        logger.info("DIAGNOSTICO: Caminho do projeto: %s", project_root)
        logger.info("DIAGNOSTICO: Diretório atual: %s", os.getcwd())
        logger.info("DIAGNOSTICO: sys.path: %s", sys.path)
        
        # Verificar diretórios importantes
        data_dir = os.path.join(project_root, 'data')
        docs_dir = os.path.join(project_root, 'docs_entrada')
        config_dir = os.path.join(project_root, 'config')
        core_dir = os.path.join(project_root, 'core')
        armazenamento_dir = os.path.join(core_dir, 'armazenamento')
        extracao_dir = os.path.join(core_dir, 'extracao')
        
        logger.info("DIAGNOSTICO: Verificando diretórios...")
        logger.info("DIAGNOSTICO: data_dir existe: %s", os.path.exists(data_dir))
        logger.info("DIAGNOSTICO: docs_dir existe: %s", os.path.exists(docs_dir))
        logger.info("DIAGNOSTICO: config_dir existe: %s", os.path.exists(config_dir))
        logger.info("DIAGNOSTICO: core_dir existe: %s", os.path.exists(core_dir))
        logger.info("DIAGNOSTICO: armazenamento_dir existe: %s", os.path.exists(armazenamento_dir))
        logger.info("DIAGNOSTICO: extracao_dir existe: %s", os.path.exists(extracao_dir))
        
        # Listar arquivos nos diretórios importantes
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
        
        # Verificar arquivos específicos que causam problemas
        database_py = os.path.join(armazenamento_dir, 'database.py')
        extractor_py = os.path.join(extracao_dir, 'extractor.py')
        
        logger.info("DIAGNOSTICO: database.py existe: %s", os.path.exists(database_py))
        logger.info("DIAGNOSTICO: extractor.py existe: %s", os.path.exists(extractor_py))
        
        # Verificar arquivos alternativos
        database_optimized = os.path.join(armazenamento_dir, 'database_optimized.py')
        logger.info("DIAGNOSTICO: database_optimized.py existe: %s", os.path.exists(database_optimized))
        
        # Verificar arquivos de init nos diretórios
        armazenamento_init = os.path.join(armazenamento_dir, '__init__.py')
        extracao_init = os.path.join(extracao_dir, '__init__.py')
        
        logger.info("DIAGNOSTICO: armazenamento/__init__.py existe: %s", os.path.exists(armazenamento_init))
        logger.info("DIAGNOSTICO: extracao/__init__.py existe: %s", os.path.exists(extracao_init))
        
        # Verificar variáveis de ambiente importantes
        logger.info("DIAGNOSTICO: Variáveis de ambiente:")
        logger.info("DIAGNOSTICO: SSA_DB_PATH: %s", os.environ.get('SSA_DB_PATH'))
        logger.info("DIAGNOSTICO: SSA_TABLE_NAME: %s", os.environ.get('SSA_TABLE_NAME'))
        logger.info("DIAGNOSTICO: PYTHONPATH: %s", os.environ.get('PYTHONPATH'))
        
        setup_project_structure.setup_dirs()
        logger.info("Estrutura de pastas verificada.")
        logger.info("DIAGNOSTICO: Preparação do ambiente concluída com sucesso.")

        # --- 2. Configuração ---
        logger.debug("Garantindo configuracoes padrao...")
        logger.info("DIAGNOSTICO: Iniciando configuração do sistema...")
        try:
            ensure_default_settings()
            logger.debug("Configuracoes padrao verificadas.")
            logger.info("DIAGNOSTICO: Configuração do sistema concluída com sucesso.")
        except Exception as e:
            logger.error(f"DIAGNOSTICO: Falha na configuração do sistema: {e}")
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
            logger.info("DIAGNOSTICO: Tentando importar enable_optimized_import de armazenamento.database_optimized")
            
            # Testar caminho absoluto
            import sys
            import os
            current_project_root = project_root
            optimized_path = os.path.join(current_project_root, 'armazenamento', 'database_optimized.py')
            logger.info(f"DIAGNOSTICO: Caminho absoluto do módulo otimizado: {optimized_path}")
            logger.info(f"DIAGNOSTICO: Arquivo existe: {os.path.exists(optimized_path)}")
            
            # DIAGNÓSTICO DETALHADO: Verificação do módulo otimizado
            logger.info("DIAGNOSTICO: Verificando disponibilidade do modo otimizado...")
            
            # Verificar se o arquivo existe
            import os
            optimized_file_path = os.path.join(current_project_root, 'armazenamento', 'database_optimized.py')
            logger.info("DIAGNOSTICO: Caminho do arquivo otimizado: %s", optimized_file_path)
            logger.info("DIAGNOSTICO: Arquivo otimizado existe: %s", os.path.exists(optimized_file_path))
            
            if os.path.exists(optimized_file_path):
                # Verificar permissões
                file_stat = os.stat(optimized_file_path)
                logger.info("DIAGNOSTICO: Permissões do arquivo otimizado: %s", oct(file_stat.st_mode))
                logger.info("DIAGNOSTICO: Tamanho do arquivo otimizado: %d bytes", file_stat.st_size)
                
                # Verificar se o diretório armazenamento está no sys.path
                armazenamento_path = os.path.join(current_project_root, 'armazenamento')
                logger.info("DIAGNOSTICO: Diretório armazenamento no sys.path: %s", armazenamento_path in sys.path)
                
                # Listar arquivos no diretório armazenamento
                if os.path.exists(armazenamento_path):
                    logger.info("DIAGNOSTICO: Arquivos em armazenamento/: %s", os.listdir(armazenamento_path))
            
            try:
                # Tentar importar o módulo completo primeiro
                logger.info("DIAGNOSTICO: Tentando importar armazenamento.database_optimized...")
                import armazenamento.database_optimized
                logger.info("DIAGNOSTICO: Importação do módulo completo bem-sucedida")
                
                # Verificar se a função existe no módulo
                logger.info("DIAGNOSTICO: Verificando se enable_optimized_import existe no módulo...")
                if hasattr(armazenamento.database_optimized, 'enable_optimized_import'):
                    logger.info("DIAGNOSTICO: Função enable_optimized_import encontrada")
                    
                    from armazenamento.database_optimized import enable_optimized_import
                    logger.info("DIAGNOSTICO: Importação de enable_optimized_import bem-sucedida")
                    
                    enable_optimized_import()
                    logger.info("DIAGNOSTICO: enable_optimized_import() executado com sucesso")
                else:
                    logger.error("DIAGNOSTICO: Função enable_optimized_import NÃO encontrada no módulo")
                    logger.warning("Modo otimizado não disponível, recorrendo ao modo legado")
                    use_optimized = False
                    
            except ImportError as e:
                logger.error(f"DIAGNOSTICO: Falha ao importar enable_optimized_import: {e}")
                logger.error(f"DIAGNOSTICO: Tipo do erro: {type(e).__name__}")
                logger.error(f"DIAGNOSTICO: Módulo que causou o erro: {getattr(e, 'name', 'desconhecido')}")
                logger.warning("Modo otimizado não disponível, recorrendo ao modo legado")
                use_optimized = False
            except Exception as e:
                logger.error(f"DIAGNOSTICO: Erro ao executar enable_optimized_import: {e}")
                logger.error(f"DIAGNOSTICO: Tipo do erro: {type(e).__name__}")
                logger.warning("Modo otimizado falhou, recorrendo ao modo legado")
                use_optimized = False
        else:
            logger.info("⚠️  Usando modo LEGADO/DEBUG (--standard ativo)")

        logger.info(f"Iniciando processo de importacao (force_rescan={force_import}, optimized={use_optimized})...")
        logger.info("DIAGNOSTICO: Iniciando importação de dados...")
        logger.info("DIAGNOSTICO: Tentando importar run_importer_logic de core.extracao.extractor")
        
        # LOGS DETALHADOS PARA DIAGNÓSTICO DE IMPORTAÇÃO
        logger.info("DIAGNOSTICO: sys.path atual: %s", sys.path)
        logger.info("DIAGNOSTICO: Diretório de trabalho atual: %s", os.getcwd())
        logger.info("DIAGNOSTICO: Diretório raiz do projeto: %s", project_root)
        
        # Verificar se o diretório core existe
        core_path = os.path.join(project_root, 'core')
        logger.info("DIAGNOSTICO: Caminho do diretório core: %s", core_path)
        logger.info("DIAGNOSTICO: Diretório core existe: %s", os.path.exists(core_path))
        
        # Verificar se o diretório extracao existe (NOVA VERIFICAÇÃO: nível raiz)
        extracao_root_path = os.path.join(project_root, 'extracao')
        logger.info("DIAGNOSTICO: Caminho do diretório extracao (raiz): %s", extracao_root_path)
        logger.info("DIAGNOSTICO: Diretório extracao (raiz) existe: %s", os.path.exists(extracao_root_path))
        
        # Verificar se o diretório extracao existe (core/extracao)
        extracao_path = os.path.join(core_path, 'extracao')
        logger.info("DIAGNOSTICO: Caminho do diretório extracao (core): %s", extracao_path)
        logger.info("DIAGNOSTICO: Diretório extracao (core) existe: %s", os.path.exists(extracao_path))
        
        # Verificar se o arquivo extractor.py existe (raiz)
        extractor_root_path = os.path.join(extracao_root_path, 'extractor.py')
        logger.info("DIAGNOSTICO: Caminho do arquivo extractor.py (raiz): %s", extractor_root_path)
        logger.info("DIAGNOSTICO: Arquivo extractor.py (raiz) existe: %s", os.path.exists(extractor_root_path))
        
        # Verificar se o arquivo extractor.py existe (core/extracao)
        extractor_path = os.path.join(extracao_path, 'extractor.py')
        logger.info("DIAGNOSTICO: Caminho do arquivo extractor.py (core): %s", extractor_path)
        logger.info("DIAGNOSTICO: Arquivo extractor.py (core) existe: %s", os.path.exists(extractor_path))
        
        # Listar arquivos nos diretórios relevantes
        if os.path.exists(extracao_root_path):
            logger.info("DIAGNOSTICO: Arquivos no diretório extracao (raiz): %s", os.listdir(extracao_root_path))
        if os.path.exists(extracao_path):
            logger.info("DIAGNOSTICO: Arquivos no diretório extracao (core): %s", os.listdir(extracao_path))
        
        # Testar importações diferentes
        logger.info("DIAGNOSTICO: Testando importações...")
        logger.info("DIAGNOSTICO: sys.path atual antes das tentativas: %s", sys.path)
        
        # Testar importação do nível raiz
        logger.info("DIAGNOSTICO: Tentando importar 'from extracao import extractor'...")
        try:
            # Limpar sys.path para evitar conflitos
            original_sys_path = sys.path.copy()
            sys.path.insert(0, project_root)
            logger.info("DIAGNOSTICO: sys.path modificado: %s", sys.path)
            
            # DIAGNÓSTICO DETALHADO: Verificação do módulo extracao
            logger.info("DIAGNOSTICO: Verificação detalhada do módulo extracao...")
            
            # Verificar se o diretório extracao existe
            extracao_dir = os.path.join(project_root, 'extracao')
            logger.info("DIAGNOSTICO: Diretório extracao: %s", extracao_dir)
            logger.info("DIAGNOSTICO: Diretório extracao existe: %s", os.path.exists(extracao_dir))
            
            if os.path.exists(extracao_dir):
                # Listar arquivos no diretório
                logger.info("DIAGNOSTICO: Arquivos em extracao/: %s", os.listdir(extracao_dir))
                
                # Verificar arquivo extractor.py
                extractor_file = os.path.join(extracao_dir, 'extractor.py')
                logger.info("DIAGNOSTICO: Arquivo extractor.py: %s", extractor_file)
                logger.info("DIAGNOSTICO: Arquivo extractor.py existe: %s", os.path.exists(extractor_file))
                
                if os.path.exists(extractor_file):
                    # Verificar permissões e tamanho
                    file_stat = os.stat(extractor_file)
                    logger.info("DIAGNOSTICO: Permissões do extractor.py: %s", oct(file_stat.st_mode))
                    logger.info("DIAGNOSTICO: Tamanho do extractor.py: %d bytes", file_stat.st_size)
                    
                    # Verificar arquivo __init__.py
                    init_file = os.path.join(extracao_dir, '__init__.py')
                    logger.info("DIAGNOSTICO: Arquivo __init__.py: %s", init_file)
                    logger.info("DIAGNOSTICO: Arquivo __init__.py existe: %s", os.path.exists(init_file))
            
            # Testar se o módulo pode ser encontrado
            import importlib.util
            spec = importlib.util.find_spec('extracao')
            logger.info("DIAGNOSTICO: Espec para 'extracao': %s", spec)
            
            if spec:
                logger.info("DIAGNOSTICO: Localização do módulo extracao: %s", spec.origin)
                logger.info("DIAGNOSTICO: Caminho do spec: %s", spec.submodule_search_locations if hasattr(spec, 'submodule_search_locations') else 'N/A')
            else:
                logger.error("DIAGNOSTICO: Módulo 'extracao' não encontrado pelo importlib")
                
                # Tentar busca manual
                logger.info("DIAGNOSTICO: Tentando busca manual do módulo...")
                for path in sys.path:
                    candidate = os.path.join(path, 'extracao')
                    if os.path.isdir(candidate):
                        logger.info("DIAGNOSTICO: Candidato encontrado em: %s", candidate)
                        if os.path.exists(os.path.join(candidate, '__init__.py')):
                            logger.info("DIAGNOSTICO: __init__.py encontrado em: %s", candidate)
            
            # Tentar importação passo a passo
            logger.info("DIAGNOSTICO: Tentando importar o módulo extracao...")
            import extracao
            logger.info("DIAGNOSTICO: Importação do módulo extracao bem-sucedida")
            logger.info("DIAGNOSTICO: Atributos do módulo extracao: %s", dir(extracao))
            
            # Verificar se extractor existe no módulo
            if hasattr(extracao, 'extractor'):
                logger.info("DIAGNOSTICO: Submódulo extractor encontrado em extracao")
                logger.info("DIAGNOSTICO: Atributos de extracao.extractor: %s", dir(extracao.extractor))
                
                # Verificar se run_importer_logic existe
                if hasattr(extracao.extractor, 'run_importer_logic'):
                    logger.info("DIAGNOSTICO: Função run_importer_logic encontrada")
                    run_importer_logic = extracao.extractor.run_importer_logic
                else:
                    logger.error("DIAGNOSTICO: Função run_importer_logic NÃO encontrada em extracao.extractor")
            else:
                logger.error("DIAGNOSTICO: Submódulo extractor NÃO encontrado em extracao")
                
            from extracao import extractor
            logger.info("DIAGNOSTICO: Importação de 'from extracao import extractor' bem-sucedida")
            
        except ImportError as e:
            logger.error(f"DIAGNOSTICO: Falha ao importar 'from extracao import extractor': {e}")
            logger.error(f"DIAGNOSTICO: Tipo do erro: {type(e).__name__}")
            logger.error(f"DIAGNOSTICO: Módulo que causou o erro: {getattr(e, 'name', 'desconhecido')}")
            logger.error(f"DIAGNOSTICO: Caminho do módulo: {getattr(e, 'path', 'desconhecido')}")
            logger.error(f"DIAGNOSTICO: Detalhes completos: {e}")
            
            # Verificar se há problemas com dependências
            logger.error("DIAGNOSTICO: Verificando possíveis problemas de dependências...")
            try:
                import pandas
                logger.info("DIAGNOSTICO: pandas disponível: %s", pandas.__version__)
            except ImportError as pe:
                logger.error("DIAGNOSTICO: pandas NÃO disponível: %s", pe)
                
            try:
                import openpyxl
                logger.info("DIAGNOSTICO: openpyxl disponível: %s", openpyxl.__version__)
            except ImportError as oe:
                logger.error("DIAGNOSTICO: openpyxl NÃO disponível: %s", oe)
        
        # Restaurar sys.path
        sys.path = original_sys_path
        
        # Testar importação do core/extracao (se existir)
        if os.path.exists(extracao_path):
            logger.info("DIAGNOSTICO: Tentando importar 'from core.extracao.extractor import run_importer_logic'...")
            try:
                # Limpar sys.path novamente
                original_sys_path = sys.path.copy()
                sys.path.insert(0, project_root)
                
                spec = importlib.util.find_spec('core.extracao.extractor')
                logger.info("DIAGNOSTICO: Espec para 'core.extracao.extractor': %s", spec)
                
                if spec:
                    logger.info("DIAGNOSTICO: Localização do módulo core.extracao.extractor: %s", spec.origin)
                
                from core.extracao.extractor import run_importer_logic
                logger.info("DIAGNOSTICO: Importação de 'from core.extracao.extractor import run_importer_logic' bem-sucedida")
            except ImportError as e:
                logger.error(f"DIAGNOSTICO: Falha ao importar 'from core.extracao.extractor import run_importer_logic': {e}")
                logger.error(f"DIAGNOSTICO: Tipo do erro: {type(e).__name__}")
                logger.error(f"DIAGNOSTICO: Detalhes completos: {e}")
            finally:
                # Restaurar sys.path
                sys.path = original_sys_path
        else:
            logger.warning("DIAGNOSTICO: Diretório core/extracao não existe, pulando importação")
        
        # Se nenhuma importação funcionou, tentar importar diretamente
        logger.info("DIAGNOSTICO: Tentando importação direta do módulo extractor...")
        try:
            # Limpar sys.path
            original_sys_path = sys.path.copy()
            extracao_dir = os.path.join(project_root, 'extracao')
            sys.path.insert(0, extracao_dir)
            logger.info("DIAGNOSTICO: sys.path para importação direta: %s", sys.path)
            
            import extractor
            logger.info("DIAGNOSTICO: Importa��o direta do m�dulo extractor bem-sucedida")
            if hasattr(extractor, 'run_importer_logic'):
                run_importer_logic = extractor.run_importer_logic
                logger.info("DIAGNOSTICO: run_importer_logic obtido do m�dulo extractor")
            else:
                logger.error("DIAGNOSTICO: Fun��o run_importer_logic N�O encontrada em extractor; mantendo implementa��o de core.app_logic")
        except ImportError as e:
            logger.error(f"DIAGNOSTICO: Falha ao importar diretamente o módulo extractor: {e}")
            logger.error(f"DIAGNOSTICO: Tipo do erro: {type(e).__name__}")
            logger.error(f"DIAGNOSTICO: Detalhes completos: {e}")
            logger.error("DIAGNOSTICO: Este é um erro crítico - o módulo extractor não está disponível")
            logger.error("DIAGNOSTICO: Verifique se o arquivo extractor.py existe no diretório correto")
            logger.error("DIAGNOSTICO: Verifique se o diretório extracao existe")
            logger.error("DIAGNOSTICO: Verifique se o diretório core está no sys.path")
            logger.error("DIAGNOSTICO: Verifique se há arquivos .pyc corrompidos no diretório")
            raise
        finally:
            # Restaurar sys.path
            sys.path = original_sys_path
        
        try:
            logger.info("DIAGNOSTICO: Executando run_importer_logic...")
            db_updated = run_importer_logic(force_import=force_import)
            logger.info("DIAGNOSTICO: Importação de dados concluída. Resultado: db_updated=%s", db_updated)
        except Exception as e:
            logger.error(f"DIAGNOSTICO: Falha crítica na importação de dados: {e}")
            logger.error("DIAGNOSTICO: Este é o ponto mais crítico do processo. Verifique:")
            logger.error("  1. Existência e permissões da pasta 'data'")
            logger.error("  2. Conexão com o banco de dados")
            logger.error("  3. Arquivos Excel na pasta de entrada")
            logger.error("  4. Memória disponível do sistema")
            raise

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
            logger.info("DIAGNOSTICO: Banco de dados foi atualizado. Verifique se os dados estão acessíveis.")
        else:
            logger.info("Nenhum novo ou modificado relatorio encontrado.")
            logger.info("DIAGNOSTICO: Nenhum novo relatório encontrado. Isso pode ser normal ou indicar problemas.")
            logger.info("DIAGNOSTICO: Verifique se há arquivos Excel na pasta de entrada e se eles contêm dados válidos.")

        # --- 4. Início da Interface ---
        # Respeita variáveis de ambiente para facilitar testes e integração
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
            logger.warning("DIAGNOSTICO: Arquivo do banco NÃO encontrado. Isso pode indicar que a importação falhou.")

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
                    logger.warning(f"Falha ao fechar socket de instância única: {e}")
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
