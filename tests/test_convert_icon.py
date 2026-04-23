from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from launchers import convert_icon
from struct import unpack


def test_app_icon_ico_contains_multiple_sizes() -> None:
    header = Path("resources/app_icon.ico").read_bytes()
    reserved, icon_type, count = unpack("<HHH", header[:6])
    assert reserved == 0
    assert icon_type == 1
    assert count >= 2

    entries = []
    offset = 6
    for _ in range(count):
        chunk = header[offset : offset + 16]
        width = chunk[0] or 256
        height = chunk[1] or 256
        entries.append((width, height))
        offset += 16

    assert entries == [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]


def test_convert_svg_to_ico_uses_sizes_on_single_base_image(monkeypatch):
    save_calls: list[dict] = []
    raster_calls: list[int] = []

    class _FakeImage:
        def __init__(self, width: int = 256, height: int = 256):
            self.width = width
            self.height = height
            self.resize_calls: list[tuple[int, int]] = []

        def resize(self, size: tuple[int, int], _resample) -> "_FakeImage":
            self.resize_calls.append(size)
            return _FakeImage(*size)

        def save(self, path, **kwargs):
            save_calls.append({"path": str(path), "kwargs": kwargs})

    def _fake_open(_data):
        return _FakeImage(256, 256)

    class _FakeCairosvg:
        @staticmethod
        def svg2png(url, output_width, output_height):
            raster_calls.append(output_width)
            return b"png-bytes"

    def _fake_import(module_name):
        if module_name == "cairosvg":
            return _FakeCairosvg
        if module_name == "PIL.Image":
            return SimpleNamespace(open=_fake_open, Resampling=SimpleNamespace(LANCZOS=0))
        return None

    monkeypatch.setattr(convert_icon, "cairosvg", _FakeCairosvg)
    monkeypatch.setattr(convert_icon, "_import_optional_module", _fake_import)

    convert_icon.convert_svg_to_ico("icon.svg", "/tmp/icon.ico", sizes=[16, 32, 64])

    assert save_calls, "save nao foi chamado"
    kwargs = save_calls[0]["kwargs"]
    assert kwargs["format"] == "ICO"
    assert kwargs["sizes"] == [(64, 64), (32, 32), (16, 16)]
    assert "append_images" in kwargs
    assert raster_calls == [64, 32, 16]
