#!/usr/bin/env python3
"""Evaluate Lane A Round9 fold0 candidate against nnU-Net501 baseline."""

from __future__ import annotations

import sys
import os
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.diagnostics import laneA_round8_fold0_eval as r8_eval


OUT_ROOT = REPO_ROOT / "results/diagnostics/care_myocardium/laneA_myops/round09_baseline_initialized_adaptation"
CANDIDATE_PRED_DIR = (
    REPO_ROOT
    / "data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/"
    / (
        os.environ.get("LANEA_ROUND9_EXPERIMENT_NAME", "laneA_r9_ckptinit_6ch_edema_adapt_fold0_very_short")
        + "__nnUNetPlans__3d_fullres/fold_0/validation"
    )
)
BASELINE_MODEL = "baseline_nnunet501_fold0"
CANDIDATE_MODEL = "candidate_laneA_round9_ckptinit_6ch"


def main() -> None:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    r8_eval.BASELINE_MODEL = BASELINE_MODEL
    r8_eval.CANDIDATE_MODEL = CANDIDATE_MODEL
    baseline_rows = r8_eval.base_eval.build_case_rows(r8_eval.BASELINE_PRED_DIR, BASELINE_MODEL)
    candidate_rows = r8_eval.base_eval.build_case_rows(CANDIDATE_PRED_DIR, CANDIDATE_MODEL)
    all_rows = baseline_rows + candidate_rows
    r8_eval.write_csv(OUT_ROOT / "round9_fold0_very_short_metrics.csv", all_rows)

    subset_rows = []
    for model in [BASELINE_MODEL, CANDIDATE_MODEL]:
        for subset in r8_eval.SUBSETS:
            subset_rows.append(r8_eval.aggregate(all_rows, subset, model))
    comparison_rows = r8_eval.compare(subset_rows)
    # Re-label compare rows from Round8 helper expectations.
    for row in comparison_rows:
        row["candidate_model"] = CANDIDATE_MODEL
    r8_eval.write_csv(OUT_ROOT / "baseline_vs_candidate_by_subset.csv", comparison_rows)
    r8_eval.write_csv(
        OUT_ROOT / "no_t2_empty_gt_fp_table.csv",
        [r for r in candidate_rows if r.get("t2_present") is False and r.get("edema_gt_positive") is False],
    )
    r8_eval.write_csv(OUT_ROOT / "centerB_centerC_edema_table.csv", [r for r in candidate_rows if r.get("center") in {"CenterB", "CenterC"}])
    r8_eval.write_csv(OUT_ROOT / "scar_guardrail_table.csv", [r for r in candidate_rows if not r.get("missing_prediction")])
    flags = r8_eval.failure_flags(all_rows)
    r8_eval.write_csv(OUT_ROOT / "case_level_failure_flags.csv", flags)

    decision, reasons = r8_eval.decide(comparison_rows, flags)
    lines = [
        "# Lane A Round9 Fold0 Very-Short Summary",
        "",
        "- Candidate: `checkpoint-initialized 6-channel edema adaptation`",
        "- Scope: fold0 only; no validation zip; no upload; no fold1-4 expansion",
        "",
        "## Baseline vs Candidate By Subset",
        "",
        *r8_eval.md_table(
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
    ]
    lines.extend([f"- {r}" for r in reasons] if reasons else ["- no failure flags"])
    (OUT_ROOT / "round9_fold0_very_short_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (OUT_ROOT / "round9_decision_table.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (OUT_ROOT / "round9_next_actions.md").write_text(
        "\n".join(
            [
                "# Lane A Round9 Next Actions",
                "",
                f"Current decision: `{decision}`",
                "",
                "- Do not create validation zip or upload from Round9 without explicit user authorization.",
                "- If this decision is pass/watch, inspect subset tables before any longer fold0 train.",
                "- If this decision is fail, stop the current candidate and preserve diagnostics.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
