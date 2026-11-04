"""Interactive batch PDF queue table with folder recursion and row selection hooks."""

from __future__ import annotations

import tkinter as tk
import warnings
from pathlib import Path
from tkinter import filedialog, ttk
from typing import Callable, Optional

with warnings.catch_warnings():
    warnings.simplefilter("ignore", FutureWarning)
    import fitz

from src.core.metadata_engine import read_metadata
from src.utils.file_ops import discover_pdf_files
from src.utils.logger import get_logger

logger = get_logger("file_table")

SelectionCallback = Callable[[Optional[str]], None]
QueueChangedCallback = Callable[[int], None]


class FileQueueTable(ttk.Frame):
    """Treeview-based batch PDF file queue with file/folder addition and status tracking."""

    COLUMNS = ("file_name", "pages", "meta_summary", "status", "output_path")

    def __init__(
        self,
        parent: tk.Misc,
        on_selection_change: Optional[SelectionCallback] = None,
        on_queue_change: Optional[QueueChangedCallback] = None,
    ) -> None:
        """Initialize the toolbar and Treeview queue component."""
        super().__init__(parent)
        self.on_selection_change = on_selection_change
        self.on_queue_change = on_queue_change

        # Map normalized source_path -> Treeview item IID
        self._path_to_iid: dict[str, str] = {}
        self._iid_to_path: dict[str, str] = {}
        self._last_root_folder: Optional[str] = None

        self._build_toolbar()
        self._build_treeview()

    @property
    def last_root_folder(self) -> Optional[str]:
        """Return the most recently added folder root for MIRROR_TREE output resolution."""
        return self._last_root_folder

    def _build_toolbar(self) -> None:
        """Create the top action toolbar for managing queued PDF files."""
        toolbar = ttk.Frame(self)
        toolbar.pack(side=tk.TOP, fill=tk.X, pady=(0, 6))

        self.btn_add_files = ttk.Button(
            toolbar,
            text="+ Add PDF Files",
            style="Primary.TButton",
            command=self.prompt_add_files,
        )
        self.btn_add_files.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_add_folder = ttk.Button(
            toolbar,
            text="+ Add Folder (Recursive)",
            style="Primary.TButton",
            command=self.prompt_add_folder,
        )
        self.btn_add_folder.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_remove = ttk.Button(
            toolbar,
            text="Remove Selected",
            command=self.remove_selected,
        )
        self.btn_remove.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_clear = ttk.Button(
            toolbar,
            text="Clear Queue",
            command=self.clear_queue,
        )
        self.btn_clear.pack(side=tk.LEFT)

        self.count_label = ttk.Label(
            toolbar,
            text="0 PDFs in queue",
            style="Muted.TLabel",
        )
        self.count_label.pack(side=tk.RIGHT, padx=(6, 0))

    def _build_treeview(self) -> None:
        """Construct the scrollable 5-column Treeview table."""
        table_frame = ttk.Frame(self)
        table_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.tree = ttk.Treeview(
            table_frame,
            columns=self.COLUMNS,
            show="headings",
            selectmode="extended",
            height=8,
        )

        self.tree.heading("file_name", text="File Name", anchor=tk.W)
        self.tree.heading("pages", text="Pages", anchor=tk.CENTER)
        self.tree.heading("meta_summary", text="Current Author / Title", anchor=tk.W)
        self.tree.heading("status", text="Status", anchor=tk.CENTER)
        self.tree.heading("output_path", text="Output Path", anchor=tk.W)

        self.tree.column("file_name", width=190, minwidth=120, anchor=tk.W, stretch=True)
        self.tree.column("pages", width=60, minwidth=50, anchor=tk.CENTER, stretch=False)
        self.tree.column("meta_summary", width=210, minwidth=130, anchor=tk.W, stretch=True)
        self.tree.column("status", width=105, minwidth=85, anchor=tk.CENTER, stretch=False)
        self.tree.column("output_path", width=220, minwidth=130, anchor=tk.W, stretch=True)

        # Configure row status color tags
        self.tree.tag_configure("Pending", foreground="#334155")
        self.tree.tag_configure("Processing...", foreground="#2563EB")
        self.tree.tag_configure("Completed", foreground="#059669")
        self.tree.tag_configure("Failed", foreground="#DC2626")

        vsb = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

    def _inspect_pdf_summary(self, file_path: str) -> tuple[int, str]:
        """Extract page count and 'Author / Title' summary string for a PDF file."""
        try:
            with fitz.open(file_path) as doc:
                page_count = len(doc)
                meta = read_metadata(doc)
                author = meta.get("author") or "—"
                title = meta.get("title") or "—"
                return page_count, f"{author} / {title}"
        except Exception as exc:
            logger.warning("Could not inspect PDF '%s': %s", file_path, exc)
            return 0, "Unreadable / Encrypted"

    def prompt_add_files(self) -> None:
        """Open native Windows file dialog to add one or more PDF files."""
        selected = filedialog.askopenfilenames(
            parent=self,
            title="Select PDF Files for Batch Processing",
            filetypes=[("PDF Documents", "*.pdf"), ("All Files", "*.*")],
        )
        if selected:
            self.add_files(list(selected))

    def prompt_add_folder(self) -> None:
        """Open native Windows folder dialog and recursively discover all PDFs inside."""
        folder = filedialog.askdirectory(
            parent=self,
            title="Select Folder to Scan Recursively for PDFs",
        )
        if folder:
            self._last_root_folder = str(Path(folder).resolve())
            discovered = discover_pdf_files(folder, recursive=True)
            self.add_files(discovered)

    def add_files(self, paths: list[str]) -> int:
        """Add a list of PDF file paths to the queue, skipping duplicates."""
        added = 0
        first_added_iid: Optional[str] = None

        for raw_path in paths:
            norm_path = str(Path(raw_path).resolve())
            if norm_path in self._path_to_iid:
                continue
            if not Path(norm_path).is_file():
                continue

            pages, meta_summary = self._inspect_pdf_summary(norm_path)
            iid = self.tree.insert(
                "",
                tk.END,
                values=(
                    Path(norm_path).name,
                    pages,
                    meta_summary,
                    "Pending",
                    "—",
                ),
                tags=("Pending",),
            )
            self._path_to_iid[norm_path] = iid
            self._iid_to_path[iid] = norm_path
            if first_added_iid is None:
                first_added_iid = iid
            added += 1

        self._refresh_counts()

        # Automatically select the first row if nothing is currently selected
        if first_added_iid and not self.tree.selection():
            self.tree.selection_set(first_added_iid)
            self.tree.focus(first_added_iid)
            self._on_tree_select()

        return added

    def remove_selected(self) -> None:
        """Remove all currently highlighted rows from the queue."""
        selected_iids = self.tree.selection()
        if not selected_iids:
            return
        for iid in selected_iids:
            path = self._iid_to_path.pop(iid, None)
            if path:
                self._path_to_iid.pop(path, None)
            self.tree.delete(iid)

        self._refresh_counts()
        remaining = self.tree.get_children()
        if remaining:
            self.tree.selection_set(remaining[0])
            self._on_tree_select()
        elif self.on_selection_change:
            self.on_selection_change(None)

    def clear_queue(self) -> None:
        """Remove all files from the queue."""
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        self._path_to_iid.clear()
        self._iid_to_path.clear()
        self._last_root_folder = None
        self._refresh_counts()
        if self.on_selection_change:
            self.on_selection_change(None)

    def get_queued_files(self) -> list[str]:
        """Return ordered list of absolute file paths currently in the queue."""
        return [
            self._iid_to_path[iid]
            for iid in self.tree.get_children()
            if iid in self._iid_to_path
        ]

    def get_selected_file(self) -> Optional[str]:
        """Return the file path of the first currently selected row, or None."""
        selection = self.tree.selection()
        if not selection:
            return None
        return self._iid_to_path.get(selection[0])

    def reset_all_statuses(self) -> None:
        """Reset all rows to 'Pending' status before starting a batch run."""
        for iid in self.tree.get_children():
            vals = list(self.tree.item(iid, "values"))
            if len(vals) >= 5:
                vals[3] = "Pending"
                vals[4] = "—"
                self.tree.item(iid, values=vals, tags=("Pending",))

    def update_file_status(
        self,
        source_path: str,
        status_label: str,
        output_path: Optional[str] = None,
    ) -> None:
        """Update the Status and Output Path columns for a specific file in the queue."""
        norm_path = str(Path(source_path).resolve())
        iid = self._path_to_iid.get(norm_path) or self._path_to_iid.get(source_path)
        if not iid or not self.tree.exists(iid):
            return

        vals = list(self.tree.item(iid, "values"))
        if len(vals) >= 5:
            vals[3] = status_label
            if output_path is not None:
                vals[4] = output_path
            tag = status_label if status_label in ("Pending", "Processing...", "Completed", "Failed") else "Pending"
            self.tree.item(iid, values=vals, tags=(tag,))

    def set_controls_enabled(self, enabled: bool) -> None:
        """Enable or disable queue manipulation buttons during batch execution."""
        state = tk.NORMAL if enabled else tk.DISABLED
        self.btn_add_files.configure(state=state)
        self.btn_add_folder.configure(state=state)
        self.btn_remove.configure(state=state)
        self.btn_clear.configure(state=state)

    def _refresh_counts(self) -> None:
        """Update the queue count label and notify listener."""
        total = len(self._path_to_iid)
        noun = "PDF" if total == 1 else "PDFs"
        self.count_label.configure(text=f"{total} {noun} in queue")
        if self.on_queue_change:
            self.on_queue_change(total)

    def _on_tree_select(self, _event: Optional[tk.Event] = None) -> None:  # type: ignore[type-arg]
        """Emit the currently selected PDF file path to the preview listener."""
        if self.on_selection_change:
            self.on_selection_change(self.get_selected_file())
