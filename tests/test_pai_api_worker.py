from __future__ import annotations

from concurrent.futures import Future
from pathlib import Path
from typing import Any

from core.pai_api_options import normalize_pai_api_options
from core.pai_import_service import PaiFetchedXlsxPreview, PaiImportResult
from core.pai_scrap_report_provider import PaiScrapReportExport
from core.pai_scrap_report_provider import PaiScrapReportCertificate
from core.pai_scrap_report_provider import PaiScrapReportRequest
from gui.workers import pai_api_worker
from gui.workers.pai_api_worker import PaiApiRefreshWorker, PaiApiWorkerConfig


def test_pai_api_worker_refreshes_each_executor_sector(
    monkeypatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, Any] = {"requests": [], "import_requests": []}

    def _fake_fetch(request, *, docs_dir):
        captured["preview_calls"] = int(captured.get("preview_calls", 0)) + 1
        captured["requests"].append(request)
        captured["docs_dir"] = docs_dir
        return PaiFetchedXlsxPreview(
            export=PaiScrapReportExport(
                command=("cmd",),
                scrap_report_root=tmp_path,
                manifest_path=tmp_path / "manifest.json",
                xlsx_path=tmp_path / "data.xlsx",
                manifest={},
                stdout="",
                stderr="",
            ),
            import_xlsx_path=tmp_path / "import.xlsx",
            normalized_rows=2,
        )

    def _fake_import(request, preview, *, docs_dir, db_path):
        captured["import_calls"] = int(captured.get("import_calls", 0)) + 1
        captured["import_requests"].append(request)
        captured["preview"] = preview
        captured["import_docs_dir"] = docs_dir
        captured["db_path"] = db_path
        return PaiImportResult(
            export=preview.export,
            mode="import",
            import_xlsx_path=preview.import_xlsx_path,
            staged_files=("import.xlsx",),
            staging_summary={"staged": 1},
            imported=True,
            normalized_rows=preview.normalized_rows,
            rows_before_import=0,
            rows_after_import=2,
        )

    monkeypatch.setattr(pai_api_worker, "fetch_pai_xlsx_preview", _fake_fetch)
    monkeypatch.setattr(pai_api_worker, "import_prepared_pai_xlsx", _fake_import)
    monkeypatch.setattr(
        pai_api_worker,
        "run_pai_scrap_report_ca_export",
        lambda request: PaiScrapReportCertificate(
            command=("cert",),
            scrap_report_root=tmp_path,
            ca_file=tmp_path / "ca.pem",
            manifest_path=tmp_path / "cert.json",
            stdout="",
            stderr="",
        ),
    )
    worker = PaiApiRefreshWorker(
        PaiApiWorkerConfig(
            project_root=tmp_path,
            docs_dir=tmp_path / "docs",
            db_path=tmp_path / "ssas.db",
            output_dir=tmp_path / "pai",
            options=normalize_pai_api_options(
                {
                    "executor_sectors": ["IEE3", "MEL4", "MEL3"],
                    "sam_username": "sam.user",
                    "secret_service": "scrap_report.sam",  # pragma: allowlist secret
                    "secure_required": True,
                }
            ),
        )
    )

    worker.run()

    assert sorted(request.executor_sectors for request in captured["requests"]) == [
        ("IEE3",),
        ("MEL3",),
        ("MEL4",),
    ]
    assert [request.executor_sectors for request in captured["import_requests"]] == [
        ("IEE3",),
        ("MEL4",),
        ("MEL3",),
    ]
    assert sorted(str(request.output_dir) for request in captured["requests"]) == [
        str(tmp_path / "pai" / "IEE3"),
        str(tmp_path / "pai" / "MEL3"),
        str(tmp_path / "pai" / "MEL4"),
    ]
    assert all(request.ca_file == tmp_path / "ca.pem" for request in captured["requests"])
    assert all(request.include_details is True for request in captured["requests"])
    assert all(request.username == "sam.user" for request in captured["requests"])
    assert all(
        request.secret_service == "scrap_report.sam"  # pragma: allowlist secret
        for request in captured["requests"]
    )
    assert all(request.secure_required is True for request in captured["requests"])
    assert captured["preview_calls"] == 3
    assert captured["import_calls"] == 3
    assert captured["docs_dir"].parent == tmp_path / "docs" / "pai_api"
    assert captured["import_docs_dir"].parent == tmp_path / "docs" / "pai_api"
    assert captured["db_path"] == tmp_path / "ssas.db"
    assert captured["preview"].normalized_rows == 2
    assert len(worker.results) == 3
    assert worker.failures == []


def test_pai_api_worker_refreshes_executadas_without_ca_validation(
    monkeypatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, Any] = {"requests": [], "ca_calls": 0}

    def _fake_fetch(request, *, docs_dir):
        captured["requests"].append(request)
        captured["docs_dir"] = docs_dir
        return PaiFetchedXlsxPreview(
            export=PaiScrapReportExport(
                command=("cmd",),
                scrap_report_root=tmp_path,
                manifest_path=tmp_path / "manifest.json",
                xlsx_path=tmp_path / "data.xlsx",
                manifest={},
                stdout="",
                stderr="",
            ),
            import_xlsx_path=tmp_path / "import.xlsx",
            normalized_rows=2,
        )

    monkeypatch.setattr(pai_api_worker, "fetch_pai_xlsx_preview", _fake_fetch)
    monkeypatch.setattr(
        pai_api_worker,
        "run_pai_scrap_report_ca_export",
        lambda _request: captured.__setitem__("ca_calls", captured["ca_calls"] + 1),
    )
    worker = PaiApiRefreshWorker(
        PaiApiWorkerConfig(
            project_root=tmp_path,
            docs_dir=tmp_path / "docs",
            db_path=tmp_path / "ssas.db",
            output_dir=tmp_path / "pai",
            options=normalize_pai_api_options(
                {
                    "executor_sectors": ["IEE3"],
                    "data_scopes": ["executadas"],
                    "sam_username": "sam.user",
                    "secure_required": True,
                }
            ),
            fetch_only=True,
        )
    )

    worker.run()

    assert captured["ca_calls"] == 0
    assert len(captured["requests"]) == 1
    request = captured["requests"][0]
    assert request.data_scope == "executadas"
    assert request.include_details is False
    assert request.ca_file is None
    assert request.username == "sam.user"
    assert request.secure_required is True
    assert request.output_dir == tmp_path / "pai" / "executadas" / "IEE3"
    assert captured["docs_dir"] == tmp_path / "docs" / "pai_api" / "executadas" / "IEE3"
    assert worker.summary().import_skipped is True


def test_pai_api_worker_keeps_scraper_scope_when_rest_ca_fails(
    monkeypatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, Any] = {"requests": [], "errors": []}

    def _fake_fetch(request, *, docs_dir):
        _ = docs_dir
        captured["requests"].append(request)
        return PaiFetchedXlsxPreview(
            export=PaiScrapReportExport(
                command=("cmd",),
                scrap_report_root=tmp_path,
                manifest_path=tmp_path / "manifest.json",
                xlsx_path=tmp_path / "data.xlsx",
                manifest={},
                stdout="",
                stderr="",
            ),
            import_xlsx_path=tmp_path / "import.xlsx",
            normalized_rows=2,
        )

    def _fail_ca(_request):
        raise RuntimeError("CA unavailable")

    monkeypatch.setattr(pai_api_worker, "fetch_pai_xlsx_preview", _fake_fetch)
    monkeypatch.setattr(pai_api_worker, "run_pai_scrap_report_ca_export", _fail_ca)
    worker = PaiApiRefreshWorker(
        PaiApiWorkerConfig(
            project_root=tmp_path,
            docs_dir=tmp_path / "docs",
            db_path=tmp_path / "ssas.db",
            output_dir=tmp_path / "pai",
            options=normalize_pai_api_options(
                {
                    "executor_sectors": ["IEE3"],
                    "data_scopes": ["consulta", "executadas"],
                    "sam_username": "sam.user",
                }
            ),
            fetch_only=True,
        )
    )
    worker.error_line.connect(captured["errors"].append)

    worker.run()

    assert [request.data_scope for request in captured["requests"]] == ["executadas"]
    assert len(captured["errors"]) == 1
    assert "CA" in captured["errors"][0]
    assert worker.summary().previewed_sectors == 1


def test_pai_api_worker_rejects_executadas_without_username(tmp_path: Path) -> None:
    errors: list[str] = []
    worker = PaiApiRefreshWorker(
        PaiApiWorkerConfig(
            project_root=tmp_path,
            docs_dir=tmp_path / "docs",
            db_path=tmp_path / "ssas.db",
            output_dir=tmp_path / "pai",
            options=normalize_pai_api_options(
                {
                    "executor_sectors": ["IEE3"],
                    "data_scopes": ["executadas"],
                }
            ),
        )
    )
    worker.finished_error.connect(errors.append)

    worker.run()

    assert errors == ["Usuario SAM obrigatorio para xpath/scrap_report."]
    assert worker.results == []


def test_pai_api_worker_refreshes_both_aprovacao_scopes(
    monkeypatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, Any] = {"requests": [], "docs_dirs": [], "progress": []}

    def _fake_fetch(request, *, docs_dir):
        captured["requests"].append(request)
        captured["docs_dirs"].append(docs_dir)
        return PaiFetchedXlsxPreview(
            export=PaiScrapReportExport(
                command=("cmd",),
                scrap_report_root=tmp_path,
                manifest_path=tmp_path / "manifest.json",
                xlsx_path=tmp_path / "data.xlsx",
                manifest={},
                stdout="",
                stderr="",
            ),
            import_xlsx_path=tmp_path / "import.xlsx",
            normalized_rows=1,
        )

    monkeypatch.setattr(pai_api_worker, "fetch_pai_xlsx_preview", _fake_fetch)
    worker = PaiApiRefreshWorker(
        PaiApiWorkerConfig(
            project_root=tmp_path,
            docs_dir=tmp_path / "docs",
            db_path=tmp_path / "ssas.db",
            output_dir=tmp_path / "pai",
            options=normalize_pai_api_options(
                {
                    "executor_sectors": ["IEE3"],
                    "data_scopes": [
                        "aprovacao_emissao",
                        "aprovacao_cancelamento",
                    ],
                    "sam_username": "sam.user",
                }
            ),
            fetch_only=True,
        )
    )
    def _capture_progress(value, message):
        _ = message
        captured["progress"].append(value)

    worker.progress.connect(_capture_progress)

    worker.run()

    assert [request.data_scope for request in captured["requests"]] == [
        "aprovacao_emissao",
        "aprovacao_cancelamento",
    ]
    assert [request.report_kind for request in captured["requests"]] == [
        "aprovacao_emissao",
        "aprovacao_cancelamento",
    ]
    assert [request.output_dir for request in captured["requests"]] == [
        tmp_path / "pai" / "aprovacao_emissao" / "IEE3",
        tmp_path / "pai" / "aprovacao_cancelamento" / "IEE3",
    ]
    assert captured["docs_dirs"] == [
        tmp_path / "docs" / "pai_api" / "aprovacao_emissao" / "IEE3",
        tmp_path / "docs" / "pai_api" / "aprovacao_cancelamento" / "IEE3",
    ]
    assert worker.summary().previewed_sectors == 2
    assert captured["progress"] == sorted(captured["progress"])


def test_pai_api_worker_continues_after_sector_failure(
    monkeypatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, Any] = {"import_requests": []}

    def _fake_fetch(request, *, docs_dir):
        _ = docs_dir
        sector = request.executor_sectors[0]
        if sector == "IEE3":
            raise RuntimeError("GetPendingSSAsByLocalizacaoRange failed")
        return PaiFetchedXlsxPreview(
            export=PaiScrapReportExport(
                command=("cmd", sector),
                scrap_report_root=tmp_path,
                manifest_path=tmp_path / f"{sector}.json",
                xlsx_path=tmp_path / f"{sector}.xlsx",
                manifest={},
                stdout="",
                stderr="",
            ),
            import_xlsx_path=tmp_path / f"{sector}_import.xlsx",
            normalized_rows=1,
        )

    def _fake_import(request, preview, *, docs_dir, db_path):
        _ = preview, docs_dir, db_path
        captured["import_requests"].append(request)
        return PaiImportResult(
            export=preview.export,
            mode="import",
            import_xlsx_path=preview.import_xlsx_path,
            staged_files=(str(preview.import_xlsx_path),),
            staging_summary={"staged": 1},
            imported=True,
            normalized_rows=preview.normalized_rows,
            rows_before_import=0,
            rows_after_import=1,
        )

    monkeypatch.setattr(pai_api_worker, "fetch_pai_xlsx_preview", _fake_fetch)
    monkeypatch.setattr(pai_api_worker, "import_prepared_pai_xlsx", _fake_import)
    monkeypatch.setattr(
        pai_api_worker,
        "run_pai_scrap_report_ca_export",
        lambda request: PaiScrapReportCertificate(
            command=("cert",),
            scrap_report_root=tmp_path,
            ca_file=tmp_path / "ca.pem",
            manifest_path=tmp_path / "cert.json",
            stdout="",
            stderr="",
        ),
    )
    worker = PaiApiRefreshWorker(
        PaiApiWorkerConfig(
            project_root=tmp_path,
            docs_dir=tmp_path / "docs",
            db_path=tmp_path / "ssas.db",
            output_dir=tmp_path / "pai",
            options=normalize_pai_api_options(
                {"executor_sectors": ["IEE3", "MEL4"]}
            ),
        )
    )

    worker.run()

    assert [request.executor_sectors for request in captured["import_requests"]] == [
        ("MEL4",)
    ]
    assert len(worker.results) == 1
    assert len(worker.failures) == 1
    assert "setor IEE3" in worker.failures[0]


def test_pai_api_worker_waits_for_import_confirmation(
    monkeypatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, Any] = {"import_calls": 0, "decisions": []}

    def _fake_fetch(request, *, docs_dir):
        _ = request, docs_dir
        return PaiFetchedXlsxPreview(
            export=PaiScrapReportExport(
                command=("cmd",),
                scrap_report_root=tmp_path,
                manifest_path=tmp_path / "manifest.json",
                xlsx_path=tmp_path / "data.xlsx",
                manifest={},
                stdout="",
                stderr="",
            ),
            import_xlsx_path=tmp_path / "import.xlsx",
            normalized_rows=2,
        )

    def _fake_import(request, preview, *, docs_dir, db_path):
        _ = request, docs_dir, db_path
        captured["import_calls"] += 1
        return PaiImportResult(
            export=preview.export,
            mode="import",
            import_xlsx_path=preview.import_xlsx_path,
            staged_files=("import.xlsx",),
            staging_summary={"staged": 1},
            imported=True,
            normalized_rows=preview.normalized_rows,
            rows_before_import=0,
            rows_after_import=2,
        )

    monkeypatch.setattr(pai_api_worker, "fetch_pai_xlsx_preview", _fake_fetch)
    monkeypatch.setattr(pai_api_worker, "import_prepared_pai_xlsx", _fake_import)
    monkeypatch.setattr(
        pai_api_worker,
        "run_pai_scrap_report_ca_export",
        lambda request: PaiScrapReportCertificate(
            command=("cert",),
            scrap_report_root=tmp_path,
            ca_file=tmp_path / "ca.pem",
            manifest_path=tmp_path / "cert.json",
            stdout="",
            stderr="",
        ),
    )
    worker = PaiApiRefreshWorker(
        PaiApiWorkerConfig(
            project_root=tmp_path,
            docs_dir=tmp_path / "docs",
            db_path=tmp_path / "ssas.db",
            output_dir=tmp_path / "pai",
            options=normalize_pai_api_options({"executor_sectors": ["IEE3"]}),
            confirm_before_import=True,
        )
    )
    worker.import_decision_required.connect(
        lambda request: (
            captured["decisions"].append(request),
            worker.set_import_decision(True),
        )
    )

    worker.run()

    assert len(captured["decisions"]) == 1
    assert captured["decisions"][0].normalized_rows == 2
    assert captured["import_calls"] == 1
    assert worker.summary().imported_sectors == 1


def test_pai_api_worker_cancel_confirmation_keeps_db_unchanged(
    monkeypatch,
    tmp_path: Path,
) -> None:
    import_calls = []

    def _fake_fetch(request, *, docs_dir):
        _ = request, docs_dir
        return PaiFetchedXlsxPreview(
            export=PaiScrapReportExport(
                command=("cmd",),
                scrap_report_root=tmp_path,
                manifest_path=tmp_path / "manifest.json",
                xlsx_path=tmp_path / "data.xlsx",
                manifest={},
                stdout="",
                stderr="",
            ),
            import_xlsx_path=tmp_path / "import.xlsx",
            normalized_rows=1,
        )

    def _fake_import(*args, **kwargs):
        import_calls.append((args, kwargs))
        raise AssertionError("import should wait for positive confirmation")

    monkeypatch.setattr(pai_api_worker, "fetch_pai_xlsx_preview", _fake_fetch)
    monkeypatch.setattr(pai_api_worker, "import_prepared_pai_xlsx", _fake_import)
    monkeypatch.setattr(
        pai_api_worker,
        "run_pai_scrap_report_ca_export",
        lambda request: PaiScrapReportCertificate(
            command=("cert",),
            scrap_report_root=tmp_path,
            ca_file=tmp_path / "ca.pem",
            manifest_path=tmp_path / "cert.json",
            stdout="",
            stderr="",
        ),
    )
    worker = PaiApiRefreshWorker(
        PaiApiWorkerConfig(
            project_root=tmp_path,
            docs_dir=tmp_path / "docs",
            db_path=tmp_path / "ssas.db",
            output_dir=tmp_path / "pai",
            options=normalize_pai_api_options({"executor_sectors": ["IEE3"]}),
            confirm_before_import=True,
        )
    )
    worker.import_decision_required.connect(lambda _request: worker.set_import_decision(False))

    worker.run()

    assert import_calls == []
    summary = worker.summary()
    assert summary.import_skipped is True
    assert summary.imported_sectors == 0
    assert summary.normalized_rows == 1


def test_pai_api_worker_confirmation_timeout_emits_error(
    monkeypatch,
    tmp_path: Path,
) -> None:
    import_calls = []
    finished_errors = []
    finished_successes = []

    def _fake_fetch(request, *, docs_dir):
        _ = request, docs_dir
        return PaiFetchedXlsxPreview(
            export=PaiScrapReportExport(
                command=("cmd",),
                scrap_report_root=tmp_path,
                manifest_path=tmp_path / "manifest.json",
                xlsx_path=tmp_path / "data.xlsx",
                manifest={},
                stdout="",
                stderr="",
            ),
            import_xlsx_path=tmp_path / "import.xlsx",
            normalized_rows=1,
        )

    def _fake_import(*args, **kwargs):
        import_calls.append((args, kwargs))
        raise AssertionError("import should not run after confirmation timeout")

    monkeypatch.setattr(pai_api_worker, "fetch_pai_xlsx_preview", _fake_fetch)
    monkeypatch.setattr(pai_api_worker, "import_prepared_pai_xlsx", _fake_import)
    monkeypatch.setattr(pai_api_worker, "PAI_API_IMPORT_CONFIRM_TIMEOUT_SECONDS", 0.01)
    monkeypatch.setattr(
        pai_api_worker,
        "run_pai_scrap_report_ca_export",
        lambda request: PaiScrapReportCertificate(
            command=("cert",),
            scrap_report_root=tmp_path,
            ca_file=tmp_path / "ca.pem",
            manifest_path=tmp_path / "cert.json",
            stdout="",
            stderr="",
        ),
    )
    worker = PaiApiRefreshWorker(
        PaiApiWorkerConfig(
            project_root=tmp_path,
            docs_dir=tmp_path / "docs",
            db_path=tmp_path / "ssas.db",
            output_dir=tmp_path / "pai",
            options=normalize_pai_api_options({"executor_sectors": ["IEE3"]}),
            confirm_before_import=True,
        )
    )
    worker.finished_error.connect(finished_errors.append)
    worker.finished_success.connect(lambda: finished_successes.append(True))

    worker.run()

    assert import_calls == []
    assert finished_successes == []
    assert len(finished_errors) == 1
    assert "confirmacao de importacao nao recebida" in finished_errors[0]
    assert worker.summary().import_skipped is False
    assert worker.summary().imported_sectors == 0


def test_pai_api_worker_does_not_import_when_all_sectors_fail(
    monkeypatch,
    tmp_path: Path,
) -> None:
    import_calls = []
    errors = []

    def _fake_fetch(request, *, docs_dir):
        _ = request, docs_dir
        raise RuntimeError("api unavailable")

    def _fake_import(*args, **kwargs):
        import_calls.append((args, kwargs))
        raise AssertionError("import should not run")

    monkeypatch.setattr(pai_api_worker, "fetch_pai_xlsx_preview", _fake_fetch)
    monkeypatch.setattr(pai_api_worker, "import_prepared_pai_xlsx", _fake_import)
    monkeypatch.setattr(
        pai_api_worker,
        "run_pai_scrap_report_ca_export",
        lambda request: PaiScrapReportCertificate(
            command=("cert",),
            scrap_report_root=tmp_path,
            ca_file=tmp_path / "ca.pem",
            manifest_path=tmp_path / "cert.json",
            stdout="",
            stderr="",
        ),
    )
    worker = PaiApiRefreshWorker(
        PaiApiWorkerConfig(
            project_root=tmp_path,
            docs_dir=tmp_path / "docs",
            db_path=tmp_path / "ssas.db",
            output_dir=tmp_path / "pai",
            options=normalize_pai_api_options({"executor_sectors": ["IEE3"]}),
        )
    )
    worker.finished_error.connect(errors.append)

    worker.run()

    assert import_calls == []
    assert worker.results == []
    assert len(worker.failures) == 1
    assert errors
    assert "DB inalterado" in errors[0]


def test_pai_api_worker_reports_ca_failure_before_fetch_or_import(
    monkeypatch,
    tmp_path: Path,
) -> None:
    fetch_calls = []
    import_calls = []
    errors = []

    def _fake_fetch(*args, **kwargs):
        fetch_calls.append((args, kwargs))
        raise AssertionError("fetch should not run after CA failure")

    def _fake_import(*args, **kwargs):
        import_calls.append((args, kwargs))
        raise AssertionError("import should not run after CA failure")

    monkeypatch.setattr(pai_api_worker, "fetch_pai_xlsx_preview", _fake_fetch)
    monkeypatch.setattr(pai_api_worker, "import_prepared_pai_xlsx", _fake_import)
    monkeypatch.setattr(
        pai_api_worker,
        "run_pai_scrap_report_ca_export",
        lambda request: (_ for _ in ()).throw(RuntimeError("CA unavailable")),
    )
    worker = PaiApiRefreshWorker(
        PaiApiWorkerConfig(
            project_root=tmp_path,
            docs_dir=tmp_path / "docs",
            db_path=tmp_path / "ssas.db",
            output_dir=tmp_path / "pai",
            options=normalize_pai_api_options({"executor_sectors": ["IEE3"]}),
        )
    )
    worker.finished_error.connect(errors.append)

    worker.run()

    assert fetch_calls == []
    assert import_calls == []
    assert errors
    assert "falha ao validar CA" in errors[0]
    assert "DB inalterado" in errors[0]


def test_pai_api_worker_records_unhandled_failure_in_summary(
    monkeypatch,
    tmp_path: Path,
) -> None:
    errors: list[str] = []

    def _raise_unhandled(_self) -> None:
        raise RuntimeError("unexpected worker failure")

    monkeypatch.setattr(PaiApiRefreshWorker, "_run_refresh", _raise_unhandled)
    worker = PaiApiRefreshWorker(
        PaiApiWorkerConfig(
            project_root=tmp_path,
            docs_dir=tmp_path / "docs",
            db_path=tmp_path / "ssas.db",
            output_dir=tmp_path / "pai",
            options=normalize_pai_api_options({"executor_sectors": ["IEE3"]}),
        )
    )
    worker.finished_error.connect(errors.append)

    worker.run()

    assert errors == ["unexpected worker failure"]
    assert worker.failures == ["unexpected worker failure"]
    assert worker.summary().failures == ("unexpected worker failure",)


def test_pai_api_worker_records_preview_future_timeout(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(pai_api_worker, "PAI_API_FETCH_FUTURE_GRACE_SECONDS", 0.0)
    worker = PaiApiRefreshWorker(
        PaiApiWorkerConfig(
            project_root=tmp_path,
            docs_dir=tmp_path / "docs",
            db_path=tmp_path / "ssas.db",
            output_dir=tmp_path / "pai",
            options=normalize_pai_api_options({"executor_sectors": ["IEE3"]}),
        )
    )
    errors: list[str] = []
    worker.error_line.connect(errors.append)
    sector_request_cls = getattr(pai_api_worker, "_PaiSectorRequest")
    request = sector_request_cls(
        sector="IEE3",
        request=PaiScrapReportRequest(
            project_root=tmp_path,
            output_dir=tmp_path / "out",
            executor_sectors=("IEE3",),
            command_timeout_seconds=0.0,
        ),
        docs_dir=tmp_path / "docs" / "IEE3",
        progress_base=10,
    )
    pending: Future[Any] = Future()

    preview_from_future = getattr(worker, "_sector_preview_from_future")
    preview = preview_from_future(request, pending)

    assert preview is None
    assert errors == ["setor IEE3: timeout ao obter preview (0s)"]
    assert worker.summary().failed_sectors == 1


def test_pai_api_worker_emits_fallback_message_for_empty_exception(
    monkeypatch,
    tmp_path: Path,
) -> None:
    errors: list[str] = []

    def _raise_unhandled(_self) -> None:
        raise RuntimeError()

    monkeypatch.setattr(PaiApiRefreshWorker, "_run_refresh", _raise_unhandled)
    worker = PaiApiRefreshWorker(
        PaiApiWorkerConfig(
            project_root=tmp_path,
            docs_dir=tmp_path / "docs",
            db_path=tmp_path / "ssas.db",
            output_dir=tmp_path / "pai",
            options=normalize_pai_api_options({"executor_sectors": ["IEE3"]}),
        )
    )
    worker.finished_error.connect(errors.append)

    worker.run()

    assert errors == ["RuntimeError"]
    assert worker.failures == ["RuntimeError"]
