from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from core.pai_import_service import fetch_and_import_pai_xlsx, preview_existing_pai_xlsx
from core.pai_scrap_report_provider import (
    build_pai_scrap_report_command,
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


def test_build_pai_scrap_report_command_uses_sweep_run_for_executadas(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scrap_root = _make_scrap_report_root(tmp_path)
    output_dir = tmp_path / "out"
    monkeypatch.setattr("core.pai_scrap_report_provider.shutil.which", lambda _: "/bin/uv")

    command, _execution, manifest_path, fallback_xlsx_path = build_pai_scrap_report_command(
        PaiScrapReportRequest(
            project_root=tmp_path,
            output_dir=output_dir,
            scrap_report_root=scrap_root,
            data_scope="executadas",
            executor_sectors=("IEE3", "MEL4"),
            number_of_years=2,
            limit=123,
            username="sam.user",
            secret_service="scrap_report.sam",  # pragma: allowlist secret
            secure_required=True,
        )
    )

    assert "sweep-run" in command
    assert "sam-api-flow" not in command
    assert command[command.index("--report-kind") + 1] == "executadas"
    assert command[command.index("--runtime") + 1] == "playwright"
    assert command[command.index("--scope-mode") + 1] == "executor"
    assert command[command.index("--number-of-years") + 1] == "2"
    assert command[command.index("--limit") + 1] == "123"
    executor_index = command.index("--setores-executor")
    assert command[executor_index + 1 : executor_index + 3] == ("IEE3", "MEL4")
    assert command[command.index("--username") + 1] == "sam.user"
    assert command[command.index("--secret-service") + 1] == "scrap_report.sam"
    assert "--secure-required" in command
    assert manifest_path == output_dir / "pai_sam_api_manifest.json"
    assert fallback_xlsx_path == output_dir / "pai_sam_api.xlsx"


def test_build_pai_scrap_report_command_adds_include_details_for_consulta(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scrap_root = _make_scrap_report_root(tmp_path)
    output_dir = tmp_path / "out"
    monkeypatch.setattr("core.pai_scrap_report_provider.shutil.which", lambda _: "/bin/uv")

    command, _execution, _manifest_path, _fallback_xlsx_path = (
        build_pai_scrap_report_command(
            PaiScrapReportRequest(
                project_root=tmp_path,
                output_dir=output_dir,
                scrap_report_root=scrap_root,
                include_details=True,
            )
        )
    )

    assert "sam-api-flow" in command
    assert "--include-details" in command


def test_build_pai_scrap_report_command_requires_username_for_secure_sweep(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scrap_root = _make_scrap_report_root(tmp_path)
    monkeypatch.setattr("core.pai_scrap_report_provider.shutil.which", lambda _: "/bin/uv")

    with pytest.raises(ValueError, match="Usuario SAM obrigatorio"):
        build_pai_scrap_report_command(
            PaiScrapReportRequest(
                project_root=tmp_path,
                scrap_report_root=scrap_root,
                data_scope="executadas",
                secure_required=True,
            )
        )


def test_run_pai_scrap_report_export_reads_sweep_manifest_reports(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scrap_root = _make_scrap_report_root(tmp_path)
    output_dir = tmp_path / "out"
    xlsx_path = output_dir / "staging" / "reports" / "executadas.xlsx"
    monkeypatch.setattr("core.pai_scrap_report_provider.shutil.which", lambda _: "/bin/uv")

    def runner(command: list[str], **kwargs: Any) -> _Completed:
        assert "sweep-run" in command
        assert "--output-json" in command
        xlsx_path.parent.mkdir(parents=True, exist_ok=True)
        xlsx_path.write_bytes(b"xlsx")
        (output_dir / "pai_sam_api_manifest.json").write_text(
            (
                '{"status":"ok","items":[{"status":"ok","reports":'
                '{"data_xlsx":"staging/reports/executadas.xlsx"}}]}'
            ),
            encoding="utf-8",
        )
        return _Completed()

    result = run_pai_scrap_report_export(
        PaiScrapReportRequest(
            project_root=tmp_path,
            output_dir=output_dir,
            scrap_report_root=scrap_root,
            data_scope="executadas",
            executor_sectors=("IEE3",),
        ),
        runner=runner,
    )

    assert result.xlsx_path == xlsx_path
    assert result.manifest["items"][0]["reports"]["data_xlsx"] == (
        "staging/reports/executadas.xlsx"
    )


def test_run_pai_scrap_report_export_allows_small_mtime_skew(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scrap_root = _make_scrap_report_root(tmp_path)
    output_dir = tmp_path / "out"
    xlsx_path = output_dir / "pai_sam_api.xlsx"
    monkeypatch.setattr("core.pai_scrap_report_provider.shutil.which", lambda _: "/bin/uv")
    monkeypatch.setattr("core.pai_scrap_report_provider.time.time", lambda: 100.0)

    def runner(_command: list[str], **_kwargs: Any) -> _Completed:
        output_dir.mkdir(exist_ok=True)
        xlsx_path.write_bytes(b"xlsx")
        xlsx_path.touch()
        (output_dir / "pai_sam_api_manifest.json").write_text(
            '{"status":"ok","exports":{"data_xlsx":"pai_sam_api.xlsx"}}',
            encoding="utf-8",
        )
        xlsx_path.touch()
        import os

        os.utime(xlsx_path, (99.0, 99.0))
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


def test_run_pai_scrap_report_export_reports_sweep_label_on_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scrap_root = _make_scrap_report_root(tmp_path)
    monkeypatch.setattr("core.pai_scrap_report_provider.shutil.which", lambda _: "/bin/uv")

    class _Failed:
        returncode = 1
        stdout = "failed password=secret"
        stderr = "failed token=secret"

    with pytest.raises(RuntimeError, match="scrap_report sweep-run falhou") as excinfo:
        run_pai_scrap_report_export(
            PaiScrapReportRequest(
                project_root=tmp_path,
                output_dir=tmp_path / "out",
                scrap_report_root=scrap_root,
                data_scope="executadas",
                executor_sectors=("IEE3",),
            ),
            runner=lambda _command, **_kwargs: _Failed(),
        )
    assert "stderr=present" in str(excinfo.value)
    assert "stdout=present" in str(excinfo.value)
    assert "token=" not in str(excinfo.value)
    assert "password=" not in str(excinfo.value)


def test_build_pai_scrap_report_command_requires_exact_aprovacao_report_kind(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scrap_root = _make_scrap_report_root(tmp_path)
    monkeypatch.setattr("core.pai_scrap_report_provider.shutil.which", lambda _: "/bin/uv")

    with pytest.raises(ValueError, match="aprovacao exige report_kind explicito"):
        build_pai_scrap_report_command(
            PaiScrapReportRequest(
                project_root=tmp_path,
                scrap_report_root=scrap_root,
                data_scope="aprovacao",
            )
        )


def test_build_pai_scrap_report_command_uses_sweep_for_explicit_report_kind(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scrap_root = _make_scrap_report_root(tmp_path)
    monkeypatch.setattr("core.pai_scrap_report_provider.shutil.which", lambda _: "/bin/uv")

    command, _execution, _manifest_path, _fallback_xlsx_path = (
        build_pai_scrap_report_command(
            PaiScrapReportRequest(
                project_root=tmp_path,
                scrap_report_root=scrap_root,
                report_kind="executadas",
                executor_sectors=("IEE3",),
            )
        )
    )

    assert "sweep-run" in command
    assert "sam-api-flow" not in command
    assert command[command.index("--report-kind") + 1] == "executadas"


def test_build_pai_scrap_report_command_allows_exact_aprovacao_report_kind(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scrap_root = _make_scrap_report_root(tmp_path)
    monkeypatch.setattr("core.pai_scrap_report_provider.shutil.which", lambda _: "/bin/uv")

    command, _execution, _manifest_path, _fallback_xlsx_path = (
        build_pai_scrap_report_command(
            PaiScrapReportRequest(
                project_root=tmp_path,
                scrap_report_root=scrap_root,
                data_scope="aprovacao",
                report_kind="aprovacao_emissao",
                emitter_sectors=("MEL4",),
            )
        )
    )

    assert "sweep-run" in command
    assert command[command.index("--report-kind") + 1] == "aprovacao_emissao"
    emitter_index = command.index("--setores-emissor")
    assert command[emitter_index + 1] == "MEL4"


def test_build_pai_scrap_report_command_rejects_report_kind_as_data_scope(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scrap_root = _make_scrap_report_root(tmp_path)
    monkeypatch.setattr("core.pai_scrap_report_provider.shutil.which", lambda _: "/bin/uv")

    with pytest.raises(ValueError, match="Escopo SAM API xpath invalido"):
        build_pai_scrap_report_command(
            PaiScrapReportRequest(
                project_root=tmp_path,
                scrap_report_root=scrap_root,
                data_scope="aprovacao_emissao",
                username="sam.user",
                secure_required=True,
            )
        )


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


def test_run_pai_scrap_report_export_accepts_absolute_manifest_path_in_output_dir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scrap_root = _make_scrap_report_root(tmp_path)
    output_dir = tmp_path / "out"
    xlsx_path = output_dir / "staging" / "reports" / "executadas.xlsx"
    monkeypatch.setattr("core.pai_scrap_report_provider.shutil.which", lambda _: "/bin/uv")

    def runner(_command: list[str], **_kwargs: Any) -> _Completed:
        xlsx_path.parent.mkdir(parents=True)
        xlsx_path.write_bytes(b"xlsx")
        (output_dir / "pai_sam_api_manifest.json").write_text(
            f'{{"status":"ok","exports":{{"data_xlsx":"{xlsx_path}"}}}}',
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


def test_run_pai_scrap_report_export_rejects_parent_manifest_path(
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
            '{"status":"ok","exports":{"data_xlsx":"../outside.xlsx"}}',
            encoding="utf-8",
        )
        return _Completed()

    with pytest.raises(ValueError, match="caminho relativo invalido"):
        run_pai_scrap_report_export(
            PaiScrapReportRequest(
                project_root=tmp_path,
                output_dir=output_dir,
                scrap_report_root=scrap_root,
            ),
            runner=runner,
        )


def test_run_pai_scrap_report_export_rejects_stale_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scrap_root = _make_scrap_report_root(tmp_path)
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    (output_dir / "pai_sam_api.xlsx").write_bytes(b"old")
    (output_dir / "pai_sam_api_manifest.json").write_text(
        '{"status":"ok","exports":{"data_xlsx":"pai_sam_api.xlsx"}}',
        encoding="utf-8",
    )
    monkeypatch.setattr("core.pai_scrap_report_provider.shutil.which", lambda _: "/bin/uv")

    with pytest.raises(FileNotFoundError, match="Manifest SAM API nao criado"):
        run_pai_scrap_report_export(
            PaiScrapReportRequest(
                project_root=tmp_path,
                output_dir=output_dir,
                scrap_report_root=scrap_root,
            ),
            runner=lambda _command, **_kwargs: _Completed(),
        )


def test_run_pai_scrap_report_export_ignores_malformed_manifest_items(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scrap_root = _make_scrap_report_root(tmp_path)
    output_dir = tmp_path / "out"
    xlsx_path = output_dir / "pai_sam_api.xlsx"
    monkeypatch.setattr("core.pai_scrap_report_provider.shutil.which", lambda _: "/bin/uv")

    def runner(_command: list[str], **_kwargs: Any) -> _Completed:
        output_dir.mkdir(exist_ok=True)
        xlsx_path.write_bytes(b"data")
        (output_dir / "pai_sam_api_manifest.json").write_text(
            '{"status":"ok","items":[1,"bad",null],'
            '"exports":{"data_xlsx":"pai_sam_api.xlsx"}}',
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
        (output_dir / "sam_api_cert.json").write_text('{"status":"ok"}', encoding="utf-8")
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


def test_run_pai_scrap_report_ca_export_rejects_stale_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scrap_root = _make_scrap_report_root(tmp_path)
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    (output_dir / "itaipu_root_ca.pem").write_text("OLD CERT", encoding="utf-8")
    (output_dir / "sam_api_cert.json").write_text('{"status":"ok"}', encoding="utf-8")
    monkeypatch.setattr("core.pai_scrap_report_provider.shutil.which", lambda _: "/bin/uv")

    with pytest.raises(FileNotFoundError, match="CA SAM API nao criada"):
        run_pai_scrap_report_ca_export(
            PaiScrapReportRequest(
                project_root=tmp_path,
                output_dir=output_dir,
                scrap_report_root=scrap_root,
            ),
            runner=lambda _command, **_kwargs: _Completed(),
        )


def test_run_pai_scrap_report_ca_export_rejects_error_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scrap_root = _make_scrap_report_root(tmp_path)
    output_dir = tmp_path / "out"
    monkeypatch.setattr("core.pai_scrap_report_provider.shutil.which", lambda _: "/bin/uv")

    def runner(_command: list[str], **_kwargs: Any) -> _Completed:
        output_dir.mkdir(exist_ok=True)
        (output_dir / "itaipu_root_ca.pem").write_text("CERT", encoding="utf-8")
        (output_dir / "sam_api_cert.json").write_text(
            '{"status":"error"}',
            encoding="utf-8",
        )
        return _Completed()

    with pytest.raises(RuntimeError, match="status=error"):
        run_pai_scrap_report_ca_export(
            PaiScrapReportRequest(
                project_root=tmp_path,
                output_dir=output_dir,
                scrap_report_root=scrap_root,
            ),
            runner=runner,
        )


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
    assert result.rows_before_import is None
    assert result.rows_after_import == 1
    assert result.import_xlsx_path == tmp_path / "docs_entrada" / "pai_ssa_import.xlsx"
    normalized = pd.read_excel(result.import_xlsx_path)
    assert normalized.loc[0, "sistema_origem"] == "SAM API"
    assert normalized.loc[0, "arquivo_origem"] == "pai.xlsx"
    assert result.staged_files == (str(tmp_path / "docs_entrada" / "pai_ssa_import.xlsx"),)
    assert staged_calls[0]["source_files"] == (str(result.import_xlsx_path),)
    assert staged_calls[0]["docs_dir"] == tmp_path / "docs_entrada"
    assert import_calls[0]["docs_dir"] == str(tmp_path / "docs_entrada")
    assert import_calls[0]["db_path"] == str(tmp_path / "data" / "ssas.db")


def test_preview_existing_pai_xlsx_normalizes_without_api_call(tmp_path: Path) -> None:
    source = tmp_path / "pai_local.xlsm"
    pd.DataFrame(
        {
            "ssa_number": [202600002],
            "description": ["Local PAI"],
            "issue_datetime": ["2026-01-08T13:56:00Z"],
            "executor_sector": ["MEL4"],
        }
    ).to_excel(source, index=False)

    preview = preview_existing_pai_xlsx(
        PaiScrapReportRequest(project_root=tmp_path),
        source,
        docs_dir=tmp_path / "docs_entrada",
    )

    assert preview.normalized_rows == 1
    normalized = pd.read_excel(preview.import_xlsx_path)
    assert str(normalized.loc[0, "numero_ssa"]) == "202600002"
    assert normalized.loc[0, "sistema_origem"] == "SAM API"
    assert normalized.loc[0, "arquivo_origem"] == "pai_local.xlsm"


def _make_scrap_report_root(tmp_path: Path) -> Path:
    root = tmp_path / "scrap_report"
    cli_dir = root / "src" / "scrap_report"
    cli_dir.mkdir(parents=True)
    (root / "pyproject.toml").write_text("[project]\nname='scrap-report'\n")
    (cli_dir / "cli.py").write_text("def main(): return 0\n")
    return root
