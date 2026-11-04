"""Thread-safe rotating file logger and GUI queue handler for live log streaming."""

from __future__ import annotations

import logging
import queue
from logging.handlers import QueueHandler, RotatingFileHandler
from pathlib import Path
from typing import Optional

LOGGER_NAME = "batch_pdf_utility"
_LOG_QUEUE: queue.Queue[logging.LogRecord] = queue.Queue()
_INITIALIZED = False


def get_log_file_path(custom_dir: Optional[Path] = None) -> Path:
    """Return the path to ~/.batch_pdf_utility/app.log, falling back to local temp if needed."""
    base_dir = custom_dir or (Path.home() / ".batch_pdf_utility")
    try:
        base_dir.mkdir(parents=True, exist_ok=True)
        test_file = base_dir / ".write_check"
        test_file.touch(exist_ok=True)
        test_file.unlink(missing_ok=True)
        return base_dir / "app.log"
    except OSError:
        fallback_dir = Path.cwd() / ".batch_pdf_utility"
        fallback_dir.mkdir(parents=True, exist_ok=True)
        return fallback_dir / "app.log"


def setup_logger(level: int = logging.INFO, custom_dir: Optional[Path] = None) -> logging.Logger:
    """Configure and return the application-wide rotating file + queue logger."""
    global _INITIALIZED
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level)

    if _INITIALIZED and logger.handlers:
        return logger

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] [%(threadName)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 1. Rotating file handler writing to ~/.batch_pdf_utility/app.log
    try:
        log_path = get_log_file_path(custom_dir)
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=5 * 1024 * 1024,  # 5 MB
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except OSError:
        # Never crash if filesystem restricts log creation
        pass

    # 2. Thread-safe QueueHandler so the Tkinter GUI can poll log events
    queue_handler = QueueHandler(_LOG_QUEUE)
    queue_handler.setLevel(level)
    queue_handler.setFormatter(formatter)
    logger.addHandler(queue_handler)

    logger.propagate = False
    _INITIALIZED = True
    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Return a child logger attached to the configured root application logger."""
    setup_logger()
    if name:
        return logging.getLogger(f"{LOGGER_NAME}.{name}")
    return logging.getLogger(LOGGER_NAME)


def get_log_queue() -> queue.Queue[logging.LogRecord]:
    """Return the shared thread-safe queue containing formatted log records for the GUI."""
    setup_logger()
    return _LOG_QUEUE
