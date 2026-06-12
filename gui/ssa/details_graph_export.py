from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, MutableMapping

from core.cache_manager import CacheManager


@dataclass(frozen=True, slots=True)
class SvgRenderDependencies:
    byte_array_cls: type[Any]
    painter_cls: type[Any]
    pixmap_cls: type[Any]
    rectf_cls: type[Any]
    renderer_cls: type[Any]
    qt_module: Any


_SVG_CACHE_MAX_ENTRIES = 8
_SVG_CACHE = CacheManager(max_entries=_SVG_CACHE_MAX_ENTRIES)


def load_svg_render_dependencies() -> SvgRenderDependencies | None:
    try:
        from PyQt6.QtCore import QByteArray, QRectF, Qt
        from PyQt6.QtGui import QPainter, QPixmap
        from PyQt6.QtSvg import QSvgRenderer
    except Exception:
        return None
    return SvgRenderDependencies(
        byte_array_cls=QByteArray,
        painter_cls=QPainter,
        pixmap_cls=QPixmap,
        rectf_cls=QRectF,
        renderer_cls=QSvgRenderer,
        qt_module=Qt,
    )


def render_graph_svg_pixmap(
    *,
    graph_svg: str,
    graph_label: Any,
    graph_panel: Any,
    dependencies: SvgRenderDependencies,
    max_scale: float = 1.4,
    resize_label: bool = True,
) -> bool:
    if not graph_svg:
        return False
    graph_cache_key = _svg_graph_cache_key(graph_svg)
    renderer = _cached_svg_renderer(dependencies.renderer_cls, graph_cache_key)
    if renderer is None:
        svg_payload = graph_svg.encode("utf-8")
        renderer = dependencies.renderer_cls(
            dependencies.byte_array_cls(svg_payload)
        )
        _store_svg_renderer(dependencies.renderer_cls, graph_cache_key, renderer)
    default_size = renderer.defaultSize()
    natural_w = max(1, int(default_size.width()))
    natural_h = max(1, int(default_size.height()))
    available_w = max(120, graph_panel.width() - 24)
    available_h = max(120, graph_panel.height() - 24)
    scale = min(max_scale, available_w / natural_w, available_h / natural_h)
    render_w = max(1, int(natural_w * scale))
    render_h = max(1, int(natural_h * scale))
    cached_pixmap = _cached_svg_pixmap(
        dependencies.pixmap_cls,
        graph_cache_key,
        render_w,
        render_h,
    )
    if cached_pixmap is not None:
        graph_label.setPixmap(cached_pixmap)
        _apply_rendered_graph_size(
            graph_label,
            render_w,
            render_h,
            resize_label=resize_label,
        )
        return True
    pixmap = dependencies.pixmap_cls(render_w, render_h)
    pixmap.fill(dependencies.qt_module.GlobalColor.transparent)
    painter = dependencies.painter_cls(pixmap)
    target_rect = dependencies.rectf_cls(0.0, 0.0, float(render_w), float(render_h))
    try:
        renderer.render(painter, target_rect)
    finally:
        painter.end()
    _store_svg_pixmap(
        dependencies.pixmap_cls,
        graph_cache_key,
        render_w,
        render_h,
        pixmap,
    )
    graph_label.setPixmap(pixmap)
    _apply_rendered_graph_size(
        graph_label,
        render_w,
        render_h,
        resize_label=resize_label,
    )
    return True


def _apply_rendered_graph_size(
    graph_label: Any, render_w: int, render_h: int, *, resize_label: bool
) -> None:
    if not resize_label:
        return
    set_minimum_size = getattr(graph_label, "setMinimumSize", None)
    if callable(set_minimum_size):
        set_minimum_size(render_w, render_h)
    resize = getattr(graph_label, "resize", None)
    if callable(resize):
        resize(render_w, render_h)


def _cached_svg_renderer(renderer_cls: type[Any], graph_cache_key: str) -> Any | None:
    cache_key = _svg_cache_key(renderer_cls, graph_cache_key)
    return _SVG_CACHE.get_cached_value("svg_renderers", cache_key)


def _store_svg_renderer(
    renderer_cls: type[Any], graph_cache_key: str, renderer: Any
) -> None:
    cache_key = _svg_cache_key(renderer_cls, graph_cache_key)
    _SVG_CACHE.cache_value(
        "svg_renderers",
        cache_key,
        renderer,
        max_entries=_SVG_CACHE_MAX_ENTRIES,
    )


def _cached_svg_pixmap(
    pixmap_cls: type[Any],
    graph_cache_key: str,
    width: int,
    height: int,
) -> Any | None:
    cache_key = _svg_cache_key(pixmap_cls, graph_cache_key, width, height)
    return _SVG_CACHE.get_cached_value("svg_pixmaps", cache_key)


def _store_svg_pixmap(
    pixmap_cls: type[Any],
    graph_cache_key: str,
    width: int,
    height: int,
    pixmap: Any,
) -> None:
    cache_key = _svg_cache_key(pixmap_cls, graph_cache_key, width, height)
    _SVG_CACHE.cache_value(
        "svg_pixmaps",
        cache_key,
        pixmap,
        max_entries=_SVG_CACHE_MAX_ENTRIES,
    )


def _svg_graph_cache_key(graph_svg: str) -> str:
    return hashlib.blake2b(
        graph_svg.encode("utf-8"),
        digest_size=16,
    ).hexdigest()


def _svg_cache_key(owner_cls: type[Any], graph_cache_key: str, *parts: int) -> str:
    owner = f"{owner_cls.__module__}.{owner_cls.__qualname__}"
    suffix = ":".join(str(part) for part in parts)
    return f"{owner}:{graph_cache_key}:{suffix}"


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
        export_path = Path(path).expanduser()
        if not export_path.parent.exists():
            self.message_box_cls.warning(
                self.dialog,
                "Exportacao",
                "Diretorio de destino inexistente.",
            )
            return
        try:
            with export_path.open("w", encoding="utf-8") as handle:
                handle.write(content)
        except OSError as exc:
            self.logger.warning("%s: %s", log_message, exc, exc_info=True)
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
            log_message="Falha ao exportar grafo SVG",
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
            log_message="Falha ao exportar Mermaid",
            warning_message="Falha ao salvar o arquivo Mermaid.",
        )

    def show_menu(self, global_pos: Any) -> None:
        menu = self.menu_cls(self.dialog)
        menu.addAction("Exportar PNG", self.export_png)
        menu.addAction("Exportar SVG", self.export_svg)
        menu.addAction("Exportar Mermaid", self.export_mermaid)
        menu.exec(global_pos)
