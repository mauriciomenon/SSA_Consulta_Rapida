# core/config_manager.py 20250725 163000 (v2.1 - Melhorias de Erro, Logging)
"""
Gerenciador de configuracoes da aplicacao.

Responsavel por carregar, salvar e garantir a existencia do arquivo settings.json.
"""

import json
import os
import shutil
import tempfile
from typing import Any, Callable, Dict

from core.config_defaults import DEFAULT_DISPLAY_MAPPINGS
from core.config_defaults import default_config_payload_for_filename
from core.config_defaults import get_default_column_mappings
from shared.table_display_defaults import COLUMN_AFFINITY_SCORES
from utils.path_safety import PathSafetyError, ensure_path_is_allowed
from utils.robust_logging import get_robust_logger

__all__ = [
    "COLUMN_AFFINITY_SCORES",
    "DEFAULT_DISPLAY_MAPPINGS",
    "get_default_column_mappings",
]

logger = get_robust_logger().get_logger(__name__, "core")


class ConfigProvisionError(RuntimeError):
    """Raised when a default config file cannot be provisioned."""


def _atomic_write_json_file(
    path: str, data: Any, *, indent: int, ensure_ascii: bool
) -> None:
    """Write JSON atomically to prevent truncated/corrupted config files on crash."""
    target_dir = os.path.dirname(path) or "."
    base_name = os.path.basename(path) or "config.json"
    os.makedirs(target_dir, exist_ok=True)
    target_mode = 0o600
    try:
        target_mode = os.stat(path).st_mode & 0o777
    except FileNotFoundError:
        pass

    fd = None
    tmp_path = None
    try:
        fd, tmp_path = tempfile.mkstemp(prefix=f".{base_name}.tmp.", dir=target_dir)
        if hasattr(os, "fchmod"):
            try:
                os.fchmod(fd, target_mode)
            except OSError as exc:
                logger.debug(
                    "initial fchmod failed for config temp file (%s): %s",
                    tmp_path,
                    exc,
                )
        f = os.fdopen(fd, "w", encoding="utf-8")
        fd = None
        try:
            json.dump(data, f, indent=indent, ensure_ascii=ensure_ascii)
            f.flush()
            if hasattr(os, "fchmod"):
                try:
                    os.fchmod(f.fileno(), target_mode)
                except OSError as exc:
                    logger.debug(
                        "fchmod failed for config temp file (%s): %s",
                        tmp_path,
                        exc,
                    )
            try:
                os.fsync(f.fileno())
            except OSError as exc:
                logger.debug(
                    "fsync failed for config temp file (%s): %s", tmp_path, exc
                )
        finally:
            f.close()
        if not hasattr(os, "fchmod"):
            os.chmod(tmp_path, target_mode)
        os.replace(tmp_path, path)
        _fsync_parent_directory(target_dir)
        tmp_path = None
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except OSError as exc:
                logger.warning(
                    "Falha ao fechar file descriptor temporario de config '%s': %s",
                    path,
                    exc,
                )
        if tmp_path:
            try:
                os.remove(tmp_path)
            except FileNotFoundError:
                pass
            except OSError as exc:
                logger.warning(
                    "Falha ao remover arquivo temporario de config '%s': %s",
                    tmp_path,
                    exc,
                )


def atomic_write_json_file(
    path: str,
    data: Any,
    *,
    indent: int = 2,
    ensure_ascii: bool = False,
) -> None:
    """Public helper to write JSON atomically."""
    _atomic_write_json_file(path, data, indent=indent, ensure_ascii=ensure_ascii)


def _fsync_parent_directory(target_dir: str) -> None:
    if os.name == "nt":
        return
    try:
        dir_fd = os.open(target_dir, os.O_RDONLY)
    except OSError as exc:
        logger.debug("Falha ao abrir diretorio para fsync (%s): %s", target_dir, exc)
        return
    try:
        os.fsync(dir_fd)
    except OSError as exc:
        logger.debug("Falha no fsync do diretorio (%s): %s", target_dir, exc)
    finally:
        os.close(dir_fd)


def _atomic_copy_file(src: str, dst: str) -> None:
    """Copy a file atomically to avoid partial writes when creating defaults."""
    target_dir = os.path.dirname(dst) or "."
    base_name = os.path.basename(dst) or "file"
    os.makedirs(target_dir, exist_ok=True)
    target_mode = 0o600
    try:
        target_mode = os.stat(src).st_mode & 0o777
    except OSError as exc:
        logger.debug("Falha ao ler modo de '%s': %s", src, exc)

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=f".{base_name}.tmp.", dir=target_dir, delete=False
        ) as tmp_file:
            tmp_path = tmp_file.name
            if hasattr(os, "fchmod"):
                try:
                    os.fchmod(tmp_file.fileno(), target_mode)
                except OSError as exc:
                    logger.debug(
                        "initial fchmod failed for config temp file (%s): %s",
                        tmp_path,
                        exc,
                    )
            with open(src, "rb") as src_file:
                shutil.copyfileobj(src_file, tmp_file)
            tmp_file.flush()
            try:
                os.fsync(tmp_file.fileno())
            except OSError as exc:
                logger.debug("fsync failed for config temp file (%s): %s", tmp_path, exc)
        if not hasattr(os, "fchmod"):
            os.chmod(tmp_path, target_mode)
        os.replace(tmp_path, dst)
        _fsync_parent_directory(target_dir)
        tmp_path = None
    finally:
        if tmp_path:
            try:
                os.remove(tmp_path)
            except FileNotFoundError:
                pass
            except OSError as exc:
                logger.warning(
                    "Falha ao remover arquivo temporario de copia '%s': %s",
                    tmp_path,
                    exc,
                )


# Caminhos padrao
CONFIG_DIR = "config"
DEFAULT_SETTINGS_FILE = os.path.join(CONFIG_DIR, "default_settings.json")
USER_SETTINGS_FILE = os.path.join(CONFIG_DIR, "settings.json")
DISPLAY_MAPPINGS_FILE = os.path.join(CONFIG_DIR, "display_mappings.json")
COLUMN_MAPPINGS_FILE = os.path.join(CONFIG_DIR, "column_mappings.json")

def _get_config_dir() -> str:
    """Allow tests/overrides via SSA_CONFIG_DIR; default to 'config'."""
    raw_cfg_dir = os.environ.get("SSA_CONFIG_DIR")
    if not raw_cfg_dir:
        return CONFIG_DIR
    try:
        return str(
            ensure_path_is_allowed(
                raw_cfg_dir,
                purpose="SSA_CONFIG_DIR",
                expect_directory=True,
            )
        )
    except PathSafetyError as exc:
        logger.warning("SSA_CONFIG_DIR invalido (%s). Usando '%s'.", exc, CONFIG_DIR)
        return CONFIG_DIR


def _resolve_config_path(default_path: str) -> str:
    """Resolve a config path honoring SSA_CONFIG_DIR while keeping default constants."""
    cfg_dir = _get_config_dir()
    if cfg_dir == CONFIG_DIR:
        return default_path
    return os.path.join(cfg_dir, os.path.basename(default_path))


def resolve_user_settings_path() -> str:
    return _resolve_config_path(USER_SETTINGS_FILE)


def resolve_default_settings_path() -> str:
    return _resolve_config_path(DEFAULT_SETTINGS_FILE)


def load_default_settings_payload() -> Dict[str, Any]:
    default_settings_file = resolve_default_settings_path()
    if not os.path.exists(default_settings_file):
        raise FileNotFoundError(
            f"Arquivo de configuracoes padrao nao encontrado: {default_settings_file}"
        )
    with open(default_settings_file, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_json_mapping_integrity(
    path: str,
    default_mapping: dict,
    *,
    file_label: str,
    validator: Callable[[Any], bool],
) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if validator(data):
            return data
        logger.warning(
            "%s invalido em '%s'. Usando defaults em memoria e tentando restaurar arquivo.",
            file_label,
            path,
        )
    except (OSError, json.JSONDecodeError, ValueError, TypeError):
        logger.warning(
            "%s ausente ou ilegivel em '%s'. Usando defaults em memoria e tentando restaurar arquivo.",
            file_label,
            path,
        )
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        _atomic_write_json_file(path, default_mapping, indent=2, ensure_ascii=False)
        logger.warning("%s foi recriado em '%s' com valores padrao.", file_label, path)
        return default_mapping.copy()
    except (OSError, TypeError, ValueError) as e:
        logger.error("Falha ao restaurar %s: %s", file_label, e)
        logger.error("Usando defaults em memoria; arquivo nao foi atualizado.")
        return default_mapping.copy()


def _default_payload_for_config_target(target_file: str) -> dict[str, Any] | None:
    payload = default_config_payload_for_filename(os.path.basename(target_file))
    return dict(payload) if payload is not None else None


def _provision_default_config_file(
    target_file: str,
    example_file: str,
    *,
    cfg_dir: str,
) -> None:
    example_path = os.path.join(cfg_dir, example_file)
    if not os.path.exists(example_path):
        example_path = os.path.join(CONFIG_DIR, example_file)
    if os.path.exists(example_path):
        try:
            _atomic_copy_file(example_path, target_file)
            logger.info(f"Arquivo de configuração padrão criado: {target_file}")
            return
        except IOError as e:
            logger.error(f"Falha ao copiar '{example_path}' para '{target_file}': {e}")
            raise ConfigProvisionError(
                f"falha ao copiar config padrao de '{example_path}' para "
                f"'{target_file}': {e}"
            ) from e
    try:
        os.makedirs(os.path.dirname(target_file) or cfg_dir, exist_ok=True)
        default_content = _default_payload_for_config_target(target_file)
        if default_content is None:
            logger.warning(
                f"Arquivo de exemplo '{example_path}' não encontrado para '{target_file}'."
            )
            return
        _atomic_write_json_file(target_file, default_content, indent=2, ensure_ascii=False)
        logger.info(f"Arquivo padrão gerado: {target_file}")
        return
    except Exception as e:
        logger.error(f"Falha ao gerar arquivo padrão '{target_file}': {e}")
        raise ConfigProvisionError(
            f"falha ao gerar config padrao '{target_file}': {e}"
        ) from e


def load_display_mappings_integrity() -> Dict[str, str]:
    """Load display_mappings.json; if missing/invalid, recreate with defaults and return it."""
    cfg_dir = _get_config_dir()
    path = os.path.join(cfg_dir, "display_mappings.json")
    return _load_json_mapping_integrity(
        path,
        DEFAULT_DISPLAY_MAPPINGS,
        file_label="display_mappings.json",
        validator=lambda data: isinstance(data, dict),
    )


def load_column_mappings_integrity() -> Dict[str, list]:
    """Load column_mappings.json; if missing/invalid, recreate with defaults and return it.

    Estrutura esperada: { canonical_name: [list_of_aliases, ...], ... }
    """
    cfg_dir = _get_config_dir()
    path = os.path.join(cfg_dir, "column_mappings.json")
    return _load_json_mapping_integrity(
        path,
        get_default_column_mappings(),
        file_label="column_mappings.json",
        validator=lambda data: isinstance(data, dict)
        and bool(data)
        and all(isinstance(v, list) for v in data.values()),
    )


def load_settings() -> Dict[str, Any]:
    """
    Carrega as configurações do usuário. Se não existir, carrega as padrões.

    Returns:
        Dict[str, Any]: Um dicionário com as configurações.
    """
    user_settings_file = _resolve_config_path(USER_SETTINGS_FILE)
    default_settings_file = _resolve_config_path(DEFAULT_SETTINGS_FILE)
    settings_path = user_settings_file
    if not os.path.exists(settings_path):
        logger.info(
            f"Arquivo de configuração do usuário '{settings_path}' não encontrado. Carregando padrões."
        )
        if not os.path.exists(default_settings_file):
            message = (
                "Arquivos de configuracao ausentes: "
                f"user='{user_settings_file}', default='{default_settings_file}'. "
                "Execute ensure_default_settings antes de carregar configuracoes."
            )
            logger.critical(message)
            raise FileNotFoundError(message)
        settings_path = default_settings_file

    try:
        with open(settings_path, "r", encoding="utf-8") as f:
            settings = json.load(f)
        logger.debug(f"Configurações carregadas de '{settings_path}'.")
        return settings
    except FileNotFoundError:
        if settings_path != default_settings_file and os.path.exists(
            default_settings_file
        ):
            logger.warning(
                "Arquivo de configuracao do usuario sumiu durante leitura. "
                "Carregando default '%s'.",
                default_settings_file,
            )
            with open(default_settings_file, "r", encoding="utf-8") as f:
                return json.load(f)
        logger.critical(f"Arquivo de configuração '{settings_path}' não encontrado.")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Erro ao decodificar JSON em '{settings_path}': {e}")
        raise


def save_settings(settings: Dict[str, Any]):
    """
    Salva as configurações do usuário.

    Args:
        settings (Dict[str, Any]): O dicionário de configurações a ser salvo.
    """
    user_settings_file = _resolve_config_path(USER_SETTINGS_FILE)
    try:
        os.makedirs(os.path.dirname(user_settings_file), exist_ok=True)
        _atomic_write_json_file(
            user_settings_file, settings, indent=4, ensure_ascii=False
        )
        logger.info(f"Configuracoes salvas em '{user_settings_file}'.")
    except IOError as e:
        logger.error(f"Erro ao salvar configuracoes em '{user_settings_file}': {e}")
        raise


def ensure_default_settings(*, fail_fast: bool = True) -> list[str]:
    """
    Garante que os arquivos de configuração padrão existam.
    Se não existirem, os copia dos arquivos de exemplo ou os cria.

    Args:
        fail_fast (bool): Se True, levanta RuntimeError quando houver falhas.

    Returns:
        list[str]: Lista de erros de provisionamento. Lista vazia indica sucesso.

    Raises:
        RuntimeError: Quando `fail_fast=True` e existir falha de provisionamento.
    """
    errors: list[str] = []
    required_files = {
        _resolve_config_path(DEFAULT_SETTINGS_FILE): "default_settings.json.example",
        _resolve_config_path(DISPLAY_MAPPINGS_FILE): "display_mappings.json.example",
        _resolve_config_path(COLUMN_MAPPINGS_FILE): "column_mappings.json.example",
        # Adicione outros arquivos de configuração aqui se necessário
    }

    for target_file, example_file in required_files.items():
        if not os.path.exists(target_file):
            cfg_dir = _get_config_dir()
            try:
                _provision_default_config_file(
                    target_file,
                    example_file,
                    cfg_dir=cfg_dir,
                )
            except ConfigProvisionError as exc:
                errors.append(str(exc))
    if errors:
        logger.critical(
            "ensure_default_settings completed with errors: %s", "; ".join(errors)
        )
        if fail_fast:
            raise RuntimeError("ensure_default_settings failed: " + "; ".join(errors))
    return errors
