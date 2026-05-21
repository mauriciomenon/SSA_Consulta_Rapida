from __future__ import annotations

import errno
from pathlib import Path

import pytest

from core import pai_xlsx_normalizer
from core.pai_xlsx_normalizer import _replace_xlsx_with_retry
from core.pai_xlsx_normalizer import normalize_pai_xlsx_for_ssa_import


def test_normalize_pai_xlsx_reports_read_failure(tmp_path: Path) -> None:
    source = tmp_path / "broken.xlsx"
    source.write_text("not an xlsx", encoding="utf-8")

    with pytest.raises(ValueError, match="Falha ao ler XLSX PAI"):
        normalize_pai_xlsx_for_ssa_import(source, tmp_path / "out.xlsx")


def test_normalize_pai_xlsx_retries_target_replace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source.xlsx"
    target = tmp_path / "normalized.xlsx"
    source.write_text("xlsx-bytes", encoding="utf-8")
    attempts = {"count": 0}
    original_replace = pai_xlsx_normalizer.os.replace

    def _flaky_replace(src, dst):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise PermissionError(errno.EACCES, "locked")
        return original_replace(src, dst)

    monkeypatch.setattr(pai_xlsx_normalizer.os, "name", "nt")
    monkeypatch.setattr(pai_xlsx_normalizer.os, "replace", _flaky_replace)

    _replace_xlsx_with_retry(source, target)

    assert attempts["count"] == 2
    assert target.exists()
