import pytest

from interface.cli import get_ssa_query


def test_get_ssa_query_rejects_invalid_table_identifier():
    with pytest.raises(ValueError):
        get_ssa_query('ssa_table"; DROP TABLE ssa_table; --')


def test_get_ssa_query_accepts_valid_table_identifier():
    query = get_ssa_query("ssa_table")
    assert 'FROM "ssa_table"' in query


def test_get_ssa_query_accepts_legacy_aliases():
    query = get_ssa_query("ssas")
    assert 'FROM "ssa_table"' in query


def test_get_ssa_query_accepts_second_legacy_alias():
    query = get_ssa_query("ssa_chamados")
    assert 'FROM "ssa_table"' in query
