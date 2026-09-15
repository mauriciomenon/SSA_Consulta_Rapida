"""Database operations used by GUI controllers."""

from __future__ import annotations

import logging
import os
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def execute_vacuum_analyze(
    db_path: str, vacuum_analyze_database_fn: Callable[[str], dict[str, Any]]
) -> dict[str, Any]:
    return vacuum_analyze_database_fn(db_path)


def validate_database_candidate(
    db_file: str,
    *,
    table_name: str,
    query_db_fn: Callable[..., Any],
) -> dict[str, Any]:
    try:
        test_df = query_db_fn(db_file, table_name, raise_on_error=True)
    except Exception as exc:
        return {"ok": False, "error": str(exc), "db_file": db_file}
    has_rows = bool(test_df is not None and not test_df.empty)
    return {"ok": has_rows, "db_file": db_file}


def copy_database_into_data_dir(
    source_path: str,
    *,
    data_dir: str,
) -> dict[str, Any]:
    """Copia um banco externo para ``data_dir`` sem alterar a origem.

    Usa a backup API do SQLite com a origem aberta em modo read-only, o
    que produz um snapshot consistente inclusive com WAL aberto. Um
    destino existente e arquivado como ``.bak-<timestamp>`` (nunca
    sobrescrito); se a origem ja estiver dentro de ``data_dir`` a
    funcao e um no-op.

    Retorna ``{"ok": bool, "db_file": <destino>, "copied": bool,
    "archived": <base do backup ou None>, "error": <msg ou None>}``.
    """
    try:
        src = Path(source_path).expanduser().resolve()
    except (OSError, RuntimeError, ValueError) as exc:
        return {
            "ok": False,
            "db_file": source_path,
            "copied": False,
            "archived": None,
            "error": f"caminho de origem invalido: {exc}",
        }
    if not src.is_file():
        return {
            "ok": False,
            "db_file": str(src),
            "copied": False,
            "archived": None,
            "error": "arquivo de origem nao existe",
        }
    try:
        dest_dir = Path(data_dir).expanduser().resolve()
        dest_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return {
            "ok": False,
            "db_file": source_path,
            "copied": False,
            "archived": None,
            "error": f"falha ao preparar diretorio de dados: {exc}",
        }
    dest = dest_dir / src.name
    # Identidade precisa considerar aliases do filesystem: em volumes
    # case-insensitive (APFS/NTFS padrao) "data" e "Data" resolvem para o
    # mesmo inode, e a comparacao de strings deixaria a propria origem ser
    # arquivada como destino antigo.
    same_file = dest == src
    if not same_file and dest.exists():
        try:
            same_file = os.path.samefile(dest, src)
        except OSError:
            same_file = False
    if same_file:
        return {
            "ok": True,
            "db_file": str(src),
            "copied": False,
            "archived": None,
            "error": None,
        }

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    staged = dest.with_name(f"{dest.name}.copy-{timestamp}")

    def _remove_staging() -> None:
        for suffix in ("-wal", "-shm", "-journal", ""):
            partial = Path(f"{staged}{suffix}")
            if partial.exists():
                try:
                    os.remove(partial)
                except OSError as exc:
                    logger.warning("Falha ao remover copia parcial %s: %s", partial, exc)

    # Etapa 1: snapshot da origem no arquivo de staging. O destino nao e
    # tocado nesta etapa, entao uma falha nao deixa o caminho sem banco.
    try:
        source_uri = src.as_uri() + "?mode=ro"
        # URIs com authority (caminhos UNC -> file://servidor/...) sao
        # rejeitadas pelo SQLite; nesse caso abre-se pelo caminho direto.
        if urlparse(source_uri).netloc not in ("", "localhost"):
            source_conn_ctx = closing(sqlite3.connect(str(src)))
        else:
            source_conn_ctx = closing(sqlite3.connect(source_uri, uri=True))
        with source_conn_ctx as source_conn:
            with closing(sqlite3.connect(str(staged))) as staged_conn:
                source_conn.backup(staged_conn)
    except (OSError, sqlite3.Error, ValueError) as exc:
        _remove_staging()
        return {
            "ok": False,
            "db_file": str(dest),
            "copied": False,
            "archived": None,
            "error": f"falha ao copiar banco: {exc}",
        }

    # Etapa 2: arquiva o trio destino existente (WAL/ShM antes do .db, como
    # no emergency_import; sidecars orfaos tambem sao arquivados). Se o
    # arquivamento falhar no meio, o que ja foi movido e restaurado.
    archived_base: str | None = None
    moved: list[tuple[str, str]] = []
    dest_sidecars = [dest] + [Path(f"{dest}{s}") for s in ("-wal", "-shm")]
    if any(p.exists() for p in dest_sidecars):
        archived_base = f"{dest}.bak-{timestamp}"
        for suffix in ("-wal", "-shm", ""):
            stale = Path(f"{dest}{suffix}")
            if not stale.exists():
                continue
            target = f"{archived_base}{suffix}"
            try:
                os.replace(stale, target)
            except OSError as exc:
                for orig, archived_name in reversed(moved):
                    try:
                        os.replace(archived_name, orig)
                    except OSError as restore_exc:
                        logger.error(
                            "Falha ao restaurar %s de %s: %s",
                            orig,
                            archived_name,
                            restore_exc,
                        )
                _remove_staging()
                return {
                    "ok": False,
                    "db_file": str(dest),
                    "copied": False,
                    "archived": archived_base,
                    "error": f"falha ao arquivar banco existente {stale}: {exc}",
                }
            moved.append((str(stale), target))

    # Etapa 3: promocao atomica do staging para o destino. Em falha, o
    # trio arquivado e restaurado para manter o banco anterior utilizavel.
    try:
        os.replace(staged, dest)
    except OSError as exc:
        for orig, archived_name in reversed(moved):
            try:
                os.replace(archived_name, orig)
            except OSError as restore_exc:
                logger.error(
                    "Falha ao restaurar %s de %s: %s",
                    orig,
                    archived_name,
                    restore_exc,
                )
        _remove_staging()
        return {
            "ok": False,
            "db_file": str(dest),
            "copied": False,
            "archived": archived_base,
            "error": f"falha ao promover copia para {dest}: {exc}",
        }

    return {
        "ok": True,
        "db_file": str(dest),
        "copied": True,
        "archived": archived_base,
        "error": None,
    }
