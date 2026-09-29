from __future__ import annotations

import os
from pathlib import Path

import pytest

from core import import_run_report


def _reports(directory: Path, count: int) -> list[Path]:
    reports = [
        directory / f"import_run_20260101_000000_{index:06d}.json"
        for index in range(count)
    ]
    for report in reports:
        report.write_text("{}", encoding="utf-8")
    return reports


def test_prune_uses_run_id_and_preserves_unowned_files(tmp_path: Path) -> None:
    reports = _reports(tmp_path, 52)
    for index, report in enumerate(reports):
        os.utime(report, (1000 - index, 1000 - index))
    unrelated = [
        tmp_path / "import_run_notes.json",
        tmp_path / "import_run_20269999_000000_000000.json",
        tmp_path / "other_report.json",
    ]
    for path in unrelated:
        path.write_text("keep", encoding="utf-8")

    import_run_report._prune_import_run_reports(str(tmp_path))

    assert all(not report.exists() for report in reports[:2])
    assert all(report.exists() for report in reports[2:])
    assert all(path.read_text(encoding="utf-8") == "keep" for path in unrelated)


def test_prune_continues_when_one_stat_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    reports = _reports(tmp_path, 52)
    original_stat = os.stat

    def failing_stat(path: str | os.PathLike[str], *args, **kwargs):
        if os.fspath(path) == str(reports[0]):
            raise OSError("stat blocked")
        return original_stat(path, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(import_run_report.os, "stat", failing_stat)
        import_run_report._prune_import_run_reports(str(tmp_path))

    assert reports[0].exists()
    assert not reports[1].exists()
    assert all(report.exists() for report in reports[2:])
    assert "Falha ao examinar relatorio" in caplog.text


def test_prune_continues_when_one_unlink_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    reports = _reports(tmp_path, 52)
    original_remove = os.remove

    def failing_remove(path: str | os.PathLike[str]) -> None:
        if os.fspath(path) == str(reports[0]):
            raise OSError("unlink blocked")
        original_remove(path)

    with monkeypatch.context() as patch:
        patch.setattr(import_run_report.os, "remove", failing_remove)
        import_run_report._prune_import_run_reports(str(tmp_path))

    assert reports[0].exists()
    assert not reports[1].exists()
    assert all(report.exists() for report in reports[2:])
    assert "Falha ao descartar relatorio antigo" in caplog.text
