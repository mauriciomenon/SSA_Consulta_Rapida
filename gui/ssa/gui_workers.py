# gui/ssa/gui_workers.py
# Relation: used by gui/gui_ssa.py (SSAMainWindow facade).
# Relation: uses gui/workers and worker retention globals from gui/gui_ssa.py.
# Relation: owns load_data flow and worker cleanup; no layout changes.

from __future__ import annotations

import logging
import os
from time import perf_counter
import pandas as pd

logger = logging.getLogger(__name__)


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
            if w in window._retired_data_loader_workers:
                window._retired_data_loader_workers.remove(w)
        except Exception as exc:
            logger.debug("Falha ao remover worker de carga da lista local aposentada: %s", exc)
        try:
            if w in global_workers:
                global_workers.remove(w)
        except Exception as exc:
            logger.debug("Falha ao remover worker de carga da lista global aposentada: %s", exc)
        try:
            global_meta.pop(w, None)
        except Exception as exc:
            logger.debug("Falha ao remover meta do worker de carga: %s", exc)

    try:
        worker.finished.connect(_release_worker_ref)
    except Exception as exc:
        logger.debug("Falha ao conectar cleanup no signal finished do worker de carga: %s", exc)
        _release_worker_ref()
    try:
        worker.destroyed.connect(_release_worker_ref)
    except Exception as exc:
        logger.debug("Falha ao conectar cleanup no signal destroyed do worker de carga: %s", exc)
    try:
        worker.finished.connect(worker.deleteLater)
    except Exception as exc:
        logger.debug("Falha ao conectar deleteLater no worker de carga: %s", exc)
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
    except Exception:
        return False


def is_data_loader_worker_running(worker, sip_module) -> bool:
    if not is_data_loader_worker_alive(worker, sip_module):
        return False
    try:
        if hasattr(worker, "isRunning"):
            return bool(worker.isRunning())
    except Exception:
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
    retired_local = list(getattr(window, "_retired_data_loader_workers", []) or [])
    pruned_local = []
    for w in retired_local:
        if not is_data_loader_worker_running(w, sip_module):
            global_meta.pop(w, None)
            continue
        started_at = global_meta.get(w, now)
        age = now - started_at
        if age > retired_ttl_sec:
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
                global_meta.pop(w, None)
                continue
            global_meta[w] = now
        pruned_local.append(w)
    window._retired_data_loader_workers = pruned_local

    running_global = []
    for w in global_workers:
        if not is_data_loader_worker_running(w, sip_module):
            global_meta.pop(w, None)
            continue
        started_at = global_meta.get(w, now)
        age = now - started_at
        if age > retired_ttl_sec:
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
                global_meta.pop(w, None)
                continue
            global_meta[w] = now
        running_global.append(w)
    if len(running_global) > max_global_workers:
        running_global = running_global[-max_global_workers:]
    global_workers[:] = running_global
    for w in list(global_meta.keys()):
        if w not in global_workers and w not in window._retired_data_loader_workers:
            global_meta.pop(w, None)


def is_rescan_worker_running(worker, sip_module) -> bool:
    if not is_data_loader_worker_alive(worker, sip_module):
        return False
    try:
        if hasattr(worker, "isRunning"):
            return bool(worker.isRunning())
    except Exception:
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
    now = perf_counter()
    running_global = []
    for w in global_workers:
        if not is_rescan_worker_running(w, sip_module):
            global_meta.pop(w, None)
            continue
        started_at = global_meta.get(w, now)
        age = now - started_at
        if age > retired_ttl_sec:
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
                global_meta.pop(w, None)
                continue
            global_meta[w] = now
        running_global.append(w)
    if len(running_global) > max_global_workers:
        running_global = running_global[-max_global_workers:]
    global_workers[:] = running_global
    for w in list(global_meta.keys()):
        if w not in global_workers:
            global_meta.pop(w, None)


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
    try:
        try:
            worker.data_loaded.disconnect()
        except Exception as exc:
            logger.debug("Falha ao desconectar data_loaded do worker de carga: %s", exc)
        try:
            worker.error_occurred.disconnect()
        except Exception as exc:
            logger.debug("Falha ao desconectar error_occurred do worker de carga: %s", exc)
        try:
            worker.finished.disconnect()
        except Exception as exc:
            logger.debug("Falha ao desconectar finished do worker de carga: %s", exc)
        still_running = False
        try:
            if hasattr(worker, "cancel"):
                worker.cancel()
            elif hasattr(worker, "requestInterruption"):
                worker.requestInterruption()
            if hasattr(worker, "isRunning") and worker.isRunning():
                worker.quit()
                if int(wait_ms or 0) > 0:
                    worker.wait(int(wait_ms))
            still_running = bool(hasattr(worker, "isRunning") and worker.isRunning())
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
            logger.debug("Falha ao podar workers de carga apos erro de cleanup: %s", prune_exc)
        return False
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
        logger.debug("Falha ao podar workers de carga apos cleanup: %s", exc)
    return True


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
        missing_db_msg = f"Banco de dados '{db_path}' nao encontrado. Execute o programa principal primeiro."
        logger.warning(missing_db_msg)
        try:
            window.status_label.setText("Status: Banco de dados nao encontrado.")
        except Exception:
            pass
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
    worker.data_loaded.connect(lambda df, rid=request_id: on_data_loaded(window, df, request_id=rid))
    worker.error_occurred.connect(lambda msg, rid=request_id: on_load_error(window, msg, request_id=rid, qmessagebox=qmessagebox))
    worker.finished.connect(
        lambda w=worker, rid=request_id: on_load_finished(
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
    )
    try:
        worker.finished.connect(worker.deleteLater)
    except Exception as exc:
        logger.debug("Falha ao conectar deleteLater no worker de carga atual: %s", exc)
    worker.start()


def on_data_loaded(window, df: pd.DataFrame, request_id: int | None = None):
    active_id = getattr(window, "_active_data_load_request_id", None)
    if request_id is not None and active_id is not None and request_id != active_id:
        logger.debug("Ignorando resultado de carga obsoleto (request_id=%s, active=%s)", request_id, active_id)
        return
    df_copy = df.copy()
    window.df_completo = df_copy
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
    except Exception:
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


def on_load_error(window, error_msg: str, *, request_id: int | None = None, qmessagebox=None):
    active_id = getattr(window, "_active_data_load_request_id", None)
    if request_id is not None and active_id is not None and request_id != active_id:
        logger.debug("Ignorando erro de carga obsoleto (request_id=%s, active=%s)", request_id, active_id)
        return
    safe_error_msg = "Nao foi possivel carregar os dados. Consulte os logs para detalhes tecnicos."
    logger.error("Erro no carregamento de dados (request_id=%s): %s", request_id, error_msg)
    if os.environ.get("PYTEST_CURRENT_TEST"):
        logger.debug("PYTEST_CURRENT_TEST set; skipping modal load error dialog.")
    else:
        if qmessagebox is not None:
            qmessagebox.critical(window, "Erro de Carregamento", safe_error_msg)
    window.status_label.setText("Status: Erro ao carregar dados.")
    window.load_button.setEnabled(True)
    window.search_button.setEnabled(True)
    window.progress_bar.setVisible(False)


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
