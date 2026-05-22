import pandas as pd

from utils.formatting import format_cell, format_dataframe_for_display


def test_format_cell_number_and_nulls():
    assert format_cell(10.0) == "10"  # suprime .0
    assert format_cell(float("nan")) == ""  # NaN vira vazio
    assert format_cell(None) == ""
    assert format_cell(pd.NA) == ""


def test_format_cell_dates():
    assert format_cell("2025-07-14", column="data_cadastro") == "14/07/2025"
    assert (
        format_cell("2025-07-14T09:30:00", column="data_cadastro") == "14/07/2025"
    )
    assert (
        format_cell("2025-07-14T09:30:00.123Z", column="data_cadastro")
        == "14/07/2025"
    )
    assert (
        format_cell("2025-07-14T09:30:00-03:00", column="data_cadastro")
        == "14/07/2025"
    )
    assert (
        format_cell("2025-07-14T09:30:00+0300", column="data_cadastro")
        == "14/07/2025"
    )
    assert (
        format_cell(pd.to_datetime("2025-07-15"), column="data_limite") == "15/07/2025"
    )


def test_format_dataframe_for_display_and_ssa():
    df = pd.DataFrame(
        {
            "numero_ssa": ["123", "202500045", None],
            "semana_cadastro": [30.0, 31.0, None],
            "data_cadastro": ["14/07/2025", "2025-07-15", None],
            "texto": ["abc", None, ""],
        }
    )
    out = format_dataframe_for_display(df)
    # numero_ssa so exibe valor canonico quando valido
    assert out.loc[0, "numero_ssa"] == ""
    assert out.loc[1, "numero_ssa"] == "202500045"
    assert out.loc[2, "numero_ssa"] == ""
    # semana becomes int string without .0
    assert out.loc[0, "semana_cadastro"] == "30"
    assert out.loc[1, "semana_cadastro"] == "31"
    assert out.loc[2, "semana_cadastro"] == ""
    # dates formatted
    assert out.loc[0, "data_cadastro"] == "14/07/2025"
    assert out.loc[1, "data_cadastro"] == "15/07/2025"
    # null text becomes empty string (table_printer later maps empty to '-')
    assert out.loc[1, "texto"] == ""


def test_format_dataframe_for_display_hides_pandas_na_in_generic_columns():
    df = pd.DataFrame(
        {
            "texto": [pd.NA, "ok"],
            "setor_executor": [pd.NA, "MEL1"],
        }
    )

    out = format_dataframe_for_display(df)

    assert out.loc[0, "texto"] == ""
    assert out.loc[0, "setor_executor"] == ""
    assert out.loc[1, "texto"] == "ok"
    assert out.loc[1, "setor_executor"] == "MEL1"
