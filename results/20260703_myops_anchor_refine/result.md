# Result 20260703 MyoPS Anchor Refine

status: EXECUTED_UNAUDITED
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
- `/users/a/e/aereinh/CARE/data/benchmarks/protocol/splits_MyoPS.json`
- `/users/a/e/aereinh/CARE/data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS/dataset.json`
- `/users/a/e/aereinh/CARE/results/diagnostics/care_myocardium/laneA_myops/myops_modality_center_case_metrics.csv`
- `/users/a/e/aereinh/CARE/data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_0/validation`
- `/users/a/e/aereinh/CARE/data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS/labelsTr`
- `/users/a/e/aereinh/CARE/data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS/imagesTr`

## Files Changed

- `src/care_myocardium/postprocess/__init__.py`
- `src/care_myocardium/postprocess/anchor_refine.py`
- `scripts/evaluation/run_myops_anchor_refine_20260703.py`
- `results/20260703_myops_anchor_refine/`

## Commands

- `/users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/evaluation/run_myops_anchor_refine_20260703.py` -> exit 0

## Claims

claim.same_split_baseline: unchanged local nnU-Net fold0 predictions/probabilities/checkpoint under `/users/a/e/aereinh/CARE/data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_0` were used as baseline.
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
