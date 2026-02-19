#!/usr/bin/env python3
"""
Script para converter SVG para ICO, ICNS e PNG
Usado no build dos executaveis multi-plataforma
"""

import os
import io
import importlib
from typing import Any


def _import_optional_module(module_name: str) -> Any | None:
    try:
        return importlib.import_module(module_name)
    except ImportError:
        return None


def _require_pillow_image() -> Any:
    image_module = _import_optional_module("PIL.Image")
    if image_module is None:
        raise ImportError("Pillow nao encontrado")
    return image_module


cairosvg = _import_optional_module("cairosvg")

def convert_svg_to_ico(svg_path, ico_path, sizes=[16, 32, 48, 64, 128, 256]):
    """Converte SVG para ICO com multiplos tamanhos (Windows)"""

    if cairosvg is None:
        raise ImportError("cairosvg nao encontrado")
    image_module = _require_pillow_image()

    # Converter SVG para PNG primeiro
    png_data = cairosvg.svg2png(url=svg_path, output_width=256, output_height=256)

    # Criar imagem PIL
    base_img = image_module.open(io.BytesIO(png_data))

    # Criar imagens em diferentes tamanhos
    images = []
    for size in sizes:
        img = base_img.resize((size, size), image_module.Resampling.LANCZOS)
        images.append(img)

    # Salvar como ICO
    images[0].save(
        ico_path,
        format='ICO',
        sizes=[(img.width, img.height) for img in images],
        append_images=images[1:]
    )

    print(f"Icone ICO convertido: {ico_path}")

def convert_svg_to_icns(svg_path, icns_path, sizes=[16, 32, 64, 128, 256, 512, 1024]):
    """Converte SVG para ICNS (macOS)"""

    if cairosvg is None:
        raise ImportError("cairosvg nao encontrado")
    image_module = _require_pillow_image()

    # No macOS, usar iconutil se disponivel
    try:
        import subprocess
        import tempfile

        # Criar diretorio temporario para iconset
        with tempfile.TemporaryDirectory() as temp_dir:
            iconset_dir = os.path.join(temp_dir, "icon.iconset")
            os.makedirs(iconset_dir)

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
                (1024, "icon_512x512@2x.png")
            ]

            for size, filename in iconset_sizes:
                png_data = cairosvg.svg2png(url=svg_path, output_width=size, output_height=size)
                img = image_module.open(io.BytesIO(png_data))
                img.save(os.path.join(iconset_dir, filename), format='PNG')

            # Usar iconutil para gerar ICNS
            result = subprocess.run([
                'iconutil', '-c', 'icns', iconset_dir, '-o', icns_path
            ], capture_output=True, text=True)

            if result.returncode == 0:
                print(f"Icone ICNS convertido: {icns_path}")
                return True
            else:
                print(f"Erro com iconutil: {result.stderr}")
                return False

    except Exception as e:
        print(f"Fallback para conversao PIL: {e}")
        # Fallback: converter para PNG de alta resolucao
        png_data = cairosvg.svg2png(url=svg_path, output_width=1024, output_height=1024)
        img = image_module.open(io.BytesIO(png_data))
        img.save(icns_path.replace('.icns', '.png'), format='PNG')
        print(f"Icone PNG criado como fallback: {icns_path.replace('.icns', '.png')}")
        return True

def convert_svg_to_png(svg_path, png_path, size=256):
    """Converte SVG para PNG (Linux)"""

    if cairosvg is None:
        raise ImportError("cairosvg nao encontrado")

    # Converter SVG para PNG
    png_data = cairosvg.svg2png(url=svg_path, output_width=size, output_height=size)

    with open(png_path, 'wb') as f:
        f.write(png_data)

    print(f"Icone PNG convertido: {png_path}")

def convert_all_icons():
    """Converte icone SVG para todos os formatos necessarios"""
    svg_file = "resources/app_icon.svg"

    if not os.path.exists(svg_file):
        print(f"SVG nao encontrado: {svg_file}")
        return False

    # Garantir que diretorio resources existe
    os.makedirs("resources", exist_ok=True)

    success = True

    try:
        # Windows ICO
        ico_file = "resources/app_icon.ico"
        convert_svg_to_ico(svg_file, ico_file)
    except Exception as e:
        print(f"Erro convertendo ICO: {e}")
        success = False

    try:
        # macOS ICNS
        icns_file = "resources/app_icon.icns"
        convert_svg_to_icns(svg_file, icns_file)
    except Exception as e:
        print(f"Erro convertendo ICNS: {e}")
        success = False

    try:
        # Linux PNG
        png_file = "resources/app_icon.png"
        convert_svg_to_png(svg_file, png_file)
    except Exception as e:
        print(f"Erro convertendo PNG: {e}")
        success = False

    return success

if __name__ == "__main__":
    success = convert_all_icons()
    if not success:
        print("ERRO: Nem todos os icones foram convertidos")
        if cairosvg is None:
            print("Instale cairosvg: pip install cairosvg")
    else:
        print("Todos os icones convertidos com sucesso")
