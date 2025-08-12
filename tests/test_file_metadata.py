import os
import sys
from datetime import datetime

import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, PROJECT_ROOT)

from utils.file_metadata import extract_datetime_from_filename, should_update_ssa, get_file_metadata


def test_extract_datetime_from_filename_variants():
    cases = [
        ("Todas as SSAs - 15-07-2025_0143PM (2).xlsx", datetime(2025, 7, 15, 13, 43)),
        ("IEE3_Emissor__202401_20250715_Todas as SSAs - 15-07-2025_1033AM.xlsx", datetime(2025, 7, 15, 10, 33)),
        ("SSAs Executadas_15-07-2025_0239PM.xlsx", datetime(2025, 7, 15, 14, 39)),
        ("Consulta SSA - 14-07-2025_0343PM.xlsx", datetime(2025, 7, 14, 15, 43)),
        ("Pendentes de Execução_15-07-2025_0223PM.xlsx", datetime(2025, 7, 15, 14, 23)),
    ]
    for fname, expected_dt in cases:
        dt = extract_datetime_from_filename(fname)
        assert dt == expected_dt


def test_extract_datetime_from_filename_invalid():
    assert extract_datetime_from_filename("Sem data.xlsx") is None


def test_should_update_ssa_logic():
    # No existing date -> update
    assert should_update_ssa(None, datetime(2025, 7, 14, 10, 0).isoformat()) is True
    # No new date -> do not update
    assert should_update_ssa(datetime(2025, 7, 14, 10, 0).isoformat(), None) is False
    # Newer wins
    assert should_update_ssa(datetime(2025, 7, 14, 10, 0).isoformat(), datetime(2025, 7, 15, 9, 0).isoformat()) is True
    # Older does not update
    assert should_update_ssa(datetime(2025, 7, 15, 9, 0).isoformat(), datetime(2025, 7, 14, 10, 0).isoformat()) is False


def test_get_file_metadata_shapes(tmp_path):
    # Create a dummy filename
    fname = "SSAs Executadas_15-07-2025_0239PM.xlsx"
    p = tmp_path / fname
    p.write_text("dummy")
    name, dt_iso, import_iso = get_file_metadata(str(p))
    assert name == fname
    assert dt_iso == datetime(2025, 7, 15, 14, 39).isoformat()
    # import_iso should be a valid ISO string representing now (not asserting exact value)
    assert isinstance(import_iso, str)
