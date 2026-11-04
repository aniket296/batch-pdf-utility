# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller specification for compiling BatchPDFStudio.exe on Windows."""

from PyInstaller.utils.hooks import collect_all

block_cipher = None

fitz_datas, fitz_binaries, fitz_hiddenimports = collect_all("pymupdf")
pil_datas, pil_binaries, pil_hiddenimports = collect_all("PIL")

hidden_imports = [
    "fitz",
    "pymupdf",
    "PIL",
    "PIL.Image",
    "PIL.ImageDraw",
    "PIL.ImageTk",
    "tkinter",
    "tkinter.ttk",
    "tkinter.filedialog",
    "tkinter.colorchooser",
    "tkinter.messagebox",
] + fitz_hiddenimports + pil_hiddenimports

a = Analysis(
    ["src/main.py"],
    pathex=["."],
    binaries=fitz_binaries + pil_binaries,
    datas=fitz_datas + pil_datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "onnxruntime"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="BatchPDFStudio",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

