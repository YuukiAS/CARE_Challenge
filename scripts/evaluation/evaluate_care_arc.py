#!/usr/bin/env python3
"""Evaluate CARE-ARC checkpoints against fold split cases and nnU-Net anchor."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import SimpleITK as sitk
import torch
import torch.nn.functional as F
from scipy.ndimage import binary_erosion, distance_transform_edt, generate_binary_structure, label

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.evaluation.evaluate_predictions import _hd_scipy, _hd95_scipy  # noqa: E402
from src.care_myocardium.data.care_arc_dataset import CAREARCDataset, build_case_records, collate_single_case, load_label  # noqa: E402
from src.care_myocardium.inference.care_arc_predictor import CAREARCDecodeConfig, decode_care_arc_outputs  # noqa: E402
from src.care_myocardium.training.care_arc_trainer import load_care_arc_checkpoint, stable_json_sha256  # noqa: E402

TASK_KEY = "20260729_care_arc_clean_fold1"
RESULT_ROOT = REPO_ROOT / "results" / TASK_KEY
NNUNET_FOLD0 = (
    REPO_ROOT
    / "data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_0/validation"
)


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys or ["status"], extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def resample_label(path: Path, reference: sitk.Image) -> np.ndarray:
    img = sitk.ReadImage(str(path))
    if (
        img.GetSize() != reference.GetSize()
        or img.GetSpacing() != reference.GetSpacing()
        or img.GetOrigin() != reference.GetOrigin()
        or img.GetDirection() != reference.GetDirection()
    ):
        img = sitk.Resample(img, reference, sitk.Transform(), sitk.sitkNearestNeighbor, 0, sitk.sitkUInt8)
    return sitk.GetArrayFromImage(img).astype(np.uint8, copy=False)


def uncrop_to_original(patch: np.ndarray, original_shape: tuple[int, int, int], crop_hw: int) -> np.ndarray:
    out = np.zeros(original_shape, dtype=patch.dtype)
    h, w = original_shape[-2:]
    y0 = h // 2 - int(crop_hw) // 2
    x0 = w // 2 - int(crop_hw) // 2
    src_y0 = max(0, -y0)
    src_x0 = max(0, -x0)
    dst_y0 = max(0, y0)
    dst_x0 = max(0, x0)
    copy_h = min(h, y0 + int(crop_hw)) - dst_y0
    copy_w = min(w, x0 + int(crop_hw)) - dst_x0
    if copy_h > 0 and copy_w > 0:
        out[..., dst_y0 : dst_y0 + copy_h, dst_x0 : dst_x0 + copy_w] = patch[
            ..., src_y0 : src_y0 + copy_h, src_x0 : src_x0 + copy_w
        ]
    return out


def write_like(reference: sitk.Image, arr: np.ndarray, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img = sitk.GetImageFromArray(arr.astype(np.uint8, copy=False))
    img.CopyInformation(reference)
    sitk.WriteImage(img, str(path))


def binary_dice(pred: np.ndarray, gt: np.ndarray, *, skip_if_gt_empty: bool = True) -> float | None:
    p = pred.astype(bool)
    g = gt.astype(bool)
    if skip_if_gt_empty and not g.any():
        return None if not p.any() else 0.0
    denom = int(p.sum()) + int(g.sum())
    if denom == 0:
        return 1.0
    return float(2.0 * np.logical_and(p, g).sum() / denom)


def binary_hd95(pred: np.ndarray, gt: np.ndarray, spacing_zyx: tuple[float, float, float]) -> float | None:
    p = pred.astype(bool)
    g = gt.astype(bool)
    if not p.any() and not g.any():
        return 0.0
    if not p.any() or not g.any():
        return None
    v = _hd95_scipy(p, g, spacing_zyx)
    return None if np.isinf(v) else float(v)


def binary_hd(pred: np.ndarray, gt: np.ndarray, spacing_zyx: tuple[float, float, float]) -> float | None:
    p = pred.astype(bool)
    g = gt.astype(bool)
    if not p.any() and not g.any():
        return 0.0
    if not p.any() or not g.any():
        return None
    v = _hd_scipy(p, g, spacing_zyx)
    return None if np.isinf(v) else float(v)


def binary_component_stats(pred: np.ndarray, gt: np.ndarray, myocardium: np.ndarray, spacing_zyx: tuple[float, float, float]) -> dict[str, Any]:
    spacing_volume = float(np.prod(spacing_zyx))
    pred_mask = pred.astype(bool)
    gt_mask = gt.astype(bool)
    cc, n_cc = label(pred_mask, structure=generate_binary_structure(pred_mask.ndim, 1))
    fp_mask = pred_mask & ~gt_mask
    fp_cc, n_fp = label(fp_mask, structure=generate_binary_structure(pred_mask.ndim, 1))
    small_fp = 0
    for idx in range(1, int(n_fp) + 1):
        if float(np.count_nonzero(fp_cc == idx)) * spacing_volume < 50.0:
            small_fp += 1
    if myocardium.any():
        dist_to_myo = distance_transform_edt(~myocardium.astype(bool), sampling=spacing_zyx)
        remote_fp = fp_mask & (dist_to_myo > 10.0)
    else:
        remote_fp = fp_mask
    return {
        "component_count": int(n_cc),
        "small_fp_count_lt50mm3": int(small_fp),
        "remote_fp_volume_mm3": float(np.count_nonzero(remote_fp) * spacing_volume),
        "pred_volume_mm3": float(np.count_nonzero(pred_mask) * spacing_volume),
        "gt_volume_mm3": float(np.count_nonzero(gt_mask) * spacing_volume),
        "volume_ratio": None if not gt_mask.any() else float(np.count_nonzero(pred_mask) / max(1, np.count_nonzero(gt_mask))),
    }


def average_precision(y_true: list[np.ndarray], y_score: list[np.ndarray]) -> tuple[float | None, float]:
    y = np.concatenate([a.reshape(-1).astype(np.uint8, copy=False) for a in y_true])
    s = np.concatenate([a.reshape(-1).astype(np.float32, copy=False) for a in y_score])
    prevalence = float(y.mean()) if y.size else 0.0
    positives = int(y.sum())
    if positives == 0:
        return None, prevalence
    order = np.argsort(-s, kind="mergesort")
    y_sorted = y[order]
    tp = np.cumsum(y_sorted)
    rank = np.arange(1, y_sorted.size + 1)
    precision = tp / rank
    ap = float((precision * y_sorted).sum() / positives)
    return ap, prevalence


def mean_value(rows: list[dict[str, Any]], key: str) -> float | None:
    vals = [float(r[key]) for r in rows if r.get(key) is not None and r.get(key) != "" and not math.isnan(float(r[key]))]
    return float(np.mean(vals)) if vals else None


def median_value(rows: list[dict[str, Any]], key: str) -> float | None:
    vals = [float(r[key]) for r in rows if r.get(key) is not None and r.get(key) != "" and not math.isnan(float(r[key]))]
    return float(np.median(vals)) if vals else None


def summarize(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for variant in sorted({r["variant"] for r in rows}):
        for pathology in sorted({r["pathology"] for r in rows}):
            rs = [r for r in rows if r["variant"] == variant and r["pathology"] == pathology]
            pos = [r for r in rs if r["gt_positive"]]
            out.append(
                {
                    "variant": variant,
                    "pathology": pathology,
                    "case_rows": len(rs),
                    "positive_case_rows": len(pos),
                    "mean_dice_positive": mean_value(pos, "dice"),
                    "mean_hd95_positive": mean_value(pos, "hd95"),
                    "mean_exact_hd_positive": mean_value(pos, "exact_hd"),
                    "median_volume_ratio_positive": median_value(pos, "volume_ratio"),
                    "mean_component_count_positive": mean_value(pos, "component_count"),
                    "mean_remote_fp_volume_mm3": mean_value(rs, "remote_fp_volume_mm3"),
                    "empty_prediction_rate_positive": mean_value(pos, "empty_prediction"),
                }
            )
    return out


def run(args: argparse.Namespace) -> int:
    checkpoint = Path(args.checkpoint)
    if not checkpoint.is_absolute():
        checkpoint = REPO_ROOT / checkpoint
    out_root = Path(args.output_root)
    if not out_root.is_absolute():
        out_root = REPO_ROOT / out_root
    out_root.mkdir(parents=True, exist_ok=True)
    device = torch.device(args.device)
    model, payload = load_care_arc_checkpoint(checkpoint, map_location=device)
    model.to(device).eval()
    records = build_case_records(args.fold, args.role)
    ds = CAREARCDataset(records, crop_hw=args.crop_hw)
    decode_cfg = CAREARCDecodeConfig(
        scar_threshold=args.scar_threshold,
        edema_threshold=args.edema_threshold,
        scar_min_component_mm3=args.scar_min_component_mm3,
        edema_min_component_mm3=args.edema_min_component_mm3,
    )
    rows: list[dict[str, Any]] = []
    ap_buffers: dict[str, dict[str, list[np.ndarray]]] = {}
    presence_truth: dict[str, list[np.ndarray]] = {}
    presence_score: dict[str, list[np.ndarray]] = {}
    alignment_rows: list[dict[str, Any]] = []
    no_t2_failures: list[str] = []
    context_invariance = {"status": "PASS", "checked_case": ""}
    modes = [m.strip() for m in args.alignment_modes.split(",") if m.strip()]
    with torch.no_grad():
        for idx, record in enumerate(records):
            item = collate_single_case([ds[idx]])
            images = item["images"].to(device)
            availability = item["availability"].to(device)
            gt_arr, ref_img = load_label(record.case_id)
            spacing = tuple(float(x) for x in ref_img.GetSpacing()[::-1])
            myocardium = np.isin(gt_arr, [1, 4, 5])
            nnunet_path = Path(args.nnunet_pred_dir) / f"{record.case_id}.nii.gz"
            if not nnunet_path.is_absolute():
                nnunet_path = REPO_ROOT / nnunet_path
            nnunet = resample_label(nnunet_path, ref_img)
            if idx == 0:
                ctx_a = {"probabilities": torch.randn(1, 6, *images.shape[-3:], device=device)}
                ctx_b = {"probabilities": torch.randn(1, 6, *images.shape[-3:], device=device) * 100.0}
                out_a = model(images, availability, external_nnunet_context=ctx_a)
                out_b = model(images, availability, external_nnunet_context=ctx_b)
                context_invariance = {
                    "status": "PASS"
                    if torch.equal(out_a["scar_direct_logit"], out_b["scar_direct_logit"])
                    and torch.equal(out_a["edema_zone_direct_logit"], out_b["edema_zone_direct_logit"])
                    else "FAIL",
                    "checked_case": record.case_id,
                }
            for mode in modes:
                out = model(images, availability, alignment_mode=mode)
                decoded = decode_care_arc_outputs(out, availability[0], spacing, decode_cfg)
                scar_prob = torch.sigmoid(out["scar_direct_logit"]).detach().cpu().numpy()[0, 0]
                edema_prob = torch.sigmoid(out["edema_zone_direct_logit"]).detach().cpu().numpy()[0, 0]
                raw = np.zeros_like(scar_prob, dtype=np.uint8)
                raw_edema_zone = (edema_prob >= 0.50) if record.t2_present else np.zeros_like(scar_prob, dtype=bool)
                raw_scar = scar_prob >= 0.50
                raw[(raw_edema_zone & ~raw_scar)] = 4
                raw[raw_scar] = 5
                raw_full = uncrop_to_original(raw, gt_arr.shape, args.crop_hw)
                post_full = uncrop_to_original(decoded["compact_pathology"], gt_arr.shape, args.crop_hw)
                write_like(ref_img, raw_full, out_root / f"predictions/raw_direct_{mode}/{record.case_id}.nii.gz")
                write_like(ref_img, post_full, out_root / f"predictions/postprocessed_{mode}/{record.case_id}.nii.gz")
                scar_prob_full = uncrop_to_original(scar_prob.astype(np.float32), gt_arr.shape, args.crop_hw)
                edema_prob_full = uncrop_to_original(edema_prob.astype(np.float32), gt_arr.shape, args.crop_hw)
                coarse_scar = F.interpolate(out["scar"]["coarse_extent_logit"], size=out["scar_direct_logit"].shape[-3:], mode="trilinear", align_corners=False)
                coarse_edema = F.interpolate(out["edema"]["coarse_extent_logit"], size=out["edema_zone_direct_logit"].shape[-3:], mode="trilinear", align_corners=False)
                ap_buffers.setdefault(mode, {}).setdefault("scar_y", []).append(gt_arr == 5)
                ap_buffers.setdefault(mode, {}).setdefault("scar_score", []).append(uncrop_to_original(torch.sigmoid(coarse_scar).cpu().numpy()[0, 0], gt_arr.shape, args.crop_hw))
                ap_buffers.setdefault(mode, {}).setdefault("edema_zone_y", []).append(np.isin(gt_arr, [4, 5]))
                ap_buffers.setdefault(mode, {}).setdefault("edema_zone_score", []).append(uncrop_to_original(torch.sigmoid(coarse_edema).cpu().numpy()[0, 0], gt_arr.shape, args.crop_hw))
                presence_truth.setdefault(mode + "_scar", []).append(np.array([1 if np.any(gt_arr == 5) else 0], dtype=np.uint8))
                presence_score.setdefault(mode + "_scar", []).append(torch.sigmoid(out["scar"]["presence_logit"]).cpu().numpy().reshape(-1))
                presence_truth.setdefault(mode + "_edema_zone", []).append(np.array([1 if np.any(np.isin(gt_arr, [4, 5])) else 0], dtype=np.uint8))
                presence_score.setdefault(mode + "_edema_zone", []).append(torch.sigmoid(out["edema"]["presence_logit"]).cpu().numpy().reshape(-1))
                align = out["alignment"]
                alignment_rows.append(
                    {
                        "case_id": record.case_id,
                        "alignment_mode": mode,
                        "t2_present": record.t2_present,
                        "t2_offset_max_abs": float(align["t2_offset"].abs().max().cpu()),
                        "c0_offset_max_abs": float(align["c0_offset"].abs().max().cpu()),
                        "t2_confidence_mean": float(align["t2_confidence"].mean().cpu()),
                        "c0_confidence_mean": float(align["c0_confidence"].mean().cpu()),
                    }
                )
                if not record.t2_present and (int(np.count_nonzero(raw_full == 4)) or int(np.count_nonzero(post_full == 4))):
                    no_t2_failures.append(record.case_id)
                variants = {
                    f"raw_direct_{mode}": raw_full,
                    f"postprocessed_{mode}": post_full,
                }
                if mode == modes[0]:
                    variants["nnunet_anchor"] = nnunet
                for variant, pred in variants.items():
                    for pathology, pred_mask, gt_mask, anchor_mask in [
                        ("scar", pred == 5, gt_arr == 5, nnunet == 5),
                        ("edema_zone", np.isin(pred, [4, 5]), np.isin(gt_arr, [4, 5]), np.isin(nnunet, [4, 5])),
                        ("pure_edema", pred == 4, gt_arr == 4, nnunet == 4),
                    ]:
                        stats = binary_component_stats(pred_mask, gt_mask, myocardium, spacing)
                        rows.append(
                            {
                                "case_id": record.case_id,
                                "variant": variant,
                                "alignment_mode": mode if variant != "nnunet_anchor" else "",
                                "pathology": pathology,
                                "center": record.center,
                                "modality_group": record.modality_group,
                                "t2_present": record.t2_present,
                                "gt_positive": bool(gt_mask.any()),
                                "pred_positive": bool(pred_mask.any()),
                                "dice": binary_dice(pred_mask, gt_mask),
                                "hd95": binary_hd95(pred_mask, gt_mask, spacing),
                                "exact_hd": binary_hd(pred_mask, gt_mask, spacing),
                                "empty_prediction": 1.0 if not pred_mask.any() else 0.0,
                                "changed_mask_ratio_vs_nnunet": float(np.logical_xor(pred_mask, anchor_mask).sum() / max(1, gt_mask.sum())),
                                **stats,
                            }
                        )
    summary_rows = summarize(rows)
    summary = {(r["variant"], r["pathology"]): r for r in summary_rows}
    ap_report: dict[str, Any] = {}
    for mode in modes:
        scar_ap, scar_prev = average_precision(ap_buffers[mode]["scar_y"], ap_buffers[mode]["scar_score"])
        edema_ap, edema_prev = average_precision(ap_buffers[mode]["edema_zone_y"], ap_buffers[mode]["edema_zone_score"])
        scar_presence_ap, scar_presence_prev = average_precision(presence_truth[mode + "_scar"], presence_score[mode + "_scar"])
        edema_presence_ap, edema_presence_prev = average_precision(presence_truth[mode + "_edema_zone"], presence_score[mode + "_edema_zone"])
        ap_report[mode] = {
            "scar_coarse_auprc": scar_ap,
            "scar_coarse_prevalence": scar_prev,
            "edema_zone_coarse_auprc": edema_ap,
            "edema_zone_coarse_prevalence": edema_prev,
            "scar_presence_auprc": scar_presence_ap,
            "scar_presence_prevalence": scar_presence_prev,
            "edema_zone_presence_auprc": edema_presence_ap,
            "edema_zone_presence_prevalence": edema_presence_prev,
        }
    def delta(mode: str, pathology: str, variant_prefix: str) -> float | None:
        a = summary.get((f"{variant_prefix}_{mode}", pathology), {}).get("mean_dice_positive")
        b = summary.get(("nnunet_anchor", pathology), {}).get("mean_dice_positive")
        return None if a is None or b is None else float(a) - float(b)

    align_cmp: dict[str, Any] = {}
    if "enabled" in modes and "identity" in modes:
        scar_d = delta("enabled", "scar", "postprocessed")
        scar_i = delta("identity", "scar", "postprocessed")
        edema_d = delta("enabled", "edema_zone", "postprocessed")
        edema_i = delta("identity", "edema_zone", "postprocessed")
        scar_gain = None if scar_d is None or scar_i is None else scar_d - scar_i
        edema_gain = None if edema_d is None or edema_i is None else edema_d - edema_i
        hd_s = summary.get(("postprocessed_enabled", "scar"), {}).get("mean_hd95_positive")
        hd_si = summary.get(("postprocessed_identity", "scar"), {}).get("mean_hd95_positive")
        hd_e = summary.get(("postprocessed_enabled", "edema_zone"), {}).get("mean_hd95_positive")
        hd_ei = summary.get(("postprocessed_identity", "edema_zone"), {}).get("mean_hd95_positive")
        scar_hd_ratio = None if not hd_s or not hd_si else float(hd_s) / float(hd_si)
        edema_hd_ratio = None if not hd_e or not hd_ei else float(hd_e) / float(hd_ei)
        enabled_align_rows = [r for r in alignment_rows if r["alignment_mode"] == "enabled"]
        conf_vals = [r["t2_confidence_mean"] for r in enabled_align_rows if r["t2_present"]]
        offset_max = max([r["t2_offset_max_abs"] for r in enabled_align_rows] + [r["c0_offset_max_abs"] for r in enabled_align_rows])
        confidence_ok = bool(conf_vals and min(conf_vals) > 0.01 and max(conf_vals) < 0.99)
        offset_ok = bool(offset_max < 3.98)
        enable = (
            scar_gain is not None
            and edema_gain is not None
            and scar_gain >= -0.002
            and edema_gain >= -0.002
            and ((scar_gain + edema_gain) / 2.0) >= 0.003
            and (scar_hd_ratio is not None and scar_hd_ratio <= 1.02)
            and (edema_hd_ratio is not None and edema_hd_ratio <= 1.02)
            and confidence_ok
            and offset_ok
        )
        align_cmp = {
            "status": "PASS",
            "frozen_alignment_mode": "enabled" if enable else "identity",
            "scar_dice_gain_enabled_minus_identity": scar_gain,
            "edema_zone_dice_gain_enabled_minus_identity": edema_gain,
            "mean_dice_gain": None if scar_gain is None or edema_gain is None else (scar_gain + edema_gain) / 2.0,
            "scar_hd95_ratio_enabled_over_identity": scar_hd_ratio,
            "edema_zone_hd95_ratio_enabled_over_identity": edema_hd_ratio,
            "confidence_ok": confidence_ok,
            "offset_ok": offset_ok,
        }
    frozen = align_cmp.get("frozen_alignment_mode", modes[0])
    selected_rows = [r for r in rows if r["variant"] == f"raw_direct_{frozen}" and r["gt_positive"]]
    component_rows = [r for r in rows if r["variant"] == f"postprocessed_{frozen}"]
    anchor_rows = {(r["case_id"], r["pathology"]): r for r in rows if r["variant"] == "nnunet_anchor"}
    changed_ok: dict[str, Any] = {}
    component_ok = True
    for pathology in ("scar", "edema_zone"):
        pos = [r for r in component_rows if r["pathology"] == pathology and r["gt_positive"]]
        changed_fraction = mean_value([{"v": 1.0 if float(r["changed_mask_ratio_vs_nnunet"]) >= 0.05 else 0.0} for r in pos], "v")
        changed_ok[pathology] = {"positive_cases": len(pos), "fraction_changed_at_least_5pct": changed_fraction}
        for r in pos:
            a = anchor_rows.get((r["case_id"], pathology), {})
            limit = max(50.0, 10.0 * float(a.get("component_count") or 0.0) + 10.0)
            if float(r["component_count"]) > limit:
                component_ok = False
    raw_scar_delta = delta(frozen, "scar", "raw_direct")
    raw_edema_delta = delta(frozen, "edema_zone", "raw_direct")
    raw_scar_vol = summary.get((f"raw_direct_{frozen}", "scar"), {}).get("median_volume_ratio_positive")
    raw_edema_vol = summary.get((f"raw_direct_{frozen}", "edema_zone"), {}).get("median_volume_ratio_positive")
    ap = ap_report[frozen]
    mechanism_conditions = {
        "scar_coarse_auprc_gt_prevalence": ap["scar_coarse_auprc"] is not None and ap["scar_coarse_auprc"] > ap["scar_coarse_prevalence"],
        "edema_zone_coarse_auprc_gt_prevalence": ap["edema_zone_coarse_auprc"] is not None and ap["edema_zone_coarse_auprc"] > ap["edema_zone_coarse_prevalence"],
        "scar_presence_auprc_gt_prevalence": ap["scar_presence_auprc"] is not None and ap["scar_presence_auprc"] > ap["scar_presence_prevalence"],
        "edema_zone_presence_auprc_gt_prevalence": ap["edema_zone_presence_auprc"] is not None and ap["edema_zone_presence_auprc"] > ap["edema_zone_presence_prevalence"],
        "raw_scar_dice_delta_ge_minus_0_05": raw_scar_delta is not None and raw_scar_delta >= -0.05,
        "raw_edema_zone_dice_delta_ge_minus_0_05": raw_edema_delta is not None and raw_edema_delta >= -0.05,
        "scar_median_volume_ratio_in_range": raw_scar_vol is not None and 0.25 <= float(raw_scar_vol) <= 4.0,
        "edema_zone_median_volume_ratio_in_range": raw_edema_vol is not None and 0.25 <= float(raw_edema_vol) <= 4.0,
        "scar_changed_mask_fraction_ge_half": (changed_ok["scar"]["fraction_changed_at_least_5pct"] or 0.0) >= 0.50,
        "edema_zone_changed_mask_fraction_ge_half": (changed_ok["edema_zone"]["fraction_changed_at_least_5pct"] or 0.0) >= 0.50,
        "component_no_order_explosion": component_ok,
        "no_t2_exact_zero": not no_t2_failures,
        "anchor_context_invariance": context_invariance["status"] == "PASS",
    }
    gate_status = "PASS" if all(mechanism_conditions.values()) else "FAIL"
    detection_conditions = [
        mechanism_conditions["scar_coarse_auprc_gt_prevalence"],
        mechanism_conditions["edema_zone_coarse_auprc_gt_prevalence"],
        mechanism_conditions["scar_presence_auprc_gt_prevalence"],
        mechanism_conditions["edema_zone_presence_auprc_gt_prevalence"],
    ]
    volume_conditions = [
        mechanism_conditions["scar_median_volume_ratio_in_range"],
        mechanism_conditions["edema_zone_median_volume_ratio_in_range"],
    ]
    if gate_status == "PASS":
        failure_classification = ""
    elif not any(detection_conditions):
        failure_classification = "ENCODER_LIMITED"
    elif not all(detection_conditions):
        failure_classification = "DETECTION_LIMITED"
    elif not all(volume_conditions):
        failure_classification = "DETECTION_LIMITED"
    elif not mechanism_conditions["component_no_order_explosion"] or not mechanism_conditions["no_t2_exact_zero"]:
        failure_classification = "EXECUTION_FAILURE"
    else:
        failure_classification = "CONTOUR_LIMITED"
    gate = {
        "task_key": TASK_KEY,
        "created_at_utc": now_utc(),
        "stage": "W3_FOLD0_ZERO_CREDIT_DEVELOPMENT",
        "status": gate_status,
        "fold": int(args.fold),
        "role": args.role,
        "formal_training_credit": 0,
        "checkpoint": str(checkpoint.relative_to(REPO_ROOT) if checkpoint.is_relative_to(REPO_ROOT) else checkpoint),
        "frozen_alignment_mode": frozen,
        "raw_direct_dice_delta_vs_nnunet": {"scar": raw_scar_delta, "edema_zone": raw_edema_delta},
        "raw_direct_median_volume_ratio": {"scar": raw_scar_vol, "edema_zone": raw_edema_vol},
        "changed_mask": changed_ok,
        "mechanism_conditions": mechanism_conditions,
        "failure_classification": failure_classification,
    }
    volume_strata: dict[str, Any] = {}
    for pathology in ("scar", "edema_zone", "pure_edema"):
        strata = {"underseg": [], "near": [], "overseg": []}
        for r in [x for x in rows if x["variant"] == f"postprocessed_{frozen}" and x["pathology"] == pathology and x["gt_positive"]]:
            anchor = anchor_rows.get((r["case_id"], pathology), {})
            ratio = anchor.get("volume_ratio")
            if ratio is None:
                continue
            key = "underseg" if float(ratio) < 0.8 else ("overseg" if float(ratio) > 1.2 else "near")
            strata[key].append(float(r["dice"] or 0.0) - float(anchor.get("dice") or 0.0))
        volume_strata[pathology] = {k: {"n": len(v), "mean_dice_delta_candidate_minus_nnunet": float(np.mean(v)) if v else None} for k, v in strata.items()}
    mechanism = {
        "task_key": TASK_KEY,
        "created_at_utc": now_utc(),
        "checkpoint_step": int(payload.get("step", -1)),
        "ap_report": ap_report,
        "alignment_comparison": align_cmp,
        "context_invariance": context_invariance,
        "no_t2_failures": no_t2_failures,
        "summary_rows_path": str((out_root / "raw_direct_summary.csv").relative_to(REPO_ROOT)),
        "casewise_metrics_path": str((out_root / "casewise_metrics.csv").relative_to(REPO_ROOT)),
        "gate": gate,
    }
    write_csv(out_root / "casewise_metrics.csv", rows)
    write_csv(out_root / "raw_direct_summary.csv", summary_rows)
    write_csv(out_root / "alignment_control.csv", alignment_rows)
    write_json(out_root / "volume_stratified_report.json", volume_strata)
    write_json(out_root / "mechanism_report.json", mechanism)
    write_json(RESULT_ROOT / "fold0_development_adequacy_gate.json", gate)
    write_json(RESULT_ROOT / "alignment_mode_freeze_receipt.json", align_cmp)
    print(json.dumps(gate, indent=2, sort_keys=True), flush=True)
    return 0 if gate_status == "PASS" else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fold", type=int, required=True)
    parser.add_argument("--role", choices=["inner", "outer"], required=True)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--crop-hw", type=int, default=256)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--alignment-modes", default="enabled,identity")
    parser.add_argument("--nnunet-pred-dir", default=str(NNUNET_FOLD0))
    parser.add_argument("--scar-threshold", type=float, default=0.40)
    parser.add_argument("--edema-threshold", type=float, default=0.35)
    parser.add_argument("--scar-min-component-mm3", type=float, default=25.0)
    parser.add_argument("--edema-min-component-mm3", type=float, default=50.0)
    return run(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
