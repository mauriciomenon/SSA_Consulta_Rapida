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
    src_dir = tmp_path / "externo"
    src_dir.mkdir()
    # Mesmo basename do destino: sem isso a falha ocorreria sobre
    # data/bad.db e a preservacao de um destino existente nao seria
    # exercitada.
    bad_src = src_dir / "x.db"
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
    # mode=ro nao pode recuperar o journal quente: a leitura falha.
    assert result["ok"] is False


def test_stage_database_copy_never_modifies_source_with_hot_wal(tmp_path):
    """Origem WAL com transacao aberta: copia deve sair sem tocar na origem.

    mode=ro impede que a leitura dispare recuperacao/checkpoint na origem
    (CodeRabbit): nenhum arquivo do diretorio de origem pode mudar.
    """
    import hashlib

    from gui.ssa import database_operations as ssa_ops

    src_dir = tmp_path / "externo"
    src_dir.mkdir()
    src = _make_db(src_dir / "src.db", ["a", "b"], wal=True)
    writer = sqlite3.connect(str(src))
    writer.execute("BEGIN")
    writer.execute("INSERT INTO ssa_table VALUES ('quente')")
    result: dict = {}
    try:
        before = {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in src_dir.iterdir()
        }
        dest_dir = tmp_path / "data"
        dest_dir.mkdir()
        result = ssa_ops.stage_database_copy(src, dest_dir / "src.db")
        assert result["ok"] is True, result
        after = {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in src_dir.iterdir()
        }
        assert after == before, "origem foi modificada pela copia"
        assert not any(
            Path(f"{result['staged']}{suffix}").exists()
            for suffix in ("-wal", "-shm", "-journal")
        )
        staged_rows = _read_rows(Path(result["staged"]))
        assert {"a", "b"} <= set(staged_rows)
    finally:
        writer.close()
        if result.get("staged"):
            # Desregistra alem de remover o arquivo: uma entrada orfa no
            # registro bloquearia o fechamento da GUI em testes seguintes.
            ssa_ops.discard_staged_copy(result["staged"])


def test_get_db_connection_rejects_read_only_memory():
    """read_only=True em :memory: contradiz a semantica de origem —
    deve falhar explicito, nao abrir banco vazio."""
    from armazenamento.database import get_db_connection

    with pytest.raises(ValueError, match=":memory:"):
        with get_db_connection(":memory:", read_only=True):
            pass


def test_stage_database_copy_sweeps_stale_partial(tmp_path):
    """Um .copy-* antigo (parcial de copia interrompida) e removido no
    proximo staging; um recente e preservado."""
    import os
    import time

    from gui.ssa import database_operations as ssa_ops
    from gui.ssa.database_operations import (
        STALE_STAGED_COPY_MIN_AGE_SEC,
        stage_database_copy,
    )

    src_dir = tmp_path / "externo"
    src_dir.mkdir()
    src = _make_db(src_dir / "src.db", ["a"])
    dest_dir = tmp_path / "data"
    dest_dir.mkdir()
    dest = dest_dir / "src.db"

    stale = dest_dir / "src.db.copy-20000101_000000_000000"
    stale.write_bytes(b"partial")
    old = time.time() - STALE_STAGED_COPY_MIN_AGE_SEC - 60
    os.utime(stale, (old, old))
    recent = dest_dir / "src.db.copy-29990101_000000_000000"
    recent.write_bytes(b"awaiting promotion")

    result = stage_database_copy(src, dest)
    try:
        assert result["ok"] is True, result
        assert not stale.exists()
        assert recent.exists()
    finally:
        if result.get("staged"):
            # Desregistra + remove: unlink sozinho deixaria o staging
            # registrado como ativo e bloquearia o close da GUI depois.
            ssa_ops.discard_staged_copy(result["staged"])


def test_stage_database_copy_never_sweeps_active_staged(tmp_path):
    """Staging registrado como ativo neste processo nao e removido nem
    quando seu mtime parece antigo (copia lenta, promocao lenta)."""
    import os
    import time

    from gui.ssa import database_operations as ssa_ops
    from gui.ssa.database_operations import (
        STALE_STAGED_COPY_MIN_AGE_SEC,
        _register_staged_copy,
        _unregister_staged_copy,
        stage_database_copy,
    )

    src_dir = tmp_path / "externo"
    src_dir.mkdir()
    src = _make_db(src_dir / "src.db", ["a"])
    dest_dir = tmp_path / "data"
    dest_dir.mkdir()
    dest = dest_dir / "src.db"

    active = dest_dir / "src.db.copy-20000101_000000_000001"
    active.write_bytes(b"active copy in progress")
    active_journal = Path(f"{active}-journal")
    active_journal.write_bytes(b"journal of the active copy")
    old = time.time() - STALE_STAGED_COPY_MIN_AGE_SEC - 60
    os.utime(active, (old, old))
    os.utime(active_journal, (old, old))
    _register_staged_copy(active)
    result: dict = {}
    try:
        result = stage_database_copy(src, dest)
        assert result["ok"] is True, result
        assert active.exists()
        assert active_journal.exists()
    finally:
        _unregister_staged_copy(active)
        if result.get("staged"):
            ssa_ops.discard_staged_copy(result["staged"])


def test_sweep_removes_stale_sidecar_of_unregistered_copy(tmp_path):
    """Sidecar orfao de staging morto ainda e varrido pela idade."""
    import os
    import time

    from gui.ssa import database_operations as ssa_ops
    from gui.ssa.database_operations import (
        STALE_STAGED_COPY_MIN_AGE_SEC,
        stage_database_copy,
    )

    src_dir = tmp_path / "externo"
    src_dir.mkdir()
    src = _make_db(src_dir / "src.db", ["a"])
    dest_dir = tmp_path / "data"
    dest_dir.mkdir()
    dest = dest_dir / "src.db"

    orphan_journal = dest_dir / "src.db.copy-20000101_000000_000009-journal"
    orphan_journal.write_bytes(b"journal of a dead copy")
    old = time.time() - STALE_STAGED_COPY_MIN_AGE_SEC - 60
    os.utime(orphan_journal, (old, old))

    result = stage_database_copy(src, dest)
    try:
        assert result["ok"] is True, result
        assert not orphan_journal.exists()
    finally:
        if result.get("staged"):
            ssa_ops.discard_staged_copy(result["staged"])


def test_sweep_keeps_foreign_staging_with_recent_sidecar(tmp_path):
    """Staging de outra instancia com journal ativo nao e removido, mesmo
    com a base antiga: a idade do grupo e a do arquivo mais recente."""
    import os
    import time

    from gui.ssa import database_operations as ssa_ops
    from gui.ssa.database_operations import (
        STALE_STAGED_COPY_MIN_AGE_SEC,
        stage_database_copy,
    )

    src_dir = tmp_path / "externo"
    src_dir.mkdir()
    src = _make_db(src_dir / "src.db", ["a"])
    dest_dir = tmp_path / "data"
    dest_dir.mkdir()
    dest = dest_dir / "src.db"

    foreign = dest_dir / "src.db.copy-20000101_000000_000002"
    foreign.write_bytes(b"copy from another process")
    foreign_journal = Path(f"{foreign}-journal")
    foreign_journal.write_bytes(b"journal still being written")
    old = time.time() - STALE_STAGED_COPY_MIN_AGE_SEC - 60
    os.utime(foreign, (old, old))

    result = stage_database_copy(src, dest)
    try:
        assert result["ok"] is True, result
        assert foreign.exists()
        assert foreign_journal.exists()
    finally:
        if result.get("staged"):
            ssa_ops.discard_staged_copy(result["staged"])


def test_stage_database_copy_blocked_while_staging_barred(tmp_path):
    """Apos a barreira de encerramento, nenhum staging novo inicia.

    E a contagem atomica reflete o staging vivo ate ele ser descartado.
    """
    from gui.ssa import database_operations as ssa_ops

    src_dir = tmp_path / "externo"
    src_dir.mkdir()
    src = _make_db(src_dir / "src.db", ["a"])
    dest_dir = tmp_path / "data"
    dest_dir.mkdir()
    dest = dest_dir / "src.db"

    live = ssa_ops.stage_database_copy(src, dest)
    try:
        assert live["ok"] is True, live
        assert ssa_ops.bar_new_staged_copies() == 1
        blocked = ssa_ops.stage_database_copy(src, dest)
        assert blocked["ok"] is False
        assert blocked.get("staged") is None
        assert "encerramento" in str(blocked.get("error"))
    finally:
        ssa_ops.allow_new_staged_copies()
        if live.get("staged"):
            ssa_ops.discard_staged_copy(live["staged"])

    # Barreira reaberta: staging volta a funcionar.
    again = ssa_ops.stage_database_copy(src, dest)
    try:
        assert again["ok"] is True, again
    finally:
        if again.get("staged"):
            ssa_ops.discard_staged_copy(again["staged"])


def test_commit_staged_database_copy_uses_dest_writer_lock(
    tmp_path, monkeypatch
):
    """A transacao archive+promote tem que rodar sob o writer lock do
    destino; um escritor concorrente nao pode observar .db e sidecars
    de geracoes diferentes."""
    from gui.ssa import database_operations as ssa_ops

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    dest = _make_db(data_dir / "x.db", ["antigo"])
    staged = data_dir / "x.db.copy-20260101_000000_000000"
    staged.write_bytes(b"staged")

    locked_paths: list[str] = []

    class _RecordingLock:
        def __init__(self, path, **kwargs):
            locked_paths.append(str(path))

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(ssa_ops, "database_writer_lock", _RecordingLock)

    result = ssa_ops.commit_staged_database_copy(str(staged), str(dest))

    assert result["ok"] is True
    assert locked_paths == [str(dest)]


def test_commit_keeps_destination_visible_until_atomic_replace(tmp_path, monkeypatch):
    import os

    from gui.ssa import database_operations as ssa_ops

    dest = _make_db(tmp_path / "x.db", ["antigo"])
    staged = _make_db(tmp_path / "x.db.copy-20260101_000000_000000", ["novo"])
    real_replace = os.replace

    def _check_replace(source, target):
        if str(source) == str(staged) and str(target) == str(dest):
            assert dest.exists()
            assert _read_rows(dest) == ["antigo"]
        real_replace(source, target)

    monkeypatch.setattr(os, "replace", _check_replace)

    result = ssa_ops.commit_staged_database_copy(str(staged), str(dest))

    assert result["ok"] is True
    assert _read_rows(dest) == ["novo"]


@pytest.mark.parametrize("suffix", ["-wal", "-shm", "-journal"])
def test_commit_staged_database_copy_refuses_residual_sidecar(tmp_path, suffix):
    from gui.ssa import database_operations as ssa_ops

    dest = _make_db(tmp_path / "x.db", ["antigo"])
    staged = _make_db(tmp_path / "x.db.copy-20260101_000000_000000", ["novo"])
    Path(f"{staged}{suffix}").write_bytes(b"residual")

    result = ssa_ops.commit_staged_database_copy(str(staged), str(dest))

    assert result["ok"] is False
    assert "sidecar" in result["error"]
    assert _read_rows(dest) == ["antigo"]
    assert not staged.exists()
    assert not Path(f"{staged}{suffix}").exists()


def test_commit_staged_database_copy_refuses_symlink_dest(tmp_path):
    from gui.ssa import database_operations as ssa_ops

    target = _make_db(tmp_path / "real.db", ["vitima"])
    dest = tmp_path / "x.db"
    try:
        dest.symlink_to(target)
    except OSError as exc:
        pytest.skip(f"Symlink indisponivel: {exc}")
    staged = _make_db(tmp_path / "x.db.copy-20260101_000000_000000", ["novo"])

    result = ssa_ops.commit_staged_database_copy(str(staged), str(dest))

    assert result["ok"] is False
    assert "symlink" in result["error"]
    assert dest.is_symlink()
    assert _read_rows(target) == ["vitima"]
    assert not list(tmp_path.glob("x.db.bak-*"))
    assert not staged.exists()


def test_commit_staged_database_copy_keeps_primary_on_snapshot_failure(
    tmp_path, monkeypatch
):
    """Falha de snapshot nao remove o banco nem seus sidecars."""

    from gui.ssa import database_operations as ssa_ops

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    dest = _make_db(data_dir / "x.db", ["antigo"])
    wal = Path(f"{dest}-wal")
    wal.write_bytes(b"wal antigo")
    journal = Path(f"{dest}-journal")
    journal.write_bytes(b"journal antigo")
    staged = data_dir / "x.db.copy-20260101_000000_000001"
    staged.write_bytes(b"staged")

    def _fail_snapshot(_db, _backup):
        raise PermissionError("simulated snapshot failure")

    monkeypatch.setattr(ssa_ops, "snapshot_database_for_replace", _fail_snapshot)
    result = ssa_ops.commit_staged_database_copy(str(staged), str(dest))

    assert result["ok"] is False
    assert wal.exists() and wal.read_bytes() == b"wal antigo"
    assert journal.exists() and journal.read_bytes() == b"journal antigo"
    assert _read_rows(dest) == ["antigo"]
    assert not staged.exists()


def test_commit_staged_database_copy_keeps_primary_on_promotion_failure(
    tmp_path, monkeypatch
):
    """Falha na troca deixa o banco anterior acessivel e descarta staging."""
    import os

    from gui.ssa import database_operations as ssa_ops

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    dest = _make_db(data_dir / "x.db", ["antigo"])
    with sqlite3.connect(dest) as conn:
        assert conn.execute("PRAGMA journal_mode=WAL").fetchone() == ("wal",)
    staged = data_dir / "x.db.copy-20260101_000000_000002"
    staged.write_bytes(b"staged")

    real_replace = os.replace

    def _fail_on_promotion(src, dst):
        if str(src) == str(staged):
            raise PermissionError("simulated promotion failure")
        real_replace(src, dst)

    monkeypatch.setattr(os, "replace", _fail_on_promotion)
    try:
        result = ssa_ops.commit_staged_database_copy(str(staged), str(dest))
    finally:
        monkeypatch.setattr(os, "replace", real_replace)

    assert result["ok"] is False
    assert result["archived"] is None
    assert _read_rows(dest) == ["antigo"]
    with sqlite3.connect(dest) as conn:
        assert conn.execute("PRAGMA journal_mode").fetchone() == ("wal",)
    assert not staged.exists()


def test_commit_keeps_backup_when_journal_restore_fails(tmp_path, monkeypatch):
    import os

    from gui.ssa import database_operations as ssa_ops

    dest = _make_db(tmp_path / "x.db", ["antigo"])
    staged = _make_db(tmp_path / "x.db.copy-20260101_000000_000000", ["novo"])

    def _fail(*_args):
        raise PermissionError("simulated failure")

    monkeypatch.setattr(os, "replace", _fail)
    monkeypatch.setattr(ssa_ops, "restore_journal_mode", _fail)

    result = ssa_ops.commit_staged_database_copy(str(staged), str(dest))

    assert result["ok"] is False
    assert result["archived"] is not None
    assert _read_rows(dest) == ["antigo"]
    assert _read_rows(Path(result["archived"])) == ["antigo"]
