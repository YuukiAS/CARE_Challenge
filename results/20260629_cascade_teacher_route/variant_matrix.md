# Cascade Teacher Variant Matrix

Task: `prompts/tasks/20260629_cascade_teacher_route.md`

## Teacher Cache

- Primary cache: `results/20260629_cascade_teacher_route/teacher_cache/case_index.csv`
- Teacher mode: `oof5`
- Fold0 train rows: nnU-Net validation exports from each case's held-out fold among folds 1-4.
- Fold0 validation rows: nnU-Net fold0 validation exports.
- Coverage: `176/176` train, `44/44` validation.
- Required crop rule: probability/anatomy-support driven ROI with margin and full-volume restore; no hard teacher-mask-only cropping.

## Formal Variants

| variant | teacher input | refiner target | purpose | current state |
| --- | --- | --- | --- | --- |
| `nnunet_anatomy_prior_refiner` | OOF teacher anatomy probabilities/classes 1-3 plus raw LGE/T2/C0 and availability | conservative edema residual with scar guardrail | Test whether strong anatomy prior immediately reduces edema HD95/remote FP without harming scar | array entrypoint ready; CPU pathology contract passed |
| `nnunet_pathology_teacher_srr_refiner` | OOF teacher pathology probabilities/classes 4-5 plus SRR-style evidence/proposal channels | conservative scar+edema teacher residual correction | Test whether SRR-style residual learning adds pathology value beyond nnU-Net teacher | array entrypoint ready; CPU pathology contract passed |
| `coarse_to_fine_srr_roi` | OOF teacher anatomy/pathology soft ROI, not hard crop | ROI-prioritized conservative scar+edema residual with full restore | Test Result5-style cascade with reliable coarse prior | array entrypoint ready; CPU pathology contract passed |

Submission command after explicit shared-GPU approval:

```bash
sbatch --array=0-2 jobs/src/run_cascade_oof_refiner.sh
```

Array mapping:

- `0`: `nnunet_anatomy_prior_refiner`
- `1`: `nnunet_pathology_teacher_srr_refiner`
- `2`: `coarse_to_fine_srr_roi`

Implementation note: array entry `0` is intentionally edema-only and keeps scar unchanged as an anatomy-prior safety baseline. Array entries `1` and `2` use `ConservativePathologyResidualRefiner` with separate edema/scar residual logits and conservative scar thresholds, so they can test whether teacher/pathology and soft-ROI variants improve scar as well as edema.

## Baseline To Beat

- Teacher cache pathology baseline: `results/20260629_cascade_teacher_route/metrics_summary.md`.
- nnU-Net fold0 reference: edema Dice `0.7798`, scar Dice `0.5602` from `results/metrics/unified/nnUNet501/fold_0/evaluation_summary.json`.
- A cascade variant must report teacher-student deltas; copying the teacher is not sufficient.
