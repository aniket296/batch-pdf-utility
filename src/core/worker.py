"""Multi-threaded batch PDF processing worker engine with cancellation and callbacks."""

from __future__ import annotations

import os
import threading
import time
import warnings
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable, Optional

with warnings.catch_warnings():
    warnings.simplefilter("ignore", FutureWarning)
    import fitz

from src.core.metadata_engine import apply_metadata
from src.core.watermark_engine import apply_watermark
from src.models.job_config import BatchJobConfig, WatermarkMode
from src.models.task_result import TaskResult, TaskStatus
from src.utils.file_ops import resolve_output_path
from src.utils.logger import get_logger

logger = get_logger("worker")

FileStartCallback = Callable[[str], None]
FileCompleteCallback = Callable[[TaskResult], None]
BatchCompleteCallback = Callable[[list[TaskResult]], None]


def _replace_with_retry(src: str, dst: str, attempts: int = 20, delay_s: float = 0.05) -> None:
    """os.replace with short retries: on Windows, antivirus/indexers transiently hold files."""
    for attempt in range(attempts):
        try:
            os.replace(src, dst)
            return
        except PermissionError:
            if attempt == attempts - 1:
                raise
            time.sleep(delay_s)


class BatchProcessor:
    """Executes batch PDF metadata and watermarking jobs across a thread pool."""

    def __init__(self, max_workers: Optional[int] = None) -> None:
        """Initialize the batch processor with a configurable thread pool size."""
        cpu_cores = os.cpu_count() or 4
        self.max_workers: int = max(1, int(max_workers or cpu_cores))
        self._stop_event = threading.Event()
        self._callback_lock = threading.Lock()
        self._active_thread: Optional[threading.Thread] = None

    @property
    def is_cancelled(self) -> bool:
        """Return True if cancellation has been requested."""
        return self._stop_event.is_set()

    def cancel(self) -> None:
        """Signal all running and queued worker tasks to stop gracefully."""
        logger.warning("Cancellation requested by user; signalling worker pool to stop.")
        self._stop_event.set()

    def reset(self) -> None:
        """Clear the cancellation event before starting a new batch."""
        self._stop_event.clear()

    def process_single_file(
        self,
        source_path: str,
        job_config: BatchJobConfig,
        base_root: Optional[str] = None,
        on_file_start: Optional[FileStartCallback] = None,
        on_file_complete: Optional[FileCompleteCallback] = None,
    ) -> TaskResult:
        """Process a single PDF file: apply metadata, apply watermark, and save cleanly."""
        start_time = time.perf_counter()

        if self._stop_event.is_set():
            cancelled_res = TaskResult(
                source_path=source_path,
                output_path=None,
                status=TaskStatus.FAILED,
                pages_processed=0,
                error_message="Cancelled before execution.",
                duration_ms=0.0,
            )
            return cancelled_res

        if on_file_start is not None:
            with self._callback_lock:
                try:
                    on_file_start(source_path)
                except Exception as cb_err:
                    logger.debug("on_file_start callback error: %s", cb_err)

        logger.info("Processing PDF: %s", source_path)

        reserved_output: Optional[str] = None
        try:
            src_file = Path(source_path)
            if not src_file.is_file():
                raise FileNotFoundError(f"Source PDF file does not exist: {source_path}")

            output_path = resolve_output_path(
                source_path=source_path,
                output_config=job_config.output,
                base_root=base_root,
                reserve=True,
            )
            reserved_output = output_path

            with fitz.open(str(src_file)) as doc:
                if doc.is_encrypted:
                    raise PermissionError("PDF is password-protected / encrypted.")

                total_pages = len(doc)

                if self._stop_event.is_set():
                    raise InterruptedError("Batch job cancelled during processing.")

                # 1. Apply metadata changes or full XMP/Info wipe
                apply_metadata(doc, job_config.metadata)

                if self._stop_event.is_set():
                    raise InterruptedError("Batch job cancelled during processing.")

                # 2. Apply watermark if enabled
                if job_config.watermark.mode != WatermarkMode.NONE:
                    pages_touched = apply_watermark(doc, job_config.watermark)
                else:
                    pages_touched = total_pages

                if self._stop_event.is_set():
                    raise InterruptedError("Batch job cancelled before saving output.")

                # 3. Save with full garbage collection and stream deflation. Write to a temp
                # file and atomically replace the reserved placeholder so concurrent workers
                # never observe a deleted/half-written destination.
                temp_output = f"{output_path}.tmp"
                doc.save(temp_output, garbage=4, deflate=True)
            _replace_with_retry(temp_output, output_path)

            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            result = TaskResult(
                source_path=source_path,
                output_path=output_path,
                status=TaskStatus.SUCCESS,
                pages_processed=pages_touched if pages_touched > 0 else total_pages,
                error_message=None,
                duration_ms=round(elapsed_ms, 2),
            )
            logger.info(
                "Completed PDF: %s -> %s (%d pages, %.1f ms)",
                Path(source_path).name,
                output_path,
                result.pages_processed,
                result.duration_ms,
            )

        except Exception as exc:
            if reserved_output is not None:
                # Remove the empty placeholder (or partial file) left by a failed/cancelled job.
                try:
                    Path(reserved_output).unlink(missing_ok=True)
                    Path(f"{reserved_output}.tmp").unlink(missing_ok=True)
                except OSError as cleanup_err:
                    logger.warning("Could not remove %s: %s", reserved_output, cleanup_err)
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            result = TaskResult(
                source_path=source_path,
                output_path=None,
                status=TaskStatus.FAILED,
                pages_processed=0,
                error_message=str(exc),
                duration_ms=round(elapsed_ms, 2),
            )
            logger.error("Failed processing %s: %s", source_path, exc)

        if on_file_complete is not None:
            with self._callback_lock:
                try:
                    on_file_complete(result)
                except Exception as cb_err:
                    logger.debug("on_file_complete callback error: %s", cb_err)

        return result

    def run_batch(
        self,
        job_config: BatchJobConfig,
        base_root: Optional[str] = None,
        on_file_start: Optional[FileStartCallback] = None,
        on_file_complete: Optional[FileCompleteCallback] = None,
        on_batch_complete: Optional[BatchCompleteCallback] = None,
    ) -> list[TaskResult]:
        """Run a batch job across the ThreadPoolExecutor and return ordered TaskResults."""
        self.reset()
        files = list(job_config.files)
        if not files:
            if on_batch_complete is not None:
                on_batch_complete([])
            return []

        logger.info(
            "Starting batch job for %d file(s) with %d worker thread(s).",
            len(files),
            self.max_workers,
        )

        results_by_index: dict[int, TaskResult] = {}
        worker_count = min(self.max_workers, len(files))

        with ThreadPoolExecutor(
            max_workers=worker_count,
            thread_name_prefix="PDFWorker",
        ) as executor:
            future_to_idx: dict[Future[TaskResult], int] = {}
            for idx, file_path in enumerate(files):
                if self._stop_event.is_set():
                    cancelled_result = TaskResult(
                        source_path=file_path,
                        output_path=None,
                        status=TaskStatus.FAILED,
                        pages_processed=0,
                        error_message="Cancelled before execution.",
                        duration_ms=0.0,
                    )
                    results_by_index[idx] = cancelled_result
                    if on_file_complete is not None:
                        with self._callback_lock:
                            on_file_complete(cancelled_result)
                    continue

                fut = executor.submit(
                    self.process_single_file,
                    file_path,
                    job_config,
                    base_root,
                    on_file_start,
                    on_file_complete,
                )
                future_to_idx[fut] = idx

            for fut in as_completed(future_to_idx):
                idx = future_to_idx[fut]
                try:
                    results_by_index[idx] = fut.result()
                except Exception as exc:
                    fallback = TaskResult(
                        source_path=files[idx],
                        output_path=None,
                        status=TaskStatus.FAILED,
                        pages_processed=0,
                        error_message=str(exc),
                        duration_ms=0.0,
                    )
                    results_by_index[idx] = fallback

        ordered_results = [results_by_index[i] for i in range(len(files))]

        success_count = sum(1 for r in ordered_results if r.status == TaskStatus.SUCCESS)
        fail_count = len(ordered_results) - success_count
        logger.info(
            "Batch job finished: %d succeeded, %d failed/cancelled.",
            success_count,
            fail_count,
        )

        if on_batch_complete is not None:
            with self._callback_lock:
                try:
                    on_batch_complete(ordered_results)
                except Exception as cb_err:
                    logger.debug("on_batch_complete callback error: %s", cb_err)

        return ordered_results

    def start_batch_async(
        self,
        job_config: BatchJobConfig,
        base_root: Optional[str] = None,
        on_file_start: Optional[FileStartCallback] = None,
        on_file_complete: Optional[FileCompleteCallback] = None,
        on_batch_complete: Optional[BatchCompleteCallback] = None,
    ) -> threading.Thread:
        """Launch `run_batch` on a background daemon thread so the GUI stays responsive."""
        thread = threading.Thread(
            target=self.run_batch,
            kwargs={
                "job_config": job_config,
                "base_root": base_root,
                "on_file_start": on_file_start,
                "on_file_complete": on_file_complete,
                "on_batch_complete": on_batch_complete,
            },
            name="BatchCoordinatorThread",
            daemon=True,
        )
        self._active_thread = thread
        thread.start()
        return thread

