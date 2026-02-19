# gui/ssa/gui_workers.py
# Relation: used by gui/gui_ssa.py (SSAMainWindow facade).
# Relation: uses gui/workers and worker retention globals from gui/gui_ssa.py.
# Relation: owns load_data flow and worker cleanup; no layout changes.

from __future__ import annotations

import os
import re
import uuid
import time
import threading
from time import perf_counter
import pandas as pd

from utils.robust_logging import get_robust_logger

logger = get_robust_logger().get_logger(__name__, "gui")
_GLOBAL_WORKERS_LOCK = threading.Lock()
# NOTE: worker retention uses window-local list plus global registry; keep behavior stable.
# Refactor to a manager class is tracked in docs/RECOVERY_BACKLOG.md.
# NOTE: global worker lists are capped by max_* to limit lock contention.

try:
    from PyQt6.QtCore import Qt as _Qt
    _QT_QUEUED = _Qt.ConnectionType.QueuedConnection
except Exception as exc:
    logger.debug("Falha ao importar Qt.ConnectionType para conexao enfileirada: %s", exc)
    _QT_QUEUED = None


def _sanitize_ssa_like_value(value) -> str:
    if value is None:
        return ""
    try:
        if isinstance(value, float):
            if pd.isna(value):
                return ""
            if value.is_integer():
                return str(int(value))
            return str(value).strip()
    except (TypeError, ValueError):
        pass
    except Exception as exc:
        logger.debug("Falha inesperada ao sanitizar valor SSA-like '%r': %s", value, exc)
    text = str(value).strip()
    if not text:
        return ""
    if text.lower() in {"nan", "none", "nat", "<na>"}:
        return ""
    if re.fullmatch(r"\d+\.0+", text):
        return text.split(".", 1)[0]
    return text


def _connect_signal(signal, slot, *, label: str) -> bool:
    if signal is None:
        logger.debug("Signal ausente para %s; pulando conexao.", label)
        return False
    if not hasattr(signal, "connect"):
        logger.debug("Signal invalido para %s; sem metodo connect.", label)
        return False
    try:
        if _QT_QUEUED is not None:
            try:
                signal.connect(slot, type=_QT_QUEUED)
            except TypeError:
                signal.connect(slot)
        else:
            signal.connect(slot)
        return True
    except Exception as exc:
        logger.debug("Falha ao conectar signal %s: %s", label, exc)
        return False


def _safe_disconnect(signal, label: str) -> None:
    if signal is None:
        return
    try:
        signal.disconnect()
    except Exception as exc:
        logger.debug("Falha ao desconectar %s: %s", label, exc)


def retain_data_loader_worker_until_finished(
    window,
    worker,
    *,
    global_workers: list,
    global_meta: dict,
    max_global_workers: int,
    retired_ttl_sec: float,
    retired_force_wait_ms: int,
    sip_module,
) -> None:
    if worker is None:
        return
    prune_retired_data_loader_workers(
        window,
        global_workers=global_workers,
        global_meta=global_meta,
        max_global_workers=max_global_workers,
        retired_ttl_sec=retired_ttl_sec,
        retired_force_wait_ms=retired_force_wait_ms,
        sip_module=sip_module,
    )
    retired = getattr(window, "_retired_data_loader_workers", None)
    with _GLOBAL_WORKERS_LOCK:
        if retired is None:
            retired = []
            window._retired_data_loader_workers = retired
        if worker in retired:
            return
        retired.append(worker)
        global_meta[worker] = perf_counter()
        if worker not in global_workers:
            global_workers.append(worker)

    def _release_worker_ref(w=worker):
        try:
            with _GLOBAL_WORKERS_LOCK:
                retired_workers = getattr(window, "_retired_data_loader_workers", None)
                if retired_workers is not None and w in retired_workers:
                    retired_workers.remove(w)
                if w in global_workers:
                    global_workers.remove(w)
                global_meta.pop(w, None)
        except Exception as exc:
            logger.debug("Falha ao liberar referencias de worker de carga finalizado: %s", exc)

    finished_signal = getattr(worker, "finished", None)
    if not _connect_signal(finished_signal, _release_worker_ref, label="data_loader.finished.cleanup"):
        _release_worker_ref()
    destroyed_signal = getattr(worker, "destroyed", None)
    if destroyed_signal is not None:
        _connect_signal(destroyed_signal, _release_worker_ref, label="data_loader.destroyed.cleanup")
    if finished_signal is not None and hasattr(worker, "deleteLater"):
        _connect_signal(finished_signal, worker.deleteLater, label="data_loader.finished.deleteLater")
    prune_retired_data_loader_workers(
        window,
        global_workers=global_workers,
        global_meta=global_meta,
        max_global_workers=max_global_workers,
        retired_ttl_sec=retired_ttl_sec,
        retired_force_wait_ms=retired_force_wait_ms,
        sip_module=sip_module,
    )


def is_data_loader_worker_alive(worker, sip_module) -> bool:
    if worker is None:
        return False
    if sip_module is None:
        return True
    try:
        return not sip_module.isdeleted(worker)
    except TypeError:
        return True
    except Exception as exc:
        logger.debug("Falha ao consultar estado de delecao do worker: %s", exc)
        return False


def is_data_loader_worker_running(worker, sip_module) -> bool:
    if not is_data_loader_worker_alive(worker, sip_module):
        return False
    try:
        if hasattr(worker, "isRunning"):
            return bool(worker.isRunning())
    except Exception as exc:
        logger.debug("Falha ao consultar isRunning() do data loader worker: %s", exc)
        return False
    return False


def prune_retired_data_loader_workers(
    window,
    *,
    global_workers: list,
    global_meta: dict,
    max_global_workers: int,
    retired_ttl_sec: float,
    retired_force_wait_ms: int,
    sip_module,
) -> None:
    now = perf_counter()
    removed_local = set()
    expired_local = []
    expired_global = []
    with _GLOBAL_WORKERS_LOCK:
        if not getattr(window, "_retired_data_loader_workers", None) and not global_workers:
            return
        retired_local = list(getattr(window, "_retired_data_loader_workers", []) or [])
        for w in retired_local:
            if not is_data_loader_worker_running(w, sip_module):
                global_meta.pop(w, None)
                removed_local.add(w)
                continue
            started_at = global_meta.get(w, now)
            age = now - started_at
            if age > retired_ttl_sec:
                expired_local.append(w)

        running_global = []
        for w in list(global_workers):
            if not is_data_loader_worker_running(w, sip_module):
                global_meta.pop(w, None)
                continue
            started_at = global_meta.get(w, now)
            age = now - started_at
            if age > retired_ttl_sec:
                expired_global.append(w)
            running_global.append(w)
        if len(running_global) > max_global_workers:
            running_global = running_global[-max_global_workers:]
        global_workers[:] = running_global
    for w in expired_local:
        logger.warning("Data loader worker excedeu TTL; solicitando stop.")
        try:
            stopped = cleanup_data_loader_worker(
                window,
                w,
                wait_ms=retired_force_wait_ms,
                global_workers=global_workers,
                global_meta=global_meta,
                max_global_workers=max_global_workers,
                retired_ttl_sec=retired_ttl_sec,
                retired_force_wait_ms=retired_force_wait_ms,
                sip_module=sip_module,
            )
        except Exception as exc:
            logger.debug("Falha ao encerrar data loader worker expirado: %s", exc)
            stopped = False
        if stopped:
            with _GLOBAL_WORKERS_LOCK:
                global_meta.pop(w, None)
            removed_local.add(w)
        else:
            with _GLOBAL_WORKERS_LOCK:
                global_meta[w] = now
    for w in expired_global:
        if w in removed_local:
            continue
        logger.warning("Data loader worker excedeu TTL; solicitando stop.")
        try:
            stopped = cleanup_data_loader_worker(
                window,
                w,
                wait_ms=retired_force_wait_ms,
                global_workers=global_workers,
                global_meta=global_meta,
                max_global_workers=max_global_workers,
                retired_ttl_sec=retired_ttl_sec,
                retired_force_wait_ms=retired_force_wait_ms,
                sip_module=sip_module,
            )
        except Exception as exc:
            logger.debug("Falha ao encerrar data loader worker expirado: %s", exc)
            stopped = False
        if stopped:
            with _GLOBAL_WORKERS_LOCK:
                if w in global_workers:
                    global_workers.remove(w)
                global_meta.pop(w, None)
        else:
            with _GLOBAL_WORKERS_LOCK:
                global_meta[w] = now
    with _GLOBAL_WORKERS_LOCK:
        if removed_local:
            retired_current = list(getattr(window, "_retired_data_loader_workers", []) or [])
            window._retired_data_loader_workers = [w for w in retired_current if w not in removed_local]
        for w in list(global_meta.keys()):
            if w not in global_workers and w not in window._retired_data_loader_workers:
                global_meta.pop(w, None)


def is_rescan_worker_running(worker, sip_module) -> bool:
    if not is_data_loader_worker_alive(worker, sip_module):
        return False
    try:
        if hasattr(worker, "isRunning"):
            return bool(worker.isRunning())
    except Exception as exc:
        logger.debug("Falha ao consultar isRunning() do rescan worker: %s", exc)
        return False
    return False


def prune_retired_rescan_workers(
    window,
    *,
    global_workers: list,
    global_meta: dict,
    max_global_workers: int,
    retired_ttl_sec: float,
    retired_force_wait_ms: int,
    sip_module,
) -> None:
    # NOTE: TTL/prune logic mirrors data loader flow; keep in sync. Refactor tracked in backlog.
    now = perf_counter()
    expired_global = []
    running_global = []
    with _GLOBAL_WORKERS_LOCK:
        for w in list(global_workers):
            if not is_rescan_worker_running(w, sip_module):
                global_meta.pop(w, None)
                continue
            started_at = global_meta.get(w, now)
            age = now - started_at
            if age > retired_ttl_sec:
                expired_global.append(w)
            running_global.append(w)
        if len(running_global) > max_global_workers:
            running_global = running_global[-max_global_workers:]
        global_workers[:] = running_global
        for w in list(global_meta.keys()):
            if w not in global_workers:
                global_meta.pop(w, None)
    for w in expired_global:
        logger.warning("Rescan worker excedeu TTL; solicitando stop.")
        try:
            if hasattr(w, "stop"):
                w.stop()
            if hasattr(w, "quit"):
                w.quit()
            if hasattr(w, "wait"):
                w.wait(int(retired_force_wait_ms))
            if hasattr(w, "isRunning") and w.isRunning() and hasattr(w, "terminate"):
                w.terminate()
                w.wait(int(retired_force_wait_ms))
        except Exception as exc:
            logger.debug("Falha ao encerrar rescan worker expirado: %s", exc)
        if not is_rescan_worker_running(w, sip_module):
            with _GLOBAL_WORKERS_LOCK:
                if w in global_workers:
                    global_workers.remove(w)
                global_meta.pop(w, None)
            continue
        with _GLOBAL_WORKERS_LOCK:
            global_meta[w] = now


def cleanup_data_loader_worker(
    window,
    worker,
    *,
    wait_ms: int = 1500,
    global_workers: list,
    global_meta: dict,
    max_global_workers: int,
    retired_ttl_sec: float,
    retired_force_wait_ms: int,
    sip_module,
) -> bool:
    if worker is None:
        return True
    still_running = False
    try:
        _safe_disconnect(getattr(worker, "data_loaded", None), "data_loaded do worker de carga")
        _safe_disconnect(getattr(worker, "error_occurred", None), "error_occurred do worker de carga")
        _safe_disconnect(getattr(worker, "finished", None), "finished do worker de carga")
        try:
            if hasattr(worker, "cancel"):
                worker.cancel()
            elif hasattr(worker, "requestInterruption"):
                worker.requestInterruption()
            if is_data_loader_worker_running(worker, sip_module):
                worker.quit()
                if int(wait_ms or 0) > 0:
                    worker.wait(int(wait_ms))
            still_running = is_data_loader_worker_running(worker, sip_module)
        except Exception as exc:
            logger.warning("Falha ao solicitar encerramento do worker de carga: %s", exc)
            still_running = True
        if still_running:
            retain_data_loader_worker_until_finished(
                window,
                worker,
                global_workers=global_workers,
                global_meta=global_meta,
                max_global_workers=max_global_workers,
                retired_ttl_sec=retired_ttl_sec,
                retired_force_wait_ms=retired_force_wait_ms,
                sip_module=sip_module,
            )
            return False
        try:
            worker.deleteLater()
        except Exception as exc:
            logger.debug("Falha ao chamar deleteLater no worker de carga: %s", exc)
    except Exception as exc:
        logger.warning("Falha durante cleanup do worker de carga: %s", exc)
        still_running = True
    finally:
        try:
            prune_retired_data_loader_workers(
                window,
                global_workers=global_workers,
                global_meta=global_meta,
                max_global_workers=max_global_workers,
                retired_ttl_sec=retired_ttl_sec,
                retired_force_wait_ms=retired_force_wait_ms,
                sip_module=sip_module,
            )
        except Exception as prune_exc:
            logger.debug("Falha ao podar workers de carga apos cleanup: %s", prune_exc)
    return not still_running


def load_data(
    window,
    *,
    db_path: str,
    table_name: str,
    data_loader_cls,
    qmessagebox,
    global_workers: list,
    global_meta: dict,
    max_global_workers: int,
    retired_ttl_sec: float,
    retired_force_wait_ms: int,
    sip_module,
) -> None:
    try:
        prune_retired_data_loader_workers(
            window,
            global_workers=global_workers,
            global_meta=global_meta,
            max_global_workers=max_global_workers,
            retired_ttl_sec=retired_ttl_sec,
            retired_force_wait_ms=retired_force_wait_ms,
            sip_module=sip_module,
        )
    except Exception as exc:
        logger.debug("Falha ao podar workers de carga antes de novo load: %s", exc)
    if not os.path.exists(db_path):
        missing_db_msg = "Banco de dados nao encontrado. Execute o programa principal primeiro."
        logger.warning("Banco de dados nao encontrado.")
        try:
            window.status_label.setText("Status: Banco de dados nao encontrado.")
        except Exception as exc:
            logger.debug("Falha ao atualizar status_label em banco ausente: %s", exc)
        if os.environ.get("PYTEST_CURRENT_TEST"):
            return
        if qmessagebox is not None:
            qmessagebox.warning(window, "Erro", missing_db_msg)
        return

    try:
        if hasattr(window, "_invalidate_active_filter_request"):
            window._invalidate_active_filter_request("load_data_new_dataset")
    except Exception as exc:
        logger.warning("Falha ao invalidar request de filtro antes do load: %s", exc)
    try:
        if hasattr(window, "_cancel_active_filter_worker"):
            window._cancel_active_filter_worker("load_data_new_dataset", wait_ms=0)
    except Exception as exc:
        logger.warning("Falha ao cancelar worker de filtro antes do load: %s", exc)
    try:
        window._debounce_timer.stop()
    except Exception as exc:
        logger.debug("Falha ao parar debounce de filtro antes do load: %s", exc)

    request_id = int(getattr(window, "_data_load_request_seq", 0) or 0) + 1
    window._data_load_request_seq = request_id
    window._active_data_load_request_id = request_id

    window.status_label.setText("Status: Carregando dados...")
    window.progress_bar.setVisible(True)
    window.load_button.setEnabled(False)
    window.search_button.setEnabled(False)

    previous_worker = getattr(window, "data_loader_thread", None)
    if previous_worker is not None:
        cleanup_data_loader_worker(
            window,
            previous_worker,
            wait_ms=0,
            global_workers=global_workers,
            global_meta=global_meta,
            max_global_workers=max_global_workers,
            retired_ttl_sec=retired_ttl_sec,
            retired_force_wait_ms=retired_force_wait_ms,
            sip_module=sip_module,
        )
        if getattr(window, "data_loader_thread", None) is previous_worker:
            window.data_loader_thread = None

    if data_loader_cls is None:
        logger.error("DataLoaderWorker indisponivel para load_data")
        if os.environ.get("PYTEST_CURRENT_TEST"):
            logger.debug("PYTEST_CURRENT_TEST set; skipping modal DataLoaderWorker error dialog.")
        else:
            if qmessagebox is not None:
                qmessagebox.critical(
                    window,
                    "Erro de Carregamento",
                    "Data loader indisponivel neste ambiente. Consulte os logs.",
                )
        window.status_label.setText("Status: Erro ao carregar dados.")
        window.progress_bar.setVisible(False)
        window.load_button.setEnabled(True)
        window.search_button.setEnabled(True)
        return

    worker = data_loader_cls(db_path, table_name)
    window.data_loader_thread = worker

    def _handle_data_loaded(df, rid=request_id):
        handler = getattr(window, "on_data_loaded", None)
        if callable(handler):
            return handler(df, request_id=rid)
        return on_data_loaded(window, df, request_id=rid)

    def _handle_load_error(msg, rid=request_id):
        try:
            handler = getattr(window, "on_load_error", None)
            if callable(handler):
                return handler(msg, request_id=rid)
            return on_load_error(
                window,
                msg,
                request_id=rid,
                db_path=db_path,
                qmessagebox=qmessagebox,
                global_workers=global_workers,
                global_meta=global_meta,
                max_global_workers=max_global_workers,
                retired_ttl_sec=retired_ttl_sec,
                retired_force_wait_ms=retired_force_wait_ms,
                sip_module=sip_module,
            )
        finally:
            try:
                now = perf_counter()
                should_prune = False
                with _GLOBAL_WORKERS_LOCK:
                    last_prune = float(getattr(window, "_last_data_loader_prune_ts", 0.0) or 0.0)
                    if now - last_prune >= 1.0:
                        window._last_data_loader_prune_ts = now
                        should_prune = True
                if should_prune:
                    prune_retired_data_loader_workers(
                        window,
                        global_workers=global_workers,
                        global_meta=global_meta,
                        max_global_workers=max_global_workers,
                        retired_ttl_sec=retired_ttl_sec,
                        retired_force_wait_ms=retired_force_wait_ms,
                        sip_module=sip_module,
                    )
            except Exception as exc:
                logger.debug("Falha ao podar workers de carga apos erro no handler: %s", exc)

    def _handle_load_finished(w=worker, rid=request_id):
        handler = getattr(window, "on_load_finished", None)
        if callable(handler):
            return handler(worker=w, request_id=rid)
        return on_load_finished(
            window,
            worker=w,
            request_id=rid,
            global_workers=global_workers,
            global_meta=global_meta,
            max_global_workers=max_global_workers,
            retired_ttl_sec=retired_ttl_sec,
            retired_force_wait_ms=retired_force_wait_ms,
            sip_module=sip_module,
        )

    _connect_signal(worker.data_loaded, _handle_data_loaded, label="data_loader.data_loaded")
    _connect_signal(worker.error_occurred, _handle_load_error, label="data_loader.error_occurred")
    _connect_signal(worker.finished, _handle_load_finished, label="data_loader.finished")
    _connect_signal(worker.finished, worker.deleteLater, label="data_loader.finished.deleteLater")
    worker.start()


def on_data_loaded(window, df: pd.DataFrame, request_id: int | None = None):
    active_id = getattr(window, "_active_data_load_request_id", None)
    if request_id is not None and active_id is not None and request_id != active_id:
        logger.debug("Ignorando resultado de carga obsoleto (request_id=%s, active=%s)", request_id, active_id)
        return
    df_copy = df.copy()
    for ssa_col in ("numero_ssa", "derivada_de"):
        if ssa_col in df_copy.columns:
            try:
                df_copy[ssa_col] = df_copy[ssa_col].map(_sanitize_ssa_like_value)
            except Exception as exc:
                logger.debug("Falha ao sanitizar coluna %s na carga de dados: %s", ssa_col, exc)
    window.df_completo = df_copy
    try:
        last_req = getattr(window, "_data_revision_request_id", None)
        if request_id is None or request_id != last_req:
            if hasattr(window, "_bump_data_revision"):
                window._bump_data_revision("data_loaded")
            else:
                window._data_revision = int(getattr(window, "_data_revision", 0) or 0) + 1
            try:
                window._data_uuid = uuid.uuid4().hex
            except Exception as exc:
                logger.debug("Falha ao gerar UUID de dados; usando fallback textual: %s", exc)
                window._data_uuid = (
                    f"fallback-{time.time_ns()}-{int(getattr(window, '_data_revision', 0) or 0)}"
                )
            window._data_revision_request_id = request_id
    except Exception as exc:
        logger.debug("Falha ao atualizar revisao de dados; resetando para baseline: %s", exc)
        window._data_revision = 1
    try:
        window.clear_filter_cache()
    except Exception as exc:
        logger.debug("Falha ao limpar cache de filtros apos recarga de dados: %s", exc)
    window._adv_options_dirty = True
    window._adv_values_cache = None
    window._responsavel_materialized_prefixes = set()
    window._mark_responsavel_dirty()
    try:
        timer = getattr(window, "_sector_debounce_timer", None)
        if timer is not None:
            timer.stop()
    except Exception as exc:
        logger.debug("Falha ao parar debounce de setor apos carga de dados: %s", exc)
    base = df_copy
    try:
        if 'situacao' in base.columns:
            is_ste = base['situacao'].astype(str).str.upper().eq('STE')
        else:
            is_ste = pd.Series([False] * len(base), index=base.index)
        if 'numero_ssa' in base.columns:
            ssa_text = base["numero_ssa"].astype(str)
            ssa_digits = ssa_text.str.replace(r"\D+", "", regex=True)
            ssa_int = pd.to_numeric(ssa_digits, errors="coerce").fillna(-1).astype("int64")
        else:
            ssa_int = pd.Series([-1] * len(base), index=base.index)
        base = base.assign(__is_ste=is_ste, __ssa=ssa_int).sort_values(
            by=['__is_ste', '__ssa'],
            ascending=[True, False],
            na_position='last',
        ).drop(columns=['__is_ste', '__ssa'])
    except Exception as e:
        logger.warning("Falha na ordenacao inicial dos dados: %s", e)
    window.df_exibido = base
    window._df_last_search_filtered = df_copy
    window._widths_computed_for_df_hash = None
    try:
        window.clear_filter_button.setEnabled(window._has_any_active_filters())
    except Exception as exc:
        logger.debug("Falha ao avaliar filtros ativos; habilitando botao de limpeza por fallback: %s", exc)
        window.clear_filter_button.setEnabled(True)
    window._refresh_after_filter_change()
    try:
        window._refresh_advanced_filter_options()
    except Exception as e:
        logger.warning("Falha ao atualizar opcoes de filtros avancados: %s", e)
    try:
        window._update_derivadas_button_state()
    except Exception as exc:
        logger.warning("Falha ao atualizar estado do botao de derivadas: %s", exc)
    profile_hint = f" (perfil: {window.current_filter_profile})" if window.current_filter_profile else ""
    window.status_label.setText(
        f"Status: {len(window.df_exibido)} SSAs carregadas{profile_hint}. Pronto para filtrar."
    )


def _mask_db_path(error_msg: str, db_path: str | None) -> str:
    if not error_msg or not db_path:
        return error_msg
    try:
        msg = str(error_msg)
        raw = str(db_path)
        db_norm = os.path.normpath(raw)
        candidates = {
            raw,
            db_norm,
            raw.replace("\\", "/"),
            raw.replace("/", "\\"),
            db_norm.replace("\\", "/"),
            db_norm.replace("/", "\\"),
        }
        for candidate in sorted(candidates, key=len, reverse=True):
            candidate_str = str(candidate)
            if candidate_str:
                msg = str(msg).replace(candidate_str, "<db_path>")
        return msg
    except Exception as exc:
        logger.debug("Falha ao mascarar db_path em mensagem de erro; retornando texto bruto: %s", exc)
        return error_msg


def on_load_error(
    window,
    error_msg: str,
    *,
    request_id: int | None = None,
    db_path: str | None = None,
    qmessagebox=None,
    global_workers: list | None = None,
    global_meta: dict | None = None,
    max_global_workers: int | None = None,
    retired_ttl_sec: float | None = None,
    retired_force_wait_ms: int | None = None,
    sip_module=None,
):
    active_id = getattr(window, "_active_data_load_request_id", None)
    if request_id is not None and active_id is not None and request_id != active_id:
        logger.debug("Ignorando erro de carga obsoleto (request_id=%s, active=%s)", request_id, active_id)
        return
    safe_error_msg = "Nao foi possivel carregar os dados. Consulte os logs para detalhes tecnicos."
    masked_error = _mask_db_path(error_msg, db_path)
    logger.error("Erro no carregamento de dados (request_id=%s): %s", request_id, masked_error)
    if os.environ.get("PYTEST_CURRENT_TEST"):
        logger.debug("PYTEST_CURRENT_TEST set; skipping modal load error dialog.")
    else:
        if qmessagebox is not None:
            qmessagebox.critical(window, "Erro de Carregamento", safe_error_msg)
    window.status_label.setText("Status: Erro ao carregar dados.")
    window.load_button.setEnabled(True)
    window.search_button.setEnabled(True)
    window.progress_bar.setVisible(False)
    if global_workers is not None and global_meta is not None:
        try:
            prune_retired_data_loader_workers(
                window,
                global_workers=global_workers,
                global_meta=global_meta,
                max_global_workers=int(max_global_workers or 0),
                retired_ttl_sec=float(retired_ttl_sec or 0),
                retired_force_wait_ms=int(retired_force_wait_ms or 0),
                sip_module=sip_module,
            )
        except Exception as exc:
            logger.debug("Falha ao podar workers de carga apos erro: %s", exc)


def on_load_finished(
    window,
    *,
    worker=None,
    request_id: int | None = None,
    global_workers: list,
    global_meta: dict,
    max_global_workers: int,
    retired_ttl_sec: float,
    retired_force_wait_ms: int,
    sip_module,
) -> None:
    active_id = getattr(window, "_active_data_load_request_id", None)
    is_stale = request_id is not None and active_id is not None and request_id != active_id
    target_worker = worker if worker is not None else getattr(window, "data_loader_thread", None)
    if is_stale:
        try:
            cleanup_data_loader_worker(
                window,
                target_worker,
                global_workers=global_workers,
                global_meta=global_meta,
                max_global_workers=max_global_workers,
                retired_ttl_sec=retired_ttl_sec,
                retired_force_wait_ms=retired_force_wait_ms,
                sip_module=sip_module,
            )
        finally:
            if target_worker is not None and getattr(window, "data_loader_thread", None) is target_worker:
                window.data_loader_thread = None
            try:
                prune_retired_data_loader_workers(
                    window,
                    global_workers=global_workers,
                    global_meta=global_meta,
                    max_global_workers=max_global_workers,
                    retired_ttl_sec=retired_ttl_sec,
                    retired_force_wait_ms=retired_force_wait_ms,
                    sip_module=sip_module,
                )
            except Exception as exc:
                logger.debug("Falha ao podar workers de carga no cleanup de request obsoleto: %s", exc)
        return

    window.progress_bar.setVisible(False)
    window.load_button.setEnabled(True)
    window.search_button.setEnabled(True)
    try:
        cleanup_data_loader_worker(
            window,
            target_worker,
            global_workers=global_workers,
            global_meta=global_meta,
            max_global_workers=max_global_workers,
            retired_ttl_sec=retired_ttl_sec,
            retired_force_wait_ms=retired_force_wait_ms,
            sip_module=sip_module,
        )
    finally:
        if target_worker is not None and getattr(window, "data_loader_thread", None) is target_worker:
            window.data_loader_thread = None
        try:
            prune_retired_data_loader_workers(
                window,
                global_workers=global_workers,
                global_meta=global_meta,
                max_global_workers=max_global_workers,
                retired_ttl_sec=retired_ttl_sec,
                retired_force_wait_ms=retired_force_wait_ms,
                sip_module=sip_module,
            )
        except Exception as exc:
            logger.debug("Falha ao podar workers de carga no fim do load: %s", exc)


def rescan_data(
    window,
    *,
    project_root: str,
    rescan_worker_cls,
    rescan_dialog_cls,
    qmessagebox,
    global_workers: list,
    global_meta: dict,
    max_global_workers: int,
    retired_ttl_sec: float,
    retired_force_wait_ms: int,
    sip_module,
) -> None:
    active_worker = getattr(window, "_active_rescan_worker", None)
    if active_worker is not None:
        try:
            if hasattr(active_worker, "isRunning") and active_worker.isRunning():
                window.status_label.setText("Status: Reescaneamento ja em andamento.")
                return
        except Exception as exc:
            logger.debug("Falha ao checar worker ativo de reescaneamento: %s", exc)

    main_py_path = os.path.join(project_root, "main.py")
    if not os.path.exists(main_py_path):
        if qmessagebox is not None:
            qmessagebox.warning(window, "Erro", f"Arquivo main.py nao encontrado em {main_py_path}")
        return

    progress_dialog = rescan_dialog_cls(window)

    worker = rescan_worker_cls(main_py_path, project_root)
    window._active_rescan_worker = worker

    _connect_signal(worker.output_line, progress_dialog.append_output, label="rescan.output_line")
    _connect_signal(worker.error_line, progress_dialog.append_error, label="rescan.error_line")
    _connect_signal(worker.progress, progress_dialog.update_progress, label="rescan.progress")

    cancelled = False

    def _release_worker_ref(*_args) -> None:
        try:
            if getattr(window, "_active_rescan_worker", None) is worker:
                window._active_rescan_worker = None
        except Exception as exc:
            logger.debug("Falha ao liberar referencia do RescanWorker: %s", exc)
        try:
            if worker in global_workers:
                with _GLOBAL_WORKERS_LOCK:
                    if worker in global_workers:
                        global_workers.remove(worker)
        except Exception as exc:
            logger.debug("Falha ao remover RescanWorker da lista global: %s", exc)
        try:
            with _GLOBAL_WORKERS_LOCK:
                global_meta.pop(worker, None)
        except Exception as exc:
            logger.debug("Falha ao remover meta do RescanWorker: %s", exc)

    def on_success():
        nonlocal cancelled
        if cancelled:
            progress_dialog.set_finished(False, "Processo cancelado pelo usuario")
            window.status_label.setText("Status: Reescaneamento cancelado.")
            _release_worker_ref()
            return
        _release_worker_ref()
        progress_dialog.set_finished(True)
        window.status_label.setText(
            "Status: Reescaneamento concluido. Clique em 'Carregar Dados' para atualizar."
        )

    def on_error(error_msg):
        nonlocal cancelled
        if cancelled or str(error_msg).strip().lower().startswith("processo cancelado"):
            cancelled = True
            progress_dialog.set_finished(False, "Processo cancelado pelo usuario")
            window.status_label.setText("Status: Reescaneamento cancelado.")
            _release_worker_ref()
            return
        progress_dialog.set_finished(False, error_msg)
        window.status_label.setText("Status: Erro no reescaneamento.")
        _release_worker_ref()

    _connect_signal(worker.finished_success, on_success, label="rescan.finished_success")
    _connect_signal(worker.finished_error, on_error, label="rescan.finished_error")
    _connect_signal(worker.finished, _release_worker_ref, label="rescan.finished.release")
    _connect_signal(worker.finished, worker.deleteLater, label="rescan.finished.deleteLater")

    def on_cancel_requested():
        nonlocal cancelled
        cancelled = True
        try:
            running = bool(worker.isRunning())
        except Exception as exc:
            logger.debug("Falha ao checar estado do RescanWorker no cancelamento: %s", exc)
            running = False
        if running:
            worker.stop()
            window.status_label.setText("Status: Cancelamento solicitado no reescaneamento.")

    progress_dialog.cancel_requested.connect(on_cancel_requested)

    worker.start()
    progress_dialog.exec()

    try:
        still_running = bool(worker.isRunning())
    except Exception as exc:
        logger.debug("Falha ao checar estado do RescanWorker apos dialogo: %s", exc)
        still_running = False
    if still_running:
        with _GLOBAL_WORKERS_LOCK:
            if worker not in global_workers:
                global_workers.append(worker)
                global_meta[worker] = perf_counter()
                if len(global_workers) > max_global_workers:
                    global_workers[:] = global_workers[-max_global_workers:]
        prune_retired_rescan_workers(
            window,
            global_workers=global_workers,
            global_meta=global_meta,
            max_global_workers=max_global_workers,
            retired_ttl_sec=retired_ttl_sec,
            retired_force_wait_ms=retired_force_wait_ms,
            sip_module=sip_module,
        )
        logger.warning("RescanWorker ainda esta em execucao apos fechamento do dialogo; mantendo em background.")
