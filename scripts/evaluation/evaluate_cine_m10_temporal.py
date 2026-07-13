#!/usr/bin/env python3
"""Evaluate and aggregate M10 Wave 3 Cine runtime evidence."""

from __future__ import annotations

import argparse
import os
import runpy
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-root", default="results/20260711_srr_v3_m10_complete_mechanism_repair/runtime/m10_cine_temporal_executor")
    args = parser.parse_args()
    sys.argv = [
        "aggregate_cine_m10_packet.py",
        "--phase",
        "all",
        "--runtime-root",
        args.runtime_root,
        "--job-id",
        os.environ.get("SLURM_JOB_ID", ""),
        "--job-state",
        os.environ.get("SLURM_JOB_STATE", ""),
        "--job-exit-code",
        os.environ.get("SLURM_JOB_EXIT_CODE", ""),
        "--job-log",
        os.environ.get("LOG_FILE", ""),
        "--partition",
        os.environ.get("SLURM_JOB_PARTITION", ""),
    ]
    runpy.run_path(str(REPO_ROOT / "scripts/evaluation/aggregate_cine_m10_packet.py"), run_name="__main__")


if __name__ == "__main__":
    main()
