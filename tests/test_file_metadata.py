import os
import logging
from datetime import datetime
from typing import cast

from utils.file_metadata import (
    choose_latest,
    extract_datetime_from_filename,
    get_file_metadata,
    parse_datetime_from_filename,
    should_update_ssa,
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


def test_choose_latest_prefers_name_over_mtime(tmp_path):
    f1 = tmp_path / "Consulta SSA - 14-07-2025_0343PM.xlsx"
    f1.write_text("a")
    f2 = tmp_path / "Consulta SSA - 13-07-2025_0343PM.xlsx"
    f2.write_text("b")
    os.utime(f1, (1_700_000_000, 1_700_000_000))
    os.utime(f2, (1_800_000_000, 1_800_000_000))
    chosen = choose_latest([str(f1), str(f2)])
    assert chosen is not None
    assert os.path.basename(chosen).startswith("Consulta SSA - 14-07-2025")


def test_choose_latest_logs_and_ignores_invalid_candidate(caplog):
    with caplog.at_level(logging.DEBUG):
        chosen = choose_latest([cast(str, None)])

    assert chosen is None
    assert "Ignorando candidato de arquivo invalido" in caplog.text


def test_extract_datetime_from_filename_variants():
    cases = [
        ("Todas as SSAs - 15-07-2025_0143PM (2).xlsx", datetime(2025, 7, 15, 13, 43)),
        (
            "IEE3_Emissor__202401_20250715_Todas as SSAs - 15-07-2025_1033AM.xlsx",
            datetime(2025, 7, 15, 10, 33),
        ),
        ("SSAs Executadas_15-07-2025_0239PM.xlsx", datetime(2025, 7, 15, 14, 39)),
        ("Consulta SSA - 14-07-2025_0343PM.xlsx", datetime(2025, 7, 14, 15, 43)),
        ("Pendentes de Execucao_15-07-2025_0223PM.xlsx", datetime(2025, 7, 15, 14, 23)),
    ]
    for fname, expected_dt in cases:
        dt = extract_datetime_from_filename(fname)
        assert dt == expected_dt


def test_extract_datetime_from_filename_invalid():
    assert extract_datetime_from_filename("Sem data.xlsx") is None


def test_should_update_ssa_logic():
    assert should_update_ssa(None, datetime(2025, 7, 14, 10, 0).isoformat()) is True
    assert should_update_ssa(datetime(2025, 7, 14, 10, 0).isoformat(), None) is False
    assert (
        should_update_ssa(
            datetime(2025, 7, 14, 10, 0).isoformat(),
            datetime(2025, 7, 15, 9, 0).isoformat(),
        )
        is True
    )
    assert (
        should_update_ssa(
            datetime(2025, 7, 15, 9, 0).isoformat(),
            datetime(2025, 7, 14, 10, 0).isoformat(),
        )
        is False
    )


def test_get_file_metadata_shapes(tmp_path):
    fname = "SSAs Executadas_15-07-2025_0239PM.xlsx"
    p = tmp_path / fname
    p.write_text("dummy")
    name, dt_iso, import_iso = get_file_metadata(str(p))
    assert name == fname
    assert dt_iso == datetime(2025, 7, 15, 14, 39).isoformat()
    assert isinstance(import_iso, str)
