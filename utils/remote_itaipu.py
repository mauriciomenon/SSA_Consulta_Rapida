"""
Utilities to access Itaipu SSA APIs with safe defaults.

Features:
- Sync (requests) and async (aiohttp) clients
- Timeout and optional SSL verification disable (for diagnostics only)
- Lightweight retry/backoff for transient errors
- Optional cancellation via threading.Event or asyncio.CancelledError
- Helper functions to filter by executor and to map responses to pandas DataFrame

Note: Do not disable SSL verification in production. Pass verify_ssl=True when possible.
"""

from __future__ import annotations

import importlib
import json
import os
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional


def _import_requests() -> Any:
    try:
        return importlib.import_module("requests")
    except ImportError as exc:
        raise RuntimeError("requests dependency not installed") from exc


def _import_aiohttp() -> Any:
    try:
        return importlib.import_module("aiohttp")
    except ImportError as exc:
        raise RuntimeError("aiohttp dependency not installed") from exc


def _env_url_or_default(name: str, default_url: str) -> str:
    value = os.getenv(name)
    if value is None:
        return default_url
    normalized = str(value).strip()
    return normalized or default_url


BASE_PENDING = _env_url_or_default(
    "ITAIPU_BASE_PENDING",
    "https://apps.itaipu.gov.br/SAM_SMA_API/rest/SSA_API/GetPendingSSAsByLocalizationRange",
)
BASE_DETAIL = _env_url_or_default(
    "ITAIPU_BASE_DETAIL",
    "https://apps.itaipu.gov.br/SAM_SMA_API/rest/SSA_API/GetSSABySSANumber",
)


@dataclass
class RequestOptions:
    timeout: float = 30.0
    verify_ssl: bool = True
    retries: int = 2
    backoff: float = 0.8  # seconds, exponential backoff


def _sleep_backoff(attempt: int, base: float) -> None:
    time.sleep(max(0.0, base * (2 ** max(0, attempt - 1))))


def fetch_pending_ssas(
    start: str = "A000A000",
    end: str = "Z999Z999",
    years: int = 100000,
    opts: Optional[RequestOptions] = None,
    cancel_flag: Optional[threading.Event] = None,
) -> List[Dict[str, Any]]:
    """Synchronous fetch of pending SSAs by localization range.

    cancel_flag: optional threading.Event to allow cooperative cancellation.
    """
    requests = _import_requests()

    if opts is None:
        opts = RequestOptions()

    params = {
        "StartLocalizationCode": start,
        "EndLocalizationCode": end,
        "NumberOfYears": years,
    }
    last_err: Optional[BaseException] = None
    for attempt in range(opts.retries + 1):
        if cancel_flag is not None and cancel_flag.is_set():
            raise RuntimeError("operation cancelled")
        try:
            resp = requests.get(
                BASE_PENDING,
                params=params,
                timeout=opts.timeout,
                verify=opts.verify_ssl,
            )
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list):
                return data
            # Some APIs wrap payloads; accept common shapes
            if isinstance(data, dict):
                for k in ("items", "data", "result"):
                    if k in data and isinstance(data[k], list):
                        return data[k]
            # Fallback: return as single-item list
            return [data]
        except Exception as e:  # noqa: BLE001
            last_err = e
            if attempt >= opts.retries:
                raise
            _sleep_backoff(attempt, opts.backoff)
    # Should not reach here
    if last_err:
        raise last_err
    return []


def fetch_ssa_detail(
    ssa_number: str,
    opts: Optional[RequestOptions] = None,
    cancel_flag: Optional[threading.Event] = None,
) -> Dict[str, Any]:
    requests = _import_requests()

    if opts is None:
        opts = RequestOptions()
    params = {"SSANumber": ssa_number}
    last_err: Optional[BaseException] = None
    for attempt in range(opts.retries + 1):
        if cancel_flag is not None and cancel_flag.is_set():
            raise RuntimeError("operation cancelled")
        try:
            resp = requests.get(
                BASE_DETAIL,
                params=params,
                timeout=opts.timeout,
                verify=opts.verify_ssl,
            )
            resp.raise_for_status()
            data = resp.json()
            return data if isinstance(data, dict) else {"data": data}
        except Exception as e:  # noqa: BLE001
            last_err = e
            if attempt >= opts.retries:
                raise
            _sleep_backoff(attempt, opts.backoff)
    if last_err:
        raise last_err
    return {}


def filter_by_executors(
    items: Iterable[Dict[str, Any]], executors: Iterable[str]
) -> List[Dict[str, Any]]:
    targets = {str(x).strip().lower() for x in executors if str(x).strip()}
    if not targets:
        return list(items)
    out: List[Dict[str, Any]] = []
    for it in items:
        sector = (
            str(it.get("ExecutorSector") or it.get("setor_executor") or "")
            .strip()
            .lower()
        )
        if sector in targets:
            out.append(it)
    return out


def map_to_dataframe(items: Iterable[Dict[str, Any]]):
    try:
        import pandas as pd

        df = pd.DataFrame(list(items))
        # Normalize common column names used in the app
        rename_map = {
            "SSANumber": "numero_ssa",
            "ExecutorSector": "setor_executor",
            "Status": "situacao",
            "Description": "descricao_ssa",
            "RegistrationDate": "data_cadastro",
            "LocalizationCode": "localizacao_codigo",
        }
        cols = {k: v for k, v in rename_map.items() if k in df.columns}
        if cols:
            df = df.rename(columns=cols)
        return df
    except Exception:
        return None


# ------------------ Async versions ------------------
async def fetch_pending_ssas_async(
    start: str = "A000A000",
    end: str = "Z999Z999",
    years: int = 100000,
    opts: Optional[RequestOptions] = None,
    session: Any = None,
):
    aiohttp = _import_aiohttp()
    import ssl as _ssl

    if opts is None:
        opts = RequestOptions()
    params = {
        "StartLocalizationCode": start,
        "EndLocalizationCode": end,
        "NumberOfYears": years,
    }
    ssl_ctx = None
    if not opts.verify_ssl:
        ssl_ctx = _ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = _ssl.CERT_NONE

    close_session = False
    if session is None:
        timeout = aiohttp.ClientTimeout(total=opts.timeout)
        session = aiohttp.ClientSession(timeout=timeout)
        close_session = True
    last_err: Optional[BaseException] = None
    try:
        for attempt in range(opts.retries + 1):
            try:
                async with session.get(
                    BASE_PENDING, params=params, ssl=ssl_ctx
                ) as resp:
                    resp.raise_for_status()
                    data = await resp.json()
                    if isinstance(data, list):
                        return data
                    if isinstance(data, dict):
                        for k in ("items", "data", "result"):
                            if k in data and isinstance(data[k], list):
                                return data[k]
                    return [data]
            except Exception as e:  # noqa: BLE001
                last_err = e
                if attempt >= opts.retries:
                    raise
                await _async_sleep_backoff(attempt, opts.backoff)
    finally:
        if close_session:
            await session.close()
    if last_err:
        raise last_err
    return []


async def fetch_ssa_detail_async(
    ssa_number: str,
    opts: Optional[RequestOptions] = None,
    session: Any = None,
):
    aiohttp = _import_aiohttp()
    import ssl as _ssl

    if opts is None:
        opts = RequestOptions()
    params = {"SSANumber": ssa_number}
    ssl_ctx = None
    if not opts.verify_ssl:
        ssl_ctx = _ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = _ssl.CERT_NONE
    close_session = False
    if session is None:
        timeout = aiohttp.ClientTimeout(total=opts.timeout)
        session = aiohttp.ClientSession(timeout=timeout)
        close_session = True
    last_err: Optional[BaseException] = None
    try:
        for attempt in range(opts.retries + 1):
            try:
                async with session.get(BASE_DETAIL, params=params, ssl=ssl_ctx) as resp:
                    resp.raise_for_status()
                    data = await resp.json()
                    return data if isinstance(data, dict) else {"data": data}
            except Exception as e:  # noqa: BLE001
                last_err = e
                if attempt >= opts.retries:
                    raise
                await _async_sleep_backoff(attempt, opts.backoff)
    finally:
        if close_session:
            await session.close()
    if last_err:
        raise last_err
    return {}


async def _async_sleep_backoff(attempt: int, base: float) -> None:
    import asyncio as _asyncio

    await _asyncio.sleep(max(0.0, base * (2 ** max(0, attempt - 1))))


# --------------- Small helpers for integration ---------------
def parse_executors_csv(csv_text: str) -> List[str]:
    if not csv_text:
        return []
    parts = [p.strip() for p in csv_text.replace(";", ",").split(",")]
    return [p for p in parts if p]


def describe_error(err: BaseException) -> str:
    try:
        return f"{type(err).__name__}: {err}"
    except Exception:
        return str(err) or repr(err)


def to_json_pretty(payload: Any) -> str:
    try:
        return json.dumps(payload, ensure_ascii=False, indent=2)
    except Exception:
        return str(payload)
