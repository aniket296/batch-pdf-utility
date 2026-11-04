"""Unit tests for the PDF metadata reading, selective injection, and full XMP wipe engine."""

from __future__ import annotations

import warnings
from pathlib import Path

with warnings.catch_warnings():
    warnings.simplefilter("ignore", FutureWarning)
    import fitz

from src.core.metadata_engine import apply_metadata, read_metadata
from src.models.job_config import MetadataConfig


def test_read_initial_metadata(sample_pdf_path: Path) -> None:
    """Verify read_metadata extracts all standard fields and detects XMP XML streams."""
    with fitz.open(str(sample_pdf_path)) as doc:
        meta = read_metadata(doc)

    assert meta["title"] == "Legacy Contract v1"
    assert meta["author"] == "Original Author"
    assert meta["subject"] == "Confidential M&A"
    assert meta["keywords"] == "legacy, internal, draft"
    assert meta["creator"] == "LegacyWordProcessor"
    assert meta["producer"] == "LegacyPDFEngine"
    assert meta["has_xml_metadata"] is True


def test_selective_metadata_injection_preserves_untouched_fields(
    sample_pdf_path: Path,
    tmp_path: Path,
) -> None:
    """Verify non-empty fields are updated while blank fields remain preserved."""
    out_pdf = tmp_path / "selective_out.pdf"
    config = MetadataConfig(
        author="Enterprise Compliance Team",
        title="Approved Contract v2",
        subject="",  # Leave blank -> should preserve "Confidential M&A"
        keywords="approved, final",
        creator="",  # Leave blank -> should preserve "LegacyWordProcessor"
        producer="",
        wipe_all=False,
    )

    with fitz.open(str(sample_pdf_path)) as doc:
        apply_metadata(doc, config)
        doc.save(str(out_pdf), garbage=4, deflate=True)

    with fitz.open(str(out_pdf)) as reloaded:
        meta = read_metadata(reloaded)

    assert meta["author"] == "Enterprise Compliance Team"
    assert meta["title"] == "Approved Contract v2"
    assert meta["keywords"] == "approved, final"
    assert meta["subject"] == "Confidential M&A"
    assert meta["creator"] == "LegacyWordProcessor"
    assert meta["producer"] == "LegacyPDFEngine"


def test_full_metadata_and_xmp_wipe(
    sample_pdf_path: Path,
    tmp_path: Path,
) -> None:
    """Verify wipe_all=True scrubs all standard metadata keys and deletes XMP streams."""
    out_pdf = tmp_path / "wiped_out.pdf"
    config = MetadataConfig(
        author="Should Be Ignored When Wipe All Is True",
        title="Should Be Ignored",
        wipe_all=True,
    )

    with fitz.open(str(sample_pdf_path)) as doc:
        apply_metadata(doc, config)
        doc.save(str(out_pdf), garbage=4, deflate=True)

    with fitz.open(str(out_pdf)) as reloaded:
        meta = read_metadata(reloaded)

    assert meta["title"] == ""
    assert meta["author"] == ""
    assert meta["subject"] == ""
    assert meta["keywords"] == ""
    assert meta["creator"] == ""
    assert meta["creationDate"] == ""
    assert meta["modDate"] == ""
    assert meta["has_xml_metadata"] is False
