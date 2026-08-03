# CARE-ASE R2 Last Hotfix v9 Final Addendum

Task key: `20260803_care_ase_r2_last_hotfix_v9`

This addendum is part of the same v9 pretraining closure scope. It does not
authorize formal training, outer evaluation, Docker build/upload, checkpoint
selection changes, new model components, new losses, or additional optimizer
budget. It closes the remaining implementation and runtime fidelity gaps before
Commit A.

The effective v9 contract, executor plan, controller context, critical source
manifest, and external review request must bind this file by SHA256.

## Required Closures

- The executor plan must exist at
  `prompts/tasks/20260803_care_ase_r2_last_hotfix_v9_executor_plan.yaml` and
  pass `scripts/ops/validate_executor_plan.py`.
- Canonical full-volume CARE-ASE inference must preserve stock nnU-Net sliding
  window semantics: starts, padding, Gaussian importance weighting, mirroring,
  inverse mirror aggregation, dtype, and denominator normalization. Auxiliary
  maps used for global extent must follow the same mirror/inverse-mirror path as
  base logits.
- Augmentation must carry explicit transformed `source_z_id` and
  `source_z_valid` authority. Extent targets and extent bias validity must use
  the transformed source-z authority, including z mirror and z padding.
- Inner trend monitoring must import only canonical full-volume inference, use
  the v9 self-contained inference loader, reject old v5-v8 roots, require
  verified checkpoints, reject outer cases, and write only monitoring packets
  that cannot alter training state.
- The checkpoint selector must be deterministic, accept only fixed candidates
  `4000,6000,8000,10000,12000,14000`, implement the frozen score formula, and
  reject missing metrics or any outer-derived input.
- Mandatory named evidence modules must have per-module gradient and
  intervention evidence after the first real update; aggregate branch gradients
  are not sufficient.
- Parameter ownership oracle must be independent from production grouping and
  verify owner, group, aliases, Stage A/B/C trainability, and optimizer LR by
  parameter object identity.
- Stage A/B/C transactional runtime checks must reuse the same formal runtime
  data path and restore all model, optimizer, scheduler, sampler, augmentation,
  and RNG state without optimizer steps.
- SIGUSR1/SIGTERM handling must only save after a complete optimizer step,
  write resumable interrupted receipts, stop heartbeat, and resume without
  overlap or gap.
- Formal runtime should use read-only case/target cache reuse and avoid per-micro
  GPU synchronization on non-log steps while retaining finite checks.
- Outer evaluation must be modeled as a single-use resumable transaction; this
  task must not read outer data.
- Direct stock OOF proof must verify actual held-out membership instead of
  hard-coding truth.
- Stage C descriptor semantics must record `case_group = complete`, with
  `center_group` carrying `complete_centerB` or `complete_centerC`.

## Final State

The only successful terminal state remains:

`PRETRAINING_EXTERNAL_REVIEW_REQUEST_READY`

The failure state is:

`NEEDS_REPAIR`
