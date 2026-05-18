import time

import pandas as pd

from core import app_logic


def _large_identifier_frame(rows: int = 80_000) -> pd.DataFrame:
    target_index = rows // 2
    numeros = [f"2036{i:05d}" for i in range(rows)]
    numeros[target_index] = "202605373"
    return pd.DataFrame(
        {
            "numero_ssa": numeros,
            "derivada_de": [""] * rows,
            "descricao_ssa": [f"descricao linha {i}" for i in range(rows)],
            "setor_executor": ["IEE1" if i % 2 else "MEL4" for i in range(rows)],
        }
    )


def test_exact_identifier_search_uses_identifier_columns_without_heavy_cache() -> None:
    df = _large_identifier_frame()

    started = time.perf_counter()
    result = app_logic.filter_dataframe(
        df,
        ["=202605373"],
        ["numero_ssa", "derivada_de", "descricao_ssa", "setor_executor"],
    )
    elapsed_ms = (time.perf_counter() - started) * 1000.0

    assert result["numero_ssa"].tolist() == ["202605373"]
    assert "_filter_search_cache" not in df.attrs
    assert elapsed_ms < 250


def test_exact_identifier_search_is_limited_to_relation_identifier_columns() -> None:
    df = pd.DataFrame(
        {
            "numero_ssa": ["202600001", "202600002"],
            "derivada_de": ["", ""],
            "descricao_ssa": ["202605373", "texto normal"],
        }
    )

    result = app_logic.filter_dataframe(
        df,
        ["=202605373"],
        ["numero_ssa", "derivada_de", "descricao_ssa"],
    )

    assert result.empty


def test_exact_identifier_search_accepts_float_artifact_in_relation_columns() -> None:
    df = pd.DataFrame(
        {
            "numero_ssa": ["202600001", "202605373.0"],
            "derivada_de": ["", ""],
            "descricao_ssa": ["a", "b"],
        }
    )

    result = app_logic.filter_dataframe(
        df,
        ["=202605373"],
        ["numero_ssa", "derivada_de", "descricao_ssa"],
    )

    assert result["numero_ssa"].tolist() == ["202605373.0"]
