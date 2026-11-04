"""Unit tests for text/image watermarking, tiled grid layouts, page ranges, and collision safety."""

from __future__ import annotations

import warnings
from pathlib import Path

with warnings.catch_warnings():
    warnings.simplefilter("ignore", FutureWarning)
    import fitz

from src.core.preview_engine import generate_preview_image
from src.core.watermark_engine import apply_watermark
from src.core.worker import BatchProcessor
from src.models.job_config import (
    BatchJobConfig,
    CollisionStrategy,
    MetadataConfig,
    OutputConfig,
    WatermarkConfig,
    WatermarkLayout,
    WatermarkMode,
)
from src.models.task_result import TaskStatus
from src.utils.file_ops import parse_page_ranges, resolve_output_path


def test_text_watermark_injection_and_page_range_filtering(
    sample_pdf_path: Path,
    tmp_path: Path,
) -> None:
    """Verify text watermarks are injected only on target pages ('1,3')."""
    out_pdf = tmp_path / "text_wm.pdf"
    wm_config = WatermarkConfig(
        mode=WatermarkMode.TEXT,
        text="STRICTLY CONFIDENTIAL",
        font_size=42,
        color_rgb=(0.8, 0.1, 0.1),
        opacity=0.35,
        rotation=45,
        layout=WatermarkLayout.DIAGONAL_STAMP,
        target_pages="1,3",
    )

    with fitz.open(str(sample_pdf_path)) as doc:
        pages_count = apply_watermark(doc, wm_config)
        doc.save(str(out_pdf), garbage=4, deflate=True)

    assert pages_count == 2

    with fitz.open(str(out_pdf)) as reloaded:
        assert "STRICTLY CONFIDENTIAL" in reloaded[0].get_text()
        assert "STRICTLY CONFIDENTIAL" not in reloaded[1].get_text()
        assert "STRICTLY CONFIDENTIAL" in reloaded[2].get_text()
        assert "STRICTLY CONFIDENTIAL" not in reloaded[3].get_text()


def test_tiled_grid_text_watermark_repeats_across_page(
    sample_pdf_path: Path,
) -> None:
    """Verify TILED_GRID layout renders multiple watermark instances on each target page."""
    wm_config = WatermarkConfig(
        mode=WatermarkMode.TEXT,
        text="DO NOT COPY",
        font_size=28,
        opacity=0.25,
        rotation=30,
        layout=WatermarkLayout.TILED_GRID,
        target_pages="1",
    )

    with fitz.open(str(sample_pdf_path)) as doc:
        pages_count = apply_watermark(doc, wm_config)
        page1_text = doc[0].get_text()

    assert pages_count == 1
    occurrences = page1_text.count("DO NOT COPY")
    assert occurrences >= 6


def test_image_logo_watermark_overlay(
    sample_pdf_path: Path,
    sample_logo_png: Path,
    tmp_path: Path,
) -> None:
    """Verify transparent PNG logo watermarking embeds XObject images onto target pages."""
    out_pdf = tmp_path / "image_wm.pdf"
    wm_config = WatermarkConfig(
        mode=WatermarkMode.IMAGE,
        image_path=str(sample_logo_png),
        scale=0.4,
        opacity=0.5,
        rotation=15,
        layout=WatermarkLayout.SINGLE_CENTER,
        target_pages="1-2",
    )

    with fitz.open(str(sample_pdf_path)) as doc:
        pages_count = apply_watermark(doc, wm_config)
        doc.save(str(out_pdf), garbage=4, deflate=True)

    assert pages_count == 2

    with fitz.open(str(out_pdf)) as reloaded:
        assert len(reloaded[0].get_images()) >= 1
        assert len(reloaded[1].get_images()) >= 1
        assert len(reloaded[2].get_images()) == 0
        assert len(reloaded[3].get_images()) == 0


def test_collision_safe_output_path_resolution(
    sample_pdf_path: Path,
    tmp_path: Path,
) -> None:
    """Verify resolve_output_path never overwrites source or existing destination files."""
    # 1. Empty suffix in source folder still avoids overwriting source_path
    cfg_same_dir = OutputConfig(
        output_dir=None,
        suffix="",
        strategy=CollisionStrategy.APPEND_SUFFIX,
    )
    resolved_1 = Path(resolve_output_path(str(sample_pdf_path), cfg_same_dir))
    assert resolved_1 != sample_pdf_path.resolve()
    assert resolved_1.name == "sample_contract_processed.pdf"

    # Simulate first output file existing on disk -> next call must auto-increment to _1
    resolved_1.write_bytes(b"%PDF-1.4 mock")
    resolved_2 = Path(resolve_output_path(str(sample_pdf_path), cfg_same_dir))
    assert resolved_2.name == "sample_contract_processed_1.pdf"

    # 2. Dedicated output folder strategy
    dedicated_dir = tmp_path / "exported_pdfs"
    cfg_dedicated = OutputConfig(
        output_dir=str(dedicated_dir),
        suffix="_stamped",
        strategy=CollisionStrategy.DEDICATED_FOLDER,
    )
    resolved_3 = Path(resolve_output_path(str(sample_pdf_path), cfg_dedicated))
    assert resolved_3.parent == dedicated_dir.resolve()
    assert resolved_3.name == "sample_contract_stamped.pdf"


def test_parse_page_ranges() -> None:
    """Verify 1-based page range string parsing into sorted 0-based page indices."""
    assert parse_page_ranges("all", 5) == [0, 1, 2, 3, 4]
    assert parse_page_ranges("1-3, 5", 6) == [0, 1, 2, 4]
    assert parse_page_ranges("2, 4-10", 5) == [1, 3, 4]


def test_preview_engine_and_multithreaded_batch_worker(
    batch_pdf_paths: list[Path],
    sample_logo_png: Path,
    tmp_path: Path,
) -> None:
    """Verify non-destructive preview rendering and end-to-end multithreaded batch execution."""
    wm_cfg = WatermarkConfig(
        mode=WatermarkMode.IMAGE,
        image_path=str(sample_logo_png),
        scale=0.3,
        opacity=0.4,
        rotation=30,
        layout=WatermarkLayout.TILED_GRID,
        target_pages="all",
    )

    preview_img = generate_preview_image(
        str(batch_pdf_paths[0]),
        wm_cfg,
        page_num=0,
        max_dim=360,
    )
    assert preview_img.mode == "RGB"
    assert max(preview_img.size) == 360

    out_dir = tmp_path / "batch_output"
    job_cfg = BatchJobConfig(
        files=[str(p) for p in batch_pdf_paths],
        metadata=MetadataConfig(author="BatchBot", wipe_all=False),
        watermark=wm_cfg,
        output=OutputConfig(
            output_dir=str(out_dir),
            suffix="_final",
            strategy=CollisionStrategy.DEDICATED_FOLDER,
        ),
    )

    started_files: list[str] = []
    completed_results = []

    processor = BatchProcessor(max_workers=2)
    results = processor.run_batch(
        job_cfg,
        on_file_start=lambda fp: started_files.append(fp),
        on_file_complete=lambda res: completed_results.append(res),
    )

    assert len(results) == 3
    assert len(started_files) == 3
    assert len(completed_results) == 3
    for res in results:
        assert res.status == TaskStatus.SUCCESS
        assert res.output_path is not None
        assert Path(res.output_path).is_file()
        assert res.pages_processed == 3
