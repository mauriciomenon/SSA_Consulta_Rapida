from __future__ import annotations

from typing import cast

from gui.ssa import details_derivadas_model


def test_normalize_relation_value_rejects_prefixed_identifier() -> None:
    assert details_derivadas_model.normalize_relation_value("SSA-2025") == ""
    assert details_derivadas_model.normalize_relation_value("REF_123") == ""


def test_normalize_tree_data_preserves_parent_sibling_family() -> None:
    data = details_derivadas_model.normalize_tree_data(
        target="202600101",
        snapshot=None,
        fallback_children=[],
        direct_parent="202600100",
        local_payload={
            "parents": ["202600100"],
            "children": [],
            "family_roots": ["202600100"],
            "family_descendants": [
                {"ssa": "202600101", "parent": "202600100"},
                {"ssa": "202600102", "parent": "202600100"},
            ],
            "family_truncated": False,
        },
        related=[],
        target_status="APG",
    )

    assert data["parents"] == ["202600100"]
    assert data["family_roots"] == ["202600100"]
    assert data["render_family"] is True
    assert data["target_status"] == "APG"


def test_build_tree_render_model_orders_family_without_gui() -> None:
    model = details_derivadas_model.build_tree_render_model(
        {
            "target": "202600101",
            "family_roots": ["202600100"],
            "descendants": [
                {"ssa": "202600101", "parent": "202600100"},
                {"ssa": "202600102", "parent": "202600100"},
                {"ssa": "202600103", "parent": "202600102"},
            ],
            "render_family": True,
            "descendants_count": 3,
        }
    )

    assert model is not None
    assert model.render_family is True
    first_child = model.child_map["202600100"][0]
    nested_child = model.child_map["202600102"][0]
    assert isinstance(first_child, dict)
    assert isinstance(nested_child, dict)
    assert cast(dict[str, object], first_child)["ssa"] == "202600101"
    assert cast(dict[str, object], nested_child)["ssa"] == "202600103"


def test_build_graph_model_marks_related_edges_and_partial_count() -> None:
    model = details_derivadas_model.build_graph_model(
        {
            "target": "202600023",
            "children": ["202600024"],
            "descendants": [
                {
                    "ssa": "202600024",
                    "parent": "202600023",
                    "relation_type": 2,
                    "relation_raw_label": "Relacionada",
                }
            ],
            "related": [{"ssa": "202500777", "relacao": "REL"}],
            "descendants_count": 2,
            "descendants_partial": True,
        },
        max_descendants=1,
        node_width=100,
        node_height=30,
        x_gap=170,
        y_gap=60,
        margin=8,
    )

    assert model is not None
    assert ("202600023", "202600024") in model.edges
    assert ("202600023", "202600024") in model.dashed_edges
    assert ("202600023", "202500777") in model.dashed_edges
    assert model.truncated == 1


def test_build_graph_model_positions_family_target_even_when_descendants_skip_target() -> None:
    model = details_derivadas_model.build_graph_model(
        {
            "target": "202600101",
            "parents": ["202600100"],
            "family_roots": ["202600100"],
            "descendants": [
                {"ssa": "202600102", "parent": "202600100"},
            ],
            "render_family": True,
        },
        max_descendants=10,
        node_width=100,
        node_height=30,
        x_gap=170,
        y_gap=60,
        margin=8,
    )

    assert model is not None
    assert ("202600100", "202600101") in model.edges
    assert "202600101" in model.nodes
    assert "202600101" in model.positions
    assert "202600102" in model.positions


def test_build_graph_model_keeps_single_node_without_edges() -> None:
    model = details_derivadas_model.build_graph_model(
        {"target": "202600023", "children": [], "descendants": [], "related": []},
        max_descendants=1,
        node_width=100,
        node_height=30,
        x_gap=170,
        y_gap=60,
        margin=8,
    )

    assert model is not None
    assert model.nodes == {"202600023"}
    assert model.edges == []


def test_build_mermaid_text_uses_stable_text_node_ids() -> None:
    mermaid = details_derivadas_model.build_mermaid_text(
        {"target": "SSA-2025", "children": ["REL-2025"]},
        normalizer=lambda value: str(value or "").strip(),
    )

    assert mermaid.startswith("flowchart LR")
    assert "N_" in mermaid
    assert "N2025" not in mermaid


def test_build_graph_model_accepts_same_custom_normalizer_as_mermaid() -> None:
    def normalizer(value: object) -> str:
        return str(value or "").strip().upper()

    model = details_derivadas_model.build_graph_model(
        {"target": "ssa-2025", "children": ["rel-2025"]},
        max_descendants=1,
        node_width=100,
        node_height=30,
        x_gap=170,
        y_gap=60,
        margin=8,
        normalizer=normalizer,
    )

    assert model is not None
    assert model.target == "SSA-2025"
    assert ("SSA-2025", "REL-2025") in model.edges
