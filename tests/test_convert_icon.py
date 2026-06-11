from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

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
            _ = output_height
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

    convert_icon.convert_svg_to_ico("icon.svg", "icon.ico", sizes=[16, 32, 64])

    assert save_calls, "save nao foi chamado"
    kwargs = save_calls[0]["kwargs"]
    assert kwargs["format"] == "ICO"
    assert kwargs["sizes"] == [(64, 64), (32, 32), (16, 16)]
    assert "append_images" in kwargs
    assert raster_calls == [64, 32, 16]


def test_app_icon_ico_contains_expected_sizes_via_pillow() -> None:
    Image = pytest.importorskip("PIL.Image", reason="Pillow optional in base env")

    with Image.open("resources/app_icon.ico") as image:
        ico_sizes = image.info.get("sizes", set())
        assert len(ico_sizes) == 6
        assert { (16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)} <= set(ico_sizes)


def test_convert_svg_to_ico_uses_rsvg_when_cairosvg_unavailable(monkeypatch):
    save_calls: list[dict] = []
    command_calls: list[list[str]] = []

    class _FakeImage:
        def __init__(self, width: int = 1024, height: int = 1024):
            self.width = width
            self.height = height

        def save(self, path, **kwargs):
            save_calls.append({"path": str(path), "kwargs": kwargs})

    class _FakeCommandResult:
        returncode = 0
        stdout = b"png-bytes"
        stderr = b""

    def _fake_open(_data):
        return _FakeImage(1024, 1024)

    def _fake_import(module_name):
        if module_name == "PIL.Image":
            return SimpleNamespace(open=_fake_open, Resampling=SimpleNamespace(LANCZOS=0))
        return None

    def _fake_run_command(command):
        command_calls.append(command)
        return _FakeCommandResult()

    monkeypatch.setattr(convert_icon, "cairosvg", None)
    monkeypatch.setattr(convert_icon, "_import_optional_module", _fake_import)
    monkeypatch.setattr(convert_icon, "_run_command", _fake_run_command)
    monkeypatch.setattr(convert_icon, "RSVG_CONVERT", "rsvg-convert")

    convert_icon.convert_svg_to_ico("icon.svg", "icon.ico", sizes=[16])

    assert command_calls, "rsvg-convert nao foi chamado"
    assert command_calls[0][0] == "rsvg-convert"
    assert command_calls[0][1:4] == [
        "--format=png",
        "--width=16",
        "--height=16",
    ]
    assert save_calls


def test_import_optional_module_rejects_unexpected_module() -> None:
    with pytest.raises(ValueError, match="Unsupported optional module"):
        convert_icon._import_optional_module("os")


def test_convert_svg_to_ico_rejects_empty_sizes(monkeypatch) -> None:
    monkeypatch.setattr(convert_icon, "_require_pillow_image", lambda: object())

    with pytest.raises(ValueError, match="sizes must not be empty"):
        convert_icon.convert_svg_to_ico("icon.svg", "icon.ico", sizes=[])


def test_convert_svg_to_icns_uses_requested_sizes_and_closes_images(
    monkeypatch,
    tmp_path,
) -> None:
    rendered_sizes: list[int] = []
    saved_names: list[str] = []
    closed_count = 0
    command_calls: list[list[str]] = []

    class _FakeImage:
        def save(self, path, **_kwargs):
            saved_names.append(Path(path).name)

        def close(self):
            nonlocal closed_count
            closed_count += 1

    fake_image_module = SimpleNamespace(open=lambda _data: _FakeImage())

    def _fake_render(_svg_path, size):
        rendered_sizes.append(size)
        return b"png-bytes"

    def _fake_run_command(command):
        command_calls.append(command)
        return SimpleNamespace(returncode=0, stderr=b"")

    monkeypatch.setattr(convert_icon, "_require_pillow_image", lambda: fake_image_module)
    monkeypatch.setattr(convert_icon, "_render_svg_to_png", _fake_render)
    monkeypatch.setattr(convert_icon.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(convert_icon, "_run_command", _fake_run_command)

    result = convert_icon.convert_svg_to_icns(
        "icon.svg",
        tmp_path / "icon.icns",
        sizes=[16, 32],
    )

    assert result is True
    assert rendered_sizes == [16, 32, 32]
    assert saved_names == ["icon_16x16.png", "icon_16x16@2x.png", "icon_32x32.png"]
    assert closed_count == 3
    assert command_calls[0][0] == "/usr/bin/iconutil"


def test_convert_icon_main_returns_failure_status(monkeypatch) -> None:
    monkeypatch.setattr(convert_icon, "convert_all_icons", lambda: False)
    monkeypatch.setattr(convert_icon, "cairosvg", object())

    assert convert_icon.main() == 1


def test_convert_icon_main_returns_success_status(monkeypatch) -> None:
    monkeypatch.setattr(convert_icon, "convert_all_icons", lambda: True)

    assert convert_icon.main() == 0
