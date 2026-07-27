#!/usr/bin/env python3
"""Strict fail-closed validator for the CARE-DG validation packet."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.evaluation.build_care_dg_validation_packet import RESULT_ROOT, validate_packet


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet-root", type=Path, default=RESULT_ROOT)
    args = parser.parse_args()
    if args.packet_root != RESULT_ROOT:
        raise SystemExit(f"CARE-DG validator currently expects packet root {RESULT_ROOT}")
    report = validate_packet()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
