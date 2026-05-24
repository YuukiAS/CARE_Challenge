# Lane A Round11 Active Component-Safe Bidirectional Edema Refiner Execution

Plan source: `docs/plans/laneA_round11_next_component_safe_bidirectional_edema_refiner_execution.md`

Status: `fail_stop_bidirectional_refiner_candidate_no_longer_train`

Execution root:

```text
results/diagnostics/phase0_phase1/laneA_myops/round11_component_safe_refiner/
```

## What Ran

1. Round10 reproducibility gate:
   - checkpoint exists;
   - Round10 validation predictions are 44/44;
   - failure cases reproduced as `Case2031` and `Case3012`.
2. Case-level failure audit and overlays:
   - `Case2031`: low-T2-support tiny additions;
   - `Case3012`: residual remote addition.
3. Offline fusion / threshold grid:
   - no offline rule passed the clean component/HD95/scar/no-T2 gate.
4. Bidirectional edema-only refiner implementation:
   - `src/care_myocardium/refiner/laneA_round11_model.py`
   - `scripts/training/run_laneA_round11_bidirectional_refiner_train.py`
   - class_4 edema only; class_5 scar immutable; no-T2 additions disabled; component fallback enabled.
5. Unit/gradient smoke:
   - finite loss/gradients;
   - scar changed voxels 0;
   - no-T2 new edema voxels 0.
6. Tiny overfit / safety screen:
   - after component fallback, `Case3012` reverts to baseline instead of worsening component count;
   - selected T2-present cases show local edema signal;
   - scar/no-T2 remain clean.
7. Single bounded htzhulab fold0 very-short Slurm job:
   - command: `sbatch jobs/nnUNet/laneA_round11_bidirectional_refiner_fold0_very_short.sh`
   - job id: `52109889`
   - state: `COMPLETED`
   - exit code: `0:0`
   - elapsed: `00:00:52`

## Fold0 Very-Short Result

| subset | delta Dice | delta HD95 improvement | component improvement | remote FP improvement | scar delta |
| --- | ---: | ---: | ---: | ---: | ---: |
| all-case | +0.0025 | -0.0243 | +0.5455 | -0.0682 | 0.0000 |
| T2-present GT-positive | +0.0025 | -0.0669 | +1.5000 | -0.1875 | 0.0000 |
| CenterB | +0.0087 | -0.0251 | +1.1429 | 0.0000 | 0.0000 |
| CenterC | -0.0022 | -0.0993 | +1.7778 | -0.3333 | 0.0000 |
| no-T2 empty-GT | NA | 0.0000 | 0.0000 | 0.0000 | 0.0000 |

Failure flags:

- `Case3011`: `edema_remote_fp_worse`
- `Case3040`: `edema_remote_fp_worse`

## Gate Decision

The current Round11 candidate must stop. It preserves the two most important safety rails, scar and no-T2 empty-GT stability, but it fails the CenterC/remote-FP/HD95 gate. The positive Dice/component signal is not clean enough to justify fold0 short train, longer train, fold1-4, 5-fold, validation zip, or submission.

## Next Recommendation

Do not add epochs to this candidate. If Lane A continues in this route, first audit `Case3011` and `Case3040` overlays and design an inference-safe remote-FP/anatomy-distance guard. Otherwise, escalate through a new controlled plan focused on T2 support estimation or anatomy/lesion consistency, not whole-network fine-tuning.
