#!/usr/bin/env python3
"""Collect Lane A Round16 fold0 very-short results.

This is a read-only diagnostics collector. It does not train, submit Slurm,
create validation zips, upload, or expand beyond fold0.
"""

from __future__ import annotations

import csv
from pathlib import Path


CARE_ROOT = Path(__file__).resolve().parents[2]
OUT_ROOT = CARE_ROOT / "results/diagnostics/care_myocardium/laneA_myops/round16_external_mechanism_integration"

CANDIDATES = [
    "R16_A_care_strong_t2_lge_intensity_prior_fold0_vs",
    "R16_C_anatomy_pathology_cascade_care_fold0_vs",
    "R16_E_intensity_plus_component_surface_aux_fold0_vs",
    "R16_F_small_modality_conditioned_moe_fold0_vs",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        keys: list[str] = []
        for row in rows:
            for key in row:
                if key not in keys:
                    keys.append(key)
        fieldnames = keys or ["status"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def parse_float(value: object) -> float | None:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def candidate_status(candidate: str) -> dict[str, object]:
    cdir = OUT_ROOT / candidate
    summary = read_csv(cdir / "train_summary.csv")
    comparison = read_csv(cdir / "baseline_vs_candidate_by_subset.csv")
    flags = read_csv(cdir / "case_level_failure_flags.csv")
    case_metrics = read_csv(cdir / "fold0_very_short_case_metrics.csv")
    pred_dir = cdir / "validation_predictions"
    pred_count = len(list(pred_dir.glob("*.nii.gz"))) if pred_dir.exists() else 0
    if not summary:
        return {
            "candidate_id": candidate,
            "status": "pending_or_not_started",
            "reason": "train_summary.csv missing",
            "pred_count": pred_count,
        }
    if not comparison or not flags or pred_count < 44:
        return {
            "candidate_id": candidate,
            "status": "pending_or_incomplete",
            "reason": f"comparison={bool(comparison)} flags={bool(flags)} pred_count={pred_count}",
            "pred_count": pred_count,
            **summary[0],
        }
    hard_flags = [r for r in flags if r.get("flags")]
    by_subset = {r.get("subset", ""): r for r in comparison}
    t2 = by_subset.get("t2_present_gt_positive", {})
    center_c = by_subset.get("CenterC", {})
    t2_dice = parse_float(t2.get("delta_edema_dice")) or 0.0
    t2_hd95 = parse_float(t2.get("delta_edema_hd95_improvement")) or 0.0
    c_dice = parse_float(center_c.get("delta_edema_dice")) or 0.0
    c_hd95 = parse_float(center_c.get("delta_edema_hd95_improvement")) or 0.0
    if hard_flags:
        status = "fail_stop_no_longer_train"
        reason = f"{len(hard_flags)} case-level failure flags"
    elif t2_dice < -0.02 or t2_hd95 < -1.0 or c_dice < -0.02 or c_hd95 < -1.0:
        status = "fail_stop_target_subset_regression"
        reason = "T2-present/CenterC edema Dice or HD95 regressed"
    elif (t2_dice > 0.005 and t2_hd95 >= -0.1) or (t2_hd95 > 0.5 and t2_dice >= -0.001):
        status = "pass_watch_consider_fold0_short"
        reason = "clean T2-present GT-positive edema signal"
    elif (c_dice > 0.005 and c_hd95 >= -0.1) or (c_hd95 > 0.5 and c_dice >= -0.001):
        status = "pass_watch_consider_fold0_short"
        reason = "clean CenterC edema signal"
    else:
        status = "watch_stop_no_clear_positive_signal"
        reason = "no clean T2-present/CenterC signal"
    return {
        "candidate_id": candidate,
        "status": status,
        "reason": reason,
        "pred_count": pred_count,
        "n_case_metric_rows": len(case_metrics),
        "n_flagged_cases": len(hard_flags),
        "t2_present_gt_positive_delta_dice": t2_dice,
        "t2_present_gt_positive_delta_hd95_improvement": t2_hd95,
        "CenterC_delta_dice": c_dice,
        "CenterC_delta_hd95_improvement": c_hd95,
        **summary[0],
    }


def markdown_decision(rows: list[dict[str, object]]) -> str:
    lines = [
        "# Lane A Round16 Candidate Decision Table",
        "",
        "Scope: fold0 very-short only. No validation zip/upload and no fold1-4/5-fold expansion were performed.",
        "",
        "| candidate | status | reason | predictions | T2+ GT+ Dice delta | T2+ GT+ HD95 improvement | CenterC Dice delta | CenterC HD95 improvement | flagged cases |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            "| {candidate_id} | `{status}` | {reason} | {pred_count} | {t2_present_gt_positive_delta_dice} | {t2_present_gt_positive_delta_hd95_improvement} | {CenterC_delta_dice} | {CenterC_delta_hd95_improvement} | {n_flagged_cases} |".format(
                candidate_id=row.get("candidate_id", ""),
                status=row.get("status", ""),
                reason=row.get("reason", ""),
                pred_count=row.get("pred_count", ""),
                t2_present_gt_positive_delta_dice=row.get("t2_present_gt_positive_delta_dice", ""),
                t2_present_gt_positive_delta_hd95_improvement=row.get("t2_present_gt_positive_delta_hd95_improvement", ""),
                CenterC_delta_dice=row.get("CenterC_delta_dice", ""),
                CenterC_delta_hd95_improvement=row.get("CenterC_delta_hd95_improvement", ""),
                n_flagged_cases=row.get("n_flagged_cases", ""),
            )
        )
    completed = [r for r in rows if str(r.get("status", "")).startswith(("fail", "pass", "watch"))]
    pending = [r for r in rows if str(r.get("status", "")).startswith("pending")]
    if pending:
        conclusion = "Some fold0 very-short jobs are still pending or incomplete; do not promote any candidate yet."
    elif any(r.get("status") == "pass_watch_consider_fold0_short" for r in rows):
        conclusion = "At least one candidate has a gated positive signal and may be considered for fold0 short only after manual review."
    else:
        conclusion = "No candidate has a clean enough signal for automatic fold0 short promotion."
    lines.extend(["", f"Conclusion: {conclusion}", ""])
    return "\n".join(lines)


def main() -> None:
    comparison_rows: list[dict[str, object]] = []
    flag_rows: list[dict[str, object]] = []
    case_rows: list[dict[str, object]] = []
    statuses = []
    for candidate in CANDIDATES:
        cdir = OUT_ROOT / candidate
        comparison_rows.extend(read_csv(cdir / "baseline_vs_candidate_by_subset.csv"))
        flag_rows.extend(read_csv(cdir / "case_level_failure_flags.csv"))
        case_rows.extend(read_csv(cdir / "fold0_very_short_case_metrics.csv"))
        statuses.append(candidate_status(candidate))

    write_csv(OUT_ROOT / "round16_fold0_very_short_metrics.csv", comparison_rows)
    write_csv(OUT_ROOT / "round16_fold0_very_short_results.csv", case_rows)
    write_csv(OUT_ROOT / "round16_baseline_vs_candidate_by_subset.csv", comparison_rows)
    write_csv(OUT_ROOT / "round16_case_level_failure_flags.csv", flag_rows)
    write_csv(OUT_ROOT / "round16_candidate_status_summary.csv", statuses)
    write_csv(OUT_ROOT / "round16_centerC_edema_table.csv", [r for r in comparison_rows if r.get("subset") == "CenterC"])
    write_csv(OUT_ROOT / "round16_no_t2_empty_gt_fp_table.csv", [r for r in comparison_rows if r.get("subset") == "no_t2_empty_gt"])
    write_csv(OUT_ROOT / "round16_scar_guardrail_table.csv", comparison_rows)
    write_csv(OUT_ROOT / "round16_component_remote_fp_table.csv", comparison_rows)

    decision = markdown_decision(statuses)
    (OUT_ROOT / "round16_candidate_decision_table.md").write_text(decision, encoding="utf-8")
    (OUT_ROOT / "round16_decision_table.md").write_text(decision, encoding="utf-8")
    (OUT_ROOT / "round16_round17_recommendation.md").write_text(
        "# Round16 to Round17 Recommendation\n\n"
        + decision.split("Conclusion: ", 1)[-1].strip()
        + "\n",
        encoding="utf-8",
    )
    print(decision)


if __name__ == "__main__":
    main()
