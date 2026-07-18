#!/usr/bin/env python3
"""Validate Route B Round03 B3-B5 staged MyoPS receipts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


TOKENS = {
    "evidence_warmup": "ROUTE_B_ROUND03_B3_EVIDENCE_WARMUP_PASSED",
    "proposal": "ROUTE_B_ROUND03_B4_PROPOSAL_GATE_PASSED",
    "refiner": "ROUTE_B_ROUND03_B5_REFINER_GATE_PASSED",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True, choices=sorted(TOKENS))
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("result_dir", type=Path)
    args = parser.parse_args()
    errors: list[str] = []
    completion = args.result_dir / "completion.json"
    for name in ("completion.json", "training_adequacy.csv", "metrics_summary.csv"):
        if not (args.result_dir / name).is_file():
            errors.append(f"missing:{name}")
    payload = {}
    if completion.is_file():
        payload = json.loads(completion.read_text(encoding="utf-8"))
        if payload.get("stage") != args.stage:
            errors.append("stage_mismatch")
        if payload.get("completion_token") != TOKENS[args.stage]:
            errors.append("completion_token_not_pass")
        if payload.get("status") != "PASS":
            errors.append("status_not_pass")
        checks = payload.get("gate_checks", {})
        for key, value in checks.items():
            if value is not True:
                errors.append(f"gate_check_failed:{key}")
        if payload.get("optimizer_steps", 0) < payload.get("required_optimizer_steps", 10**12):
            errors.append("optimizer_steps_under_required")
        if payload.get("train_loop_seconds", 0.0) < payload.get("required_train_loop_seconds", 10**12):
            errors.append("train_loop_seconds_under_required")
        if payload.get("validation_events", 0) < payload.get("required_validation_events", 10**12):
            errors.append("validation_events_under_required")
    status = "PASS" if not errors else "FAIL"
    print(json.dumps({"status": status, "errors": errors, "completion_token": payload.get("completion_token")}, indent=2, sort_keys=True))
    return 1 if args.strict and errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
