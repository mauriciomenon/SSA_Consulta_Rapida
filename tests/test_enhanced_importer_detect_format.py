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
