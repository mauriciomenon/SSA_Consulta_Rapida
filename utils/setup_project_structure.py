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
* Lightweight validation step used by a guard test
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# Pastas exigidas na raiz (lista fixa; sem extensao por ambiente)
_BASE_REQUIRED_DIRS = (
    "config",
    "data",
    "data/historico_backups",
    "docs_entrada",
    "docs_saida",
    "logs",
    "reports",
    "extracao",
    "exportacao",
)


@dataclass
class SetupResult:
    created: list[str] = field(default_factory=list)
    existing: list[str] = field(default_factory=list)
    errors: dict[str, str] = field(default_factory=dict)

    @property
    def ok(self) -> bool:  # pragma: no cover - trivial
        return not self.errors


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

    for rel in _BASE_REQUIRED_DIRS:
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
        missing = [
            d
            for d in _BASE_REQUIRED_DIRS
            if not os.path.isdir(os.path.join(base_path, d))
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
