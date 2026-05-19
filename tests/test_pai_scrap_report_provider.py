from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from core.pai_import_service import fetch_and_import_pai_xlsx
from core.pai_scrap_report_provider import (
    PaiScrapReportExport,
    PaiScrapReportRequest,
    run_pai_scrap_report_export,
    run_pai_scrap_report_ca_export,
)


class _Completed:
    returncode = 0
    stdout = ""
    stderr = ""


def test_run_pai_scrap_report_export_creates_xlsx_from_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scrap_root = _make_scrap_report_root(tmp_path)
    output_dir = tmp_path / "out"
    xlsx_path = output_dir / "pai_sam_api.xlsx"
    monkeypatch.setattr("core.pai_scrap_report_provider.shutil.which", lambda _: "/bin/uv")

    def runner(command: list[str], **kwargs: Any) -> _Completed:
        assert command[:5] == ["/bin/uv", "run", "--project", str(scrap_root), "python"]
        assert "sam-api-flow" in command
        output_dir.mkdir(exist_ok=True)
        xlsx_path.write_bytes(b"xlsx")
        (output_dir / "pai_sam_api_manifest.json").write_text(
            '{"status":"ok","exports":{"data_xlsx":"pai_sam_api.xlsx"}}',
            encoding="utf-8",
        )
        return _Completed()

    result = run_pai_scrap_report_export(
        PaiScrapReportRequest(
            project_root=tmp_path,
            output_dir=output_dir,
            scrap_report_root=scrap_root,
        ),
        runner=runner,
    )

    assert result.xlsx_path == xlsx_path
    assert result.manifest_path == output_dir / "pai_sam_api_manifest.json"


def test_run_pai_scrap_report_export_rejects_manifest_path_escape(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scrap_root = _make_scrap_report_root(tmp_path)
    output_dir = tmp_path / "out"
    outside = tmp_path / "outside.xlsx"
    monkeypatch.setattr("core.pai_scrap_report_provider.shutil.which", lambda _: "/bin/uv")

    def runner(_command: list[str], **_kwargs: Any) -> _Completed:
        output_dir.mkdir(exist_ok=True)
        outside.write_bytes(b"xlsx")
        (output_dir / "pai_sam_api_manifest.json").write_text(
            f'{{"status":"ok","exports":{{"data_xlsx":"{outside}"}}}}',
            encoding="utf-8",
        )
        return _Completed()

    with pytest.raises(ValueError, match="fora do diretorio esperado"):
        run_pai_scrap_report_export(
            PaiScrapReportRequest(
                project_root=tmp_path,
                output_dir=output_dir,
                scrap_report_root=scrap_root,
            ),
            runner=runner,
        )


def test_run_pai_scrap_report_ca_export_creates_ca_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scrap_root = _make_scrap_report_root(tmp_path)
    output_dir = tmp_path / "out"
    monkeypatch.setattr("core.pai_scrap_report_provider.shutil.which", lambda _: "/bin/uv")

    def runner(command: list[str], **kwargs: Any) -> _Completed:
        assert command[:5] == ["/bin/uv", "run", "--project", str(scrap_root), "python"]
        assert "sam-api-cert" in command
        assert "--output" in command
        output_dir.mkdir(exist_ok=True)
        (output_dir / "itaipu_root_ca.pem").write_text("CERT", encoding="utf-8")
        return _Completed()

    result = run_pai_scrap_report_ca_export(
        PaiScrapReportRequest(
            project_root=tmp_path,
            output_dir=output_dir,
            scrap_report_root=scrap_root,
        ),
        runner=runner,
    )

    assert result.ca_file == output_dir / "itaipu_root_ca.pem"
    assert "sam-api-cert" in result.command


def test_fetch_and_import_pai_xlsx_stages_and_imports(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    xlsx_path = tmp_path / "out" / "pai.xlsx"
    xlsx_path.parent.mkdir()
    pd.DataFrame(
        {
            "ssa_number": [202600001],
            "description": ["Teste PAI"],
            "issue_datetime": ["2026-01-07T13:56:00Z"],
            "localization": ["M075A006"],
            "emitter_sector": ["MEL4"],
            "executor_sector": ["IEE3"],
            "year_week": [202602],
        }
    ).to_excel(xlsx_path, index=False)
    export = PaiScrapReportExport(
        command=("python", "-m", "scrap_report.cli"),
        scrap_report_root=tmp_path,
        manifest_path=tmp_path / "out" / "manifest.json",
        xlsx_path=xlsx_path,
        manifest={"status": "ok"},
        stdout="",
        stderr="",
    )
    monkeypatch.setattr(
        "core.pai_import_service.run_pai_scrap_report_export",
        lambda _request: export,
    )

    staged_calls: list[dict[str, Any]] = []
    import_calls: list[dict[str, Any]] = []

    def stage_files(**kwargs: Any) -> tuple[list[str], dict[str, int]]:
        staged_calls.append(kwargs)
        return [str(tmp_path / "docs_entrada" / "pai_ssa_import.xlsx")], {
            "copied": 1,
            "skipped": 0,
            "failed": 0,
            "unsupported": 0,
            "staged": 1,
            "already_staged": 0,
        }

    def import_files(file_paths: list[str], **kwargs: Any) -> bool:
        import_calls.append({"file_paths": file_paths, **kwargs})
        db_path = Path(kwargs["db_path"])
        db_path.parent.mkdir(parents=True, exist_ok=True)
        import sqlite3

        with sqlite3.connect(db_path) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS ssa_table (numero_ssa TEXT)")
            conn.execute("INSERT INTO ssa_table (numero_ssa) VALUES ('202600001')")
        return True

    result = fetch_and_import_pai_xlsx(
        PaiScrapReportRequest(project_root=tmp_path),
        docs_dir=tmp_path / "docs_entrada",
        db_path=tmp_path / "data" / "ssas.db",
        stage_files=stage_files,
        import_files=import_files,
    )

    assert result.imported is True
    assert result.normalized_rows == 1
    assert result.rows_before_import == 0
    assert result.rows_after_import == 1
    assert result.import_xlsx_path == tmp_path / "docs_entrada" / "pai_ssa_import.xlsx"
    assert result.staged_files == (str(tmp_path / "docs_entrada" / "pai_ssa_import.xlsx"),)
    assert staged_calls[0]["source_files"] == (str(result.import_xlsx_path),)
    assert staged_calls[0]["docs_dir"] == tmp_path / "docs_entrada"
    assert import_calls[0]["docs_dir"] == str(tmp_path / "docs_entrada")
    assert import_calls[0]["db_path"] == str(tmp_path / "data" / "ssas.db")


def _make_scrap_report_root(tmp_path: Path) -> Path:
    root = tmp_path / "scrap_report"
    cli_dir = root / "src" / "scrap_report"
    cli_dir.mkdir(parents=True)
    (root / "pyproject.toml").write_text("[project]\nname='scrap-report'\n")
    (cli_dir / "cli.py").write_text("def main(): return 0\n")
    return root
