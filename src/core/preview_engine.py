"""Non-destructive in-memory PDF watermark preview renderer."""

from __future__ import annotations

import copy
import warnings
from pathlib import Path
from typing import Optional

from PIL import Image

with warnings.catch_warnings():
    warnings.simplefilter("ignore", FutureWarning)
    import fitz

from src.core.watermark_engine import apply_watermark
from src.models.job_config import WatermarkConfig, WatermarkMode
from src.utils.file_ops import parse_page_ranges
from src.utils.logger import get_logger

logger = get_logger("preview_engine")

# Standard ISO A4 dimensions in PDF points (72 points = 1 inch)
A4_WIDTH_PTS = 595.0
A4_HEIGHT_PTS = 842.0


def _create_synthetic_a4_document() -> fitz.Document:
    """Create an in-memory synthetic A4 preview document when no PDF is selected."""
    doc = fitz.open()
    page = doc.new_page(width=A4_WIDTH_PTS, height=A4_HEIGHT_PTS)

    # Subtle page header and mock document content lines so watermark contrast is visible
    shape = page.new_shape()
    shape.draw_rect(fitz.Rect(48, 48, A4_WIDTH_PTS - 48, 92))
    shape.finish(color=(0.82, 0.85, 0.90), fill=(0.95, 0.96, 0.98), width=0.8)

    page.insert_text(
        fitz.Point(62, 75),
        "SAMPLE A4 DOCUMENT PREVIEW (No PDF File Selected)",
        fontsize=12,
        fontname="helv",
        color=(0.25, 0.32, 0.42),
    )

    y_cursor = 135.0
    for block in range(4):
        for line_idx in range(6):
            line_w = (A4_WIDTH_PTS - 96) if line_idx < 5 else (A4_WIDTH_PTS - 220)
            rect = fitz.Rect(48, y_cursor, 48 + line_w, y_cursor + 6)
            shape.draw_rect(rect)
            y_cursor += 18.0
        y_cursor += 24.0
    shape.finish(color=None, fill=(0.88, 0.90, 0.93))
    shape.commit()

    return doc


def get_pdf_page_count(pdf_path: Optional[str]) -> int:
    """Return total pages in `pdf_path`, or 1 for the synthetic preview page."""
    if not pdf_path or not str(pdf_path).strip():
        return 1
    path = Path(pdf_path)
    if not path.is_file():
        return 1
    try:
        with fitz.open(str(path)) as doc:
            return max(1, len(doc))
    except Exception:
        return 1


def generate_preview_image(
    pdf_path: Optional[str],
    watermark_config: WatermarkConfig,
    page_num: int = 0,
    max_dim: int = 420,
) -> Image.Image:
    """Render an in-memory watermarked preview of a single PDF page as a PIL Image.

    Never mutates the source PDF on disk. Clones only the requested target page into
    a temporary in-memory `fitz.Document`, applies `apply_watermark` if `page_num`
    falls within `watermark_config.target_pages`, and rasterizes to fit `max_dim`.

    Args:
        pdf_path: Path to source PDF file, or None/empty for a synthetic A4 page.
        watermark_config: Current WatermarkConfig from the UI.
        page_num: Zero-based page index to preview.
        max_dim: Maximum width or height in pixels for the returned PIL Image.

    Returns:
        RGB PIL.Image.Image scaled to fit within `max_dim`.
    """
    temp_doc: Optional[fitz.Document] = None
    src_doc: Optional[fitz.Document] = None

    try:
        if pdf_path and str(pdf_path).strip() and Path(pdf_path).is_file():
            src_doc = fitz.open(str(pdf_path))
            total_pages = len(src_doc)
            if total_pages == 0:
                temp_doc = _create_synthetic_a4_document()
                total_pages = 1
                clamped_page = 0
            else:
                clamped_page = max(0, min(page_num, total_pages - 1))
                temp_doc = fitz.open()
                temp_doc.insert_pdf(src_doc, from_page=clamped_page, to_page=clamped_page)
        else:
            temp_doc = _create_synthetic_a4_document()
            total_pages = 1
            clamped_page = 0

        # Check if `clamped_page` is targeted by `watermark_config.target_pages`
        try:
            targeted_indices = parse_page_ranges(watermark_config.target_pages, total_pages)
        except ValueError:
            targeted_indices = list(range(total_pages))

        if clamped_page in targeted_indices and watermark_config.mode != WatermarkMode.NONE:
            preview_cfg = copy.deepcopy(watermark_config)
            preview_cfg.target_pages = "all"
            try:
                apply_watermark(temp_doc, preview_cfg)
            except (FileNotFoundError, ValueError) as wm_err:
                logger.debug("Preview watermark skipped: %s", wm_err)

        preview_page = temp_doc[0]
        rect = preview_page.rect
        page_max_side = max(1.0, rect.width, rect.height)
        scale_factor = float(max(64, max_dim)) / page_max_side
        matrix = fitz.Matrix(scale_factor, scale_factor)

        pixmap = preview_page.get_pixmap(matrix=matrix, alpha=False)
        img = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
        return img

    finally:
        if temp_doc is not None:
            temp_doc.close()
        if src_doc is not None:
            src_doc.close()

