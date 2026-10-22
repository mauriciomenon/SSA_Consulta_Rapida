import pandas as pd

from utils.formatting import (
    format_cell,
    format_dataframe_for_display,
    format_iso_duration,
)


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


def test_format_iso_duration_layout_sam():
    assert format_iso_duration("P1Y9M22DT5H47M") == "1a, 9m, 22d 5h : 47mi"
    assert format_iso_duration("PT45M") == "45mi"
    assert format_iso_duration("P12DT3H4M") == "12d 3h : 4mi"
    assert format_iso_duration("P1M2D") == "1m, 2d"
    # Formas vistas no SAM: minutos sem horas e horas sem minutos.
    assert format_iso_duration("P1Y6M5DT49M") == "1a, 6m, 5d 49mi"
    assert format_iso_duration("P1Y4MT38M") == "1a, 4m, 38mi"
    assert format_iso_duration("P21DT19H") == "21d 19h"
    assert format_iso_duration("P1Y") == "1a"


def test_format_iso_duration_passthrough_e_nulos():
    # Texto que o importador nao converteu volta sem alteracao.
    assert format_iso_duration("0mi") == "0mi"
    assert format_iso_duration("Fora de Prazo") == "Fora de Prazo"
    assert format_iso_duration("P") == "P"
    assert format_iso_duration("PT") == "PT"
    assert format_iso_duration("P1W") == "P1W"
    assert format_iso_duration(None) == ""
    assert format_iso_duration("") == ""


def test_format_cell_formata_somente_tempo_excedido():
    assert format_cell("P12DT3H4M", "tempo_excedido") == "12d 3h : 4mi"
    assert format_cell(None, "tempo_excedido") == ""
    # Outras colunas de tempo guardam texto SAM bruto: sem conversao.
    assert format_cell("P12DT3H4M", "tempo_total") == "P12DT3H4M"
    df = pd.DataFrame({"tempo_excedido": ["P1Y9M22DT5H47M", "x"]})
    out = format_dataframe_for_display(df)
    assert list(out["tempo_excedido"]) == ["1a, 9m, 22d 5h : 47mi", "x"]
    assert list(df["tempo_excedido"]) == ["P1Y9M22DT5H47M", "x"]
