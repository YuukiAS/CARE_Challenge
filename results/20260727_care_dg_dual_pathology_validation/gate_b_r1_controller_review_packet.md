# Gate B-R1 Controller Review Packet

created_at_utc: `2026-07-28T02:26:45Z`
git_head_before_packet_commit: `d59c5fa39b0c068c80b33e9fcf305c64891e15d9`

## Decision

`GATE_B_R1_OPERATIONAL_PASS_SCIENTIFIC_FAIL_EXPANSION_PAUSED`

Gate B-R1 is operationally valid but not scientifically sufficient for five-fold expansion. The R1 inference and train-side checkpoint selection repair passed the local validator, but complete-trimodal fold0 did not improve any target pathology by more than 0.005 Dice over the nnU-Net anchor.

## Current Runtime State

- allocation: `60657290` preserved, not terminated
- squeue: `JOBID STATE TIME TIME_LEFT NODELIST NAME / 60657290 RUNNING 2-01:21:49 22:38:11 g1807htzh01 CAREInteractive3d`
- active CARE-DG training/evaluation processes: `0`
- folds 1-4: paused; no expansion authorization
- fold4: stopped before credit; no runtime checkpoint observed

## Gate B-R1 Evidence

- operational validator: `PASS`
- scientific gate: `FAIL`
- scientific_expansion_authorized: `False`
- failure: `no_pathology_improves_by_more_than_0.005`
- selected checkpoint: `results/20260727_care_dg_dual_pathology_validation/runtime/repaired_formal_scar_priority/fold0/checkpoints/checkpoint_step08000.pt`
- checkpoint SHA256: `d0a164c951f7ad8483c0796730d381b5216b8af367448edec4dbe97b3890f1c9`
- outer_val_used_for_selection: `False`
- no-T2 edema delta exact zero: `True`
- post-scar overwritten voxels: `0`

## Scientific Gate Deltas

| pathology | Dice delta vs anchor | HD95 ok | remote FP ok | component count ok |
|---|---:|---:|---:|---:|
| scar | 0.001405 | True | True | True |
| edema_zone | 0.001168 | True | True | True |
| pure_edema | -0.002103 | True | True | True |

## Required Paths

- summary: `results/20260727_care_dg_dual_pathology_validation/gate_b_r1_summary.json`
- validator: `results/20260727_care_dg_dual_pathology_validation/gate_b_r1_validator_report.json`
- diagnostic report: `results/20260727_care_dg_dual_pathology_validation/gate_b_r1_diagnostic_report.md`
- evaluation root: `results/20260727_care_dg_dual_pathology_validation/runtime/repaired_formal_scar_priority/fold0/gate_b_r1_evaluation`
- casewise metrics: `results/20260727_care_dg_dual_pathology_validation/runtime/repaired_formal_scar_priority/fold0/gate_b_r1_evaluation/gate_b_r1_casewise_metrics.csv`
- inner checkpoint selection: `results/20260727_care_dg_dual_pathology_validation/runtime/repaired_formal_scar_priority/fold0/gate_b_r1_evaluation/gate_b_r1_inner_checkpoint_selection.csv`
- seam audit: `results/20260727_care_dg_dual_pathology_validation/runtime/repaired_formal_scar_priority/fold0/gate_b_r1_evaluation/gate_b_r1_seam_audit.csv`

## Boundary

Do not start folds 1-4, all-data fit, validation upload, Docker upload, a new Slurm job, or runtime push until a later user/planner-approved same-scope repair satisfies the Gate B scientific expansion criteria.
