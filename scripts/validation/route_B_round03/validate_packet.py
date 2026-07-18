#!/usr/bin/env python3
"""Validate Route B Round03 terminal controller packet."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


REQUIRED_B10 = [
    "finalizer_state.json",
    "routing_ledger.csv",
    "training_adequacy.csv",
    "metrics_summary.csv",
    "case_safety_matrix.csv",
    "help_harm_matrix.csv",
    "mapper_report_final.md",
    "route_local_architecture_fingerprint.json",
    "validator_packet_report.json",
    "known_bad_selftest_report.md",
    "heavy_artifact_scan.json",
    "completion.json",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--require-all-attempt-accounting", action="store_true")
    parser.add_argument("packet_dir", type=Path)
    args = parser.parse_args()
    errors: list[str] = []
    route_root = Path("results/route_B")
    b10 = route_root / "round03/executors/B10"
    for name in REQUIRED_B10:
        if not (b10 / name).is_file():
            errors.append(f"missing_b10:{name}")
    for name in ("completion_check.md", "result.md", "controller_report.md", "review_request.md", "MANIFEST.md"):
        if not (route_root / name).is_file():
            errors.append(f"missing_route_root:{name}")
    payload = {}
    if (b10 / "completion.json").is_file():
        payload = json.loads((b10 / "completion.json").read_text(encoding="utf-8"))
        terminal_negative = payload.get("terminal_negative_packet") is True
        if payload.get("completion_token") != "ROUTE_B_ROUND03_TERMINAL_PACKET_READY_FOR_REVIEW":
            errors.append("terminal_token_missing")
        if payload.get("status") != "PASS":
            errors.append("packet_status_not_pass")
        if payload.get("missing_stage_packets") and not terminal_negative:
            errors.append("missing_stage_packets")
        if payload.get("nonpass_stage_packets") and not terminal_negative:
            errors.append("nonpass_stage_packets")
        if terminal_negative:
            if not payload.get("blocked_at_stage"):
                errors.append("terminal_negative_missing_blocked_stage")
            if "SCIENTIFIC_GATE_FAILED" not in str(payload.get("blocked_completion_token", "")) and "ADEQUATE_NEGATIVE" not in str(payload.get("blocked_completion_token", "")):
                errors.append("terminal_negative_bad_blocked_token")
            if not payload.get("missing_stage_packets_justification"):
                errors.append("terminal_negative_missing_downstream_justification")
        if payload.get("heavy_artifact_scan", {}).get("status") != "PASS":
            errors.append("tracked_heavy_artifacts_present")
        forbidden = payload.get("forbidden_actions", {})
        for key, value in forbidden.items():
            if value is not False:
                errors.append(f"forbidden_action_performed:{key}")
    completion_text = (route_root / "completion_check.md").read_text(encoding="utf-8") if (route_root / "completion_check.md").is_file() else ""
    for bad in ("NEEDS_MONITOR", "PENDING_MONITOR", "JOB_SUBMITTED", "RUNNING", "AWAITING_SACCT"):
        if "ROUTE_B_ROUND03_TERMINAL_PACKET_READY_FOR_REVIEW" in completion_text and bad in completion_text:
            errors.append(f"ready_completion_contains_monitor_state:{bad}")
    status = "PASS" if not errors else "FAIL"
    print(json.dumps({"status": status, "errors": errors, "completion_token": payload.get("completion_token")}, indent=2, sort_keys=True))
    return 1 if args.strict and errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
