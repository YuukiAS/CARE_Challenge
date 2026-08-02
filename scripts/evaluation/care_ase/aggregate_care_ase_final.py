#!/usr/bin/env python
"""Aggregate CARE-ASE W5 outer metrics and module intervention evidence."""

from __future__ import annotations

import argparse
import csv
import json
import math
import pickle
import sys
from pathlib import Path
from typing import Any

import blosc2
import numpy as np
import torch

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.evaluation.care_ase.evaluate_care_ase_outer import class_metrics, decode_logits_np, read_spacing, sliding_window_final_logits
from src.care_myocardium.data.case_metadata import load_myops_case_metadata
from src.care_myocardium.data.care_ase_splits import SENTINEL_CASES, build_care_ase_case_roles
from src.care_myocardium.training.care_ase_trainer import load_care_ase_checkpoint, write_json


PREPROCESSED = REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetPlans_3d_fullres"
RESULT_DIR = REPO_ROOT / "results/20260801_care_ase_final_model"

INTERVENTIONS = {
    "scar_proposal": {"disable_scar_proposal": True},
    "scar_center": {"disable_scar_center": True},
    "scar_context": {"disable_scar_context": True},
    "edema_injury": {"disable_edema_injury": True},
    "edema_boundary": {"disable_edema_boundary": True},
    "edema_context": {"disable_edema_context": True},
    "extent_wall": {"disable_extent_wall": True},
}


def read_b2nd(path: Path) -> np.ndarray:
    return np.asarray(blosc2.open(str(path), mode="r")[:])


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ["status"])
        writer.writeheader()
        writer.writerows(rows)


def finite_mean(values: list[float]) -> float:
    vals = [v for v in values if math.isfinite(v)]
    return float(np.mean(vals)) if vals else math.nan


def subset_stats(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    out = []
    subset_defs = [
        ("all_outer", lambda row: True),
        ("sentinel_outer", lambda row: row.get("sentinel") == "True"),
        ("complete_modality", lambda row: row.get("modality_group") == "C0+LGE+T2"),
        ("centerB", lambda row: row.get("center") == "CenterB"),
        ("centerC", lambda row: row.get("center") == "CenterC"),
        ("no_t2", lambda row: row.get("modality_group") in {"LGE-only", "C0+LGE"}),
    ]
    for cls in ("scar", "edema"):
        cls_rows = [row for row in rows if row["class"] == cls]
        for name, predicate in subset_defs:
            subset = [row for row in cls_rows if predicate(row)]
            out.append(
                {
                    "subset": name,
                    "class": cls,
                    "case_metric_rows": len(subset),
                    "mean_Dice": finite_mean([float(row["Dice"]) for row in subset]),
                    "mean_HD95_mm": finite_mean([float(row["HD95_mm"]) for row in subset]),
                    "mean_exact_HD_mm": finite_mean([float(row["exact_HD_mm"]) for row in subset]),
                    "mean_precision": finite_mean([float(row["precision"]) for row in subset]),
                    "mean_sensitivity": finite_mean([float(row["sensitivity"]) for row in subset]),
                    "mean_component_count": finite_mean([float(row["component_count"]) for row in subset]),
                    "mean_remote_fp_volume_mm3": finite_mean([float(row["remote_fp_volume_mm3"]) for row in subset]),
                    "mean_blood_pool_adjacent_fp_volume_mm3": finite_mean([float(row["blood_pool_adjacent_fp_volume_mm3"]) for row in subset]),
                    "mean_volume_ratio": finite_mean([float(row["volume_ratio"]) for row in subset]),
                }
            )
    return out


def hard_manifest_rows() -> list[dict[str, str]]:
    rows = []
    for fold in (2, 3):
        path = RESULT_DIR / f"hard_negative_manifest_fold{fold}.csv"
        if path.exists():
            rows.extend(read_csv(path))
    return rows


def selected_intervention_cases(metrics: list[dict[str, str]]) -> list[tuple[int, str]]:
    selected = {
        (int(row["fold"]), row["case_id"])
        for row in metrics
        if row.get("sentinel") == "True"
    }
    hard_rows = hard_manifest_rows()
    for fold in (2, 3):
        fold_rows = [row for row in hard_rows if int(row["fold"]) == fold]
        ranked = sorted(
            fold_rows,
            key=lambda row: int(row["scar_fn_voxels"]) + int(row["scar_fp_voxels"]) + int(row["edema_fn_voxels"]) + int(row["edema_fp_voxels"]),
            reverse=True,
        )
        selected.update((fold, row["case_id"]) for row in ranked[:2])
    return sorted(selected)


def intervention_rows(cases: list[tuple[int, str]], patch_size: tuple[int, int, int], device: torch.device) -> list[dict[str, Any]]:
    metadata = load_myops_case_metadata(REPO_ROOT)
    role_lookup = {(row.fold, row.case_id): row for fold in (2, 3) for row in build_care_ase_case_roles(REPO_ROOT, fold)}
    models = {}
    out_rows = []
    with torch.no_grad():
        for fold, case_id in cases:
            if fold not in models:
                ckpt = RESULT_DIR / "runtime" / f"fold_{fold}" / "checkpoint_step14000.pt"
                model, _payload = load_care_ase_checkpoint(ckpt, map_location="cpu", restore_rng=False)
                model.to(device).eval()
                models[fold] = model
            model = models[fold]
            image_np = read_b2nd(PREPROCESSED / f"{case_id}.b2nd").astype(np.float32, copy=False)
            seg_np = read_b2nd(PREPROCESSED / f"{case_id}_seg.b2nd")[0].astype(np.int64, copy=False)
            spacing = read_spacing(case_id)
            availability = torch.tensor([metadata[case_id].availability], device=device, dtype=torch.float32)
            t2_present = bool(float(availability[0, 1].detach().cpu()) > 0.0)
            base_logits, base_meta = sliding_window_final_logits(
                model,
                image_np,
                availability,
                patch_size=patch_size,
                device=device,
                global_step=14000,
            )
            base_pred = decode_logits_np(base_logits, t2_present=t2_present)
            role = role_lookup[(fold, case_id)]
            for name, flags in INTERVENTIONS.items():
                off_logits, _off_meta = sliding_window_final_logits(
                    model,
                    image_np,
                    availability,
                    patch_size=patch_size,
                    device=device,
                    global_step=14000,
                    **flags,
                )
                off_pred = decode_logits_np(off_logits, t2_present=t2_present)
                delta = np.abs(off_logits - base_logits)
                for cls_name, cls_id in (("scar", 5), ("edema", 4)):
                    base_metrics = class_metrics(base_pred, seg_np, cls_id, spacing)
                    off_metrics = class_metrics(off_pred, seg_np, cls_id, spacing)
                    out_rows.append(
                        {
                            "fold": fold,
                            "case_id": case_id,
                            "role": role.role,
                            "sentinel": role.sentinel,
                            "center": metadata[case_id].center,
                            "modality_group": metadata[case_id].modality_group,
                            "component": name,
                            "class": cls_name,
                            "inference_method": base_meta["inference_method"],
                            "patch_count": base_meta["patch_count"],
                            "max_abs_final_logit_delta": float(delta.max()),
                            "changed_final_labels": int((off_pred != base_pred).sum()),
                            "base_Dice": base_metrics["Dice"],
                            "off_Dice": off_metrics["Dice"],
                            "Dice_delta_on_minus_off": float(base_metrics["Dice"] - off_metrics["Dice"]),
                            "base_HD95_mm": base_metrics["HD95_mm"],
                            "off_HD95_mm": off_metrics["HD95_mm"],
                            "base_exact_HD_mm": base_metrics["exact_HD_mm"],
                            "off_exact_HD_mm": off_metrics["exact_HD_mm"],
                            "base_component_count": base_metrics["component_count"],
                            "off_component_count": off_metrics["component_count"],
                            "base_remote_fp_volume_mm3": base_metrics["remote_fp_volume_mm3"],
                            "off_remote_fp_volume_mm3": off_metrics["remote_fp_volume_mm3"],
                            "base_blood_pool_adjacent_fp_volume_mm3": base_metrics["blood_pool_adjacent_fp_volume_mm3"],
                            "off_blood_pool_adjacent_fp_volume_mm3": off_metrics["blood_pool_adjacent_fp_volume_mm3"],
                            "base_volume_ratio": base_metrics["volume_ratio"],
                            "off_volume_ratio": off_metrics["volume_ratio"],
                            "mechanism_status": "INACTIVE_NO_MECHANISM_CLAIM"
                            if float(delta.max()) <= 1.0e-7 and int((off_pred != base_pred).sum()) == 0
                            else "ACTIVE_OUTPUT_CHANGED",
                        }
                    )
    return out_rows


def hard_case_atlas(metrics: list[dict[str, str]], interventions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    hard_lookup: dict[tuple[int, str], dict[str, str]] = {(int(row["fold"]), row["case_id"]): row for row in hard_manifest_rows()}
    intervention_by_case: dict[tuple[int, str], list[dict[str, Any]]] = {}
    for row in interventions:
        intervention_by_case.setdefault((int(row["fold"]), row["case_id"]), []).append(row)
    atlas = []
    for row in metrics:
        key = (int(row["fold"]), row["case_id"])
        if row.get("sentinel") != "True" and key not in hard_lookup:
            continue
        active_components = sorted({r["component"] for r in intervention_by_case.get(key, []) if r["mechanism_status"] == "ACTIVE_OUTPUT_CHANGED"})
        stock_hard = hard_lookup.get(key, {})
        atlas.append(
            {
                "fold": row["fold"],
                "case_id": row["case_id"],
                "role": row["role"],
                "sentinel": row["sentinel"],
                "center": row["center"],
                "modality_group": row["modality_group"],
                "class": row["class"],
                "care_ase_Dice": row["Dice"],
                "care_ase_HD95_mm": row["HD95_mm"],
                "care_ase_exact_HD_mm": row["exact_HD_mm"],
                "care_ase_sensitivity": row["sensitivity"],
                "care_ase_pred_voxels": row["pred_voxels"],
                "care_ase_gt_voxels": row["gt_voxels"],
                "stock_hard_manifest_status": stock_hard.get("status", ""),
                "stock_scar_fp_voxels": stock_hard.get("scar_fp_voxels", ""),
                "stock_scar_fn_voxels": stock_hard.get("scar_fn_voxels", ""),
                "stock_edema_fp_voxels": stock_hard.get("edema_fp_voxels", ""),
                "stock_edema_fn_voxels": stock_hard.get("edema_fn_voxels", ""),
                "active_components_on_case": "|".join(active_components),
            }
        )
    return atlas


def write_atlas_md(path: Path, rows: list[dict[str, Any]]) -> None:
    lines = [
        "# CARE-ASE W5 Hard-Case Atlas",
        "",
        "This atlas is a lightweight tabular audit over frozen fold2/fold3 outer metrics, sentinel roles, frozen stock hard-negative rows, and component on/off evidence. It is not a validation upload or hosted metric claim.",
        "",
        "| fold | case | role | class | Dice | HD95_mm | sensitivity | stock_fp_fn | active_components |",
        "|---:|---|---|---|---:|---:|---:|---|---|",
    ]
    for row in rows:
        stock = f"sFP={row['stock_scar_fp_voxels']}/sFN={row['stock_scar_fn_voxels']}/eFP={row['stock_edema_fp_voxels']}/eFN={row['stock_edema_fn_voxels']}"
        lines.append(
            f"| {row['fold']} | {row['case_id']} | {row['role']} | {row['class']} | {float(row['care_ase_Dice']):.4f} | {float(row['care_ase_HD95_mm']):.4f} | {float(row['care_ase_sensitivity']):.4f} | {stock} | {row['active_components_on_case']} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--patch-size", default="20,256,256")
    parser.add_argument("--implementation-validity-status", default="VALID_UNLESS_SNAPSHOT_REVIEW_FINDS_ERROR")
    args = parser.parse_args()
    patch_size = tuple(int(v) for v in args.patch_size.replace("x", ",").split(",") if v)
    if len(patch_size) != 3:
        raise ValueError("--patch-size must contain exactly three integers")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    metrics = []
    receipts = []
    for fold in (2, 3):
        eval_dir = RESULT_DIR / "outer_eval" / f"fold_{fold}"
        receipt = json.loads((eval_dir / "evaluation_receipt.json").read_text(encoding="utf-8"))
        receipts.append(receipt)
        metrics.extend(read_csv(eval_dir / "casewise_metrics.csv"))
    pooled = subset_stats(metrics)
    write_csv(RESULT_DIR / "pooled_fold2_fold3_statistics.csv", pooled)
    selected_cases = selected_intervention_cases(metrics)
    interventions = intervention_rows(selected_cases, patch_size, device)
    write_csv(RESULT_DIR / "module_intervention_outer.csv", interventions)
    atlas = hard_case_atlas(metrics, interventions)
    write_csv(RESULT_DIR / "hard_case_atlas.csv", atlas)
    write_atlas_md(RESULT_DIR / "hard_case_atlas.md", atlas)
    active_by_component = {
        name: any(row["mechanism_status"] == "ACTIVE_OUTPUT_CHANGED" for row in interventions if row["component"] == name)
        for name in INTERVENTIONS
    }
    primary = {
        (row["class"], row["subset"]): row
        for row in pooled
        if row["subset"] in {"all_outer", "sentinel_outer", "centerB", "centerC"}
    }
    receipt = {
        "status": "PASS",
        "implementation_validity_status": args.implementation_validity_status,
        "outer_evaluation_receipts": receipts,
        "pooled_statistics_path": "results/20260801_care_ase_final_model/pooled_fold2_fold3_statistics.csv",
        "hard_case_atlas_csv": "results/20260801_care_ase_final_model/hard_case_atlas.csv",
        "hard_case_atlas_md": "results/20260801_care_ase_final_model/hard_case_atlas.md",
        "module_intervention_outer_csv": "results/20260801_care_ase_final_model/module_intervention_outer.csv",
        "module_intervention_inference_method": "tiled_sliding_window_average_logits",
        "module_intervention_patch_size": list(patch_size),
        "intervention_case_count": len(selected_cases),
        "intervention_cases": [{"fold": fold, "case_id": case_id} for fold, case_id in selected_cases],
        "component_output_activity": active_by_component,
        "primary_outer_summary": primary,
        "stock_comparison_boundary": "Full same-split stock Dice/HD is not recomputed here; frozen hard-negative manifests provide stock error context only. No hosted metric claim is authorized.",
        "promotion_gate_scientific_decision": "PENDING_CONTROLLER_REPORT",
    }
    write_json(RESULT_DIR / "w5_aggregation_receipt.json", receipt)
    print(json.dumps(receipt, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
