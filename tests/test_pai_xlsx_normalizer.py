from __future__ import annotations

import errno
from pathlib import Path
from zipfile import BadZipFile

import pytest

from core import pai_xlsx_normalizer
from core.pai_xlsx_normalizer import _coalesce_columns
from core.pai_xlsx_normalizer import _replace_xlsx_with_retry
from core.pai_xlsx_normalizer import _validate_source_excel_path
from core.pai_xlsx_normalizer import build_normalized_pai_dataframe
from core.pai_xlsx_normalizer import normalize_pai_xlsx_for_ssa_import


def test_normalize_pai_xlsx_reports_read_failure(tmp_path: Path) -> None:
    source = tmp_path / "broken.xlsx"
    source.write_text("not an xlsx", encoding="utf-8")

    with pytest.raises(ValueError, match="Falha ao ler XLSX SAM API"):
        normalize_pai_xlsx_for_ssa_import(source, tmp_path / "out.xlsx")


def test_normalize_pai_xlsx_rejects_size_before_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "large.xlsx"
    source.write_bytes(b"12345")
    read_called = False
    monkeypatch.setattr("extracao.extractor.MAX_XLSX_FILE_BYTES", 4)

    def _unexpected_read(*_args, **_kwargs):
        nonlocal read_called
        read_called = True
        raise AssertionError("read_excel must not run")

    monkeypatch.setattr(pai_xlsx_normalizer.pd, "read_excel", _unexpected_read)

    with pytest.raises(ValueError, match="excede o limite"):
        normalize_pai_xlsx_for_ssa_import(source, tmp_path / "out.xlsx")

    assert read_called is False


def test_build_normalized_pai_dataframe_maps_situation_desc_to_situacao() -> None:
    normalized = build_normalized_pai_dataframe(
        pai_xlsx_normalizer.pd.DataFrame(
            {
                "ssa_number": [202607611],
                "description": ["Teste"],
                "issue_datetime": ["2026-05-22T16:57:00Z"],
                "situation_desc": ["APL - AGUARDANDO PLANEJAMENTO"],
            }
        )
    )

    assert normalized.loc[0, "situacao"] == "APL - AGUARDANDO PLANEJAMENTO"


def test_build_normalized_pai_dataframe_uses_process_status_when_situation_is_empty() -> None:
    normalized = build_normalized_pai_dataframe(
        pai_xlsx_normalizer.pd.DataFrame(
            {
                "ssa_number": [202607611],
                "description": ["Teste"],
                "issue_datetime": ["2026-05-22T16:57:00Z"],
                "situation_desc": [""],
                "process_status": ["Emitida"],
            }
        )
    )

    assert normalized.loc[0, "situacao"] == "Emitida"


def test_coalesce_columns_missing_returns_string_series() -> None:
    frame = pai_xlsx_normalizer.pd.DataFrame({"other": [1, 2]})

    series = _coalesce_columns(frame, ("missing",))

    assert str(series.dtype) == "string"
    assert series.isna().tolist() == [True, True]


def test_validate_source_excel_path_accepts_uppercase_suffix(tmp_path: Path) -> None:
    source = tmp_path / "SAM_API.XLSX"
    source.write_bytes(b"xlsx")

    _validate_source_excel_path(source)


def test_normalize_pai_xlsx_reports_bad_zip_read_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "broken.xlsx"
    source.write_bytes(b"broken")

    def _raise_bad_zip(*_args, **_kwargs):
        raise BadZipFile("bad zip")

    monkeypatch.setattr(pai_xlsx_normalizer.pd, "read_excel", _raise_bad_zip)

    with pytest.raises(ValueError, match="Falha ao ler XLSX SAM API"):
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
