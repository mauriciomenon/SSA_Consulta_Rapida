from __future__ import annotations

import pandas as pd

from core.handler_base import HandlerBase, HandlerContext


class _DummyHandler(HandlerBase):
    def __init__(self) -> None:
        super().__init__(name="dummy")

    def execute(self, context: HandlerContext):
        return self.create_result(data=None, context=context)


def test_create_result_ignores_non_dataframe_data() -> None:
    handler = _DummyHandler()
    context = HandlerContext(output_format="table")

    result = handler.create_result(
        data="legacy-non-dataframe",
        context=context,
        success=True,
    )

    assert result.success is True
    assert result.output_text == ""
    assert result.stats == {}


def test_create_result_keeps_dataframe_behavior() -> None:
    handler = _DummyHandler()
    context = HandlerContext(output_format="table")
    frame = pd.DataFrame({"numero_ssa": ["202600654"]})

    result = handler.create_result(data=frame, context=context, success=True)

    assert result.success is True
    assert result.output_text != ""
    assert isinstance(result.stats, dict)
    assert "processed_rows" in result.stats
