from __future__ import annotations

import os
import tempfile
from pathlib import Path

from PIL import Image


SUPPORTED_SUFFIXES = frozenset({".bmp", ".png"})


def convert_image_to_png(
    input_path: Path, output_path: Path, compression_level: int = 9
) -> Path:
    """Losslessly recompress one BMP or PNG, retaining pixels and source DPI."""
    if not 0 <= compression_level <= 9:
        raise ValueError("PNG圧縮レベルは0〜9で指定してください。")

    input_path = Path(input_path)
    output_path = Path(output_path)
    if input_path.suffix.casefold() not in SUPPORTED_SUFFIXES:
        raise ValueError("BMPまたはPNGファイルを指定してください。")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{output_path.stem}-", suffix=".tmp.png", dir=output_path.parent
    )
    os.close(fd)
    temporary_path = Path(temporary_name)
    try:
        with Image.open(input_path) as image:
            dpi = image.info.get("dpi")
            save_options = {"format": "PNG", "compress_level": compression_level}
            if dpi:
                save_options["dpi"] = dpi
            image.save(temporary_path, **save_options)
        temporary_path.replace(output_path)
        return output_path
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise


def convert_bmp_to_png(input_path: Path, compression_level: int = 9) -> Path:
    """Backward-compatible wrapper for the original BMP conversion function."""
    return convert_image_to_png(input_path, Path(input_path).with_suffix(".png"), compression_level)
