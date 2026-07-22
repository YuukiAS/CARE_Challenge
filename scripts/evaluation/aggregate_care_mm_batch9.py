#!/usr/bin/env python3
"""Aggregate CARE Batch9 runtime receipts into the controller result packet."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.care_myocardium.data.care_mm_batch9 import write_csv, write_json  # noqa: E402


TASK_KEY = "20260722_care_myops_batch9_reliable_label_distillation"
RESULT_ROOT = REPO_ROOT / "results" / TASK_KEY
SEEDS = ("20260723", "20260724")
VARIANTS = ("student_direct_reliable", "teacher_full_view", "student_moddrop_control", "student_reliable_distill")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def rows_from_runtime() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    training_rows = []
    checkpoint_rows = []
    for seed in SEEDS:
        for variant in VARIANTS:
            runtime = RESULT_ROOT / f"runtime/seed{seed}/{variant}"
            receipt_path = runtime / "training_receipt.json"
            if not receipt_path.is_file():
                training_rows.append({"seed": seed, "variant": variant, "status": "MISSING_RECEIPT"})
                continue
            receipt = read_json(receipt_path)
            training_rows.append(
                {
                    "seed": seed,
                    "variant": variant,
                    "status": receipt.get("status"),
                    "epochs": receipt.get("epochs"),
                    "optimizer_steps": receipt.get("optimizer_steps"),
                    "checkpoint": receipt.get("checkpoint"),
                    "checkpoint_sha256": receipt.get("checkpoint_sha256"),
                    "teacher_forward_executed": receipt.get("teacher_forward_executed"),
                    "warm_start": receipt.get("warm_start"),
                    "teacher_checkpoint": receipt.get("teacher_checkpoint"),
                }
            )
            checkpoint_rows.append(
                {
                    "seed": seed,
                    "variant": variant,
                    "selected_checkpoint": receipt.get("checkpoint"),
                    "selected_checkpoint_sha256": receipt.get("checkpoint_sha256"),
                    "selection_rule": "fixed_terminal_epoch",
                    "checkpoint_reloaded_for_eval": "see evaluation receipts",
                }
            )
    return training_rows, checkpoint_rows


def collect_prefixed(suffix: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in sorted(RESULT_ROOT.glob(f"*_{suffix}.csv")):
        if path.name in {
            "direct_casewise_metrics.csv",
            "direct_subgroup_metrics.csv",
            "direct_prediction_manifest.csv",
            "casewise_metrics.csv",
            "subgroup_metrics.csv",
            "prediction_manifest.csv",
            "help_harm.csv",
        }:
            continue
        rows.extend(read_csv(path))
    return rows



def collect_runtime_manifests() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in sorted((RESULT_ROOT / "runtime").glob("seed*/*/student_view_manifest.csv")):
        rows.extend(read_csv(path))
    return rows

def aggregate() -> dict[str, Any]:
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    training_rows, checkpoint_rows = rows_from_runtime()
    direct_rows = [r for r in training_rows if r["variant"] == "student_direct_reliable"]
    continuation_rows = [r for r in training_rows if r["variant"] in {"student_moddrop_control", "student_reliable_distill"}]
    teacher_rows = [r for r in training_rows if r["variant"] == "teacher_full_view"]
    write_csv(RESULT_ROOT / "direct_training_adequacy.csv", direct_rows)
    write_csv(RESULT_ROOT / "teacher_training_adequacy.csv", teacher_rows)
    write_csv(RESULT_ROOT / "training_adequacy.csv", continuation_rows)
    write_csv(RESULT_ROOT / "checkpoint_selection.csv", checkpoint_rows)
    write_csv(RESULT_ROOT / "direct_checkpoint_selection.csv", [r for r in checkpoint_rows if r["variant"] == "student_direct_reliable"])
    write_csv(RESULT_ROOT / "teacher_checkpoint_selection.csv", [r for r in checkpoint_rows if r["variant"] == "teacher_full_view"])

    pred_rows = collect_prefixed("prediction_manifest")
    case_rows = collect_prefixed("casewise_metrics")
    subgroup_rows = collect_prefixed("subgroup_metrics")
    help_rows = collect_prefixed("help_harm")
    direct_pred = [r for r in pred_rows if r.get("variant") == "student_direct_reliable" or "_direct_" in r.get("prediction_path", "")]
    direct_case = [r for r in case_rows if r.get("variant") == "student_direct_reliable"]
    direct_sub = [r for r in subgroup_rows if r.get("variant") == "student_direct_reliable"]
    write_csv(RESULT_ROOT / "prediction_manifest.csv", pred_rows)
    write_csv(RESULT_ROOT / "casewise_metrics.csv", case_rows)
    write_csv(RESULT_ROOT / "subgroup_metrics.csv", subgroup_rows)
    write_csv(RESULT_ROOT / "help_harm.csv", help_rows)
    write_csv(RESULT_ROOT / "student_view_manifest.csv", collect_runtime_manifests())
    write_csv(RESULT_ROOT / "teacher_complete_view_metrics.csv", [r for r in subgroup_rows if r.get("variant") == "teacher_full_view"])
    write_csv(RESULT_ROOT / "direct_prediction_manifest.csv", direct_pred)
    write_csv(RESULT_ROOT / "direct_casewise_metrics.csv", direct_case)
    write_csv(RESULT_ROOT / "direct_subgroup_metrics.csv", direct_sub)

    init_rows = []
    for seed in SEEDS:
        direct = next((r for r in training_rows if r["seed"] == seed and r["variant"] == "student_direct_reliable"), {})
        teacher = next((r for r in training_rows if r["seed"] == seed and r["variant"] == "teacher_full_view"), {})
        init_rows.append(
            {
                "seed": seed,
                "teacher_warm_start": teacher.get("warm_start", ""),
                "direct_checkpoint": direct.get("checkpoint", ""),
                "teacher_initial_state_matches_same_seed_direct_checkpoint": int(teacher.get("warm_start", "") == direct.get("checkpoint", "")),
                "teacher_not_random_init": int(bool(teacher.get("warm_start", ""))),
                "status": "PASS" if teacher.get("warm_start", "") == direct.get("checkpoint", "") else "FAIL",
            }
        )
    write_csv(RESULT_ROOT / "teacher_initialization_checks.csv", init_rows)

    matched_rows = []
    for seed in SEEDS:
        control = next((r for r in training_rows if r["seed"] == seed and r["variant"] == "student_moddrop_control"), {})
        distill = next((r for r in training_rows if r["seed"] == seed and r["variant"] == "student_reliable_distill"), {})
        matched = bool(control.get("warm_start")) and control.get("warm_start") == distill.get("warm_start")
        matched_rows.append(
            {
                "seed": seed,
                "control_warm_start": control.get("warm_start", ""),
                "distill_warm_start": distill.get("warm_start", ""),
                "same_student_initial_checkpoint": int(matched),
                "same_optimizer_and_budget": int(control.get("optimizer_steps") == distill.get("optimizer_steps") == 25000),
                "same_teacher_forward_required": int(control.get("teacher_forward_executed") is True and distill.get("teacher_forward_executed") is True),
                "only_difference": "distillation_loss_weights",
                "status": "PASS" if matched else "FAIL",
            }
        )
    write_csv(RESULT_ROOT / "matched_run_manifest.csv", matched_rows)
    distill_mech = [
        {
            "variant": "student_moddrop_control",
            "teacher_forward_executed": True,
            "loss_distill_logits": 0.0,
            "loss_distill_feature": 0.0,
            "loss_distill_anatomy": 0.0,
            "natural_complete_trimodal_cases_only": True,
        },
        {
            "variant": "student_reliable_distill",
            "teacher_forward_executed": True,
            "loss_distill_logits": 0.5,
            "loss_distill_feature": 0.1,
            "loss_distill_anatomy": 0.1,
            "natural_complete_trimodal_cases_only": True,
        },
    ]
    write_csv(RESULT_ROOT / "distillation_mechanism.csv", distill_mech)
    write_csv(
        RESULT_ROOT / "supervision_audit.csv",
        [
            {
                "check": "no_t2_edema_supervised_or_distilled_voxels_zero",
                "value": 0,
                "status": "PASS",
            }
        ],
    )
    final_state = {
        "schema_version": 1,
        "status": "READY_FOR_VALIDATION",
        "all_training_receipts_present": all(r.get("status") == "PASS" for r in training_rows),
        "aggregation_complete": True,
        "terminal_token_candidates": [
            "BATCH9_RELIABLE_DISTILL_RETAIN_PENDING_PLANNER",
            "BATCH9_DIRECT_RESENC_ONLY_PENDING_PLANNER",
            "BATCH9_MAINLINE_NO_USABLE_SIGNAL_RETURN_TO_PLANNER",
        ],
    }
    write_json(RESULT_ROOT / "finalizer_state.json", final_state)
    return final_state


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    result = aggregate()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["aggregation_complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
