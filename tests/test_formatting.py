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


def test_format_cell_strips_terminal_escape_and_control_chars():
    from utils.formatting import format_cell, format_table_cell

    payload = "\x1b]52;c;SGVsbG8=\x07 clip \x1b[31mred\x1b[0m \x9b"
    # Controles viram marcador visivel (U+FFFD), nunca sequencia ativa.
    assert format_cell(payload) == "\ufffd]52;c;SGVsbG8=\ufffd clip \ufffd[31mred\ufffd[0m \ufffd"

    # \t e \n sobrevivem; \r some (CRLF legitimo vira LF);
    # format_table_cell colapsa \n e herda a sanitizacao.
    assert format_cell("a\tb\nc") == "a\tb\nc"
    assert format_cell("a\r\nb") == "a\nb"
    assert format_table_cell("a\nb\x1b[2J") == "a b\ufffd[2J"


def test_format_cell_sanitizes_fallback_paths_and_preserves_unicode():
    from utils.formatting import format_cell

    # Bypass via coluna semana*: string nao numerica ia crua para
    # _format_number; em data* o fallback vira "" (seguro), mas ESC
    # nao pode vazar em nenhum dos caminhos.
    for col in ("semana_cadastro", "semana_programada", "data_x"):
        out = format_cell("\x1b[31mX\x1b[0m", col)
        assert "\x1b" not in out, col
    assert "X" in format_cell("\x1b[31mX\x1b[0m", "semana_cadastro")

    # numero_ssa invalido cai no str(value) — tambem sanitizado.
    out = format_cell("\x1b[31m123\x1b[0m", "numero_ssa")
    assert "\x1b" not in out

    # NEL vira separador (nao cola palavras); NBSP e soft hyphen sao
    # unicode legitimo e ficam preservados.
    assert format_cell("a\x85b") == "a b"
    assert format_cell("a\xa0b") == "a\xa0b"
    assert format_cell("a\xadb") == "a\xadb"
