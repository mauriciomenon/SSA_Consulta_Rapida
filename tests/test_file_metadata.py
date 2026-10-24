import logging

from utils.file_metadata import (
    parse_datetime_from_filename,
)


def test_parse_datetime_from_filename_basic_pm():
    fn = "Consulta SSA - 14-07-2025_0343PM.xlsx"
    dt = parse_datetime_from_filename(fn)
    assert dt is not None
    assert dt.year == 2025 and dt.month == 7 and dt.day == 14
    assert dt.hour == 15 and dt.minute == 43


def test_parse_datetime_from_filename_alt_format():
    fn = "Relatorio_2025-07-14 15.43.xlsx"
    dt = parse_datetime_from_filename(fn)
    assert dt is not None
    assert (dt.year, dt.month, dt.day, dt.hour, dt.minute) == (2025, 7, 14, 15, 43)


def test_parse_datetime_from_filename_logs_invalid_date(caplog):
    with caplog.at_level(logging.DEBUG):
        dt = parse_datetime_from_filename("Relatorio_2025-99-99 99.99.xlsx")

    assert dt is None
    assert "Falha ao interpretar data no nome" in caplog.text




def test_dead_file_metadata_helpers_removed():
    """A-30: helpers sem chamador de producao sairam do modulo."""
    from utils import file_metadata

    for name in (
        "choose_latest",
        "extract_datetime_from_filename",
        "get_file_metadata",
        "should_update_ssa",
        "test_date_extraction",
        "PROTECTED_FILENAMES",
    ):
        assert not hasattr(file_metadata, name), name
