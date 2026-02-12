from __future__ import annotations

import sqlite3
import threading
import time

from armazenamento.derivadas_queries import (
    get_ancestors,
    get_children,
    get_descendants,
    get_hierarchy_profile,
    get_parent,
    get_parents,
    get_paths_down,
    get_paths_up,
    get_top_by_metric,
)
from armazenamento.derivadas_sync import sync_derivadas


def _seed_graph(db_path: str) -> None:
    rows = [
        ("202500001", None),
        ("202500002", "202500001"),
        ("202500003", "202500002"),
        ("202500004", "202500001"),
    ]
    with sqlite3.connect(db_path) as conn:
        conn.executemany(
            "INSERT INTO ssa_table (numero_ssa, derivada_de, descricao_ssa) VALUES (?, ?, ?)",
            [(numero_ssa, derivada_de, f"SSA {numero_ssa}") for numero_ssa, derivada_de in rows],
        )
        conn.commit()
    sync_derivadas(db_path)


def test_parents_and_children_queries(temp_db):
    _seed_graph(temp_db)

    assert get_parent(temp_db, "202500002") == "202500001"
    assert get_parents(temp_db, "202500003") == ["202500002"]
    assert get_children(temp_db, "202500001") == ["202500002", "202500004"]
    assert get_children(temp_db, "202500999") == []


def test_ancestors_descendants_and_profile(temp_db):
    _seed_graph(temp_db)

    ancestors = get_ancestors(temp_db, "202500003")
    descendants = get_descendants(temp_db, "202500001")
    profile = get_hierarchy_profile(temp_db, "202500001")

    assert [item["ssa"] for item in ancestors] == ["202500002", "202500001"]
    assert [item["ssa"] for item in descendants] == ["202500002", "202500004", "202500003"]
    assert profile["direct_children_count"] == 2
    assert profile["descendants_count"] == 3


def test_paths_and_top_metrics(temp_db):
    _seed_graph(temp_db)

    down_paths = get_paths_down(temp_db, "202500001", depth=4, max_nodes=100)
    up_paths = get_paths_up(temp_db, "202500003", depth=4, max_nodes=100)
    top_rows = get_top_by_metric(temp_db, "descendants", limit=2)

    assert any(path[:2] == ["202500001", "202500002"] for path in down_paths)
    assert any(path[-1] == "202500001" for path in up_paths)
    assert top_rows
    assert top_rows[0]["ssa"] == "202500001"
    assert top_rows[0]["metric"] >= 2


def test_queries_remain_read_only_under_write_lock(temp_db):
    _seed_graph(temp_db)

    lock_conn = sqlite3.connect(temp_db, timeout=0.1, check_same_thread=False)
    lock_conn.execute("BEGIN IMMEDIATE")

    def _release_lock() -> None:
        time.sleep(1.0)
        lock_conn.rollback()
        lock_conn.close()

    releaser = threading.Thread(target=_release_lock)
    releaser.start()
    started_at = time.perf_counter()
    op_elapsed = 0.0
    try:
        children = get_children(temp_db, "202500001")
        op_elapsed = time.perf_counter() - started_at
    finally:
        releaser.join(timeout=2.0)

    assert children == ["202500002", "202500004"]
    assert op_elapsed < 0.5
