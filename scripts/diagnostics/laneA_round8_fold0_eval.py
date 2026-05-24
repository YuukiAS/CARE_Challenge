#!/usr/bin/env python3
"""Evaluate Lane A Round8 fold0 candidate against nnU-Net501 baseline."""

from __future__ import annotations

import csv
import math
import sys
from pathlib import Path
from statistics import mean


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.diagnostics import laneA_round04_fold0_short_train_eval as base_eval


OUT_ROOT = REPO_ROOT / "results/diagnostics/care_myocardium/laneA_myops/round08_t2_edema_expert"
CANDIDATE_PRED_DIR = (
    REPO_ROOT
    / "data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/"
    / "laneA_t2_edema_expert_sephead_fold0_short__nnUNetPlans__3d_fullres/fold_0/validation"
)
BASELINE_PRED_DIR = base_eval.BASELINE_PRED_DIR
BASELINE_MODEL = "baseline_nnunet501_fold0"
CANDIDATE_MODEL = "candidate_laneA_round08_t2_edema_expert"

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


def failure_flags(all_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    by_case: dict[str, dict[str, dict[str, object]]] = {}
    for row in all_rows:
        by_case.setdefault(str(row["case_id"]), {})[str(row["model"])] = row
    out = []
    for cid, pair in sorted(by_case.items()):
        b = pair.get(BASELINE_MODEL)
        c = pair.get(CANDIDATE_MODEL)
        if not b or not c or c.get("missing_prediction"):
            out.append({"case_id": cid, "flags": "missing_baseline_or_candidate"})
            continue
        flags = []
        ed_dice_delta = delta(c.get("myops_edema_dice"), b.get("myops_edema_dice"))
        ed_hd95_delta = delta(c.get("myops_edema_hd95"), b.get("myops_edema_hd95"), lower_is_better=True)
        comp_delta = delta(c.get("myops_edema_component_count"), b.get("myops_edema_component_count"), lower_is_better=True)
        remote_delta = delta(c.get("myops_edema_remote_fp"), b.get("myops_edema_remote_fp"), lower_is_better=True)
        scar_dice_delta = delta(c.get("myops_scar_dice"), b.get("myops_scar_dice"))
        scar_hd95_delta = delta(c.get("myops_scar_hd95"), b.get("myops_scar_hd95"), lower_is_better=True)
        if ed_dice_delta is not None and ed_dice_delta > 0.005 and ed_hd95_delta is not None and ed_hd95_delta < -0.5:
            flags.append("edema_dice_up_hd95_worse")
        if comp_delta is not None and comp_delta < -0.5:
            flags.append("edema_component_worse")
        if remote_delta is not None and remote_delta < 0:
            flags.append("edema_remote_fp_worse")
        if scar_dice_delta is not None and scar_dice_delta < -0.02:
            flags.append("scar_dice_guardrail_drop")
        if scar_hd95_delta is not None and scar_hd95_delta < -1.0:
            flags.append("scar_hd95_guardrail_worse")
        if c.get("t2_present") is False and c.get("edema_gt_positive") is False:
            if float(c.get("myops_edema_component_count") or 0) > float(b.get("myops_edema_component_count") or 0):
                flags.append("no_t2_empty_gt_new_edema_fp")
        out.append(
            {
                "case_id": cid,
                "center": c.get("center"),
                "modality_group": c.get("modality_group"),
                "t2_present": c.get("t2_present"),
                "edema_gt_positive": c.get("edema_gt_positive"),
                "delta_edema_dice": ed_dice_delta,
                "delta_edema_hd95_improvement": ed_hd95_delta,
                "delta_edema_component_count_improvement": comp_delta,
                "delta_edema_remote_fp_improvement": remote_delta,
                "delta_scar_dice": scar_dice_delta,
                "delta_scar_hd95_improvement": scar_hd95_delta,
                "flags": ";".join(flags),
            }
        )
    return out


def decide(comparison_rows: list[dict[str, object]], flag_rows: list[dict[str, object]]) -> tuple[str, list[str]]:
    if any(r.get("flags") for r in flag_rows):
        reasons = [f"{r['case_id']}: {r['flags']}" for r in flag_rows if r.get("flags")]
        return "fail_stop_no_longer_train", reasons[:20]
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
    return (
        ("pass_watch_consider_fold0_short_train", ["clean positive CenterC/T2-present edema signal"])
        if positive
        else ("watch_stop_no_clear_positive_signal", ["no clean CenterC or T2-present edema signal"])
    )


def md_table(rows: list[dict[str, object]], columns: list[str]) -> list[str]:
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(base_eval.fmt(row.get(col)) for col in columns) + " |")
    return lines


def main() -> None:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    baseline_rows = base_eval.build_case_rows(BASELINE_PRED_DIR, BASELINE_MODEL)
    candidate_rows = base_eval.build_case_rows(CANDIDATE_PRED_DIR, CANDIDATE_MODEL)
    all_rows = baseline_rows + candidate_rows
    write_csv(OUT_ROOT / "round8_fold0_very_short_metrics.csv", all_rows)
    write_csv(OUT_ROOT / "round8_fold0_short_train_metrics.csv", all_rows)

    subset_rows = []
    for model in [BASELINE_MODEL, CANDIDATE_MODEL]:
        for subset in SUBSETS:
            subset_rows.append(aggregate(all_rows, subset, model))
    comparison_rows = compare(subset_rows)
    write_csv(OUT_ROOT / "baseline_vs_candidate_by_subset.csv", comparison_rows)
    write_csv(OUT_ROOT / "no_t2_empty_gt_fp_table.csv", [r for r in candidate_rows if r.get("t2_present") is False and r.get("edema_gt_positive") is False])
    write_csv(OUT_ROOT / "centerB_centerC_edema_table.csv", [r for r in candidate_rows if r.get("center") in {"CenterB", "CenterC"}])
    write_csv(OUT_ROOT / "scar_guardrail_table.csv", [r for r in candidate_rows if not r.get("missing_prediction")])
    flags = failure_flags(all_rows)
    write_csv(OUT_ROOT / "case_level_failure_flags.csv", flags)
    decision, reasons = decide(comparison_rows, flags)
    lines = [
        "# Lane A Round8 Fold0 Very-Short Train Summary",
        "",
        "- Candidate: `T2-present edema expert + separated class_4 supervision + T2-absent abstention bias`",
        "- Scope: fold0 only; no validation zip; no upload; no fold1-4 expansion",
        "",
        "## Baseline vs Candidate By Subset",
        "",
        *md_table(
            comparison_rows,
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
        "## Decision",
        "",
        f"Decision: `{decision}`",
        "",
        "Reasons:",
        *[f"- {reason}" for reason in reasons],
    ]
    (OUT_ROOT / "round8_fold0_very_short_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (OUT_ROOT / "round8_decision_table.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote Round8 fold0 evaluation to {OUT_ROOT}")
    print(f"Decision: {decision}")


if __name__ == "__main__":
    main()
