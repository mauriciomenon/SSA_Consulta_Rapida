"""Shared dataframe builders and contract test spies for filter tests."""

from __future__ import annotations

from typing import Callable

import pandas as pd


def pipeline_measure_timing(_name: str, callback: Callable[[], object]) -> object:
    """Identity timing hook for apply_filter_refresh_pipeline contract tests."""
    return callback()


def make_numero_ssa_sort_counter() -> tuple[dict[str, int], Callable[..., pd.DataFrame]]:
    """Return sort call counter and patched DataFrame.sort_values wrapper."""
    sort_calls = {"numero_ssa": 0}
    original_sort_values = pd.DataFrame.sort_values

    def counter(frame, by=None, *args, **kwargs):
        if by == "numero_ssa":
            sort_calls["numero_ssa"] += 1
        return original_sort_values(frame, by=by, *args, **kwargs)

    return sort_calls, counter


def make_series_tolist_spy() -> tuple[dict[str, int], Callable[..., list]]:
    """Return tolist call counter and patched Series.tolist wrapper."""
    tolist_calls = {"count": 0}
    original_tolist = pd.Series.tolist

    def spy(self, *args, **kwargs):
        tolist_calls["count"] += 1
        return original_tolist(self, *args, **kwargs)

    return tolist_calls, spy


def build_base_filter_df(*, rows: int = 5) -> pd.DataFrame:
    situacoes = ["APV", "STE", "SCA", "AMP", "APV"]
    executores = ["IEE3", "OURO", "MEL4", "XYZ", "IEE2"]
    emissores = ["ABC", "IEE3", "MEL4", "MEL3", "XYZ"]
    descricoes = ["Teste A", "Teste B", "Teste C", "Teste D", "Teste E"]
    return pd.DataFrame(
        {
            "numero_ssa": list(range(1, rows + 1)),
            "situacao": situacoes[:rows],
            "derivada_de": [""] * rows,
            "localizacao_codigo": [f"LOC{i}" for i in range(1, rows + 1)],
            "descricao_localizacao": ["Desc1"] * rows,
            "equipamento": ["EQ1"] * rows,
            "semana_cadastro": [202501] * rows,
            "semana_programada": [202503] * rows,
            "semana_executada": [202501 + idx for idx in range(rows)],
            "data_cadastro": ["2025-01-01"] * rows,
            "descricao_ssa": descricoes[:rows],
            "setor_executor": executores[:rows],
            "setor_emissor": emissores[:rows],
            "descricao_execucao": [f"Exec {chr(65 + idx)}" for idx in range(rows)],
            "solicitante": [f"User{i}" for i in range(1, rows + 1)],
        }
    )


def build_advanced_filter_contract_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "numero_ssa": [202600001, 202600002, 202600003, 202600004],
            "situacao": ["APV", "STE", "APV", "SCA"],
            "derivada_de": ["", "", "", ""],
            "localizacao_codigo": ["LOC1", "LOC2", "LOC3", "LOC4"],
            "descricao_localizacao": ["Desc"] * 4,
            "equipamento": ["EQ1"] * 4,
            "semana_cadastro": [202501, 202601, 202501, 202701],
            "semana_programada": [202503] * 4,
            "semana_executada": [202501, 202502, 202503, 202504],
            "data_cadastro": [
                "2025-01-01",
                "2026-01-01",
                "2025-05-01",
                "2027-01-01",
            ],
            "descricao_ssa": ["Teste A", "Teste B", "Teste C", "Teste D"],
            "setor_executor": ["IEE3", "IEE3", "MEL4", "MEL4"],
            "setor_emissor": ["ABC", "XYZ", "ABC", "MEL4"],
            "descricao_execucao": ["Exec A", "Exec B", "Exec C", "Exec D"],
            "solicitante": ["Sol A", "Sol B", "Sol A", "Sol C"],
            "responsavel_programacao": ["Prog A", "Prog B", "Prog A", "Prog C"],
            "responsavel_execucao": ["Exec A", "Exec B", "Exec A", "Exec C"],
            "num_reprogramacoes": [0, 1, 2, 2],
            "grau_prioridade_emissao": [1, 2, 1, 3],
            "grau_prioridade_planejamento": [2, 2, 3, 1],
        }
    )


def build_derivadas_family_df(*, child_count: int = 3) -> pd.DataFrame:
    rows: list[tuple[str, str, str]] = [("202600100", "", "STE")]
    rows.append(("202600101", "202600100", "APG"))
    for idx in range(child_count):
        rows.append((f"202600{102 + idx:03d}", "202600100", "SPG"))
    return pd.DataFrame(rows, columns=["numero_ssa", "derivada_de", "situacao"])


def build_large_derivadas_chain(*, total_nodes: int) -> pd.DataFrame:
    rows: list[tuple[str, str, str]] = [("202600000", "", "APG")]
    rows.append(("202600001", "202600000", "APG"))
    for idx in range(2, total_nodes):
        rows.append((f"2026{idx:05d}", "202600000", "APG"))
    return pd.DataFrame(rows, columns=["numero_ssa", "derivada_de", "situacao"])


def build_large_filter_df(*, rows: int) -> pd.DataFrame:
    """Repeat base filter rows to reach the requested row count."""
    template = build_base_filter_df(rows=5)
    chunks = [template] * (rows // 5)
    remainder = rows % 5
    if remainder:
        chunks.append(template.iloc[:remainder].copy())
    large_df = pd.concat(chunks, ignore_index=True)
    large_df["numero_ssa"] = list(range(1, rows + 1))
    return large_df
