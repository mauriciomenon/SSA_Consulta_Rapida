"""Persistence helpers for saved GUI filters."""

from __future__ import annotations

import copy
import json
import os
import tempfile
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from gui.gui_config import get_gui_main_preferences_path
from utils.robust_logging import get_robust_logger

logger = get_robust_logger().get_logger(__name__, "gui")


@dataclass(frozen=True)
class PersistentFilterIndex:
    signature: tuple[tuple[str, str], ...]
    state_keys: frozenset[str]
    legacy_terms: frozenset[str]


@dataclass
class PersistentFilterStore:
    path: str
    _index: PersistentFilterIndex | None = None
    _index_count: int | None = None

    def load(self) -> list[dict[str, Any]]:
        filters = load_persistent_filters_file(self.path)
        self._index = build_persistent_filter_index(filters)
        self._index_count = len(filters)
        return filters

    def save(self, filters: Any) -> bool:
        return save_persistent_filters_file(self.path, filters or [])

    def add_filter(
        self,
        filters: list[dict[str, Any]],
        new_filter: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], bool]:
        updated_filters = sort_persistent_filters([*filters, new_filter])
        if not self.save(updated_filters):
            return filters, False
        self._add_filter_to_index(new_filter)
        self._index_count = len(updated_filters)
        return updated_filters, True

    def invalidate_index(self) -> None:
        self._index = None
        self._index_count = None

    def index_for(self, filters: Any) -> PersistentFilterIndex:
        filter_list = filters if isinstance(filters, list) else []
        if not isinstance(self._index, PersistentFilterIndex):
            self._index = build_persistent_filter_index(filter_list)
        elif self._index_count != len(filter_list):
            self._index = build_persistent_filter_index(filter_list)
        self._index_count = len(filter_list)
        return self._index

    def _add_filter_to_index(self, new_filter: dict[str, Any]) -> None:
        if not isinstance(self._index, PersistentFilterIndex):
            return
        state_key = _filter_item_state_key(new_filter)
        term = str(new_filter.get("terms", "") or "").strip()
        state_keys = set(self._index.state_keys)
        legacy_terms = set(self._index.legacy_terms)
        if state_key:
            state_keys.add(state_key)
        elif term:
            legacy_terms.add(term)
        self._index = PersistentFilterIndex(
            signature=(*self._index.signature, (state_key, term)),
            state_keys=frozenset(state_keys),
            legacy_terms=frozenset(legacy_terms),
        )


def get_gui_saved_filters_path() -> str:
    config_dir = os.path.dirname(get_gui_main_preferences_path())
    return os.path.join(config_dir, "gui_saved_filters.json")


class PersistentFilterJSONEncoder(json.JSONEncoder):
    def default(self, o: Any) -> Any:
        if isinstance(o, set):
            return sorted(o, key=str)
        if isinstance(o, datetime):
            return o.isoformat(sep=" ")
        if isinstance(o, date):
            return o.isoformat()
        return super().default(o)


def persistent_filter_state_key(state: Any) -> str:
    if not isinstance(state, dict):
        return ""
    return json.dumps(
        state,
        sort_keys=True,
        ensure_ascii=True,
        cls=PersistentFilterJSONEncoder,
    )


def _filter_item_state_key(item: dict[str, Any]) -> str:
    return persistent_filter_state_key(item.get("state"))


def _iter_filter_index_parts(filters: Any) -> Iterator[tuple[str, str]]:
    if not isinstance(filters, list):
        return
    for item in filters:
        if not isinstance(item, dict):
            continue
        state_key = _filter_item_state_key(item)
        term = str(item.get("terms", "") or "").strip()
        if state_key:
            yield (state_key, term)
        else:
            yield ("", term)


def build_persistent_filter_index(filters: Any) -> PersistentFilterIndex:
    state_keys: set[str] = set()
    legacy_terms: set[str] = set()
    signature_parts: list[tuple[str, str]] = []
    for state_key, term in _iter_filter_index_parts(filters):
        signature_parts.append((state_key, term))
        if state_key:
            state_keys.add(state_key)
        elif term:
            legacy_terms.add(term)
    signature = tuple(signature_parts)
    return PersistentFilterIndex(
        signature=signature,
        state_keys=frozenset(state_keys),
        legacy_terms=frozenset(legacy_terms),
    )


def _write_private_json_file(path: str, payload: dict[str, Any]) -> None:
    target_dir = os.path.dirname(path) or "."
    base_name = os.path.basename(path) or "gui_saved_filters.json"
    os.makedirs(target_dir, exist_ok=True)
    tmp_path = None
    try:
        with _private_file_umask():
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                prefix=".tmp.",
                suffix=f".{base_name}",
                dir=target_dir,
                delete=False,
            ) as handle:
                tmp_path = handle.name
                if os.name == "posix":
                    os.fchmod(handle.fileno(), 0o600)
                _dump_private_json_payload(handle, payload)
        _replace_private_json_file(tmp_path, path)
        tmp_path = None
    finally:
        if tmp_path:
            try:
                os.remove(tmp_path)
            except FileNotFoundError:
                pass
            except OSError as exc:
                logger.warning(
                    "Falha ao remover arquivo temporario de filtros: %s", exc
                )


def _replace_private_json_file(source_path: str, target_path: str) -> None:
    last_error: OSError | None = None
    for attempt in range(3):
        try:
            os.replace(source_path, target_path)
            if os.name == "posix":
                os.chmod(target_path, 0o600)
            return
        except OSError as exc:
            last_error = exc
            if attempt >= 2:
                break
            time.sleep(0.05 * (attempt + 1))
    if last_error is not None:
        raise last_error


@contextmanager
def _private_file_umask() -> Iterator[None]:
    old_umask = os.umask(0o177)
    try:
        yield
    finally:
        os.umask(old_umask)


def _dump_private_json_payload(handle: Any, payload: dict[str, Any]) -> None:
    json.dump(
        payload,
        handle,
        indent=2,
        ensure_ascii=False,
        cls=PersistentFilterJSONEncoder,
    )
    handle.flush()


def sort_persistent_filters(filters: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(filters, key=lambda item: str(item.get("name") or "").casefold())


def load_persistent_filters_file(path: str) -> list[dict[str, Any]]:
    if not os.path.exists(path):
        return []
    try:
        with open(path, encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Falha ao carregar filtros salvos: %s", exc)
        return []

    filters = payload.get("filters") if isinstance(payload, dict) else payload
    if not isinstance(filters, list):
        return []

    loaded_filters: list[dict[str, Any]] = []
    for item in filters:
        if not isinstance(item, dict):
            logger.warning("Filtro salvo invalido ignorado: item nao e objeto.")
            continue
        name = str(item.get("name") or "").strip()
        terms = str(item.get("terms") or "").strip()
        state = item.get("state")
        if not name:
            logger.warning("Filtro salvo invalido ignorado: nome ausente.")
            continue
        if not isinstance(state, dict) and not terms:
            logger.warning("Filtro salvo invalido ignorado: state/terms ausente.")
            continue
        loaded_filter = {"name": name, "terms": terms}
        if isinstance(state, dict):
            loaded_filter["state"] = copy.deepcopy(state)
        loaded_filters.append(loaded_filter)
    return sort_persistent_filters(loaded_filters)


def save_persistent_filters_file(path: str, filters: Any) -> bool:
    payload = {
        "version": 1,
        "filters": filters or [],
    }
    try:
        _write_private_json_file(path, payload)
        return True
    except OSError as exc:
        logger.warning(
            "Falha ao salvar filtros persistentes ou ajustar permissoes: %s", exc
        )
    except Exception as exc:
        logger.warning("Falha ao salvar filtros persistentes: %s", exc)
    return False
