#!/usr/bin/env python3
"""Evaluate Lane A Round10 edema refiner predictions against baseline."""

from __future__ import annotations

import argparse
import csv
import math
import os
import sys
from pathlib import Path
from statistics import mean

import numpy as np
import SimpleITK as sitk


REPO_ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault("CARE_ROOT", str(REPO_ROOT))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.diagnostics import laneA_round4_fold0_short_train_eval as base_eval


OUT_ROOT = REPO_ROOT / "results/diagnostics/phase0_phase1/laneA_myops/round10_edema_refiner"
BASELINE_MODEL = "baseline_nnunet501_fold0"
CANDIDATE_MODEL = "candidate_laneA_round10_edema_refiner"
SUBSETS = [
    "all_case",
    "t2_present_gt_positive",
    "complete_modality",
    "CenterB",
    "CenterC",
    "no_t2_empty_gt",
    "modality:C0+LGE+T2",
    "modality:C0+LGE",
    "modality:LGE-only",
]


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    names = fieldnames or (list(rows[0].keys()) if rows else [])
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=names, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def finite(values: list[object]) -> list[float]:
    out = []
    for value in values:
        if value in ("", None):
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if not math.isnan(number) and not math.isinf(number):
            out.append(number)
    return out


def avg(values: list[object]) -> float | None:
    vals = finite(values)
    return float(mean(vals)) if vals else None


def delta(candidate: object, baseline: object, *, lower_is_better: bool = False) -> float | None:
    if candidate is None or baseline is None:
        return None
    try:
        c = float(candidate)
        b = float(baseline)
    except (TypeError, ValueError):
        return None
    if math.isnan(c) or math.isnan(b) or math.isinf(c) or math.isinf(b):
        return None
    return b - c if lower_is_better else c - b


def subset_filter(name: str):
    if name == "all_case":
        return lambda r: True
    if name == "t2_present_gt_positive":
        return lambda r: r.get("t2_present") is True and r.get("edema_gt_positive") is True
    if name == "complete_modality":
        return lambda r: r.get("modality_group") == "C0+LGE+T2"
    if name == "CenterB":
        return lambda r: r.get("center") == "CenterB"
    if name == "CenterC":
        return lambda r: r.get("center") == "CenterC"
    if name == "no_t2_empty_gt":
        return lambda r: r.get("t2_present") is False and r.get("edema_gt_positive") is False
    if name.startswith("modality:"):
        group = name.split(":", 1)[1]
        return lambda r: r.get("modality_group") == group
    raise ValueError(name)


def aggregate(rows: list[dict[str, object]], subset: str, model: str) -> dict[str, object]:
    filt = subset_filter(subset)
    items = [r for r in rows if r["model"] == model and not r.get("missing_prediction") and filt(r)]
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
    }


def compare(subset_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    by_key = {(r["model"], r["subset"]): r for r in subset_rows}
    out = []
    for subset in SUBSETS:
        b = by_key[(BASELINE_MODEL, subset)]
        c = by_key[(CANDIDATE_MODEL, subset)]
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
                "delta_edema_component_count_improvement": delta(
                    c["myops_edema_component_count"], b["myops_edema_component_count"], lower_is_better=True
                ),
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


def read_label(path: Path) -> tuple[sitk.Image, np.ndarray]:
    img = sitk.ReadImage(str(path))
    return img, sitk.GetArrayFromImage(img).astype(np.uint8, copy=False)


def scar_guardrail(candidate_pred_dir: Path) -> list[dict[str, object]]:
    rows = []
    for cid in base_eval.fold0_cases():
        gt_img, _ = read_label(base_eval.GT_DIR / f"{cid}.nii.gz")
        baseline = base_eval.read_pred(base_eval.BASELINE_PRED_DIR / f"{cid}.nii.gz", gt_img)
        candidate = base_eval.read_pred(candidate_pred_dir / f"{cid}.nii.gz", gt_img)
        scar_changed = int(np.logical_xor(baseline == 5, candidate == 5).sum())
        non_edema_changed = int(((baseline != candidate) & (baseline != 4) & (candidate != 4)).sum())
        rows.append(
            {
                "case_id": cid,
                "scar_changed_voxels": scar_changed,
                "non_edema_changed_voxels": non_edema_changed,
                "changed_voxels_total": int((baseline != candidate).sum()),
            }
        )
    return rows


def failure_flags(all_rows: list[dict[str, object]], scar_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    by_case: dict[str, dict[str, dict[str, object]]] = {}
    for row in all_rows:
        by_case.setdefault(str(row["case_id"]), {})[str(row["model"])] = row
    scar_by_case = {str(r["case_id"]): r for r in scar_rows}
    out = []
    for cid, pair in sorted(by_case.items()):
        b = pair.get(BASELINE_MODEL)
        c = pair.get(CANDIDATE_MODEL)
        flags = []
        if not b or not c or c.get("missing_prediction"):
            flags.append("missing_baseline_or_candidate")
        else:
            ed_dice_delta = delta(c.get("myops_edema_dice"), b.get("myops_edema_dice"))
            ed_hd95_delta = delta(c.get("myops_edema_hd95"), b.get("myops_edema_hd95"), lower_is_better=True)
            comp_delta = delta(c.get("myops_edema_component_count"), b.get("myops_edema_component_count"), lower_is_better=True)
            remote_delta = delta(c.get("myops_edema_remote_fp"), b.get("myops_edema_remote_fp"), lower_is_better=True)
            if ed_dice_delta is not None and ed_dice_delta > 0.005 and ed_hd95_delta is not None and ed_hd95_delta < -0.5:
                flags.append("edema_dice_up_hd95_worse")
            if comp_delta is not None and comp_delta < -0.5:
                flags.append("edema_component_worse")
            if remote_delta is not None and remote_delta < 0:
                flags.append("edema_remote_fp_worse")
            if c.get("t2_present") is False and c.get("edema_gt_positive") is False:
                if float(c.get("myops_edema_component_count") or 0) > float(b.get("myops_edema_component_count") or 0):
                    flags.append("no_t2_empty_gt_new_edema_fp")
        scar = scar_by_case.get(cid, {})
        if int(scar.get("scar_changed_voxels") or 0) != 0:
            flags.append("scar_changed")
        out.append(
            {
                "case_id": cid,
                "center": c.get("center") if c else "",
                "modality_group": c.get("modality_group") if c else "",
                "t2_present": c.get("t2_present") if c else "",
                "edema_gt_positive": c.get("edema_gt_positive") if c else "",
                "flags": ";".join(flags),
            }
        )
    return out


def decide(comparison_rows: list[dict[str, object]], flags: list[dict[str, object]]) -> tuple[str, list[str]]:
    hard = [r for r in flags if r.get("flags")]
    if hard:
        return "fail_stop_refiner_candidate", [f"{r['case_id']}: {r['flags']}" for r in hard[:20]]
    by_subset = {r["subset"]: r for r in comparison_rows}
    center = by_subset["CenterC"]
    t2pos = by_subset["t2_present_gt_positive"]
    positive = any(
        [
            isinstance(center.get("delta_edema_dice"), float) and center["delta_edema_dice"] > 0.005,
            isinstance(center.get("delta_edema_hd95_improvement"), float) and center["delta_edema_hd95_improvement"] > 0.5,
            isinstance(t2pos.get("delta_edema_dice"), float) and t2pos["delta_edema_dice"] > 0.005,
            isinstance(t2pos.get("delta_edema_hd95_improvement"), float) and t2pos["delta_edema_hd95_improvement"] > 0.5,
        ]
    )
    if positive:
        return "pass_watch_consider_fold0_short_refiner", ["clean positive T2-present or CenterC edema signal"]
    return "watch_stop_no_clear_positive_signal", ["no clean positive T2-present or CenterC edema signal"]


def md_table(rows: list[dict[str, object]], columns: list[str]) -> list[str]:
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(base_eval.fmt(row.get(col)) for col in columns) + " |")
    return lines


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-pred-dir", type=Path, required=True)
    parser.add_argument("--metrics-name", default="round10_fold0_very_short_metrics.csv")
    args = parser.parse_args()
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    baseline_rows = base_eval.build_case_rows(base_eval.BASELINE_PRED_DIR, BASELINE_MODEL)
    candidate_rows = base_eval.build_case_rows(args.candidate_pred_dir, CANDIDATE_MODEL)
    all_rows = baseline_rows + candidate_rows
    write_csv(OUT_ROOT / args.metrics_name, all_rows)
    subset_rows = []
    for model in [BASELINE_MODEL, CANDIDATE_MODEL]:
        for subset in SUBSETS:
            subset_rows.append(aggregate(all_rows, subset, model))
    comparison = compare(subset_rows)
    write_csv(OUT_ROOT / "baseline_vs_refiner_by_subset.csv", comparison)
    write_csv(OUT_ROOT / "no_t2_empty_gt_fp_table.csv", [r for r in candidate_rows if r.get("t2_present") is False and r.get("edema_gt_positive") is False])
    write_csv(OUT_ROOT / "centerB_centerC_edema_table.csv", [r for r in candidate_rows if r.get("center") in {"CenterB", "CenterC"}])
    scar_rows = scar_guardrail(args.candidate_pred_dir)
    write_csv(OUT_ROOT / "scar_unchanged_guardrail_table.csv", scar_rows)
    flags = failure_flags(all_rows, scar_rows)
    write_csv(OUT_ROOT / "case_level_failure_flags.csv", flags)
    decision, reasons = decide(comparison, flags)
    lines = [
        "# Lane A Round10 Refiner Decision",
        "",
        f"Decision: `{decision}`",
        "",
        "## Baseline vs Refiner By Subset",
        "",
        *md_table(
            comparison,
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
        "## Reasons",
        "",
        *[f"- {reason}" for reason in reasons],
        "",
        "No validation zip was created. No upload was performed. No fold1-4 refiner training was run.",
    ]
    (OUT_ROOT / "round10_decision_table.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (OUT_ROOT / "round10_next_actions.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Decision: {decision}")


if __name__ == "__main__":
    main()
