"""Copia consistente de um SQLite para os scripts de build (CD-11, parcial).

Regra unica usada por scripts/copy_data_to_builds.py, scripts/create_distribution.py
e launchers/build_multiplatform.py. As copias do runtime (create_sqlite_backup,
snapshot_database_for_replace, stage_database_copy) tem garantias diferentes de
proposito e ficam fora; unifica-las depende do estudo do BL-24.
"""

from __future__ import annotations

import os
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path

from armazenamento.database_lock import database_writer_lock
from utils.sqlite_backup import bounded_sqlite_backup

_SQLITE_SIDECAR_SUFFIXES = ("-wal", "-shm", "-journal")


def snapshot_sqlite_file(source: Path, target: Path) -> None:
    """Copia `source` (aberta so leitura) para `target` sem expor arquivo parcial.

    Sob o lock de escrita do destino: backup online para um temporario de nome
    unico na pasta do destino, `quick_check`, recusa se o destino tiver sidecar
    SQLite (-wal/-shm/-journal) e so entao `os.replace`.

    Raises:
        OSError: destino com sidecar ou falha de arquivo.
        sqlite3.Error: falha no backup ou no quick_check.
        filelock.Timeout: outro processo grava o banco de destino.
    """
    # Import local: armazenamento.database carrega pandas, e os scripts de build so
    # precisam dele quando ha banco a copiar.
    from armazenamento.database import read_only_sqlite_uri

    target = Path(target)
    temporary: Path | None = None
    with database_writer_lock(str(target), timeout=0):
        try:
            with tempfile.NamedTemporaryFile(
                dir=target.parent, prefix=f"{target.name}.", suffix=".tmp", delete=False
            ) as stage:
                temporary = Path(stage.name)
            source_uri = read_only_sqlite_uri(str(source))
            with closing(sqlite3.connect(source_uri, uri=True, timeout=5)) as source_conn:
                with closing(sqlite3.connect(temporary)) as target_conn:
                    bounded_sqlite_backup(source_conn, target_conn)
                    if target_conn.execute("PRAGMA quick_check").fetchone() != ("ok",):
                        raise sqlite3.DatabaseError("snapshot do banco falhou no quick_check")
            if any(os.path.lexists(f"{target}{suffix}") for suffix in _SQLITE_SIDECAR_SUFFIXES):
                raise OSError(
                    "Destino tem sidecars SQLite; feche o runtime e verifique o banco "
                    "antes de substituir."
                )
            os.replace(temporary, target)
            temporary = None
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
