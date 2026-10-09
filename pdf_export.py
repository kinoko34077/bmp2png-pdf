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


def create_combined_pdf(png_paths: Sequence[Path], output_path: Path) -> Path:
    """Create one A4 page per PNG, preserving raster pixels and DPI placement."""
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
        pdf = canvas.Canvas(str(reportlab_path), pagesize=A4, pageCompression=1)
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
                natural_width, natural_height = pixel_width * 72.0 / dpi_x, pixel_height * 72.0 / dpi_y
                scale = min(1.0, (page_width - 2 * margin) / natural_width, (page_height - 2 * margin) / natural_height)
                draw_width, draw_height = natural_width * scale, natural_height * scale
                pdf.drawImage(
                    ImageReader(image), (page_width - draw_width) / 2,
                    (page_height - draw_height) / 2, width=draw_width, height=draw_height,
                    preserveAspectRatio=True, anchor="c", mask="auto",
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
