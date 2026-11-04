"""Main Windows desktop application controller wiring queue, panels, preview, and worker threads."""

from __future__ import annotations

import queue
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any, Optional

from src.core.worker import BatchProcessor
from src.gui.components.file_table import FileQueueTable
from src.gui.components.metadata_panel import MetadataPanel
from src.gui.components.preview_panel import PreviewPanel
from src.gui.components.watermark_panel import WatermarkPanel
from src.gui.styles import (
    COLOR_BG,
    COLOR_SURFACE,
    FONT_MONO,
    apply_corporate_theme,
)
from src.models.job_config import BatchJobConfig, CollisionStrategy, OutputConfig, WatermarkMode
from src.models.task_result import TaskResult, TaskStatus
from src.utils.logger import get_log_queue, get_logger

logger = get_logger("gui.app")


class BatchPDFApp:
    """High-DPI native Windows Tkinter application controller and layout orchestrator."""

    POLL_INTERVAL_MS = 80

    def __init__(self, root: tk.Tk) -> None:
        """Initialize the main window, corporate theme, sub-panels, and event queues."""
        self.root = root
        self.root.title("Batch PDF Studio — Metadata Sanitizer & Watermarking Utility")
        self.root.geometry("1320x860")
        self.root.minsize(1080, 720)
        self.root.configure(bg=COLOR_BG)

        self.style = apply_corporate_theme(self.root)
        self.processor = BatchProcessor()

        # Thread-safe UI event queue for worker callbacks
        self._ui_event_queue: queue.Queue[tuple[str, Any]] = queue.Queue()
        self._log_queue = get_log_queue()

        # State variables
        self.status_var = tk.StringVar(value="Ready — 0 PDFs queued")
        self.progress_var = tk.DoubleVar(value=0.0)
        self._total_batch_files: int = 0
        self._completed_batch_files: int = 0
        self._is_running: bool = False
        self._log_visible: bool = False

        # Output Settings variables
        self.output_strategy_var = tk.StringVar(value=CollisionStrategy.APPEND_SUFFIX.value)
        self.output_suffix_var = tk.StringVar(value="_processed")
        self.output_dir_var = tk.StringVar(value="")

        self._build_header_banner()
        self._build_main_split_layout()
        self._build_collapsible_log_console()
        self._build_bottom_action_bar()

        # Render initial synthetic A4 preview and start polling loop
        self.root.after(100, self._initial_preview_sync)
        self.root.after(self.POLL_INTERVAL_MS, self._poll_queues)

    def _build_header_banner(self) -> None:
        """Build the corporate navy top branding bar."""
        banner = ttk.Frame(self.root, style="Header.TFrame", padding=(16, 10))
        banner.pack(side=tk.TOP, fill=tk.X)

        title_lbl = ttk.Label(
            banner,
            text="Batch PDF Metadata & Watermarking Studio",
            style="AppBanner.TLabel",
        )
        title_lbl.pack(side=tk.LEFT)

        subtitle_lbl = ttk.Label(
            banner,
            text="Enterprise Metadata Sanitization • Custom XMP/Info Injection • Vector Text & PNG Watermarking",
            style="AppSubBanner.TLabel",
        )
        subtitle_lbl.pack(side=tk.RIGHT)

    def _build_main_split_layout(self) -> None:
        """Build the left/right PanedWindow hosting queue, configuration tabs, and live preview."""
        self.main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_paned.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=12, pady=(8, 4))

        # Left Pane: File Queue + Configuration Notebook Tabs
        self.left_pane = ttk.Frame(self.main_paned, padding=(0, 0, 6, 0))
        self.main_paned.add(self.left_pane, weight=3)

        self.queue_container = ttk.LabelFrame(
            self.left_pane,
            text=" Batch PDF Queue ",
            padding=8,
        )
        self.queue_container.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=(0, 8))

        self.file_table = FileQueueTable(
            self.queue_container,
            on_selection_change=self._on_queue_selection_changed,
            on_queue_change=self._on_queue_count_changed,
        )
        self.file_table.pack(fill=tk.BOTH, expand=True)

        self.config_notebook = ttk.Notebook(self.left_pane)
        self.config_notebook.pack(side=tk.BOTTOM, fill=tk.X, expand=False)

        self.tab_metadata = ttk.Frame(self.config_notebook, padding=10)
        self.tab_watermark = ttk.Frame(self.config_notebook, padding=10)
        self.tab_output = ttk.Frame(self.config_notebook, padding=10)

        self.config_notebook.add(self.tab_metadata, text=" 1. Metadata & Sanitization ")
        self.config_notebook.add(self.tab_watermark, text=" 2. Watermark Designer ")
        self.config_notebook.add(self.tab_output, text=" 3. Output & Collision Strategy ")

        # Instantiate MetadataPanel & WatermarkPanel inside their tabs
        self.metadata_panel = MetadataPanel(
            self.tab_metadata,
            get_selected_pdf_callback=self.file_table.get_selected_file,
        )
        self.metadata_panel.pack(fill=tk.BOTH, expand=True)

        self.watermark_panel = WatermarkPanel(
            self.tab_watermark,
            on_change=self._on_watermark_config_changed,
        )
        self.watermark_panel.pack(fill=tk.BOTH, expand=True)

        self._build_output_settings_tab()

        # Right Pane: Live Interactive PDF Preview
        self.right_pane = ttk.Frame(self.main_paned, padding=(6, 0, 0, 0))
        self.main_paned.add(self.right_pane, weight=2)

        self.preview_container = ttk.LabelFrame(
            self.right_pane,
            text=" Live Watermark Preview ",
            padding=8,
        )
        self.preview_container.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.preview_panel = PreviewPanel(self.preview_container)
        self.preview_panel.pack(fill=tk.BOTH, expand=True)

    def _build_output_settings_tab(self) -> None:
        """Build the Output & Collision Strategy controls inside Tab 3."""
        strat_frame = ttk.LabelFrame(
            self.tab_output,
            text=" Destination & Collision Protection Strategy ",
            padding=8,
        )
        strat_frame.pack(side=tk.TOP, fill=tk.X, pady=(0, 8))

        rb_suffix = ttk.Radiobutton(
            strat_frame,
            text="Append Suffix in Source Folder (Never overwrites original files)",
            value=CollisionStrategy.APPEND_SUFFIX.value,
            variable=self.output_strategy_var,
            command=self._sync_output_controls,
        )
        rb_suffix.grid(row=0, column=0, columnspan=3, sticky=tk.W, pady=3)

        rb_dedicated = ttk.Radiobutton(
            strat_frame,
            text="Save to Dedicated Output Directory",
            value=CollisionStrategy.DEDICATED_FOLDER.value,
            variable=self.output_strategy_var,
            command=self._sync_output_controls,
        )
        rb_dedicated.grid(row=1, column=0, columnspan=3, sticky=tk.W, pady=3)

        rb_mirror = ttk.Radiobutton(
            strat_frame,
            text="Mirror Source Folder Tree inside Dedicated Output Directory",
            value=CollisionStrategy.MIRROR_TREE.value,
            variable=self.output_strategy_var,
            command=self._sync_output_controls,
        )
        rb_mirror.grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=3)

        ttk.Label(strat_frame, text="Filename Suffix:").grid(
            row=3, column=0, sticky=tk.W, padx=(0, 8), pady=(8, 4)
        )
        self.suffix_entry = ttk.Entry(
            strat_frame,
            textvariable=self.output_suffix_var,
            width=18,
        )
        self.suffix_entry.grid(row=3, column=1, sticky=tk.W, pady=(8, 4))

        ttk.Label(strat_frame, text="Output Folder:").grid(
            row=4, column=0, sticky=tk.W, padx=(0, 8), pady=4
        )
        self.output_dir_entry = ttk.Entry(
            strat_frame,
            textvariable=self.output_dir_var,
            width=46,
            state=tk.DISABLED,
        )
        self.output_dir_entry.grid(row=4, column=1, sticky="ew", padx=(0, 8), pady=4)

        self.btn_browse_output = ttk.Button(
            strat_frame,
            text="Browse Folder...",
            command=self._prompt_output_directory,
            state=tk.DISABLED,
        )
        self.btn_browse_output.grid(row=4, column=2, sticky=tk.W, pady=4)
        strat_frame.columnconfigure(1, weight=1)

    def _build_collapsible_log_console(self) -> None:
        """Build a collapsible real-time activity log panel above the bottom bar."""
        self.log_frame = ttk.LabelFrame(
            self.root,
            text=" Live Activity Log Console ",
            padding=6,
        )

        self.log_text = tk.Text(
            self.log_frame,
            height=6,
            bg=COLOR_SURFACE,
            fg="#1E293B",
            font=FONT_MONO,
            state=tk.DISABLED,
            wrap=tk.NONE,
        )
        log_scroll = ttk.Scrollbar(
            self.log_frame,
            orient=tk.VERTICAL,
            command=self.log_text.yview,
        )
        self.log_text.configure(yscrollcommand=log_scroll.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def _build_bottom_action_bar(self) -> None:
        """Build the bottom execution bar with progress bar, log toggle, and batch controls."""
        self.bottom_bar = ttk.Frame(self.root, padding=(12, 8))
        self.bottom_bar.pack(side=tk.BOTTOM, fill=tk.X)

        self.btn_toggle_log = ttk.Button(
            self.bottom_bar,
            text="Show Activity Log ▲",
            command=self.toggle_log_console,
        )
        self.btn_toggle_log.pack(side=tk.LEFT, padx=(0, 12))

        self.status_label = ttk.Label(
            self.bottom_bar,
            textvariable=self.status_var,
            style="Section.TLabel",
            width=34,
        )
        self.status_label.pack(side=tk.LEFT, padx=(0, 12))

        self.progress_bar = ttk.Progressbar(
            self.bottom_bar,
            variable=self.progress_var,
            maximum=100.0,
            mode="determinate",
            style="Horizontal.TProgressbar",
        )
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 12))

        self.cancel_btn = ttk.Button(
            self.bottom_bar,
            text="Cancel",
            style="Danger.TButton",
            state=tk.DISABLED,
            command=self.cancel_batch,
        )
        self.cancel_btn.pack(side=tk.RIGHT, padx=(6, 0))

        self.start_btn = ttk.Button(
            self.bottom_bar,
            text="▶ Start Batch Processing",
            style="Success.TButton",
            command=self.start_batch,
        )
        self.start_btn.pack(side=tk.RIGHT)

    def toggle_log_console(self) -> None:
        """Show or hide the collapsible real-time activity log console."""
        if self._log_visible:
            self.log_frame.pack_forget()
            self.btn_toggle_log.configure(text="Show Activity Log ▲")
            self._log_visible = False
        else:
            self.log_frame.pack(
                side=tk.BOTTOM,
                fill=tk.X,
                padx=12,
                pady=(0, 4),
                before=self.bottom_bar,
            )
            self.btn_toggle_log.configure(text="Hide Activity Log ▼")
            self._log_visible = True

    def _sync_output_controls(self) -> None:
        """Enable or disable the output directory selector based on collision strategy."""
        strat = self.output_strategy_var.get()
        needs_dir = strat in (
            CollisionStrategy.DEDICATED_FOLDER.value,
            CollisionStrategy.MIRROR_TREE.value,
        )
        state = tk.NORMAL if needs_dir else tk.DISABLED
        self.output_dir_entry.configure(state=state)
        self.btn_browse_output.configure(state=state)

    def _prompt_output_directory(self) -> None:
        """Open folder browser for Dedicated / Mirror output directory."""
        chosen = filedialog.askdirectory(
            parent=self.root,
            title="Select Dedicated Output Directory for Processed PDFs",
        )
        if chosen:
            self.output_dir_var.set(str(Path(chosen).resolve()))

    def _initial_preview_sync(self) -> None:
        """Perform initial watermark preview render on startup."""
        self.preview_panel.update_watermark_config(self.watermark_panel.get_config())

    def _on_queue_selection_changed(self, selected_path: Optional[str]) -> None:
        """Update the live preview panel whenever the user highlights a file in the queue."""
        self.preview_panel.set_pdf_file(selected_path)

    def _on_queue_count_changed(self, total_files: int) -> None:
        """Update status counter when files are added or removed."""
        if not self._is_running:
            noun = "PDF" if total_files == 1 else "PDFs"
            self.status_var.set(f"Ready — {total_files} {noun} queued")

    def _on_watermark_config_changed(self, wm_config: Any) -> None:
        """Update the live preview panel when watermark settings change."""
        self.preview_panel.update_watermark_config(wm_config)

    def get_output_config(self) -> OutputConfig:
        """Construct an OutputConfig from Tab 3 controls."""
        try:
            strategy = CollisionStrategy(self.output_strategy_var.get())
        except ValueError:
            strategy = CollisionStrategy.APPEND_SUFFIX

        return OutputConfig(
            output_dir=self.output_dir_var.get().strip() or None,
            suffix=self.output_suffix_var.get().strip(),
            strategy=strategy,
        )

    def start_batch(self) -> None:
        """Validate configuration and launch multi-threaded batch execution."""
        if self._is_running:
            return

        queued_files = self.file_table.get_queued_files()
        if not queued_files:
            messagebox.showwarning(
                "Queue Empty",
                "Please add at least one PDF file to the queue before starting the batch.",
                parent=self.root,
            )
            return

        wm_config = self.watermark_panel.get_config()
        if wm_config.mode == WatermarkMode.IMAGE:
            if not wm_config.image_path or not Path(wm_config.image_path).is_file():
                messagebox.showerror(
                    "Missing Watermark Image",
                    "Please select a valid PNG logo image file for Image Watermark mode.",
                    parent=self.root,
                )
                self.config_notebook.select(self.tab_watermark)
                return

        out_config = self.get_output_config()
        if out_config.strategy in (
            CollisionStrategy.DEDICATED_FOLDER,
            CollisionStrategy.MIRROR_TREE,
        ) and not out_config.output_dir:
            messagebox.showerror(
                "Output Directory Required",
                "Please choose a destination folder in the 'Output & Collision Strategy' tab.",
                parent=self.root,
            )
            self.config_notebook.select(self.tab_output)
            return

        job_config = BatchJobConfig(
            files=queued_files,
            metadata=self.metadata_panel.get_config(),
            watermark=wm_config,
            output=out_config,
        )

        self._is_running = True
        self._total_batch_files = len(queued_files)
        self._completed_batch_files = 0
        self.progress_var.set(0.0)
        self.status_var.set(f"Processing 0 / {self._total_batch_files} PDFs...")

        self.file_table.reset_all_statuses()
        self.file_table.set_controls_enabled(False)
        self.start_btn.configure(state=tk.DISABLED)
        self.cancel_btn.configure(state=tk.NORMAL)

        self.processor.start_batch_async(
            job_config=job_config,
            base_root=self.file_table.last_root_folder,
            on_file_start=lambda fp: self._ui_event_queue.put(("file_start", fp)),
            on_file_complete=lambda res: self._ui_event_queue.put(("file_complete", res)),
            on_batch_complete=lambda all_res: self._ui_event_queue.put(
                ("batch_complete", all_res)
            ),
        )

    def cancel_batch(self) -> None:
        """Signal the background worker pool to stop processing remaining files."""
        if self._is_running:
            self.processor.cancel()
            self.status_var.set("Cancelling active batch job...")
            self.cancel_btn.configure(state=tk.DISABLED)

    def _poll_queues(self) -> None:
        """Poll worker UI events and rotating logger queue via `root.after()`."""
        # 1. Drain worker callback events
        while True:
            try:
                event_type, payload = self._ui_event_queue.get_nowait()
            except queue.Empty:
                break

            if event_type == "file_start":
                self.file_table.update_file_status(str(payload), "Processing...")
            elif event_type == "file_complete":
                res: TaskResult = payload
                self._completed_batch_files += 1
                pct = (
                    (self._completed_batch_files / max(1, self._total_batch_files)) * 100.0
                )
                self.progress_var.set(pct)
                self.status_var.set(
                    f"Processing {self._completed_batch_files} / {self._total_batch_files} PDFs..."
                )
                if res.status == TaskStatus.SUCCESS:
                    self.file_table.update_file_status(
                        res.source_path,
                        "Completed",
                        res.output_path or "—",
                    )
                else:
                    self.file_table.update_file_status(
                        res.source_path,
                        "Failed",
                        f"Error: {res.error_message or 'Failed'}",
                    )
            elif event_type == "batch_complete":
                results: list[TaskResult] = payload
                self._on_batch_finished(results)

        # 2. Drain logger queue into collapsible activity log console
        while True:
            try:
                record = self._log_queue.get_nowait()
            except queue.Empty:
                break
            self._append_log_line(record.getMessage(), record.levelname)

        self.root.after(self.POLL_INTERVAL_MS, self._poll_queues)

    def _append_log_line(self, message: str, level: str = "INFO") -> None:
        """Append a formatted line to the activity log console widget."""
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"[{level}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def _on_batch_finished(self, results: list[TaskResult]) -> None:
        """Restore UI controls and display summary status upon batch completion."""
        self._is_running = False
        self.file_table.set_controls_enabled(True)
        self.start_btn.configure(state=tk.NORMAL)
        self.cancel_btn.configure(state=tk.DISABLED)

        succeeded = sum(1 for r in results if r.status == TaskStatus.SUCCESS)
        failed = len(results) - succeeded
        self.progress_var.set(100.0 if results else 0.0)
        self.status_var.set(
            f"Completed: {succeeded} succeeded, {failed} failed ({len(results)} total)"
        )
