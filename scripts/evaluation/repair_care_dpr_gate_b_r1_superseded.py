#!/usr/bin/env python3
"""Mark CARE-DPR Gate B-R1 superseded by B-R2 using existing R1 evidence only."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.evaluation.care_dpr_gate_b_science import scientific_gate_from_casewise

TASK_KEY = "20260728_care_dpr_fold0_global_redesign"
RESULT_ROOT = REPO_ROOT / "results" / TASK_KEY
MODEL_NAME = "A2_care_dpr_gate_b_r1_selected"

SUPERSEDE_REASONS = [
    "complete16 scar, edema-zone, and pure-edema Dice did not reach +0.005",
    "scientific gate omitted the at-least-one-pathology Dice improvement >= +0.005 requirement",
    "validator did not independently recompute the scientific gate",
    "utility regression minimum was added without contract authorization",
]


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise FileNotFoundError(path)
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def mark_payload(payload: dict[str, Any], *, superseded_at: str) -> dict[str, Any]:
    out = dict(payload)
    old_status = out.get("status")
    out.update(
        {
            "status": "SUPERSEDED_BY_DPR_GATE_B_R2",
            "superseded_by": "DPR_GATE_B_R2",
            "superseded_at_utc": superseded_at,
            "previous_status": old_status,
            "scientific_final_output_credit": 0,
            "fold_expansion_authorized": False,
            "formal_expansion_authorized": False,
            "all_data_fit_authorized": False,
            "validation_upload_authorized": False,
            "approval_token_valid": False,
            "approve_dpr_gate_b_r1_accepted": False,
            "reason": SUPERSEDE_REASONS,
        }
    )
    return out


def repair(args: argparse.Namespace) -> dict[str, Any]:
    result_root = Path(args.result_root)
    runtime_root = Path(args.runtime_root) if args.runtime_root else result_root / "runtime" / args.runtime_name
    eval_root = runtime_root / "gate_b_r1_evaluation"
    casewise = read_csv(eval_root / "gate_b_r1_casewise_metrics.csv")
    model_summary = read_csv(eval_root / "gate_b_r1_model_summary.csv")
    no_t2 = read_csv(eval_root / "gate_b_r1_no_t2_safety_audit.csv")
    gate, help_harm = scientific_gate_from_casewise(
        casewise,
        no_t2,
        population="fold0_complete_trimodal16",
        model_name=MODEL_NAME,
    )
    if "no_pathology_improves_by_at_least_0.005" not in gate["failures"]:
        raise RuntimeError("R1 existing evidence unexpectedly satisfies +0.005 improvement requirement")
    gate["status"] = "FAIL"
    gate["scientific_final_output_credit"] = 0
    gate["fold_expansion_authorized"] = False
    gate["recomputed_from_existing_r1_files_only"] = True
    gate["outer_fold0_rerun"] = False

    superseded_at = now_utc()
    summary_path = eval_root / "gate_b_r1_summary.json"
    root_summary_path = result_root / "gate_b_r1_summary.json"
    summary = read_json(summary_path)
    summary = mark_payload(summary, superseded_at=superseded_at)
    summary["scientific_gate"] = gate
    summary["gate_b_r2_repair_required"] = True
    summary["development_evidence_only"] = True
    summary["r1_existing_evidence_files_reused"] = {
        "casewise": str((eval_root / "gate_b_r1_casewise_metrics.csv").relative_to(REPO_ROOT)),
        "model_summary": str((eval_root / "gate_b_r1_model_summary.csv").relative_to(REPO_ROOT)),
        "no_t2": str((eval_root / "gate_b_r1_no_t2_safety_audit.csv").relative_to(REPO_ROOT)),
    }
    summary["model_summary_rows_read"] = len(model_summary)

    root_summary = dict(summary)
    root_summary["evidence_root"] = str(eval_root.relative_to(REPO_ROOT))
    write_csv(eval_root / "gate_b_r1_help_harm.csv", help_harm)
    write_json(eval_root / "gate_b_r1_scientific_gate.json", gate)
    write_json(summary_path, summary)
    write_json(root_summary_path, root_summary)

    node_path = result_root / "checkpoint_notifications" / "dpr_gate_b_r1.json"
    if node_path.is_file():
        node = mark_payload(read_json(node_path), superseded_at=superseded_at)
        node["gate_summary"] = root_summary
        write_json(node_path, node)
    receipt_path = result_root / "checkpoint_notifications" / "dpr_gate_b_r1_send_receipt.json"
    if receipt_path.is_file():
        receipt = mark_payload(read_json(receipt_path), superseded_at=superseded_at)
        write_json(receipt_path, receipt)
    superseded_packet = {
        "task_key": TASK_KEY,
        "gate": "DPR_GATE_B_R1",
        "status": "SUPERSEDED_BY_DPR_GATE_B_R2",
        "superseded_at_utc": superseded_at,
        "scientific_final_output_credit": 0,
        "fold_expansion_authorized": False,
        "formal_expansion_authorized": False,
        "reason": SUPERSEDE_REASONS,
        "scientific_gate": gate,
        "outer_fold0_rerun": False,
        "source_evidence": summary["r1_existing_evidence_files_reused"],
    }
    write_json(result_root / "gate_b_r1_superseded_by_r2.json", superseded_packet)
    return superseded_packet


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-root", default=str(RESULT_ROOT))
    parser.add_argument("--runtime-name", default="formal_fold0_r1")
    parser.add_argument("--runtime-root", default="")
    args = parser.parse_args()
    report = repair(args)
    print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
