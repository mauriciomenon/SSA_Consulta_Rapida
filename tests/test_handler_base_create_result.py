from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pandas as pd
import pytest

from core.handler_base import (
    ExportHandlerBase,
    FilterHandlerBase,
    HandlerBase,
    HandlerContext,
)


class _DummyHandler(HandlerBase):
    def __init__(self) -> None:
        super().__init__(name="dummy")

    def execute(self, context: HandlerContext):
        return self.create_result(data=None, context=context)


class _FailingFilterHandler(FilterHandlerBase):
    def __init__(self) -> None:
        super().__init__(name="failing")

    def apply_filters(self, data: pd.DataFrame, context: HandlerContext) -> pd.DataFrame:
        return data

    def _load_base_data(self, context: HandlerContext) -> pd.DataFrame:
        raise RuntimeError("load failed")


class _InvalidLoadFilterHandler(FilterHandlerBase):
    def __init__(self) -> None:
        super().__init__(name="invalid_load")

    def apply_filters(self, data: pd.DataFrame, context: HandlerContext) -> pd.DataFrame:
        return data

    def _load_base_data(self, context: HandlerContext) -> pd.DataFrame:
        return cast(Any, None)


class _InvalidApplyFilterHandler(FilterHandlerBase):
    def __init__(self) -> None:
        super().__init__(name="invalid_apply")

    def apply_filters(self, data: pd.DataFrame, context: HandlerContext) -> pd.DataFrame:
        return cast(Any, ["not", "a", "dataframe"])

    def _load_base_data(self, context: HandlerContext) -> pd.DataFrame:
        return pd.DataFrame({"numero_ssa": ["202600001"]})


class _RecordingExportHandler(ExportHandlerBase):
    def __init__(self) -> None:
        super().__init__(name="export")
        self.output_path: Path | None = None

    def export_data(
        self, data: pd.DataFrame, output_path: Path, context: HandlerContext
    ) -> bool:
        self.output_path = output_path
        return True

    def _load_export_data(self, context: HandlerContext) -> pd.DataFrame:
        return pd.DataFrame({"numero_ssa": ["202600001"]})


class _FailingExportHandler(ExportHandlerBase):
    def __init__(self) -> None:
        super().__init__(name="export_fail")

    def export_data(
        self, data: pd.DataFrame, output_path: Path, context: HandlerContext
    ) -> bool:
        raise RuntimeError("export failed")

    def _load_export_data(self, context: HandlerContext) -> pd.DataFrame:
        return pd.DataFrame({"numero_ssa": ["202600001"]})


class _InvalidExportDataHandler(ExportHandlerBase):
    def __init__(self) -> None:
        super().__init__(name="invalid_export")

    def export_data(
        self, data: pd.DataFrame, output_path: Path, context: HandlerContext
    ) -> bool:
        return True

    def _load_export_data(self, context: HandlerContext) -> pd.DataFrame:
        return cast(Any, None)


def test_create_result_keeps_stats_for_non_dataframe_data() -> None:
    handler = _DummyHandler()
    context = HandlerContext(output_format="table")

    result = handler.create_result(
        data=cast(Any, "legacy-non-dataframe"),
        context=context,
        success=True,
    )

    assert result.success is True
    assert result.output_text == ""
    assert result.stats["processed_rows"] == 0


def test_create_result_formats_empty_dataframe_feedback() -> None:
    handler = _DummyHandler()
    context = HandlerContext(output_format="table")

    result = handler.create_result(
        data=pd.DataFrame(),
        context=context,
        success=True,
    )

    assert result.success is True
    assert result.output_text == "Nenhum resultado encontrado."
    assert result.stats["processed_rows"] == 0


def test_create_result_keeps_empty_json_machine_readable() -> None:
    handler = _DummyHandler()
    context = HandlerContext(output_format="json")

    result = handler.create_result(
        data=pd.DataFrame(columns=["numero_ssa"]),
        context=context,
        success=True,
    )

    assert result.success is True
    assert result.output_text == "[]"


def test_create_result_keeps_empty_csv_machine_readable() -> None:
    handler = _DummyHandler()
    context = HandlerContext(output_format="csv")

    result = handler.create_result(
        data=pd.DataFrame(columns=["numero_ssa"]),
        context=context,
        success=True,
    )

    assert result.success is True
    assert result.output_text == "numero_ssa\n"


def test_create_result_keeps_dataframe_behavior() -> None:
    handler = _DummyHandler()
    context = HandlerContext(output_format="table")
    frame = pd.DataFrame({"numero_ssa": ["202600654"]})

    result = handler.create_result(data=frame, context=context, success=True)

    assert result.success is True
    assert result.output_text != ""
    assert isinstance(result.stats, dict)
    assert "processed_rows" in result.stats


def test_filter_handler_logs_exception_context(caplog: pytest.LogCaptureFixture) -> None:
    handler = _FailingFilterHandler()
    context = HandlerContext(output_format="table")

    with caplog.at_level("ERROR", logger="core.handler_base"):
        result = handler.execute(context)

    assert result.success is False
    assert context.error_count == 1
    assert "Filter handler 'failing' failed" in caplog.text


def test_filter_handler_rejects_invalid_loaded_data(
    caplog: pytest.LogCaptureFixture,
) -> None:
    handler = _InvalidLoadFilterHandler()
    context = HandlerContext(output_format="table")

    with caplog.at_level("ERROR", logger="core.handler_base"):
        result = handler.execute(context)

    assert result.success is False
    assert context.error_count == 1
    assert "invalid_load._load_base_data deve retornar pandas.DataFrame" in result.message
    assert "Filter handler 'invalid_load' failed" in caplog.text


def test_filter_handler_rejects_invalid_filtered_data(
    caplog: pytest.LogCaptureFixture,
) -> None:
    handler = _InvalidApplyFilterHandler()
    context = HandlerContext(output_format="table")

    with caplog.at_level("ERROR", logger="core.handler_base"):
        result = handler.execute(context)

    assert result.success is False
    assert context.error_count == 1
    assert "invalid_apply.apply_filters deve retornar pandas.DataFrame" in result.message
    assert "Filter handler 'invalid_apply' failed" in caplog.text


def test_export_handler_validates_output_path(tmp_path: Path) -> None:
    handler = _RecordingExportHandler()
    context = HandlerContext(output_path=str(tmp_path / "out.csv"))

    result = handler.execute(context)

    assert result.success is True
    assert isinstance(result.data, pd.DataFrame)
    assert result.stats["processed_rows"] == 1
    assert handler.output_path == tmp_path / "out.csv"


def test_export_handler_rejects_invalid_loaded_data(
    caplog: pytest.LogCaptureFixture,
) -> None:
    handler = _InvalidExportDataHandler()
    context = HandlerContext(output_path="out.csv")

    with caplog.at_level("ERROR", logger="core.handler_base"):
        result = handler.execute(context)

    assert result.success is False
    assert context.error_count == 1
    assert "invalid_export._load_export_data deve retornar pandas.DataFrame" in result.message
    assert "Export handler 'invalid_export' failed" in caplog.text


def test_export_handler_failure_increments_context_stats(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    handler = _FailingExportHandler()
    context = HandlerContext(output_path=str(tmp_path / "out.csv"))

    with caplog.at_level("ERROR", logger="core.handler_base"):
        result = handler.execute(context)

    assert result.success is False
    assert context.error_count == 1
    assert result.stats["error_count"] == 1
    assert "Export handler 'export_fail' failed" in caplog.text
