#!/usr/bin/env python3
"""Redirect to scripts/nnunet/convert_myops_to_nnunet.py (stable path for docs)."""
import os
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_TARGET = _HERE / "nnunet" / "convert_myops_to_nnunet.py"
os.execv(sys.executable, [sys.executable, str(_TARGET)] + sys.argv[1:])
