"""Dual-mode watermark configuration panel with debounced change hooks."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import colorchooser, filedialog, ttk
from typing import Callable, Optional

from src.models.job_config import WatermarkConfig, WatermarkLayout, WatermarkMode

WatermarkChangeCallback = Callable[[WatermarkConfig], None]


class WatermarkPanel(ttk.Frame):
    """UI panel for configuring text or PNG image watermarks with a 250ms debounce hook."""

    DEBOUNCE_MS = 250

    def __init__(
        self,
        parent: tk.Misc,
        on_change: Optional[WatermarkChangeCallback] = None,
    ) -> None:
        """Initialize watermark variables, dynamic sub-frames, and shared geometry controls."""
        super().__init__(parent)
        self.on_change = on_change
        self._debounce_after_id: Optional[str] = None

        # Mode variable
        self.mode_var = tk.StringVar(value=WatermarkMode.NONE.value)

        # Text Stamp variables
        self.text_var = tk.StringVar(value="CONFIDENTIAL")
        self.font_size_var = tk.IntVar(value=48)
        self._color_rgb: tuple[float, float, float] = (0.75, 0.12, 0.12)
        self._color_hex: str = "#BF1F1F"

        # Image Logo variables
        self.image_path_var = tk.StringVar(value="")
        self.scale_pct_var = tk.IntVar(value=35)

        # Shared Geometry variables
        self.opacity_pct_var = tk.IntVar(value=25)
        self.rotation_deg_var = tk.IntVar(value=45)
        self.layout_var = tk.StringVar(value=WatermarkLayout.DIAGONAL_STAMP.value)
        self.page_scope_var = tk.StringVar(value="all")  # "all" or "custom"
        self.custom_pages_var = tk.StringVar(value="1-3, 5")

        self._build_mode_selector()
        self._build_dynamic_mode_frames()
        self._build_shared_geometry_controls()
        self._attach_variable_traces()
        self._sync_mode_visibility()

    def _build_mode_selector(self) -> None:
        """Build the top radio button row switching between None, Text, and Image modes."""
        mode_bar = ttk.Frame(self)
        mode_bar.pack(side=tk.TOP, fill=tk.X, pady=(0, 8))

        ttk.Label(mode_bar, text="Watermark Mode:", style="Section.TLabel").pack(
            side=tk.LEFT, padx=(0, 12)
        )

        modes = [
            ("No Watermark", WatermarkMode.NONE.value),
            ("Text Stamp", WatermarkMode.TEXT.value),
            ("Image / Corporate Logo (PNG)", WatermarkMode.IMAGE.value),
        ]
        for label_text, val in modes:
            rb = ttk.Radiobutton(
                mode_bar,
                text=label_text,
                value=val,
                variable=self.mode_var,
                command=self._on_mode_switched,
            )
            rb.pack(side=tk.LEFT, padx=(0, 14))

    def _build_dynamic_mode_frames(self) -> None:
        """Create dynamic sub-frames for Text Stamp controls and Image Logo controls."""
        self.dynamic_container = ttk.Frame(self)
        self.dynamic_container.pack(side=tk.TOP, fill=tk.X, pady=(0, 8))

        # --- Sub-frame A: Text Stamp Controls ---
        self.text_frame = ttk.LabelFrame(
            self.dynamic_container,
            text=" Text Stamp Settings ",
            padding=8,
        )

        ttk.Label(self.text_frame, text="Stamp Text:").grid(
            row=0, column=0, sticky=tk.W, padx=(0, 6), pady=3
        )
        self.text_entry = ttk.Entry(self.text_frame, textvariable=self.text_var, width=28)
        self.text_entry.grid(row=0, column=1, sticky="ew", padx=(0, 14), pady=3)

        ttk.Label(self.text_frame, text="Font Size (pt):").grid(
            row=0, column=2, sticky=tk.W, padx=(0, 6), pady=3
        )
        self.font_spin = ttk.Spinbox(
            self.text_frame,
            from_=10,
            to=160,
            increment=2,
            textvariable=self.font_size_var,
            width=6,
            command=self._schedule_debounced_change,
        )
        self.font_spin.grid(row=0, column=3, sticky=tk.W, padx=(0, 14), pady=3)

        ttk.Label(self.text_frame, text="Color:").grid(
            row=0, column=4, sticky=tk.W, padx=(0, 6), pady=3
        )
        self.color_swatch = tk.Label(
            self.text_frame,
            bg=self._color_hex,
            width=3,
            relief=tk.SOLID,
            borderwidth=1,
        )
        self.color_swatch.grid(row=0, column=5, sticky=tk.W, padx=(0, 6), pady=3)

        self.btn_pick_color = ttk.Button(
            self.text_frame,
            text="Pick Color...",
            command=self._prompt_color_picker,
        )
        self.btn_pick_color.grid(row=0, column=6, sticky=tk.W, pady=3)
        self.text_frame.columnconfigure(1, weight=1)

        # --- Sub-frame B: Image / Corporate Logo Controls ---
        self.image_frame = ttk.LabelFrame(
            self.dynamic_container,
            text=" Corporate Logo / PNG Overlay Settings ",
            padding=8,
        )

        ttk.Label(self.image_frame, text="PNG File:").grid(
            row=0, column=0, sticky=tk.W, padx=(0, 6), pady=3
        )
        self.image_entry = ttk.Entry(
            self.image_frame,
            textvariable=self.image_path_var,
            width=34,
        )
        self.image_entry.grid(row=0, column=1, sticky="ew", padx=(0, 8), pady=3)

        self.btn_browse_png = ttk.Button(
            self.image_frame,
            text="Browse PNG...",
            style="Primary.TButton",
            command=self._prompt_browse_png,
        )
        self.btn_browse_png.grid(row=0, column=2, sticky=tk.W, padx=(0, 14), pady=3)

        ttk.Label(self.image_frame, text="Scale (% of Page):").grid(
            row=0, column=3, sticky=tk.W, padx=(0, 6), pady=3
        )
        self.scale_slider = ttk.Scale(
            self.image_frame,
            from_=10,
            to=90,
            orient=tk.HORIZONTAL,
            command=self._on_scale_slider_moved,
        )
        self.scale_slider.set(self.scale_pct_var.get())
        self.scale_slider.grid(row=0, column=4, sticky="ew", padx=(0, 6), pady=3)

        self.scale_val_lbl = ttk.Label(self.image_frame, text="35%", width=5)
        self.scale_val_lbl.grid(row=0, column=5, sticky=tk.W, pady=3)
        self.image_frame.columnconfigure(1, weight=1)

    def _build_shared_geometry_controls(self) -> None:
        """Create shared Opacity, Rotation, Layout, and Page Range controls."""
        self.shared_frame = ttk.LabelFrame(
            self,
            text=" Geometry, Layout & Target Page Range ",
            padding=8,
        )
        self.shared_frame.pack(side=tk.TOP, fill=tk.X)

        # Row 0: Opacity slider + Rotation slider + Quick 45° button
        ttk.Label(self.shared_frame, text="Opacity (5%–100%):").grid(
            row=0, column=0, sticky=tk.W, padx=(0, 6), pady=4
        )
        self.opacity_slider = ttk.Scale(
            self.shared_frame,
            from_=5,
            to=100,
            orient=tk.HORIZONTAL,
            command=self._on_opacity_slider_moved,
        )
        self.opacity_slider.set(self.opacity_pct_var.get())
        self.opacity_slider.grid(row=0, column=1, sticky="ew", padx=(0, 6), pady=4)

        self.opacity_val_lbl = ttk.Label(self.shared_frame, text="25%", width=5)
        self.opacity_val_lbl.grid(row=0, column=2, sticky=tk.W, padx=(0, 16), pady=4)

        ttk.Label(self.shared_frame, text="Rotation (-90° to +90°):").grid(
            row=0, column=3, sticky=tk.W, padx=(0, 6), pady=4
        )
        self.rotation_slider = ttk.Scale(
            self.shared_frame,
            from_=-90,
            to=90,
            orient=tk.HORIZONTAL,
            command=self._on_rotation_slider_moved,
        )
        self.rotation_slider.set(self.rotation_deg_var.get())
        self.rotation_slider.grid(row=0, column=4, sticky="ew", padx=(0, 6), pady=4)

        self.rotation_val_lbl = ttk.Label(self.shared_frame, text="45°", width=5)
        self.rotation_val_lbl.grid(row=0, column=5, sticky=tk.W, padx=(0, 6), pady=4)

        self.btn_preset_45 = ttk.Button(
            self.shared_frame,
            text="45°",
            width=4,
            command=lambda: self._set_rotation_preset(45),
        )
        self.btn_preset_45.grid(row=0, column=6, sticky=tk.W, padx=(0, 4), pady=4)

        self.btn_preset_0 = ttk.Button(
            self.shared_frame,
            text="0°",
            width=4,
            command=lambda: self._set_rotation_preset(0),
        )
        self.btn_preset_0.grid(row=0, column=7, sticky=tk.W, pady=4)

        # Row 1: Layout selector + Target Page Range selector
        ttk.Label(self.shared_frame, text="Layout Pattern:").grid(
            row=1, column=0, sticky=tk.W, padx=(0, 6), pady=4
        )
        layout_box = ttk.Frame(self.shared_frame)
        layout_box.grid(row=1, column=1, columnspan=2, sticky=tk.W, pady=4)

        layouts = [
            ("Single Center", WatermarkLayout.SINGLE_CENTER.value),
            ("Diagonal Stamp", WatermarkLayout.DIAGONAL_STAMP.value),
            ("Repeated Tiled Grid", WatermarkLayout.TILED_GRID.value),
        ]
        for lbl_text, val in layouts:
            ttk.Radiobutton(
                layout_box,
                text=lbl_text,
                value=val,
                variable=self.layout_var,
                command=self._schedule_debounced_change,
            ).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Label(self.shared_frame, text="Target Pages:").grid(
            row=1, column=3, sticky=tk.W, padx=(0, 6), pady=4
        )
        pages_box = ttk.Frame(self.shared_frame)
        pages_box.grid(row=1, column=4, columnspan=4, sticky="ew", pady=4)

        ttk.Radiobutton(
            pages_box,
            text="All Pages",
            value="all",
            variable=self.page_scope_var,
            command=self._on_page_scope_changed,
        ).pack(side=tk.LEFT, padx=(0, 8))

        ttk.Radiobutton(
            pages_box,
            text="Custom:",
            value="custom",
            variable=self.page_scope_var,
            command=self._on_page_scope_changed,
        ).pack(side=tk.LEFT, padx=(0, 4))

        self.custom_pages_entry = ttk.Entry(
            pages_box,
            textvariable=self.custom_pages_var,
            width=14,
            state=tk.DISABLED,
        )
        self.custom_pages_entry.pack(side=tk.LEFT)

        self.shared_frame.columnconfigure(1, weight=1)
        self.shared_frame.columnconfigure(4, weight=1)

    def _attach_variable_traces(self) -> None:
        """Attach debounced change listeners to text and entry variables."""
        for var in (
            self.text_var,
            self.font_size_var,
            self.image_path_var,
            self.custom_pages_var,
        ):
            var.trace_add("write", lambda *_: self._schedule_debounced_change())

    def _on_mode_switched(self) -> None:
        """Switch visible dynamic sub-frame and trigger a debounced preview update."""
        self._sync_mode_visibility()
        self._schedule_debounced_change()

    def _sync_mode_visibility(self) -> None:
        """Show either the Text frame or Image frame based on the active mode."""
        self.text_frame.pack_forget()
        self.image_frame.pack_forget()

        mode = self.mode_var.get()
        if mode == WatermarkMode.TEXT.value:
            self.text_frame.pack(side=tk.TOP, fill=tk.X)
        elif mode == WatermarkMode.IMAGE.value:
            self.image_frame.pack(side=tk.TOP, fill=tk.X)

    def _on_page_scope_changed(self) -> None:
        """Enable or disable the custom page range text entry."""
        if self.page_scope_var.get() == "custom":
            self.custom_pages_entry.configure(state=tk.NORMAL)
        else:
            self.custom_pages_entry.configure(state=tk.DISABLED)
        self._schedule_debounced_change()

    def _prompt_color_picker(self) -> None:
        """Open native color chooser dialog and convert RGB to normalized [0.0, 1.0] floats."""
        chosen = colorchooser.askcolor(
            color=self._color_hex,
            title="Select Watermark Text Color",
            parent=self,
        )
        if chosen and chosen[0] and chosen[1]:
            r, g, b = chosen[0]
            self._color_rgb = (
                round(float(r) / 255.0, 4),
                round(float(g) / 255.0, 4),
                round(float(b) / 255.0, 4),
            )
            self._color_hex = str(chosen[1])
            self.color_swatch.configure(bg=self._color_hex)
            self._schedule_debounced_change()

    def _prompt_browse_png(self) -> None:
        """Open file dialog to choose a transparent PNG logo image."""
        selected = filedialog.askopenfilename(
            parent=self,
            title="Select Corporate Logo / Watermark Image (PNG)",
            filetypes=[("PNG Images", "*.png"), ("All Images", "*.png;*.jpg;*.jpeg")],
        )
        if selected:
            self.image_path_var.set(str(Path(selected).resolve()))

    def _on_scale_slider_moved(self, raw_val: str) -> None:
        val = int(round(float(raw_val)))
        self.scale_pct_var.set(val)
        self.scale_val_lbl.configure(text=f"{val}%")
        self._schedule_debounced_change()

    def _on_opacity_slider_moved(self, raw_val: str) -> None:
        val = int(round(float(raw_val)))
        self.opacity_pct_var.set(val)
        self.opacity_val_lbl.configure(text=f"{val}%")
        self._schedule_debounced_change()

    def _on_rotation_slider_moved(self, raw_val: str) -> None:
        val = int(round(float(raw_val)))
        self.rotation_deg_var.set(val)
        self.rotation_val_lbl.configure(text=f"{val}°")
        self._schedule_debounced_change()

    def _set_rotation_preset(self, angle: int) -> None:
        self.rotation_deg_var.set(angle)
        self.rotation_slider.set(angle)
        self.rotation_val_lbl.configure(text=f"{angle}°")
        self._schedule_debounced_change()

    def _schedule_debounced_change(self) -> None:
        """Schedule a 250ms debounced invocation of `on_change`."""
        if self._debounce_after_id is not None:
            try:
                self.after_cancel(self._debounce_after_id)
            except Exception:
                pass
        self._debounce_after_id = self.after(self.DEBOUNCE_MS, self._emit_change)

    def _emit_change(self) -> None:
        """Invoke `on_change` with the current WatermarkConfig."""
        self._debounce_after_id = None
        if self.on_change is not None:
            self.on_change(self.get_config())

    def get_config(self) -> WatermarkConfig:
        """Build and return a validated WatermarkConfig from the current widget state."""
        try:
            mode = WatermarkMode(self.mode_var.get())
        except ValueError:
            mode = WatermarkMode.NONE

        try:
            layout = WatermarkLayout(self.layout_var.get())
        except ValueError:
            layout = WatermarkLayout.DIAGONAL_STAMP

        try:
            font_size = max(8, int(self.font_size_var.get()))
        except (ValueError, tk.TclError):
            font_size = 48

        target_pages = (
            "all"
            if self.page_scope_var.get() == "all"
            else (self.custom_pages_var.get().strip() or "all")
        )

        img_path = self.image_path_var.get().strip() or None

        return WatermarkConfig(
            mode=mode,
            text=self.text_var.get(),
            font_size=font_size,
            color_rgb=self._color_rgb,
            image_path=img_path,
            scale=max(0.05, min(1.0, float(self.scale_pct_var.get()) / 100.0)),
            opacity=max(0.05, min(1.0, float(self.opacity_pct_var.get()) / 100.0)),
            rotation=int(self.rotation_deg_var.get()),
            layout=layout,
            target_pages=target_pages,
        )
