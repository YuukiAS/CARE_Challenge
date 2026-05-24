# Lane A Round10 Active Edema-Only Residual Refiner Execution

Plan metadata:
- Type: active/in-progress round execution record
- Lane: Lane A, MyoPS scar/edema
- Round scope: Round10
- Status: executed fold0 very-short gate; current candidate failed stop gate
- Parent roadmap: `/overflow/htzhu/CARE/TODO.md`
- Parent plan: `docs/plans/laneA_round10_next_edema_only_residual_refiner_execution.md`
- Function: record actual Round10 execution for baseline-preserving class_4 edema residual refiner
- Do not: treat this as validation-submission authorization; do not run fold1-4; do not train whole nnU-Net; do not download weights or external repos

## Execution Summary

Round10 executed the first-party edema-only residual refiner route through:

1. cache/reproducibility gate;
2. unit/gradient smoke;
3. tiny-overfit safety screen;
4. one bounded `htzhulab` fold0 very-short refiner Slurm job;
5. fold0 validation evaluation against the existing nnU-Net501 baseline.

No validation zip was created. No upload was performed. No fold1-4 or 5-fold run was started. The nnU-Net backbone and baseline prediction directories were not overwritten.

## Implemented Files

- `src/care_myocardium/refiner/__init__.py`
- `src/care_myocardium/refiner/laneA_round10_model.py`
- `src/care_myocardium/refiner/laneA_round10_dataset.py`
- `scripts/diagnostics/laneA_round10_cache_refiner_dataset.py`
- `scripts/diagnostics/laneA_round10_refiner_smoke.py`
- `scripts/diagnostics/laneA_round10_refiner_eval.py`
- `scripts/training/run_laneA_round10_refiner_train.py`
- `jobs/nnUNet/laneA_round10_refiner_fold0_very_short.sh`

## Output Root

All Round10 outputs are isolated under:

```text
results/diagnostics/phase0_phase1/laneA_myops/round10_edema_refiner/
```

Key outputs:

- `round10_cache_manifest.csv`
- `round10_cache_sanity.md`
- `round10_refiner_config.yaml`
- `round10_unit_gradient_smoke.csv`
- `round10_tiny_overfit_metrics.csv`
- `round10_refiner_train_log.csv`
- `round10_fold0_very_short_metrics.csv`
- `baseline_vs_refiner_by_subset.csv`
- `no_t2_empty_gt_fp_table.csv`
- `centerB_centerC_edema_table.csv`
- `scar_unchanged_guardrail_table.csv`
- `residual_magnitude_summary.csv`
- `case_level_failure_flags.csv`
- `round10_decision_table.md`
- `round10_next_actions.md`

Prediction export:

```text
results/diagnostics/phase0_phase1/laneA_myops/round10_edema_refiner/predictions/laneA_r10_edema_residual_refiner_fold0_very_short/validation/
```

## Cache Gate

Decision: `pass_cache_gate`

Evidence:

- 220/220 train cases have existing baseline hard predictions and probabilities.
- Fold0 train rows use out-of-fold nnU-Net501 probabilities from folds 1-4.
- Fold0 validation rows use fold0 nnU-Net501 probabilities.
- Split coverage: 176 train, 44 validation.
- Modality coverage: 116 LGE-only, 80 C0+LGE+T2, 24 C0+LGE.
- Compact label semantics are unchanged: edema=4, scar=5.

## Smoke Gate

Decision: `pass_tiny_refiner_safety_gate`

Evidence:

- One-batch gradient smoke finite for selected CenterB, CenterC, LGE-only, and C0+LGE cases.
- Tiny-overfit safety screen completed.
- Scar changed voxels: 0.
- no-T2 new edema voxels in tiny screen: 0.
- Residual was clipped and measured; delta max touched the configured `delta_max=1.0`, but mean residual remained small and did not create no-T2 edema in the tiny screen.

## Fold0 Very-Short Job

Submitted job:

```text
sbatch jobs/nnUNet/laneA_round10_refiner_fold0_very_short.sh
```

Job id:

```text
52102044
```

Slurm result:

```text
COMPLETED, ExitCode=0:0, Elapsed=00:01:49
```

Training budget:

- refiner-only, no nnU-Net backbone update;
- 3 epochs;
- 40 patch steps per epoch;
- `delta_max=1.0`;
- threshold `0.5`;
- fold0 validation export: 44/44 cases.

## Fold0 Very-Short Result

Decision: `fail_stop_refiner_candidate`

Subset deltas from `baseline_vs_refiner_by_subset.csv`:

| subset | delta edema Dice | delta edema HD95 improvement | delta component improvement | delta remote FP improvement | scar delta |
| --- | ---: | ---: | ---: | ---: | ---: |
| all-case | +0.0025 | -0.0189 | +0.1591 | +0.0227 | 0.0000 |
| T2-present GT-positive | +0.0025 | -0.0519 | +0.4375 | +0.0625 | 0.0000 |
| CenterB | +0.0051 | +0.0867 | +0.2857 | 0.0000 | 0.0000 |
| CenterC | +0.0005 | -0.1597 | +0.5556 | +0.1111 | 0.0000 |
| no-T2 empty-GT | NA | 0.0000 | 0.0000 | 0.0000 | 0.0000 |

Failure flags:

- `Case2031`: `edema_component_worse`
- `Case3012`: `edema_component_worse`

Guardrails:

- class_5 scar unchanged by voxel check on all 44 fold0 validation cases.
- no-T2 empty-GT edema FP did not increase.
- no-T2 empty-GT component sum remained 0 across 28 cases.
- Refiner changed 1145 voxels across 44 validation cases; mean clipped-residual voxel fraction was about 0.0278.
- Candidate still fails because case-level component regression violates the Round10 refiner gate, and CenterC HD95 is slightly worse despite aggregate component/remote FP improvements.

## Current Recommendation

Do not proceed to fold0 short, fold0 longer, fold1-4, 5-fold, or validation submission for the current Round10 candidate.

Recommended next action:

- Treat the current conservative add-only residual refiner as `fail_stop_candidate`.
- If Lane A continues, do not just increase epochs. The next plan should investigate why add-only fusion improves components on average but worsens component count in specific positive cases, especially `Case2031` and `Case3012`.
- Any follow-up should be a bounded refiner-design audit or a new Round11 plan, not automatic longer training.
