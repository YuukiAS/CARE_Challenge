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
ALLOWED_NONREADY_TOKENS = {"ROUTE_B_IMPLEMENTATION_NEEDS_REVISION", "ROUTE_B_NEEDS_REVISION", "ROUTE_B_NEEDS_EVIDENCE"}


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
    code_gate_passed = bool(gate.get("code_gate_passed", False))
    real_case_gate_passed = bool(gate.get("real_case_gate_passed", False))
    legacy_gate_passed = bool(gate.get("gate_passed", False))
    implemented_rows = [row for row in trace if row.get("implementation_status") == "implemented"]
    legacy_missing_rows = [row for row in trace if row.get("route_b_status") and row.get("route_b_status") != "implemented"]
    if token == "ROUTE_B_READY_FOR_REVIEW" and not real_case_gate_passed:
        errors.append("ready_token_without_real_case_gate")
    if token == "ROUTE_B_READY_FOR_REVIEW" and legacy_missing_rows:
        errors.append("ready_token_with_legacy_missing_components")
    if token == "ROUTE_B_NEEDS_EVIDENCE" and not code_gate_passed:
        errors.append("needs_evidence_external_blocker_requires_code_gate_passed")
    if token in ALLOWED_NONREADY_TOKENS and token != "ROUTE_B_NEEDS_EVIDENCE" and not legacy_missing_rows and not code_gate_passed:
        errors.append("nonready_token_without_legacy_missing_or_code_gate")
    if gate.get("formal_training_submitted") is True:
        errors.append("formal_training_submitted_before_gate")
    if gate.get("monitor_state") is True or gate.get("submitted_only_state") is True:
        errors.append("monitor_or_submitted_state_in_implementation_gate")
    if token not in ALLOWED_NONREADY_TOKENS and not (real_case_gate_passed or legacy_gate_passed):
        errors.append(f"unexpected_nonpassing_token:{token}")
    for branch in ("MyoPS", "Cine"):
        if not any(row.get("branch") == branch for row in trace):
            errors.append(f"missing_{branch.lower()}_component_rows")
    if code_gate_passed:
        for section in ("myops", "cine"):
            payload = gate.get(section)
            if not isinstance(payload, dict) or payload.get("status") != "PASS":
                errors.append(f"{section}_code_gate_missing_or_failed")
            if not isinstance(payload, dict) or not payload.get("loss_finite_nonzero"):
                errors.append(f"{section}_loss_not_finite_nonzero")
            if isinstance(payload, dict) and float(payload.get("save_reload_delta", 1.0)) >= 1e-5:
                errors.append(f"{section}_save_reload_delta_too_large")
        if len(implemented_rows) < 4:
            errors.append("code_gate_passed_without_component_trace")
    else:
        warnings.append(f"legacy_missing_or_unverified_components:{len(legacy_missing_rows)}")
    return {
        "status": "PASS" if not errors else "FAIL",
        "token": token,
        "code_gate_passed": code_gate_passed,
        "real_case_gate_passed": real_case_gate_passed,
        "legacy_missing_component_count": len(legacy_missing_rows),
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
    if payload.get("external_blocker_claimed") is True and payload.get("code_gate_passed") is not True:
        errors.append("external_blocker_without_code_gate")
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
