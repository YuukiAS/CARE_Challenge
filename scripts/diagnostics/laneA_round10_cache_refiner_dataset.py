#!/usr/bin/env python3
"""Build Lane A Round10 refiner cache manifest and sanity report."""

from __future__ import annotations

import os
import sys
from collections import Counter
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault("CARE_ROOT", str(REPO_ROOT))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.care_myocardium.refiner.laneA_round10_dataset import build_cases, summarize_geometry, write_csv


OUT_ROOT = REPO_ROOT / "results/diagnostics/phase0_phase1/laneA_myops/round10_edema_refiner"


def main() -> None:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    cases = build_cases()
    rows = summarize_geometry(cases)
    write_csv(OUT_ROOT / "round10_cache_manifest.csv", rows)

    missing_pred = [r["case_id"] for r in rows if not r["prediction_available"]]
    missing_prob = [r["case_id"] for r in rows if not r["probability_available"]]
    missing_gt = [r["case_id"] for r in rows if not r["gt_available"]]
    split_counts = Counter(str(r["split"]) for r in rows)
    source_counts = Counter(str(r["baseline_source_fold"]) for r in rows)
    modality_counts = Counter(str(r["modality_group"]) for r in rows)
    center_counts = Counter(str(r["center"]) for r in rows)
    train_missing = [r["case_id"] for r in rows if r["split"] == "train" and not r["probability_available"]]
    val_missing = [r["case_id"] for r in rows if r["split"] == "val" and not r["probability_available"]]
    gate = "pass_cache_gate" if not missing_pred and not missing_prob and not missing_gt else "fail_cache_gate"

    readme = OUT_ROOT / "round10_goal_execution_readme.md"
    readme.write_text(
        "\n".join(
            [
                "# Lane A Round10 Goal Execution Readme",
                "",
                "- Scope: edema-only residual refiner / baseline-preserving correction.",
                "- No validation zip was created. No upload was performed. No fold1-4 refiner training was executed by this cache step.",
                "- Baseline source: existing nnU-Net501 five-fold validation predictions/probabilities.",
                "- Fold0 train rows use out-of-fold baseline predictions from folds 1-4; fold0 val rows use fold0 validation predictions.",
                "- Compact labels remain unchanged: edema=4, scar=5.",
                "",
                "Outputs:",
                "- `round10_cache_manifest.csv`",
                "- `round10_cache_sanity.md`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    lines = [
        "# Lane A Round10 Cache Sanity",
        "",
        f"Gate: `{gate}`",
        "",
        "## Coverage",
        "",
        f"- total cases: {len(rows)}",
        f"- split counts: {dict(split_counts)}",
        f"- baseline source fold counts: {dict(source_counts)}",
        f"- missing hard predictions: {len(missing_pred)}",
        f"- missing probabilities: {len(missing_prob)}",
        f"- missing GT: {len(missing_gt)}",
        f"- train rows missing probabilities: {len(train_missing)}",
        f"- val rows missing probabilities: {len(val_missing)}",
        "",
        "## Metadata",
        "",
        f"- modality counts: {dict(modality_counts)}",
        f"- center counts: {dict(center_counts)}",
        "- feature channel order: `baseline_prob_0..5,C0,LGE,T2,C0_present,LGE_present,T2_present,baseline_anatomy_support`",
        "- target: `gt_class_4_edema_binary`",
        "- probability source: `.npz` probabilities from existing nnU-Net501 validation exports.",
        "",
        "## Safety Notes",
        "",
        "- This step does not write into `data/nnUNet/nnUNet_results` or `data/nnUNet/nnUNet_preprocessed`.",
        "- Fold0 train labels are paired with out-of-fold baseline predictions, avoiding fold0 validation label leakage.",
        "- The refiner remains a separate module and must prove class_5 scar unchanged at fusion/export.",
    ]
    if missing_pred or missing_prob or missing_gt:
        lines.extend(
            [
                "",
                "## Missing Cases",
                "",
                f"- missing hard predictions: {missing_pred[:20]}",
                f"- missing probabilities: {missing_prob[:20]}",
                f"- missing GT: {missing_gt[:20]}",
            ]
        )
    (OUT_ROOT / "round10_cache_sanity.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {OUT_ROOT / 'round10_cache_manifest.csv'}")
    print(f"Gate: {gate}")


if __name__ == "__main__":
    main()
