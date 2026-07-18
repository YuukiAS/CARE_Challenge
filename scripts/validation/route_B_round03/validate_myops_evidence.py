#!/usr/bin/env python3
"""Validate Route B Round03 B6 MyoPS terminal evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


REQUIRED = [
    "all_checkpoint_metrics.json",
    "training_adequacy.csv",
    "selected_checkpoint_reload.json",
    "intervention_report.json",
    "case_safety_matrix.json",
    "help_harm_matrix.json",
    "completion.json",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("result_dir", type=Path)
    args = parser.parse_args()
    errors = [f"missing:{name}" for name in REQUIRED if not (args.result_dir / name).is_file()]
    payload = {}
    if not errors:
        payload = json.loads((args.result_dir / "completion.json").read_text(encoding="utf-8"))
        if payload.get("completion_token") != "ROUTE_B_ROUND03_B6_MYOPS_EVIDENCE_TERMINAL":
            errors.append("myops_terminal_token_not_positive")
        if payload.get("status") != "PASS":
            errors.append("status_not_pass")
        if payload.get("total_optimizer_steps", 0) < 32000:
            errors.append("total_optimizer_steps_under_32000")
        if payload.get("total_train_loop_seconds", 0) < 9600:
            errors.append("total_train_loop_seconds_under_9600")
        if payload.get("total_validation_events", 0) < 16:
            errors.append("total_validation_events_under_16")
    status = "PASS" if not errors else "FAIL"
    print(json.dumps({"status": status, "errors": errors, "completion_token": payload.get("completion_token")}, indent=2, sort_keys=True))
    return 1 if args.strict and errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
