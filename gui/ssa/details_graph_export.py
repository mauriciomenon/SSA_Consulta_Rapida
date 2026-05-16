from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Any, MutableMapping


@dataclass(frozen=True, slots=True)
class SvgRenderDependencies:
    byte_array_cls: type[Any]
    painter_cls: type[Any]
    pixmap_cls: type[Any]
    renderer_cls: type[Any]
    qt_module: Any


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
    renderer = None
    svg_payload = graph_svg.encode("utf-8")
    cached_svg = getattr(graph_label, "_ssa_graph_svg_text", None)
    cached_key = getattr(graph_label, "_ssa_graph_svg_cache_key", None)
    cached_renderer = getattr(graph_label, "_ssa_graph_svg_renderer", None)
    if cached_svg is graph_svg and cached_renderer is not None:
        renderer = cached_renderer
        cache_key = cached_key
    else:
        cache_key = hashlib.blake2b(svg_payload, digest_size=12).hexdigest()
        if cached_key == cache_key and cached_renderer is not None:
            renderer = cached_renderer
            graph_label._ssa_graph_svg_text = graph_svg
    if renderer is None:
        renderer = dependencies.renderer_cls(
            dependencies.byte_array_cls(svg_payload)
        )
        graph_label._ssa_graph_svg_text = graph_svg
        graph_label._ssa_graph_svg_cache_key = cache_key
        graph_label._ssa_graph_svg_renderer = renderer
    default_size = renderer.defaultSize()
    natural_w = max(1, int(default_size.width()))
    natural_h = max(1, int(default_size.height()))
    available_w = max(120, graph_panel.width() - 24)
    available_h = max(120, graph_panel.height() - 24)
    scale = min(1.35, available_w / natural_w, available_h / natural_h)
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
