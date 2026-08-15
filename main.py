#!/usr/bin/env python3
# main.py
"""
Ponto de entrada da aplicacao de Consulta Rapida de SSAs.

Inicializa logging, processa argumentos de linha de comando
e inicia a interface CLI ou GUI conforme as opcoes fornecidas.
"""

import argparse
import importlib
import itertools
import logging
import os
import sys
import warnings
from collections.abc import Mapping
from logging.handlers import RotatingFileHandler

from interface.cli_args import build_argument_parser
from interface.streamlit_launcher import launch_streamlit
from launchers.main_runtime import (
    _get_project_root,
    ensure_runtime_environment,
    patch_pyoxidizer_pandas,
)
from utils.ascii_sanitizer import sanitize_ascii_arg, sanitize_ascii_text

patch_pyoxidizer_pandas()

# Suppress pandas FutureWarnings about chained assignment
warnings.filterwarnings("ignore", category=FutureWarning)

logger: logging.Logger
# Logger level will be set by argument parsing - do not hardcode DEBUG
_logging_configured = False
_console_logging_level = logging.WARNING
_file_logging_level = logging.INFO


class _ASCIIOnlyFilter(logging.Filter):
    """Remove qualquer caractere nao ASCII das mensagens de log."""

    @staticmethod
    def _to_ascii(value):
        return sanitize_ascii_text(value)

    @classmethod
    def _to_ascii_arg(cls, value, depth: int = 0):
        return sanitize_ascii_arg(value, depth)

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = self._to_ascii(record.msg)
        if record.args:
            if (
                isinstance(record.args, tuple)
                and len(record.args) == 1
                and isinstance(record.args[0], Mapping)
                and "%(" in str(record.msg)
            ):
                record.args = {
                    str(key): self._to_ascii_arg(value)
                    for key, value in record.args[0].items()
                }
            elif isinstance(record.args, Mapping):
                record.args = self._to_ascii_arg(record.args)
            else:
                record.args = tuple(self._to_ascii_arg(arg) for arg in record.args)
        if record.exc_text:
            record.exc_text = self._to_ascii(record.exc_text)
        return True


def _configure_logging(
    project_root: str,
    level_console: int = logging.WARNING,
    level_file: int = logging.INFO,
    use_robust_system: bool = True,
):
    """Configura sistema de logging (robusto ou legado) sem mensagens ruidosas."""
    global _logging_configured, logger, _console_logging_level, _file_logging_level
    if _logging_configured:
        return
    _console_logging_level = level_console
    _file_logging_level = level_file

    if use_robust_system:
        try:
            from utils.robust_logging import get_robust_logger

            robust_logger = get_robust_logger()
            logger = robust_logger.get_logger("ssa", "main")
            root_logger = logging.getLogger()
            root_logger.setLevel(min(level_console, level_file))
            ascii_filter = _ASCIIOnlyFilter()
            for handler in root_logger.handlers:
                if isinstance(handler, logging.FileHandler):
                    handler.setLevel(level_file)
                elif isinstance(handler, logging.StreamHandler):
                    handler.setLevel(level_console)
                handler.addFilter(ascii_filter)
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
    console_handler.setFormatter(logging.Formatter("%(levelname)s - %(message)s"))

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(min(level_console, level_file))
    logger = logging.getLogger("ssa")
    ascii_filter = _ASCIIOnlyFilter()
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    for handler in root_logger.handlers:
        handler.addFilter(ascii_filter)

    logger.propagate = True
    _logging_configured = True


def _set_logging_level(
    level: int,
    *,
    level_console: int | None = None,
    level_file: int | None = None,
) -> None:
    global _console_logging_level, _file_logging_level
    if level_console is None:
        level_console = _console_logging_level
    else:
        _console_logging_level = level_console
    if level_file is None:
        level_file = _file_logging_level
    else:
        _file_logging_level = level_file
    root_logger = logging.getLogger()
    root_logger.setLevel(min(level_console, level_file, level))
    for handler in root_logger.handlers:
        if isinstance(handler, logging.FileHandler):
            handler.setLevel(level_file)
        elif isinstance(handler, logging.StreamHandler):
            handler.setLevel(level_console)
    logger.setLevel(level)


def _debug_listdir_preview(path: str, label: str, limit: int = 50) -> None:
    """Loga uma previsualizacao de conteudo de diretorio sem varrer tudo."""
    if not logger.isEnabledFor(logging.DEBUG):
        return
    if not os.path.exists(path):
        return
    try:
        entries = []
        with os.scandir(path) as it:
            for entry in itertools.islice(it, limit + 1):
                entries.append(entry.name)
        truncated = len(entries) > limit
        if truncated:
            entries = entries[:limit]
        suffix = " (preview truncado)" if truncated else ""
        logger.debug("Arquivos em %s: %s%s", label, entries, suffix)
    except Exception as exc:  # noqa: BLE001
        logger.debug("Falha ao listar %s: %s", label, exc)


project_root = _get_project_root()
runtime_root = project_root
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def _ensure_runtime_environment() -> str:
    """Prepare writable runtime once while keeping project_root trusted."""
    global runtime_root
    runtime_root = ensure_runtime_environment(project_root)
    return runtime_root


def get_app_version():
    """Obtem versao da aplicacao"""
    try:
        from utils.version import get_app_version as _get_version

        return _get_version()
    except ImportError:
        return "3.11+"
    except Exception as exc:  # noqa: BLE001
        logger.debug("Falha ao obter versao via utils.version: %s", exc)
        return "3.11+"



def _log_startup_diagnostics(active_runtime_root: str) -> None:
    if not logger.isEnabledFor(logging.DEBUG):
        return
    logger.debug("Iniciando funcao main()")
    logger.debug("Verificando escopo da variavel sys...")
    logger.debug("sys disponivel no escopo global: %s", "sys" in globals())
    logger.debug("sys disponivel no escopo local: %s", "sys" in locals())
    logger.debug("sys.argv disponivel: %s", hasattr(sys, "argv"))
    logger.debug("Verificando estrutura de diretorios do projeto...")
    logger.debug("Diretorio raiz do projeto: %s", project_root)
    logger.debug("Diretorio runtime da aplicacao: %s", active_runtime_root)
    logger.debug("sys.path atual: %s", sys.path)


def _load_runtime_dependencies():
    try:
        from core.app_logic import run_importer_logic
        from core.config_manager import ensure_default_settings
        from interface.cli import start_cli_loop
        from utils import setup_project_structure
    except ImportError as exc:
        logger.error("Falha critica nas importacoes: %s", exc)
        print(f" Aviso: Alguns modulos nao puderam ser carregados: {exc}")
        print("Sistema nao pode iniciar sem as dependencias obrigatorias.")
        return None
    logger.debug("Dependencias de runtime carregadas com sucesso")
    return (
        run_importer_logic,
        ensure_default_settings,
        start_cli_loop,
        setup_project_structure,
    )


def _run_maintenance_action(args: argparse.Namespace) -> bool:
    if args.reset_db:
        print("Resetando banco de dados...")
        try:
            from scripts_manutencao.gerenciar_banco import reset_database
        except ImportError:
            print("Modulo de gerenciamento de banco nao disponivel")
            return True
        reset_database()
        print("Banco de dados resetado com sucesso!")
        return True

    if args.clean_data:
        print("Limpando pasta data...")
        try:
            from scripts_manutencao.gerenciar_banco import (
                clean_old_backups,
                sanitize_data_folder,
            )
        except ImportError:
            print("Modulo de gerenciamento de banco nao disponivel")
            return True
        clean_old_backups()
        sanitize_data_folder()
        print("Limpeza concluida!")
        return True

    return False


def _log_environment_diagnostics(
    active_runtime_root: str,
    data_dir: str,
    docs_dir: str,
    config_dir: str,
    core_dir: str,
    armazenamento_dir: str,
    extracao_dir: str,
) -> None:
    if not logger.isEnabledFor(logging.DEBUG):
        return
    logger.debug("Verificando diretorios...")
    logger.debug("data_dir existe: %s", os.path.exists(data_dir))
    logger.debug("docs_dir existe: %s", os.path.exists(docs_dir))
    logger.debug("config_dir existe: %s", os.path.exists(config_dir))
    logger.debug("core_dir existe: %s", os.path.exists(core_dir))
    logger.debug("armazenamento_dir existe: %s", os.path.exists(armazenamento_dir))
    logger.debug("extracao_dir existe: %s", os.path.exists(extracao_dir))
    _debug_listdir_preview(data_dir, "data/")
    _debug_listdir_preview(docs_dir, "docs_entrada/")
    _debug_listdir_preview(config_dir, "config/")
    _debug_listdir_preview(core_dir, "core/")
    _debug_listdir_preview(armazenamento_dir, "armazenamento/")
    _debug_listdir_preview(extracao_dir, "core/extracao/")

    database_py = os.path.join(armazenamento_dir, "database.py")
    extractor_py = os.path.join(extracao_dir, "extractor.py")
    database_optimized = os.path.join(armazenamento_dir, "database_optimized.py")
    armazenamento_init = os.path.join(armazenamento_dir, "__init__.py")
    extracao_init = os.path.join(extracao_dir, "__init__.py")
    logger.debug("database.py existe: %s", os.path.exists(database_py))
    logger.debug("extractor.py existe: %s", os.path.exists(extractor_py))
    logger.debug("database_optimized.py existe: %s", os.path.exists(database_optimized))
    logger.debug("armazenamento/__init__.py existe: %s", os.path.exists(armazenamento_init))
    logger.debug("extracao/__init__.py existe: %s", os.path.exists(extracao_init))
    logger.debug("Variaveis de ambiente:")
    logger.debug("SSA_DB_PATH: %s", os.environ.get("SSA_DB_PATH"))
    logger.debug("SSA_TABLE_NAME: %s", os.environ.get("SSA_TABLE_NAME"))
    logger.debug("PYTHONPATH: %s", os.environ.get("PYTHONPATH"))


def _prepare_application_environment(active_runtime_root: str, setup_project_structure):
    logger.debug("Verificando/criando estrutura de pastas...")
    logger.debug("Iniciando preparacao do ambiente...")
    logger.debug("Caminho do projeto: %s", project_root)
    logger.debug("Diretorio atual: %s", os.getcwd())
    logger.debug("sys.path: %s", sys.path)

    data_dir = os.path.join(active_runtime_root, "data")
    docs_dir = os.path.join(active_runtime_root, "docs_entrada")
    config_dir = os.path.join(active_runtime_root, "config")
    core_dir = os.path.join(project_root, "core")
    armazenamento_dir = os.path.join(project_root, "armazenamento")
    extracao_dir = os.path.join(core_dir, "extracao")
    _log_environment_diagnostics(
        active_runtime_root,
        data_dir,
        docs_dir,
        config_dir,
        core_dir,
        armazenamento_dir,
        extracao_dir,
    )

    setup_project_structure.setup_dirs(base_path=active_runtime_root)
    logger.info("Estrutura de pastas verificada.")
    logger.debug("Preparacao do ambiente concluida com sucesso.")


def _ensure_default_configuration(ensure_default_settings) -> None:
    logger.debug("Garantindo configuracoes padrao...")
    logger.debug("Iniciando configuracao do sistema...")
    try:
        config_errors = ensure_default_settings(fail_fast=False)
    except Exception as exc:
        logger.exception("Falha na configuracao do sistema: %s", exc)
        raise
    if config_errors:
        logger.warning(
            "Configuracao padrao concluida com erros nao bloqueantes: %s",
            "; ".join(config_errors),
        )
    logger.debug("Configuracoes padrao verificadas.")
    logger.debug("Configuracao do sistema concluida com sucesso.")


def _run_backfill_action(args: argparse.Namespace, backfill_args: list[str]) -> None:
    if getattr(args, "acao", "processar") != "backfill":
        return
    logger.info(
        "Acao=backfill selecionada. Encaminhando argumentos ao backfill: %s",
        backfill_args,
    )
    try:
        from scripts.migracao.backfill_reprocessar import main as backfill_main
    except ModuleNotFoundError as exc:
        missing_name = getattr(exc, "name", "")
        expected_missing = {
            "scripts",
            "scripts.migracao",
            "scripts.migracao.backfill_reprocessar",
        }
        if missing_name not in expected_missing:
            raise
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        from scripts.migracao.backfill_reprocessar import main as backfill_main
    exit_code = backfill_main(backfill_args)
    logger.info("Backfill finalizado (exit_code=%s)", exit_code)
    sys.exit(exit_code)


def _enable_optimized_import():
    logger.info("Modo de importacao OTIMIZADA ativo (padrao)")
    logger.debug(
        "Tentando importar enable_optimized_import de armazenamento.database_optimized"
    )
    optimized_file_path = os.path.join(
        project_root, "armazenamento", "database_optimized.py"
    )
    logger.debug("Caminho do arquivo otimizado: %s", optimized_file_path)
    logger.debug("Arquivo otimizado existe: %s", os.path.exists(optimized_file_path))
    if os.path.exists(optimized_file_path) and logger.isEnabledFor(logging.DEBUG):
        file_stat = os.stat(optimized_file_path)
        logger.debug("Permissoes do arquivo otimizado: %s", oct(file_stat.st_mode))
        logger.debug("Tamanho do arquivo otimizado: %d bytes", file_stat.st_size)
        armazenamento_path = os.path.join(project_root, "armazenamento")
        logger.debug(
            "Diretorio armazenamento no sys.path: %s", armazenamento_path in sys.path
        )
        _debug_listdir_preview(armazenamento_path, "armazenamento/")

    try:
        optimized_module = importlib.import_module("armazenamento.database_optimized")
        enable_optimized_import = getattr(optimized_module, "enable_optimized_import")
        enable_optimized_import()
        logger.debug("enable_optimized_import() executado com sucesso")
        return optimized_module
    except ImportError as exc:
        message = (
            "Modo otimizado indisponivel: falha ao importar "
            "armazenamento.database_optimized"
        )
        logger.error("%s: %s", message, exc)
        raise RuntimeError(message) from exc
    except (RuntimeError, OSError, AttributeError, TypeError, ValueError) as exc:
        message = "Modo otimizado falhou ao inicializar"
        logger.error("%s: %s", message, exc)
        raise RuntimeError(message) from exc


def _disable_optimized_import(optimized_module) -> None:
    if optimized_module is None:
        return
    try:
        disable_optimized_import = getattr(optimized_module, "disable_optimized_import")
        disable_optimized_import()
    except AttributeError as exc:
        logger.debug("disable_optimized_import indisponivel no cleanup: %s", exc)
    except (RuntimeError, OSError, TypeError, ValueError) as exc:
        logger.warning("Falha ao desativar modo otimizado: %s", exc)


def _log_import_failure_context() -> None:
    logger.error("Este e o ponto mais critico do processo. Verifique:")
    logger.error("  1. Existencia e permissoes da pasta 'data'")
    logger.error("  2. Conexao com o banco de dados")
    logger.error("  3. Arquivos Excel na pasta de entrada")
    logger.error("  4. Memoria disponivel do sistema")


def _run_data_import(args: argparse.Namespace, run_importer_logic) -> bool:
    if not getattr(args, "force_rescan", False):
        logger.info(
            "Importacao automatica no startup desativada. "
            "Use --force-rescan/--rescan ou acione manualmente via GUI/CLI."
        )
        return False

    logger.info(
        "Full rescan solicitado via CLI; preparando recriacao do banco e reprocessamento completo."
    )
    force_import = args.force_rescan
    use_optimized = not args.standard
    if args.optimized and args.standard:
        logger.warning("Flags --optimized e --standard informadas juntas; usando modo standard.")

    optimized_module = None
    if use_optimized:
        optimized_module = _enable_optimized_import()
    else:
        logger.debug("Usando modo LEGADO/DEBUG (--standard ativo)")

    logger.info(
        "Iniciando processo de importacao (force_rescan=%s, optimized=%s)...",
        force_import,
        use_optimized,
    )
    try:
        db_updated = run_importer_logic(force_import=force_import)
        logger.debug("Importacao de dados concluida. Resultado: db_updated=%s", db_updated)
    except (RuntimeError, OSError, TypeError, ValueError, AttributeError) as exc:
        if use_optimized and force_import:
            logger.error(
                "Falha no modo otimizado durante --force-rescan; sem fallback legado automatico para evitar reprocessamento duplicado."
            )
        elif use_optimized:
            logger.error(
                "Falha no modo otimizado; sem fallback legado automatico para preservar desempenho e previsibilidade."
            )
        logger.error("Falha critica na importacao de dados: %s", exc)
        _log_import_failure_context()
        raise
    finally:
        _disable_optimized_import(optimized_module)

    if db_updated:
        logger.info("Banco de dados atualizado com sucesso.")
        logger.debug("Banco de dados foi atualizado. Verifique se os dados estao acessiveis.")
    else:
        logger.info("Nenhum novo ou modificado relatorio encontrado.")
        logger.debug("Nenhum novo relatorio encontrado. Isso pode ser normal ou indicar problemas.")
        logger.debug(
            "Verifique se ha arquivos Excel na pasta de entrada e se eles contem dados validos."
        )
    return db_updated


def _resolve_database_target(active_runtime_root: str) -> tuple[str, str]:
    db_path = os.environ.get("SSA_DB_PATH") or os.path.join(
        active_runtime_root, "data", "ssas.db"
    )
    table_name = os.environ.get("SSA_TABLE_NAME") or "ssa_table"
    logger.info("Usando base: %s (tabela: %s)", db_path, table_name)
    logger.debug("Caminho do banco: %s", db_path)
    logger.debug("Nome da tabela: %s", table_name)
    if os.path.exists(db_path):
        logger.debug("Arquivo do banco encontrado.")
        logger.debug("Tamanho do arquivo do banco: %d bytes", os.path.getsize(db_path))
    else:
        logger.debug(
            "Arquivo do banco NAO encontrado. Isso pode indicar que a importacao falhou."
        )
    return db_path, table_name


def _launch_gui(db_path: str, table_name: str, start_cli_loop, active_runtime_root: str) -> None:
    logger.info("Iniciando interface grafica (GUI)...")
    try:
        from gui.launcher import GuiOperationalError, launch_gui
    except ImportError as exc:
        logger.error("Falha ao iniciar GUI por dependencia/importacao: %s", exc)
        logger.info("Recuando para CLI.")
        start_cli_loop(db_path, table_name)
        return

    try:
        launch_gui(active_runtime_root, sys.argv, logger)
    except ImportError as exc:
        logger.error("Falha ao iniciar GUI por dependencia/importacao: %s", exc)
        logger.info("Recuando para CLI.")
        start_cli_loop(db_path, table_name)
    except GuiOperationalError as exc:
        logger.error("Falha operacional ao criar/mostrar janela da GUI: %s", exc)
        logger.info("Recuando para CLI.")
        start_cli_loop(db_path, table_name)


def _launch_interface(
    args: argparse.Namespace,
    db_path: str,
    table_name: str,
    start_cli_loop,
    active_runtime_root: str,
) -> None:
    if args.launch_streamlit:
        if args.gui:
            print("Nao combine --gui com --streamlit ao mesmo tempo.")
            return
        launched = launch_streamlit(
            project_root, port=args.streamlit_port, log_root=active_runtime_root
        )
        if launched:
            print("Interface web ativa. Pressione CTRL+C quando desejar encerrar este processo.")
        return

    if args.gui:
        _launch_gui(db_path, table_name, start_cli_loop, active_runtime_root)
        return

    logger.info("Iniciando interface de linha de comando...")
    start_cli_loop(db_path, table_name)


def main(cli_args=None):
    """
    Funcao principal da aplicacao com help melhorado.

    Args:
        cli_args (list, optional): Argumentos da linha de comando para testes.
                                   Se None, sys.argv e usado.
    """
    active_runtime_root = _ensure_runtime_environment()
    sys_argv = getattr(sys, "argv", None) or []
    raw_args = list(cli_args) if cli_args is not None else list(sys_argv[1:])
    early_log_level = "INFO"
    log_level_explicit = False
    for index, token in enumerate(raw_args):
        if token == "--log-level" and index + 1 < len(raw_args):
            early_log_level = raw_args[index + 1]
            log_level_explicit = True
            break
        if token.startswith("--log-level="):
            early_log_level = token.split("=", 1)[1]
            log_level_explicit = True
            break
    early_level = getattr(logging, early_log_level, logging.INFO)
    early_console_level = early_level if log_level_explicit else logging.WARNING
    _configure_logging(
        active_runtime_root,
        level_console=early_console_level,
        level_file=early_level,
    )
    _set_logging_level(
        early_level,
        level_console=early_console_level,
        level_file=early_level,
    )

    _log_startup_diagnostics(active_runtime_root)

    APP_VERSION = get_app_version()

    # Fix para PyOxidizer: sys.argv[0] pode ser None
    prog_name = sys_argv[0] if sys_argv and sys_argv[0] else "SSA_Consulta_Rapida"
    parser = build_argument_parser(APP_VERSION, prog_name)

    # Suporte a passagem de argumentos apos '--' exclusivamente ao backfill
    logger.debug("Processando argumentos de linha de comando")
    logger.debug("cli_args fornecido: %s", cli_args is not None)
    logger.debug("sys.argv disponivel: %s", hasattr(sys, "argv"))

    if sys_argv:
        logger.debug("sys.argv[1:]: %s", sys_argv[1:])
    else:
        logger.error("sys.argv nao esta disponivel!")

    backfill_args: list[str] = []
    if "--" in raw_args:
        split_idx = raw_args.index("--")
        main_args = raw_args[:split_idx]
        backfill_args = raw_args[split_idx + 1 :]
    else:
        main_args = raw_args

    logger.debug("raw_args: %s", raw_args)
    logger.debug("main_args: %s", main_args)
    logger.debug("backfill_args: %s", backfill_args)

    # Parse dos argumentos principais
    args = parser.parse_args(main_args)

    # --version: imprime e sai antes de qualquer outra acao
    if getattr(args, "version", False):
        print(get_app_version())
        return

    try:
        requested_level = getattr(logging, args.log_level)
        requested_console_level = requested_level if log_level_explicit else logging.WARNING
        _set_logging_level(
            requested_level,
            level_console=requested_console_level,
            level_file=requested_level,
        )
    except AttributeError:
        print(f"Nivel de log invalido: {args.log_level}. Usando INFO.")
        _set_logging_level(
            logging.INFO,
            level_console=logging.WARNING,
            level_file=logging.INFO,
        )

    # Banner inicial
    print(f"Pesquisa Rapida de SSAs {APP_VERSION}")

    try:
        dependencies = _load_runtime_dependencies()
        if dependencies is None:
            sys.exit(1)
        (
            run_importer_logic,
            ensure_default_settings,
            start_cli_loop,
            setup_project_structure,
        ) = dependencies
        if _run_maintenance_action(args):
            return
        _prepare_application_environment(active_runtime_root, setup_project_structure)
        _ensure_default_configuration(ensure_default_settings)
        _run_backfill_action(args, backfill_args)
        _run_data_import(args, run_importer_logic)
        db_path, table_name = _resolve_database_target(active_runtime_root)
        _launch_interface(
            args, db_path, table_name, start_cli_loop, active_runtime_root
        )

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
