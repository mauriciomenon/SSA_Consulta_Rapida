import pytest

from interface import table_printer as tp


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        (None, '-'),        # None
        ('', '-'),          # vazio
        ('  \t ', '-'),    # whitespace
        ('12', '12'),       # curto (< limiar)
        ('001', '001'),     # preserva zeros curtos
        ('202512345', '202512345'),        # já normalizado
        ('XX202512345YY', '202512345'),    # strip não dígitos
        ('2025123456789', '512345678'),    # últimos 9
        ('abc123xyz', '123'),             # apenas dígitos
    ],
)
def test_normalize_ssa_cases(valor, esperado):  # noqa: D103
    assert tp._normalize_ssa(valor) == esperado


def test_normalize_ssa_short_threshold_boundary():  # noqa: D103
    below = '1234'  # 4 dígitos (< limiar)
    assert tp._normalize_ssa(below) == '1234'
    equal = '12345'  # == limiar (5) => não cai no retorno curto (<)
    assert tp._normalize_ssa(equal) == '12345'


def test_normalize_ssa_full_length_non_prefix():  # noqa: D103
    num = '999999999'  # 9 dígitos sem prefixo 2025
    assert tp._normalize_ssa(num) == '999999999'


def test_normalize_ssa_large_with_prefix_middle():  # noqa: D103
    val = 'AA12025123456789ZZ'
    digits = ''.join(ch for ch in val if ch.isdigit())
    assert digits == '12025123456789'
    expected = digits[-tp.SSA_FULL_LENGTH:]
    assert len(expected) == tp.SSA_FULL_LENGTH
    assert tp._normalize_ssa(val) == expected


def test_normalize_ssa_idempotent_on_clean():  # noqa: D103
    original = '202512345'
    assert tp._normalize_ssa(original) == original
    assert tp._normalize_ssa(tp._normalize_ssa(original)) == original
