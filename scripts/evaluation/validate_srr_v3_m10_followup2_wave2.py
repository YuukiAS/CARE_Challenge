#!/usr/bin/env python3
"""Strict validator for M10 follow-up2 Wave 2 evidence repair."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = REPO_ROOT / "results/20260715_srr_v3_m10_followup2_wave2_evidence_repair"


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_report(out_dir: Path, name: str, findings: list[str]) -> None:
    status = "PASS" if not findings else "FAIL"
    (out_dir / name).write_text(
        "# M10 Follow-up2 Wave 2 Validator\n\n"
        f"Status: `{status}`\n\n"
        + ("\n".join(f"- {item}" for item in findings) if findings else "No validator findings.\n"),
        encoding="utf-8",
    )
    rows = [{"status": status, "finding": item} for item in findings] or [{"status": status, "finding": ""}]
    fields = ["status", "finding"]
    with (out_dir / "validator_report.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def validate(out_dir: Path) -> list[str]:
    findings: list[str] = []
    required = [
        "result.md",
        "inherited_runtime_fingerprint_ledger.csv",
        "checkpoint_inventory.csv",
        "calibration_freeze_receipt.json",
        "checkpoint_replay_ledger.csv",
        "checkpoint_replay_receipts.jsonl",
        "all_checkpoint_case_metrics.csv",
        "checkpoint_eligibility.csv",
        "checkpoint_selector_recalculation.csv",
        "selected_checkpoints.json",
        "d2_component_interventions.csv",
        "d3_component_interventions.csv",
        "component_state_classification.csv",
        "hard_subgroup_help_harm.csv",
        "no_t2_safety_report.csv",
        "commands_run.md",
        "runtime_manifest.json",
        "executor_completion.md",
        "MANIFEST.md",
    ]
    for name in required:
        if not (out_dir / name).is_file():
            findings.append(f"missing required output: {name}")
    if (out_dir / "review.md").exists():
        findings.append("review.md exists but executor/controller must not write it")
    inventory = read_csv(out_dir / "checkpoint_inventory.csv")
    if inventory and any(row.get("old_candidate_metrics_used") != "false" for row in inventory):
        findings.append("historical candidate metrics were marked as used")
    eligibility = read_csv(out_dir / "checkpoint_eligibility.csv")
    if not eligibility:
        findings.append("checkpoint eligibility table missing or empty")
    for row in eligibility:
        if str(row.get("eligible", "")).lower() != "true":
            findings.append(f"ineligible checkpoint {row.get('phase')}::{row.get('checkpoint_name')}: {row.get('exclusion_reason')}")
    for name in ("d2_component_interventions.csv", "d3_component_interventions.csv"):
        for row in read_csv(out_dir / name):
            if row.get("status") != "INTERVENTION_EVALUATED":
                findings.append(f"{name} intervention not evaluated: {row.get('phase')}::{row.get('intervention')} status={row.get('status')}")
            if row.get("intervention") == "no_op_control" and row.get("changed_voxels") not in {"0", 0}:
                findings.append("no_op_control changed final output")
            if row.get("intervention") == "swapped_positive_negative_known_bad" and row.get("changed_voxels") in {"", "0", 0}:
                findings.append("known-bad intervention had no final-output effect")
    token_path = out_dir / "executor_completion.md"
    if token_path.is_file():
        token = token_path.read_text(encoding="utf-8").strip()
        if token != "M10_FOLLOWUP2_WAVE2_EVIDENCE_READY_FOR_CONTROLLER_MERGE":
            findings.append(f"completion token is not ready: {token}")
    return findings


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--known-bad-selftest", action="store_true")
    args = parser.parse_args()
    out_dir = Path(args.result_dir)
    if not out_dir.is_absolute():
        out_dir = REPO_ROOT / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    if args.known_bad_selftest:
        write_report(out_dir, "known_bad_selftest_report.md", ["known-bad fixture generation is not yet implemented for followup2"])
        raise SystemExit(2)
    findings = validate(out_dir)
    write_report(out_dir, "validator_report.md", findings)
    raise SystemExit(0 if not findings else 2)


if __name__ == "__main__":
    main()
