from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
import pytest

from gui.ssa.database_operations import validate_database_candidate


def test_validate_database_candidate_raises_query_errors_explicitly():
    calls: list[dict[str, object]] = []

    def _query_db(*args, **kwargs):
        calls.append({"args": args, "kwargs": kwargs})
        raise RuntimeError("db open failed")

    result = validate_database_candidate(
        "/tmp/candidate.db",
        table_name="ssa_table",
        query_db_fn=_query_db,
    )

    assert result == {
        "ok": False,
        "error": "db open failed",
        "db_file": "/tmp/candidate.db",
    }
    assert calls[0]["kwargs"] == {"raise_on_error": True, "read_only": True}


def test_validate_database_candidate_accepts_non_empty_table():
    def _query_db(*args, **kwargs):
        return pd.DataFrame({"numero_ssa": ["202600001"]})

    result = validate_database_candidate(
        "/tmp/candidate.db",
        table_name="ssa_table",
        query_db_fn=_query_db,
    )

    assert result == {"ok": True, "db_file": "/tmp/candidate.db"}


def _make_db(path: Path, rows: list[str], wal: bool = False) -> Path:
    conn = sqlite3.connect(str(path))
    if wal:
        conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("CREATE TABLE ssa_table (numero_ssa TEXT)")
    conn.executemany("INSERT INTO ssa_table VALUES (?)", [(r,) for r in rows])
    conn.commit()
    conn.close()
    return path


def _read_rows(path: Path) -> list[str]:
    with sqlite3.connect(str(path)) as conn:
        return [r[0] for r in conn.execute("SELECT numero_ssa FROM ssa_table")]


def test_copy_database_into_data_dir_copies_external_db(tmp_path):
    from gui.ssa.database_operations import copy_database_into_data_dir

    src_dir = tmp_path / "externo"
    src_dir.mkdir()
    src = _make_db(src_dir / "meu_banco.db", ["202600001", "202600002"])
    data_dir = tmp_path / "data"

    result = copy_database_into_data_dir(str(src), data_dir=str(data_dir))

    assert result["ok"] is True
    assert result["copied"] is True
    assert result["archived"] is None
    dest = data_dir / "meu_banco.db"
    assert result["db_file"] == str(dest.resolve())
    assert _read_rows(dest) == ["202600001", "202600002"]
    # Origem intocada
    assert _read_rows(src) == ["202600001", "202600002"]


def test_copy_database_into_data_dir_noop_when_source_inside_data_dir(tmp_path):
    from gui.ssa.database_operations import copy_database_into_data_dir

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    src = _make_db(data_dir / "ssas.db", ["202600001"])

    result = copy_database_into_data_dir(str(src), data_dir=str(data_dir))

    assert result["ok"] is True
    assert result["copied"] is False
    assert result["db_file"] == str(src.resolve())


def test_copy_database_into_data_dir_archives_existing_dest(tmp_path):
    from gui.ssa.database_operations import copy_database_into_data_dir

    src_dir = tmp_path / "externo"
    src_dir.mkdir()
    src = _make_db(src_dir / "ssas.db", ["novo"])
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    _make_db(data_dir / "ssas.db", ["antigo"])

    result = copy_database_into_data_dir(str(src), data_dir=str(data_dir))

    assert result["ok"] is True
    assert result["copied"] is True
    assert result["archived"]
    archived = [p for p in data_dir.iterdir() if ".bak-" in p.name]
    assert len(archived) == 1
    assert _read_rows(archived[0]) == ["antigo"]
    assert _read_rows(data_dir / "ssas.db") == ["novo"]


def test_copy_database_into_data_dir_captures_wal_pending_commits(tmp_path):
    from gui.ssa.database_operations import copy_database_into_data_dir

    src_dir = tmp_path / "externo"
    src_dir.mkdir()
    src = src_dir / "wal.db"
    conn = sqlite3.connect(str(src))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("CREATE TABLE ssa_table (numero_ssa TEXT)")
    conn.execute("INSERT INTO ssa_table VALUES ('pendente')")
    conn.commit()
    assert (src_dir / "wal.db-wal").exists()

    data_dir = tmp_path / "data"
    result = copy_database_into_data_dir(str(src), data_dir=str(data_dir))
    conn.close()

    assert result["ok"] is True, result
    assert _read_rows(data_dir / "wal.db") == ["pendente"]


def test_copy_database_into_data_dir_case_alias_source_is_noop(tmp_path):
    """Em FS case-insensitive, data dir com case diferente nao deve
    arquivar/destruir a propria origem (bug reproduzido em APFS)."""
    from gui.ssa.database_operations import copy_database_into_data_dir

    data_dir = tmp_path / "Dados"
    data_dir.mkdir()
    src = _make_db(data_dir / "ssas.db", ["orig"])
    alias_dir = tmp_path / "dados"
    if not (alias_dir.exists() and alias_dir.samefile(data_dir)):
        pytest.skip("filesystem diferencia maiusculas")
    result = copy_database_into_data_dir(str(src), data_dir=str(alias_dir))
    assert result["ok"] is True
    assert result["copied"] is False
    assert src.exists()
    assert _read_rows(src) == ["orig"]


def test_copy_database_into_data_dir_failed_copy_preserves_dest(tmp_path):
    """Falha na copia nao pode remover nem arquivar o destino existente."""
    from gui.ssa.database_operations import copy_database_into_data_dir

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    dest = _make_db(data_dir / "x.db", ["antigo"])
    bad_src = tmp_path / "bad.db"
    bad_src.write_bytes(b"not a sqlite database at all")

    result = copy_database_into_data_dir(str(bad_src), data_dir=str(data_dir))

    assert result["ok"] is False
    assert _read_rows(dest) == ["antigo"]
    assert not list(data_dir.glob("*.bak-*"))
    assert not list(data_dir.glob("*.copy-*"))


def test_copy_database_into_data_dir_archives_orphan_dest_sidecars(tmp_path):
    """dest-wal/-shm orfaos (sem o .db) nao podem contaminar o destino novo."""
    from gui.ssa.database_operations import copy_database_into_data_dir

    src_dir = tmp_path / "externo"
    src_dir.mkdir()
    src = _make_db(src_dir / "x.db", ["novo"])
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "x.db-wal").write_text("wal orfao")
    (data_dir / "x.db-shm").write_text("shm orfao")

    result = copy_database_into_data_dir(str(src), data_dir=str(data_dir))

    assert result["ok"] is True, result
    assert result["archived"]
    baks = sorted(p.name for p in data_dir.iterdir() if ".bak-" in p.name)
    assert len(baks) == 2 and all(p.endswith(("-wal", "-shm")) for p in baks)
    assert not (data_dir / "x.db-wal").exists()
    assert _read_rows(data_dir / "x.db") == ["novo"]


def test_copy_database_into_data_dir_rejects_non_sqlite_source(tmp_path):
    from gui.ssa.database_operations import copy_database_into_data_dir

    src = tmp_path / "externo.db"
    src.write_text("isto nao e um sqlite")
    data_dir = tmp_path / "data"

    result = copy_database_into_data_dir(str(src), data_dir=str(data_dir))

    assert result["ok"] is False
    assert result["copied"] is False
    assert result["error"]
    assert not (data_dir / "externo.db").exists()


def test_copy_database_into_data_dir_missing_source(tmp_path):
    from gui.ssa.database_operations import copy_database_into_data_dir

    result = copy_database_into_data_dir(
        str(tmp_path / "inexistente.db"), data_dir=str(tmp_path / "data")
    )

    assert result["ok"] is False
    assert "nao existe" in result["error"]


def test_validate_database_candidate_never_modifies_source_with_hot_journal(
    tmp_path,
):
    """Validacao usa mode=ro: um -journal quente nao pode ser recuperado
    (escrito) no arquivo do usuario — a leitura falha ou le o estado
    anterior, mas a origem fica byte-a-byte intacta.

    O journal quente e produzido num subprocesso morto com os._exit: um
    writer vivo manteria lock RESERVED e o journal nao seria quente.
    """
    import hashlib
    import subprocess
    import sys

    from armazenamento.database import query_db

    src_dir = tmp_path / "externo"
    src_dir.mkdir()
    src = src_dir / "orig.db"
    conn = sqlite3.connect(str(src))
    conn.execute("PRAGMA journal_mode=DELETE")
    conn.execute("CREATE TABLE ssa_table (numero_ssa TEXT)")
    conn.execute("INSERT INTO ssa_table VALUES ('ok')")
    conn.commit()
    conn.close()

    # Writer morre sem commit/rollback com cache_size=1: o spill forca
    # paginas sujas no .db, deixando -journal genuinamente quente (writer
    # vivo seguraria lock RESERVED e o journal nao seria quente).
    subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import os, sqlite3, sys\n"
                "c = sqlite3.connect(sys.argv[1])\n"
                "c.execute('PRAGMA cache_size=1')\n"
                "c.execute('BEGIN IMMEDIATE')\n"
                "for i in range(200):\n"
                "    c.execute(\n"
                "        \"INSERT INTO ssa_table VALUES (?)\",\n"
                "        (('q' + str(i)) * 100,),\n"
                "    )\n"
                "os._exit(0)\n"
            ),
            str(src),
        ],
        check=True,
    )
    assert (src_dir / "orig.db-journal").exists()

    before = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in src_dir.iterdir()
    }
    result = validate_database_candidate(
        str(src),
        table_name="ssa_table",
        query_db_fn=query_db,
    )
    after = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in src_dir.iterdir()
    }

    assert after == before, "validacao modificou a origem"
    assert "ok" in result


def test_stage_database_copy_never_modifies_source_with_hot_wal(tmp_path):
    """Origem WAL com transacao aberta: copia deve sair sem tocar na origem.

    mode=ro impede que a leitura dispare recuperacao/checkpoint na origem
    (CodeRabbit): nenhum arquivo do diretorio de origem pode mudar.
    """
    import hashlib

    from gui.ssa.database_operations import stage_database_copy

    src_dir = tmp_path / "externo"
    src_dir.mkdir()
    src = _make_db(src_dir / "src.db", ["a", "b"], wal=True)
    writer = sqlite3.connect(str(src))
    writer.execute("BEGIN")
    writer.execute("INSERT INTO ssa_table VALUES ('quente')")
    try:
        before = {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in src_dir.iterdir()
        }
        dest_dir = tmp_path / "data"
        dest_dir.mkdir()
        result = stage_database_copy(src, dest_dir / "src.db")
        assert result["ok"] is True, result
        after = {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in src_dir.iterdir()
        }
        assert after == before, "origem foi modificada pela copia"
        staged_rows = _read_rows(Path(result["staged"]))
        assert {"a", "b"} <= set(staged_rows)
    finally:
        writer.close()
