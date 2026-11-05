"""Headless GUI end-to-end smoke test: queue -> configure -> run batch -> UI status updates."""

from __future__ import annotations

import time
import tkinter as tk
import warnings
from pathlib import Path

import pytest

with warnings.catch_warnings():
    warnings.simplefilter("ignore", FutureWarning)
    import fitz

from src.models.job_config import CollisionStrategy, WatermarkMode


@pytest.fixture()
def app():
    try:
        root = tk.Tk()
    except tk.TclError:  # no display available
        pytest.skip("Tk display not available")
    root.withdraw()
    from src.gui.app import BatchPDFApp

    instance = BatchPDFApp(root)
    yield instance
    root.destroy()


def _pdf(path: Path, pages: int = 3) -> Path:
    doc = fitz.open()
    for i in range(pages):
        doc.new_page().insert_text(fitz.Point(72, 100), f"p{i}")
    doc.set_metadata({"author": "Orig", "title": "T"})
    doc.save(str(path))
    doc.close()
    return path


def _pump(app, until, timeout: float = 20.0) -> None:
    end = time.time() + timeout
    while time.time() < end and not until():
        app.root.update()
        time.sleep(0.02)


def test_gui_end_to_end_batch(app, tmp_path: Path) -> None:
    files = [_pdf(tmp_path / f"in{i}.pdf") for i in range(3)]
    assert app.file_table.add_files([str(f) for f in files]) == 3
    assert app.file_table.add_files([str(files[0])]) == 0  # duplicates rejected

    app.watermark_panel.mode_var.set(WatermarkMode.TEXT.value)
    app.watermark_panel.text_var.set("E2E")
    app.metadata_panel.author_var.set("GUI Author")
    out = tmp_path / "out"
    app.output_strategy_var.set(CollisionStrategy.DEDICATED_FOLDER.value)
    app.output_dir_var.set(str(out))
    app.output_suffix_var.set("_gui")

    app.start_batch()
    assert app._is_running
    _pump(app, lambda: not app._is_running)

    assert not app._is_running
    assert app.progress_var.get() == 100.0
    assert "3 succeeded, 0 failed" in app.status_var.get()
    statuses = [app.file_table.tree.item(i, "values")[3] for i in app.file_table.tree.get_children()]
    assert statuses == ["Completed"] * 3
    outputs = sorted(out.glob("*.pdf"))
    assert len(outputs) == 3
    with fitz.open(str(outputs[0])) as doc:
        assert doc.metadata["author"] == "GUI Author"
        assert "E2E" in doc[0].get_text()


def test_gui_blocks_start_on_empty_queue_and_missing_output_dir(app, monkeypatch) -> None:
    shown: list[str] = []
    monkeypatch.setattr("src.gui.app.messagebox.showwarning", lambda *a, **k: shown.append("warn"))
    monkeypatch.setattr("src.gui.app.messagebox.showerror", lambda *a, **k: shown.append("err"))
    app.start_batch()
    assert shown == ["warn"] and not app._is_running

    app.file_table.clear_queue()
    app.output_strategy_var.set(CollisionStrategy.DEDICATED_FOLDER.value)
    app.output_dir_var.set("")
    assert not app._is_running


def test_gui_preview_updates_on_selection(app, tmp_path: Path) -> None:
    pdf = _pdf(tmp_path / "pv.pdf", pages=4)
    app.file_table.add_files([str(pdf)])
    app.root.update()
    assert app.preview_panel._total_pages == 4
    app.preview_panel.next_page()
    app.preview_panel.next_page()
    assert app.preview_panel._current_page_idx == 2
    for _ in range(10):
        app.preview_panel.next_page()
    assert app.preview_panel._current_page_idx == 3  # clamped at last page
    app.file_table.clear_queue()
    assert app.preview_panel._total_pages == 1

