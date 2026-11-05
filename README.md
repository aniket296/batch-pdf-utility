# 📄 Batch PDF Metadata & Watermarking Studio

[![Platform: Windows](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0078D6?logo=windows&logoColor=white)](https://microsoft.com)
[![Python: 3.11+](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Architecture: Modular](https://img.shields.io/badge/Architecture-Clean%20%2F%20Modular-blueviolet)](#architecture)
[![Build: PyInstaller](https://img.shields.io/badge/Packaged%20With-PyInstaller-yellow)](https://pyinstaller.org)

> **A high-performance, 100% offline desktop application for batch PDF processing.** Modify or completely scrub sensitive metadata, apply custom text or corporate image watermarks, and inspect changes in real-time with zero cloud exposure.

---

## 🌟 Why This Exists (Real-World Impact)

Most free PDF editing tools operate online, forcing legal, financial, healthcare, and educational teams to upload sensitive documents to third-party cloud servers. This introduces significant privacy and compliance risks.

**Batch PDF Metadata & Watermarking Studio** solves this problem by executing all operations strictly on your local machine:
- 🔒 **Absolute Data Privacy:** Documents never leave your hardware.
- ⚡ **No Upload/Download Bottlenecks:** Process hundreds of multi-page PDFs using local CPU power.
- 📴 **100% Offline Autonomy:** Works reliably in air-gapped or restricted network environments.

---

## ✨ Key Features

- **🛡️ Full Metadata Scrubbing:** One-click sanitize mode wipes author info, editing history, and hidden XMP metadata packets.
- **✏️ Targeted Metadata Editing:** Selectively update Title, Author, Subject, and Keywords without altering untouched fields.
- **💧 Dual-Mode Watermarking:** Apply customizable vector text stamps or transparent PNG corporate logos.
- **📐 Flexible Layouts:** Choose between centered stamps, diagonal banner overlays, or anti-crop tiled grid patterns.
- **👁️ Live Interactive Preview:** Non-destructive in-memory renderer shows real-time watermark placement before running the batch.
- **🛡️ Collision-Safe Output:** Never overwrites originals by default; supports custom suffixes and dedicated destination folders.

---

## 🏗️ Architecture

Built using a clean, multi-module separation of concerns:

```text
batch-pdf-utility/
├── src/
│   ├── core/               # Pure business logic (PyMuPDF engines & worker pool)
│   │   ├── metadata_engine.py
│   │   ├── watermark_engine.py
│   │   ├── preview_engine.py
│   │   └── worker.py
│   ├── gui/                # Desktop UI layer (Tkinter / TTK)
│   │   ├── components/     # File queue, preview canvas, and settings forms
│   │   ├── app.py          # Application shell & thread orchestration
│   │   └── styles.py       # Slate & Navy corporate styling system
│   ├── models/             # Strongly-typed dataclasses & job schemas
│   └── utils/              # Thread-safe logging and collision-safe file operations
├── installer/              # Inno Setup Windows installer configuration
│   └── setup.iss
├── scripts/                # Automated build and packaging scripts
│   ├── build_exe.bat
│   └── build_installer.bat
├── tests/                  # Automated pytest verification suite
│   ├── conftest.py
│   ├── test_metadata.py
│   └── test_watermark.py
├── release/                # Pre-built standalone Windows binary
│   └── BatchPDFStudio.exe
├── requirements.txt        # Core package requirements
├── run_local.bat           # One-click local source launcher
└── pyproject.toml          # Project configuration & dependencies
```

---

## 🚀 Quick Start & Dual-Mode Execution

### Option 0: Windows Installer (For End Users)

1. Go to the [**GitHub Releases**](https://github.com/aniket296/batch-pdf-utility/releases) page and download **`BatchPDFStudio_Setup.exe`**.
2. Run **`BatchPDFStudio_Setup.exe`** to install **Batch PDF Metadata & Watermarking Studio** with optional Desktop and Start Menu shortcuts.
3. You can uninstall the application cleanly at any time via **Windows Settings → Installed Apps** (or Control Panel).

---

### Option A: Run Directly from Source (Developers)

Using the automated one-click launcher:
```powershell
.\run_local.bat
```
> **What `run_local.bat` does:**
> 1. Automatically creates a virtual environment in `.venv/` if not present.
> 2. Installs or updates all required dependencies (`PyMuPDF`, `Pillow`).
> 3. Launches the application from source (`python -m src.main`).
> 4. Keeps the console open on error for rapid debugging.

Or run manually via Python:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m src.main
```

---

### Option B: Run Standalone Executable (No Python Required)

Double-click the pre-built binary located at:
```text
release\BatchPDFStudio.exe
```
This is a standalone, self-contained Windows executable packaged with all required runtime dependencies.

---

## 🧪 Running Automated Unit Tests

To run the complete test suite verifying metadata sanitization, watermarking geometry, and collision safety:

```powershell
.\.venv\Scripts\pytest
```

---

## 🔨 Building the Executable & Windows Installer from Source

To compile the standalone Windows executable yourself using PyInstaller:

```powershell
.\scripts\build_exe.bat
```

This script will run unit tests first, compile the binary using `build_windows.spec`, and verify the final artifact at `dist\BatchPDFStudio.exe`.

To compile the full Windows Setup Installer (`dist_installer\BatchPDFStudio_Setup.exe`) using [Inno Setup 6](https://jrsoftware.org/isinfo.php):

```powershell
.\scripts\build_installer.bat
```

This script automatically runs `scripts\build_exe.bat` first, locates `ISCC.exe`, compiles `installer\setup.iss`, and outputs `dist_installer\BatchPDFStudio_Setup.exe` ready for GitHub Releases.

---

## 📜 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
