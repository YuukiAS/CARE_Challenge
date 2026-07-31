#!/usr/bin/env python3
"""CARE-MyoWall-IF arm runner.

This entrypoint refuses formal training until metric truth dependency is PASS.
Use ``--zero-credit-smoke`` for P2 smoke checks.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

TASK_KEY = "20260731_care_myowall_if_mechanism_pilot"
RESULT_ROOT = REPO_ROOT / "results" / TASK_KEY


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm", choices=["C0", "W1", "W2", "W3"], required=True)
    parser.add_argument("--steps", type=int, default=8000)
    parser.add_argument("--zero-credit-smoke", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=RESULT_ROOT)
    args = parser.parse_args()
    metric = RESULT_ROOT / "metric_dependency_receipt.json"
    if not args.zero_credit_smoke:
        if not metric.is_file() or read_json(metric).get("metric_dependency_status") != "PASS":
            raise SystemExit("formal MyoWall-IF arm training blocked: metric truth receipt is not PASS")
        if args.steps != 8000:
            raise SystemExit("formal MyoWall-IF arm training must use exactly 8000 optimizer steps")
    payload = {
        "arm": args.arm,
        "status": "ZERO_CREDIT_SMOKE_RECORDED" if args.zero_credit_smoke else "FORMAL_TRAINING_ENTRY_READY",
        "optimizer_steps": 0 if args.zero_credit_smoke else args.steps,
        "formal_credit": not args.zero_credit_smoke,
        "metric_dependency_checked": metric.is_file(),
        "checkpoint_reload_required": True,
    }
    name = "zero_credit_smoke_report.json" if args.zero_credit_smoke else f"arm_{args.arm}_training_summary.json"
    write_json(args.output_dir / name, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
