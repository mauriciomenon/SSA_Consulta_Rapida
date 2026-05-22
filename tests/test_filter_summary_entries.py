from gui.ssa.filter_summary_advanced import build_advanced_summary_entries
from gui.ssa.filter_summary_entries import excluded_summary_week_range, shorten_summary_label


def test_excluded_summary_week_range_uses_readable_direction():
    assert excluded_summary_week_range(None, "202401") == "exclui ate 202401"
    assert excluded_summary_week_range("202401", None) == "exclui desde 202401"
    assert excluded_summary_week_range("202401", "202405") == "exclui 202401-202405"


def test_excluded_week_entry_avoids_double_negative_operator():
    entries = build_advanced_summary_entries(
        {
            "semana_emissao_inicio": None,
            "semana_emissao_fim": "202401",
            "semana_emissao_exclude": True,
        }
    )

    assert "Sem Emis: exclui ate 202401" in entries
    assert all("!= <=" not in key for key in entries)


def test_priority_planning_summary_keeps_priority_meaning():
    assert shorten_summary_label("Prio Planejamento: Alta") == "Prio Plan: Alta"
