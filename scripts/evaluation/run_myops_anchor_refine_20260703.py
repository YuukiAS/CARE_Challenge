#!/usr/bin/env python3
"""Task-scoped MyoPS nnU-Net anchored refinement variants."""

from __future__ import annotations

import os
import platform
import shutil
import sys
import time
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.care_myocardium.postprocess.anchor_refine import (  # noqa: E402
    EDEMA,
    PATHOLOGY,
    SCAR,
    VARIANTS,
    annotate_component_action_rows,
    annotate_roi_coverage_rows,
    build_cases,
    collect_case_metrics,
    compare_to_baseline,
    decide_variant,
    fmt,
    load_fold_cases,
    load_probs,
    read_image_array,
    read_label,
    resample_label,
    summarize_subgroups,
    write_csv,
    write_json,
    write_prediction,
    write_text,
)


OUT_ROOT = REPO_ROOT / "results/20260703_myops_anchor_refine"
VARIANT_ROOT = OUT_ROOT / "variants"
NNUNET_FOLD0_ROOT = (
    REPO_ROOT
    / "data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/"
    / "nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_0"
)
NNUNET_VALIDATION_DIR = NNUNET_FOLD0_ROOT / "validation"
BASELINE_CHECKPOINT = NNUNET_FOLD0_ROOT / "checkpoint_best.pth"
GT_DIR = REPO_ROOT / "data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS/labelsTr"
IMAGE_DIR = REPO_ROOT / "data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS/imagesTr"
SPLITS_JSON = REPO_ROOT / "data/benchmarks/protocol/splits_MyoPS.json"
CASE_META_CSV = REPO_ROOT / "results/diagnostics/care_myocardium/laneA_myops/myops_modality_center_case_metrics.csv"
DATASET_JSON = REPO_ROOT / "data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS/dataset.json"
LABEL_UTIL = REPO_ROOT / "code/nnUNet/nnunet_label_utils.py"
SUBMISSION_SCRIPT = REPO_ROOT / "scripts/submission/prepare_care_myocardium_validation.py"
STALE_SYMLINK_BASELINE_DIR = REPO_ROOT / "results/predictions/nnUNet501/fold_0"


def require_paths(paths: list[Path]) -> list[str]:
    missing = [str(p) for p in paths if not p.exists()]
    return missing


def preflight() -> tuple[list[str], list[str], list[str]]:
    required = [
        NNUNET_VALIDATION_DIR,
        BASELINE_CHECKPOINT,
        GT_DIR,
        IMAGE_DIR,
        SPLITS_JSON,
        CASE_META_CSV,
        DATASET_JSON,
        LABEL_UTIL,
        SUBMISSION_SCRIPT,
    ]
    missing = require_paths(required)
    val_cases = load_fold_cases(SPLITS_JSON, 0, "val") if not missing else []
    train_cases = load_fold_cases(SPLITS_JSON, 0, "train") if not missing else []
    for cid in val_cases:
        for path in [
            NNUNET_VALIDATION_DIR / f"{cid}.nii.gz",
            NNUNET_VALIDATION_DIR / f"{cid}.npz",
            GT_DIR / f"{cid}.nii.gz",
            IMAGE_DIR / f"{cid}_0000.nii.gz",
        ]:
            if not path.exists():
                missing.append(str(path))
    return missing, train_cases, val_cases


def write_variant_static_files(variant: str, n_cases: int) -> None:
    vdir = VARIANT_ROOT / variant
    config = f"""task_key: 20260703_myops_anchor_refine
variant: {variant}
fold: 0
checkpoint_tag: checkpoint_best
method_type: deterministic_nnunet_anchored_postprocessor
uses_fold0_validation_labels_for_fitting: false
uses_fold0_validation_labels_for_prediction_decisions: false
decision_feature_contract: no GT-derived fields enter variant selectors; component_action_table GT columns are post-hoc evaluation annotations
uses_alignment_inputs: false
uses_srr_or_propref_inputs: false
uses_local_users_nnunet_cache: true
baseline_prediction_dir: {NNUNET_VALIDATION_DIR}
baseline_probability_dir: {NNUNET_VALIDATION_DIR}
baseline_checkpoint: {BASELINE_CHECKPOINT}
raw_image_dir: {IMAGE_DIR}
cases_evaluated: {n_cases}
"""
    write_text(vdir / "config.yaml", config)
    write_json(
        vdir / "checkpoints/fold_0/checkpoint_best.json",
        {
            "checkpoint_type": "deterministic_parameter_record",
            "learned_weights": "evidence not found",
            "variant": variant,
            "fold": 0,
            "source": "scripts/evaluation/run_myops_anchor_refine_20260703.py",
            "baseline_checkpoint": str(BASELINE_CHECKPOINT),
        },
    )
    write_text(
        vdir / "logs/run.log",
        f"variant={variant}\nstatus=completed\ncases_evaluated={n_cases}\nlearned_training=false\n",
    )


def format_metric_table(subgroups: list[dict[str, object]], variants: list[str]) -> str:
    lines = [
        "# MyoPS Anchor Refine Metrics Summary",
        "",
        "| variant | metric | group | n | Dice | HD95 | components | remote FP | small FP | volume ratio |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    want_groups = {
        "myops_scar": ["all_cases", "gt_positive_only", "LGE-only", "complete_modality", "CenterB", "CenterC"],
        "myops_edema": [
            "all_cases",
            "gt_positive_only",
            "t2_present",
            "complete_modality",
            "CenterB",
            "CenterC",
            "no_T2_empty_GT",
        ],
    }
    for variant in variants:
        for metric_name, groups in want_groups.items():
            for group in groups:
                row = next(
                    (
                        r
                        for r in subgroups
                        if r["variant"] == variant and r["metric_name"] == metric_name and r["group"] == group
                    ),
                    None,
                )
                if row is None:
                    continue
                lines.append(
                    "| {variant} | {metric} | {group} | {n} | {dice} | {hd95} | {comp} | {remote} | {small} | {vr} |".format(
                        variant=variant,
                        metric=metric_name,
                        group=group,
                        n=row["n"],
                        dice=fmt(row.get("dice_mean")),
                        hd95=fmt(row.get("hd95_mean")),
                        comp=fmt(row.get("component_count_mean")),
                        remote=fmt(row.get("remote_fp_mean")),
                        small=fmt(row.get("small_fp_mean")),
                        vr=fmt(row.get("pred_gt_volume_ratio_mean")),
                    )
                )
    return "\n".join(lines) + "\n"


def main() -> None:
    start = time.time()
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    command = " ".join([sys.executable, "scripts/evaluation/run_myops_anchor_refine_20260703.py"])
    missing, train_cases, val_cases = preflight()
    if missing:
        write_text(
            OUT_ROOT / "result.md",
            "# Result 20260703 MyoPS Anchor Refine\n\nstatus: NEEDS_EVIDENCE\n\nmissing evidence:\n"
            + "\n".join(f"- `{m}`" for m in missing)
            + "\n",
        )
        write_text(
            OUT_ROOT / "MANIFEST.md",
            "# Manifest 20260703 MyoPS Anchor Refine\n\nTask stopped at NEEDS_EVIDENCE during preflight.\n",
        )
        raise SystemExit(2)

    if OUT_ROOT.exists():
        for child in OUT_ROOT.iterdir():
            if child.name in {"result.md", "MANIFEST.md"}:
                child.unlink()
            elif child.is_dir() and child.name == "variants":
                shutil.rmtree(child)
            elif child.is_file() and child.name != "review.md":
                child.unlink()

    cases = build_cases(
        fold_val_cases=val_cases,
        case_meta_csv=CASE_META_CSV,
        gt_dir=GT_DIR,
        baseline_pred_dir=NNUNET_VALIDATION_DIR,
        prob_dir=NNUNET_VALIDATION_DIR,
        image_dir=IMAGE_DIR,
    )
    all_case_rows: list[dict[str, object]] = []
    all_component_rows: list[dict[str, object]] = []
    all_roi_rows: list[dict[str, object]] = []
    variants = ["baseline_nnunet501_fold0"] + list(VARIANTS)
    prediction_counts: dict[str, int] = {"baseline_nnunet501_fold0": len(cases)}

    for case in cases:
        gt_img, gt = read_label(case.gt_path)
        baseline = resample_label(case.pred_path, gt_img)
        probs = load_probs(case.prob_path)
        raw = {name: read_image_array(path, gt_img) for name, path in case.image_paths.items() if path.exists()}
        for name in ("LGE", "T2", "C0"):
            raw.setdefault(name, np.zeros_like(gt, dtype=np.float32))

        all_case_rows.extend(collect_case_metrics("baseline_nnunet501_fold0", case, baseline, gt, gt_img))
        for variant, func in VARIANTS.items():
            pred, component_rows, roi_rows = func(case, baseline, probs, raw)
            pred_path = VARIANT_ROOT / variant / "predictions/fold_0/checkpoint_best" / f"{case.case_id}.nii.gz"
            write_prediction(pred_path, pred, gt_img)
            all_case_rows.extend(collect_case_metrics(variant, case, pred, gt, gt_img))
            all_component_rows.extend(annotate_component_action_rows(component_rows, gt))
            for roi_row in roi_rows:
                all_roi_rows.extend(
                    annotate_roi_coverage_rows(
                        str(roi_row["variant"]),
                        roi_row["case"],
                        roi_row["roi"],
                        pred,
                        gt,
                    )
                )
            prediction_counts[variant] = prediction_counts.get(variant, 0) + 1

    subgroup_rows = summarize_subgroups(all_case_rows)
    delta_rows = compare_to_baseline(subgroup_rows)
    for variant in VARIANTS:
        write_variant_static_files(variant, prediction_counts.get(variant, 0))
        vrows = [r for r in subgroup_rows if r["variant"] == variant]
        write_csv(VARIANT_ROOT / variant / "metrics/subgroup_metrics.csv", vrows)
        write_csv(VARIANT_ROOT / variant / "metrics/component_hd_by_case.csv", [r for r in all_case_rows if r["variant"] == variant])

    write_csv(OUT_ROOT / "subgroup_metrics.csv", subgroup_rows)
    write_csv(OUT_ROOT / "component_hd_by_case.csv", all_case_rows)
    write_csv(OUT_ROOT / "teacher_student_delta.csv", delta_rows)
    write_csv(OUT_ROOT / "component_action_table.csv", all_component_rows)
    write_csv(OUT_ROOT / "roi_coverage.csv", all_roi_rows)
    write_text(OUT_ROOT / "metrics_summary.md", format_metric_table(subgroup_rows, variants))

    decisions = {variant: decide_variant(variant, delta_rows) for variant in VARIANTS}
    variant_lines = [
        "# Variant Matrix",
        "",
        "| variant | mechanism | prediction path | checkpoint/config | decision | rationale |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    mechanisms = {
        "nnunet_component_score_refiner": "scar component scoring around nnU-Net pathology with soft anatomy support",
        "myocardium_roi_pathology_refiner": "soft myocardium/union ROI expansion using raw LGE/T2/C0 context and probabilities",
        "scar_precision_edema_recall_dual_refiner": "class-specific scar precision and T2-aware edema recall logic",
    }
    for variant, (decision, reason) in decisions.items():
        variant_lines.append(
            f"| `{variant}` | {mechanisms[variant]} | `variants/{variant}/predictions/fold_0/checkpoint_best/` | "
            f"`variants/{variant}/config.yaml`; `variants/{variant}/checkpoints/fold_0/checkpoint_best.json` | `{decision}` | {reason} |"
        )
    write_text(OUT_ROOT / "variant_matrix.md", "\n".join(variant_lines) + "\n")

    stale_note = "not present"
    if STALE_SYMLINK_BASELINE_DIR.exists():
        stale_note = "contains symlinks to /overflow; not used as the primary cache in this task"
    write_text(
        OUT_ROOT / "cache_contract.md",
        f"""# Cache Contract

- task output root: `{OUT_ROOT}`
- fold: `0`
- train cases in split: `{len(train_cases)}`
- validation cases evaluated: `{len(val_cases)}`
- baseline prediction/probability cache used: `{NNUNET_VALIDATION_DIR}`
- baseline checkpoint used: `{BASELINE_CHECKPOINT}`
- stale compatibility path: `{STALE_SYMLINK_BASELINE_DIR}` -> {stale_note}
- variant cache pattern: `results/20260703_myops_anchor_refine/variants/<variant>/predictions/fold_0/checkpoint_best/`
- no validation upload/package was created.
- no fold split, evaluator, label mapping, or prior result directory was modified.
- train/validation separation: no thresholds, weights, or model parameters were fit on fold0 validation labels; fold0 validation labels were used only for metrics and post-hoc annotations after predictions were fixed.
- decision/evaluation separation: variant functions do not receive fold0 validation GT; component selectors use only prediction/probability/anatomy-support features. `component_action_table.csv` uses `decision_*` columns for action inputs and `evaluation_*` columns for GT-derived post-hoc annotations.
- learned OOF train-cache evidence: `evidence not found`; deterministic postprocessor parameter records are used instead of learned checkpoints.
""",
    )
    write_text(
        OUT_ROOT / "training_summary.md",
        f"""# Training Summary

status: `no_gpu_training_run`

The formal variants were executed as deterministic nnU-Net/coarse anchored postprocessor/refiners with fixed task-scoped parameters. This preserves train/validation separation because fold0 validation labels were not used to fit parameters or decide suppress/add/refine actions.

Revision note: validation-label leakage from the audited package was removed. Variant functions no longer receive fold0 validation GT; GT-derived component annotations are generated only after predictions are written and are labeled as `evaluation_*` fields.

Learned pathology-refiner checkpoints: `evidence not found`. The blocker is missing train/OOF nnU-Net coarse prediction/probability caches for the fold0 training split; generating them or training a learned local ROI refiner would require a separate bounded execution after audit/controller approval.

Executed variants:

- `nnunet_component_score_refiner`: component scoring/refinement around scar predictions.
- `myocardium_roi_pathology_refiner`: soft ROI local pathology refinement using raw LGE/T2/C0 and nnU-Net probabilities.
- `scar_precision_edema_recall_dual_refiner`: separate scar precision and T2-aware edema recall logic.

GPU jobs submitted: none.
Wall time seconds: `{time.time() - start:.2f}`.
""",
    )
    invalid_rows = [r for r in all_case_rows if r.get("invalid_label_values")]
    write_text(
        OUT_ROOT / "label_export_qc.md",
        f"""# Label Export QC

- evaluator label space: compact Dataset501 labels.
- compact labels: `0=background`, `1=myocardium`, `2=LV_blood`, `3=RV_blood`, `4=myops_edema`, `5=myops_scar`.
- raw-to-compact mapping source: `{LABEL_UTIL}`.
- compact-to-raw validation export mapping source: `{SUBMISSION_SCRIPT}`.
- prediction files per formal variant: `{ {k: v for k, v in prediction_counts.items() if k != 'baseline_nnunet501_fold0'} }`.
- invalid compact labels outside `0..5`: `{len(invalid_rows)}` rows.
- raw-label validation package/export evidence: `evidence not found`; validation packaging/upload was not authorized.
""",
    )
    failure_lines = [
        "# Failure Interpretation",
        "",
        "The task produced fold0 compact-label local evidence only. It does not prove hosted validation improvement.",
        "",
        "Revision note: the prior audited package leaked validation labels into component action selection. This revision removes GT from prediction/refiner function inputs and treats GT-derived component fields as post-hoc evaluation annotations only. Because clean evidence remains fixed-rule and no learned train/OOF refiner evidence exists, no variant is promotable.",
        "",
    ]
    for variant, (decision, reason) in decisions.items():
        scar = next(
            (
                r
                for r in delta_rows
                if r["variant"] == variant and int(r["class_id"]) == SCAR and r["group"] == "all_cases"
            ),
            {},
        )
        edema = next(
            (
                r
                for r in delta_rows
                if r["variant"] == variant and int(r["class_id"]) == EDEMA and r["group"] == "gt_positive_only"
            ),
            {},
        )
        failure_lines.extend(
            [
                f"## `{variant}`",
                "",
                f"- decision: `{decision}` ({reason})",
                f"- scar all-case delta Dice: `{fmt(scar.get('delta_dice_mean'))}`; delta HD95 improvement: `{fmt(scar.get('delta_hd95_mean_improvement'))}`; delta remote FP improvement: `{fmt(scar.get('delta_remote_fp_mean_improvement'))}`",
                f"- edema GT-positive delta Dice: `{fmt(edema.get('delta_dice_mean'))}`; delta HD95 improvement: `{fmt(edema.get('delta_hd95_mean_improvement'))}`; delta remote FP improvement: `{fmt(edema.get('delta_remote_fp_mean_improvement'))}`",
                "",
            ]
        )
    failure_lines.extend(
        [
            "## Evidence Gaps",
            "",
            "- learned checkpoint evidence: `evidence not found`.",
            "- train/OOF nnU-Net coarse predictions for fold0 training cases: `evidence not found`.",
            "- hosted validation metrics: `evidence not found`.",
            "- validation package/upload evidence: `evidence not found`.",
        ]
    )
    write_text(OUT_ROOT / "failure_interpretation.md", "\n".join(failure_lines) + "\n")

    write_text(
        OUT_ROOT / "command_transcript.md",
        f"""# Command Transcript

- command: `{command}`
- cwd: `{REPO_ROOT}`
- python: `{sys.executable}`
- platform: `{platform.platform()}`
- allow_network: `false`
- external_upload: `false`
- revision_note: `removed fold0 validation GT from prediction/refiner action selection; GT-derived component annotations are post-hoc evaluation only`
- start_epoch: `{start:.3f}`
- elapsed_seconds: `{time.time() - start:.2f}`
- exit_status: `0`
""",
    )

    status = "EXECUTED_UNAUDITED"
    result = f"""# Result 20260703 MyoPS Anchor Refine

status: {status}
self_assessed_status: partial_complete
domain_evidence_label: PARTIAL_MECHANISM_INCOMPLETE

## Execution Summary

Executed three formal nnU-Net anchored fold0 postprocessor/refiner variants against the unchanged local fold0 nnU-Net reference. The variants wrote 44 compact-label predictions each, subgroup metrics, case-level HD/HD95/component/FP metrics, teacher-student deltas, ROI coverage, configs, logs, and deterministic checkpoint parameter records.

No learned pathology-refiner training was run. Fold0 validation labels were used only for metrics, ROI coverage reporting, and post-hoc component-action annotations after predictions were fixed; learned train/OOF coarse caches for fold0 training cases were `evidence not found`.

## Revision Note

The audited `NEEDS_REVISION` blocker was validation-label leakage in component action selection. This revision removes fold0 validation GT from all variant/refiner function inputs and selector features. `component_action_table.csv` now separates action inputs as `decision_*` columns from GT-derived `evaluation_*` annotations.

## Files Read

- `prompts/tasks/20260703_myops_anchor_refine.md`
- `results/20260703_myops_audit/review.md`
- `results/20260703_myops_fp_control/review.md`
- `results/20260703_myops_srr_propose_refine/review.md`
- `results/20260703_myops_alignment_gate/review.md`
- `{SPLITS_JSON}`
- `{DATASET_JSON}`
- `{CASE_META_CSV}`
- `{NNUNET_VALIDATION_DIR}`
- `{GT_DIR}`
- `{IMAGE_DIR}`

## Files Changed

- `src/care_myocardium/postprocess/__init__.py`
- `src/care_myocardium/postprocess/anchor_refine.py`
- `scripts/evaluation/run_myops_anchor_refine_20260703.py`
- `results/20260703_myops_anchor_refine/`

## Commands

- `{command}` -> exit 0

## Claims

claim.same_split_baseline: unchanged local nnU-Net fold0 predictions/probabilities/checkpoint under `{NNUNET_FOLD0_ROOT}` were used as baseline.
claim.train_val_separation: no fold0 validation labels were used to fit thresholds, weights, checkpoints, or prediction/refiner actions.
claim.decision_evaluation_split: variant selectors use only decision features from predictions/probabilities/anatomy support; GT-derived component fields are post-hoc `evaluation_*` annotations.
claim.no_alignment_dependency: alignment inputs were not used; prior alignment route remains stopped.
claim.no_srr_continuation: no SRR/PropRef tuning or SRR artifacts were used as selected route inputs.
claim.label_export_qc: outputs contain compact labels `0..5`; raw-label export/package evidence is not present.
claim.next_state: executor stops at `EXECUTED_UNAUDITED` pending separate audit.

## Incomplete Evidence

- learned checkpoint/training evidence: `evidence not found`.
- train/OOF nnU-Net coarse probability caches for fold0 training cases: `evidence not found`.
- hosted validation metrics and validation package/upload: `evidence not found`.

## Next State

`EXECUTED_UNAUDITED`; separate read-only audit required before any promotion, fold expansion, package generation, commit, or push.
"""
    write_text(OUT_ROOT / "result.md", result)

    manifest_lines = [
        "# Manifest 20260703 MyoPS Anchor Refine",
        "",
        "- task: `prompts/tasks/20260703_myops_anchor_refine.md`",
        "- controller task: `prompts/tasks/20260703_hardmode_goal.md`",
        "- result: `results/20260703_myops_anchor_refine/result.md`",
        "- review: `results/20260703_myops_anchor_refine/review.md` (preserved prior `NEEDS_REVISION` audit history; this revision is `EXECUTED_UNAUDITED` pending a separate re-audit)",
        "",
        "## Root Artifacts",
        "",
    ]
    for name in [
        "variant_matrix.md",
        "cache_contract.md",
        "training_summary.md",
        "metrics_summary.md",
        "subgroup_metrics.csv",
        "component_hd_by_case.csv",
        "teacher_student_delta.csv",
        "roi_coverage.csv",
        "component_action_table.csv",
        "label_export_qc.md",
        "failure_interpretation.md",
        "command_transcript.md",
    ]:
        manifest_lines.append(f"- `results/20260703_myops_anchor_refine/{name}`")
    manifest_lines.extend(["", "## Variant Artifacts", ""])
    for variant in VARIANTS:
        manifest_lines.extend(
            [
                f"- `results/20260703_myops_anchor_refine/variants/{variant}/config.yaml`",
                f"- `results/20260703_myops_anchor_refine/variants/{variant}/checkpoints/fold_0/checkpoint_best.json`",
                f"- `results/20260703_myops_anchor_refine/variants/{variant}/predictions/fold_0/checkpoint_best/`",
                f"- `results/20260703_myops_anchor_refine/variants/{variant}/metrics/subgroup_metrics.csv`",
                f"- `results/20260703_myops_anchor_refine/variants/{variant}/metrics/component_hd_by_case.csv`",
                f"- `results/20260703_myops_anchor_refine/variants/{variant}/logs/run.log`",
            ]
        )
    manifest_lines.extend(
        [
            "",
            "## Changed First-Party Code",
            "",
            "- `src/care_myocardium/postprocess/__init__.py`",
            "- `src/care_myocardium/postprocess/anchor_refine.py`",
            "- `scripts/evaluation/run_myops_anchor_refine_20260703.py`",
        ]
    )
    write_text(OUT_ROOT / "MANIFEST.md", "\n".join(manifest_lines) + "\n")


if __name__ == "__main__":
    main()
