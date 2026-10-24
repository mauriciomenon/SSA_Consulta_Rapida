"""CF-15: GUI e script localizam o scrap_report pela mesma regra."""

from pathlib import Path

from core.pai_scrap_report_provider import scrap_report_location_from_env

ROOT = Path(__file__).resolve().parent.parent


def test_location_defaults_to_sibling_without_env(monkeypatch):
    monkeypatch.delenv("SSA_SCRAP_REPORT_ROOT", raising=False)
    monkeypatch.delenv("SSA_ALLOW_SIBLING_SCRAP_REPORT", raising=False)
    assert scrap_report_location_from_env() == (None, True)


def test_location_honors_env(monkeypatch, tmp_path):
    monkeypatch.setenv("SSA_SCRAP_REPORT_ROOT", str(tmp_path))
    monkeypatch.setenv("SSA_ALLOW_SIBLING_SCRAP_REPORT", "0")
    assert scrap_report_location_from_env() == (tmp_path, False)


def test_gui_and_script_use_the_shared_rule():
    for rel in ("gui/workers/pai_api_worker.py", "scripts/import_pai_api_xlsx.py"):
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert "scrap_report_location_from_env()" in text, rel
        assert "allow_sibling_scrap_report=True" not in text, rel
