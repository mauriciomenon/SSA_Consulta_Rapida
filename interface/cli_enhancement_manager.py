"""
CLI Enhancement Integration - Integra melhorias na CLI existente
Permite ativar/desativar enhanced table printer facilmente.
"""

import errno
import json
import os
import tempfile
import time
from typing import Any

from utils.path_safety import ensure_path_is_allowed
from utils.robust_logging import get_robust_logger

logger = get_robust_logger().get_logger(__name__, "cli")

LOCK_RETRY_ATTEMPTS = 3
LOCK_RETRY_DELAY_SECONDS = 0.05
CLI_ENHANCEMENTS_PATH_ENV = "SSA_CLI_ENHANCEMENTS_PATH"


def _get_project_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _resolve_settings_file_path(project_root: str) -> str:
    override = os.environ.get(CLI_ENHANCEMENTS_PATH_ENV, "").strip()
    if override:
        return str(ensure_path_is_allowed(os.path.abspath(override)))
    return os.path.join(project_root, "config", "cli_enhancements.json")


try:
    import fcntl
except ImportError:  # pragma: no cover - Windows
    fcntl = None  # type: ignore
try:
    import msvcrt
except ImportError:  # pragma: no cover - POSIX
    msvcrt = None  # type: ignore


class CLIEnhancementManager:
    """
    Gerencia a integração das melhorias na CLI.
    """

    def __init__(self):
        """Inicializa o gerenciador de melhorias."""
        self.project_root = _get_project_root()
        self.settings_file = _resolve_settings_file_path(self.project_root)
        self.settings = self._load_settings()

    def _load_settings(self) -> dict:
        """Carrega configurações das melhorias CLI."""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Erro ao carregar configurações CLI: {e}")

        # Configurações padrão
        return {
            "enhanced_table_printer": True,
            "unified_column_config": True,
            "improved_ssa_normalization": True,
            "word_wrap_in_cli": True,
            "debug_output": False,
            "version": "1.0",
        }

    def _save_settings(self):
        """Salva configurações das melhorias."""
        lock_file = None
        lock_path = ""
        lock_path_created_now = False
        try:
            os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
            target_dir = os.path.dirname(self.settings_file) or "."
            base_name = os.path.basename(self.settings_file) or "cli_enhancements.json"
            self._cleanup_stale_temp_settings_files(target_dir, base_name)

            try:
                lock_path = f"{self.settings_file}.lock"
                try:
                    lock_fd = os.open(
                        lock_path, os.O_RDWR | os.O_CREAT | os.O_EXCL, 0o600
                    )
                    lock_path_created_now = True
                except FileExistsError:
                    lock_fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
                    lock_path_created_now = False
                if os.name == "posix":
                    try:
                        os.chmod(lock_path, 0o600)
                    except OSError as chmod_exc:
                        logger.debug(
                            "Falha ao ajustar permissao do lock file (%s): %s",
                            lock_path,
                            chmod_exc,
                        )
                try:
                    lock_file = os.fdopen(lock_fd, "a+")
                except BaseException:
                    os.close(lock_fd)
                    raise
                self._lock_file_if_possible(lock_file)
            except Exception as exc:
                logger.error(
                    "Nao foi possivel adquirir lock de settings; gravacao abortada: %s",
                    exc,
                )
                if lock_file is not None:
                    try:
                        lock_file.close()
                    except Exception as close_exc:
                        logger.warning(
                            "Falha ao fechar lock file de settings: %s", close_exc
                        )
                if lock_path and lock_path_created_now:
                    try:
                        os.remove(lock_path)
                    except FileNotFoundError:
                        pass
                    except Exception as remove_exc:
                        logger.debug(
                            "Falha ao remover lock file apos erro de lock '%s': %s",
                            lock_path,
                            remove_exc,
                        )
                lock_file = None
                raise RuntimeError(
                    "Falha ao salvar configuracoes CLI: lock indisponivel"
                ) from exc

            fd = None
            tmp_path = None
            try:
                fd, tmp_path = tempfile.mkstemp(
                    prefix=f".{base_name}.tmp.", dir=target_dir
                )
                try:
                    fobj = os.fdopen(fd, "w", encoding="utf-8")
                except BaseException:
                    os.close(fd)
                    raise
                with fobj as f:
                    json.dump(self.settings, f, indent=2, ensure_ascii=False)
                    f.flush()
                    try:
                        os.fsync(f.fileno())
                    except OSError as exc:
                        logger.debug(
                            "fsync failed for temp settings file (%s): %s",
                            tmp_path,
                            exc,
                        )
                os.replace(tmp_path, self.settings_file)
                if os.name == "posix":
                    try:
                        dir_fd = os.open(target_dir, os.O_RDONLY)
                        try:
                            os.fsync(dir_fd)
                        finally:
                            os.close(dir_fd)
                    except OSError as exc:
                        logger.debug(
                            "fsync failed for settings directory (%s): %s",
                            target_dir,
                            exc,
                        )
                tmp_path = None
            finally:
                if tmp_path:
                    try:
                        os.remove(tmp_path)
                    except FileNotFoundError:
                        pass
                    except Exception as remove_exc:
                        logger.warning(
                            "Falha ao remover arquivo temporario de settings '%s': %s",
                            tmp_path,
                            remove_exc,
                        )
        except Exception as e:
            logger.error("Erro ao salvar configuracoes CLI: %s", e)
            if isinstance(e, RuntimeError) and "lock indisponivel" in str(e):
                raise
            raise RuntimeError("Falha ao persistir configuracoes CLI") from e
        finally:
            if lock_file is not None:
                try:
                    lock_file.close()
                except Exception as close_exc:
                    logger.warning(
                        "Falha ao fechar lock file final de settings: %s", close_exc
                    )

    def _cleanup_stale_temp_settings_files(
        self, target_dir: str, base_name: str
    ) -> None:
        """Remove temp stale de settings para evitar acumulacao de lixo local."""
        prefix = f".{base_name}.tmp."
        now = time.time()
        stale_after_seconds = 24 * 60 * 60
        try:
            entries = os.listdir(target_dir)
        except Exception as exc:
            logger.debug(
                "Falha ao listar temp stale de settings em '%s': %s", target_dir, exc
            )
            return

        for entry in entries:
            if not entry.startswith(prefix):
                continue
            temp_path = os.path.join(target_dir, entry)
            try:
                stat = os.stat(temp_path)
                if now - stat.st_mtime < stale_after_seconds:
                    continue
                os.remove(temp_path)
                logger.debug("Temp stale de settings removido: %s", temp_path)
            except FileNotFoundError:
                continue
            except Exception as exc:
                logger.warning(
                    "Falha ao remover temp stale de settings '%s': %s", temp_path, exc
                )

    def _lock_file_if_possible(self, f: Any) -> None:
        """Acquire advisory lock for settings writes."""
        if fcntl is not None:
            if not hasattr(fcntl, "LOCK_NB"):
                raise RuntimeError(
                    "Backend fcntl sem LOCK_NB; lock bloqueante nao permitido"
                )
            flags = fcntl.LOCK_EX | fcntl.LOCK_NB
            last_exc = None
            for attempt in range(LOCK_RETRY_ATTEMPTS):
                try:
                    fcntl.flock(f.fileno(), flags)
                    return
                except OSError as exc:
                    last_exc = exc
                    if exc.errno not in (errno.EAGAIN, errno.EACCES):
                        raise RuntimeError(
                            f"Falha ao aplicar flock no settings: {exc}"
                        ) from exc
                    if attempt + 1 < LOCK_RETRY_ATTEMPTS:
                        time.sleep(LOCK_RETRY_DELAY_SECONDS)
            raise RuntimeError(
                f"Falha ao aplicar flock no settings apos retries: {last_exc}"
            ) from last_exc
        if msvcrt is not None:  # pragma: no cover - Windows
            mode = msvcrt.LK_NBLCK  # Always use non-blocking lock
            last_exc = None
            for attempt in range(LOCK_RETRY_ATTEMPTS):
                lock_len = 1
                try:
                    f.seek(0)
                except Exception:
                    pass
                try:
                    msvcrt.locking(f.fileno(), mode, lock_len)
                    return
                except OSError as exc:
                    last_exc = exc
                    # Retry only on lock contention; fail fast on other OS errors.
                    if exc.errno not in (errno.EACCES, errno.EAGAIN):
                        raise RuntimeError(
                            f"Falha critica ao aplicar msvcrt.locking no settings: {exc}"
                        ) from exc
                    if attempt + 1 < LOCK_RETRY_ATTEMPTS:
                        time.sleep(LOCK_RETRY_DELAY_SECONDS)
            raise RuntimeError(
                f"Falha ao aplicar msvcrt.locking no settings apos retries: {last_exc}"
            ) from last_exc
        raise RuntimeError("Nenhum backend de lock disponivel para settings")

    def is_enhanced_printer_enabled(self) -> bool:
        """Verifica se enhanced table printer está habilitado."""
        return self.settings.get("enhanced_table_printer", True)

    def is_unified_config_enabled(self) -> bool:
        """Verifica se configuração unificada está habilitada."""
        return self.settings.get("unified_column_config", True)

    def is_debug_enabled(self) -> bool:
        """Verifica se debug está habilitado."""
        return self.settings.get("debug_output", False)

    def enable_enhanced_printer(self):
        """Habilita enhanced table printer."""
        self.settings["enhanced_table_printer"] = True
        self._save_settings()

    def disable_enhanced_printer(self):
        """Desabilita enhanced table printer."""
        self.settings["enhanced_table_printer"] = False
        self._save_settings()

    def toggle_debug(self):
        """Alterna modo debug."""
        self.settings["debug_output"] = not self.settings.get("debug_output", False)
        self._save_settings()
        return self.settings["debug_output"]

    def get_status_report(self) -> str:
        """Retorna relatório do status das melhorias."""
        status = []
        status.append("INFO STATUS DAS MELHORIAS CLI")
        status.append("=" * 40)

        enhanced = "OK ATIVO" if self.is_enhanced_printer_enabled() else "ERR INATIVO"
        status.append(f"Enhanced Table Printer: {enhanced}")

        unified = "OK ATIVO" if self.is_unified_config_enabled() else "ERR INATIVO"
        status.append(f"Configuração Unificada: {unified}")

        debug = "[OK] ATIVO" if self.is_debug_enabled() else "[X] INATIVO"
        status.append(f"Debug Output: {debug}")

        status.append("")
        status.append("[MELHORIAS] MELHORIAS IMPLEMENTADAS:")
        status.append("• Larguras fixas determinísticas (como GUI)")
        status.append("• Sistema de crescimento proporcional 50/50")
        status.append("• Normalização correta de números SSA")
        status.append("• Configuração unificada GUI/CLI")
        status.append("• Quebra conservadora e truncamento de descrições")
        status.append("• Seleção otimizada de colunas")

        version = self.settings.get("version", "1.0")
        status.append("")
        status.append(f"Versão das melhorias: {version}")

        return "\n".join(status)


# Instância global
enhancement_manager = CLIEnhancementManager()


def print_cli_enhancements_status():
    """Função de conveniência para imprimir status."""
    print(enhancement_manager.get_status_report())


def toggle_cli_debug():
    """Função de conveniência para alternar debug."""
    new_state = enhancement_manager.toggle_debug()
    state_str = "ATIVADO" if new_state else "DESATIVADO"
    print(f"Debug CLI {state_str}")
    return new_state
