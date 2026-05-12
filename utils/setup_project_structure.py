"""Utilities for ensuring required project directory structure.

Recovery Note
-------------
The original implementation of ``setup_project_structure`` was missing
from the repository history accessible locally (no hits via
``git log -S setup_project_structure``). This file is a reconstructed
and enhanced version providing idempotent directory setup plus basic
validation & reporting so that future regressions are easier to detect.

Responsibilities
----------------
* Ensure core directories exist (idempotent)
* Provide structured result (created / existing / errors)
* Allow extension: additional required dirs via environment variable
    ``SSA_EXTRA_DIRS=dir1,dir2``
* Lightweight validation step used by a guard test
"""

from __future__ import annotations

import importlib.util
import logging
import os
from collections.abc import Iterable
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


def _is_within_base(path: str, base: str) -> bool:
    """Return True when `path` is inside `base` after realpath normalization."""
    try:
        path_real = os.path.realpath(path)
        base_real = os.path.realpath(base)
        return os.path.commonpath([path_real, base_real]) == base_real
    except Exception:
        return False


# Base imutável; cópia de trabalho é derivada em runtime
# para evitar mutação global por chamadas repetidas
_BASE_REQUIRED_DIRS = [
    "config",
    "data",
    "data/historico_backups",
    "docs_entrada",
    "docs_saida",
    "logs",
    "reports",
    "extracao",
    "exportacao",
]


@dataclass
class SetupResult:
    created: list[str] = field(default_factory=list)
    existing: list[str] = field(default_factory=list)
    errors: dict[str, str] = field(default_factory=dict)

    @property
    def ok(self) -> bool:  # pragma: no cover - trivial
        return not self.errors


def _load_legacy_required_dirs() -> list[str]:  # pragma: no cover - caminho opcional
    """Carrega diretórios legados se módulo externo definir legacy_required_dirs().

    Segurança: não lança exceções fatais; falhas geram log DEBUG e retorna [].
    """
    module_path_raw = os.environ.get("SSA_LEGACY_SETUP_MODULE")
    if not module_path_raw:
        return []
    module_path = os.path.realpath(os.path.abspath(module_path_raw))
    project_root = os.path.realpath(
        os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    )
    allow_external = os.environ.get("SSA_ALLOW_EXTERNAL_LEGACY_SETUP_MODULE") == "1"
    if not allow_external and not _is_within_base(module_path, project_root):
        logger.warning(
            "SSA_LEGACY_SETUP_MODULE fora da raiz do projeto foi bloqueado: %s",
            module_path,
        )
        return []
    try:
        if not os.path.isfile(module_path):
            logger.warning(
                "SSA_LEGACY_SETUP_MODULE aponta para arquivo inexistente: %s",
                module_path,
            )
            return []
        spec = importlib.util.spec_from_file_location("_ssa_legacy_setup", module_path)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            func = getattr(mod, "legacy_required_dirs", None)
            if callable(func):
                legacy_raw = func()
                # Accept any iterable of strings defensively
                # Tratar iteráveis simples evitando tuple de tipos especificada pelo linter.
                if isinstance(legacy_raw, str):
                    legacy_iter: Iterable = [legacy_raw]
                elif isinstance(legacy_raw, bytes):  # noqa: SIM101 (separado para evitar regra tuple)
                    legacy_iter = [legacy_raw]
                elif isinstance(legacy_raw, Iterable):
                    try:
                        legacy_iter = list(
                            legacy_raw
                        )  # materializa para iteração única
                    except Exception:  # pragma: no cover
                        legacy_iter = [legacy_raw]
                else:
                    legacy_iter = [legacy_raw]
                legacy_list = list(
                    {
                        str(d).strip()
                        for d in legacy_iter
                        if isinstance(d, str) and str(d).strip()
                    }
                )
                if legacy_list:
                    logger.info("Diretórios legados detectados (%d)", len(legacy_list))
                return legacy_list
            logger.warning("Módulo legado não expõe legacy_required_dirs() utilizável")
    except Exception as e:  # pragma: no cover - defensivo
        logger.debug("Falha ao carregar módulo legado: %s", e)
    return []


def setup_dirs(
    base_path: str | None = None, ensure_permissions: bool = False
) -> SetupResult:
    """Ensure required directories exist.

    Parameters
    ----------
    base_path: optional base directory (defaults to project root where main.py resides)
    """
    if base_path is None:
        # Determine project root relative to this file
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))

    result = SetupResult()

    # Construir lista de trabalho (não mutar base global)
    working_required = list(_BASE_REQUIRED_DIRS)

    # Diretórios vindos de configuração legada (se existir)
    legacy_dirs = _load_legacy_required_dirs()
    for d in legacy_dirs:
        if d not in working_required:
            working_required.append(d)

    # Allow extra dirs via env (prioridade após legado)
    extra_raw = os.environ.get("SSA_EXTRA_DIRS", "").strip()
    if extra_raw:
        for part in [p.strip() for p in extra_raw.split(",") if p.strip()]:
            if part and part not in working_required:
                working_required.append(part)

    for rel in working_required:
        full = os.path.join(base_path, rel)
        try:
            if os.path.isdir(full):
                result.existing.append(rel)
            else:
                os.makedirs(full, exist_ok=True)
                result.created.append(rel)
                logger.info("Criado diretório requerido: %s", rel)
            if ensure_permissions:
                # Best effort: rwx for user
                try:
                    # nosemgrep: python.lang.security.audit.insecure-file-permissions.insecure-file-permissions
                    os.chmod(full, 0o700)
                except Exception as e:  # pragma: no cover
                    logger.debug("Falha ao ajustar permissões %s: %s", full, e)
        except Exception as e:  # pragma: no cover - defensive
            result.errors[rel] = str(e)

    logger.debug(
        "setup_dirs concluído: created=%s existing=%s errors=%s",
        len(result.created),
        len(result.existing),
        len(result.errors),
    )
    return result


# Backwards compatibility object-style API expected in main:
class SetupProjectStructure:  # Renamed to follow CapWords; keep legacy alias below
    @staticmethod
    def setup_dirs(
        base_path: str | None = None, ensure_permissions: bool = False
    ) -> SetupResult:
        return setup_dirs(base_path, ensure_permissions=ensure_permissions)

    @staticmethod
    def validate(base_path: str | None = None) -> bool:
        """Quick validation used by tests: all required dirs present."""
        if base_path is None:
            base_path = os.path.abspath(
                os.path.join(os.path.dirname(__file__), os.pardir)
            )
        # Montar lista coerente (base + possíveis legados + extras env)
        working_required = list(_BASE_REQUIRED_DIRS)
        for add in _load_legacy_required_dirs():
            if add not in working_required:
                working_required.append(add)
        extra_raw = os.environ.get("SSA_EXTRA_DIRS", "").strip()
        if extra_raw:
            for part in [p.strip() for p in extra_raw.split(",") if p.strip()]:
                if part not in working_required:
                    working_required.append(part)
        missing = [
            d for d in working_required if not os.path.isdir(os.path.join(base_path, d))
        ]
        if missing:
            logger.warning("Diretórios faltando: %s", missing)
            return False
        return True


# Module-level validate helper for tests/tools expecting validate symbol directly
def validate(base_path: str | None = None) -> bool:  # pragma: no cover - delega
    return SetupProjectStructure.validate(base_path)


# Backwards compatibility alias (legacy lowercase name still referenced externally)
setup_project_structure = SetupProjectStructure
