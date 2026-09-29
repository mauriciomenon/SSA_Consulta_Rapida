import sqlite3

from gui.ssa.derivadas_table_resolver import resolve_derivadas_table_name


def test_resolver_does_not_create_missing_database(tmp_path):
    db_path = tmp_path / "missing.db"

    assert resolve_derivadas_table_name(
        str(db_path), ["ssas", "ssa_table"], "ssa_table"
    ) == "ssa_table"
    assert not db_path.exists()


def test_resolver_selects_first_compatible_table(tmp_path):
    db_path = tmp_path / "existing.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE ssas (numero_ssa TEXT)")
        conn.execute("CREATE TABLE ssa_table (numero_ssa TEXT, derivada_de TEXT)")

    assert resolve_derivadas_table_name(
        str(db_path), ["ssas", "ssa_table"], "ssas"
    ) == "ssa_table"
