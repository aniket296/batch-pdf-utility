"""Main Windows desktop application shell for Batch PDF Metadata & Watermarking Utility."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from src.gui.styles import COLOR_BG, COLOR_PRIMARY, COLOR_SURFACE, apply_corporate_theme


class BatchPDFApp:
    """High-DPI native Windows Tkinter application controller and layout shell."""

    def __init__(self, root: tk.Tk) -> None:
        """Initialize the main application window, theme, and split-pane layout."""
        self.root = root
        self.root.title("Batch PDF Studio — Metadata Sanitizer & Watermarking Utility")
        self.root.geometry("1280x820")
        self.root.minsize(1040, 700)
        self.root.configure(bg=COLOR_BG)

        self.style = apply_corporate_theme(self.root)

        self.status_var = tk.StringVar(value="Ready — 0 files queued")
        self.progress_var = tk.DoubleVar(value=0.0)

        self._build_header_banner()
        self._build_main_split_layout()
        self._build_bottom_action_bar()

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
        """Build the left/right PanedWindow hosting queue/tabs and live visual preview."""
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

        self.config_notebook = ttk.Notebook(self.left_pane)
        self.config_notebook.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=False)

        self.tab_metadata = ttk.Frame(self.config_notebook, padding=10)
        self.tab_watermark = ttk.Frame(self.config_notebook, padding=10)
        self.tab_output = ttk.Frame(self.config_notebook, padding=10)

        self.config_notebook.add(self.tab_metadata, text=" 1. Metadata & Sanitization ")
        self.config_notebook.add(self.tab_watermark, text=" 2. Watermark Designer ")
        self.config_notebook.add(self.tab_output, text=" 3. Output & Collision Strategy ")

        # Right Pane: Live Visual Preview Container
        self.right_pane = ttk.Frame(self.main_paned, padding=(6, 0, 0, 0))
        self.main_paned.add(self.right_pane, weight=2)

        self.preview_container = ttk.LabelFrame(
            self.right_pane,
            text=" Live Watermark Preview ",
            padding=8,
        )
        self.preview_container.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.preview_placeholder = tk.Canvas(
            self.preview_container,
            bg=COLOR_SURFACE,
            highlightthickness=1,
            highlightbackground=COLOR_PRIMARY,
        )
        self.preview_placeholder.pack(fill=tk.BOTH, expand=True)

    def _build_bottom_action_bar(self) -> None:
        """Build the bottom execution bar with progress bar, status counter, and buttons."""
        bottom_bar = ttk.Frame(self.root, padding=(12, 8))
        bottom_bar.pack(side=tk.BOTTOM, fill=tk.X)

        self.status_label = ttk.Label(
            bottom_bar,
            textvariable=self.status_var,
            style="Section.TLabel",
            width=36,
        )
        self.status_label.pack(side=tk.LEFT, padx=(0, 12))

        self.progress_bar = ttk.Progressbar(
            bottom_bar,
            variable=self.progress_var,
            maximum=100.0,
            mode="determinate",
            style="Horizontal.TProgressbar",
        )
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 12))

        self.cancel_btn = ttk.Button(
            bottom_bar,
            text="Cancel",
            style="Danger.TButton",
            state=tk.DISABLED,
        )
        self.cancel_btn.pack(side=tk.RIGHT, padx=(6, 0))

        self.start_btn = ttk.Button(
            bottom_bar,
            text="▶ Start Batch Processing",
            style="Success.TButton",
        )
        self.start_btn.pack(side=tk.RIGHT)
