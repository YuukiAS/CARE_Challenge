# R2 G2 GPU Fidelity Rereview 01

Decision: PASS_CONTINUE

Candidate: `c9d815b01580062b658fd23fb4c0cde6669a3433`

Reviewer session: `019fc386-dba4-7b72-a29f-06a657b4fc5f`

Effective contract SHA256: `b3ea5986b7a2458f758f7353ab023cea85a9cb67a6fb7c7bf12e5bc10e61d09c`

## Scope Reviewed

Reviewed only the immutable detached checkout:

`/users/a/e/aereinh/CARE_reviewers/care_ase_r2/R2_G2_GPU_FIDELITY_REREVIEW01/c9d815b01580062b658fd23fb4c0cde6669a3433`

and the specified controller submission:

`/users/a/e/aereinh/CARE/results/20260803_care_ase_r2_full_fidelity_execution/reviewer/R2_G2_GPU_FIDELITY_REREVIEW01/controller_submission.json`

No mutable main worktree source review or modification was performed. No fold1/fold4 outer data were read. The prepared `data` symlink was used only for actual-train data and stock checkpoint access during the G2 GPU probe.

## R2-G2-F001 Repair

PASS. `scripts/validation/run_care_ase_r2_g2_gpu_fidelity.py` now defines `module_off_checks()` and runs the eight required ablations:

- `disable_scar_proposal`
- `disable_scar_center`
- `disable_scar_context`
- `disable_edema_injury`
- `disable_edema_boundary`
- `disable_edema_context`
- `disable_extent_wall`
- `disable_all_evidence`

The committed receipt and independent rerun receipt both include `module_off_final_logit_final_label_evidence`. Each toggle records final-logit deltas, scar/edema logit deltas, final-label changed voxel count, and `passes_logit_or_label_effect`. The field is included in `pass_conditions`, raising the gate to `16/16`.

Independent rerun command:

```bash
srun --jobid=61794608 --overlap /users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/validation/run_care_ase_r2_g2_gpu_fidelity.py --fold 1 --output-dir /users/a/e/aereinh/.tmp/codex-CARE/20260803_care_ase_r2_full_fidelity_execution/reviewer/R2_G2_GPU_FIDELITY_REREVIEW01/gpu_rerun --patch-size 8,64,64 --sliding-window-patch-size 8,128,128
```

Rerun result: exit `0`, `decision: PASS`, `pass_condition_count: 16/16`, CUDA device `NVIDIA H100 NVL`, Slurm job `61794608`.

## Regression Check

No regression found. The rerun receipt confirms:

- Required descriptors: complete CenterB, complete CenterC, LGE-only, LGE+C0, small scar.
- Step0 parity: PASS.
- Complete-case gradients reach scar branch, edema branch, and component heads.
- No-T2 edema-exclusive gradient is exactly `0.0`.
- 400-step sampler composition and manifest consumption: PASS.
- Scheduler boundary/mid samples: PASS.
- Area references: `actual_train_only`, `inner_or_outer_access: forbidden_not_used`.
- Checkpoint required fields, sidecar, and reload parity: PASS with reload logits max absolute error `0.0`.
- Resume fields include scheduler state, cursor fields, and next batch hash.
- Sliding-window full-volume smoke produced finite logits.
- Fixed decode excludes class 4 for no-T2.
- `outer_access_count_before_freeze`: `0`.

Static receipts for semantic loss, sampler, scheduler, checkpoint, and contract coverage remain PASS.
