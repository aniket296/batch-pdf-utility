"""Strongly-typed domain models and configuration dataclasses."""

from src.models.job_config import (
    BatchJobConfig,
    CollisionStrategy,
    MetadataConfig,
    OutputConfig,
    WatermarkConfig,
    WatermarkLayout,
    WatermarkMode,
)
from src.models.task_result import TaskResult, TaskStatus

__all__ = [
    "BatchJobConfig",
    "CollisionStrategy",
    "MetadataConfig",
    "OutputConfig",
    "TaskResult",
    "TaskStatus",
    "WatermarkConfig",
    "WatermarkLayout",
    "WatermarkMode",
]
