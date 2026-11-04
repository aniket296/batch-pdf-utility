"""Configuration dataclasses and enums for batch PDF metadata and watermarking jobs."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class WatermarkMode(str, Enum):
    """Operational mode for PDF watermarking."""

    NONE = "NONE"
    TEXT = "TEXT"
    IMAGE = "IMAGE"


class WatermarkLayout(str, Enum):
    """Geometric layout pattern for applying watermarks onto PDF pages."""

    SINGLE_CENTER = "SINGLE_CENTER"
    DIAGONAL_STAMP = "DIAGONAL_STAMP"
    TILED_GRID = "TILED_GRID"


class CollisionStrategy(str, Enum):
    """Output file path resolution and collision strategy."""

    APPEND_SUFFIX = "APPEND_SUFFIX"
    DEDICATED_FOLDER = "DEDICATED_FOLDER"
    MIRROR_TREE = "MIRROR_TREE"


@dataclass
class MetadataConfig:
    """Configuration for PDF document metadata updates or complete sanitization."""

    author: str = ""
    title: str = ""
    subject: str = ""
    keywords: str = ""
    creator: str = ""
    producer: str = ""
    wipe_all: bool = False

    def has_updates(self) -> bool:
        """Return True if wipe_all is active or any metadata field is non-empty."""
        if self.wipe_all:
            return True
        return any(
            bool(val.strip())
            for val in (
                self.author,
                self.title,
                self.subject,
                self.keywords,
                self.creator,
                self.producer,
            )
        )


@dataclass
class WatermarkConfig:
    """Configuration for text or transparent PNG image watermarking."""

    mode: WatermarkMode = WatermarkMode.NONE
    text: str = "CONFIDENTIAL"
    font_size: int = 48
    color_rgb: tuple[float, float, float] = (0.45, 0.45, 0.45)
    image_path: Optional[str] = None
    scale: float = 0.35
    opacity: float = 0.25
    rotation: int = 45
    layout: WatermarkLayout = WatermarkLayout.DIAGONAL_STAMP
    target_pages: str = "all"

    def __post_init__(self) -> None:
        """Normalize and validate numeric bounds for watermark geometry."""
        self.opacity = max(0.05, min(1.0, float(self.opacity)))
        self.scale = max(0.05, min(3.0, float(self.scale)))
        self.font_size = max(6, int(self.font_size))
        self.rotation = int(self.rotation)
        if len(self.color_rgb) != 3:
            raise ValueError("color_rgb must be a 3-tuple of (R, G, B) floats in [0.0, 1.0].")
        self.color_rgb = (
            max(0.0, min(1.0, float(self.color_rgb[0]))),
            max(0.0, min(1.0, float(self.color_rgb[1]))),
            max(0.0, min(1.0, float(self.color_rgb[2]))),
        )


@dataclass
class OutputConfig:
    """Configuration for output directory and filename collision handling."""

    output_dir: Optional[str] = None
    suffix: str = "_processed"
    strategy: CollisionStrategy = CollisionStrategy.APPEND_SUFFIX


@dataclass
class BatchJobConfig:
    """Top-level configuration aggregating files, metadata, watermark, and output settings."""

    files: list[str] = field(default_factory=list)
    metadata: MetadataConfig = field(default_factory=MetadataConfig)
    watermark: WatermarkConfig = field(default_factory=WatermarkConfig)
    output: OutputConfig = field(default_factory=OutputConfig)

