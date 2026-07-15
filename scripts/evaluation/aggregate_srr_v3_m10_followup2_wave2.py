#!/usr/bin/env python3
"""Aggregate M10 follow-up2 Wave 2 evidence repair packet."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = REPO_ROOT / "results/20260715_srr_v3_m10_followup2_wave2_evidence_repair"


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
    parser.add_argument("--result-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--print-contract", action="store_true")
    args = parser.parse_args()
    out_dir = Path(args.result_dir)
    if not out_dir.is_absolute():
        out_dir = REPO_ROOT / out_dir
    if args.print_contract:
        print(json.dumps({"task_key": out_dir.name, "mode": "aggregate_followup2_wave2", "strict": args.strict}, indent=2))
        return
    out_dir.mkdir(parents=True, exist_ok=True)
    eligibility = read_csv(out_dir / "checkpoint_eligibility.csv")
    d2 = read_csv(out_dir / "d2_component_interventions.csv")
    d3 = read_csv(out_dir / "d3_component_interventions.csv")
    blockers = []
    if not eligibility:
        blockers.append("missing_checkpoint_eligibility")
    blockers.extend(row.get("exclusion_reason", "") for row in eligibility if str(row.get("eligible", "")).lower() != "true")
    for row in d2 + d3:
        status = row.get("status", "")
        if status != "INTERVENTION_EVALUATED":
            blockers.append(status or "missing_intervention_status")
    state = "M10_FOLLOWUP2_WAVE2_EVIDENCE_READY_FOR_CONTROLLER_MERGE" if not blockers else "M10_FOLLOWUP2_WAVE2_EVIDENCE_NEEDS_REVISION"
    if any("raw_logit_or_probability_manifest_missing" in item for item in blockers):
        state = "M10_FOLLOWUP2_WAVE2_EVIDENCE_NEEDS_EVIDENCE"
    (out_dir / "result.md").write_text(
        "\n".join(
            [
                "# M10 Follow-up2 Wave 2 Evidence Repair",
                "",
                f"Completion token: `{state}`",
                "",
                f"Checkpoint eligibility rows: `{len(eligibility)}`",
                f"D2 intervention rows: `{len(d2)}`",
                f"D3 intervention rows: `{len(d3)}`",
                f"Blocker count: `{len([x for x in blockers if x])}`",
                "",
                "No training, validation packaging, upload, push, or review.md was produced by this packet.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (out_dir / "executor_completion.md").write_text(state + "\n", encoding="utf-8")
    (out_dir / "commands_run.md").write_text(
        "# Commands Run\n\n"
        "- `python scripts/evaluation/evaluate_srr_v3_m10_followup2_all_checkpoints.py --print-contract`\n"
        "- formal replay requires `--evaluate --force` under Slurm\n"
        "- `python scripts/evaluation/run_srr_v3_m10_followup2_interventions.py`\n"
        "- `python scripts/evaluation/aggregate_srr_v3_m10_followup2_wave2.py --strict`\n",
        encoding="utf-8",
    )
    (out_dir / "MANIFEST.md").write_text(
        "# M10 Follow-up2 Wave 2 Manifest\n\n"
        "- result.md\n- inherited_runtime_fingerprint_ledger.csv\n- checkpoint_inventory.csv\n"
        "- calibration_freeze_receipt.json\n- checkpoint_replay_ledger.csv\n- checkpoint_replay_receipts.jsonl\n"
        "- checkpoint_raw_output_manifest.csv\n- all_checkpoint_case_metrics.csv\n- all_checkpoint_subgroup_metrics.csv\n"
        "- checkpoint_eligibility.csv\n- checkpoint_selector_recalculation.csv\n- selected_checkpoints.json\n"
        "- selected_checkpoint_reload_receipts.json\n- d2_component_interventions.csv\n- d3_component_interventions.csv\n"
        "- d2_intervention_output_manifest.csv\n- d3_intervention_output_manifest.csv\n- component_state_classification.csv\n"
        "- hard_subgroup_help_harm.csv\n- no_t2_safety_report.csv\n- validator_report.md\n- validator_report.csv\n"
        "- known_bad_selftest_report.md\n- commands_run.md\n- runtime_manifest.json\n- executor_completion.md\n",
        encoding="utf-8",
    )
    write_csv(out_dir / "validator_report.csv", [{"status": "PENDING_VALIDATOR", "blocker_count": len([x for x in blockers if x])}])
    raise SystemExit(0 if not args.strict or state.endswith("READY_FOR_CONTROLLER_MERGE") else 2)


if __name__ == "__main__":
    main()
