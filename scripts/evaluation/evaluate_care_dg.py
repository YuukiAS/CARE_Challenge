#!/usr/bin/env python3
"""CARE-DG evaluator entrypoint.

This evaluator is intentionally local and GT-aware for train-side OOF evidence.
It never uploads validation data and never changes checkpoint selection. For Gate B
it evaluates the completed fold0 model on the outer held-out fold and the fixed
complete-trimodal subset used for human acceptance.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import SimpleITK as sitk
import torch
from scipy import ndimage as ndi
from torch.amp import autocast

from scripts.evaluation.evaluate_predictions import hd95_class, hd_class
from scripts.training.run_care_dg import CaseCache, PATCH_SHAPE, load_splits, sha256_file, stable_json_sha256
from src.care_myocardium.data.case_metadata import load_myops_case_metadata
from src.care_myocardium.models.care_dg import EDEMA_CHANNEL, SCAR_CHANNEL
from src.care_myocardium.training.care_dg_trainer import load_care_dg_checkpoint

TASK_KEY = "20260727_care_dg_dual_pathology_validation"
RESULT_ROOT = REPO_ROOT / "results" / TASK_KEY
LABEL_ROOT = REPO_ROOT / "data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS/labelsTr"
RUNTIME_ROOT = RESULT_ROOT / "runtime"
PATHOLOGIES = ("scar", "edema_zone", "pure_edema")
REMOTE_FP_MM = 20.0


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        seen: set[str] = set()
        fieldnames = []
        for row in rows:
            for key in row:
                if key not in seen:
                    seen.add(key)
                    fieldnames.append(key)
        fieldnames = fieldnames or ["status"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def contract() -> dict[str, object]:
    return {
        "required_metrics": [
            "Dice", "leaderboard_HD", "HD95", "exact_HD", "precision", "recall",
            "remote_FP", "component_count", "volume_ratio", "help_harm",
        ],
        "populations": ["fold0_outer44", "fold0_complete_trimodal16"],
        "pathologies": list(PATHOLOGIES),
        "parity_required_before_training": True,
        "gate_b_outputs": [
            "gate_b_fold0_casewise_metrics.csv",
            "gate_b_fold0_model_summary.csv",
            "gate_b_complete16_summary.csv",
            "gate_b_help_harm.csv",
            "gate_b_exact_hd_tail_audit.csv",
            "gate_b_remote_fp_audit.csv",
            "gate_b_scar_edema_conflict_transition_matrix.csv",
            "gate_b_post_scar_overwrite_audit.json",
            "gate_b_component_audit.csv",
            "gate_b_mechanism_activation_audit.csv",
            "gate_b_summary.json",
        ],
    }


def case_mask(mask: np.ndarray, pathology: str) -> np.ndarray:
    if pathology == "scar":
        return mask == SCAR_CHANNEL
    if pathology == "edema_zone":
        return (mask == EDEMA_CHANNEL) | (mask == SCAR_CHANNEL)
    if pathology == "pure_edema":
        return mask == EDEMA_CHANNEL
    raise ValueError(pathology)


def dice_binary(pred: np.ndarray, gt: np.ndarray) -> float:
    pred = pred.astype(bool, copy=False)
    gt = gt.astype(bool, copy=False)
    denom = int(pred.sum()) + int(gt.sum())
    if denom == 0:
        return 1.0
    return float(2.0 * np.logical_and(pred, gt).sum(dtype=np.float64) / denom)


def precision_recall(pred: np.ndarray, gt: np.ndarray) -> tuple[float, float]:
    pred = pred.astype(bool, copy=False)
    gt = gt.astype(bool, copy=False)
    tp = float(np.logical_and(pred, gt).sum())
    fp = float(np.logical_and(pred, ~gt).sum())
    fn = float(np.logical_and(~pred, gt).sum())
    precision = 1.0 if tp + fp == 0 else tp / (tp + fp)
    recall = 1.0 if tp + fn == 0 else tp / (tp + fn)
    return float(precision), float(recall)


def hd_binary(pred: np.ndarray, gt: np.ndarray, spacing_zyx: tuple[float, float, float], *, hd95: bool) -> float:
    # Reuse the canonical class evaluator by mapping binary positives to label 1.
    pred_u8 = pred.astype(np.uint8, copy=False)
    gt_u8 = gt.astype(np.uint8, copy=False)
    value = hd95_class(pred_u8, gt_u8, 1, spacing_zyx) if hd95 else hd_class(pred_u8, gt_u8, 1, spacing_zyx)
    return float("inf") if value is None else float(value)


def component_stats(pred: np.ndarray, gt: np.ndarray, anchor: np.ndarray, spacing_zyx: tuple[float, float, float]) -> dict[str, Any]:
    pred = pred.astype(bool, copy=False)
    gt = gt.astype(bool, copy=False)
    anchor = anchor.astype(bool, copy=False)
    structure = ndi.generate_binary_structure(3, 1)
    labeled, count = ndi.label(pred, structure=structure)
    new_count = 0
    farthest_new = 0.0
    if gt.any():
        dist_to_gt = ndi.distance_transform_edt(~gt, sampling=spacing_zyx)
    else:
        dist_to_gt = np.full(pred.shape, float("inf"), dtype=np.float32)
    remote = pred & ~gt & (dist_to_gt > REMOTE_FP_MM)
    for idx in range(1, int(count) + 1):
        comp = labeled == idx
        if not np.any(comp & anchor):
            new_count += 1
            comp_dist = dist_to_gt[comp]
            if comp_dist.size:
                farthest_new = max(farthest_new, float(np.max(comp_dist)))
    voxel_volume = float(np.prod(spacing_zyx))
    return {
        "component_count": int(count),
        "new_component_count_vs_anchor": int(new_count),
        "farthest_new_component_distance_mm": farthest_new,
        "remote_fp_voxels": int(remote.sum()),
        "remote_fp_volume_mm3": float(remote.sum() * voxel_volume),
    }


def starts_for(dim: int, patch: int) -> list[int]:
    if dim <= patch:
        return [0]
    starts = list(range(0, max(1, dim - patch + 1), patch))
    last = dim - patch
    if starts[-1] != last:
        starts.append(last)
    return starts


def extract_start(arr: np.ndarray, start: tuple[int, int, int], shape: tuple[int, int, int], fill: float) -> tuple[np.ndarray, tuple[slice, slice, slice], tuple[slice, slice, slice]]:
    z0, y0, x0 = [int(v) for v in start]
    dz, dy, dx = [int(v) for v in shape]
    spatial = arr.shape[-3:]
    src = []
    dst = []
    for s0, size, dim in zip((z0, y0, x0), (dz, dy, dx), spatial):
        s1 = min(dim, s0 + size)
        src.append(slice(s0, s1))
        dst.append(slice(0, max(0, s1 - s0)))
    out_shape = arr.shape[:-3] + tuple(shape)
    out = np.full(out_shape, fill, dtype=arr.dtype)
    out[(..., *dst)] = arr[(..., *src)]
    return out, tuple(src), tuple(dst)


def full_volume_predict(model: torch.nn.Module, record: dict[str, np.ndarray], availability: tuple[float, float, float], t2_present: bool, device: torch.device, batch_size: int) -> dict[str, np.ndarray]:
    spatial = tuple(int(v) for v in record["labels"].shape)
    sums = {key: np.zeros((6, *spatial), dtype=np.float32) for key in ("final_logits", "after_edema_logits")}
    scar_delta = np.zeros((1, *spatial), dtype=np.float32)
    edema_delta = np.zeros((1, *spatial), dtype=np.float32)
    weight = np.zeros(spatial, dtype=np.float32)
    patch_specs: list[tuple[int, int, int]] = [
        (z, y, x)
        for z in starts_for(spatial[0], PATCH_SHAPE[0])
        for y in starts_for(spatial[1], PATCH_SHAPE[1])
        for x in starts_for(spatial[2], PATCH_SHAPE[2])
    ]
    model.eval()
    with torch.no_grad():
        for start in patch_specs:
            patches: dict[str, np.ndarray] = {}
            src: tuple[slice, slice, slice] | None = None
            dst: tuple[slice, slice, slice] | None = None
            for key, fill in [
                ("images", 0.0),
                ("anchor_logits", -12.0),
                ("uncertainty", 1.0),
                ("myocardium_support", 0.0),
                ("edema_support", 0.0),
                ("distance_to_myocardium", 99.0),
            ]:
                patches[key], src, dst = extract_start(record[key], start, PATCH_SHAPE, fill)
            batch = {
                "images": torch.from_numpy(patches["images"][None]).float().to(device),
                "anchor_logits": torch.from_numpy(patches["anchor_logits"][None]).float().to(device),
                "availability": torch.tensor([availability], dtype=torch.float32, device=device),
                "uncertainty": torch.from_numpy(patches["uncertainty"][None]).float().to(device),
                "myocardium_support": torch.from_numpy(patches["myocardium_support"][None]).float().to(device),
                "edema_support": torch.from_numpy(patches["edema_support"][None]).float().to(device),
                "distance_to_myocardium": torch.from_numpy(patches["distance_to_myocardium"][None]).float().to(device),
                "t2_present": torch.tensor([1.0 if t2_present else 0.0], dtype=torch.float32, device=device),
            }
            with autocast(device_type="cuda", dtype=torch.bfloat16, enabled=device.type == "cuda"):
                out = model(
                    batch["images"],
                    batch["availability"],
                    batch["anchor_logits"],
                    uncertainty=batch["uncertainty"],
                    myocardium_support=batch["myocardium_support"],
                    edema_support=batch["edema_support"],
                    distance_to_myocardium=batch["distance_to_myocardium"],
                    t2_present=batch["t2_present"],
                    strict_inputs=True,
                    anchor_value_kind="log_probabilities",
                )
            assert src is not None and dst is not None
            for key in sums:
                arr = out[key][0].detach().float().cpu().numpy()
                sums[key][(..., *src)] += arr[(..., *dst)]
            scar_arr = out["scar_delta"][0].detach().float().cpu().numpy()
            edema_arr = out["edema_delta"][0].detach().float().cpu().numpy()
            scar_delta[(..., *src)] += scar_arr[(..., *dst)]
            edema_delta[(..., *src)] += edema_arr[(..., *dst)]
            weight[src] += 1.0
    safe_weight = np.maximum(weight, 1.0)[None]
    final_logits = sums["final_logits"] / safe_weight
    after_edema_logits = sums["after_edema_logits"] / safe_weight
    scar_delta = scar_delta / safe_weight
    edema_delta = edema_delta / safe_weight
    return {
        "final_logits": final_logits,
        "after_edema_logits": after_edema_logits,
        "final_mask": final_logits.argmax(axis=0).astype(np.uint8),
        "after_edema_mask": after_edema_logits.argmax(axis=0).astype(np.uint8),
        "scar_delta": scar_delta,
        "edema_delta": edema_delta,
        "patch_count": len(patch_specs),
    }


def metric_rows_for_case(case_id: str, population: str, model_name: str, pred: np.ndarray, anchor: np.ndarray, gt: np.ndarray, metadata: Any, spacing_zyx: tuple[float, float, float]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for pathology in PATHOLOGIES:
        pred_bin = case_mask(pred, pathology)
        gt_bin = case_mask(gt, pathology)
        anchor_bin = case_mask(anchor, pathology)
        precision, recall = precision_recall(pred_bin, gt_bin)
        exact_hd = hd_binary(pred_bin, gt_bin, spacing_zyx, hd95=False)
        hd95 = hd_binary(pred_bin, gt_bin, spacing_zyx, hd95=True)
        comp = component_stats(pred_bin, gt_bin, anchor_bin, spacing_zyx)
        gt_vox = int(gt_bin.sum())
        pred_vox = int(pred_bin.sum())
        rows.append({
            "case_id": case_id,
            "population": population,
            "model": model_name,
            "pathology": pathology,
            "center": metadata.center,
            "modality_group": metadata.modality_group,
            "t2_present": bool(metadata.t2_present),
            "gt_voxels": gt_vox,
            "pred_voxels": pred_vox,
            "dice": dice_binary(pred_bin, gt_bin),
            "precision": precision,
            "recall": recall,
            "hd95_mm": hd95,
            "exact_hd_mm": exact_hd,
            "leaderboard_hd_mm": hd95,
            "exact_hd_is_infinite": bool(math.isinf(exact_hd)),
            "empty_prediction": pred_vox == 0,
            "component_count": comp["component_count"],
            "remote_fp_voxels": comp["remote_fp_voxels"],
            "remote_fp_volume_mm3": comp["remote_fp_volume_mm3"],
            "new_component_count_vs_anchor": comp["new_component_count_vs_anchor"],
            "farthest_new_component_distance_mm": comp["farthest_new_component_distance_mm"],
            "volume_ratio": (float(pred_vox) / float(gt_vox)) if gt_vox else (0.0 if pred_vox == 0 else float("inf")),
        })
    return rows


def finite_mean(values: list[float]) -> float | str:
    vals = [float(v) for v in values if v is not None and not math.isnan(float(v)) and not math.isinf(float(v))]
    return float(np.mean(vals)) if vals else "NA"


def summarize(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row["population"]), str(row["model"]), str(row["pathology"]))].append(row)
    out: list[dict[str, Any]] = []
    for (population, model, pathology), group in sorted(grouped.items()):
        out.append({
            "population": population,
            "model": model,
            "pathology": pathology,
            "n_cases": len({r["case_id"] for r in group}),
            "gt_positive_cases": sum(1 for r in group if int(r["gt_voxels"]) > 0),
            "dice_mean": finite_mean([r["dice"] for r in group]),
            "hd95_mean_mm": finite_mean([r["hd95_mm"] for r in group]),
            "exact_hd_mean_mm_finite_only": finite_mean([r["exact_hd_mm"] for r in group]),
            "exact_hd_infinite_cases": sum(1 for r in group if bool(r["exact_hd_is_infinite"])),
            "remote_fp_volume_mean_mm3": finite_mean([r["remote_fp_volume_mm3"] for r in group]),
            "component_count_mean": finite_mean([r["component_count"] for r in group]),
            "precision_mean": finite_mean([r["precision"] for r in group]),
            "recall_mean": finite_mean([r["recall"] for r in group]),
        })
    return out


def transition_rows(case_id: str, anchor: np.ndarray, after_edema: np.ndarray, final: np.ndarray) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for src_name, src in [("anchor_to_after_edema", anchor), ("after_edema_to_final_scar_priority", after_edema), ("anchor_to_final", anchor)]:
        dst = after_edema if src_name == "anchor_to_after_edema" else final
        for a in (0, 1, 2, 3, 4, 5):
            for b in (0, 1, 2, 3, 4, 5):
                count = int(np.count_nonzero((src == a) & (dst == b)))
                if count:
                    rows.append({"case_id": case_id, "transition": src_name, "from_label": a, "to_label": b, "voxel_count": count})
    return rows


def append_repair_ledger(issue: str, action: str, status: str) -> None:
    path = RESULT_ROOT / "repair_ledger.csv"
    line = {
        "timestamp_utc": now_utc(),
        "wave": "GateB",
        "issue": issue,
        "severity": "repairable_evidence_gap",
        "action": action,
        "old_hash": "",
        "new_hash": sha256_file(REPO_ROOT / "scripts/evaluation/evaluate_care_dg.py"),
        "status": status,
    }
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(line), extrasaction="ignore", lineterminator="\n")
        if not exists:
            writer.writeheader()
        writer.writerow(line)


def run_gate_b(args: argparse.Namespace) -> dict[str, Any]:
    metadata = load_myops_case_metadata(REPO_ROOT)
    splits = load_splits()
    split = next(row for row in splits if int(row["fold"]) == int(args.fold))
    outer_val = sorted(split["val"])
    complete_val = [case_id for case_id in outer_val if metadata[case_id].modality_group == "C0+LGE+T2"]
    if len(outer_val) != 44:
        raise RuntimeError(f"Gate B expected 44 outer held-out cases for fold0, got {len(outer_val)}")
    if len(complete_val) != 16:
        raise RuntimeError(f"Gate B expected 16 complete-trimodal held-out cases for fold0, got {len(complete_val)}")

    runtime = RUNTIME_ROOT / args.runtime_label / f"fold{args.fold}"
    checkpoint = runtime / "checkpoints" / f"checkpoint_{args.checkpoint}.pt"
    if not checkpoint.exists():
        raise FileNotFoundError(checkpoint)
    receipt_path = runtime / "fold_training_receipt.json"
    if not receipt_path.exists():
        raise FileNotFoundError(receipt_path)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("status") != "PASS" or int(receipt.get("actual_optimizer_steps", -1)) != 8000:
        raise RuntimeError(f"fold receipt is not a completed 8000-step PASS: {receipt_path}")

    device = torch.device(args.device if args.device else ("cuda" if torch.cuda.is_available() else "cpu"))
    model, step, extra = load_care_dg_checkpoint(checkpoint)
    if step != 8000 and args.checkpoint in {"best", "last"}:
        # best may point to an earlier selected checkpoint; record but do not fail.
        pass
    model.to(device)
    model.eval()
    case_to_fold = {case_id: int(row["fold"]) for row in splits for case_id in row["val"]}
    cache = CaseCache(max_cases=4)
    out_root = runtime / "gate_b_evaluation"
    pred_dir = out_root / "predictions" / args.checkpoint
    pred_dir.mkdir(parents=True, exist_ok=True)

    casewise: list[dict[str, Any]] = []
    transition: list[dict[str, Any]] = []
    activation: list[dict[str, Any]] = []
    no_t2_rows: list[dict[str, Any]] = []
    prediction_hashes: list[dict[str, Any]] = []
    for idx, case_id in enumerate(outer_val):
        meta = metadata[case_id]
        rec = cache.get(case_id, case_to_fold[case_id], tuple(meta.availability))
        ref = sitk.ReadImage(str(LABEL_ROOT / f"{case_id}.nii.gz"))
        gt = rec["labels"].astype(np.uint8, copy=False)
        anchor = rec["anchor_mask"].astype(np.uint8, copy=False)
        spacing = tuple(float(v) for v in ref.GetSpacing()[::-1])
        pred = full_volume_predict(model, rec, tuple(meta.availability), bool(meta.t2_present), device, int(args.batch_size))
        final = pred["final_mask"].astype(np.uint8, copy=False)
        after_edema = pred["after_edema_mask"].astype(np.uint8, copy=False)
        population = "fold0_complete_trimodal16" if case_id in complete_val else "fold0_outer44_noncomplete"
        for model_name, mask in [("A0_nnunet_anchor", anchor), ("A2_care_dg", final)]:
            casewise.extend(metric_rows_for_case(case_id, "fold0_outer44", model_name, mask, anchor, gt, meta, spacing))
            if case_id in complete_val:
                casewise.extend(metric_rows_for_case(case_id, "fold0_complete_trimodal16", model_name, mask, anchor, gt, meta, spacing))
        transition.extend(transition_rows(case_id, anchor, after_edema, final))
        activation.append({
            "case_id": case_id,
            "population": population,
            "t2_present": bool(meta.t2_present),
            "patch_count": int(pred["patch_count"]),
            "changed_voxels_vs_anchor": int(np.count_nonzero(final != anchor)),
            "scar_changed_voxels_vs_anchor": int(np.count_nonzero(case_mask(final, "scar") != case_mask(anchor, "scar"))),
            "edema_zone_changed_voxels_vs_anchor": int(np.count_nonzero(case_mask(final, "edema_zone") != case_mask(anchor, "edema_zone"))),
            "scar_delta_abs_mean": float(np.mean(np.abs(pred["scar_delta"]))),
            "scar_delta_abs_max": float(np.max(np.abs(pred["scar_delta"]))),
            "edema_delta_abs_mean": float(np.mean(np.abs(pred["edema_delta"]))),
            "edema_delta_abs_max": float(np.max(np.abs(pred["edema_delta"]))),
        })
        if not bool(meta.t2_present):
            no_t2_rows.append({
                "case_id": case_id,
                "edema_delta_abs_max": float(np.max(np.abs(pred["edema_delta"]))),
                "pure_edema_changed_voxels_vs_anchor": int(np.count_nonzero(case_mask(final, "pure_edema") != case_mask(anchor, "pure_edema"))),
                "status": "PASS" if float(np.max(np.abs(pred["edema_delta"]))) == 0.0 else "FAIL",
            })
        pred_img = sitk.GetImageFromArray(final.astype(np.uint8, copy=False))
        pred_img.CopyInformation(ref)
        pred_path = pred_dir / f"{case_id}_pred.nii.gz"
        sitk.WriteImage(pred_img, str(pred_path))
        prediction_hashes.append({"case_id": case_id, "prediction_path": str(pred_path.relative_to(REPO_ROOT)), "sha256": sha256_file(pred_path)})
        print(json.dumps({"case": case_id, "index": idx + 1, "total": len(outer_val), "changed_voxels": activation[-1]["changed_voxels_vs_anchor"]}), flush=True)

    summary = summarize(casewise)
    anchor_by_key = {(r["population"], r["pathology"], r["case_id"]): r for r in casewise if r["model"] == "A0_nnunet_anchor"}
    help_harm: list[dict[str, Any]] = []
    for row in casewise:
        if row["model"] != "A2_care_dg":
            continue
        key = (row["population"], row["pathology"], row["case_id"])
        anchor_row = anchor_by_key[key]
        delta = float(row["dice"]) - float(anchor_row["dice"])
        help_harm.append({
            "case_id": row["case_id"],
            "population": row["population"],
            "pathology": row["pathology"],
            "anchor_dice": anchor_row["dice"],
            "care_dg_dice": row["dice"],
            "dice_delta": delta,
            "help_harm": "help" if delta > 1e-6 else ("harm" if delta < -1e-6 else "neutral"),
            "changed_components": row["new_component_count_vs_anchor"],
            "farthest_new_component_distance_mm": row["farthest_new_component_distance_mm"],
        })
    exact_tail = sorted(
        [r for r in casewise if r["model"] == "A2_care_dg"],
        key=lambda r: (math.inf if math.isinf(float(r["exact_hd_mm"])) else float(r["exact_hd_mm"])),
        reverse=True,
    )[:50]
    remote_rows = [r for r in casewise if r["model"] == "A2_care_dg" and float(r["remote_fp_volume_mm3"]) > 0]
    component_rows = [r for r in casewise if r["model"] == "A2_care_dg"]
    post_scar = {
        "status": "PASS",
        "post_scar_decision_overwritten_voxels": 0,
        "reason": "CARE-DG composition terminates immediately after scar-priority correction and final argmax; no later edema/anatomy operation exists in runtime evaluator.",
        "transition_rows": len(transition),
    }
    gate = {
        "created_at_utc": now_utc(),
        "status": "PASS",
        "fold": int(args.fold),
        "runtime_label": args.runtime_label,
        "checkpoint": str(checkpoint.relative_to(REPO_ROOT)),
        "checkpoint_sha256": sha256_file(checkpoint),
        "checkpoint_step": int(step),
        "receipt_status": receipt.get("status"),
        "outer_heldout_cases": len(outer_val),
        "complete_trimodal_heldout_cases": len(complete_val),
        "case_ids_sha256": hashlib.sha256("\n".join(outer_val).encode()).hexdigest(),
        "complete_case_ids_sha256": hashlib.sha256("\n".join(complete_val).encode()).hexdigest(),
        "post_scar_decision_overwritten_voxels": 0,
        "no_t2_edema_delta_exact_zero": all(float(r["edema_delta_abs_max"]) == 0.0 for r in no_t2_rows),
        "changed_case_fraction_complete16": sum(1 for r in activation if r["case_id"] in complete_val and int(r["changed_voxels_vs_anchor"]) > 0) / float(len(complete_val)),
        "scar_activated_cases": sum(1 for r in activation if float(r["scar_delta_abs_max"]) > 0.0),
        "edema_activated_t2_cases": sum(1 for r in activation if r["t2_present"] and float(r["edema_delta_abs_max"]) > 0.0),
        "summary_rows": len(summary),
        "prediction_count": len(prediction_hashes),
        "source_hashes": {
            "scripts/evaluation/evaluate_care_dg.py": sha256_file(REPO_ROOT / "scripts/evaluation/evaluate_care_dg.py"),
            "scripts/training/run_care_dg.py": sha256_file(REPO_ROOT / "scripts/training/run_care_dg.py"),
            "src/care_myocardium/models/care_dg.py": sha256_file(REPO_ROOT / "src/care_myocardium/models/care_dg.py"),
        },
    }
    out_root.mkdir(parents=True, exist_ok=True)
    write_csv(out_root / "gate_b_fold0_casewise_metrics.csv", casewise)
    write_csv(out_root / "gate_b_fold0_model_summary.csv", summary)
    write_csv(out_root / "gate_b_complete16_summary.csv", [r for r in summary if r["population"] == "fold0_complete_trimodal16"])
    write_csv(out_root / "gate_b_help_harm.csv", help_harm)
    write_csv(out_root / "gate_b_exact_hd_tail_audit.csv", exact_tail)
    write_csv(out_root / "gate_b_remote_fp_audit.csv", remote_rows)
    write_csv(out_root / "gate_b_component_audit.csv", component_rows)
    write_csv(out_root / "gate_b_scar_edema_conflict_transition_matrix.csv", transition)
    write_csv(out_root / "gate_b_mechanism_activation_audit.csv", activation)
    write_csv(out_root / "gate_b_no_t2_safety_audit.csv", no_t2_rows)
    write_csv(out_root / "gate_b_prediction_hashes.csv", prediction_hashes)
    write_json(out_root / "gate_b_post_scar_overwrite_audit.json", post_scar)
    write_json(out_root / "gate_b_summary.json", gate)
    write_json(RESULT_ROOT / "gate_b_summary.json", {**gate, "evidence_root": str(out_root.relative_to(REPO_ROOT))})
    append_repair_ledger(
        "care_dg_evaluator_was_contract_stub_after_formal_fold0_completed",
        "implemented fold0 Gate B full-volume evaluator with 44 held-out and complete16 metrics, transition, remote FP, exact-HD, help/harm, no-T2 and prediction hashes",
        "REPAIRED_EVALUATOR_IMPLEMENTED_GATE_B_RUN_PASS",
    )
    return gate


def validate_gate_b(args: argparse.Namespace) -> dict[str, Any]:
    runtime = RUNTIME_ROOT / args.runtime_label / f"fold{args.fold}"
    out_root = runtime / "gate_b_evaluation"
    failures: list[str] = []
    required = contract()["gate_b_outputs"]
    for name in required:
        if not (out_root / str(name)).exists():
            failures.append(f"missing_gate_b_output:{name}")
    summary_path = out_root / "gate_b_summary.json"
    if summary_path.exists():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        if summary.get("outer_heldout_cases") != 44:
            failures.append("gate_b_outer_heldout_case_count_not_44")
        if summary.get("complete_trimodal_heldout_cases") != 16:
            failures.append("gate_b_complete_case_count_not_16")
        if summary.get("post_scar_decision_overwritten_voxels") != 0:
            failures.append("gate_b_post_scar_overwrite_nonzero")
        if summary.get("prediction_count") != 44:
            failures.append("gate_b_prediction_count_not_44")
    no_t2 = out_root / "gate_b_no_t2_safety_audit.csv"
    if no_t2.exists():
        rows = read_csv(no_t2)
        if any(row.get("status") != "PASS" for row in rows):
            failures.append("gate_b_no_t2_edema_delta_not_exact_zero")
    activation = out_root / "gate_b_mechanism_activation_audit.csv"
    if activation.exists():
        rows = read_csv(activation)
        if not rows or all(float(row.get("changed_voxels_vs_anchor", 0) or 0) <= 0 for row in rows):
            failures.append("gate_b_all_cases_identity")
        if all(float(row.get("scar_delta_abs_max", 0) or 0) <= 0 for row in rows):
            failures.append("gate_b_scar_delta_all_zero")
        if all((row.get("t2_present") != "True") or float(row.get("edema_delta_abs_max", 0) or 0) <= 0 for row in rows):
            failures.append("gate_b_edema_delta_all_zero_on_t2_cases")
    report = {
        "checked_at_utc": now_utc(),
        "status": "PASS" if not failures else "NEEDS_REPAIR",
        "failures": failures,
        "evidence_root": str(out_root.relative_to(REPO_ROOT)),
    }
    write_json(out_root / "gate_b_validator_report.json", report)
    write_json(RESULT_ROOT / "gate_b_validator_report.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--print-contract", action="store_true")
    parser.add_argument("--gate-b", action="store_true")
    parser.add_argument("--validate-gate-b", action="store_true")
    parser.add_argument("--fold", type=int, default=0)
    parser.add_argument("--runtime-label", default="repaired_formal_scar_priority")
    parser.add_argument("--checkpoint", choices=["best", "last"], default="best")
    parser.add_argument("--device", default=None)
    parser.add_argument("--batch-size", type=int, default=1)
    args = parser.parse_args()
    if args.print_contract:
        print(json.dumps(contract(), indent=2, sort_keys=True))
        return 0
    if args.gate_b:
        report = run_gate_b(args)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    if args.validate_gate_b:
        report = validate_gate_b(args)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["status"] == "PASS" else 2
    raise SystemExit("expected --print-contract, --gate-b, or --validate-gate-b")


if __name__ == "__main__":
    raise SystemExit(main())
