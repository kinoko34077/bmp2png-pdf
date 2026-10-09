from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Sequence

from PIL import Image
from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import A4, landscape, portrait
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


def convert_bmp_to_png(input_path: Path, compression_level: int = 9) -> Path:
    """Convert one BMP to a lossless PNG beside its source."""
    if not 0 <= compression_level <= 9:
        raise ValueError("PNG圧縮レベルは0〜9で指定してください。")

    output_path = input_path.with_suffix(".png")
    with Image.open(input_path) as image:
        image.save(output_path, format="PNG", compress_level=compression_level)
    return output_path


def create_combined_pdf(png_paths: Sequence[Path], output_path: Path) -> Path:
    """Create one A4 page per PNG without resampling the embedded raster data."""
    if not png_paths:
        raise ValueError("PDFに含めるPNGがありません。")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{output_path.stem}-", suffix=".tmp.pdf", dir=output_path.parent
    )
    os.close(fd)
    temporary_path = Path(temporary_name)

    try:
        pdf = canvas.Canvas(str(temporary_path), pagesize=A4, pageCompression=1)
        pdf.setTitle(output_path.stem)
        margin = 24.0

        for png_path in png_paths:
            with Image.open(png_path) as image:
                pixel_width, pixel_height = image.size
                dpi = image.info.get("dpi", (96, 96))
                try:
                    dpi_x, dpi_y = float(dpi[0]), float(dpi[1])
                    if dpi_x <= 0 or dpi_y <= 0:
                        raise ValueError
                except (TypeError, ValueError, IndexError):
                    dpi_x = dpi_y = 96.0

                page_size = landscape(A4) if pixel_width > pixel_height else portrait(A4)
                page_width, page_height = page_size
                pdf.setPageSize(page_size)

                # Keep all source pixels in the PDF image XObject. Placement may
                # shrink to fit the physical page; the raster itself is untouched.
                natural_width = pixel_width * 72.0 / dpi_x
                natural_height = pixel_height * 72.0 / dpi_y
                available_width = page_width - 2 * margin
                available_height = page_height - 2 * margin
                scale = min(
                    1.0,
                    available_width / natural_width,
                    available_height / natural_height,
                )
                draw_width = natural_width * scale
                draw_height = natural_height * scale
                x = (page_width - draw_width) / 2
                y = (page_height - draw_height) / 2
                pdf.drawImage(
                    ImageReader(image),
                    x,
                    y,
                    width=draw_width,
                    height=draw_height,
                    preserveAspectRatio=True,
                    anchor="c",
                    mask="auto",
                )
                pdf.showPage()

        pdf.save()

        reader = PdfReader(str(temporary_path))
        writer = PdfWriter()
        writer.append(reader)
        writer.set_page_layout("/SinglePage")
        if writer.pages:
            writer.open_destination = writer.pages[0]
        with temporary_path.open("wb") as stream:
            writer.write(stream)

        temporary_path.replace(output_path)
        return output_path
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise
