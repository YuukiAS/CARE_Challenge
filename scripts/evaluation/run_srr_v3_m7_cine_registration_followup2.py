#!/usr/bin/env python3
"""M7 follow-up2 cropped/anatomy-guided Cine registration escalation."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from pathlib import Path

import numpy as np
import SimpleITK as sitk

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.evaluation.run_srr_v3_m7_cine_registration_repair import (
    OUT_ROOT,
    RUNTIME_ROOT,
    dice,
    extract_frame,
    frame_path,
    hd95,
    image_ncc,
    read_csv,
    run_antspy_syn,
    run_demons,
    selected_pairs,
    warp_segmentation,
    write_csv,
    write_text,
)


def mask_center(seg: sitk.Image) -> np.ndarray:
    arr = sitk.GetArrayFromImage(seg)
    mask = (arr == 2) | (arr == 3)
    coords = np.argwhere(mask)
    if coords.size == 0:
        return np.asarray(arr.shape, dtype=np.float64) / 2.0
    return coords.mean(axis=0)


def com_translation_warp(moving_seg: sitk.Image, fixed_seg: sitk.Image) -> tuple[sitk.Image, dict[str, object]]:
    delta_zyx = mask_center(fixed_seg) - mask_center(moving_seg)
    spacing = np.asarray(fixed_seg.GetSpacing(), dtype=np.float64)
    delta_xyz = np.asarray([delta_zyx[2], delta_zyx[1], delta_zyx[0]], dtype=np.float64) * spacing
    transform = sitk.TranslationTransform(3, [float(v) for v in delta_xyz])
    warped = sitk.Resample(moving_seg, fixed_seg, transform, sitk.sitkNearestNeighbor, 0, moving_seg.GetPixelID())
    return warped, {"displacement_smoothness": float(np.linalg.norm(delta_xyz)), "jacobian_or_fold_proxy": 0, "roundtrip_proxy": float(np.linalg.norm(delta_xyz))}


def row(
    *,
    method: str,
    pair: dict[str, object],
    fixed_img: sitk.Image,
    moving_img: sitk.Image,
    fixed_seg: sitk.Image,
    moving_seg: sitk.Image,
    warped_seg: sitk.Image | None,
    runtime_seconds: float,
    usable: bool,
    failure_reason: str,
    stats: dict[str, object] | None = None,
) -> dict[str, object]:
    stats = stats or {}
    seg = warped_seg if warped_seg is not None else moving_seg
    before_myo = dice(fixed_seg, moving_seg, 2)
    after_myo = dice(fixed_seg, seg, 2)
    before_lv = dice(fixed_seg, moving_seg, 3)
    after_lv = dice(fixed_seg, seg, 3)
    return {
        "method": method,
        "case_id": pair["case_id"],
        "reference_frame_id": pair["fixed_frame"],
        "moving_frame_id": pair["moving_frame"],
        "before_myo_dice": before_myo,
        "after_myo_dice": after_myo,
        "before_lv_dice": before_lv,
        "after_lv_dice": after_lv,
        "before_hd95": hd95(fixed_seg, moving_seg, 2),
        "after_hd95": hd95(fixed_seg, seg, 2),
        "before_ncc": image_ncc(fixed_img, moving_img),
        "after_ncc": "EVIDENCE_NOT_FOUND_SEGMENTATION_WARP_ONLY",
        "displacement_smoothness": stats.get("displacement_smoothness", stats.get("displacement_mean", "")),
        "jacobian_or_fold_proxy": stats.get("jacobian_or_fold_proxy", stats.get("jacobian_fold_voxels", "")),
        "roundtrip_proxy": stats.get("roundtrip_proxy", "EVIDENCE_NOT_FOUND"),
        "runtime_seconds": runtime_seconds,
        "usable_for_temporal_dictionary": bool(usable),
        "failure_reason": failure_reason,
    }


def usable_decision(r: dict[str, object]) -> bool:
    try:
        return (
            float(r["after_myo_dice"]) > float(r["before_myo_dice"])
            and float(r["after_lv_dice"]) >= float(r["before_lv_dice"])
            and float(r["after_hd95"]) <= float(r["before_hd95"])
        )
    except Exception:
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-cases", type=int, default=3)
    parser.add_argument("--pairs-per-case", type=int, default=2)
    parser.add_argument("--demons-iterations", type=int, default=40)
    parser.add_argument("--antspy-iterations", type=int, default=20)
    parser.add_argument("--skip-antspy", action="store_true")
    args = parser.parse_args()

    RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
    pairs = selected_pairs(args.max_cases, args.pairs_per_case)
    rows: list[dict[str, object]] = []
    for pair in pairs:
        cine_path = Path(pair["cine_path"])
        fixed_frame = int(pair["fixed_frame"])
        moving_frame = int(pair["moving_frame"])
        center = str(pair["center"])
        case_id = str(pair["case_id"])
        fixed_img = extract_frame(cine_path, fixed_frame)
        moving_img = extract_frame(cine_path, moving_frame)
        fixed_seg = sitk.ReadImage(str(frame_path(case_id, center, fixed_frame)))
        moving_seg = sitk.ReadImage(str(frame_path(case_id, center, moving_frame)))

        start = time.monotonic()
        try:
            warped, stats = com_translation_warp(moving_seg, fixed_seg)
            r = row(method="heart_crop_center_of_mass_affine", pair=pair, fixed_img=fixed_img, moving_img=moving_img, fixed_seg=fixed_seg, moving_seg=moving_seg, warped_seg=warped, runtime_seconds=time.monotonic() - start, usable=False, failure_reason="", stats=stats)
            r["usable_for_temporal_dictionary"] = usable_decision(r)
            if not r["usable_for_temporal_dictionary"]:
                r["failure_reason"] = "COM affine did not improve all required anatomy metrics"
            rows.append(r)
        except Exception as exc:
            rows.append(row(method="heart_crop_center_of_mass_affine", pair=pair, fixed_img=fixed_img, moving_img=moving_img, fixed_seg=fixed_seg, moving_seg=moving_seg, warped_seg=None, runtime_seconds=time.monotonic() - start, usable=False, failure_reason=f"{type(exc).__name__}:{exc}"))

        start = time.monotonic()
        try:
            displacement, stats = run_demons(fixed_img, moving_img, args.demons_iterations)
            warped = warp_segmentation(moving_seg, fixed_img, displacement)
            r = row(method="heart_crop_SimpleITK_BSpline_or_Demons_tuned", pair=pair, fixed_img=fixed_img, moving_img=moving_img, fixed_seg=fixed_seg, moving_seg=moving_seg, warped_seg=warped, runtime_seconds=time.monotonic() - start, usable=False, failure_reason="", stats=stats)
            r["usable_for_temporal_dictionary"] = usable_decision(r)
            if not r["usable_for_temporal_dictionary"]:
                r["failure_reason"] = "tuned Demons did not improve all required anatomy metrics"
            rows.append(r)
        except Exception as exc:
            rows.append(row(method="heart_crop_SimpleITK_BSpline_or_Demons_tuned", pair=pair, fixed_img=fixed_img, moving_img=moving_img, fixed_seg=fixed_seg, moving_seg=moving_seg, warped_seg=None, runtime_seconds=time.monotonic() - start, usable=False, failure_reason=f"{type(exc).__name__}:{exc}"))

        if (not args.skip_antspy) and importlib.util.find_spec("ants") is not None:
            start = time.monotonic()
            try:
                warped, stats = run_antspy_syn(fixed_img, moving_img, moving_seg, fixed_seg, args.antspy_iterations, RUNTIME_ROOT / f"followup2_ants_{case_id}_t{moving_frame:02d}_")
                r = row(method="ANTsPy_SyN_cropped_subset", pair=pair, fixed_img=fixed_img, moving_img=moving_img, fixed_seg=fixed_seg, moving_seg=moving_seg, warped_seg=warped, runtime_seconds=time.monotonic() - start, usable=False, failure_reason="", stats=stats)
                r["usable_for_temporal_dictionary"] = usable_decision(r)
                if not r["usable_for_temporal_dictionary"]:
                    r["failure_reason"] = "cropped SyN did not improve all required anatomy metrics"
                rows.append(r)
            except Exception as exc:
                rows.append(row(method="ANTsPy_SyN_cropped_subset", pair=pair, fixed_img=fixed_img, moving_img=moving_img, fixed_seg=fixed_seg, moving_seg=moving_seg, warped_seg=None, runtime_seconds=time.monotonic() - start, usable=False, failure_reason=f"{type(exc).__name__}:{exc}"))

        rows.append(row(method="optical_flow_proxy_warp", pair=pair, fixed_img=fixed_img, moving_img=moving_img, fixed_seg=fixed_seg, moving_seg=moving_seg, warped_seg=None, runtime_seconds=0.0, usable=False, failure_reason="proxy-only diagnostic; not sufficient as sole usable registration"))

    if not pairs:
        rows.append({"method": "EVIDENCE_NOT_FOUND", "case_id": "EVIDENCE_NOT_FOUND", "usable_for_temporal_dictionary": False, "failure_reason": "No safe cases/pairs available for follow-up2 Cine registration."})

    if importlib.util.find_spec("ants") is None and not args.skip_antspy:
        rows.append({"method": "ANTsPy_SyN_cropped_subset", "case_id": "availability_probe", "usable_for_temporal_dictionary": False, "failure_reason": "ANTsPy module not available"})
    rows.append({"method": "trained_or_trainable_voxelmorph_probe", "case_id": "availability_probe", "usable_for_temporal_dictionary": False, "failure_reason": "No trained CARE CineMyoPS VoxelMorph weights found; untrained VoxelMorph remains negative control."})

    usable_rows = [r for r in rows if str(r.get("usable_for_temporal_dictionary", "")).lower() == "true"]
    write_csv(OUT_ROOT / "registration_same_subset_matrix.csv", rows)
    if usable_rows:
        temporal = [{
            "status": "TEMPORAL_DICTIONARY_FOLLOWUP2_REQUIRED_NOT_EXECUTED",
            "ed_reference_anchor_feature": "frame0",
            "selected_non_reference_frame_id": usable_rows[0].get("moving_frame_id", ""),
            "warped_source": usable_rows[0].get("method", ""),
            "registration_quality": "usable_row_present",
            "frame_quality": "safe_case_subset",
            "motion_saliency": "EVIDENCE_NOT_FOUND",
            "temporal_representer_slot_usage": "PENDING_DICTIONARY_IMPLEMENTATION",
            "aggregation_output_summary": "NOT_RUN_IN_FOLLOWUP2",
            "local_class_1_myocardium_proxy": "EVIDENCE_NOT_FOUND",
            "hosted_metric_caveat": "no hosted metric claim",
            "temporal_dictionary_attempted": False,
        }]
        cine_decision = "CINE_REGISTRATION_HAS_USABLE_ROW_TEMPORAL_DICTIONARY_REQUIRED_NOT_EXECUTED"
    else:
        temporal = [{"status": "CINE_REGISTRATION_BLOCKED_AFTER_FOLLOWUP2_ESCALATION", "usable_nonreference_registration": False, "temporal_dictionary_attempted": False, "reason": "No non-reference registration row passed the follow-up2 usability rule."}]
        cine_decision = "CINE_REGISTRATION_BLOCKED_AFTER_FOLLOWUP2_ESCALATION"
    write_csv(OUT_ROOT / "temporal_dictionary_evidence.csv", temporal)
    write_csv(OUT_ROOT / "cine_metrics_summary.csv", rows)
    write_text(
        OUT_ROOT / "cine_registration_followup2_report.md",
        "# Cine Registration Follow-up2 Report\n\n"
        f"status: `EXECUTED_UNAUDITED`\n\ncine_decision: `{cine_decision}`\n\n"
        f"- pairs attempted: `{len(pairs)}`\n"
        "- attempted: `heart_crop_center_of_mass_affine`, `heart_crop_SimpleITK_BSpline_or_Demons_tuned`, `ANTsPy_SyN_cropped_subset` when available, `optical_flow_proxy_warp`, `trained_or_trainable_voxelmorph_probe`.\n"
        "- temporal dictionary remains blocked unless `registration_same_subset_matrix.csv` contains a usable non-reference row.\n",
    )
    print(json.dumps({"cine_decision": cine_decision, "rows": len(rows), "usable_rows": len(usable_rows)}, indent=2))


if __name__ == "__main__":
    main()
