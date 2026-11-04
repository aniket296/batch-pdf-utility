"""File system path resolution, collision protection, and page range parsing utilities."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from src.models.job_config import CollisionStrategy, OutputConfig


def resolve_output_path(
    source_path: str,
    output_config: OutputConfig,
    base_root: Optional[str] = None,
) -> str:
    """Resolve a collision-safe output file path that never overwrites the source file.

    Args:
        source_path: Path to the original input PDF file.
        output_config: Output directory, suffix, and collision strategy settings.
        base_root: Optional root directory when using MIRROR_TREE strategy.

    Returns:
        Absolute path string to a non-existing, collision-safe destination PDF path.
    """
    src = Path(source_path).resolve()
    stem = src.stem
    ext = src.suffix if src.suffix else ".pdf"
    suffix = output_config.suffix if output_config.suffix is not None else "_processed"

    strategy = output_config.strategy
    out_dir_raw = (output_config.output_dir or "").strip()

    if strategy == CollisionStrategy.DEDICATED_FOLDER and out_dir_raw:
        target_dir = Path(out_dir_raw).resolve()
        candidate_stem = f"{stem}{suffix}" if suffix else stem
    elif strategy == CollisionStrategy.MIRROR_TREE and out_dir_raw:
        target_root = Path(out_dir_raw).resolve()
        if base_root:
            try:
                rel_parent = src.parent.relative_to(Path(base_root).resolve())
                target_dir = target_root / rel_parent
            except ValueError:
                target_dir = target_root
        else:
            target_dir = target_root
        candidate_stem = f"{stem}{suffix}" if suffix else stem
    else:
        # Default: APPEND_SUFFIX in the source file's directory
        target_dir = src.parent
        safe_suffix = suffix if suffix else "_processed"
        candidate_stem = f"{stem}{safe_suffix}"

    target_dir.mkdir(parents=True, exist_ok=True)
    candidate = (target_dir / f"{candidate_stem}{ext}").resolve()

    # Never allow overwriting the source file even if target_dir == src.parent and suffix == ""
    if candidate == src:
        candidate_stem = f"{stem}_processed"
        candidate = (target_dir / f"{candidate_stem}{ext}").resolve()

    # Auto-increment (_1, _2, ...) if the destination file already exists or matches source
    counter = 1
    while candidate.exists() or candidate == src:
        candidate = (target_dir / f"{candidate_stem}_{counter}{ext}").resolve()
        counter += 1

    return str(candidate)


def parse_page_ranges(range_str: str, total_pages: int) -> list[int]:
    """Parse a 1-based page range specification into sorted, unique 0-based page indices.

    Supports:
        - "all" or "" or "*" -> all pages [0, 1, ..., total_pages - 1]
        - Comma-separated tokens: "1, 3, 5" -> [0, 2, 4]
        - Inclusive ranges: "1-3, 5" -> [0, 1, 2, 4]
        - Open-ended ranges: "3-" -> [2, ..., total_pages - 1]

    Args:
        range_str: User-supplied page range string.
        total_pages: Total number of pages in the PDF document.

    Returns:
        Sorted list of valid 0-based page indices within [0, total_pages - 1].

    Raises:
        ValueError: If range_str contains malformed tokens.
    """
    if total_pages <= 0:
        return []

    cleaned = (range_str or "").strip().lower()
    if not cleaned or cleaned in ("all", "*"):
        return list(range(total_pages))

    indices: set[int] = set()
    tokens = [tok.strip() for tok in cleaned.split(",") if tok.strip()]
    if not tokens:
        return list(range(total_pages))

    for token in tokens:
        if "-" in token:
            parts = token.split("-", 1)
            start_str, end_str = parts[0].strip(), parts[1].strip()
            if not start_str:
                raise ValueError(f"Invalid page range token: '{token}'")
            try:
                start_page = int(start_str)
                end_page = int(end_str) if end_str else total_pages
            except ValueError as exc:
                raise ValueError(f"Invalid page range numbers in '{token}'") from exc

            if start_page < 1 or end_page < start_page:
                raise ValueError(
                    f"Page range '{token}' must start at >= 1 and have end >= start."
                )

            for page_1based in range(start_page, min(end_page, total_pages) + 1):
                indices.add(page_1based - 1)
        else:
            try:
                page_1based = int(token)
            except ValueError as exc:
                raise ValueError(f"Invalid page number token: '{token}'") from exc

            if page_1based < 1:
                raise ValueError(f"Page number must be >= 1, got {page_1based}")
            if page_1based <= total_pages:
                indices.add(page_1based - 1)

    return sorted(indices)


def discover_pdf_files(directory: str, recursive: bool = True) -> list[str]:
    """Scan a directory and return sorted absolute paths to all PDF files."""
    root = Path(directory).resolve()
    if not root.is_dir():
        return []

    pattern = "**/*.pdf" if recursive else "*.pdf"
    matched: list[Path] = []
    for item in root.glob(pattern):
        if item.is_file() and item.suffix.lower() == ".pdf":
            matched.append(item.resolve())
    # Case-insensitive fallback check on Windows/POSIX
    if recursive:
        for dirpath, _, filenames in os.walk(root):
            for fname in filenames:
                if fname.lower().endswith(".pdf"):
                    matched.append((Path(dirpath) / fname).resolve())
    else:
        for item in root.iterdir():
            if item.is_file() and item.name.lower().endswith(".pdf"):
                matched.append(item.resolve())

    unique_sorted = sorted({str(p) for p in matched}, key=lambda s: s.lower())
    return unique_sorted

