"""RD-07a: numero_ssa exibido como esta gravado (regra unica display_numero_ssa)."""

import pytest

from interface import table_printer as tp
from interface.cli_width_manager import CLIWidthManager
from shared.numero_ssa import display_numero_ssa


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        (None, "-"),
        ("", "-"),
        ("  \t ", "-"),
        ("nan", "-"),
        ("12", "12"),
        ("001", "001"),
        ("202512345", "202512345"),
        ("202512345.0", "202512345"),  # artefato float nao vira 2025123450
        (202512345.0, "202512345"),
        ("XX202512345YY", "202512345"),
        ("2025123456789", "2025123456789"),  # sem truncar (antes: 512345678)
        ("abc123xyz", "123"),
    ],
)
def test_display_numero_ssa_cases(valor, esperado):  # noqa: D103
    assert display_numero_ssa(valor) == esperado


def test_cli_displays_use_the_same_rule():  # noqa: D103
    manager = CLIWidthManager()
    for valor in ("202512345.0", "2025123456789", "", "SSA 202512345"):
        assert manager.normalize_ssa_number(valor) == display_numero_ssa(valor)
    assert not hasattr(tp, "_normalize_ssa")


def test_display_numero_ssa_idempotent():  # noqa: D103
    for valor in ("202512345", "2025123456789", "12"):
        assert display_numero_ssa(display_numero_ssa(valor)) == display_numero_ssa(valor)
