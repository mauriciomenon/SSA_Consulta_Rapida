from __future__ import annotations

import subprocess
from pathlib import Path

from scripts import smoke_cli


def test_count_imported_rows_closes_connection(monkeypatch, tmp_path: Path) -> None:
    class FakeCursor:
        @staticmethod
        def fetchone() -> tuple[int]:
            return (1,)

    class FakeConnection:
        closed = False

        @staticmethod
        def execute(_query: str, _parameters: tuple[str]) -> FakeCursor:
            return FakeCursor()

        def close(self) -> None:
            self.closed = True

    db_path = tmp_path / "ssas.db"
    db_path.touch()
    connection = FakeConnection()
    monkeypatch.setattr(smoke_cli.sqlite3, "connect", lambda _path: connection)

    rows = smoke_cli._count_imported_rows(db_path, smoke_cli.SMOKE_TABLE_NAME)

    assert rows == 1
    assert connection.closed is True


def test_smoke_cleanup_warning_does_not_fail_valid_import(monkeypatch, tmp_path: Path) -> None:
    def fake_copy_runtime_config(runtime_root: Path) -> Path:
        config_dir = runtime_root / "config"
        config_dir.mkdir(parents=True)
        return config_dir

    monkeypatch.setattr(smoke_cli, "_copy_runtime_config", fake_copy_runtime_config)
    monkeypatch.setattr(smoke_cli, "_write_smoke_workbook", lambda sample_path: None)
    monkeypatch.setattr(smoke_cli, "_count_imported_rows", lambda db_path, table_name: 1)
    monkeypatch.setattr(
        smoke_cli,
        "_run_cli_entry",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=["ssa-cli"],
            returncode=0,
            stdout="Importacao concluida\n",
            stderr="",
        ),
    )
    monkeypatch.setattr(
        smoke_cli.tempfile,
        "mkdtemp",
        lambda prefix: str(tmp_path / f"{prefix}locked"),
    )
    monkeypatch.setattr(
        smoke_cli.shutil,
        "rmtree",
        lambda path: (_ for _ in ()).throw(PermissionError("locked db")),
    )
    monkeypatch.setattr(smoke_cli.time, "sleep", lambda _seconds: None)

    result = smoke_cli.run_smoke()

    assert result["ok"] is True
    assert result["imported_rows"] == 1
    assert "PermissionError" in str(result["cleanup_warning"])


def test_smoke_main_prints_cleanup_warning(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        smoke_cli,
        "run_smoke",
        lambda executable=None: {
            "ok": True,
            "mode": "functional-import",
            "returncode": 0,
            "imported_rows": 1,
            "cleanup_warning": "PermissionError: locked db",
        },
    )

    exit_code = smoke_cli.main([])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Aviso cleanup" in captured.out
    assert "PermissionError: locked db" in captured.out
