"""Database operations used by GUI controllers."""

from __future__ import annotations

import logging
import os
import sqlite3
import threading
import time
from contextlib import closing
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from filelock import Timeout

from armazenamento.database import read_only_sqlite_uri
from armazenamento.database_lock import database_writer_lock

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
        # read_only: a validacao de um arquivo escolhido pelo usuario nao
        # pode escrever no .db dele (ex.: recuperacao de -journal quente).
        test_df = query_db_fn(db_file, table_name, raise_on_error=True, read_only=True)
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

    staged_result = stage_database_copy(src, dest)
    if not staged_result.get("ok"):
        return staged_result
    return commit_staged_database_copy(
        str(staged_result["staged"]), str(staged_result["dest"])
    )


# Stagings criados por este processo e ainda nao promovidos/descartados.
# O sweep nunca remove um arquivo registrado aqui — copia lenta ou
# promocao lenta continuam protegidas; so entram no sweep arquivos de
# processos mortos E com mtime alem da janela minima.
_ACTIVE_STAGED_COPIES: set[str] = set()
_ACTIVE_STAGED_LOCK = threading.Lock()
_STAGING_BARRED = False
STALE_STAGED_COPY_MIN_AGE_SEC = 120.0


def _register_staged_copy(staged: Path) -> None:
    with _ACTIVE_STAGED_LOCK:
        _ACTIVE_STAGED_COPIES.add(str(staged))


def _unregister_staged_copy(staged: Path) -> None:
    with _ACTIVE_STAGED_LOCK:
        _ACTIVE_STAGED_COPIES.discard(str(staged))


def active_staged_copy_count() -> int:
    """Quantidade de stagings `.copy-*` vivos criados por este processo.

    Fonte de verdade para "existe copia de banco em andamento" — cobre
    inclusive threads cuja referencia a GUI ja descartou (timeout de
    validacao, request substituido).
    """
    with _ACTIVE_STAGED_LOCK:
        return len(_ACTIVE_STAGED_COPIES)


def bar_new_staged_copies() -> int:
    """Impede novos stagings e conta os ativos, atomicamente.

    Barreira de encerramento: depois desta chamada nenhum
    `stage_database_copy` inicia copia — ou havia stagings vivos (e o
    chamador deve adiar + `allow_new_staged_copies`), ou nao existe e nao
    pode nascer nenhum (seguro encerrar).
    """
    global _STAGING_BARRED
    with _ACTIVE_STAGED_LOCK:
        _STAGING_BARRED = True
        return len(_ACTIVE_STAGED_COPIES)


def allow_new_staged_copies() -> None:
    """Reabre o staging apos um fechamento que acabou adiado."""
    global _STAGING_BARRED
    with _ACTIVE_STAGED_LOCK:
        _STAGING_BARRED = False


def _is_active_staged_path(path: Path, active: set[str]) -> bool:
    """True se `path` for um staging ativo ou sidecar (`-wal` etc.) de um.

    O glob `*.copy-*` tambem casa sidecars como `x.db.copy-<ts>-journal`;
    remover o journal de um sqlite3.backup() em andamento corromperia a
    copia ativa, entao o registro protege a base e seus sidecars.
    """
    name = str(path)
    if name in active:
        return True
    for suffix in ("-wal", "-shm", "-journal"):
        if name.endswith(suffix) and name.removesuffix(suffix) in active:
            return True
    return False


def _sweep_stale_staged_copies(dest: Path) -> None:
    """Remove `.copy-*` orfaos do destino (best-effort).

    Um arquivo so e removido se nao estiver registrado como staging ativo
    deste processo (nem for sidecar de um) E for mais antigo que a janela
    minima.
    """
    cutoff = time.time() - STALE_STAGED_COPY_MIN_AGE_SEC
    try:
        siblings = list(dest.parent.glob(f"{dest.name}.copy-*"))
    except OSError as exc:
        logger.warning("Falha ao listar copias de staging antigas: %s", exc)
        return
    with _ACTIVE_STAGED_LOCK:
        active = set(_ACTIVE_STAGED_COPIES)
    for stale in siblings:
        try:
            if _is_active_staged_path(stale, active):
                continue
            if stale.stat().st_mtime < cutoff:
                discard_staged_copy(stale)
        except OSError as exc:
            logger.warning("Falha ao inspecionar copia parcial %s: %s", stale, exc)


def stage_database_copy(src: Path, dest: Path) -> dict[str, Any]:
    """Grava o snapshot da origem em arquivo de staging ao lado do destino.

    Nao toca no destino: a promocao acontece em commit_staged_database_copy,
    o que permite ao chamador decidir (ou descartar) depois da copia pesada.
    """
    _sweep_stale_staged_copies(dest)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    staged = dest.with_name(f"{dest.name}.copy-{timestamp}")
    # Registro sob o mesmo lock da barreira de encerramento: ou este
    # staging entra na contagem (e o shutdown espera), ou o encerramento
    # ja barrou novos stagings e nenhum arquivo e criado.
    with _ACTIVE_STAGED_LOCK:
        if _STAGING_BARRED:
            return {
                "ok": False,
                "db_file": str(dest),
                "copied": False,
                "archived": None,
                "error": "encerramento em andamento",
            }
        _ACTIVE_STAGED_COPIES.add(str(staged))
    try:
        # mode=ro (inclusive em UNC): a leitura nao pode disparar
        # recuperacao de journal quente na origem.
        source_uri = read_only_sqlite_uri(str(src))
        with closing(sqlite3.connect(source_uri, uri=True)) as source_conn:
            with closing(sqlite3.connect(str(staged))) as staged_conn:
                source_conn.backup(staged_conn)
                if staged_conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal":
                    checkpoint = staged_conn.execute(
                        "PRAGMA wal_checkpoint(TRUNCATE)"
                    ).fetchone()
                    if checkpoint is None or checkpoint[0] != 0:
                        raise sqlite3.OperationalError(
                            "checkpoint do staging SQLite incompleto"
                        )
    except (OSError, sqlite3.Error, ValueError) as exc:
        _unregister_staged_copy(staged)
        discard_staged_copy(staged)
        return {
            "ok": False,
            "db_file": str(dest),
            "copied": False,
            "archived": None,
            "error": f"falha ao copiar banco: {exc}",
        }
    return {
        "ok": True,
        "staged": str(staged),
        "dest": str(dest),
        "timestamp": timestamp,
        "db_file": str(dest),
        "copied": True,
        "archived": None,
        "error": None,
    }


def discard_staged_copy(staged: str | Path) -> None:
    """Remove arquivo de staging e sidecars orfaos (best-effort)."""
    _unregister_staged_copy(Path(staged))
    for suffix in ("-wal", "-shm", "-journal", ""):
        partial = Path(f"{staged}{suffix}")
        if partial.exists():
            try:
                os.remove(partial)
            except OSError as exc:
                logger.warning(
                    "Falha ao remover copia parcial %s: %s", partial, exc
                )


def commit_staged_database_copy(staged: str, dest_str: str) -> dict[str, Any]:
    """Arquiva o destino existente e promove o staging atomicamente.

    O lock e adquirido sem espera para nao bloquear a thread de UI. Ele
    cobre arquivamento+promocao+rollback: sem ele,
    um escritor concorrente (CLI ou outra GUI) poderia observar .db e
    sidecars de geracoes diferentes. Em falha, restaura o que foi
    arquivado para manter o banco anterior utilizavel.
    """
    try:
        with database_writer_lock(dest_str, timeout=0):
            return _commit_staged_database_copy_locked(staged, dest_str)
    except Timeout as exc:
        logger.warning(
            "Promocao recusada, escrita em curso no destino %s: %s", dest_str, exc
        )
        error = f"destino indisponivel para promocao (escrita em curso): {exc}"
    except OSError as exc:
        # O try cobre aquisicao, corpo e liberacao do lock: nao da para
        # afirmar que o lock estava ocupado - reporta a causa real.
        logger.warning("Falha de IO na promocao para %s: %s", dest_str, exc)
        error = f"falha de IO na promocao do banco para {dest_str}: {exc}"
    discard_staged_copy(staged)
    return {
        "ok": False,
        "db_file": dest_str,
        "copied": False,
        "archived": None,
        "error": error,
    }


def _commit_staged_database_copy_locked(
    staged: str, dest_str: str
) -> dict[str, Any]:
    dest = Path(dest_str)
    if any(Path(f"{staged}{suffix}").exists() for suffix in ("-wal", "-shm", "-journal")):
        discard_staged_copy(staged)
        return {
            "ok": False,
            "db_file": str(dest),
            "copied": False,
            "archived": None,
            "error": "copia de banco com sidecar SQLite residual",
        }
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    archived_base: str | None = None
    moved: list[tuple[str, str]] = []
    # Arquiva o destino existente (sidecars antes do .db, como no
    # emergency_import; sidecars orfaos tambem sao arquivados).
    dest_sidecars = [dest] + [
        Path(f"{dest}{s}") for s in ("-wal", "-shm", "-journal")
    ]
    if any(p.exists() for p in dest_sidecars):
        archived_base = f"{dest}.bak-{timestamp}"
        for suffix in ("-wal", "-shm", "-journal", ""):
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
                discard_staged_copy(staged)
                return {
                    "ok": False,
                    "db_file": str(dest),
                    "copied": False,
                    "archived": archived_base,
                    "error": f"falha ao arquivar banco existente {stale}: {exc}",
                }
            moved.append((str(stale), target))

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
        discard_staged_copy(staged)
        return {
            "ok": False,
            "db_file": str(dest),
            "copied": False,
            "archived": archived_base,
            "error": f"falha ao promover copia para {dest}: {exc}",
        }

    # O nome .copy-* deixou de existir; libera o registro de staging ativo.
    _unregister_staged_copy(Path(staged))
    return {
        "ok": True,
        "db_file": str(dest),
        "copied": True,
        "archived": archived_base,
        "error": None,
    }
