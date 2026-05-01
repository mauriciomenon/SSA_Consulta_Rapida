from __future__ import annotations

import logging
import sqlite3
import time

import pytest

from armazenamento.derivadas_queries import (
    _collect_paths,
    _open_derivadas_connection,
    build_family_payload_from_edges,
    get_ancestors,
    get_children,
    get_descendants,
    get_hierarchy_profile,
    get_parent,
    get_parents,
    get_paths_down,
    get_paths_up,
    get_ssa_hierarchy_snapshot,
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
            [
                (numero_ssa, derivada_de, f"SSA {numero_ssa}")
                for numero_ssa, derivada_de in rows
            ],
        )
        conn.commit()
    sync_derivadas(db_path)


def _seed_cycle_graph(db_path: str) -> None:
    # Minimal cycle A <-> B to validate path collection behavior.
    rows = [
        ("202500001", "202500002"),
        ("202500002", "202500001"),
    ]
    with sqlite3.connect(db_path) as conn:
        conn.executemany(
            "INSERT INTO ssa_table (numero_ssa, derivada_de, descricao_ssa) VALUES (?, ?, ?)",
            [
                (numero_ssa, derivada_de, f"SSA {numero_ssa}")
                for numero_ssa, derivada_de in rows
            ],
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
    assert [item["ssa"] for item in descendants] == [
        "202500002",
        "202500004",
        "202500003",
    ]
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


def test_paths_do_not_include_spurious_partial_path_when_cycle_only(temp_db):
    _seed_cycle_graph(temp_db)

    down_paths = get_paths_down(temp_db, "202500001", depth=5, max_nodes=100)

    assert ["202500001", "202500002", "202500001"] in down_paths
    assert ["202500001", "202500002"] not in down_paths


def test_paths_emit_warning_when_truncated_by_cap(temp_db, caplog):
    _seed_graph(temp_db)

    with caplog.at_level(logging.WARNING, logger="armazenamento.derivadas_queries"):
        down_paths = get_paths_down(temp_db, "202500001", depth=10, max_nodes=1)

    assert down_paths == [["202500001"]]
    assert "Path traversal truncated" in caplog.text


def test_collect_paths_hard_caps_dense_graph(caplog):
    adjacency = {
        "202500001": [f"2025001{i:02d}" for i in range(20)],
    }
    for child in adjacency["202500001"]:
        adjacency[child] = [f"2025002{i:02d}" for i in range(20)]

    with caplog.at_level(logging.WARNING, logger="armazenamento.derivadas_queries"):
        paths = _collect_paths(
            adjacency,
            "202500001",
            depth=5,
            max_nodes=3,
        )

    assert len(paths) <= 3
    assert "Path traversal truncated" in caplog.text


def test_queries_remain_read_only_under_write_lock(temp_db):
    _seed_graph(temp_db)

    lock_conn = sqlite3.connect(temp_db, timeout=0.1, check_same_thread=False)
    lock_conn.execute("BEGIN IMMEDIATE")
    started_at = time.perf_counter()
    op_elapsed = 0.0
    try:
        children = get_children(temp_db, "202500001")
        op_elapsed = time.perf_counter() - started_at
    finally:
        lock_conn.rollback()
        lock_conn.close()

    assert children == ["202500002", "202500004"]
    assert op_elapsed < 0.5


def test_snapshot_returns_gui_friendly_payload(temp_db):
    _seed_graph(temp_db)

    snapshot = get_ssa_hierarchy_snapshot(temp_db, "202500001", max_distance=5)
    assert snapshot["ssa"] == "202500001"
    assert snapshot["parent"] is None
    assert snapshot["children"] == ["202500002", "202500004"]
    assert snapshot["children_count"] == 2
    assert snapshot["has_children"] is True
    assert snapshot["hierarchy_profile"]["descendants_count"] == 3
    assert [row["ssa"] for row in snapshot["descendants"]] == [
        "202500002",
        "202500004",
        "202500003",
    ]
    assert snapshot["family_roots"] == ["202500001"]
    assert {"ssa": "202500002", "parent": "202500001", "min_distance": 1} in snapshot[
        "family_descendants"
    ]
    assert {"ssa": "202500004", "parent": "202500001", "min_distance": 1} in snapshot[
        "family_descendants"
    ]


def test_snapshot_preserves_relation_metadata_for_graph_rendering(temp_db):
    _seed_graph(temp_db)
    with sqlite3.connect(temp_db) as conn:
        conn.execute(
            """
            UPDATE ssa_derivada_matrix
            SET relation_type = 2, relation_raw_label = 'Relacionada'
            WHERE parent_ssa = '202500001' AND child_ssa = '202500002'
            """
        )
        conn.commit()

    snapshot = get_ssa_hierarchy_snapshot(temp_db, "202500001", max_distance=5)

    child_matches = [
        item for item in snapshot["family_descendants"] if item["ssa"] == "202500002"
    ]
    assert child_matches
    child = child_matches[0]
    assert child["relation_type"] == 2
    assert child["relation_raw_label"] == "Relacionada"


def test_snapshot_ignores_invalid_relation_type_for_graph_rendering(temp_db):
    _seed_graph(temp_db)
    with sqlite3.connect(temp_db) as conn:
        conn.execute(
            """
            UPDATE ssa_derivada_matrix
            SET relation_type = 'bad', relation_raw_label = 'Relacionada'
            WHERE parent_ssa = '202500001' AND child_ssa = '202500002'
            """
        )
        conn.commit()

    snapshot = get_ssa_hierarchy_snapshot(temp_db, "202500001", max_distance=5)

    child_matches = [
        item for item in snapshot["family_descendants"] if item["ssa"] == "202500002"
    ]
    assert child_matches
    child = child_matches[0]
    assert "relation_type" not in child
    assert child["relation_raw_label"] == "Relacionada"


def test_snapshot_for_child_includes_parent_and_sibling_family(temp_db):
    _seed_graph(temp_db)

    snapshot = get_ssa_hierarchy_snapshot(temp_db, "202500003", max_distance=None)

    assert snapshot["parents"] == ["202500002"]
    assert snapshot["family_roots"] == ["202500001"]
    assert {"ssa": "202500002", "parent": "202500001", "min_distance": 1} in snapshot[
        "family_descendants"
    ]
    assert {"ssa": "202500004", "parent": "202500001", "min_distance": 1} in snapshot[
        "family_descendants"
    ]
    assert {"ssa": "202500003", "parent": "202500002", "min_distance": 2} in snapshot[
        "family_descendants"
    ]


def test_snapshot_family_cap_preserves_parent_target_edge(temp_db):
    root = "202500000"
    parent = "202500999"
    target = "202501000"
    rows = [(root, None), (parent, root), (target, parent)]
    rows.extend((f"202500{i:03d}", root) for i in range(1, 20))
    with sqlite3.connect(temp_db) as conn:
        conn.executemany(
            "INSERT INTO ssa_table (numero_ssa, derivada_de, descricao_ssa) VALUES (?, ?, ?)",
            [
                (numero_ssa, derivada_de, f"SSA {numero_ssa}")
                for numero_ssa, derivada_de in rows
            ],
        )
        conn.commit()
    sync_derivadas(temp_db)

    snapshot = get_ssa_hierarchy_snapshot(temp_db, target, max_distance=None, max_nodes=3)

    assert snapshot["family_truncated"] is True
    assert {"ssa": target, "parent": parent, "min_distance": 2} in snapshot[
        "family_descendants"
    ]


def test_build_family_payload_from_edges_includes_parent_and_siblings():
    payload = build_family_payload_from_edges(
        "202500003",
        [
            ("202500001", "202500002"),
            ("202500001", "202500004"),
            ("202500002", "202500003"),
        ],
        max_nodes=10,
    )

    assert payload["parents"] == ["202500002"]
    assert payload["children"] == []
    assert payload["family_roots"] == ["202500001"]
    assert {"ssa": "202500002", "parent": "202500001", "min_distance": 1} in payload[
        "family_descendants"
    ]
    assert {"ssa": "202500004", "parent": "202500001", "min_distance": 1} in payload[
        "family_descendants"
    ]
    assert {"ssa": "202500003", "parent": "202500002", "min_distance": 2} in payload[
        "family_descendants"
    ]


def test_build_family_payload_cap_preserves_direct_parent_target_edge():
    edges = [("202500000", "202599999")]
    edges.extend(("202500000", f"202500{i:03d}") for i in range(1, 40))

    payload = build_family_payload_from_edges(
        "202599999",
        edges,
        max_nodes=1,
    )

    assert payload["family_truncated"] is True
    assert payload["family_descendants"] == [
        {"ssa": "202599999", "parent": "202500000", "min_distance": 1}
    ]


def test_build_family_payload_cap_preserves_target_direct_child_over_sibling():
    edges = [("202500000", "202599999"), ("202599999", "202599998")]
    edges.extend(("202500000", f"202500{i:03d}") for i in range(1, 40))

    payload = build_family_payload_from_edges(
        "202599999",
        edges,
        max_nodes=3,
    )
    edge_pairs = {
        (row["parent"], row["ssa"])
        for row in payload["family_descendants"]
    }

    assert payload["family_truncated"] is True
    assert ("202500000", "202599999") in edge_pairs
    assert ("202599999", "202599998") in edge_pairs


def test_build_family_payload_relation_ids_require_explicit_flag():
    strict_payload = build_family_payload_from_edges(
        "101",
        [("100", "101"), ("100", "102")],
        max_nodes=10,
    )
    relation_payload = build_family_payload_from_edges(
        "101",
        [("100", "101"), ("100", "102")],
        max_nodes=10,
        allow_relation_ids=True,
    )

    assert strict_payload["parents"] == []
    assert strict_payload["family_descendants"] == []
    assert relation_payload["parents"] == ["100"]
    assert relation_payload["family_roots"] == ["100"]
    assert relation_payload["family_descendants"] == [
        {"ssa": "101", "parent": "100", "min_distance": 1},
        {"ssa": "102", "parent": "100", "min_distance": 1},
    ]


def test_build_family_payload_uses_min_distance_for_multiparent_node():
    payload = build_family_payload_from_edges(
        "202500003",
        [
            ("202500001", "202500002"),
            ("202500001", "202500003"),
            ("202500002", "202500003"),
        ],
        max_nodes=10,
    )

    target_edges = [
        row
        for row in payload["family_descendants"]
        if row["ssa"] == "202500003"
    ]

    assert target_edges
    assert {row["parent"] for row in target_edges} == {"202500001", "202500002"}
    assert {row["min_distance"] for row in target_edges} == {1}


def test_snapshot_returns_empty_for_invalid_ssa(temp_db):
    _seed_graph(temp_db)
    snapshot = get_ssa_hierarchy_snapshot(temp_db, "invalid", max_distance=5)
    assert snapshot["ssa"] is None
    assert snapshot["parents"] == []
    assert snapshot["children"] == []


def test_queries_reject_invalid_max_distance(temp_db):
    _seed_graph(temp_db)
    with pytest.raises(ValueError):
        get_ancestors(temp_db, "202500003", max_distance=0)
    with pytest.raises(ValueError):
        get_descendants(temp_db, "202500001", max_distance=-1)
    with pytest.raises(ValueError):
        get_ssa_hierarchy_snapshot(temp_db, "202500001", max_distance=0)


def test_queries_on_fresh_db_do_not_create_derivadas_tables(temp_db):
    with sqlite3.connect(temp_db) as conn:
        before = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name LIKE 'ssa_derivada_%'"
            ).fetchall()
        }
    assert before == set()

    assert get_children(temp_db, "202500001") == []
    assert get_hierarchy_profile(temp_db, "202500001") == {}
    snapshot = get_ssa_hierarchy_snapshot(temp_db, "202500001", max_distance=5)
    assert snapshot["ssa"] == "202500001"
    assert snapshot["children"] == []

    with sqlite3.connect(temp_db) as conn:
        after = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name LIKE 'ssa_derivada_%'"
            ).fetchall()
        }
    assert after == set()


def test_open_derivadas_connection_hides_connection_when_schema_not_ready(temp_db):
    with _open_derivadas_connection(temp_db) as (conn, schema_ready):
        assert schema_ready is False
        assert conn is None
