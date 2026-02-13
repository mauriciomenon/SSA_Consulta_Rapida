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
import subprocess
import sys
from logging.handlers import RotatingFileHandler
from typing import Optional

# CRITICAL FIX: PyOxidizer monkey patch for pandas delvewheel
# pandas._libs uses __file__ which is None in PyOxidizer causing crash
# This must be BEFORE any imports that use pandas
if getattr(sys, 'oxidized', False):
    import builtins
    _original_import = builtins.__import__
    def _patched_import(name, *args, **kwargs):
        module = _original_import(name, *args, **kwargs)
        if not hasattr(module, '__file__') or module.__file__ is None:
            # Set a dummy __file__ for modules that need it
            module.__file__ = os.path.join(os.path.dirname(sys.executable), f"{name.replace('.', os.sep)}.py")
        return module
    builtins.__import__ = _patched_import

# Suppress pandas FutureWarnings about chained assignment
import warnings
warnings.filterwarnings('ignore', category=FutureWarning)

logger = logging.getLogger("ssa")
# Logger level will be set by argument parsing - do not hardcode DEBUG
_logging_configured = False


class _ASCIIOnlyFilter(logging.Filter):
    """Remove qualquer caractere não ASCII das mensagens de log."""

    @staticmethod
    def _to_ascii(value):
        if isinstance(value, str):
            return value.encode('ascii', 'ignore').decode('ascii')
        return value

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = self._to_ascii(record.msg)
        if record.args:
            record.args = tuple(self._to_ascii(arg) for arg in record.args)
        if record.exc_text:
            record.exc_text = self._to_ascii(record.exc_text)
        return True


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


def _configure_logging(
    project_root: str,
    level_console: int = logging.WARNING,
    level_file: int = logging.INFO,
    use_robust_system: bool = True,
):
    """Configura sistema de logging (robusto ou legado) sem mensagens ruidosas."""
    global _logging_configured
    if _logging_configured:
        return

    if use_robust_system:
        try:
            from utils.robust_logging import setup_logging

            setup_logging()
            root_logger = logging.getLogger()
            root_logger.setLevel(min(level_console, level_file))
            for handler in root_logger.handlers:
                if isinstance(handler, logging.StreamHandler):
                    handler.setLevel(level_console)
                else:
                    handler.setLevel(level_file)
            _logging_configured = True
            return
        except Exception:  # noqa: BLE001
            sys.stderr.write(
                "Falha ao inicializar logging robusto; usando configuracao simplificada.\n"
            )

    logs_dir = os.path.join(project_root, "logs")
    os.makedirs(logs_dir, exist_ok=True)

    file_handler = RotatingFileHandler(
        filename=os.path.join(logs_dir, "ssa.log"),
        maxBytes=1_000_000,
        backupCount=1,
        encoding="utf-8",
    )
    file_handler.setLevel(level_file)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
    )

    console_handler = logging.StreamHandler()
    console_handler.setLevel(level_console)
    console_handler.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(min(level_console, level_file))
    ascii_filter = _ASCIIOnlyFilter()
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    for handler in root_logger.handlers:
        handler.addFilter(ascii_filter)

    logger.propagate = True
    _logging_configured = True


# Adiciona o diretorio raiz do projeto ao sys.path
def _get_project_root():
    """Retorna o diretorio raiz do projeto de forma robusta para diferentes builds."""
    # PyOxidizer
    if getattr(sys, 'oxidized', False):
        return os.path.dirname(sys.executable)
    # PyInstaller - CRITICAL FIX FOR ONEDRIVE/NETWORK PATHS
    # sys._MEIPASS eh pasta temporaria interna - NAO USAR
    # Precisamos do diretorio onde o usuario colocou o .exe
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return os.path.dirname(os.path.abspath(sys.executable))
    # Nuitka
    if '__compiled__' in globals():
        return os.path.dirname(sys.executable)
    # Desenvolvimento
    try:
        if __file__ is not None:
            return os.path.dirname(os.path.abspath(__file__))
        else:
            return os.getcwd()
    except (NameError, TypeError):
        return os.getcwd()

project_root = _get_project_root()
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
    logger.debug("Iniciando funcao main()")

    import sys
    import os

    logger.debug("Verificando escopo da variavel sys...")
    logger.debug("sys disponivel no escopo global: %s", 'sys' in globals())
    logger.debug("sys disponivel no escopo local: %s", 'sys' in locals())
    logger.debug("sys.argv disponivel: %s", hasattr(sys, 'argv'))

    logger.debug("Verificando estrutura de diretorios do projeto...")
    logger.debug("Diretorio raiz do projeto: %s", project_root)
    logger.debug("sys.path atual: %s", sys.path)

    extracao_root = os.path.join(project_root, 'extracao')
    extracao_core = os.path.join(project_root, 'core', 'extracao')

    logger.debug("Diretorio extracao (raiz): %s", extracao_root)
    logger.debug("Diretorio extracao (core): %s", extracao_core)
    logger.debug("Diretorio extracao (raiz) existe: %s", os.path.exists(extracao_root))
    logger.debug("Diretorio extracao (core) existe: %s", os.path.exists(extracao_core))

    if os.path.exists(extracao_root) and logger.isEnabledFor(logging.DEBUG):
        try:
            logger.debug("Conteudo de extracao (raiz): %s", os.listdir(extracao_root))
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao listar conteudo de extracao (raiz): %s", exc)
    if os.path.exists(extracao_core) and logger.isEnabledFor(logging.DEBUG):
        try:
            logger.debug("Conteudo de extracao (core): %s", os.listdir(extracao_core))
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao listar conteudo de extracao (core): %s", exc)

    extractor_root = os.path.join(extracao_root, 'extractor.py')
    extractor_core = os.path.join(extracao_core, 'extractor.py')

    logger.debug("Arquivo extractor.py (raiz): %s", extractor_root)
    logger.debug("Arquivo extractor.py (core): %s", extractor_core)
    logger.debug("Arquivo extractor.py (raiz) existe: %s", os.path.exists(extractor_root))
    logger.debug("Arquivo extractor.py (core) existe: %s", os.path.exists(extractor_core))

    if os.path.exists(extractor_root):
        logger.debug("Permissoes do arquivo extractor.py (raiz): %s", oct(os.stat(extractor_root).st_mode))
    if os.path.exists(extractor_core):
        logger.debug("Permissoes do arquivo extractor.py (core): %s", oct(os.stat(extractor_core).st_mode))

    APP_VERSION = get_app_version()

    # Fix para PyOxidizer: sys.argv[0] pode ser None
    prog_name = sys.argv[0] if sys.argv and sys.argv[0] else "SSA_Consulta_Rapida"
    parser = argparse.ArgumentParser(
        prog=prog_name,
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

    # Versao
    parser.add_argument(
        '--version', action='store_true',
        help='Exibe versao curta e encerra')

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
        '--skip-import',
        action='store_true',
        help='''Pula a importacao/verificacao inicial e inicia a GUI/CLI usando o banco existente.

        Use quando voce precisa abrir o app rapidamente e aceita trabalhar com dados possivelmente desatualizados.
        Para importar depois:
          - GUI: use o botao "Reescanear" (quando disponivel)
          - CLI: execute sem --skip-import (ou com --force-rescan, se necessario)
        '''
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
    logger.debug("Processando argumentos de linha de comando")
    logger.debug("cli_args fornecido: %s", cli_args is not None)
    logger.debug("sys.argv disponivel: %s", hasattr(sys, 'argv'))

    if hasattr(sys, 'argv'):
        logger.debug("sys.argv[1:]: %s", sys.argv[1:])
    else:
        logger.error("sys.argv nao esta disponivel!")

    raw_args = cli_args if cli_args is not None else sys.argv[1:]
    backfill_args: list[str] = []
    if '--' in raw_args:
        split_idx = raw_args.index('--')
        main_args = raw_args[:split_idx]
        backfill_args = raw_args[split_idx + 1:]
    else:
        main_args = raw_args

    logger.debug("raw_args: %s", raw_args)
    logger.debug("main_args: %s", main_args)
    logger.debug("backfill_args: %s", backfill_args)

    # Parse dos argumentos principais
    args = parser.parse_args(main_args)

    # --version: imprime e sai antes de qualquer outra acao
    if getattr(args, 'version', False):
        try:
            print(get_app_version())
        except Exception:
            print('0.0.0')
        return

    if getattr(args, "skip_import", False) and getattr(args, "force_rescan", False):
        parser.error("--skip-import nao pode ser combinado com --force-rescan/--rescan")

    # Configura logging
    _configure_logging(project_root)
    try:
        logger.setLevel(getattr(logging, args.log_level))
    except AttributeError:
        print(f"Nível de log inválido: {args.log_level}. Usando INFO.")
        logger.setLevel(logging.INFO)

    # Banner inicial
    print(f"Pesquisa Rapida de SSAs {APP_VERSION}")

    try:
        # Imports dinamicos para evitar problemas
        try:
            logger.debug("Tentando importar modulos...")

            # Testar importacao individualmente
            try:
                from core.app_logic import run_importer_logic
                logger.debug("Importacao de core.app_logic bem sucedida")
            except ImportError as e:
                logger.error("Falha ao importar core.app_logic: %s", e)

            try:
                from core.config_manager import ensure_default_settings
                logger.debug("Importacao de core.config_manager bem sucedida")
            except ImportError as e:
                logger.error("Falha ao importar core.config_manager: %s", e)

            try:
                from interface.cli import start_cli_loop
                logger.debug("Importacao de interface.cli bem sucedida")
            except ImportError as e:
                logger.error("Falha ao importar interface.cli: %s", e)

            try:
                from utils import setup_project_structure
                logger.debug("Importacao de utils.setup_project_structure bem sucedida")
            except ImportError as e:
                logger.error("Falha ao importar utils.setup_project_structure: %s", e)

            # Tentar importar todos juntos
            from core.app_logic import run_importer_logic
            from core.config_manager import ensure_default_settings
            from interface.cli import start_cli_loop
            from utils import setup_project_structure
            logger.debug("Todas as importacoes bem sucedidas")

        except ImportError as e:
            logger.error("Falha critica nas importacoes: %s", e)
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
        logger.debug("Iniciando preparacao do ambiente...")
        logger.debug("Caminho do projeto: %s", project_root)
        logger.debug("Diretorio atual: %s", os.getcwd())
        logger.debug("sys.path: %s", sys.path)

        # Verificar diretorios importantes
        data_dir = os.path.join(project_root, 'data')
        docs_dir = os.path.join(project_root, 'docs_entrada')
        config_dir = os.path.join(project_root, 'config')
        core_dir = os.path.join(project_root, 'core')
        armazenamento_dir = os.path.join(core_dir, 'armazenamento')
        extracao_dir = os.path.join(core_dir, 'extracao')

        logger.debug("Verificando diretorios...")
        logger.debug("data_dir existe: %s", os.path.exists(data_dir))
        logger.debug("docs_dir existe: %s", os.path.exists(docs_dir))
        logger.debug("config_dir existe: %s", os.path.exists(config_dir))
        logger.debug("core_dir existe: %s", os.path.exists(core_dir))
        logger.debug("armazenamento_dir existe: %s", os.path.exists(armazenamento_dir))
        logger.debug("extracao_dir existe: %s", os.path.exists(extracao_dir))

        # Listar arquivos nos diretorios importantes
        if logger.isEnabledFor(logging.DEBUG):
            if os.path.exists(data_dir):
                try:
                    logger.debug("Arquivos em data/: %s", os.listdir(data_dir))
                except Exception as exc:  # noqa: BLE001
                    logger.debug("Falha ao listar data/: %s", exc)
            if os.path.exists(docs_dir):
                try:
                    logger.debug("Arquivos em docs_entrada/: %s", os.listdir(docs_dir))
                except Exception as exc:  # noqa: BLE001
                    logger.debug("Falha ao listar docs_entrada/: %s", exc)
            if os.path.exists(config_dir):
                try:
                    logger.debug("Arquivos em config/: %s", os.listdir(config_dir))
                except Exception as exc:  # noqa: BLE001
                    logger.debug("Falha ao listar config/: %s", exc)
            if os.path.exists(core_dir):
                try:
                    logger.debug("Arquivos em core/: %s", os.listdir(core_dir))
                except Exception as exc:  # noqa: BLE001
                    logger.debug("Falha ao listar core/: %s", exc)
            if os.path.exists(armazenamento_dir):
                try:
                    logger.debug("Arquivos em core/armazenamento/: %s", os.listdir(armazenamento_dir))
                except Exception as exc:  # noqa: BLE001
                    logger.debug("Falha ao listar core/armazenamento/: %s", exc)
            if os.path.exists(extracao_dir):
                try:
                    logger.debug("Arquivos em core/extracao/: %s", os.listdir(extracao_dir))
                except Exception as exc:  # noqa: BLE001
                    logger.debug("Falha ao listar core/extracao/: %s", exc)

        # Verificar arquivos especificos que causam problemas
        database_py = os.path.join(armazenamento_dir, 'database.py')
        extractor_py = os.path.join(extracao_dir, 'extractor.py')

        logger.debug("database.py existe: %s", os.path.exists(database_py))
        logger.debug("extractor.py existe: %s", os.path.exists(extractor_py))

        # Verificar arquivos alternativos
        database_optimized = os.path.join(armazenamento_dir, 'database_optimized.py')
        logger.debug("database_optimized.py existe: %s", os.path.exists(database_optimized))

        # Verificar arquivos de init nos diretorios
        armazenamento_init = os.path.join(armazenamento_dir, '__init__.py')
        extracao_init = os.path.join(extracao_dir, '__init__.py')

        logger.debug("armazenamento/__init__.py existe: %s", os.path.exists(armazenamento_init))
        logger.debug("extracao/__init__.py existe: %s", os.path.exists(extracao_init))

        # Verificar variaveis de ambiente importantes
        logger.debug("Variaveis de ambiente:")
        logger.debug("SSA_DB_PATH: %s", os.environ.get('SSA_DB_PATH'))
        logger.debug("SSA_TABLE_NAME: %s", os.environ.get('SSA_TABLE_NAME'))
        logger.debug("PYTHONPATH: %s", os.environ.get('PYTHONPATH'))

        setup_project_structure.setup_dirs()
        logger.info("Estrutura de pastas verificada.")
        logger.debug("Preparacao do ambiente concluida com sucesso.")

        # --- 2. Configuracao ---
        logger.debug("Garantindo configuracoes padrao...")
        logger.debug("Iniciando configuracao do sistema...")
        try:
            ensure_default_settings()
            logger.debug("Configuracoes padrao verificadas.")
            logger.debug("Configuracao do sistema concluida com sucesso.")
        except Exception as e:
            logger.exception("Falha na configuracao do sistema: %s", e)
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
        if getattr(args, "skip_import", False):
            logger.info("Pulando importacao/verificacao inicial (--skip-import).")
            db_updated = False
        else:
            # Determina se a reimportacao e forcada e se deve usar versao otimizada
            force_import = args.force_rescan

            # MUDANCA: Modo otimizado agora e PADRAO (exceto se --standard for usado)
            use_optimized = not args.standard

            # Aviso de depreciacao se --optimized for usado
            if args.optimized:
                logger.warning("  Flag --optimized e deprecated: modo otimizado ja e padrao. Use --standard para modo legado.")

            # Ativar importacao otimizada (agora padrao)
            optimized_enabled = False
            if use_optimized:
                logger.info("Modo de importacao OTIMIZADA ativo (padrao)")
                logger.debug("Tentando importar enable_optimized_import de armazenamento.database_optimized")

                # Testar caminho absoluto
                import sys
                import os
                current_project_root = project_root
                optimized_path = os.path.join(current_project_root, 'armazenamento', 'database_optimized.py')
                logger.debug("Caminho absoluto do modulo otimizado: %s", optimized_path)
                logger.debug("Arquivo otimizado presente: %s", os.path.exists(optimized_path))

                logger.debug("Verificando disponibilidade do modo otimizado...")

                # Verificar se o arquivo existe
                import os
                optimized_file_path = os.path.join(current_project_root, 'armazenamento', 'database_optimized.py')
                logger.debug("Caminho do arquivo otimizado: %s", optimized_file_path)
                logger.debug("Arquivo otimizado existe: %s", os.path.exists(optimized_file_path))

                if os.path.exists(optimized_file_path):
                    file_stat = os.stat(optimized_file_path)
                    logger.debug("Permissoes do arquivo otimizado: %s", oct(file_stat.st_mode))
                    logger.debug("Tamanho do arquivo otimizado: %d bytes", file_stat.st_size)

                    armazenamento_path = os.path.join(current_project_root, 'armazenamento')
                    logger.debug("Diretorio armazenamento no sys.path: %s", armazenamento_path in sys.path)

                    if os.path.exists(armazenamento_path) and logger.isEnabledFor(logging.DEBUG):
                        try:
                            logger.debug("Arquivos em armazenamento/: %s", os.listdir(armazenamento_path))
                        except Exception as exc:  # noqa: BLE001
                            logger.debug("Falha ao listar armazenamento/: %s", exc)

                try:
                    # Tentar importar o modulo completo primeiro
                    logger.debug("Tentando importar armazenamento.database_optimized...")
                    import armazenamento.database_optimized
                    logger.debug("Importacao do modulo completo bem-sucedida")

                    # Verificar se a funcao existe no modulo
                    logger.debug("Verificando se enable_optimized_import existe no modulo...")
                    if hasattr(armazenamento.database_optimized, 'enable_optimized_import'):
                        logger.debug("Funcao enable_optimized_import encontrada")

                        from armazenamento.database_optimized import enable_optimized_import
                        logger.debug("Importacao de enable_optimized_import bem-sucedida")

                        enable_optimized_import()
                        optimized_enabled = True
                        logger.debug("enable_optimized_import() executado com sucesso")
                    else:
                        logger.error("Funcao enable_optimized_import NAO encontrada no modulo")
                        logger.warning("Modo otimizado nao disponivel, recorrendo ao modo legado")
                        use_optimized = False

                except ImportError as e:
                    logger.error("Falha ao importar enable_optimized_import: %s", e)
                    logger.debug("Tipo do erro: %s", type(e).__name__)
                    logger.debug("Modulo associado: %s", getattr(e, 'name', 'desconhecido'))
                    logger.warning("Modo otimizado nao disponivel, recorrendo ao modo legado")
                    use_optimized = False
                except Exception as e:
                    logger.error("Erro ao executar enable_optimized_import: %s", e)
                    logger.debug("Tipo do erro: %s", type(e).__name__)
                    logger.warning("Modo otimizado falhou, recorrendo ao modo legado")
                    use_optimized = False
            else:
                logger.debug("Usando modo LEGADO/DEBUG (--standard ativo)")

            logger.info(f"Iniciando processo de importacao (force_rescan={force_import}, optimized={use_optimized})...")

            try:
                logger.debug("Executando run_importer_logic...")
                db_updated = run_importer_logic(force_import=force_import)
                logger.debug("Importacao de dados concluida. Resultado: db_updated=%s", db_updated)
            except Exception as e:
                logger.error("Falha critica na importacao de dados: %s", e)
                logger.error("Este e o ponto mais critico do processo. Verifique:")
                logger.error("  1. Existencia e permissoes da pasta 'data'")
                logger.error("  2. Conexao com o banco de dados")
                logger.error("  3. Arquivos Excel na pasta de entrada")
                logger.error("  4. Memoria disponivel do sistema")
                raise

            # Desativar importacao otimizada apos uso
            if optimized_enabled:
                try:
                    from armazenamento.database_optimized import disable_optimized_import
                    disable_optimized_import()
                except ImportError:
                    pass
                except Exception as e:
                    logger.warning(f"Falha ao desativar modo otimizado: {e}")

            if db_updated:
                logger.info("Banco de dados atualizado com sucesso.")
                logger.debug("Banco de dados foi atualizado. Verifique se os dados estao acessiveis.")
            else:
                logger.info("Nenhum novo ou modificado relatorio encontrado.")
                logger.debug("Nenhum novo relatorio encontrado. Isso pode ser normal ou indicar problemas.")
                logger.debug("Verifique se ha arquivos Excel na pasta de entrada e se eles contem dados validos.")

        # --- 4. Inicio da Interface ---
        # Respeita variaveis de ambiente para facilitar testes e integracao
        # Exemplos:
        #   SSA_DB_PATH=C:\\tmp\\test_ssas.db  SSA_TABLE_NAME=ssas  python main.py --log-level INFO
        db_path = os.environ.get('SSA_DB_PATH') or os.path.join(project_root, 'data', 'ssas.db')
        table_name = os.environ.get('SSA_TABLE_NAME') or 'ssa_table'
        logger.info(f"Usando base: {db_path} (tabela: {table_name})")
        logger.debug("Verificando acesso ao banco de dados...")
        logger.debug("Caminho do banco: %s", db_path)
        logger.debug("Nome da tabela: %s", table_name)
        logger.debug("Verificando se o arquivo do banco existe...")
        if os.path.exists(db_path):
            logger.debug("Arquivo do banco encontrado.")
            file_size = os.path.getsize(db_path)
            logger.debug("Tamanho do arquivo do banco: %d bytes", file_size)
        else:
            logger.debug("Arquivo do banco NAO encontrado. Isso pode indicar que a importacao falhou.")

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
                # Permite multiplas janelas da GUI
                # O SQLite tem seus proprios mecanismos de lock
                app = QApplication(sys.argv)
                window = SSAMainWindow()
                window.show()  # type: ignore[attr-defined]
                # Executa o loop de eventos
                app.exec()
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
