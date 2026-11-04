"""Slate & Navy corporate ttk styling system for the Windows desktop interface."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

# Corporate Color Palette
COLOR_PRIMARY = "#1B365D"       # Deep Corporate Navy
COLOR_PRIMARY_HOVER = "#264B80" # Lighter Navy for active states
COLOR_BG = "#F4F6F9"            # Soft Slate Background
COLOR_SURFACE = "#FFFFFF"       # Pure White Card/Surface
COLOR_TEXT = "#2C3E50"          # Dark Slate Typography
COLOR_TEXT_MUTED = "#64748B"    # Muted Secondary Text
COLOR_BORDER = "#CBD5E1"        # Subtle Divider Border
COLOR_SUCCESS = "#10B981"       # Emerald Green Action/Success
COLOR_SUCCESS_HOVER = "#059669"
COLOR_DANGER = "#EF4444"        # Crimson Danger/Cancel
COLOR_DANGER_HOVER = "#DC2626"
COLOR_WARNING_BG = "#FEF2F2"    # Soft Alert Tinted Background

FONT_FAMILY = "Segoe UI"
FONT_HEADER = (FONT_FAMILY, 13, "bold")
FONT_SUBHEADER = (FONT_FAMILY, 10, "bold")
FONT_BODY = (FONT_FAMILY, 9)
FONT_BODY_BOLD = (FONT_FAMILY, 9, "bold")
FONT_SMALL = (FONT_FAMILY, 8)
FONT_MONO = ("Consolas", 9)


def apply_corporate_theme(root: tk.Misc) -> ttk.Style:
    """Configure and apply the Slate & Navy ttk 'clam' theme onto `root`."""
    style = ttk.Style(root)
    if "clam" in style.theme_names():
        style.theme_use("clam")

    root.option_add("*Font", "{Segoe UI} 9")

    # Base Frame & Label styles
    style.configure(".", background=COLOR_BG, foreground=COLOR_TEXT, font=FONT_BODY)
    style.configure("TFrame", background=COLOR_BG)
    style.configure("Surface.TFrame", background=COLOR_SURFACE)
    style.configure("Header.TFrame", background=COLOR_PRIMARY)

    style.configure("TLabel", background=COLOR_BG, foreground=COLOR_TEXT, font=FONT_BODY)
    style.configure("Surface.TLabel", background=COLOR_SURFACE, foreground=COLOR_TEXT, font=FONT_BODY)
    style.configure("Muted.TLabel", background=COLOR_BG, foreground=COLOR_TEXT_MUTED, font=FONT_SMALL)
    style.configure("Section.TLabel", background=COLOR_BG, foreground=COLOR_PRIMARY, font=FONT_SUBHEADER)
    style.configure(
        "AppBanner.TLabel",
        background=COLOR_PRIMARY,
        foreground="#FFFFFF",
        font=FONT_HEADER,
    )
    style.configure(
        "AppSubBanner.TLabel",
        background=COLOR_PRIMARY,
        foreground="#DCE4F2",
        font=FONT_BODY,
    )

    # LabelFrame
    style.configure(
        "TLabelframe",
        background=COLOR_BG,
        bordercolor=COLOR_BORDER,
        lightcolor=COLOR_BORDER,
        darkcolor=COLOR_BORDER,
        relief="solid",
        borderwidth=1,
    )
    style.configure(
        "TLabelframe.Label",
        background=COLOR_BG,
        foreground=COLOR_PRIMARY,
        font=FONT_SUBHEADER,
    )

    # Notebook / Tabs
    style.configure(
        "TNotebook",
        background=COLOR_BG,
        bordercolor=COLOR_BORDER,
        tabmargins=[2, 4, 2, 0],
    )
    style.configure(
        "TNotebook.Tab",
        background="#E2E8F0",
        foreground=COLOR_TEXT,
        padding=[14, 6],
        font=FONT_BODY_BOLD,
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", COLOR_PRIMARY), ("active", "#CBD5E1")],
        foreground=[("selected", "#FFFFFF"), ("active", COLOR_PRIMARY)],
    )

    # Buttons
    style.configure(
        "TButton",
        background="#E2E8F0",
        foreground=COLOR_TEXT,
        bordercolor=COLOR_BORDER,
        focusthickness=1,
        padding=[10, 5],
        font=FONT_BODY,
    )
    style.map(
        "TButton",
        background=[("active", "#CBD5E1"), ("disabled", "#F1F5F9")],
        foreground=[("disabled", "#94A3B8")],
    )

    style.configure(
        "Primary.TButton",
        background=COLOR_PRIMARY,
        foreground="#FFFFFF",
        bordercolor=COLOR_PRIMARY,
        padding=[12, 6],
        font=FONT_BODY_BOLD,
    )
    style.map(
        "Primary.TButton",
        background=[("active", COLOR_PRIMARY_HOVER), ("disabled", "#94A3B8")],
        foreground=[("disabled", "#E2E8F0")],
    )

    style.configure(
        "Success.TButton",
        background=COLOR_SUCCESS,
        foreground="#FFFFFF",
        bordercolor=COLOR_SUCCESS,
        padding=[16, 7],
        font=FONT_SUBHEADER,
    )
    style.map(
        "Success.TButton",
        background=[("active", COLOR_SUCCESS_HOVER), ("disabled", "#94A3B8")],
        foreground=[("disabled", "#E2E8F0")],
    )

    style.configure(
        "Danger.TButton",
        background=COLOR_DANGER,
        foreground="#FFFFFF",
        bordercolor=COLOR_DANGER,
        padding=[12, 7],
        font=FONT_BODY_BOLD,
    )
    style.map(
        "Danger.TButton",
        background=[("active", COLOR_DANGER_HOVER), ("disabled", "#FCA5A5")],
        foreground=[("disabled", "#FEE2E2")],
    )

    # Entries, Spinboxes, Checkbuttons, Radiobuttons
    style.configure(
        "TEntry",
        fieldbackground=COLOR_SURFACE,
        foreground=COLOR_TEXT,
        bordercolor=COLOR_BORDER,
        padding=4,
    )
    style.map(
        "TEntry",
        fieldbackground=[("disabled", "#E2E8F0"), ("readonly", "#F8FAFC")],
        foreground=[("disabled", "#94A3B8")],
    )

    style.configure(
        "TCheckbutton",
        background=COLOR_BG,
        foreground=COLOR_TEXT,
        font=FONT_BODY,
    )
    style.configure(
        "Warning.TCheckbutton",
        background=COLOR_BG,
        foreground=COLOR_DANGER,
        font=FONT_BODY_BOLD,
    )
    style.configure(
        "TRadiobutton",
        background=COLOR_BG,
        foreground=COLOR_TEXT,
        font=FONT_BODY,
    )

    # Treeview
    style.configure(
        "Treeview",
        background=COLOR_SURFACE,
        fieldbackground=COLOR_SURFACE,
        foreground=COLOR_TEXT,
        rowheight=26,
        bordercolor=COLOR_BORDER,
        font=FONT_BODY,
    )
    style.configure(
        "Treeview.Heading",
        background=COLOR_PRIMARY,
        foreground="#FFFFFF",
        relief="flat",
        padding=[6, 5],
        font=FONT_BODY_BOLD,
    )
    style.map(
        "Treeview.Heading",
        background=[("active", COLOR_PRIMARY_HOVER)],
    )
    style.map(
        "Treeview",
        background=[("selected", "#DBEAFE")],
        foreground=[("selected", COLOR_PRIMARY)],
    )

    # Progressbar
    style.configure(
        "Horizontal.TProgressbar",
        troughcolor="#E2E8F0",
        background=COLOR_SUCCESS,
        bordercolor=COLOR_BORDER,
        lightcolor=COLOR_SUCCESS,
        darkcolor=COLOR_SUCCESS,
        thickness=16,
    )

    return style
