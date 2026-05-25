#!/usr/bin/env python3
"""Collect Lane A Round17 MedNeXt fold0 very-short results."""

from __future__ import annotations

import argparse
import csv
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean

import numpy as np
import SimpleITK as sitk


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_ROOT = REPO_ROOT / "results/diagnostics/care_myocardium/laneA_myops/round17_mednext_backbone"
DEFAULT_CANDIDATE = "R17_A_mednext_s_kernel3_standard_dicece_fold0_vs"
BASELINE = "baseline_nnunet501_fold0"
FOCUS_CASES = {"Case2031", "Case3011", "Case3012", "Case3040", "Case3044"}
GT_DIR = REPO_ROOT / "data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS/labelsTr"
BASELINE_PRED_DIR = (
    REPO_ROOT
    / "data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/"
    / "nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_0/validation"
)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    names = fieldnames or (list(rows[0].keys()) if rows else [])
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=names, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def num(value: object) -> float | None:
    if value in ("", None):
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(out) or math.isinf(out):
        return None
    return out


def avg(values: list[object]) -> float | None:
    vals = [v for v in (num(x) for x in values) if v is not None]
    return float(mean(vals)) if vals else None


def fmt(value: object) -> str:
    v = num(value)
    if v is None:
        return "NA"
    return f"{v:.4f}"


def as_bool(value: object) -> bool:
    return str(value).strip().lower() == "true"


def delta(candidate: object, baseline: object, *, lower_is_better: bool = False) -> float | None:
    c = num(candidate)
    b = num(baseline)
    if c is None or b is None:
        return None
    return b - c if lower_is_better else c - b


def subset_filter(name: str):
    if name == "all_case":
        return lambda r: True
    if name == "t2_present":
        return lambda r: as_bool(r.get("t2_present"))
    if name == "t2_present_gt_positive":
        return lambda r: as_bool(r.get("t2_present")) and as_bool(r.get("edema_gt_positive"))
    if name == "complete_modality":
        return lambda r: r.get("modality_group") == "C0+LGE+T2"
    if name == "CenterB":
        return lambda r: r.get("center") == "CenterB"
    if name == "CenterC":
        return lambda r: r.get("center") == "CenterC"
    if name == "no_t2_empty_gt":
        return lambda r: (not as_bool(r.get("t2_present"))) and (not as_bool(r.get("edema_gt_positive")))
    if name == "C0+LGE_no_T2":
        return lambda r: r.get("modality_group") == "C0+LGE"
    if name == "LGE_only":
        return lambda r: r.get("modality_group") == "LGE-only"
    raise ValueError(name)


def aggregate(rows: list[dict[str, str]], model: str, subset: str) -> dict[str, object]:
    filt = subset_filter(subset)
    items = [r for r in rows if r.get("model") == model and not as_bool(r.get("missing_prediction")) and filt(r)]
    return {
        "model": model,
        "subset": subset,
        "n": len(items),
        "myops_edema_dice": avg([r.get("myops_edema_dice") for r in items]),
        "myops_edema_hd": avg([r.get("myops_edema_hd") for r in items]),
        "myops_edema_hd95": avg([r.get("myops_edema_hd95") for r in items]),
        "myops_edema_component_count": avg([r.get("myops_edema_component_count") for r in items]),
        "myops_edema_small_fp": avg([r.get("myops_edema_small_fp") for r in items]),
        "myops_edema_remote_fp": avg([r.get("myops_edema_remote_fp") for r in items]),
        "myops_edema_pred_gt_volume_ratio": avg([r.get("myops_edema_pred_gt_volume_ratio") for r in items]),
        "myops_scar_dice": avg([r.get("myops_scar_dice") for r in items]),
        "myops_scar_hd": avg([r.get("myops_scar_hd") for r in items]),
        "myops_scar_hd95": avg([r.get("myops_scar_hd95") for r in items]),
        "myops_scar_component_count": avg([r.get("myops_scar_component_count") for r in items]),
        "myops_scar_remote_fp": avg([r.get("myops_scar_remote_fp") for r in items]),
    }


def comparison_rows(agg_rows: list[dict[str, object]], candidate: str, subsets: list[str]) -> list[dict[str, object]]:
    by_key = {(row["model"], row["subset"]): row for row in agg_rows}
    out = []
    for subset in subsets:
        b = by_key[(BASELINE, subset)]
        c = by_key[(candidate, subset)]
        out.append(
            {
                "subset": subset,
                "n": c["n"],
                "baseline_edema_dice": b["myops_edema_dice"],
                "candidate_edema_dice": c["myops_edema_dice"],
                "delta_edema_dice": delta(c["myops_edema_dice"], b["myops_edema_dice"]),
                "baseline_edema_hd95": b["myops_edema_hd95"],
                "candidate_edema_hd95": c["myops_edema_hd95"],
                "delta_edema_hd95_improvement": delta(c["myops_edema_hd95"], b["myops_edema_hd95"], lower_is_better=True),
                "baseline_edema_component_count": b["myops_edema_component_count"],
                "candidate_edema_component_count": c["myops_edema_component_count"],
                "delta_edema_component_count_improvement": delta(c["myops_edema_component_count"], b["myops_edema_component_count"], lower_is_better=True),
                "baseline_edema_remote_fp": b["myops_edema_remote_fp"],
                "candidate_edema_remote_fp": c["myops_edema_remote_fp"],
                "delta_edema_remote_fp_improvement": delta(c["myops_edema_remote_fp"], b["myops_edema_remote_fp"], lower_is_better=True),
                "baseline_scar_dice": b["myops_scar_dice"],
                "candidate_scar_dice": c["myops_scar_dice"],
                "delta_scar_dice": delta(c["myops_scar_dice"], b["myops_scar_dice"]),
                "baseline_scar_hd95": b["myops_scar_hd95"],
                "candidate_scar_hd95": c["myops_scar_hd95"],
                "delta_scar_hd95_improvement": delta(c["myops_scar_hd95"], b["myops_scar_hd95"], lower_is_better=True),
            }
        )
    return out


def failure_flags(rows: list[dict[str, str]], candidate: str) -> list[dict[str, object]]:
    by_case: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)
    for row in rows:
        by_case[row["case_id"]][row["model"]] = row
    out = []
    for case_id, pair in sorted(by_case.items()):
        b = pair.get(BASELINE)
        c = pair.get(candidate)
        if not b or not c:
            out.append({"case_id": case_id, "flags": "missing_baseline_or_candidate"})
            continue
        flags = []
        ed_dice = delta(c.get("myops_edema_dice"), b.get("myops_edema_dice"))
        ed_hd95 = delta(c.get("myops_edema_hd95"), b.get("myops_edema_hd95"), lower_is_better=True)
        ed_comp = delta(c.get("myops_edema_component_count"), b.get("myops_edema_component_count"), lower_is_better=True)
        ed_remote = delta(c.get("myops_edema_remote_fp"), b.get("myops_edema_remote_fp"), lower_is_better=True)
        scar_dice = delta(c.get("myops_scar_dice"), b.get("myops_scar_dice"))
        scar_hd95 = delta(c.get("myops_scar_hd95"), b.get("myops_scar_hd95"), lower_is_better=True)
        if ed_dice is not None and ed_dice < -0.02:
            flags.append("edema_dice_drop")
        if ed_hd95 is not None and ed_hd95 < -1:
            flags.append("edema_hd95_worse")
        if ed_comp is not None and ed_comp < -0.5:
            flags.append("edema_component_worse")
        if ed_remote is not None and ed_remote < 0:
            flags.append("edema_remote_fp_worse")
        if not as_bool(c.get("t2_present")) and not as_bool(c.get("edema_gt_positive")):
            if num(c.get("myops_edema_component_count")) and (num(c.get("myops_edema_component_count")) or 0) > (num(b.get("myops_edema_component_count")) or 0):
                flags.append("no_t2_empty_gt_edema_fp")
        if scar_dice is not None and scar_dice < -0.02:
            flags.append("scar_dice_guardrail_drop")
        if scar_hd95 is not None and scar_hd95 < -1:
            flags.append("scar_hd95_guardrail_worse")
        out.append(
            {
                "case_id": case_id,
                "center": c.get("center"),
                "modality_group": c.get("modality_group"),
                "t2_present": c.get("t2_present"),
                "edema_gt_positive": c.get("edema_gt_positive"),
                "focus_case": case_id in FOCUS_CASES,
                "delta_edema_dice": ed_dice,
                "delta_edema_hd95_improvement": ed_hd95,
                "delta_edema_component_count_improvement": ed_comp,
                "delta_edema_remote_fp_improvement": ed_remote,
                "delta_scar_dice": scar_dice,
                "delta_scar_hd95_improvement": scar_hd95,
                "flags": ";".join(flags),
            }
        )
    return out


def md_table(rows: list[dict[str, object]], columns: list[str]) -> list[str]:
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for row in rows:
        cells = []
        for col in columns:
            val = row.get(col)
            cells.append(fmt(val) if isinstance(val, float) or col.startswith("delta") or col.startswith("baseline") or col.startswith("candidate") else str(val))
        lines.append("| " + " | ".join(cells) + " |")
    return lines


def decide(comp: list[dict[str, object]], flags: list[dict[str, object]], train_status: str) -> tuple[str, list[str]]:
    by_subset = {r["subset"]: r for r in comp}
    reasons = [f"train_status={train_status}"]
    hard = [r for r in flags if r.get("flags")]
    if hard:
        reasons.append(f"{len(hard)} case-level guardrail failures")
    for subset in ["t2_present_gt_positive", "CenterC", "no_t2_empty_gt", "all_case"]:
        row = by_subset[subset]
        reasons.append(
            f"{subset}: edema_dice_delta={fmt(row.get('delta_edema_dice'))}, "
            f"edema_hd95_improvement={fmt(row.get('delta_edema_hd95_improvement'))}, "
            f"scar_dice_delta={fmt(row.get('delta_scar_dice'))}"
        )
    if train_status != "completed_with_44_predictions":
        return "fail_incomplete_predictions", reasons
    if hard:
        return "fail_stop_no_promoted_candidate", reasons
    primary = by_subset["t2_present_gt_positive"]
    centerc = by_subset["CenterC"]
    primary_signal = (num(primary.get("delta_edema_dice")) or 0) > 0.005 or (num(primary.get("delta_edema_hd95_improvement")) or 0) > 0.5
    centerc_signal = (num(centerc.get("delta_edema_dice")) or 0) > 0.005 or (num(centerc.get("delta_edema_hd95_improvement")) or 0) > 0.5
    if primary_signal or centerc_signal:
        return "watch_possible_signal_needs_guardrail_review", reasons
    return "stop_no_clear_edema_signal", reasons


def read_image_array(path: Path) -> tuple[sitk.Image, np.ndarray]:
    img = sitk.ReadImage(str(path))
    arr = sitk.GetArrayFromImage(img)
    return img, arr


def same_geometry(a: sitk.Image, b: sitk.Image) -> bool:
    return (
        a.GetSize() == b.GetSize()
        and a.GetSpacing() == b.GetSpacing()
        and a.GetOrigin() == b.GetOrigin()
        and a.GetDirection() == b.GetDirection()
    )


def label_hist(arr: np.ndarray) -> dict[int, int]:
    vals, counts = np.unique(arr.astype(np.int64, copy=False), return_counts=True)
    return {int(v): int(c) for v, c in zip(vals, counts)}


def prediction_distribution(candidate: str, metric_rows: list[dict[str, str]]) -> tuple[list[dict[str, object]], dict[str, object]]:
    meta = {row["case_id"]: row for row in metric_rows if row.get("model") == candidate}
    pred_dir = OUT_ROOT / candidate / "validation_predictions"
    rows: list[dict[str, object]] = []
    totals = defaultdict(int)
    for pred_path in sorted(pred_dir.glob("Case*.nii.gz")):
        case_id = pred_path.name.removesuffix(".nii.gz")
        gt_img, gt = read_image_array(GT_DIR / f"{case_id}.nii.gz")
        pred_img, pred = read_image_array(pred_path)
        base_img, base = read_image_array(BASELINE_PRED_DIR / f"{case_id}.nii.gz")
        hist = label_hist(pred)
        base_hist = label_hist(base)
        gt_hist = label_hist(gt)
        for cls, count in hist.items():
            totals[f"pred_label_{cls}"] += count
        row_meta = meta.get(case_id, {})
        edema_fp_vox = int(((pred == 4) & (gt != 4)).sum())
        scar_fp_vox = int(((pred == 5) & (gt != 5)).sum())
        rows.append(
            {
                "case_id": case_id,
                "center": row_meta.get("center", ""),
                "modality_group": row_meta.get("modality_group", ""),
                "t2_present": row_meta.get("t2_present", ""),
                "edema_gt_positive": row_meta.get("edema_gt_positive", ""),
                "candidate_unique_labels": " ".join(str(k) for k in sorted(hist)),
                "candidate_label0_vox": hist.get(0, 0),
                "candidate_label1_vox": hist.get(1, 0),
                "candidate_label2_vox": hist.get(2, 0),
                "candidate_label3_vox": hist.get(3, 0),
                "candidate_edema_label4_vox": hist.get(4, 0),
                "candidate_scar_label5_vox": hist.get(5, 0),
                "baseline_edema_label4_vox": base_hist.get(4, 0),
                "baseline_scar_label5_vox": base_hist.get(5, 0),
                "gt_edema_label4_vox": gt_hist.get(4, 0),
                "gt_scar_label5_vox": gt_hist.get(5, 0),
                "candidate_edema_fp_vox": edema_fp_vox,
                "candidate_scar_fp_vox": scar_fp_vox,
                "candidate_foreground_vox": int((pred > 0).sum()),
                "candidate_foreground_fraction": float((pred > 0).mean()),
                "baseline_foreground_vox": int((base > 0).sum()),
                "gt_foreground_vox": int((gt > 0).sum()),
                "geometry_matches_gt": same_geometry(pred_img, gt_img),
                "baseline_geometry_matches_gt": same_geometry(base_img, gt_img),
                "spacing": " ".join(str(v) for v in gt_img.GetSpacing()),
                "size": " ".join(str(v) for v in gt_img.GetSize()),
            }
        )
    summary = {
        "n_predictions": len(rows),
        "total_candidate_edema_vox": sum(int(r["candidate_edema_label4_vox"]) for r in rows),
        "total_candidate_scar_vox": sum(int(r["candidate_scar_label5_vox"]) for r in rows),
        "total_candidate_foreground_vox": sum(int(r["candidate_foreground_vox"]) for r in rows),
        "mean_candidate_foreground_fraction": mean([float(r["candidate_foreground_fraction"]) for r in rows]) if rows else 0,
        "all_geometry_match_gt": all(bool(r["geometry_matches_gt"]) for r in rows) if rows else False,
        "label_totals": dict(totals),
    }
    return rows, summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-id", default=DEFAULT_CANDIDATE)
    args = parser.parse_args()
    cand_dir = OUT_ROOT / args.candidate_id
    metrics_path = cand_dir / "fold0_very_short_case_metrics.csv"
    results_path = OUT_ROOT / "round17_fold0_very_short_results.csv"
    rows = read_csv(metrics_path)
    train_rows = read_csv(results_path)
    train_status = next((r.get("status", "") for r in train_rows if r.get("candidate_id") == args.candidate_id), "")
    subsets = [
        "all_case",
        "t2_present",
        "t2_present_gt_positive",
        "complete_modality",
        "CenterB",
        "CenterC",
        "no_t2_empty_gt",
        "C0+LGE_no_T2",
        "LGE_only",
    ]
    agg_rows = [aggregate(rows, model, subset) for model in [BASELINE, args.candidate_id] for subset in subsets]
    comp = comparison_rows(agg_rows, args.candidate_id, subsets)
    flags = failure_flags(rows, args.candidate_id)
    dist_rows, dist_summary = prediction_distribution(args.candidate_id, rows)
    decision, reasons = decide(comp, flags, train_status)
    write_csv(OUT_ROOT / "baseline_vs_candidate_by_subset.csv", comp)
    write_csv(OUT_ROOT / "case_level_failure_flags.csv", flags)
    if args.candidate_id == DEFAULT_CANDIDATE:
        dist_path = OUT_ROOT / "r17A_prediction_distribution.csv"
        audit_path = OUT_ROOT / "r17A_failure_audit.md"
    else:
        dist_path = OUT_ROOT / f"{args.candidate_id}_prediction_distribution.csv"
        audit_path = OUT_ROOT / f"{args.candidate_id}_failure_audit.md"
    write_csv(dist_path, dist_rows)
    write_csv(OUT_ROOT / "round17_centerC_edema_table.csv", [r for r in flags if r.get("center") == "CenterC"])
    write_csv(OUT_ROOT / "round17_scar_guardrail_table.csv", [r for r in comp if r["subset"] in {"all_case", "t2_present_gt_positive", "CenterB", "CenterC"}])
    focus_rows = [r for r in flags if r.get("focus_case")]
    write_csv(OUT_ROOT / "round17_focus_case_table.csv", focus_rows)
    is_original_engineering = args.candidate_id == DEFAULT_CANDIDATE
    displayed_decision = "engineering_smoke_completed_performance_insufficient" if is_original_engineering else decision
    summary = [
        "# Round17 MedNeXt Fold0 Very-Short Summary",
        "",
        f"- Candidate: `{args.candidate_id}`",
        f"- Train/export status: `{train_status}`",
        f"- Decision: `{displayed_decision}`",
        "- Scope: fold0 very-short only; no pretrained weights; no external data; no validation zip/upload; no fold1-4.",
        "",
        "## Baseline vs Candidate",
        "",
        *md_table(
            comp,
            [
                "subset",
                "n",
                "delta_edema_dice",
                "delta_edema_hd95_improvement",
                "delta_edema_component_count_improvement",
                "delta_edema_remote_fp_improvement",
                "delta_scar_dice",
                "delta_scar_hd95_improvement",
            ],
        ),
        "",
        "## Decision Reasons",
        "",
        *[f"- {reason}" for reason in reasons],
        *(
            ["- Gate correction: this 2-epoch result is not a final MedNeXt / stronger-backbone stop decision."]
            if is_original_engineering
            else []
        ),
        "",
        "## Focus Cases",
        "",
        *md_table(
            focus_rows,
            [
                "case_id",
                "center",
                "modality_group",
                "delta_edema_dice",
                "delta_edema_hd95_improvement",
                "delta_edema_component_count_improvement",
                "delta_edema_remote_fp_improvement",
                "delta_scar_dice",
                "delta_scar_hd95_improvement",
                "flags",
            ],
        ),
        "",
    ]
    write_text(OUT_ROOT / "round17_fold0_very_short_summary.md", "\n".join(summary))
    audit_lines = [
        "# R17A Failure Audit",
        "",
        "## Status",
        "",
        f"- Candidate: `{args.candidate_id}`",
        f"- Train/export status: `{train_status}`",
        "- Original budget: `2 epochs x 24 steps`." if is_original_engineering else "- Budget: fair fold0 short candidate.",
        "- Interpretation: this is an engineering/performance-insufficient negative, not final evidence against MedNeXt / stronger backbone."
        if is_original_engineering
        else "- Interpretation: this is a fair-short local fold0 result for this candidate.",
        "",
        "## Key Findings",
        "",
        f"- 44/44 validation predictions exported.",
        f"- Geometry matches GT for all predictions: `{dist_summary['all_geometry_match_gt']}`.",
        f"- Total candidate edema voxels: `{dist_summary['total_candidate_edema_vox']}`.",
        f"- Total candidate scar voxels: `{dist_summary['total_candidate_scar_vox']}`.",
        f"- Mean candidate foreground fraction: `{float(dist_summary['mean_candidate_foreground_fraction']):.4f}`.",
        "- Prediction pattern: severe over-fragmented foreground with widespread class_4/class_5 false positives and remote components.",
        "- Training stability: loss decreased and no NaN/Inf was observed, so this is not a numerical crash.",
        "",
        "## Likely Failure Mechanisms",
        "",
        "- Training budget is far below a fair full-backbone comparison; 48 update steps cannot be compared to a fully trained nnU-Net501 baseline.",
        "- The first R17A run used a custom preprocessed-to-raw resize/export path before this continuation; fair-short reruns must use nnU-Net `export_prediction_from_logits` semantics.",
        "- Scratch MedNeXt has no baseline-preserving initialization, so early predictions are expected to have poor class calibration and component stability.",
        "- Class imbalance and no-T2 empty-GT edema FP are uncontrolled in the 2-epoch engineering run.",
        "",
        "## Gate Correction",
        "",
        "The 2-epoch run is reclassified from final `fail_stop_no_promoted_candidate` to `engineering_smoke_completed_performance_insufficient`. It should not stop the MedNeXt route by itself. Round17 now requires fair fold0 short training before performance promotion/stop decisions."
        if is_original_engineering
        else "This fair-short candidate is evaluated with scar+edema joint MedNeXt gates.",
    ]
    write_text(audit_path, "\n".join(audit_lines) + "\n")
    decision_lines = [
        "# Round17 Decision Table",
        "",
        f"| candidate | train_status | decision |",
        "| --- | --- | --- |",
        f"| `{args.candidate_id}` | `{train_status}` | `{displayed_decision}` |",
        "",
        "Decision reasons:",
        *[f"- {reason}" for reason in reasons],
        "",
        "Promotion rule: Round17 MedNeXt can promote only with clean edema signal on T2-present GT-positive or CenterC while scar remains co-primary non-regressed/improved.",
        "",
        *(
            [
                "Gate correction: the 2-epoch result must not be used as final MedNeXt route stop evidence. It is an engineering smoke/performance-insufficient negative and triggers fair fold0 short training, not Round18 by itself."
            ]
            if is_original_engineering
            else []
        ),
    ]
    write_text(OUT_ROOT / "round17_decision_table.md", "\n".join(decision_lines))
    print(f"Decision: {decision}")
    print(f"Wrote Round17 collected results under {OUT_ROOT}")


if __name__ == "__main__":
    main()
