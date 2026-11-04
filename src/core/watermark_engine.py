"""PDF watermark engine supporting vector text, transparent PNG logos, and tiled grids."""

from __future__ import annotations

import io
import math
import warnings
from pathlib import Path

from PIL import Image

with warnings.catch_warnings():
    warnings.simplefilter("ignore", FutureWarning)
    import fitz

from src.models.job_config import WatermarkConfig, WatermarkLayout, WatermarkMode
from src.utils.file_ops import parse_page_ranges
from src.utils.logger import get_logger

logger = get_logger("watermark_engine")


def _compute_anchor_points(
    page_rect: fitz.Rect,
    item_width: float,
    item_height: float,
    layout: WatermarkLayout,
) -> list[fitz.Point]:
    """Calculate center anchor coordinates on a page for the chosen watermark layout."""
    cx = (page_rect.x0 + page_rect.x1) / 2.0
    cy = (page_rect.y0 + page_rect.y1) / 2.0

    if layout in (WatermarkLayout.SINGLE_CENTER, WatermarkLayout.DIAGONAL_STAMP):
        return [fitz.Point(cx, cy)]

    # TILED_GRID: compute a multi-row, multi-column lattice across the page bounding box
    page_w = max(1.0, page_rect.width)
    page_h = max(1.0, page_rect.height)

    step_x = max(item_width * 1.45, page_w / 3.0)
    step_y = max(item_height * 2.2, page_h / 4.0)

    # Ensure at least a 3x3 or 2x3 grid so watermarks cannot be cropped out
    cols = max(2, int(math.ceil(page_w / step_x)))
    rows = max(3, int(math.ceil(page_h / step_y)))

    col_spacing = page_w / cols
    row_spacing = page_h / rows

    points: list[fitz.Point] = []
    for r in range(rows):
        y = page_rect.y0 + (r + 0.5) * row_spacing
        # Slight horizontal stagger on odd rows for stronger anti-cropping coverage
        stagger = (col_spacing * 0.25) if (r % 2 == 1 and cols >= 3) else 0.0
        for c in range(cols):
            x = page_rect.x0 + (c + 0.5) * col_spacing + stagger
            if page_rect.x0 + 20 <= x <= page_rect.x1 - 20:
                points.append(fitz.Point(x, y))
            else:
                points.append(fitz.Point(page_rect.x0 + (c + 0.5) * col_spacing, y))

    return points


def _effective_rotation(config: WatermarkConfig) -> float:
    """Determine the effective rotation angle in degrees based on layout and config."""
    if config.layout == WatermarkLayout.DIAGONAL_STAMP and config.rotation == 0:
        return 45.0
    return float(config.rotation)


def _apply_text_watermark_to_page(page: fitz.Page, config: WatermarkConfig) -> None:
    """Render vector text watermarks onto a single PDF page with opacity and rotation."""
    text = (config.text or "").strip()
    if not text:
        return

    font = fitz.Font("helv")
    fontsize = float(config.font_size)
    text_width = font.text_length(text, fontsize=fontsize)
    ascender = font.ascender * fontsize
    descender = font.descender * fontsize
    text_height = max(fontsize, ascender - descender)

    angle = _effective_rotation(config)
    rad = math.radians(abs(angle))
    rot_w = abs(text_width * math.cos(rad)) + abs(text_height * math.sin(rad))
    rot_h = abs(text_width * math.sin(rad)) + abs(text_height * math.cos(rad))

    anchors = _compute_anchor_points(page.rect, rot_w, rot_h, config.layout)

    for pivot in anchors:
        tw = fitz.TextWriter(page.rect)
        # Position baseline so the glyph bounding box is centered at `pivot`
        baseline_x = pivot.x - (text_width / 2.0)
        baseline_y = pivot.y + ((ascender + descender) / 2.0)
        tw.append(fitz.Point(baseline_x, baseline_y), text, font=font, fontsize=fontsize)
        # In PDF/PyMuPDF coordinates, positive angle in Matrix rotates counter-clockwise
        tw.write_text(
            page,
            color=config.color_rgb,
            opacity=config.opacity,
            morph=(pivot, fitz.Matrix(angle)),
            overlay=True,
        )


def _prepare_watermark_image_bytes(
    config: WatermarkConfig,
    reference_page_rect: fitz.Rect,
) -> tuple[bytes, float, float]:
    """Load, alpha-modulate, scale, and rotate a PNG image into a PNG byte stream.

    Returns:
        Tuple of (png_bytes, display_width_pts, display_height_pts).
    """
    if not config.image_path:
        raise ValueError("WatermarkMode.IMAGE requires a valid image_path.")

    img_path = Path(config.image_path)
    if not img_path.is_file():
        raise FileNotFoundError(f"Watermark image file not found: {img_path}")

    with Image.open(img_path) as raw_img:
        rgba = raw_img.convert("RGBA")

    # Adjust alpha channel proportionally by config.opacity
    r_ch, g_ch, b_ch, a_ch = rgba.split()
    opacity_factor = max(0.05, min(1.0, float(config.opacity)))
    a_ch = a_ch.point(lambda p: int(round(p * opacity_factor)))
    rgba = Image.merge("RGBA", (r_ch, g_ch, b_ch, a_ch))

    # Rotate cleanly with expand=True before converting to bytes
    angle = _effective_rotation(config)
    if abs(angle) > 0.01:
        rgba = rgba.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True)

    # Calculate target PDF point dimensions proportional to page width and config.scale
    base_target_w = max(24.0, reference_page_rect.width * float(config.scale))
    aspect_ratio = rgba.height / max(1, rgba.width)
    display_w = base_target_w
    display_h = max(24.0, display_w * aspect_ratio)

    buf = io.BytesIO()
    rgba.save(buf, format="PNG")
    return buf.getvalue(), display_w, display_h


def _apply_image_watermark_to_page(
    page: fitz.Page,
    config: WatermarkConfig,
    png_bytes: bytes,
    base_w: float,
    base_h: float,
) -> None:
    """Overlay a prepared PNG byte stream onto a PDF page in single or tiled layout."""
    anchors = _compute_anchor_points(page.rect, base_w, base_h, config.layout)

    for pivot in anchors:
        half_w = base_w / 2.0
        half_h = base_h / 2.0
        target_rect = fitz.Rect(
            pivot.x - half_w,
            pivot.y - half_h,
            pivot.x + half_w,
            pivot.y + half_h,
        )
        page.insert_image(target_rect, stream=png_bytes, keep_proportion=True, overlay=True)


def apply_watermark(doc: fitz.Document, config: WatermarkConfig) -> int:
    """Apply configured text or PNG image watermark across target pages of `doc`.

    Args:
        doc: Open PyMuPDF Document to watermark in place.
        config: WatermarkConfig specifying mode, appearance, layout, and target pages.

    Returns:
        Number of pages in `doc` that had a watermark applied.
    """
    if config.mode == WatermarkMode.NONE or len(doc) == 0:
        return 0

    target_indices = parse_page_ranges(config.target_pages, len(doc))
    if not target_indices:
        return 0

    pages_watermarked = 0

    if config.mode == WatermarkMode.TEXT:
        if not (config.text or "").strip():
            return 0
        for page_idx in target_indices:
            page = doc[page_idx]
            _apply_text_watermark_to_page(page, config)
            pages_watermarked += 1
        logger.debug(
            "Applied TEXT watermark ('%s', layout=%s) to %d page(s).",
            config.text,
            config.layout.value,
            pages_watermarked,
        )
        return pages_watermarked

    if config.mode == WatermarkMode.IMAGE:
        first_page_rect = doc[target_indices[0]].rect
        png_bytes, disp_w, disp_h = _prepare_watermark_image_bytes(config, first_page_rect)
        for page_idx in target_indices:
            page = doc[page_idx]
            _apply_image_watermark_to_page(page, config, png_bytes, disp_w, disp_h)
            pages_watermarked += 1
        logger.debug(
            "Applied IMAGE watermark ('%s', layout=%s) to %d page(s).",
            config.image_path,
            config.layout.value,
            pages_watermarked,
        )
        return pages_watermarked

    return 0
