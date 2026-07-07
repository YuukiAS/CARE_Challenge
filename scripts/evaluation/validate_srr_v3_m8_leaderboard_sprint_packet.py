#!/usr/bin/env python3
"""Fail-closed validator for SRR-v3 M8 leaderboard sprint packets."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path


READY_STATE = "M8_READY_FOR_REVIEW"
MONITOR_TOKENS = {
    "PENDING_MONITOR",
    "NEEDS_MONITOR",
    "JOB_SUBMITTED",
    "PENDING_PRIORITY",
    "RUNNING",
    "AWAITING_SACCT",
    "AWAITING_RUNTIME_AGGREGATION",
}
ALLOWED_STATES = {
    READY_STATE,
    "M8_NEEDS_MONITOR_NO_REVIEW",
    "M8_RESOURCE_BLOCKED",
    "M8_NEEDS_REVISION_TRAINING_UNDERRUN",
    "M8_NEEDS_REVISION_ARCHITECTURE_GAP",
    "M8_NEEDS_EVIDENCE_UNDERTRAINED",
    "M8_NEEDS_EVIDENCE_METRICS_INCOMPLETE",
    "M8_NEEDS_EVIDENCE_CINE_REGISTRATION",
    "M8_NEEDS_REVISION",
    "M8_BLOCKED_BY_M7",
}

REQUIRED_READY_FILES = [
    "result.md",
    "completion_check.md",
    "review_request.md",
    "MANIFEST.md",
    "commands_run.md",
    "m8_training_budget_ledger.csv",
    "m8_variant_config_contract.json",
    "m8_variant_matrix.csv",
    "m8_architecture_gap_closure_table.csv",
    "m8_batch_composition.csv",
    "m8_srr_contribution_by_case.csv",
    "m8_same_split_help_harm.csv",
    "m8_registration_same_subset_matrix.csv",
    "m8_temporal_dictionary_evidence.csv",
    "m8_label_export_dry_run_qc.md",
    "m8_official_label_mapping_qc.csv",
]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def completion_state(packet: Path) -> str:
    text = read_text(packet / "completion_check.md")
    match = re.search(r"status:\s*`?([A-Z0-9_]+)`?", text)
    return match.group(1) if match else "EVIDENCE_NOT_FOUND"


def numeric(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def validate(packet: Path) -> list[str]:
    errors: list[str] = []
    state = completion_state(packet)
    if state not in ALLOWED_STATES:
        errors.append(f"completion_check.md has invalid or missing status: {state}")

    all_text = "\n".join(
        read_text(path)
        for path in packet.glob("*.md")
        if path.name not in {"m8_strict_validator_report.md", "m8_validator_unit_test_report.md"}
    )
    forbidden_claims = [
        "validation upload",
        "hosted metric claim",
        "challenge-ready",
        "leaderboard-ready",
        "M9",
    ]
    if state == READY_STATE:
        for token in MONITOR_TOKENS:
            if token in all_text:
                errors.append(f"ready packet contains monitor token {token}")
        for file_name in REQUIRED_READY_FILES:
            if not (packet / file_name).is_file():
                errors.append(f"ready packet missing required file {file_name}")
        ledger = read_csv(packet / "m8_training_budget_ledger.csv")
        included_seconds = 0.0
        for row in ledger:
            if str(row.get("included_in_8h_budget", "")).lower() in {"true", "1", "yes"}:
                value = numeric(row.get("train_loop_seconds", ""))
                if value is not None:
                    included_seconds += value
        if included_seconds < 28800.0:
            errors.append(f"ready packet has included train_loop_seconds {included_seconds:.1f} < 28800")
        try:
            contract = json.loads((packet / "m8_variant_config_contract.json").read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"variant config contract unreadable: {type(exc).__name__}")
            contract = {}
        variants = contract.get("variants") if isinstance(contract, dict) else {}
        if not isinstance(variants, dict) or len(variants) < 3:
            errors.append("variant config contract does not define three M8 variants")
        contribution = read_csv(packet / "m8_srr_contribution_by_case.csv")
        if not contribution:
            errors.append("m8_srr_contribution_by_case.csv has no rows")
        for row in contribution[:20]:
            if row.get("anchor_delta_rate") in {"", None, "EVIDENCE_NOT_EXPORTED_PER_CASE", "EVIDENCE_NOT_FOUND"}:
                errors.append("m8_srr_contribution_by_case.csv lacks real per-case anchor_delta_rate")
                break
        architecture = read_csv(packet / "m8_architecture_gap_closure_table.csv")
        bad_status = [row.get("closure_status", "") for row in architecture if row.get("closure_status") in {"CLOSED", "NEEDS_REVISION", "NEEDS_EVIDENCE"}]
        if bad_status:
            errors.append("architecture closure table contains bare/blocked closure statuses")
    else:
        if READY_STATE in all_text:
            errors.append(f"non-ready packet text contains {READY_STATE}")

    lower_text = all_text.lower()
    if "upload_ready/" in lower_text or "care-myocardium-organagent.zip" in lower_text:
        errors.append("packet references upload package path or zip")
    for phrase in forbidden_claims:
        if phrase in lower_text and "not " not in lower_text[max(0, lower_text.find(phrase) - 20): lower_text.find(phrase)]:
            errors.append(f"packet may contain forbidden claim: {phrase}")
    return errors


def write_reports(packet: Path, errors: list[str]) -> None:
    state = completion_state(packet)
    now = datetime.now(UTC).isoformat()
    rows = [{"status": state, "error_count": str(len(errors)), "error": error} for error in errors]
    if not rows:
        rows = [{"status": state, "error_count": "0", "error": ""}]
    write_csv(packet / "m8_strict_validator_report.csv", rows, ["status", "error_count", "error"])
    result = "pass" if not errors else "fail"
    error_text = "\n".join(f"- `{error}`" for error in errors) or "- none"
    (packet / "m8_strict_validator_report.md").write_text(
        "\n".join(
            [
                "# M8 Strict Validator Report",
                "",
                f"status: `{state}`",
                f"updated_at_utc: `{now}`",
                "",
                "Command:",
                "",
                "```bash",
                "PYTHONPATH=. python scripts/evaluation/validate_srr_v3_m8_leaderboard_sprint_packet.py --packet results/20260707_srr_v3_m8_editor_grade_leaderboard_sprint",
                "```",
                "",
                f"Result: `{result}`, `error_count={len(errors)}`.",
                "",
                "Interpretation: this validates the current packet state only. A non-ready status is not M8 completion.",
                "",
                "## Errors",
                error_text,
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", required=True)
    args = parser.parse_args()
    packet = Path(args.packet)
    if not packet.is_absolute():
        packet = Path.cwd() / packet
    errors = validate(packet)
    write_reports(packet, errors)
    print(json.dumps({"packet": str(packet), "error_count": len(errors), "errors": errors}, indent=2))
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
