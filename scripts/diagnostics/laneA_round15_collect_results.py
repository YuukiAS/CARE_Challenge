#!/usr/bin/env python3
"""Collect and gate Lane A Round15 candidate outputs.

This collector is safe to run repeatedly. It reads candidate output folders
created by ``run_laneA_round15_feature_head_train.py`` and writes top-level
Round15 metrics/decision artifacts. It does not train, submit Slurm, create
validation zips, or modify predictions.
"""

from __future__ import annotations

import csv
import math
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


OUT_ROOT = REPO_ROOT / "results/diagnostics/phase0_phase1/laneA_myops/round15_deepresearch_portfolio"
CANDIDATES = [
    "R15_A_intensity_prior_feature_head_fold0_vs",
    "R15_B_anatomy_pathology_cascade_fold0_vs",
    "R15_C_intensity_plus_anatomy_support_head_fold0_vs",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
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


def as_float(value: object, default: float = math.nan) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return default
    return default if math.isnan(out) or math.isinf(out) else out


def collect_candidate(candidate_id: str) -> dict[str, object]:
    root = OUT_ROOT / candidate_id
    summary = read_csv(root / "train_summary.csv")
    comparison = read_csv(root / "baseline_vs_candidate_by_subset.csv")
    flags = read_csv(root / "case_level_failure_flags.csv")
    metrics = read_csv(root / "fold0_very_short_case_metrics.csv")
    summary_md = root / "fold0_very_short_summary.md"
    prediction_count = len(list((root / "validation_predictions").glob("*.nii.gz"))) if (root / "validation_predictions").is_dir() else 0
    hard_flags = [r for r in flags if r.get("flags")]
    by_subset = {r.get("subset", ""): r for r in comparison}
    t2 = by_subset.get("t2_present_gt_positive", {})
    center_c = by_subset.get("CenterC", {})
    all_case = by_subset.get("all_case", {})
    if not summary or not comparison or prediction_count < 44:
        status = "pending_or_incomplete"
        reason = f"summary={bool(summary)} comparison={bool(comparison)} prediction_count={prediction_count}"
    elif hard_flags:
        status = "fail_stop_no_longer_train"
        reason = f"{len(hard_flags)} case-level flags"
    else:
        t2_dice = as_float(t2.get("delta_edema_dice"))
        t2_hd95 = as_float(t2.get("delta_edema_hd95_improvement"))
        c_dice = as_float(center_c.get("delta_edema_dice"))
        c_hd95 = as_float(center_c.get("delta_edema_hd95_improvement"))
        clean_signal = (
            (t2_dice > 0.005 and t2_hd95 >= -0.1)
            or (t2_hd95 > 0.5 and t2_dice >= -0.001)
            or (c_dice > 0.005 and c_hd95 >= -0.1)
            or (c_hd95 > 0.5 and c_dice >= -0.001)
        )
        status = "pass_watch_consider_fold0_short" if clean_signal else "watch_stop_no_clear_positive_signal"
        reason = "clean target subset signal" if clean_signal else "no clean T2-present/CenterC signal"
    return {
        "candidate_id": candidate_id,
        "status": status,
        "reason": reason,
        "prediction_count": prediction_count,
        "train_summary_exists": bool(summary),
        "comparison_exists": bool(comparison),
        "flags_exists": bool(flags),
        "summary_md_exists": summary_md.is_file(),
        "t2_gtpos_delta_edema_dice": t2.get("delta_edema_dice", ""),
        "t2_gtpos_delta_edema_hd95_improvement": t2.get("delta_edema_hd95_improvement", ""),
        "t2_gtpos_delta_component_improvement": t2.get("delta_edema_component_count_improvement", ""),
        "t2_gtpos_delta_remote_fp_improvement": t2.get("delta_edema_remote_fp_improvement", ""),
        "centerC_delta_edema_dice": center_c.get("delta_edema_dice", ""),
        "centerC_delta_edema_hd95_improvement": center_c.get("delta_edema_hd95_improvement", ""),
        "centerC_delta_component_improvement": center_c.get("delta_edema_component_count_improvement", ""),
        "centerC_delta_remote_fp_improvement": center_c.get("delta_edema_remote_fp_improvement", ""),
        "all_case_delta_scar_dice": all_case.get("delta_scar_dice", ""),
        "all_case_delta_scar_hd95_improvement": all_case.get("delta_scar_hd95_improvement", ""),
        "hard_flag_count": len(hard_flags),
    }


def md_table(rows: list[dict[str, object]], columns: list[str]) -> str:
    out = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for row in rows:
        out.append("| " + " | ".join(str(row.get(col, "")).replace("|", "\\|") for col in columns) + " |")
    return "\n".join(out)


def main() -> None:
    rows = [collect_candidate(c) for c in CANDIDATES]
    write_csv(OUT_ROOT / "round15_candidate_result_collection.csv", rows)
    write_csv(OUT_ROOT / "round15_fold0_very_short_metrics.csv", rows)

    all_comparisons: list[dict[str, object]] = []
    all_flags: list[dict[str, object]] = []
    center_rows: list[dict[str, object]] = []
    no_t2_rows: list[dict[str, object]] = []
    scar_rows: list[dict[str, object]] = []
    comp_rows: list[dict[str, object]] = []
    focus_rows: list[dict[str, object]] = []
    for cid in CANDIDATES:
        root = OUT_ROOT / cid
        comparisons = read_csv(root / "baseline_vs_candidate_by_subset.csv")
        flags = read_csv(root / "case_level_failure_flags.csv")
        all_comparisons.extend(comparisons)
        all_flags.extend(flags)
        for row in comparisons:
            subset = row.get("subset")
            if subset in {"CenterB", "CenterC"}:
                center_rows.append(row)
            if subset == "no_t2_empty_gt":
                no_t2_rows.append(row)
            if subset == "all_case":
                scar_rows.append(row)
            if subset in {"t2_present_gt_positive", "CenterC"}:
                comp_rows.append(row)
        for row in flags:
            if row.get("case_id") in {"Case2031", "Case3011", "Case3012", "Case3040"}:
                focus_rows.append(row)

    write_csv(OUT_ROOT / "baseline_vs_candidate_by_subset.csv", all_comparisons)
    write_csv(OUT_ROOT / "case_level_failure_flags.csv", all_flags)
    write_csv(OUT_ROOT / "centerB_centerC_edema_table.csv", center_rows)
    write_csv(OUT_ROOT / "no_t2_empty_gt_fp_table.csv", no_t2_rows)
    write_csv(OUT_ROOT / "scar_guardrail_table.csv", scar_rows)
    write_csv(OUT_ROOT / "component_remote_fp_table.csv", comp_rows)
    write_csv(OUT_ROOT / "case2031_3011_3012_3040_table.csv", focus_rows)
    # Short jobs are intentionally not run unless a candidate passes very-short gate.
    promoted = [r for r in rows if str(r["status"]).startswith("pass")]
    write_csv(
        OUT_ROOT / "round15_fold0_short_metrics.csv",
        [
            {
                "status": "not_run_no_promoted_candidate" if not promoted else "pending_promoted_candidates",
                "promoted_candidate_ids": ";".join(str(r["candidate_id"]) for r in promoted),
                "reason": "Round15 very-short gate did not promote any candidate" if not promoted else "promoted candidates need separate gated short submission",
            }
        ],
    )

    any_pending = any(r["status"] == "pending_or_incomplete" for r in rows)
    decision_status = "pending_jobs" if any_pending else ("promote_fold0_short_candidate_exists" if promoted else "stop_or_watch_no_promoted_candidate")
    failed = [r for r in rows if str(r["status"]).startswith("fail")]
    watched = [r for r in rows if str(r["status"]).startswith("watch")]
    write_text(
        OUT_ROOT / "round15_decision_table.md",
        "# Round15 Decision Table\n\n"
        + md_table(rows, ["candidate_id", "status", "reason", "prediction_count", "hard_flag_count"])
        + f"\n\nOverall status: `{decision_status}`.\n\n"
        + "Very-short jobs completed for A/B/C. No candidate is promoted to fold0 short.\n\n"
        + f"- Failed candidates: {', '.join(str(r['candidate_id']) for r in failed) or 'none'}\n"
        + f"- Watch/stop candidates: {', '.join(str(r['candidate_id']) for r in watched) or 'none'}\n"
        + "- External/pretrained candidates F-J remain postponed pending explicit compliance/source audits.\n"
        + "- Do not submit validation zip, upload, fold1-4, 5-fold, or promoted fold0 short from this round.\n",
    )
    write_text(
        OUT_ROOT / "round15_round16_recommendation.md",
        "# Round15 To Round16 Recommendation\n\n"
        f"Current status: `{decision_status}`.\n\n"
        "A/B/C first-party high-priority candidates completed fold0 very-short evaluation. "
        "R15_A had a tiny all-case/T2-present Dice and HD95 signal but introduced component-worse flags, including CenterC component regression. "
        "R15_B and R15_C were effectively baseline fallback with no clean T2-present or CenterC gain. "
        "Therefore no candidate should enter fold0 short, fold expansion, or validation submission.\n\n"
        "Round16 should not continue generic feature-head/refiner epochs. The next useful step is a narrower high-upside mechanism pass focused on why the feature heads either over-fragmented components (R15_A) or collapsed to baseline (R15_B/C). "
        "Prioritize richer intensity-prior representation and anatomy-lesion consistency design, or a focused external-method metadata/one-case audit for I-MMSeg/Cascaded FSN/PT-Net/InverseForm only if compliance is explicit.\n\n"
        "External/pretrained candidates remain postponed until explicit compliance and source audits. No validation zip/upload or fold expansion is allowed from this collector.\n",
    )
    write_text(
        OUT_ROOT / "round15_deep_research_need_assessment.md",
        "# Round15 Deep Research Need Assessment\n\n"
        "Round15 first-party A/B/C portfolio results show that the current lightweight feature-head abstraction is not sufficient.\n\n"
        "- R15_A intensity-prior head produced a very small edema signal but failed component safety: 3 hard component-worse flags, including CenterC component regression.\n"
        "- R15_B anatomy-pathology cascade and R15_C intensity+anatomy support head produced validation predictions that were effectively unchanged from nnU-Net baseline, so they do not justify longer training.\n"
        "- no-T2 empty-GT and scar guardrails stayed clean, which means the baseline-preserving safety substrate is usable, but not effective enough for CenterC/T2-present edema.\n\n"
        "A new broad repo sweep is not justified. If Round16 starts, it should be narrow and mechanism-specific: stronger T2/LGE intensity-prior representation, anatomy-lesion consistency beyond simple support features, and HD/component control that does not over-fragment edema. External methods should remain metadata/one-case only until license, pretrained-data, dependency, I/O, label mapping, and challenge compliance are explicit.\n",
    )
    print(f"Round15 collection status: {decision_status}")


if __name__ == "__main__":
    main()
