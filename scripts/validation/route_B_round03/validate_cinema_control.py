#!/usr/bin/env python3
"""Validate Route B Round03 B7 CineMA matched-control packet."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


REQUIRED = ["completion.json", "source_provenance.json", "lane_training_adequacy.csv", "control_classification.json"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("result_dir", type=Path)
    args = parser.parse_args()
    errors = [f"missing:{name}" for name in REQUIRED if not (args.result_dir / name).is_file()]
    payload = {}
    if not errors:
        payload = json.loads((args.result_dir / "completion.json").read_text(encoding="utf-8"))
        if payload.get("completion_token") != "ROUTE_B_ROUND03_B7_CINEMA_CONTROL_TERMINAL":
            errors.append("b7_terminal_token_missing")
        if payload.get("status") != "PASS":
            errors.append("status_not_pass")
        for key, value in payload.get("gate_checks", {}).items():
            if value is not True:
                errors.append(f"gate_check_failed:{key}")
    status = "PASS" if not errors else "FAIL"
    print(json.dumps({"status": status, "errors": errors, "completion_token": payload.get("completion_token")}, indent=2, sort_keys=True))
    return 1 if args.strict and errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
