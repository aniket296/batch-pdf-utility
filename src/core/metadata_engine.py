"""PDF metadata extraction, selective property injection, and full XMP/Info sanitization."""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import Any, Union

with warnings.catch_warnings():
    warnings.simplefilter("ignore", FutureWarning)
    import fitz

from src.models.job_config import MetadataConfig
from src.utils.logger import get_logger

logger = get_logger("metadata_engine")

STANDARD_METADATA_KEYS: tuple[str, ...] = (
    "title",
    "author",
    "subject",
    "keywords",
    "creator",
    "producer",
    "creationDate",
    "modDate",
)


def read_metadata(doc: Union[fitz.Document, str, Path]) -> dict[str, Any]:
    """Extract current standard PDF metadata and XMP presence from a document.

    Args:
        doc: An open fitz.Document instance (or a file path to a PDF).

    Returns:
        Dictionary of normalized metadata strings plus 'has_xml_metadata' flag.
    """
    if isinstance(doc, (str, Path)):
        with fitz.open(str(doc)) as opened_doc:
            return read_metadata(opened_doc)

    raw_meta = doc.metadata or {}
    normalized: dict[str, Any] = {}
    for key in STANDARD_METADATA_KEYS:
        val = raw_meta.get(key)
        normalized[key] = str(val).strip() if val else ""

    normalized["format"] = str(raw_meta.get("format") or "")
    normalized["encryption"] = str(raw_meta.get("encryption") or "")

    try:
        xml_meta = doc.get_xml_metadata()
        normalized["has_xml_metadata"] = bool(xml_meta and xml_meta.strip())
    except Exception:
        normalized["has_xml_metadata"] = False

    return normalized


def apply_metadata(doc: fitz.Document, config: MetadataConfig) -> None:
    """Apply metadata updates or perform a complete metadata/XMP sanitization on a PDF.

    If `config.wipe_all` is True:
        - Clears all standard metadata dictionary keys (title, author, subject,
          keywords, creator, producer, creationDate, modDate).
        - Deletes document-level XML/XMP metadata streams via `doc.del_xml_metadata()`.
        - Scrubs any residual XMP packets or PieceInfo dictionaries in the PDF catalog.

    Otherwise:
        - Selectively updates only the non-empty fields provided in `config`,
          preserving existing metadata fields that were left blank.

    Args:
        doc: Open PyMuPDF Document to modify in place.
        config: MetadataConfig specifying wipe_all or selective field values.
    """
    if config.wipe_all:
        logger.debug("Wiping all PDF metadata and XMP streams.")
        # 1. Clear Info dictionary completely
        doc.set_metadata({})
        empty_meta = {key: "" for key in STANDARD_METADATA_KEYS}
        doc.set_metadata(empty_meta)

        # 2. Delete XML / XMP metadata stream
        try:
            doc.del_xml_metadata()
        except Exception as exc:
            logger.debug("del_xml_metadata raised non-fatal exception: %s", exc)

        # 3. Scrub catalog /Metadata and /PieceInfo keys if present at low-level xref
        try:
            cat_xref = doc.pdf_catalog()
            if cat_xref > 0:
                doc.xref_set_key(cat_xref, "Metadata", "null")
                doc.xref_set_key(cat_xref, "PieceInfo", "null")
        except Exception as exc:
            logger.debug("Catalog xref metadata scrub skipped: %s", exc)

        # 4. Also clear Info xref keys directly so even producer/dates do not linger
        try:
            trailer_info = doc. pdf_trailer()
            if trailer_info:
                for page in doc:
                    try:
                        doc.xref_set_key(page.xref, "Metadata", "null")
                        doc.xref_set_key(page.xref, "PieceInfo", "null")
                    except Exception:
                        pass
        except Exception:
            pass
        return

    # Selective metadata update: preserve existing fields when config field is blank
    current_meta = dict(doc.metadata or {})
    cleaned_meta: dict[str, str] = {}
    for key in STANDARD_METADATA_KEYS:
        val = current_meta.get(key)
        cleaned_meta[key] = str(val) if val else ""

    field_mapping = {
        "title": config.title,
        "author": config.author,
        "subject": config.subject,
        "keywords": config.keywords,
        "creator": config.creator,
        "producer": config.producer,
    }

    updated_any = False
    for meta_key, new_value in field_mapping.items():
        if new_value and new_value.strip():
            cleaned_meta[meta_key] = new_value.strip()
            updated_any = True

    if updated_any:
        logger.debug("Applying selective metadata updates to PDF.")
        doc.set_metadata(cleaned_meta)

