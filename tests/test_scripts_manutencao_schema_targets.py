import importlib.util
import sqlite3
from pathlib import Path


def _load_module(module_path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _create_test_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    schema_path = Path(__file__).resolve().parents[1] / "config" / "schema_unified.sql"
    with sqlite3.connect(db_path) as conn:
        conn.executescript(schema_path.read_text(encoding="utf-8"))
        conn.executemany(
            """
            INSERT INTO ssa_table (
                numero_ssa, situacao, descricao_ssa,
                localizacao_codigo, setor_executor, semana_cadastro
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                ("1001", "ABERTA", "desc 1", "LOC1", "SET1", "2026-W01"),
                ("1002", "FECHADA", "desc 2", "LOC2", "SET2", "2026-W02"),
            ],
        )


def test_analyze_db_integrity_uses_ssa_table_and_runs(tmp_path, monkeypatch):
    db_path = tmp_path / "data" / "ssas.db"
    _create_test_db(db_path)
    monkeypatch.chdir(tmp_path)

    module = _load_module(
        Path(__file__).resolve().parents[1] / "scripts_manutencao" / "analyze_db_integrity.py",
        "analyze_db_integrity_test",
    )
    result = module.analyze_database_integrity()

    assert module.TABLE_NAME == "ssa_table"
    assert isinstance(result, dict)
    assert result["total_records"] == 2


def test_verificar_integridade_uses_ssa_table_and_passes(tmp_path, monkeypatch):
    db_path = tmp_path / "data" / "ssas.db"
    _create_test_db(db_path)
    monkeypatch.chdir(tmp_path)

    module = _load_module(
        Path(__file__).resolve().parents[1] / "scripts_manutencao" / "verificar_integridade.py",
        "verificar_integridade_test",
    )
    ok = module.verificar_integridade()

    assert module.TABLE_NAME == "ssa_table"
    assert ok is True


def test_limpar_banco_targets_ssa_table_and_clears(tmp_path, monkeypatch):
    db_path = tmp_path / "data" / "ssas.db"
    _create_test_db(db_path)
    monkeypatch.chdir(tmp_path)

    module = _load_module(
        Path(__file__).resolve().parents[1] / "scripts_manutencao" / "limpar_banco.py",
        "limpar_banco_test",
    )
    ok = module.limpar_banco()

    assert module.TABLE_NAME == "ssa_table"
    assert ok is True
    with sqlite3.connect(db_path) as conn:
        remaining = conn.execute("SELECT COUNT(*) FROM ssa_table").fetchone()[0]
    assert remaining == 0
