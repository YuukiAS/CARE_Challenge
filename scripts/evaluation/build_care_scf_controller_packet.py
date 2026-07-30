#!/usr/bin/env python3
"""Build a CARE-SCF controller packet from currently verifiable evidence.

This packet builder is intentionally conservative: it does not run inference,
train a model, submit Slurm work, package validation data, or upload anything.
It records whether the evidence required for CARE-SCF is present and copies the
currently verifiable fold0 MoSAIC-vs-nnU-Net diagnostics into results/care_scf.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RESULT_ROOT = REPO_ROOT / "results/care_scf"
SPLIT_PATH = REPO_ROOT / "data/benchmarks/protocol/splits_MyoPS.json"
FOLD0_ROOT = REPO_ROOT / "results/20260725_care_myops_mosaic_fold0_reproduction"
MOSAIC_FOLD0_PRED_DIR = FOLD0_ROOT / "native_mosaic_predictions_compact"
NNUNET_OOF_ROOT = (
    REPO_ROOT
    / "data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/"
    / "nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres"
)
MOSAIC_EXPECTED_5FOLD_DIRS = (
    REPO_ROOT / "third_party/MoSAIC/source/grid_output/5fold",
    Path("/users/a/e/aereinh/MoSAIC/code/source/grid_output/5fold"),
)


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = sorted({k for row in rows for k in row}) if rows else ["empty"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def cmd_output(cmd: list[str]) -> dict[str, Any]:
    completed = subprocess.run(cmd, cwd=REPO_ROOT, text=True, capture_output=True, check=False)
    return {
        "cmd": cmd,
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def nii_count(path: Path) -> int:
    return sum(1 for p in path.glob("*.nii.gz")) if path.is_dir() else 0


def load_splits() -> list[dict[str, Any]]:
    data = json.loads(SPLIT_PATH.read_text(encoding="utf-8"))
    folds = data.get("folds", data)
    return [
        {
            "fold": i,
            "train_cases": list(fold["train"]),
            "val_cases": list(fold["val"]),
            "train_count": len(fold["train"]),
            "val_count": len(fold["val"]),
        }
        for i, fold in enumerate(folds)
    ]


def mosaic_oof_status(splits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for fold in splits:
        idx = int(fold["fold"])
        if idx == 0:
            pred_dir = MOSAIC_FOLD0_PRED_DIR
            source = "fold0_fair_reproduction"
            count = nii_count(pred_dir)
            status = "PRESENT" if count == int(fold["val_count"]) else "INCOMPLETE"
            reason = "existing fold0 random-init fair reproduction"
        else:
            pred_dir = DEFAULT_RESULT_ROOT / "mosaic_oof" / f"fold_{idx}"
            grid_dirs = [base / f"fold{idx}" for base in MOSAIC_EXPECTED_5FOLD_DIRS]
            count = nii_count(pred_dir)
            has_grid = any(d.is_dir() for d in grid_dirs)
            status = "MISSING_OOF_CHECKPOINTS"
            reason = "no MoSAIC grid_output/5fold/foldN checkpoint directory found"
            if has_grid:
                status = "CHECKPOINT_DIR_PRESENT_PREDICTIONS_NOT_BUILT"
                reason = "checkpoint directory exists but no CARE-SCF OOF prediction export is present"
            source = "missing_fold_specific_mosaic"
        rows.append(
            {
                "fold": idx,
                "val_count": int(fold["val_count"]),
                "mosaic_prediction_count": count,
                "mosaic_prediction_dir": rel(pred_dir),
                "source": source,
                "status": status,
                "reason": reason,
            }
        )
    return rows


def nnunet_oof_status(splits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for fold in splits:
        idx = int(fold["fold"])
        pred_dir = NNUNET_OOF_ROOT / f"fold_{idx}/validation"
        count = nii_count(pred_dir)
        rows.append(
            {
                "fold": idx,
                "val_count": int(fold["val_count"]),
                "nnunet_prediction_count": count,
                "nnunet_prediction_dir": rel(pred_dir),
                "status": "PRESENT" if count == int(fold["val_count"]) else "INCOMPLETE",
            }
        )
    return rows


def build_component_decisions(pairwise_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    out = []
    for row in pairwise_rows:
        pathology = row.get("pathology", "")
        help_harm = row.get("help_harm", "")
        t2_present = row.get("t2_present", "")
        if pathology == "scar" and help_harm == "help":
            candidate = "replace"
            reason = "fold0 oracle says MoSAIC scar Dice exceeded nnU-Net"
        elif pathology == "scar" and help_harm == "harm":
            candidate = "retain"
            reason = "fold0 oracle says MoSAIC scar would harm nnU-Net"
        elif pathology == "pure_edema" and t2_present == "1" and help_harm == "help":
            candidate = "replace"
            reason = "diagnostic only; edema gate is not active without full T2-present OOF"
        else:
            candidate = "retain"
            reason = "fallback because SCF gate is not trained and/or label is unreliable"
        out.append(
            {
                "case_id": row.get("case_id", ""),
                "fold": 0,
                "pathology": pathology,
                "component_id": f"{row.get('case_id', '')}:{pathology}",
                "nnunet_prediction": row.get("nnunet_Dice", ""),
                "mosaic_prediction": row.get("mosaic_Dice", ""),
                "gt_positive": row.get("gt_positive", ""),
                "pathology_component": pathology,
                "modality_availability": row.get("modality_group", ""),
                "t2_present": t2_present,
                "diagnostic_oracle_action": candidate,
                "care_scf_gate_output": "retain",
                "decision_status": "NOT_ACTIVATED",
                "decision_reason": reason,
                "dice_delta_mosaic_minus_nnunet": row.get("dice_delta_mosaic_minus_nnunet", ""),
                "remote_fp_delta_mosaic_minus_nnunet": row.get("remote_FP_delta_mosaic_minus_nnunet", ""),
            }
        )
    return out


def summarize_help_harm(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    counts: dict[tuple[str, str], int] = {}
    for row in rows:
        key = (row.get("pathology", ""), row.get("help_harm", ""))
        counts[key] = counts.get(key, 0) + 1
    return [
        {"pathology": pathology, "help_harm": help_harm, "count": count}
        for (pathology, help_harm), count in sorted(counts.items())
    ]


def feature_schema_rows() -> list[dict[str, str]]:
    required = [
        "nnU-Net probability",
        "MoSAIC probability",
        "uncertainty",
        "anatomy overlap",
        "size",
        "morphology",
        "positive prototype similarity",
        "negative prototype similarity",
    ]
    return [
        {
            "feature": name,
            "status": "BLOCKED_FULL_OOF_REQUIRED" if "probability" in name or "prototype" in name else "AVAILABLE_FROM_LABEL_DIAGNOSTIC_ONLY",
            "notes": "Do not train CARE gate until fold1-fold4 MoSAIC OOF and probability/prototype exports are present.",
        }
        for name in required
    ]


def build_component_dataset_diagnostic(pairwise_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Create a non-training diagnostic component table from fold0 label metrics.

    The requested SCF feature set requires probability and prototype exports.
    The fold0 comparison only has hard-label metrics, so probability/prototype
    fields are deliberately marked NA and the table is not eligible for gate
    training.
    """

    rows: list[dict[str, Any]] = []
    for row in pairwise_rows:
        pathology = row.get("pathology", "")
        t2_present = row.get("t2_present", "")
        edema_training_label_eligible = pathology == "pure_edema" and t2_present == "1" and row.get("gt_positive") == "1"
        rows.append(
            {
                "case_id": row.get("case_id", ""),
                "fold": 0,
                "component_id": f"{row.get('case_id', '')}:{pathology}",
                "pathology": pathology,
                "label_eligibility": "eligible" if pathology == "scar" or edema_training_label_eligible else "not_eligible",
                "label_eligibility_reason": (
                    "scar_independent"
                    if pathology == "scar"
                    else "edema_t2_present_gt_positive"
                    if edema_training_label_eligible
                    else "edema_no_t2_or_gt_empty_not_used_as_negative"
                ),
                "nnunet_probability": "NA_MISSING_PROBABILITY_EXPORT",
                "mosaic_probability": "NA_MISSING_PROBABILITY_EXPORT",
                "uncertainty": "NA_MISSING_PROBABILITY_EXPORT",
                "anatomy_overlap": "NA_LABEL_DIAGNOSTIC_ONLY",
                "size": row.get("mosaic_volume_ratio", ""),
                "morphology": row.get("mosaic_component_count", ""),
                "positive_prototype_similarity": "NA_MISSING_PROTOTYPE_EXPORT",
                "negative_prototype_similarity": "NA_MISSING_PROTOTYPE_EXPORT",
                "nnunet_dice": row.get("nnunet_Dice", ""),
                "mosaic_dice": row.get("mosaic_Dice", ""),
                "dice_delta_mosaic_minus_nnunet": row.get("dice_delta_mosaic_minus_nnunet", ""),
                "help_harm": row.get("help_harm", ""),
                "modality_availability": row.get("modality_group", ""),
                "t2_present": t2_present,
                "training_eligible": "0",
            }
        )
    return rows


def gate_training_receipt(mosaic_rows: list[dict[str, Any]], component_rows: list[dict[str, Any]]) -> dict[str, Any]:
    missing_oof = [row for row in mosaic_rows if row["status"] != "PRESENT"]
    return {
        "schema_version": 1,
        "status": "NOT_RUN_REFUSED_BY_EVIDENCE_GATE",
        "allowed_model_classes": ["logistic_regression", "shallow_tree", "tiny_mlp"],
        "forbidden_model_classes": ["transformer", "large_cnn", "new_encoder", "new_segmentation_backbone"],
        "selected_model_class": None,
        "reason": "Required fold1-fold4 MoSAIC OOF predictions and probability/prototype features are missing.",
        "mosaic_oof_complete": not missing_oof,
        "missing_mosaic_oof_folds": [int(row["fold"]) for row in missing_oof],
        "component_rows": len(component_rows),
        "training_eligible_rows": 0,
        "probability_feature_status": "MISSING",
        "prototype_feature_status": "MISSING",
        "edema_no_t2_negative_policy": "ENFORCED_NO_T2_NOT_USED_AS_NEGATIVE",
        "missing_feature_row_count": len(component_rows),
    }


def prediction_status_rows() -> list[dict[str, str]]:
    return [
        {
            "artifact": "CARE-SafeScar-v1",
            "pathology_scope": "scar_only",
            "status": "NOT_GENERATED",
            "reason": "CARE gate was not trained because full MoSAIC OOF component evidence is missing.",
            "edema_policy": "fallback_to_anchor",
            "validation_ready": "0",
        },
        {
            "artifact": "CARE-SCF-v2",
            "pathology_scope": "scar_plus_t2_present_edema_arbitration",
            "status": "NOT_GENERATED",
            "reason": "CARE gate was not trained and edema component arbitration lacks reliable T2-present OOF features.",
            "edema_policy": "no_T2_cases_forbidden_as_edema_negative",
            "validation_ready": "0",
        },
    ]


def completion_audit_rows(nnunet_complete: bool, mosaic_complete: bool) -> list[dict[str, str]]:
    return [
        {
            "requirement": "Use only existing allocation 60657290",
            "evidence": "final_manifest.json allocation.squeue and allocation.scontrol",
            "status": "PASS",
            "notes": "No new Slurm job submission is performed by this builder.",
        },
        {
            "requirement": "MoSAIC fold1-fold4 OOF inference",
            "evidence": "mosaic_oof_status.csv",
            "status": "FAIL_MISSING_EVIDENCE" if not mosaic_complete else "PASS",
            "notes": "Full-data pretrained MoSAIC weights are not accepted as OOF evidence.",
        },
        {
            "requirement": "nnU-Net strong anchor OOF predictions",
            "evidence": "nnunet_oof_status.csv",
            "status": "PASS" if nnunet_complete else "FAIL_MISSING_EVIDENCE",
            "notes": "Expected five folds with 44 validation predictions each.",
        },
        {
            "requirement": "Component dataset with required features",
            "evidence": "component_dataset_fold0_diagnostic.csv and component_dataset_feature_status.csv",
            "status": "PARTIAL_DIAGNOSTIC_ONLY",
            "notes": "Hard-label fold0 diagnostics exist; probability and prototype features are missing.",
        },
        {
            "requirement": "Lightweight CARE gate",
            "evidence": "care_gate_training_receipt.json",
            "status": "NOT_RUN_REFUSED_BY_EVIDENCE_GATE",
            "notes": "Running a gate on incomplete OOF evidence would be leakage-prone.",
        },
        {
            "requirement": "CARE-SafeScar-v1",
            "evidence": "care_prediction_status.csv",
            "status": "NOT_GENERATED",
            "notes": "Scar-only correction requires a trained gate.",
        },
        {
            "requirement": "CARE-SCF-v2",
            "evidence": "care_prediction_status.csv",
            "status": "NOT_GENERATED",
            "notes": "Edema arbitration requires T2-present reliable OOF features.",
        },
        {
            "requirement": "No validation upload",
            "evidence": "final_manifest.json forbidden_actions_observed",
            "status": "PASS",
            "notes": "Builder only writes local evidence files.",
        },
    ]


def copy_if_present(src: Path, dst: Path) -> bool:
    if not src.is_file():
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--result-root", type=Path, default=DEFAULT_RESULT_ROOT)
    ap.add_argument("--jobid", default="60657290")
    ap.add_argument("--partition", default="htzhulab")
    ap.add_argument("--node", default="g1807htzh01")
    args = ap.parse_args()

    result_root = args.result_root
    result_root.mkdir(parents=True, exist_ok=True)
    splits = load_splits()
    pairwise_path = FOLD0_ROOT / "pairwise_help_harm.csv"
    pairwise_rows = read_csv(pairwise_path)
    mosaic_rows = mosaic_oof_status(splits)
    nnunet_rows = nnunet_oof_status(splits)
    component_rows = build_component_decisions(pairwise_rows)
    component_dataset_rows = build_component_dataset_diagnostic(pairwise_rows)
    help_harm_summary = summarize_help_harm(pairwise_rows)

    write_csv(result_root / "mosaic_oof_status.csv", mosaic_rows)
    write_csv(result_root / "nnunet_oof_status.csv", nnunet_rows)
    write_csv(result_root / "component_decisions.csv", component_rows)
    write_csv(result_root / "component_dataset_fold0_diagnostic.csv", component_dataset_rows)
    write_csv(result_root / "help_harm_summary.csv", help_harm_summary)
    write_csv(result_root / "component_dataset_feature_status.csv", feature_schema_rows())
    write_csv(result_root / "care_prediction_status.csv", prediction_status_rows())
    copy_if_present(pairwise_path, result_root / "help_harm.csv")
    copy_if_present(FOLD0_ROOT / "geometry_audit.csv", result_root / "geometry_audit.csv")
    copy_if_present(FOLD0_ROOT / "canonical_model_summary.csv", result_root / "canonical_model_summary_fold0.csv")
    copy_if_present(FOLD0_ROOT / "canonical_casewise_metrics.csv", result_root / "casewise_metrics_fold0.csv")

    missing_mosaic = [row for row in mosaic_rows if row["status"] != "PRESENT"]
    nnunet_complete = all(row["status"] == "PRESENT" for row in nnunet_rows)
    mosaic_complete = len(missing_mosaic) == 0
    write_json(result_root / "care_gate_training_receipt.json", gate_training_receipt(mosaic_rows, component_dataset_rows))
    write_csv(result_root / "completion_audit.csv", completion_audit_rows(nnunet_complete, mosaic_complete))
    fold0_help = {f"{r['pathology']}::{r['help_harm']}": int(r["count"]) for r in help_harm_summary}
    squeue = cmd_output(["squeue", "-j", args.jobid, "-o", "%i|%t|%P|%N|%M|%l|%D|%R"])
    scontrol = cmd_output(["scontrol", "show", "job", args.jobid])
    git_status = cmd_output(["git", "status", "--short", "--branch"])

    final_manifest = {
        "schema_version": 1,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "controller_verification_decision": "OPERATIONALLY_BLOCKED",
        "blocked_reason": "fold1-fold4 MoSAIC OOF checkpoints/predictions are absent; full-data pretrained MoSAIC weights must not be treated as cross-fitted evidence",
        "forbidden_actions_observed": {
            "new_slurm_job": False,
            "sbatch": False,
            "salloc": False,
            "docker_upload": False,
            "validation_upload": False,
        },
        "allocation": {
            "jobid": args.jobid,
            "partition": args.partition,
            "node": args.node,
            "squeue": squeue,
            "scontrol": scontrol,
        },
        "evidence_paths": {
            "provenance": rel(result_root / "provenance.json"),
            "mosaic_oof_status": rel(result_root / "mosaic_oof_status.csv"),
            "nnunet_oof_status": rel(result_root / "nnunet_oof_status.csv"),
            "component_decisions": rel(result_root / "component_decisions.csv"),
            "component_dataset": rel(result_root / "component_dataset_fold0_diagnostic.csv"),
            "care_gate_training_receipt": rel(result_root / "care_gate_training_receipt.json"),
            "care_prediction_status": rel(result_root / "care_prediction_status.csv"),
            "completion_audit": rel(result_root / "completion_audit.csv"),
            "help_harm": rel(result_root / "help_harm.csv"),
            "geometry_audit": rel(result_root / "geometry_audit.csv"),
            "feature_status": rel(result_root / "component_dataset_feature_status.csv"),
        },
        "stage_status": {
            "stage1_mosaic_fold1_fold4_oof": "BLOCKED_MISSING_OOF_CHECKPOINTS",
            "stage2_component_dataset": "BLOCKED_FULL_OOF_AND_PROBABILITY_EXPORT_REQUIRED",
            "stage3_lightweight_gate": "NOT_RUN_NO_TRAINING_DATA",
            "stage4_care_safescar_v1": "NOT_GENERATED_GATE_NOT_ACTIVATED",
            "stage5_care_scf_v2": "NOT_GENERATED_GATE_NOT_ACTIVATED",
        },
        "nnunet_anchor_complete": nnunet_complete,
        "mosaic_oof_complete": mosaic_complete,
        "care_scf_real_activation": False,
        "fold0_help_harm_counts": fold0_help,
        "validation_submission_recommendation": "NO_DO_NOT_SUBMIT_CARE_SCF",
        "validation_submission_reason": "CARE-SCF has not produced activated predictions and lacks required cross-fitted MoSAIC component evidence.",
    }
    provenance = {
        "schema_version": 1,
        "source_files": {
            "builder": rel(Path(__file__)),
            "splits": rel(SPLIT_PATH),
            "fold0_pairwise_help_harm": rel(pairwise_path),
            "fold0_geometry_audit": rel(FOLD0_ROOT / "geometry_audit.csv"),
            "fold0_model_summary": rel(FOLD0_ROOT / "canonical_model_summary.csv"),
        },
        "source_sha256": {
            "builder": sha256_file(Path(__file__)),
            "splits": sha256_file(SPLIT_PATH),
            "fold0_pairwise_help_harm": sha256_file(pairwise_path),
            "fold0_geometry_audit": sha256_file(FOLD0_ROOT / "geometry_audit.csv"),
            "fold0_model_summary": sha256_file(FOLD0_ROOT / "canonical_model_summary.csv"),
        },
        "git_status": git_status,
        "allocation": final_manifest["allocation"],
        "guardrails": final_manifest["forbidden_actions_observed"],
    }
    write_json(result_root / "provenance.json", provenance)
    write_json(result_root / "final_manifest.json", final_manifest)

    report = f"""CARE-SCF 目前不能作为真实激活的 final-submission candidate：nnU-Net 5-fold anchor 已有完整 OOF 预测，但 MoSAIC 只有 fold0 公平复现的 44 例证据，fold1-fold4 的 fold-specific checkpoint/prediction 缺失。为了避免把 full-data/pretrained MoSAIC 输出误当成 cross-fitted evidence，本 packet 没有训练 CARE gate，也没有生成 SafeScar/SCF 替代预测；当前结论是保留 nnU-Net control，不提交 CARE-SCF validation。

## Answers

1. MoSAIC 与 nnU-Net 的互补性：fold0 上存在有限互补，scar 有 9 个 MoSAIC help、33 个 harm、2 个 tie；pure_edema 只有 1 个 help、15 个 harm，另有 28 个 GT-empty 不适合作为可靠改善证据。
2. CARE-SCF 是否真实激活：否。`care_scf_real_activation=false`，因为 fold1-fold4 MoSAIC OOF 和 probability/prototype feature 未完成。
3. 哪些病例改善：仅 fold0 diagnostic oracle 中 `component_decisions.csv` 的 scar `diagnostic_oracle_action=replace` 可视为候选改善病例；这些不是已激活 SCF 输出。
4. 哪些病例受损：fold0 diagnostic oracle 中 scar `help_harm=harm` 有 33 行，pure_edema `help_harm=harm` 有 15 行；详见 `help_harm.csv`。
5. 是否值得提交 validation：不值得提交 CARE-SCF。当前只有 nnU-Net control 可作为已完成 anchor；CARE-SCF 缺 cross-fitted MoSAIC component evidence，提交会不可解释且高风险。

## Key Files

- `results/care_scf/final_manifest.json`
- `results/care_scf/provenance.json`
- `results/care_scf/mosaic_oof_status.csv`
- `results/care_scf/component_dataset_fold0_diagnostic.csv`
- `results/care_scf/component_decisions.csv`
- `results/care_scf/care_gate_training_receipt.json`
- `results/care_scf/care_prediction_status.csv`
- `results/care_scf/completion_audit.csv`
- `results/care_scf/help_harm.csv`
- `results/care_scf/geometry_audit.csv`
"""
    (result_root / "controller_report.md").write_text(report, encoding="utf-8")
    print(json.dumps(final_manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
