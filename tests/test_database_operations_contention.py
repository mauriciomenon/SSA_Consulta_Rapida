from __future__ import annotations

import threading

from armazenamento.database_lock import database_writer_lock
from gui.ssa.database_operations import commit_staged_database_copy


def test_promocao_recusa_destino_ocupado_sem_trocar_arquivos(tmp_path):
    dest = tmp_path / "ssas.db"
    staged = tmp_path / "ssas.db.copy-pendente"
    dest.write_bytes(b"banco anterior")
    staged.write_bytes(b"banco novo")
    acquired = threading.Event()
    release = threading.Event()

    def hold_writer():
        with database_writer_lock(str(dest)):
            acquired.set()
            release.wait(timeout=5)

    writer = threading.Thread(target=hold_writer)
    writer.start()
    try:
        assert acquired.wait(timeout=2)
        result = commit_staged_database_copy(str(staged), str(dest))
        assert result["ok"] is False
        assert "indisponivel" in result["error"]
        assert dest.read_bytes() == b"banco anterior"
        assert not staged.exists()
        assert not list(tmp_path.glob("*.bak-*"))
    finally:
        release.set()
        writer.join(timeout=2)
    assert not writer.is_alive()
