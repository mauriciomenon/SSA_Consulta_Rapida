from __future__ import annotations

from pathlib import Path

import pytest

from gui.ssa import gui_details
from gui.ssa.details_graph_export import (
    DetailsGraphExportController,
    SvgRenderDependencies,
    render_graph_svg_pixmap,
)


class _FakeFileDialog:
    next_path = ""
    calls: list[tuple[object, str, str, str]] = []

    @classmethod
    def getSaveFileName(cls, dialog, title, default_name, file_filter):
        cls.calls.append((dialog, title, default_name, file_filter))
        return cls.next_path, ""


class _FakeMessageBox:
    warnings: list[tuple[object, str, str]] = []

    @classmethod
    def warning(cls, dialog, title, message):
        cls.warnings.append((dialog, title, message))


class _FakeMenu:
    created = []

    def __init__(self, dialog):
        self.dialog = dialog
        self.actions = []
        self.exec_pos = None
        self.__class__.created.append(self)

    def addAction(self, text, callback):
        self.actions.append((text, callback))

    def exec(self, global_pos):
        self.exec_pos = global_pos


class _FakeLogger:
    warnings: list[tuple[str, object, object]] = []

    def warning(self, message, exc, *, exc_info=None):
        self.warnings.append((message, exc, exc_info))


class _FakePixmap:
    def __init__(self, is_null=False):
        self._is_null = is_null
        self.saved: list[tuple[str, str]] = []

    def isNull(self):
        return self._is_null

    def save(self, path, fmt):
        self.saved.append((path, fmt))
        return True


class _FakeGraphWidget:
    def __init__(self, pixmap):
        self.pixmap = pixmap

    def grab(self):
        return self.pixmap


class _FakeSize:
    def __init__(self, width: int, height: int) -> None:
        self._width = width
        self._height = height

    def width(self):
        return self._width

    def height(self):
        return self._height


class _FakeRenderer:
    instances = 0
    last_rect = None
    render_calls = 0

    def __init__(self, _payload) -> None:
        self.__class__.instances += 1

    def defaultSize(self):
        return _FakeSize(300, 120)

    def render(self, _painter, rect) -> None:
        self.__class__.render_calls += 1
        self.__class__.last_rect = rect
        return


class _FakeRectF:
    def __init__(self, x: float, y: float, width: float, height: float) -> None:
        self.x = x
        self.y = y
        self.width = width
        self.height = height


class _FakeByteArray:
    def __init__(self, payload) -> None:
        self.payload = payload


class _FakeSvgPixmap:
    def __init__(self, width: int = 0, height: int = 0) -> None:
        self.width = width
        self.height = height
        self.dpr = 1.0

    def setDevicePixelRatio(self, dpr: float) -> None:
        self.dpr = dpr

    def fill(self, _color) -> None:
        return

    def size(self):
        return _FakeSize(self.width, self.height)


class _FakePainter:
    end_calls = 0

    def __init__(self, _pixmap) -> None:
        return

    def end(self) -> None:
        self.__class__.end_calls += 1
        return


class _FailingRenderer(_FakeRenderer):
    def render(self, _painter, rect) -> None:
        self.__class__.render_calls += 1
        self.__class__.last_rect = rect
        raise RuntimeError("render failed")


class _FakeQtModule:
    class GlobalColor:
        transparent = "transparent"


class _FakeGraphLabel:
    def __init__(self) -> None:
        self.pixmap = None
        self.fixed_size = None
        self.tooltip = None

    def setPixmap(self, pixmap) -> None:
        self.pixmap = pixmap

    def setFixedSize(self, width, height=None) -> None:
        if height is None:
            self.fixed_size = (width.width(), width.height())
        else:
            self.fixed_size = (width, height)

    def setToolTip(self, text: str) -> None:
        self.tooltip = text


class _FakeGraphPanel:
    def width(self):
        return 400

    def height(self):
        return 200

    def devicePixelRatioF(self):
        return 2.0


def _controller(tmp_path: Path, *, state: dict[str, object]):
    _FakeFileDialog.next_path = str(tmp_path / "out.svg")
    _FakeFileDialog.calls = []
    _FakeMessageBox.warnings = []
    _FakeMenu.created = []
    _FakeLogger.warnings = []
    pixmap = _FakePixmap()
    return DetailsGraphExportController(
        dialog=object(),
        graph_widget=_FakeGraphWidget(pixmap),
        export_state=state,
        file_dialog_cls=_FakeFileDialog,
        message_box_cls=_FakeMessageBox,
        menu_cls=_FakeMenu,
        logger=_FakeLogger(),
    )


def test_extract_inline_svg_markup_reads_svg_inside_full_html() -> None:
    html = "<html><body><p>before</p><svg><text>ok</text></svg></body></html>"

    assert gui_details._extract_inline_svg_markup(html) == "<svg><text>ok</text></svg>"


def test_render_graph_svg_pixmap_uses_logical_label_size() -> None:
    label = _FakeGraphLabel()
    _FakeRenderer.instances = 0
    _FakeRenderer.render_calls = 0
    deps = SvgRenderDependencies(
        byte_array_cls=_FakeByteArray,
        painter_cls=_FakePainter,
        pixmap_cls=_FakeSvgPixmap,
        rectf_cls=_FakeRectF,
        renderer_cls=_FakeRenderer,
        qt_module=_FakeQtModule,
    )

    ok = render_graph_svg_pixmap(
        graph_svg="<svg></svg>",
        graph_label=label,
        graph_panel=_FakeGraphPanel(),
        dependencies=deps,
    )
    second_ok = render_graph_svg_pixmap(
        graph_svg="<svg></svg>",
        graph_label=label,
        graph_panel=_FakeGraphPanel(),
        dependencies=deps,
    )

    assert ok is True
    assert second_ok is True
    assert label.pixmap is not None
    assert label.pixmap.width == 376
    assert label.pixmap.height == 150
    assert label.fixed_size == (376, 150)
    assert label.tooltip == ""
    assert _FakeRenderer.last_rect is not None
    assert _FakeRenderer.last_rect.width == 376.0
    assert _FakeRenderer.last_rect.height == 150.0
    assert _FakeRenderer.instances == 1
    assert _FakeRenderer.render_calls == 1


def test_render_graph_svg_pixmap_ends_painter_when_render_fails() -> None:
    label = _FakeGraphLabel()
    _FailingRenderer.instances = 0
    _FailingRenderer.render_calls = 0
    _FakePainter.end_calls = 0
    deps = SvgRenderDependencies(
        byte_array_cls=_FakeByteArray,
        painter_cls=_FakePainter,
        pixmap_cls=_FakeSvgPixmap,
        rectf_cls=_FakeRectF,
        renderer_cls=_FailingRenderer,
        qt_module=_FakeQtModule,
    )

    with pytest.raises(RuntimeError, match="render failed"):
        render_graph_svg_pixmap(
            graph_svg="<svg><text>fail</text></svg>",
            graph_label=label,
            graph_panel=_FakeGraphPanel(),
            dependencies=deps,
        )

    assert _FakePainter.end_calls == 1
    assert _FailingRenderer.render_calls == 1
    assert label.pixmap is None


def test_graph_export_controller_uses_stable_target_basename(tmp_path: Path) -> None:
    controller = _controller(tmp_path, state={"target": "202600001"})

    assert controller.target_basename() == "derivadas_202600001"


def test_graph_export_controller_warns_when_svg_missing(tmp_path: Path) -> None:
    controller = _controller(tmp_path, state={"target": "202600001", "svg": ""})

    controller.export_svg()

    assert _FakeMessageBox.warnings == [
        (
            controller.dialog,
            "Exportacao",
            "Grafo indisponivel para exportacao em SVG.",
        )
    ]
    assert _FakeFileDialog.calls == []


def test_graph_export_controller_menu_registers_expected_actions(tmp_path: Path) -> None:
    controller = _controller(tmp_path, state={"target": "202600001"})

    controller.show_menu("point")

    menu = _FakeMenu.created[-1]
    assert [text for text, _callback in menu.actions] == [
        "Exportar PNG",
        "Exportar SVG",
        "Exportar Mermaid",
    ]
    assert menu.exec_pos == "point"


def test_graph_export_controller_warns_when_parent_dir_is_missing(
    tmp_path: Path,
) -> None:
    missing_path = tmp_path / "missing" / "graph.svg"
    controller = _controller(
        tmp_path,
        state={"target": "202600001", "svg": "<svg></svg>"},
    )
    _FakeFileDialog.next_path = str(missing_path)

    controller.export_svg()

    assert _FakeMessageBox.warnings == [
        (
            controller.dialog,
            "Exportacao",
            "Diretorio de destino inexistente.",
        )
    ]
    assert not missing_path.exists()
