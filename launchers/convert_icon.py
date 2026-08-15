#!/usr/bin/env python3
"""
Script para converter SVG para ICO, ICNS e PNG
Usado no build dos executaveis multi-plataforma
"""

import importlib
import io
import os
import subprocess  # nosec B404
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

_robust_logging = importlib.import_module("utils.robust_logging")
logger = _robust_logging.get_robust_logger().get_logger(__name__, "maintenance")
_OPTIONAL_MODULE_ALLOWLIST = frozenset({"cairosvg", "PIL.Image"})


def _get_project_root() -> Path:
    return PROJECT_ROOT


def _import_optional_module(module_name: str) -> Any | None:
    if module_name not in _OPTIONAL_MODULE_ALLOWLIST:
        raise ValueError(f"Unsupported optional module: {module_name!r}")
    if module_name == "cairosvg" and sys.platform == "darwin":
        library_search_paths = ["/opt/homebrew/lib", "/usr/local/lib", "/usr/lib"]
        candidates = [
            p for p in library_search_paths if os.path.isdir(p) and "libcairo.2.dylib" in os.listdir(p)
        ]
        if candidates:
            for var in ("DYLD_LIBRARY_PATH", "DYLD_FALLBACK_LIBRARY_PATH"):
                current = [path for path in os.environ.get(var, "").split(":") if path]
                merged = current + [path for path in candidates if path not in current]
                os.environ[var] = ":".join(merged)
    try:
        return importlib.import_module(module_name)
    except OSError:
        return None
    except ImportError:
        return None


def _require_pillow_image() -> Any:
    image_module = _import_optional_module("PIL.Image")
    if image_module is None:
        raise ImportError("Pillow nao encontrado")
    return image_module


cairosvg = _import_optional_module("cairosvg")
RSVG_CONVERT = shutil.which("rsvg-convert")


def _run_command(command: list[str]) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(  # nosec B603
        command,
        check=False,
        capture_output=True,
        text=False,
    )


def _render_svg_to_png(svg_path: str, size: int) -> bytes:
    if cairosvg is not None:
        try:
            return cairosvg.svg2png(url=svg_path, output_width=size, output_height=size)
        except OSError:
            logger.warning(
                "Falha no cairosvg para svg %s e tamanho %s; tentando rsvg-convert",
                svg_path,
                size,
            )

    if RSVG_CONVERT is None:
        raise ImportError("cairosvg falhou e rsvg-convert nao foi encontrado")

    result = _run_command(
        [
            RSVG_CONVERT,
            "--format=png",
            f"--width={size}",
            f"--height={size}",
            svg_path,
        ]
    )
    if result.returncode != 0:
        stderr = result.stderr.decode() if result.stderr else ""
        raise RuntimeError(f"Falha no rsvg-convert: {stderr}")
    if not result.stdout:
        raise RuntimeError("Falha no rsvg-convert: sem dados de saida")
    return result.stdout


def convert_svg_to_ico(
    svg_path, ico_path, sizes=None
):  # noqa: ANN001,ANN201
    """Converte SVG para ICO com multiplos tamanhos (Windows)"""
    svg_path = str(svg_path)
    ico_path = str(ico_path)

    if sizes is None:
        sizes = [16, 32, 48, 64, 128, 256]

    image_module = _require_pillow_image()

    # Converter SVG para cada resolucao para manter nitidez em todos os tamanhos.
    target_sizes = sorted(set(sizes), reverse=True)
    if not target_sizes:
        raise ValueError("sizes must not be empty")
    images = []
    for size in target_sizes:
        png_data = _render_svg_to_png(svg_path, size)
        images.append(image_module.open(io.BytesIO(png_data)))

    try:
        images[0].save(
            ico_path,
            format="ICO",
            sizes=[(size, size) for size in target_sizes],
            append_images=images[1:],
        )
    finally:
        for image in images:
            close = getattr(image, "close", None)
            if callable(close):
                close()

    logger.info("Icone ICO convertido: %s", ico_path)


def convert_svg_to_icns(svg_path, icns_path, sizes=None):  # noqa: ANN001,ANN201
    """Converte SVG para ICNS (macOS)"""
    icns_file_path = Path(icns_path)
    svg_path = str(svg_path)

    image_module = _require_pillow_image()

    if sizes is None:
        sizes = [16, 32, 64, 128, 256, 512, 1024]
    target_sizes = set(sizes)
    if not target_sizes:
        raise ValueError("sizes must not be empty")

    # No macOS, usar iconutil se disponivel
    try:
        # Criar diretorio temporario para iconset
        with tempfile.TemporaryDirectory() as temp_dir:
            iconset_dir = Path(temp_dir) / "icon.iconset"
            iconset_dir.mkdir(parents=True)

            # Gerar imagens em tamanhos padrao macOS
            iconset_sizes = [
                (16, "icon_16x16.png"),
                (32, "icon_16x16@2x.png"),
                (32, "icon_32x32.png"),
                (64, "icon_32x32@2x.png"),
                (128, "icon_128x128.png"),
                (256, "icon_128x128@2x.png"),
                (256, "icon_256x256.png"),
                (512, "icon_256x256@2x.png"),
                (512, "icon_512x512.png"),
                (1024, "icon_512x512@2x.png"),
            ]
            iconset_sizes = [
                (size, filename)
                for size, filename in iconset_sizes
                if size in target_sizes
            ]
            if not iconset_sizes:
                raise ValueError("sizes must include at least one macOS icon size")

            for size, filename in iconset_sizes:
                png_data = _render_svg_to_png(svg_path, size)
                img = image_module.open(io.BytesIO(png_data))
                try:
                    img.save(str(iconset_dir / filename), format="PNG")
                finally:
                    close = getattr(img, "close", None)
                    if callable(close):
                        close()

            # Usar iconutil para gerar ICNS
            iconutil = shutil.which("iconutil")
            if iconutil is None:
                raise RuntimeError("iconutil nao encontrado")
            result = _run_command(
                [
                    iconutil,
                    "-c",
                    "icns",
                    str(iconset_dir),
                    "-o",
                    str(icns_file_path),
                ],
            )

            if result.returncode == 0:
                logger.info("Icone ICNS convertido: %s", icns_file_path)
                return True
            stderr = result.stderr.decode("utf-8", "replace") if result.stderr else ""
            logger.error("Erro com iconutil: %s", stderr)
            return False

    except Exception as e:
        logger.error("Falha ao converter ICNS: %s", e)
        return False


def convert_svg_to_png(svg_path, png_path, size=256):
    """Converte SVG para PNG (Linux)"""
    svg_path = str(svg_path)
    png_path = str(png_path)

    # Converter SVG para PNG
    png_data = _render_svg_to_png(svg_path, size)

    with open(png_path, "wb") as f:
        f.write(png_data)

    logger.info("Icone PNG convertido: %s", png_path)


def convert_all_icons():
    """Converte icone SVG para todos os formatos necessarios"""
    resources_dir = _get_project_root() / "resources"
    svg_file = resources_dir / "app_icon.svg"

    if not svg_file.exists():
        logger.error("SVG nao encontrado: %s", svg_file)
        return False

    # Garantir que diretorio resources existe
    resources_dir.mkdir(exist_ok=True)

    success = True

    try:
        # Windows ICO
        ico_file = resources_dir / "app_icon.ico"
        convert_svg_to_ico(svg_file, ico_file)
    except Exception as e:
        logger.error("Erro convertendo ICO: %s", e)
        success = False

    try:
        # macOS ICNS
        if sys.platform == "darwin":
            icns_file = resources_dir / "app_icon.icns"
            if not convert_svg_to_icns(svg_file, icns_file):
                success = False
        else:
            logger.info("Pulando conversao ICNS fora do macOS")
    except Exception as e:
        logger.error("Erro convertendo ICNS: %s", e)
        success = False

    try:
        # Linux PNG
        png_file = resources_dir / "app_icon.png"
        convert_svg_to_png(svg_file, png_file)
    except Exception as e:
        logger.error("Erro convertendo PNG: %s", e)
        success = False

    return success


def main() -> int:
    success = convert_all_icons()
    if not success:
        logger.error("ERRO: Nem todos os icones foram convertidos")
        if cairosvg is None:
            logger.error("Instale cairosvg: pip install cairosvg")
        return 1
    logger.info("Todos os icones convertidos com sucesso")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
