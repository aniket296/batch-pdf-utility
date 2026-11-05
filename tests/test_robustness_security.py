"""Negative, boundary, security, and concurrency tests (QA campaign)."""

from __future__ import annotations

import hashlib
import time
import warnings
from pathlib import Path

import pytest

with warnings.catch_warnings():
    warnings.simplefilter("ignore", FutureWarning)
    import fitz

from src.core.metadata_engine import apply_metadata
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


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _make_pdf(path: Path, pages: int = 2) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = fitz.open()
    for i in range(pages):
        doc.new_page().insert_text(fitz.Point(72, 100), f"page {i + 1}")
    doc.save(str(path))
    doc.close()
    return path


# ---------------------------------------------------------------- parse_page_ranges
@pytest.mark.parametrize("bad", ["0", "-3", "abc", "3-1", "1-x", "0-2", "--"])
def test_page_range_rejects_malformed(bad: str) -> None:
    with pytest.raises(ValueError):
        parse_page_ranges(bad, 5)


@pytest.mark.parametrize(
    ("spec", "expected"),
    [
        ("1-1000000000", [0, 1, 2]),  # huge range is clamped, no memory blow-up
        ("99", []),
        ("", [0, 1, 2]),
        ("3-", [2]),
        ("1,,2,", [0, 1]),
        ("2,2,2", [1]),
    ],
)
def test_page_range_boundaries(spec: str, expected: list[int]) -> None:
    assert parse_page_ranges(spec, 3) == expected


def test_page_range_zero_pages_and_long_input() -> None:
    assert parse_page_ranges("all", 0) == []
    start = time.perf_counter()
    parse_page_ranges("1," * 200_000, 10)
    assert time.perf_counter() - start < 3.0


# ------------------------------------------------------------- resolve_output_path
@pytest.mark.parametrize("suffix", ["..\\..\\evil", "../../evil", "a/b", "C:\\x\\y"])
def test_suffix_cannot_escape_output_dir(tmp_path: Path, suffix: str) -> None:
    src = _make_pdf(tmp_path / "in" / "doc.pdf")
    out_dir = tmp_path / "out"
    cfg = OutputConfig(
        output_dir=str(out_dir),
        suffix=suffix,
        strategy=CollisionStrategy.DEDICATED_FOLDER,
    )
    resolved = Path(resolve_output_path(str(src), cfg))
    assert resolved.parent == out_dir.resolve()


def test_reserved_paths_are_unique_for_same_stem(tmp_path: Path) -> None:
    a = _make_pdf(tmp_path / "a" / "x.pdf")
    b = _make_pdf(tmp_path / "b" / "x.pdf")
    cfg = OutputConfig(
        output_dir=str(tmp_path / "out"),
        suffix="_p",
        strategy=CollisionStrategy.DEDICATED_FOLDER,
    )
    p1 = resolve_output_path(str(a), cfg, reserve=True)
    p2 = resolve_output_path(str(b), cfg, reserve=True)
    assert p1 != p2


def test_mirror_tree_preserves_relative_structure(tmp_path: Path) -> None:
    root = tmp_path / "root"
    src = _make_pdf(root / "sub" / "deep" / "f.pdf")
    cfg = OutputConfig(
        output_dir=str(tmp_path / "out"),
        suffix="_m",
        strategy=CollisionStrategy.MIRROR_TREE,
    )
    resolved = Path(resolve_output_path(str(src), cfg, base_root=str(root)))
    assert resolved == (tmp_path / "out" / "sub" / "deep" / "f_m.pdf").resolve()


# --------------------------------------------------------------------- config bounds
def test_watermark_config_clamps_and_validates() -> None:
    cfg = WatermarkConfig(opacity=-5, scale=99, font_size=0, color_rgb=(2, -1, 0.5))
    assert cfg.opacity == 0.05
    assert cfg.scale == 3.0
    assert cfg.font_size == 6
    assert cfg.color_rgb == (1.0, 0.0, 0.5)
    with pytest.raises(ValueError):
        WatermarkConfig(color_rgb=(1.0, 1.0))  # type: ignore[arg-type]


# ----------------------------------------------------------------- engine hostile input
def test_wipe_leaves_no_residual_strings_in_file_bytes(sample_pdf_path: Path, tmp_path: Path) -> None:
    out = tmp_path / "wiped.pdf"
    with fitz.open(str(sample_pdf_path)) as doc:
        apply_metadata(doc, MetadataConfig(wipe_all=True))
        doc.save(str(out), garbage=4, deflate=True)
    raw = out.read_bytes()
    for needle in (b"Original Author", b"Legacy Contract", b"LegacyPDFEngine",
                   b"LegacyWordProcessor", b"xmpmeta", b"Confidential M&A"):
        assert needle not in raw, needle


def test_text_watermark_extreme_inputs_do_not_crash() -> None:
    doc = fitz.open()
    doc.new_page()
    for cfg in (
        WatermarkConfig(mode=WatermarkMode.TEXT, text="X" * 5000, font_size=12),
        WatermarkConfig(mode=WatermarkMode.TEXT, text="BIG", font_size=1000),
        WatermarkConfig(mode=WatermarkMode.TEXT, text="机密 CONFIDENTIAL 🔒"),
        WatermarkConfig(mode=WatermarkMode.TEXT, text="   "),
        WatermarkConfig(mode=WatermarkMode.TEXT, text="T", layout=WatermarkLayout.TILED_GRID, rotation=-90),
    ):
        start = time.perf_counter()
        apply_watermark(doc, cfg)
        assert time.perf_counter() - start < 5.0


def test_image_watermark_rejects_missing_and_fake_png(tmp_path: Path) -> None:
    doc = fitz.open()
    doc.new_page()
    with pytest.raises(FileNotFoundError):
        apply_watermark(doc, WatermarkConfig(mode=WatermarkMode.IMAGE, image_path=str(tmp_path / "nope.png")))
    fake = tmp_path / "fake.png"
    fake.write_text("this is not a png")
    with pytest.raises(Exception):  # noqa: B017 - PIL.UnidentifiedImageError
        apply_watermark(doc, WatermarkConfig(mode=WatermarkMode.IMAGE, image_path=str(fake)))


def test_preview_is_resilient_and_non_mutating(sample_pdf_path: Path) -> None:
    before = _sha(sample_pdf_path)
    bad_cfgs = [
        WatermarkConfig(mode=WatermarkMode.IMAGE, image_path="Z:\\does\\not\\exist.png"),
        WatermarkConfig(mode=WatermarkMode.TEXT, target_pages="garbage"),
    ]
    for cfg in bad_cfgs:
        img = generate_preview_image(str(sample_pdf_path), cfg, page_num=999, max_dim=300)
        assert max(img.size) == 300
    img = generate_preview_image(str(sample_pdf_path / "missing.pdf"), WatermarkConfig(), -5, 200)
    assert max(img.size) == 200
    assert _sha(sample_pdf_path) == before


# ---------------------------------------------------------------------- worker
def _job(files: list[Path], out: Path, **wm: object) -> BatchJobConfig:
    return BatchJobConfig(
        files=[str(f) for f in files],
        metadata=MetadataConfig(author="QA"),
        watermark=WatermarkConfig(mode=WatermarkMode.TEXT, text="QA", **wm),  # type: ignore[arg-type]
        output=OutputConfig(output_dir=str(out), suffix="_q", strategy=CollisionStrategy.DEDICATED_FOLDER),
    )


def test_worker_handles_hostile_files_and_leaves_no_stray_output(tmp_path: Path) -> None:
    good = _make_pdf(tmp_path / "in" / "good.pdf")
    zero = tmp_path / "in" / "zero.pdf"
    zero.write_bytes(b"")
    junk = tmp_path / "in" / "junk.pdf"
    junk.write_bytes(b"%PDF-1.7\n" + bytes(range(256)) * 20)
    text = tmp_path / "in" / "notpdf.pdf"
    text.write_text("hello")
    enc = tmp_path / "in" / "enc.pdf"
    d = fitz.open()
    d.new_page()
    d.save(str(enc), encryption=fitz.PDF_ENCRYPT_AES_256, user_pw="u", owner_pw="o")
    d.close()
    missing = tmp_path / "in" / "missing.pdf"

    hashes = {p: _sha(p) for p in (good, zero, junk, text, enc)}
    out = tmp_path / "out"
    results = BatchProcessor(max_workers=3).run_batch(_job([good, zero, junk, text, enc, missing], out))

    by_name = {Path(r.source_path).name: r for r in results}
    assert by_name["good.pdf"].status == TaskStatus.SUCCESS
    for name in ("zero.pdf", "junk.pdf", "notpdf.pdf", "enc.pdf", "missing.pdf"):
        assert by_name[name].status == TaskStatus.FAILED, name
        assert by_name[name].error_message
    produced = sorted(p.name for p in out.glob("*"))
    assert produced == ["good_q.pdf"], produced  # no 0-byte leftovers from failed jobs
    assert all(_sha(p) == h for p, h in hashes.items())  # sources never mutated


def test_worker_same_stem_files_never_overwrite_each_other(tmp_path: Path) -> None:
    files = [_make_pdf(tmp_path / f"d{i}" / "same.pdf", pages=i + 1) for i in range(12)]
    out = tmp_path / "out"
    results = BatchProcessor(max_workers=8).run_batch(_job(files, out))
    assert all(r.status == TaskStatus.SUCCESS for r in results)
    outputs = {r.output_path for r in results}
    assert len(outputs) == 12
    assert len(list(out.glob("*.pdf"))) == 12
    page_counts = sorted(len(fitz.open(p)) for p in outputs if p)
    assert page_counts == list(range(1, 13))  # each output holds its own source's content


def test_worker_cancellation_is_prompt_and_clean(tmp_path: Path) -> None:
    files = [_make_pdf(tmp_path / "in" / f"f{i}.pdf", pages=3) for i in range(25)]
    out = tmp_path / "out"
    proc = BatchProcessor(max_workers=1)
    started: list[str] = []

    def on_start(fp: str) -> None:
        started.append(fp)
        proc.cancel()

    results = proc.run_batch(_job(files, out), on_file_start=on_start)
    assert len(results) == 25
    assert len(started) <= 2
    assert sum(r.status == TaskStatus.SUCCESS for r in results) == 0
    assert list(out.glob("*")) == []  # cancelled jobs leave nothing behind
    # processor is reusable after cancellation
    again = proc.run_batch(_job(files[:2], out))
    assert [r.status for r in again] == [TaskStatus.SUCCESS] * 2


def test_worker_empty_batch_fires_completion_once(tmp_path: Path) -> None:
    calls: list[int] = []
    BatchProcessor().run_batch(_job([], tmp_path), on_batch_complete=lambda r: calls.append(len(r)))
    assert calls == [0]


def test_worker_callback_exception_does_not_break_batch(tmp_path: Path) -> None:
    files = [_make_pdf(tmp_path / "in" / f"f{i}.pdf") for i in range(3)]

    def boom(_: object) -> None:
        raise RuntimeError("ui bug")

    results = BatchProcessor(max_workers=2).run_batch(
        _job(files, tmp_path / "out"), on_file_start=boom, on_file_complete=boom
    )
    assert all(r.status == TaskStatus.SUCCESS for r in results)

