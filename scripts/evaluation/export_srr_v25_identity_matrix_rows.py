#!/usr/bin/env python3
"""Export nnU-Net identity rows for the SRR-v2.5 bounded matrix."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import SimpleITK as sitk

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.training.run_srr_myops_fold0 import (  # noqa: E402
    collect_case_metrics,
    read_case,
    summarize_subgroups,
    write_csv,
    write_prediction,
)
from src.care_myocardium.data.case_metadata import load_myops_case_metadata  # noqa: E402


DEFAULT_NNUNET_ROOT = (
    REPO_ROOT
    / "data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/"
    "nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres"
)


def parse_case_ids(text: str) -> list[str]:
    return [item.strip() for item in str(text).replace(";", ",").split(",") if item.strip()]


def read_pred(path: Path) -> np.ndarray:
    if not path.is_file():
        raise FileNotFoundError(path)
    return sitk.GetArrayFromImage(sitk.ReadImage(str(path))).astype(np.uint8, copy=False)


def summarize_context_subgroups(case_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for context_variant in sorted({str(row["variant"]) for row in case_rows}):
        subset = [row for row in case_rows if row["variant"] == context_variant]
        rows.extend(summarize_subgroups(context_variant, subset))
    return rows


def export_identity_variant(
    *,
    variant_dir: Path,
    variant: str,
    model_variant: str,
    case_ids: list[str],
    fold: int,
    nnunet_root: Path,
) -> None:
    metadata = load_myops_case_metadata()
    case_rows: list[dict[str, object]] = []
    prediction_dirs: list[str] = []
    for checkpoint_name in ("checkpoint_best", "checkpoint_final"):
        checkpoint_rows: list[dict[str, object]] = []
        for case_id in case_ids:
            case = read_case(case_id, metadata)  # type: ignore[arg-type]
            pred_path = nnunet_root / f"fold_{fold}" / "validation" / f"{case_id}.nii.gz"
            pred = read_pred(pred_path)
            for decode_mode in ("argmax", "pathology_aware"):
                out_dir = variant_dir / "predictions" / f"fold_{fold}" / checkpoint_name / decode_mode
                write_prediction(out_dir / f"{case_id}.nii.gz", pred, case.label_img)
                prediction_dirs.append(str(out_dir))
                context_variant = f"{variant}__{checkpoint_name}__{decode_mode}"
                rows = collect_case_metrics(context_variant, case, pred)
                checkpoint_rows.extend(rows)
                if checkpoint_name == "checkpoint_final":
                    case_rows.extend(rows)
        write_csv(variant_dir / f"component_hd_by_case_{checkpoint_name}.csv", checkpoint_rows)
        write_csv(variant_dir / f"subgroup_metrics_{checkpoint_name}.csv", summarize_context_subgroups(checkpoint_rows))
        write_csv(variant_dir / f"prediction_sanity_{checkpoint_name}.csv", [])
    write_csv(
        variant_dir / "training_log.csv",
        [
            {
                "variant": variant,
                "model_variant": model_variant,
                "step": 0,
                "stage": "identity_export_only",
                "loss": "",
                "baseline_gate_status": "closed_gate_identity_exact_nnunet_export",
                "batch_cases": ",".join(case_ids),
            }
        ],
    )
    write_csv(variant_dir / "validation_events.csv", [])
    write_csv(variant_dir / "retrieval_usage.csv", [])
    write_csv(variant_dir / "prototype_update_sanity_formal.csv", [])
    write_csv(variant_dir / "hardneg_memory.csv", [])
    summary = {
        "variant": variant,
        "model_variant": model_variant,
        "fold": fold,
        "device": "not_applicable_identity_export",
        "actual_optimizer_steps": 0,
        "optimizer_steps": 0,
        "stop_reason": "identity_export_only",
        "eval_cases": len(case_ids),
        "eval_case_ids": case_ids,
        "eval_case_selection": "explicit_eval_case_ids",
        "prediction_dirs": sorted(set(prediction_dirs)),
        "nnunet_anchor_root": str(nnunet_root),
        "identity_source": "same-split nnU-Net fold validation hard predictions",
        "identity_contract": "argmax and pathology_aware predictions are exact copies of the nnU-Net anchor prediction",
        "closed_gate_identity_fallback": model_variant == "closed_gate_identity_fallback",
        "case_metric_rows": len(case_rows),
    }
    (variant_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--matrix-root", type=Path, required=True)
    ap.add_argument("--case-ids", required=True)
    ap.add_argument("--fold", type=int, default=0)
    ap.add_argument("--nnunet-anchor-root", type=Path, default=DEFAULT_NNUNET_ROOT)
    args = ap.parse_args()

    nnunet_root = args.nnunet_anchor_root
    if not nnunet_root.is_absolute():
        nnunet_root = REPO_ROOT / nnunet_root
    case_ids = parse_case_ids(args.case_ids)
    if not case_ids:
        raise ValueError("--case-ids must include at least one case id")
    variants = [
        ("nnunet_context_identity", "nnunet_context_only_no_srr_correction"),
        ("closed_gate_identity_fallback", "closed_gate_identity_fallback"),
    ]
    for variant, model_variant in variants:
        variant_dir = args.matrix_root / "variants" / variant
        if variant_dir.exists():
            shutil.rmtree(variant_dir)
        variant_dir.mkdir(parents=True, exist_ok=True)
        export_identity_variant(
            variant_dir=variant_dir,
            variant=variant,
            model_variant=model_variant,
            case_ids=case_ids,
            fold=args.fold,
            nnunet_root=nnunet_root,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
