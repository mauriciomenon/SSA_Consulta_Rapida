import pandas as pd
import pytest

from utils.enhanced_importer import EnhancedAMSImporter


@pytest.fixture
def importer() -> EnhancedAMSImporter:
    return EnhancedAMSImporter()


def test_detect_format_skips_empty_indicators(importer: EnhancedAMSImporter):
    importer.known_formats = {
        "empty": {"indicators": []},
        "blank": {"indicators": ["", "   "]},
        "real": {"indicators": ["Numero da SSA"]},
    }
    df = pd.DataFrame({"Outra Coluna": [1]})

    assert importer.detect_format(df) == "unknown"


def test_import_with_format_detection_rejects_size_before_read(
    importer: EnhancedAMSImporter,
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
):
    from utils import enhanced_importer

    file_path = tmp_path / "large.xlsx"
    file_path.write_bytes(b"12345")
    read_called = False
    monkeypatch.setattr("extracao.extractor.MAX_XLSX_FILE_BYTES", 4)

    def _unexpected_read(*_args, **_kwargs):
        nonlocal read_called
        read_called = True
        raise AssertionError("read_excel must not run")

    monkeypatch.setattr(enhanced_importer.pd, "read_excel", _unexpected_read)

    assert importer.import_with_format_detection(str(file_path)) is None
    assert read_called is False
