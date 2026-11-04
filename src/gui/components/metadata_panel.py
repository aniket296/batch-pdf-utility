"""Metadata configuration and full XMP/Info sanitization panel."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Callable, Optional

from src.core.metadata_engine import read_metadata
from src.models.job_config import MetadataConfig
from src.utils.logger import get_logger

logger = get_logger("metadata_panel")


class MetadataPanel(ttk.Frame):
    """Form panel for editing PDF document metadata or enabling complete sanitization."""

    def __init__(
        self,
        parent: tk.Misc,
        get_selected_pdf_callback: Optional[Callable[[], Optional[str]]] = None,
    ) -> None:
        """Initialize the metadata inputs, wipe checkbox, and inspector button."""
        super().__init__(parent)
        self.get_selected_pdf_callback = get_selected_pdf_callback

        self.title_var = tk.StringVar(value="")
        self.author_var = tk.StringVar(value="")
        self.subject_var = tk.StringVar(value="")
        self.keywords_var = tk.StringVar(value="")
        self.creator_var = tk.StringVar(value="")
        self.producer_var = tk.StringVar(value="")
        self.wipe_all_var = tk.BooleanVar(value=False)

        self._entries: list[ttk.Entry] = []

        self._build_ui()

    def _build_ui(self) -> None:
        """Build the metadata inspector toolbar, wipe toggle, and 2-column form grid."""
        top_bar = ttk.Frame(self)
        top_bar.pack(side=tk.TOP, fill=tk.X, pady=(0, 8))

        self.wipe_checkbox = ttk.Checkbutton(
            top_bar,
            text="Sanitize / Wipe All Hidden Metadata & XMP History",
            variable=self.wipe_all_var,
            style="Warning.TCheckbutton",
            command=self._on_wipe_toggled,
        )
        self.wipe_checkbox.pack(side=tk.LEFT)

        self.btn_clear_fields = ttk.Button(
            top_bar,
            text="Clear Fields",
            command=self.clear_fields,
        )
        self.btn_clear_fields.pack(side=tk.RIGHT, padx=(6, 0))

        self.btn_load_selected = ttk.Button(
            top_bar,
            text="Load Metadata from Selected PDF",
            style="Primary.TButton",
            command=self.load_from_selected_pdf,
        )
        self.btn_load_selected.pack(side=tk.RIGHT)

        hint_lbl = ttk.Label(
            self,
            text="Leave any field blank to preserve the original value in each PDF (unless Sanitize / Wipe All is checked).",
            style="Muted.TLabel",
        )
        hint_lbl.pack(side=tk.TOP, anchor=tk.W, pady=(0, 8))

        form = ttk.Frame(self)
        form.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        fields = [
            ("Title:", self.title_var, 0, 0),
            ("Author:", self.author_var, 0, 2),
            ("Subject:", self.subject_var, 1, 0),
            ("Keywords:", self.keywords_var, 1, 2),
            ("Creator App:", self.creator_var, 2, 0),
            ("PDF Producer:", self.producer_var, 2, 2),
        ]

        for label_text, var, row_idx, col_idx in fields:
            lbl = ttk.Label(form, text=label_text)
            lbl.grid(row=row_idx, column=col_idx, sticky=tk.W, padx=(0, 8), pady=5)

            entry = ttk.Entry(form, textvariable=var, width=32)
            entry.grid(
                row=row_idx,
                column=col_idx + 1,
                sticky="ew",
                padx=(0, 16 if col_idx == 0 else 0),
                pady=5,
            )
            self._entries.append(entry)

        form.columnconfigure(1, weight=1)
        form.columnconfigure(3, weight=1)

    def _on_wipe_toggled(self) -> None:
        """Disable text inputs visually when full metadata sanitization is checked."""
        state = tk.DISABLED if self.wipe_all_var.get() else tk.NORMAL
        for entry in self._entries:
            entry.configure(state=state)

    def clear_fields(self) -> None:
        """Reset all metadata text fields to empty strings."""
        self.title_var.set("")
        self.author_var.set("")
        self.subject_var.set("")
        self.keywords_var.set("")
        self.creator_var.set("")
        self.producer_var.set("")

    def load_from_selected_pdf(self) -> None:
        """Populate metadata fields from the currently selected PDF in the queue."""
        selected_path = (
            self.get_selected_pdf_callback() if self.get_selected_pdf_callback else None
        )
        if not selected_path or not Path(selected_path).is_file():
            messagebox.showinfo(
                "No PDF Selected",
                "Please select a PDF file in the queue first to inspect its metadata.",
                parent=self,
            )
            return

        try:
            meta = read_metadata(selected_path)
            if self.wipe_all_var.get():
                self.wipe_all_var.set(False)
                self._on_wipe_toggled()

            self.title_var.set(meta.get("title", ""))
            self.author_var.set(meta.get("author", ""))
            self.subject_var.set(meta.get("subject", ""))
            self.keywords_var.set(meta.get("keywords", ""))
            self.creator_var.set(meta.get("creator", ""))
            self.producer_var.set(meta.get("producer", ""))
            logger.info("Loaded metadata from '%s'.", Path(selected_path).name)
        except Exception as exc:
            logger.error("Failed to read metadata from '%s': %s", selected_path, exc)
            messagebox.showerror(
                "Metadata Read Error",
                f"Could not read metadata from file:\n{exc}",
                parent=self,
            )

    def get_config(self) -> MetadataConfig:
        """Build and return a strongly-typed MetadataConfig from current form values."""
        return MetadataConfig(
            author=self.author_var.get().strip(),
            title=self.title_var.get().strip(),
            subject=self.subject_var.get().strip(),
            keywords=self.keywords_var.get().strip(),
            creator=self.creator_var.get().strip(),
            producer=self.producer_var.get().strip(),
            wipe_all=bool(self.wipe_all_var.get()),
        )

