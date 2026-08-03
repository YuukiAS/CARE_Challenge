#!/usr/bin/env python
"""Thin CARE-ASE R2 chunk wrapper.

All formal/probe step authority lives in
src.care_myocardium.training.care_ase_runtime.CAREASEFormalRuntime.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.care_myocardium.training.care_ase_runtime import main


if __name__ == "__main__":
    raise SystemExit(main())
