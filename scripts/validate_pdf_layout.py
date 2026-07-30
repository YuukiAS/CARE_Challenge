#!/usr/bin/env python3
"""Repository wrapper for the Chinese/math PDF layout validator."""

from __future__ import annotations

import runpy
from pathlib import Path

SCRIPT = Path("/users/a/e/aereinh/.codex-global/skills/tools-documents-media-render-chinese-math-pdf/scripts/validate_pdf_layout.py")

if __name__ == "__main__":
    runpy.run_path(str(SCRIPT), run_name="__main__")
