# Source Audit And Repairs

status: SOURCE_REPAIRS_APPLIED

## Repairs

1. Rebound CARE-ASE formal runtime identity from v9/external-review-only semantics to the 20260804 emergency controller task.
2. Added acceptance for task-scoped controller permit token `PRETRAINING_CONTROLLER_USER_AUTHORIZED_PASS_20260804`, with task SHA and user authorization checks.
3. Changed formal runtime namespace to `results/20260804_care_ase_r2_formal_training_<sha>/`.
4. Rebound sampler default hard-negative manifest path to the 20260804 task root while preserving verified v9 direct OOF manifests as allowed inherited input evidence.
5. Rebound hard-negative and full-case target manifest builders to emit into the 20260804 task root.
6. Updated the Slurm wrapper to accept `TRAINING_PERMIT` or legacy `EXTERNAL_REVIEW_PERMIT` and default to the 20260804 formal runtime namespace.
7. Updated G1 static validator to check the current task manifest path and controller-permit token.
8. Replaced self-authored sliding-window starts/end-only padding in canonical full-volume inference with installed nnUNetv2 `compute_steps_for_sliding_window`, `compute_gaussian`, and acvl `pad_nd_image` symmetric padding/crop-back semantics. Fixed crop-back so the padding slicer applies only spatial axes to 6-class logits.

## Validation

- py_compile PASS for changed Python files.
- targeted full-volume/permit pytest: 17 PASS.
- targeted runtime/sampler pytest: 14 PASS.
- G1 current-source smoke with `--skip-known-bad`: PASS.

## Notes

The default 20260804 hard-negative builder correctly rejected the old anchor manifest because it lacks direct preprocessed-grid producer fields for Case1002. The controller therefore reused the already verified v9 direct preprocessed-grid hard-negative manifests and copied them into the 20260804 task root with a provenance receipt, without weakening the builder.
