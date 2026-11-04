"""Application entry point for Batch PDF Metadata & Watermarking Utility."""

from __future__ import annotations

import ctypes
import sys
import tkinter as tk

from src.gui.app import BatchPDFApp
from src.utils.logger import get_logger

logger = get_logger("main")


def enable_windows_high_dpi() -> None:
    """Enable per-monitor High-DPI awareness on Windows platforms."""
    if sys.platform == "win32":
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass


def main() -> None:
    """Configure High-DPI awareness and launch the Tkinter desktop GUI."""
    enable_windows_high_dpi()
    logger.info("Launching Batch PDF Metadata & Watermarking Utility GUI.")
    root = tk.Tk()
    _app = BatchPDFApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

