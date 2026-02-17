"""
CLI Enhancement Integration - Integra melhorias na CLI existente
Permite ativar/desativar enhanced table printer facilmente.
"""

import os
import json
import logging
import tempfile
from typing import Any

logger = logging.getLogger(__name__)

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
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.settings_file = os.path.join(self.project_root, 'config', 'cli_enhancements.json')
        self.settings = self._load_settings()

    def _load_settings(self) -> dict:
        """Carrega configurações das melhorias CLI."""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
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
            "version": "1.0"
        }

    def _save_settings(self):
        """Salva configurações das melhorias."""
        lock_file = None
        try:
            os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
            target_dir = os.path.dirname(self.settings_file) or "."
            base_name = os.path.basename(self.settings_file) or "cli_enhancements.json"

            try:
                lock_path = f"{self.settings_file}.lock"
                lock_fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
                try:
                    lock_file = os.fdopen(lock_fd, "w")
                except BaseException:
                    os.close(lock_fd)
                    raise
                self._lock_file_if_possible(lock_file)
            except Exception as exc:
                logger.debug("Nao foi possivel preparar lock para settings: %s", exc)
                if lock_file is not None:
                    try:
                        lock_file.close()
                    except Exception as close_exc:
                        logger.warning("Falha ao fechar lock file de settings: %s", close_exc)
                lock_file = None

            fd = None
            tmp_path = None
            try:
                fd, tmp_path = tempfile.mkstemp(prefix=f".{base_name}.tmp.", dir=target_dir)
                try:
                    fobj = os.fdopen(fd, "w", encoding="utf-8")
                except BaseException:
                    os.close(fd)
                    raise
                with fobj as f:
                    self._lock_file_if_possible(f)
                    json.dump(self.settings, f, indent=2, ensure_ascii=False)
                    f.flush()
                    try:
                        os.fsync(f.fileno())
                    except OSError as exc:
                        logger.debug("fsync failed for temp settings file (%s): %s", tmp_path, exc)
                os.replace(tmp_path, self.settings_file)
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
            logger.error(f"Erro ao salvar configurações CLI: {e}")
        finally:
            if lock_file is not None:
                try:
                    lock_file.close()
                except Exception as close_exc:
                    logger.warning("Falha ao fechar lock file final de settings: %s", close_exc)

    def _lock_file_if_possible(self, f: Any) -> None:
        """Best-effort file lock to avoid races on settings writes."""
        try:
            if fcntl is not None:
                flags = fcntl.LOCK_EX
                if hasattr(fcntl, "LOCK_NB"):
                    flags |= fcntl.LOCK_NB
                fcntl.flock(f.fileno(), flags)
            elif msvcrt is not None:  # pragma: no cover - Windows
                mode = getattr(msvcrt, "LK_NBLCK", msvcrt.LK_LOCK)
                try:
                    current_pos = f.tell()
                except Exception:
                    current_pos = 0
                try:
                    file_size = os.fstat(f.fileno()).st_size
                except Exception:
                    file_size = 0
                remaining = file_size - current_pos
                lock_len = max(remaining, 1)
                msvcrt.locking(f.fileno(), mode, lock_len)
        except Exception as exc:
            logger.debug("Nao foi possivel aplicar lock no settings: %s", exc)

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
        status.append("• Word wrap inteligente para descrições")
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
