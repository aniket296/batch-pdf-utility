"""Execution status and result payload models for individual batch PDF tasks."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class TaskStatus(str, Enum):
    """Lifecycle status of an individual PDF file processing task."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


@dataclass
class TaskResult:
    """Outcome record for a single processed PDF file in a batch job."""

    source_path: str
    output_path: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    pages_processed: int = 0
    error_message: Optional[str] = None
    duration_ms: float = 0.0
