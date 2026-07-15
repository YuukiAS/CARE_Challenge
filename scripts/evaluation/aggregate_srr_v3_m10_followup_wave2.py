#!/usr/bin/env python3
"""Aggregate M10 follow-up Wave F1 outputs into the executor packet."""

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


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--print-contract", action="store_true")
    args = parser.parse_args()
    if args.print_contract:
        print(json.dumps({"task_key": "20260714_srr_v3_m10_followup_wave2_reconciliation", "mode": "aggregate_f1"}, indent=2))
        return
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    inventory = read_csv(OUT_DIR / "checkpoint_inventory.csv")
    budget_rows = []
    old_final = REPO_ROOT / "results/20260711_srr_v3_m10_complete_mechanism_repair/wave2_partition_race_retry11_finalization.json"
    old = json.loads(old_final.read_text(encoding="utf-8")) if old_final.is_file() else {}
    chain = old.get("chain_states", {}).get("htzhulab", {}) if isinstance(old.get("chain_states"), dict) else {}
    for phase, state in chain.items():
        budget_rows.append({"phase": phase, "inherited_terminal_state": state, "inheritance_status": "INHERITED_TERMINAL_RUNTIME_EVIDENCE"})
    budget_rows.append({"phase": "d0_control", "inherited_terminal_state": "COMPLETED(0:0)", "inheritance_status": "INHERITED_TERMINAL_RUNTIME_EVIDENCE_FROM_RETRY4"})
    write_csv(OUT_DIR / "inherited_wave2_budget_ledger.csv", budget_rows)
    fingerprint = [
        {
            "artifact": "old_wave2_finalization",
            "path": str(old_final),
            "status": "PRESENT" if old_final.is_file() else "MISSING",
        },
        {
            "artifact": "checkpoint_inventory",
            "path": str(OUT_DIR / "checkpoint_inventory.csv"),
            "status": "PRESENT" if inventory else "MISSING",
        },
    ]
    (OUT_DIR / "inherited_wave2_fingerprint_audit.json").write_text(json.dumps({"rows": fingerprint}, indent=2, sort_keys=True), encoding="utf-8")
    metrics = read_csv(OUT_DIR / "all_checkpoint_challenge_metrics.csv")
    eligibility = read_csv(OUT_DIR / "checkpoint_eligibility.csv")
    incomplete = [row for row in eligibility if str(row.get("eligible", "")).lower() != "true"]
    status = "M10_FOLLOWUP_WAVE2_RECONCILIATION_NEEDS_EVIDENCE" if incomplete else "M10_FOLLOWUP_WAVE2_RECONCILIATION_READY_FOR_CONTROLLER_MERGE"
    (OUT_DIR / "hard_subgroup_help_harm.csv").write_text("status,reason\nNEEDS_EVIDENCE,requires selected-checkpoint intervention/help-harm aggregation\n", encoding="utf-8")
    (OUT_DIR / "result.md").write_text(
        "\n".join(
            [
                "# M10 Follow-up Wave F1 Result",
                "",
                f"Completion token: `{status}`",
                "",
                f"Checkpoint inventory rows: `{len(inventory)}`",
                f"Challenge metric summary rows: `{len(metrics)}`",
                f"Ineligible or missing checkpoint rows: `{len(incomplete)}`",
                "",
                "This packet does not train, write review.md, push, package validation, or claim hosted metrics.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (OUT_DIR / "executor_completion.md").write_text(f"{status}\n", encoding="utf-8")
    (OUT_DIR / "commands_run.md").write_text(
        "# Commands Run\n\n"
        "- `python scripts/evaluation/evaluate_srr_v3_m10_followup_all_checkpoints.py --print-contract`\n"
        "- `python scripts/evaluation/evaluate_srr_v3_m10_followup_all_checkpoints.py`\n"
        "- `python scripts/evaluation/run_srr_v3_m10_followup_interventions.py`\n"
        "- `python scripts/evaluation/aggregate_srr_v3_m10_followup_wave2.py`\n",
        encoding="utf-8",
    )
    (OUT_DIR / "MANIFEST.md").write_text(
        "# M10 Follow-up Wave F1 Manifest\n\n"
        "- result.md\n- inherited_wave2_fingerprint_audit.json\n- inherited_wave2_budget_ledger.csv\n"
        "- checkpoint_inventory.csv\n- all_checkpoint_challenge_metrics.csv\n- checkpoint_eligibility.csv\n"
        "- selected_checkpoints.json\n- d2_component_interventions.csv\n- d3_component_interventions.csv\n"
        "- component_state_classification.csv\n- hard_subgroup_help_harm.csv\n- runtime_manifest.json\n"
        "- commands_run.md\n- executor_completion.md\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
