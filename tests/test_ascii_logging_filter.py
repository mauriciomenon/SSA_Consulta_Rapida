from __future__ import annotations

import logging

from main import _ASCIIOnlyFilter


def test_ascii_filter_preserves_mapping_args() -> None:
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="Status: %(label)s",
        args=({"label": "Aprovacao com acao"},),
        exc_info=None,
    )
    ascii_filter = _ASCIIOnlyFilter()

    keep = ascii_filter.filter(record)

    assert keep is True
    assert isinstance(record.args, dict)
    assert record.args["label"] == "Aprovacao com acao"
    assert record.getMessage() == "Status: Aprovacao com acao"


def test_ascii_filter_keeps_tuple_args_behavior() -> None:
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=25,
        msg="Valor: %s",
        args=("acao",),
        exc_info=None,
    )
    ascii_filter = _ASCIIOnlyFilter()

    keep = ascii_filter.filter(record)

    assert keep is True
    assert record.args == ("acao",)
    assert record.getMessage() == "Valor: acao"


def test_ascii_filter_sanitizes_nested_values() -> None:
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=40,
        msg="Valor: %s",
        args=({"labels": ["a\u00e7ao", "revis\u00e3o"]},),
        exc_info=None,
    )
    ascii_filter = _ASCIIOnlyFilter()

    keep = ascii_filter.filter(record)

    assert keep is True
    assert record.args == {"labels": ["aao", "reviso"]}
    assert record.getMessage() == "Valor: {'labels': ['aao', 'reviso']}"
