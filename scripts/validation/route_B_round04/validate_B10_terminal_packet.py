#!/usr/bin/env python3
"""Strict Route B Round04 terminal packet validator."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


READY_TOKEN = "ROUTE_B_ROUND04_TERMINAL_PACKET_READY_FOR_REVIEW"
TERMINAL_PREFIXES = ("COMPLETED", "FAILED", "CANCELLED", "TIMEOUT", "PREEMPTED", "OUT_OF_MEMORY", "NODE_FAIL", "BOOT_FAIL")
REQUIRED = [
    "routing_ledger.csv",
    "training_adequacy.csv",
    "terminal_branch_coverage.json",
    "validator_packet_report.json",
    "known_bad_report.json",
    "heavy_artifact_scan.json",
    "finalizer_state.json",
    "completion.json",
    "terminal_registry_snapshot.json",
    "root_packet_manifest.json",
]


def read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def add(errors: list[dict[str, str]], key: str, detail: str) -> None:
    errors.append({"key": key, "detail": detail})


def terminal_state(state: str) -> bool:
    upper = state.upper()
    return any(upper.startswith(prefix) for prefix in TERMINAL_PREFIXES)


def validate(packet_dir: Path, require_token: str) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    for name in REQUIRED:
        if not (packet_dir / name).is_file():
            add(errors, "AGGREGATION_MISSING_OR_NONZERO", f"missing {name}")
    if errors:
        return {"status": "FAIL", "errors": errors, "failure_keys": sorted({e["key"] for e in errors})}

    completion = read_json(packet_dir / "completion.json")
    state = read_json(packet_dir / "finalizer_state.json")
    branch = read_json(packet_dir / "terminal_branch_coverage.json")
    validator = read_json(packet_dir / "validator_packet_report.json")
    known_bad = read_json(packet_dir / "known_bad_report.json")
    heavy = read_json(packet_dir / "heavy_artifact_scan.json")
    registry = read_json(packet_dir / "terminal_registry_snapshot.json")
    root_manifest = read_json(packet_dir / "root_packet_manifest.json")
    adequacy = read_csv(packet_dir / "training_adequacy.csv")
    routing = read_csv(packet_dir / "routing_ledger.csv")

    if completion.get("completion_token") != require_token or require_token != READY_TOKEN or completion.get("status") != "PASS":
        add(errors, "AGGREGATION_MISSING_OR_NONZERO", "completion token/status mismatch")
    if state.get("aggregation_command_exit_code") != 0:
        add(errors, "AGGREGATION_MISSING_OR_NONZERO", "aggregation command nonzero")
    if state.get("completion_token") != completion.get("completion_token") or state.get("status") != completion.get("status"):
        add(errors, "AGGREGATION_MISSING_OR_NONZERO", "finalizer_state and completion diverge")
    if not adequacy or not routing:
        add(errors, "AGGREGATION_MISSING_OR_NONZERO", "routing/training adequacy missing rows")

    for key, failure in [
        ("early_terminal_branches_reachable", "EARLY_TERMINAL_BRANCH_UNREACHABLE"),
        ("b1_failure_finalizer_launch_covered", "B1_FAILURE_FINALIZER_NOT_LAUNCHED"),
        ("b2_external_blocker_finalizer_launch_covered", "B2_EXTERNAL_BLOCKER_FINALIZER_NOT_LAUNCHED"),
        ("b7_blocker_finalizer_launch_covered", "B7_BLOCKER_FINALIZER_NOT_LAUNCHED"),
        ("b8_registration_blocker_finalizer_launch_covered", "B8_REGISTRATION_BLOCKER_FINALIZER_NOT_LAUNCHED"),
    ]:
        if branch.get(key) is not True:
            add(errors, failure, f"branch coverage false: {key}")
    if branch.get("cine_lane_terminal_class") != "B8_CINE_REGISTRATION_BLOCKER_NO_B9" or branch.get("b9_absence_justified") is not True:
        add(errors, "B8_REGISTRATION_BLOCKER_FINALIZER_NOT_LAUNCHED", "B8 blocker/B9 absence not accounted")
    if branch.get("b6_terminal_accounted") is not True:
        add(errors, "SUCCESSFUL_B6_B9_NOT_ACCOUNTED", "B6 terminal accounting flag missing")

    stage_rows = {row.get("stage"): row for row in adequacy}
    for stage in ("B0", "B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8"):
        if stage_rows.get(stage, {}).get("status") != "PASS":
            add(errors, "SUCCESSFUL_B6_B9_NOT_ACCOUNTED" if stage == "B6" else "AGGREGATION_MISSING_OR_NONZERO", f"{stage} not PASS")
    if stage_rows.get("B9", {}).get("status") != "SKIPPED_DUE_B8_REGISTRATION_BLOCKER":
        add(errors, "SUCCESSFUL_B6_B9_NOT_ACCOUNTED", "B9 skip is not justified by B8 blocker")

    coverage = state.get("finalizer_dependency_coverage", {})
    registry_rows = registry.get("terminal_accounting", [])
    if coverage.get("dependency") != "afterany_all_started_attempts":
        add(errors, "TIMEOUT_PREEMPTION_CANCELLED_LOSER_NOT_ACCOUNTED", "finalizer dependency is not afterany")
    covered = {str(job) for job in coverage.get("covered_job_ids", [])}
    accounted = {str(row.get("job_id")) for row in registry_rows}
    if covered != accounted or not covered:
        add(errors, "TIMEOUT_PREEMPTION_CANCELLED_LOSER_NOT_ACCOUNTED", "covered/accounted job id mismatch")
    if not all(terminal_state(str(row.get("state", ""))) and row.get("terminal_accounted") is True for row in registry_rows):
        add(errors, "PENDING_OR_RUNNING_PRESENTED_AS_COMPLETE", "nonterminal started attempt present")
    for required_job in ("59546347", "59546548", "59548314"):
        if required_job not in accounted:
            add(errors, "TIMEOUT_PREEMPTION_CANCELLED_LOSER_NOT_ACCOUNTED", f"superseded/race job absent: {required_job}")
    if registry.get("superseded_attempts_reconciled") is not True:
        add(errors, "SUPERSEDED_RECEIPT_NOT_RECONCILED", "superseded receipt reconciliation false")

    if validator.get("status") != "PASS" or validator.get("semantic_checks_performed") is not True or validator.get("only_file_existence") is True:
        add(errors, "VALIDATOR_FILE_EXISTENCE_ONLY", "validator packet report lacks semantic checks")
    if known_bad.get("status") != "PASS":
        add(errors, "VALIDATOR_FILE_EXISTENCE_ONLY", "B10 known-bad report is not PASS")
    if heavy.get("status") != "PASS" or heavy.get("tracked_heavy_artifacts"):
        add(errors, "HEAVY_ARTIFACT_TRACKED", "tracked heavy artifacts present")

    forbidden = state.get("forbidden_actions", {})
    for key, value in forbidden.items():
        if value is not False:
            add(errors, "CONTROLLER_PUSH_OR_REVIEW_AUTHORITY_VIOLATION", f"forbidden action set: {key}")
    for name in ("result.md", "controller_report.md", "completion_check.md", "review_request.md", "MANIFEST.md"):
        if root_manifest.get(name, {}).get("present") is not True:
            add(errors, "AGGREGATION_MISSING_OR_NONZERO", f"root packet sidecar missing: {name}")

    return {
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "failure_keys": sorted({e["key"] for e in errors}),
        "completion_token": completion.get("completion_token"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--require-token", default=READY_TOKEN)
    args = parser.parse_args()
    report = validate(args.input, args.require_token)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if args.strict and report["status"] != "PASS" else 0


if __name__ == "__main__":
    raise SystemExit(main())
