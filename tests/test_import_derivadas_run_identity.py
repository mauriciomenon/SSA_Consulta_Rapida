from __future__ import annotations

from core import app_logic


def test_falha_no_scan_preserva_id_do_run_que_foi_comitado(monkeypatch):
    marked = []
    errors = []

    def fail_scan(**kwargs):
        raise RuntimeError("scan interrompido apos outro sync")

    monkeypatch.setattr(
        app_logic,
        "sync_derivadas",
        lambda **kwargs: {"sync_run_id": 41, "merge_stats": {"merged_edges": 1}},
    )
    monkeypatch.setattr(app_logic, "scan_derivadas_consistency", fail_scan)
    monkeypatch.setattr(
        app_logic,
        "mark_latest_sync_run_failed",
        lambda **kwargs: marked.append(kwargs) or True,
    )
    _, blocking, _ = app_logic._run_optional_derivadas_sync(
        auto_derivadas_sync_enabled=True,
        successfully_processed_files=[],
        derivadas_sheet_files=[],
        db_only_derivadas_sync=True,
        should_cancel=None,
        working_db_path="ssas.db",
        table_name="ssa_table",
        docs_dir="planilhas",
        critical_errors=errors,
        emit_progress=lambda *args: None,
    )
    assert blocking is True
    assert len(marked) == 1
    assert marked[0]["sync_run_id"] == 41
    assert len(errors) == 1
