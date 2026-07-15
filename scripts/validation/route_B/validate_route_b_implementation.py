#!/usr/bin/env python3
"""Fail-closed Route B implementation gate validator."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
RESULT_ROOT = REPO_ROOT / "results" / "route_B"
ALLOWED_FAILURE_TOKENS = {"ROUTE_B_IMPLEMENTATION_NEEDS_REVISION", "ROUTE_B_NEEDS_REVISION", "ROUTE_B_NEEDS_EVIDENCE"}


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_trace(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def evaluate(result_root: Path = RESULT_ROOT) -> dict[str, object]:
    errors: list[str] = []
    warnings: list[str] = []
    gate_path = result_root / "implementation_gate.json"
    trace_path = result_root / "architecture_component_trace.csv"
    if not gate_path.exists():
        return {"status": "FAIL", "errors": ["missing implementation_gate.json"], "warnings": []}
    if not trace_path.exists():
        return {"status": "FAIL", "errors": ["missing architecture_component_trace.csv"], "warnings": []}
    gate = load_json(gate_path)
    trace = read_trace(trace_path)
    token = str(gate.get("status", ""))
    gate_passed = bool(gate.get("gate_passed", False))
    missing_rows = [row for row in trace if row.get("route_b_status") != "implemented"]
    if gate_passed and missing_rows:
        errors.append("gate_passed_true_with_missing_components")
    if token == "ROUTE_B_READY_FOR_REVIEW" and missing_rows:
        errors.append("ready_token_with_missing_components")
    if token in ALLOWED_FAILURE_TOKENS and not missing_rows:
        errors.append("failure_token_without_recorded_missing_components")
    if gate.get("formal_training_submitted") is True:
        errors.append("formal_training_submitted_before_gate")
    if gate.get("monitor_state") is True or gate.get("submitted_only_state") is True:
        errors.append("monitor_or_submitted_state_in_implementation_gate")
    if token not in ALLOWED_FAILURE_TOKENS and not gate_passed:
        errors.append(f"unexpected_nonpassing_token:{token}")
    for branch in ("MyoPS", "Cine"):
        if not any(row.get("branch") == branch for row in trace):
            errors.append(f"missing_{branch.lower()}_component_rows")
    if missing_rows:
        warnings.append(f"missing_or_unverified_components:{len(missing_rows)}")
    return {
        "status": "PASS_FAILURE_STATE_CONSISTENT" if not errors else "FAIL",
        "token": token,
        "gate_passed": gate_passed,
        "missing_component_count": len(missing_rows),
        "errors": errors,
        "warnings": warnings,
    }


def evaluate_fixture_payload(payload: dict[str, object]) -> dict[str, object]:
    errors: list[str] = []
    token = str(payload.get("completion_token", ""))
    missing_components = int(payload.get("missing_component_count", 0))
    if token == "ROUTE_B_READY_FOR_REVIEW" and missing_components > 0:
        errors.append("ready_token_with_missing_components")
    if payload.get("formal_training_before_gate") is True:
        errors.append("formal_training_before_gate")
    if payload.get("monitor_packet_claims_completion") is True:
        errors.append("monitor_packet_claims_completion")
    return {"status": "FAIL" if errors else "PASS", "errors": errors}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--write-report", type=Path)
    parser.add_argument("--fixture", type=Path)
    args = parser.parse_args()
    if args.fixture:
        report = evaluate_fixture_payload(load_json(args.fixture))
    else:
        report = evaluate()
    if args.write_report:
        args.write_report.parent.mkdir(parents=True, exist_ok=True)
        args.write_report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if args.strict and report["status"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
