"""CD-07: a importacao explicita (SAM API) aceita a pasta do banco como raiz permitida."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from core import app_logic
from utils import path_safety
from utils.path_safety import PathSafetyError


@pytest.fixture()
def restricted_roots(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Raizes padrao sem a pasta do banco: so <tmp>/allowed faz o papel do temp do SO."""
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    monkeypatch.delenv("SSA_EXTRA_ALLOWED_PATHS", raising=False)
    monkeypatch.setattr(path_safety.tempfile, "gettempdir", lambda: str(allowed))
    path_safety.refresh_allowed_roots()
    return allowed


def _staged_file(allowed: Path) -> tuple[Path, Path]:
    docs = allowed / "docs_entrada"
    docs.mkdir()
    staged = docs / "pai_ssa_import.xlsx"
    staged.write_bytes(b"x")
    return docs, staged


def test_explicit_import_rejects_db_outside_roots_without_extra(restricted_roots, tmp_path):
    docs, staged = _staged_file(restricted_roots)
    outside_db = tmp_path / "outro" / "ssas.db"

    with pytest.raises(PathSafetyError):
        app_logic.import_explicit_files_to_database(
            [str(staged)], docs_dir=str(docs), db_path=str(outside_db), raise_on_error=True
        )


def test_explicit_import_accepts_extra_allowed_roots(restricted_roots, tmp_path, monkeypatch):
    docs, staged = _staged_file(restricted_roots)
    outside_dir = tmp_path / "outro"
    outside_dir.mkdir()
    calls: list[dict[str, Any]] = []
    monkeypatch.setattr(
        app_logic, "run_importer_logic", lambda **kwargs: calls.append(kwargs) or True
    )

    ok = app_logic.import_explicit_files_to_database(
        [str(staged)],
        docs_dir=str(docs),
        db_path=str(outside_dir / "ssas.db"),
        raise_on_error=True,
        extra_allowed_roots=(str(outside_dir),),
    )

    assert ok is True
    assert calls[0]["extra_allowed_roots"] == (str(outside_dir),)
    assert calls[0]["db_name"] == "ssas.db"
