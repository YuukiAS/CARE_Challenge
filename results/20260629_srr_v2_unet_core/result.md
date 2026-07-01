# Result 20260629 SRR-v2 U-Net Core

Status: interim, `1/3` formal variants ready.

## Summary

This task introduced an isolated multi-scale SRR-v2 U-Net route to test whether the old SRRMyoPSLite failure was primarily an architecture-capacity problem. The implementation and CPU/GPU preflights passed, and the first formal variant produced a recoverable checkpoint. Full-volume export initially failed on a depth-1 validation case, but the pooling bug was patched and the checkpoint was recovered on CPU.

The first recovered formal variant shows a real scar-side signal compared with earlier lightweight SRR routes, but the route is not complete: two required variants remain pending on `a100-gpu`, and no final SRR-v2 selection can be made yet.

## Files Read

- `prompts/tasks/20260629_srr_v2_unet_core.md`
- `docs/notes/20260629_srr_capacity_and_result5_audit.md`
- `docs/notes/20260629_result5_gap_audit.md`
- `docs/notes/deep_research/Result4.pdf`
- `docs/notes/deep_research/Result5.pdf`
- `results/20260628_result5_goal/final_status.md`
- `results/20260628_myops_proposal/selection.md`
- `results/20260629_result4_srr_core_rebuild/selection.md`
- `src/care_myocardium/models/srr_myops.py`
- `src/care_myocardium/models/srr_blocks.py`
- `src/care_myocardium/models/pathology_heads.py`
- `scripts/training/run_srr_myops_fold0.py`
- `results/metrics/nnUNet.md`

## Code and Script Changes

- Added isolated model file `src/care_myocardium/models/srr_v2_unet.py`.
- Integrated SRR-v2 variants into `scripts/training/run_srr_myops_fold0.py`.
- Patched SRR-v2 modality encoder pooling so full-volume depth-1 cases use safe per-dimension pooling.
- Added recovery exporter `scripts/evaluation/export_srr_myops_checkpoint.py`.
- Added aggregation helper `scripts/evaluation/finalize_rescue_srr_route.py`.
- Added Slurm wrapper `jobs/src/run_srr_v2_unet_core.sh`.

## Jobs

| job | variant | partition | state | elapsed | exit |
| --- | --- | --- | --- | ---: | --- |
| `57094446_0` | `srr_v2_multiscale_private_basic` | `htzhulab` | `FAILED` during export, recovered from checkpoint | 06:37:38 | `1:0` |
| `57095505_1` | `srr_v2_multiscale_private_proposal` | `a100-gpu` | `PENDING` | 00:00:00 | pending |
| `57095505_2` | `srr_v2_proposal_uncertainty_hardneg` | `a100-gpu` | `PENDING` | 00:00:00 | pending |

## Current Metrics

Recovered `srr_v2_multiscale_private_basic`:

| metric | group | Dice | HD95 |
| --- | --- | ---: | ---: |
| myops_edema | all cases | 0.3247 | 49.3507 |
| myops_edema | GT-positive | 0.1431 | 94.9052 |
| myops_scar | all cases | 0.1998 | 82.7490 |
| myops_scar | GT-positive | 0.2044 | 82.7490 |

Reference context:

- D4 dictionary scar all-case Dice: `0.1054`.
- Repaired proposal best scar all-case Dice: `0.1038`.
- nnU-Net fold0 scar Dice: `0.5602`.
- nnU-Net fold0 edema Dice: `0.3944`.

## Current Interpretation

SRR-v2 basic gives a meaningful scar improvement over the old SRR/D4/repaired proposal family, but it is still far below nnU-Net and does not rescue edema GT-positive Dice. This supports continuing the remaining SRR-v2 variants, especially the proposal and uncertainty/hard-negative variants, but it does not yet justify selecting SRR-v2 or expanding folds.

## Pending

- `srr_v2_multiscale_private_proposal`
- `srr_v2_proposal_uncertainty_hardneg`
- Final `selection.md`
- Complete usage logging for formal variants

No validation package or external upload was produced.
