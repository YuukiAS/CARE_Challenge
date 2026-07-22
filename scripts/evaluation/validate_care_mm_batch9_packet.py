#!/usr/bin/env python3
"""Fail-closed validator for CARE Batch9 controller packet."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
TASK_KEY = "20260722_care_myops_batch9_reliable_label_distillation"
RESULT_ROOT = REPO_ROOT / "results" / TASK_KEY
PENDING_TOKENS = ("PENDING", "RUNNING", "NEEDS_MONITOR", "JOB_SUBMITTED", "AWAITING_SACCT", "PLACEHOLDER", "STATIC_INITIAL")
ALLOWED_FINAL = {
    "BATCH9_RELIABLE_DISTILL_RETAIN_PENDING_PLANNER",
    "BATCH9_DIRECT_RESENC_ONLY_PENDING_PLANNER",
    "BATCH9_MAINLINE_NO_USABLE_SIGNAL_RETURN_TO_PLANNER",
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def has_pending_text(path: Path) -> bool:
    text = path.read_text(encoding="utf-8", errors="ignore")
    for allowed in ALLOWED_FINAL:
        text = text.replace(allowed, "")
    return any(tok in text for tok in PENDING_TOKENS)


def validate() -> dict[str, Any]:
    errors: list[str] = []
    required = [
        "controller_context.json",
        "controller_ledger.csv",
        "controller_bootstrap_snapshot.md",
        "batch8_supersession.md",
        "fold0_case_manifest.csv",
        "center_modality_label_inventory.csv",
        "reliable_supervision_inventory.csv",
        "resenc_environment_contract.json",
        "standard_nnunet_baseline_contract.json",
        "clean_model_import_graph.json",
        "legacy_module_call_counters.csv",
        "availability_hard_mask_checks.csv",
        "reliable_supervision_mask_checks.csv",
        "resolved_loss_contract.json",
        "loss_gradient_matrix.csv",
        "final_logit_authority_checks.csv",
        "fixed_real_case_overfit.json",
        "checkpoint_roundtrip.json",
        "known_bad_report.json",
        "direct_training_adequacy.csv",
        "teacher_initialization_checks.csv",
        "teacher_training_adequacy.csv",
        "matched_run_manifest.csv",
        "distillation_mechanism.csv",
        "training_adequacy.csv",
        "checkpoint_selection.csv",
        "prediction_manifest.csv",
        "casewise_metrics.csv",
        "subgroup_metrics.csv",
        "help_harm.csv",
        "supervision_audit.csv",
        "finalizer_state.json",
        "decision_matrix.csv",
        "controller_report.md",
        "completion_check.md",
        "MANIFEST.md",
    ]
    for name in required:
        p = RESULT_ROOT / name
        if not p.is_file():
            fail(errors, f"missing required output: {name}")
    if errors:
        return {"status": "FAIL", "errors": errors}

    manifest = read_csv(RESULT_ROOT / "fold0_case_manifest.csv")
    if len([r for r in manifest if r["split"] == "train"]) != 176:
        fail(errors, "fold0 train case count is not 176")
    if len([r for r in manifest if r["split"] == "val"]) != 44:
        fail(errors, "fold0 val case count is not 44")
    if any(r["t2_present"] == "0" and r["edema_reliable"] != "0" for r in manifest):
        fail(errors, "no-T2 case marked edema reliable")
    if any(r["center"] and r.get("center_enters_network") == "1" for r in read_csv(RESULT_ROOT / "reliable_supervision_inventory.csv")):
        fail(errors, "center enters network according to supervision inventory")

    legacy = read_csv(RESULT_ROOT / "legacy_module_call_counters.csv")
    if any(int(r["import_count"]) or int(r["instance_count"]) or int(r["forward_call_count"]) for r in legacy):
        fail(errors, "legacy SRR component count is nonzero")
    if read_json(RESULT_ROOT / "clean_model_import_graph.json").get("legacy_module_import_instance_forward_counts_all_zero") is not True:
        fail(errors, "clean import graph does not prove zero legacy counts")

    loss_contract = read_json(RESULT_ROOT / "resolved_loss_contract.json")
    if loss_contract.get("pathology_losses_use_composed_final_logit_margins") is not True:
        fail(errors, "pathology losses are not bound to final logit margins")
    grad_rows = read_csv(RESULT_ROOT / "loss_gradient_matrix.csv")
    if any(r["declared_weight"] not in {"0.0", "0"} and r["status"] != "PASS" for r in grad_rows):
        fail(errors, "nonzero loss missing authorized gradient")

    overfit = read_json(RESULT_ROOT / "fixed_real_case_overfit.json")
    if overfit.get("status") != "PASS" or overfit.get("formal_training_credit") != 0:
        fail(errors, "fixed real-case overfit is not PASS with zero formal credit")
    if read_json(RESULT_ROOT / "checkpoint_roundtrip.json").get("status") != "PASS":
        fail(errors, "checkpoint roundtrip failed")
    known_bad = read_json(RESULT_ROOT / "known_bad_report.json")
    if known_bad.get("status") != "PASS" or not all(row.get("rejected") for row in known_bad.get("known_bad_cases", [])):
        fail(errors, "known-bad fixtures did not all reject")

    direct = read_csv(RESULT_ROOT / "direct_training_adequacy.csv")
    for seed in ("20260723", "20260724"):
        rows = [r for r in direct if r["seed"] == seed and r["variant"] == "student_direct_reliable"]
        if len(rows) != 1 or rows[0]["status"] != "PASS" or int(rows[0]["epochs"]) != 500 or int(rows[0]["optimizer_steps"]) != 125000:
            fail(errors, f"direct formal run incomplete for seed {seed}")
    teachers = read_csv(RESULT_ROOT / "teacher_training_adequacy.csv")
    for seed in ("20260723", "20260724"):
        rows = [r for r in teachers if r["seed"] == seed and r["variant"] == "teacher_full_view"]
        if len(rows) != 1 or rows[0]["status"] != "PASS" or int(rows[0]["epochs"]) != 100 or int(rows[0]["optimizer_steps"]) != 25000:
            fail(errors, f"teacher formal run incomplete for seed {seed}")
    cont = read_csv(RESULT_ROOT / "training_adequacy.csv")
    for seed in ("20260723", "20260724"):
        for variant in ("student_moddrop_control", "student_reliable_distill"):
            rows = [r for r in cont if r["seed"] == seed and r["variant"] == variant]
            if len(rows) != 1 or rows[0]["status"] != "PASS" or int(rows[0]["epochs"]) != 100 or int(rows[0]["optimizer_steps"]) != 25000:
                fail(errors, f"matched continuation incomplete for {seed}/{variant}")

    pred = read_csv(RESULT_ROOT / "prediction_manifest.csv")
    expected_predictions = 2 * 4 * 44
    if len(pred) != expected_predictions:
        fail(errors, f"prediction manifest row count {len(pred)} != {expected_predictions}")
    if len({r["prediction_sha256"] for r in pred}) != len(pred):
        fail(errors, "prediction hashes are reused")
    casewise = read_csv(RESULT_ROOT / "casewise_metrics.csv")
    if len(casewise) != expected_predictions * 2:
        fail(errors, "casewise metrics row count does not cover scar and edema for all predictions")
    completion_text = (RESULT_ROOT / "completion_check.md").read_text(encoding="utf-8")
    final_tokens = [tok for tok in ALLOWED_FINAL if tok in completion_text]
    if len(final_tokens) != 1:
        fail(errors, "completion_check must contain exactly one allowed Batch9 final token")
    final_token = final_tokens[0] if final_tokens else ""
    gt_positive_empty = [r for r in casewise if r["gt_positive"] == "1" and r["prediction_positive"] == "0"]
    if gt_positive_empty and final_token != "BATCH9_MAINLINE_NO_USABLE_SIGNAL_RETURN_TO_PLANNER":
        fail(errors, "GT-positive empty pathology prediction present outside no-usable-signal terminal decision")

    if any(has_pending_text(RESULT_ROOT / name) for name in ["finalizer_state.json", "controller_report.md", "completion_check.md"]):
        fail(errors, "pending/running/placeholder token appears in terminal packet")

    return {"status": "PASS" if not errors else "FAIL", "errors": errors}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    result = validate()
    out = RESULT_ROOT / "strict_validator_report.json"
    out.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
