#!/usr/bin/env python3
"""Validate Route B Round03 terminal controller packet."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.route_B_round03.runtime_common import expected_frozen_sampler_counts  # noqa: E402


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

TERMINAL_STATES = ("COMPLETED", "FAILED", "CANCELLED", "TIMEOUT", "PREEMPTED", "OUT_OF_MEMORY", "NODE_FAIL", "BOOT_FAIL")


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def is_terminal_state(state: str) -> bool:
    upper = state.upper()
    return any(upper.startswith(term) for term in TERMINAL_STATES)


def sacct_terminal(job_ids: list[str]) -> set[str]:
    if not job_ids or shutil.which("sacct") is None:
        return set()
    proc = subprocess.run(
        ["sacct", "-j", ",".join(job_ids), "--format=JobID,State", "-P", "-n"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    terminal: set[str] = set()
    if proc.returncode != 0:
        return terminal
    for line in proc.stdout.splitlines():
        parts = line.split("|")
        if len(parts) < 2:
            continue
        base_id = parts[0].split(".", 1)[0]
        if is_terminal_state(parts[1]):
            terminal.add(base_id)
    return terminal


def validate_accounting(route_root: Path, b10: Path) -> list[str]:
    errors: list[str] = []
    controller_rows = read_csv(route_root / "round03/controller_ledger.csv")
    routing_rows = read_csv(b10 / "routing_ledger.csv")
    if not controller_rows:
        errors.append("missing_controller_ledger_rows")
    if not routing_rows:
        errors.append("missing_routing_ledger_rows")
    if controller_rows and routing_rows and controller_rows != routing_rows:
        errors.append("routing_ledger_not_controller_ledger_copy")
    rows = routing_rows or controller_rows
    job_ids = sorted({row.get("job_id", "").strip() for row in rows if row.get("job_id", "").strip()})
    terminal_from_receipts = {
        row.get("job_id", "").strip()
        for row in rows
        if row.get("job_id", "").strip() and is_terminal_state(row.get("state", ""))
    }
    missing_terminal = sorted(set(job_ids) - terminal_from_receipts)
    if missing_terminal:
        terminal_from_slurm = sacct_terminal(missing_terminal)
        missing_terminal = sorted(set(missing_terminal) - terminal_from_slurm)
    for job_id in missing_terminal:
        errors.append(f"attempt_missing_terminal_accounting:{job_id}")
    finalizer = read_json(b10 / "finalizer_state.json")
    coverage = finalizer.get("finalizer_dependency_coverage", {})
    covered = {str(v) for v in coverage.get("covered_job_ids", [])}
    if job_ids and covered != set(job_ids):
        errors.append("finalizer_dependency_coverage_job_id_mismatch")
    if job_ids and coverage.get("dependency") != "afterany_all_started_attempts":
        errors.append("finalizer_dependency_not_afterany_all_started_attempts")
    return errors


def validate_b3_sampler(route_root: Path) -> list[str]:
    errors: list[str] = []
    b3 = route_root / "round03/executors/B3"
    payload = read_json(b3 / "completion.json")
    if not payload:
        return ["b3_completion_missing"]
    for name in ("sampler_counts.csv", "sampler_sequence_prefix.csv", "sampler_sequence_receipt.json"):
        if not (b3 / name).is_file():
            errors.append(f"b3_missing_sampler_evidence:{name}")
    steps = int(payload.get("optimizer_steps", 0))
    counts = payload.get("sampler_counts", {})
    expected = payload.get("expected_sampler_counts") or expected_frozen_sampler_counts(steps)
    if counts != expected:
        errors.append("b3_frozen_sampler_counts_mismatch")
    contract = payload.get("sampler_contract", {})
    if contract.get("draw_cycle") != ["E", "E", "S", "R"]:
        errors.append("b3_frozen_sampler_bad_draw_cycle")
    if contract.get("rng") != "numpy.random.Philox" or contract.get("philox_seed") != 26071821:
        errors.append("b3_frozen_sampler_bad_rng_or_seed")
    if contract.get("with_replacement") is not True:
        errors.append("b3_frozen_sampler_not_with_replacement")
    if int(contract.get("cycle_mismatch_count", -1)) != 0:
        errors.append("b3_frozen_sampler_sequence_mismatch")
    if not contract.get("trace_sha256"):
        errors.append("b3_frozen_sampler_missing_trace_sha256")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--require-all-attempt-accounting", action="store_true")
    parser.add_argument("packet_dir", type=Path)
    args = parser.parse_args()
    errors: list[str] = []
    b10 = args.packet_dir
    route_root = b10.parents[2] if b10.name == "B10" else Path("results/route_B")
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
            if payload.get("blocked_at_stage") == "B3":
                errors.extend(validate_b3_sampler(route_root))
                b3 = read_json(route_root / "round03/executors/B3/completion.json")
                if b3.get("status") != "FAIL":
                    errors.append("b3_terminal_negative_status_not_fail")
                if b3.get("optimizer_steps", 0) < b3.get("required_optimizer_steps", 10**12):
                    errors.append("b3_terminal_negative_under_steps")
                if b3.get("train_loop_seconds", 0.0) < b3.get("required_train_loop_seconds", 10**12):
                    errors.append("b3_terminal_negative_under_seconds")
                if b3.get("validation_events", 0) < b3.get("required_validation_events", 10**12):
                    errors.append("b3_terminal_negative_under_validations")
        if payload.get("heavy_artifact_scan", {}).get("status") != "PASS":
            errors.append("tracked_heavy_artifacts_present")
        forbidden = payload.get("forbidden_actions", {})
        for key, value in forbidden.items():
            if value is not False:
                errors.append(f"forbidden_action_performed:{key}")
        rows = payload.get("validator_rows", [])
        successful_commands = [str(row.get("command", "")) for row in rows if int(row.get("exit_code", 1)) == 0]
        if not any("git diff --check" in command for command in successful_commands):
            errors.append("missing_successful_git_diff_check_evidence")
        if not any("validate_care_architecture_wiki.py" in command for command in successful_commands):
            errors.append("missing_successful_architecture_validator_evidence")
        packet_report = read_json(b10 / "validator_packet_report.json")
        if packet_report.get("status") != "PASS":
            errors.append("validator_packet_report_not_pass")
    if args.require_all_attempt_accounting:
        errors.extend(validate_accounting(route_root, b10))
    completion_text = (route_root / "completion_check.md").read_text(encoding="utf-8") if (route_root / "completion_check.md").is_file() else ""
    for bad in ("NEEDS_MONITOR", "PENDING_MONITOR", "JOB_SUBMITTED", "RUNNING", "AWAITING_SACCT"):
        if "ROUTE_B_ROUND03_TERMINAL_PACKET_READY_FOR_REVIEW" in completion_text and bad in completion_text:
            errors.append(f"ready_completion_contains_monitor_state:{bad}")
    status = "PASS" if not errors else "FAIL"
    print(json.dumps({"status": status, "errors": errors, "completion_token": payload.get("completion_token")}, indent=2, sort_keys=True))
    return 1 if args.strict and errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
