from __future__ import annotations

from pathlib import Path

from core.pai_api_options import normalize_pai_api_options
from core.pai_import_service import PaiImportResult
from core.pai_scrap_report_provider import PaiScrapReportExport
from gui.workers import pai_api_worker
from gui.workers.pai_api_worker import PaiApiRefreshWorker, PaiApiWorkerConfig


def test_pai_api_worker_batches_executor_sectors(monkeypatch, tmp_path: Path) -> None:
    captured = {}

    def _fake_fetch(request, *, docs_dir, db_path):
        captured["request"] = request
        captured["docs_dir"] = docs_dir
        captured["db_path"] = db_path
        return PaiImportResult(
            export=PaiScrapReportExport(
                command=("cmd",),
                scrap_report_root=tmp_path,
                manifest_path=tmp_path / "manifest.json",
                xlsx_path=tmp_path / "data.xlsx",
                manifest={},
                stdout="",
                stderr="",
            ),
            mode="import",
            import_xlsx_path=tmp_path / "import.xlsx",
            staged_files=("import.xlsx",),
            staging_summary={"staged": 1},
            imported=True,
            normalized_rows=2,
            rows_before_import=0,
            rows_after_import=2,
        )

    monkeypatch.setattr(pai_api_worker, "fetch_and_import_pai_xlsx", _fake_fetch)
    worker = PaiApiRefreshWorker(
        PaiApiWorkerConfig(
            project_root=tmp_path,
            docs_dir=tmp_path / "docs",
            db_path=tmp_path / "ssas.db",
            output_dir=tmp_path / "pai",
            options=normalize_pai_api_options(
                {"executor_sectors": ["IEE3", "MEL4", "MEL3"]}
            ),
        )
    )

    worker.run()

    assert captured["request"].executor_sectors == ("IEE3", "MEL4", "MEL3")
    assert captured["docs_dir"] == tmp_path / "docs"
    assert captured["db_path"] == tmp_path / "ssas.db"
    assert len(worker.results) == 1
