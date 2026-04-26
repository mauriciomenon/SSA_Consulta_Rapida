from __future__ import annotations

from launchers.build_complete import _get_project_root


PROJECT_ROOT = _get_project_root()


def test_general_search_contract_lists_reprobaciones_as_real_schema_column() -> None:
    contract = (
        PROJECT_ROOT / "docs" / "GUI_GENERAL_SEARCH_COLUMN_CONTRACT.md"
    ).read_text(encoding="utf-8")
    schema = (PROJECT_ROOT / "config" / "schema_unified.sql").read_text(
        encoding="utf-8"
    )

    assert "`num_reprogramacoes`" in contract
    assert "`num_reprobaciones`" in contract
    assert "num_reprogramacoes INTEGER" in schema
    assert "num_reprobaciones INTEGER" in schema
