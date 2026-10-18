from __future__ import annotations

import math
import os
import tempfile
from pathlib import Path
from typing import Sequence

from PIL import Image
from pypdf import PdfReader, PdfWriter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


def create_combined_pdf(png_paths: Sequence[Path], output_path: Path) -> Path:
    """Create one edge-to-edge PDF page per PNG, preserving raster pixels and DPI."""
    if not png_paths:
        raise ValueError("PDFに含めるPNGがありません。")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pdf_fd, pdf_name = tempfile.mkstemp(
        prefix=f".{output_path.stem}-", suffix=".tmp.pdf", dir=output_path.parent
    )
    os.close(pdf_fd)
    final_fd, final_name = tempfile.mkstemp(
        prefix=f".{output_path.stem}-final-", suffix=".tmp.pdf", dir=output_path.parent
    )
    os.close(final_fd)
    reportlab_path, final_path = Path(pdf_name), Path(final_name)
    try:
        pdf = canvas.Canvas(str(reportlab_path), pageCompression=1)
        pdf.setTitle(output_path.stem)
        for png_path in png_paths:
            with Image.open(png_path) as image:
                pixel_width, pixel_height = image.size
                dpi = image.info.get("dpi", (96, 96))
                try:
                    dpi_x, dpi_y = float(dpi[0]), float(dpi[1])
                    if (
                        not math.isfinite(dpi_x)
                        or not math.isfinite(dpi_y)
                        or dpi_x <= 0
                        or dpi_y <= 0
                    ):
                        raise ValueError
                except (TypeError, ValueError, IndexError):
                    dpi_x = dpi_y = 96.0
                page_width = pixel_width * 72.0 / dpi_x
                page_height = pixel_height * 72.0 / dpi_y
                pdf.setPageSize((page_width, page_height))
                pdf.drawImage(
                    ImageReader(image), 0, 0, width=page_width, height=page_height,
                    mask="auto",
                )
                pdf.showPage()
        pdf.save()

        reader = PdfReader(str(reportlab_path))
        writer = PdfWriter()
        try:
            writer.append(reader)
        finally:
            reader.close()
        writer.set_page_layout("/SinglePage")
        writer.open_destination = writer.pages[0]
        with final_path.open("wb") as stream:
            writer.write(stream)
        final_path.replace(output_path)
        return output_path
    finally:
        reportlab_path.unlink(missing_ok=True)
        final_path.unlink(missing_ok=True)
