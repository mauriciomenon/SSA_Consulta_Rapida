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
    assert isinstance(record.args, tuple)
    assert record.args == ("acao",)
