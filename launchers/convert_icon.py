#!/usr/bin/env python3
"""
Script para converter SVG para ICO, ICNS e PNG
Usado no build dos executaveis multi-plataforma
"""

import importlib
import io
import os
import subprocess
import shutil
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

_robust_logging = importlib.import_module("utils.robust_logging")
logger = _robust_logging.get_robust_logger().get_logger(__name__, "maintenance")


def _get_project_root() -> Path:
    return PROJECT_ROOT


def _import_optional_module(module_name: str) -> Any | None:
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
    return subprocess.run(
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
        raise ImportError("cairosvg nao encontrado")

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
    images = []
    for size in target_sizes:
        png_data = _render_svg_to_png(svg_path, size)
        images.append(image_module.open(io.BytesIO(png_data)))

    images[0].save(
        ico_path,
        format="ICO",
        sizes=[(size, size) for size in target_sizes],
        append_images=images[1:],
    )

    logger.info("Icone ICO convertido: %s", ico_path)


def convert_svg_to_icns(svg_path, icns_path, sizes=None):  # noqa: ANN001,ANN201
    """Converte SVG para ICNS (macOS)"""
    icns_file_path = Path(icns_path)
    svg_path = str(svg_path)

    image_module = _require_pillow_image()

    if sizes is None:
        sizes = [16, 32, 64, 128, 256, 512, 1024]

    # No macOS, usar iconutil se disponivel
    try:
        import subprocess
        import tempfile

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

            max_size = max((size for size, _ in iconset_sizes), default=1024)
            base_data = _render_svg_to_png(svg_path, max_size)
            base_image = image_module.open(io.BytesIO(base_data))

            for size, filename in iconset_sizes:
                img = base_image.resize((size, size), image_module.Resampling.LANCZOS)
                img.save(str(iconset_dir / filename), format="PNG")

            # Usar iconutil para gerar ICNS
            result = subprocess.run(
                [
                    "iconutil",
                    "-c",
                    "icns",
                    str(iconset_dir),
                    "-o",
                    str(icns_file_path),
                ],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                logger.info("Icone ICNS convertido: %s", icns_file_path)
                return True
            logger.error("Erro com iconutil: %s", result.stderr)
            return False

    except Exception as e:
        logger.error("Fallback para conversao PIL: %s", e)
        # Fallback: converter para PNG de alta resolucao
        png_data = _render_svg_to_png(svg_path, 1024)
        img = image_module.open(io.BytesIO(png_data))
        fallback_png = icns_file_path.with_suffix(".png")
        img.save(fallback_png, format="PNG")
        logger.warning("Icone PNG criado como fallback: %s", fallback_png)
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
        icns_file = resources_dir / "app_icon.icns"
        convert_svg_to_icns(svg_file, icns_file)
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


if __name__ == "__main__":
    success = convert_all_icons()
    if not success:
        logger.error("ERRO: Nem todos os icones foram convertidos")
        if cairosvg is None:
            logger.error("Instale cairosvg: pip install cairosvg")
    else:
        logger.info("Todos os icones convertidos com sucesso")
