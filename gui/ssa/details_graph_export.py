from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, MutableMapping


@dataclass(frozen=True, slots=True)
class SvgRenderDependencies:
    byte_array_cls: type[Any]
    painter_cls: type[Any]
    pixmap_cls: type[Any]
    renderer_cls: type[Any]
    qt_module: Any


_SVG_RENDERER_CACHE_MAX = 16
_SVG_RENDERER_CACHE: dict[tuple[type[Any], str], Any] = {}


def load_svg_render_dependencies() -> SvgRenderDependencies | None:
    try:
        from PyQt6.QtCore import QByteArray, Qt
        from PyQt6.QtGui import QPainter, QPixmap
        from PyQt6.QtSvg import QSvgRenderer
    except Exception:
        return None
    return SvgRenderDependencies(
        byte_array_cls=QByteArray,
        painter_cls=QPainter,
        pixmap_cls=QPixmap,
        renderer_cls=QSvgRenderer,
        qt_module=Qt,
    )


def render_graph_svg_pixmap(
    *,
    graph_svg: str,
    graph_label: Any,
    graph_panel: Any,
    dependencies: SvgRenderDependencies,
) -> bool:
    if not graph_svg:
        return False
    renderer = _cached_svg_renderer(dependencies.renderer_cls, graph_svg)
    if renderer is None:
        svg_payload = graph_svg.encode("utf-8")
        renderer = dependencies.renderer_cls(
            dependencies.byte_array_cls(svg_payload)
        )
        _store_svg_renderer(dependencies.renderer_cls, graph_svg, renderer)
    default_size = renderer.defaultSize()
    natural_w = max(1, int(default_size.width()))
    natural_h = max(1, int(default_size.height()))
    available_w = max(120, graph_panel.width() - 24)
    available_h = max(120, graph_panel.height() - 24)
    scale = min(1.0, available_w / natural_w, available_h / natural_h)
    render_w = max(1, int(natural_w * scale))
    render_h = max(1, int(natural_h * scale))
    dpr = 1.0
    device_pixel_ratio = getattr(graph_panel, "devicePixelRatioF", None)
    if callable(device_pixel_ratio):
        dpr = max(1.0, float(device_pixel_ratio()))
    pixmap = dependencies.pixmap_cls(
        max(1, int(render_w * dpr)), max(1, int(render_h * dpr))
    )
    set_dpr = getattr(pixmap, "setDevicePixelRatio", None)
    if callable(set_dpr):
        set_dpr(dpr)
    pixmap.fill(dependencies.qt_module.GlobalColor.transparent)
    painter = dependencies.painter_cls(pixmap)
    renderer.render(painter)
    painter.end()
    graph_label.setPixmap(pixmap)
    graph_label.setFixedSize(render_w, render_h)
    graph_label.setToolTip("")
    return True


def _cached_svg_renderer(renderer_cls: type[Any], graph_svg: str) -> Any | None:
    return _SVG_RENDERER_CACHE.get((renderer_cls, graph_svg))


def _store_svg_renderer(
    renderer_cls: type[Any], graph_svg: str, renderer: Any
) -> None:
    _SVG_RENDERER_CACHE[(renderer_cls, graph_svg)] = renderer
    while len(_SVG_RENDERER_CACHE) > _SVG_RENDERER_CACHE_MAX:
        first_key = next(iter(_SVG_RENDERER_CACHE), None)
        if first_key is None:
            return
        _SVG_RENDERER_CACHE.pop(first_key, None)


@dataclass(slots=True)
class DetailsGraphExportController:
    dialog: Any
    graph_widget: Any
    export_state: MutableMapping[str, object]
    file_dialog_cls: type[Any]
    message_box_cls: type[Any]
    menu_cls: type[Any]
    logger: Any

    def target_basename(self) -> str:
        safe_target = str(self.export_state.get("target") or "").strip()
        return f"derivadas_{safe_target or 'desconhecida'}"

    def _choose_save_path(self, title: str, default_name: str, file_filter: str) -> str:
        path, _ = self.file_dialog_cls.getSaveFileName(
            self.dialog,
            title,
            default_name,
            file_filter,
        )
        return str(path or "")

    def _write_text_export(
        self, *, path: str, content: str, log_message: str, warning_message: str
    ) -> None:
        parent_dir = Path(path).expanduser().parent
        if not parent_dir.exists():
            self.message_box_cls.warning(
                self.dialog,
                "Exportacao",
                "Diretorio de destino inexistente.",
            )
            return
        try:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(content)
        except OSError as exc:
            self.logger.warning(log_message, exc)
            self.message_box_cls.warning(
                self.dialog,
                "Exportacao",
                warning_message,
            )

    def export_png(self) -> None:
        default_name = f"{self.target_basename()}.png"
        path = self._choose_save_path(
            "Exportar grafo em PNG", default_name, "PNG (*.png)"
        )
        if not path:
            return
        pixmap = self.graph_widget.grab()
        if pixmap.isNull():
            self.message_box_cls.warning(
                self.dialog,
                "Exportacao",
                "Grafo indisponivel para exportacao em PNG.",
            )
            return
        if not pixmap.save(path, "PNG"):
            self.message_box_cls.warning(
                self.dialog,
                "Exportacao",
                "Falha ao salvar o arquivo PNG.",
            )

    def export_svg(self) -> None:
        graph_svg = str(self.export_state.get("svg") or "")
        if not graph_svg:
            self.message_box_cls.warning(
                self.dialog,
                "Exportacao",
                "Grafo indisponivel para exportacao em SVG.",
            )
            return
        default_name = f"{self.target_basename()}.svg"
        path = self._choose_save_path(
            "Exportar grafo em SVG", default_name, "SVG (*.svg)"
        )
        if not path:
            return
        self._write_text_export(
            path=path,
            content=graph_svg,
            log_message="Falha ao exportar grafo SVG: %s",
            warning_message="Falha ao salvar o arquivo SVG.",
        )

    def export_mermaid(self) -> None:
        mermaid_text = str(self.export_state.get("mermaid") or "")
        if not mermaid_text:
            self.message_box_cls.warning(
                self.dialog,
                "Exportacao",
                "Mermaid indisponivel para exportacao.",
            )
            return
        default_name = f"{self.target_basename()}.mmd"
        path = self._choose_save_path(
            "Exportar Mermaid", default_name, "Mermaid (*.mmd);;Texto (*.txt)"
        )
        if not path:
            return
        self._write_text_export(
            path=path,
            content=mermaid_text,
            log_message="Falha ao exportar Mermaid: %s",
            warning_message="Falha ao salvar o arquivo Mermaid.",
        )

    def show_menu(self, global_pos: Any) -> None:
        menu = self.menu_cls(self.dialog)
        menu.addAction("Exportar PNG", self.export_png)
        menu.addAction("Exportar SVG", self.export_svg)
        menu.addAction("Exportar Mermaid", self.export_mermaid)
        menu.exec(global_pos)
