#!/usr/bin/env python3
"""Strict validator for M10 follow-up Wave F1 packet."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "results/20260714_srr_v3_m10_followup_wave2_reconciliation"


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    findings: list[str] = []
    required = [
        "inherited_wave2_fingerprint_audit.json",
        "inherited_wave2_budget_ledger.csv",
        "checkpoint_inventory.csv",
        "all_checkpoint_challenge_metrics.csv",
        "checkpoint_eligibility.csv",
        "selected_checkpoints.json",
        "d2_component_interventions.csv",
        "d3_component_interventions.csv",
        "component_state_classification.csv",
        "hard_subgroup_help_harm.csv",
        "runtime_manifest.json",
        "commands_run.md",
        "executor_completion.md",
        "MANIFEST.md",
    ]
    for name in required:
        if not (OUT_DIR / name).is_file():
            findings.append(f"missing required output: {name}")
    inventory = read_csv(OUT_DIR / "checkpoint_inventory.csv")
    if inventory and any(row.get("legacy_checkpoint_selection_mode") == "legacy_val_patch_loss" for row in inventory):
        pass
    elif inventory:
        findings.append("inventory did not expose legacy selector status")
    eligibility = read_csv(OUT_DIR / "checkpoint_eligibility.csv")
    if eligibility and all(str(row.get("eligible", "")).lower() == "true" for row in eligibility):
        token = (OUT_DIR / "executor_completion.md").read_text(encoding="utf-8").strip()
        if token != "M10_FOLLOWUP_WAVE2_RECONCILIATION_READY_FOR_CONTROLLER_MERGE":
            findings.append("all checkpoints eligible but completion token is not ready")
    if (OUT_DIR / "review.md").exists():
        findings.append("review.md exists but controller/executor must not write it")
    report_name = "validator_selftest_report.md" if args.selftest else "validator_report.md"
    status = "PASS" if not findings else "FAIL"
    (OUT_DIR / report_name).write_text(
        "# M10 Follow-up Wave F1 Validator\n\n"
        f"Status: `{status}`\n\n"
        + ("\n".join(f"- {item}" for item in findings) if findings else "No validator findings.\n"),
        encoding="utf-8",
    )
    raise SystemExit(0 if not findings else 2)


if __name__ == "__main__":
    main()
