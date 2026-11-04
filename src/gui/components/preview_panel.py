"""Live interactive multi-page PDF watermark preview canvas component."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import ttk
from typing import Optional

from PIL import ImageTk

from src.core.preview_engine import generate_preview_image, get_pdf_page_count
from src.gui.styles import COLOR_BORDER, COLOR_PRIMARY
from src.models.job_config import WatermarkConfig
from src.utils.logger import get_logger

logger = get_logger("preview_panel")


class PreviewPanel(ttk.Frame):
    """Canvas and page navigation panel displaying live watermarked PDF previews."""

    def __init__(self, parent: tk.Misc) -> None:
        """Initialize the preview canvas, file indicator, and page navigation bar."""
        super().__init__(parent)
        self._current_pdf_path: Optional[str] = None
        self._current_page_idx: int = 0
        self._total_pages: int = 1
        self._watermark_config: WatermarkConfig = WatermarkConfig()
        self._photo_image: Optional[ImageTk.PhotoImage] = None
        self._resize_after_id: Optional[str] = None

        self.file_label_var = tk.StringVar(value="Previewing: Synthetic A4 Sample Page")
        self.page_label_var = tk.StringVar(value="Page 1 of 1")

        self._build_ui()

    def _build_ui(self) -> None:
        """Build the header label, drop-shadow canvas, and bottom page navigation bar."""
        header = ttk.Frame(self)
        header.pack(side=tk.TOP, fill=tk.X, pady=(0, 6))

        file_lbl = ttk.Label(
            header,
            textvariable=self.file_label_var,
            style="Muted.TLabel",
        )
        file_lbl.pack(side=tk.LEFT)

        self.canvas = tk.Canvas(
            self,
            bg="#E2E8F0",
            highlightthickness=1,
            highlightbackground=COLOR_BORDER,
        )
        self.canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        nav_bar = ttk.Frame(self, padding=(0, 6, 0, 0))
        nav_bar.pack(side=tk.BOTTOM, fill=tk.X)

        self.btn_prev = ttk.Button(
            nav_bar,
            text="< Prev Page",
            width=12,
            command=self.prev_page,
            state=tk.DISABLED,
        )
        self.btn_prev.pack(side=tk.LEFT)

        self.page_counter_lbl = ttk.Label(
            nav_bar,
            textvariable=self.page_label_var,
            style="Section.TLabel",
            anchor=tk.CENTER,
        )
        self.page_counter_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.btn_next = ttk.Button(
            nav_bar,
            text="Next Page >",
            width=12,
            command=self.next_page,
            state=tk.DISABLED,
        )
        self.btn_next.pack(side=tk.RIGHT)

    def set_pdf_file(self, pdf_path: Optional[str]) -> None:
        """Load a new PDF file into the previewer and reset to page 1."""
        self._current_pdf_path = pdf_path
        self._current_page_idx = 0
        self._total_pages = get_pdf_page_count(pdf_path)

        if pdf_path and Path(pdf_path).is_file():
            self.file_label_var.set(f"Previewing: {Path(pdf_path).name}")
        else:
            self.file_label_var.set("Previewing: Synthetic A4 Sample Page")

        self.refresh_preview()

    def update_watermark_config(self, config: WatermarkConfig) -> None:
        """Update the active WatermarkConfig and re-render the current preview page."""
        self._watermark_config = config
        self.refresh_preview()

    def prev_page(self) -> None:
        """Navigate to the previous page of the currently selected PDF."""
        if self._current_page_idx > 0:
            self._current_page_idx -= 1
            self.refresh_preview()

    def next_page(self) -> None:
        """Navigate to the next page of the currently selected PDF."""
        if self._current_page_idx < self._total_pages - 1:
            self._current_page_idx += 1
            self.refresh_preview()

    def _on_canvas_configure(self, _event: tk.Event) -> None:  # type: ignore[type-arg]
        """Debounce canvas resize events to keep live rendering smooth."""
        if self._resize_after_id is not None:
            try:
                self.after_cancel(self._resize_after_id)
            except Exception:
                pass
        self._resize_after_id = self.after(120, self.refresh_preview)

    def refresh_preview(self) -> None:
        """Render the current page via `generate_preview_image` and draw onto the canvas."""
        self._resize_after_id = None
        self._total_pages = get_pdf_page_count(self._current_pdf_path)
        if self._current_page_idx >= self._total_pages:
            self._current_page_idx = max(0, self._total_pages - 1)

        # Update navigation buttons and counter
        self.page_label_var.set(
            f"Page {self._current_page_idx + 1} of {self._total_pages}"
        )
        self.btn_prev.configure(
            state=tk.NORMAL if self._current_page_idx > 0 else tk.DISABLED
        )
        self.btn_next.configure(
            state=(
                tk.NORMAL
                if self._current_page_idx < self._total_pages - 1
                else tk.DISABLED
            )
        )

        canvas_w = max(220, self.canvas.winfo_width() - 32)
        canvas_h = max(280, self.canvas.winfo_height() - 32)
        max_dim = max(240, min(canvas_w, canvas_h))

        try:
            pil_img = generate_preview_image(
                pdf_path=self._current_pdf_path,
                watermark_config=self._watermark_config,
                page_num=self._current_page_idx,
                max_dim=max_dim,
            )
            self._photo_image = ImageTk.PhotoImage(pil_img)

            self.canvas.delete("all")
            cx = max(self.canvas.winfo_width(), pil_img.width + 24) // 2
            cy = max(self.canvas.winfo_height(), pil_img.height + 24) // 2

            # Draw subtle drop-shadow backdrop behind the page
            half_w = pil_img.width // 2
            half_h = pil_img.height // 2
            self.canvas.create_rectangle(
                cx - half_w + 4,
                cy - half_h + 4,
                cx + half_w + 4,
                cy + half_h + 4,
                fill="#94A3B8",
                outline="",
            )
            self.canvas.create_rectangle(
                cx - half_w - 1,
                cy - half_h - 1,
                cx + half_w + 1,
                cy + half_h + 1,
                fill="#FFFFFF",
                outline=COLOR_PRIMARY,
            )
            self.canvas.create_image(cx, cy, image=self._photo_image, anchor=tk.CENTER)
        except Exception as exc:
            logger.error("Preview render error: %s", exc)

