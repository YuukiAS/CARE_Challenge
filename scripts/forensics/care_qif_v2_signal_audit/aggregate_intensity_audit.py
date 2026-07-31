#!/usr/bin/env python3
"""Validate and summarize CARE-QIF v2 intensity audit outputs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT_FOR_IMPORT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT_FOR_IMPORT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT_FOR_IMPORT))

from scripts.forensics.care_qif_v2_signal_audit.common import RESULT_ROOT, read_csv, write_json  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-root", type=Path, default=RESULT_ROOT)
    args = parser.parse_args()
    required = [
        "intensity_casewise_metrics.csv",
        "intensity_transfer_summary.csv",
        "intensity_context_comparison.csv",
        "intensity_probe_coefficients.csv",
        "intensity_signal_receipt.json",
    ]
    missing = [name for name in required if not (args.result_root / name).exists()]
    receipt = json.loads((args.result_root / "intensity_signal_receipt.json").read_text(encoding="utf-8")) if not missing else {}
    summaries = read_csv(args.result_root / "intensity_transfer_summary.csv") if not missing else []
    write_json(
        args.result_root / "intensity_aggregation_receipt.json",
        {
            "missing_outputs": missing,
            "summary_rows": len(summaries),
            "intensity_signal_decision": receipt.get("intensity_signal_decision", ""),
            "status": "PASS" if not missing and receipt.get("status") == "PASS" else "FAIL",
        },
    )
    return 0 if not missing and receipt.get("status") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
