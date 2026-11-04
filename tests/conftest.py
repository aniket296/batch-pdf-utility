"""Shared pytest fixtures for generating synthetic multi-page PDFs and transparent PNGs."""

from __future__ import annotations

import warnings
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

with warnings.catch_warnings():
    warnings.simplefilter("ignore", FutureWarning)
    import fitz


@pytest.fixture()
def sample_pdf_path(tmp_path: Path) -> Path:
    """Create a 4-page sample PDF with initial metadata and XMP XML stream."""
    pdf_path = tmp_path / "sample_contract.pdf"
    doc = fitz.open()

    for idx in range(4):
        page = doc.new_page(width=595, height=842)
        page.insert_text(
            fitz.Point(72, 100),
            f"Sample Corporate Document - Page {idx + 1}",
            fontsize=14,
            fontname="helv",
        )

    doc.set_metadata(
        {
            "title": "Legacy Contract v1",
            "author": "Original Author",
            "subject": "Confidential M&A",
            "keywords": "legacy, internal, draft",
            "creator": "LegacyWordProcessor",
            "producer": "LegacyPDFEngine",
            "creationDate": "D:20220101120000Z",
            "modDate": "D:20220601120000Z",
        }
    )
    xmp_packet = (
        '<?xpacket begin="" id="W5M0MpCehiHzreSzNTczkc9d"?>'
        '<x:xmpmeta xmlns:x="adobe:ns:meta/">'
        "<rdf:RDF xmlns:rdf=\"http://www.w3.org/1999/02/22-rdf-syntax-ns#\">"
        "<rdf:Description rdf:about=\"\"/>"
        "</rdf:RDF></x:xmpmeta>"
        '<?xpacket end="w"?>'
    )
    doc.set_xml_metadata(xmp_packet)
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


@pytest.fixture()
def batch_pdf_paths(tmp_path: Path) -> list[Path]:
    """Create 3 multi-page PDF files for testing multi-threaded batch execution."""
    paths: list[Path] = []
    for file_idx in range(1, 4):
        pdf_path = tmp_path / f"batch_doc_{file_idx}.pdf"
        doc = fitz.open()
        for page_idx in range(3):
            page = doc.new_page(width=595, height=842)
            page.insert_text(
                fitz.Point(72, 120),
                f"Batch File #{file_idx} - Page {page_idx + 1}",
                fontsize=12,
            )
        doc.set_metadata({"title": f"Doc {file_idx}", "author": "InitialUser"})
        doc.save(str(pdf_path))
        doc.close()
        paths.append(pdf_path)
    return paths


@pytest.fixture()
def sample_logo_png(tmp_path: Path) -> Path:
    """Generate a synthetic transparent RGBA PNG logo for image watermark testing."""
    logo_path = tmp_path / "corporate_logo.png"
    img = Image.new("RGBA", (240, 100), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle(
        [(10, 10), (230, 90)],
        radius=16,
        fill=(27, 54, 93, 220),
        outline=(16, 185, 129, 255),
        width=4,
    )
    img.save(str(logo_path), format="PNG")
    return logo_path
