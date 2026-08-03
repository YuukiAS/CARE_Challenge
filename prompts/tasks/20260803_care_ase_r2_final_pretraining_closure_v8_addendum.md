# CARE-ASE R2 v8 Forced Closure Addendum

This addendum is part of `20260803_care_ase_r2_final_pretraining_closure_v8`.
It is not a new task and does not reopen the goal. A later user supervision
message explicitly raises the diagnostic GPU optimizer-step budget to at most
20 total reserved steps; formal training remains unauthorized. This addendum
and the v8 effective contract must record that override before Commit A.

## Authority

All original v8 requirements remain active. When this addendum conflicts with
the original v8 prompt, the stricter fail-closed rule in this addendum wins.
The final successful state remains:

```text
PRETRAINING_EXTERNAL_REVIEW_REQUEST_READY
```

The controller may not self-issue:

```text
PRETRAINING_EXTERNAL_REVIEW_PASS
FORMAL_TRAINING_AUTHORIZED
```

If Commit A has not been created, absorb this addendum normally. If Commit A
exists but probes have not run, rebuild or amend Commit A and update all source
SHA. If any optimizer probe has run on an old source SHA, stop it, mark it
zero-credit, count consumed steps against the 20-step diagnostic budget, and
only accept probes run on the final Commit A SHA.

## P0 Commit A, Commit B, and Runtime Inputs

Freeze these identities:

- `implementation_source_commit_sha`: Commit A
- `review_packet_commit_sha`: Commit B
- `formal_execution_checkout_commit_sha`: Commit B

Formal training must run from a clean detached Commit B checkout. Commit B may
contain reviewed lightweight runtime inputs and review state, but must not
change critical source, tests, contracts, or wrappers from Commit A. The
scientific implementation source remains Commit A.

Permit checks must require:

- `reviewed_candidate_commit_sha == Commit A`
- `implementation_source_sha == Commit A`
- `review_packet_commit_sha == Commit B`
- current `HEAD == Commit B`
- Commit A is an ancestor of Commit B
- Commit B is contained in `origin/main`
- Commit A and Commit B critical source manifests are identical
- worktree is clean
- mutable main, untracked files, or local copied manifests are rejected

Create and bind
`results/20260803_care_ase_r2_final_pretraining_closure_v8/formal_runtime_input_bundle.json`
with SHA256 for fold1/fold4 hard-negative manifests, fold1/fold4 full-case
target manifests, direct stock OOF provenance, area reference, effective
contract, implementation source, and the bundle payload. The bundle must not
try to contain its own Commit B SHA because that creates a Git self-reference.
Instead, Commit B is bound by the pushed review request and future external
permit through:

- `review_packet_commit_sha == Commit B`
- `formal_execution_checkout_commit_sha == Commit B`
- `formal_runtime_input_bundle_sha256 == sha256(formal_runtime_input_bundle.json)`
- current `HEAD == Commit B`

This preserves the same fail-closed runtime binding without embedding a
self-referential commit hash inside a tracked file.

Permit and formal checkpoints must include:

- `formal_execution_checkout_commit_sha`
- `formal_runtime_input_bundle_sha256`
- `hard_negative_manifest_sha256`
- `full_case_target_cache_manifest_sha256`

Sampler, target-cache manager, and formal runtime must receive manifest paths
through explicit constructor arguments. Hardcoded review directories, globbing,
"latest file" lookup, and local legacy copies are forbidden.

## P0 Extent Final Bias

`CAREASE._extent_bias()` and canonical full-volume global extent bias must make
invalid and partial-H/W slices contribute exactly zero final bias. For
`valid_slice == 0`, presence, area, wall statistics, all biases, final extent
bias, and gradients to extent heads or `p_wall` for that slice are zero. For
`full_hw_coverage_slice == 0`, area supervision and area/wall-derived final
extent bias are zero. Do not convert zero statistics through logit centering to
a nonzero negative bias. Padding must not change base logits, extent bias,
final logits, or conditional decode.

## P0 Canonical Full-Volume Inference

Create `src/care_myocardium/inference/care_ase_r2_full_volume.py` exposing
`predict_care_ase_r2_full_volume_logits(...)` and
`predict_care_ase_r2_full_volume_labels(...)`. All inference uses FP32,
forwards patches with `disable_extent_wall=True`, aggregates base logits,
`p_wall`, and extent evidence over the valid support, applies global slice
extent bias exactly once, then calls the fixed conditional decode once. Single
tile and tiled volumes must use the same path. The outer evaluator must import
this canonical module and must not carry a second CARE-ASE sliding-window or
extent aggregation implementation. The outer evaluator must take explicit
source, review, contract, critical manifest, checkpoint, permit, and output
arguments, and must not use old hardcoded result roots or W4.5 paths.

## P0 Self-Contained Checkpoint Loading

Split checkpoint APIs into training-resume and inference/deployment loaders.
Training resume continues to require the requested fold's canonical stock
checkpoint path and SHA. Inference/deployment loading must not open stock
checkpoints, default plans, default dataset JSON, or training-only nnU-Net loss
builders. The formal payload must contain architecture signature, embedded or
relocation-safe plans/dataset topology SHA, pathology deep-supervision weights,
and `deployment_load_requires_stock_checkpoint: false`.

## P0 Checkpoint Cadence and Remainder Resume

Logical chunks remain `[0,2000]`, `[2000,4000]`, ... `[12000,14000]`.
Initial formal chunk invocation must start on a 2000 boundary and end exactly
2000 steps later. Resume from a verified periodic checkpoint may start at the
checkpoint global step and continue to the original logical chunk end, for
example `1000 -> 2000` and `3000 -> 4000`. Formal-resumable checkpoints must be
accepted by the wrapper. Signal handlers may only request stop, and checkpoints
may only be saved after a complete optimizer step with microbatch cursor zero.

## P0 Named Evidence Liveness

The liveness oracle must verify every mandatory scar, edema, and detached
anatomy-context evidence source, adapter, gate, dilation producer, extent head,
and named projection. Step0 backward requires nonzero gradients for each
zero-init named projection. After one real optimizer step, diagnostic backward
and intervention checks must show each mandatory producer, adapter, gate,
dilation, and projection is alive and has owned-logit authority. Diagnostic
backward/intervention must restore model, optimizer, scheduler, gradients, RNG,
sampler, and patch RNG, and does not consume optimizer budget.

## P1 Formal Target Provenance

Formal runtime must require
`target_builder_provenance == full_case_target_cache_manifest_verified`.
Missing full-case cache, manifest, case entry, array SHA, spacing/shape match,
or transformed footprint must fail before model forward and before probe budget
consumption. Patch-local fallback may exist only in explicit unit-test helpers
and must be unreachable from formal entrypoints.

## P1 Stage B/C Transactional Runtime Oracle

Stage B and Stage C diagnostics must reuse the same `CAREASEFormalRuntime`
materialization, augmentation, target, forward, loss, backward, scheduler, and
trainability path, but skip `optimizer.step` and restore all state. These
checks do not consume optimizer-step budget.

## P1 Probe Budget Reservation

The five-step probe budget must be an append-only reservation ledger. A process
must reserve a unique slot before data materialization, forward, backward, or
optimizer step. A successful reservation permanently consumes the slot even if
the process crashes, is cancelled, OOMs, or fails before optimizer step. The
sixth reservation must fail before any forward. Fold, PID, output directory, or
probe name changes must not reset the ledger.

## P1 v7 No-Regression Matrix and Mutations

The v8 packet must include a real no-regression matrix for v7 fixes, with
source path, function/class, positive behavior test, known-bad mutation,
command exit, and status for each high-risk clause. It must not rely on
"inherited", file existence, validator PASS, or manual inspection only.

Additional real mutations 13-24 must be detected:

13. invalid slice statistic zero still produces nonzero final bias;
14. partial H/W slice adds local extent bias to final logits;
15. single-patch inference directly enables local extent;
16. outer evaluator restores old hardcoded root or permit;
17. inference checkpoint loader accesses stock checkpoint;
18. checkpoint step01000 marks formal resumable but CLI rejects resume;
19. formal runtime falls back to patch-local target without cache;
20. mandatory named evidence exists but has zero gradient/intervention;
21. Stage B/C use a non-formal-runtime data path;
22. concurrent reservations allow slot 6;
23. formal execution reads CommitB-only manifests from Commit A checkout;
24. Commit B changes critical source but permit still accepts it.

## Required Additional Files

The review packet must include:

- `formal_runtime_input_bundle.json`
- `formal_execution_checkout_binding_receipt.json`
- `extent_final_bias_zero_receipt.json`
- `canonical_full_volume_inference_receipt.json`
- `deployment_checkpoint_self_contained_receipt.json`
- `formal_checkpoint_remainder_resume_receipt.json`
- `named_evidence_liveness_receipt.json`
- `named_evidence_liveness.csv`
- `formal_target_provenance_receipt.json`
- `stage_bc_transactional_runtime_oracle.json`
- `probe_budget_atomic_reservation_receipt.json`
- `v7_full_no_regression_matrix.json`

`MANIFEST.md`, `completion_check.md`, `controller_report.md`, and
`pretraining_external_review_request.json` must list these files and SHA256.

## Final Controller Acceptance

The controller must directly inspect final Commit A/B source and diff. Ready
status is allowed only when formal execution is from clean detached Commit B,
scientific implementation source remains Commit A, runtime inputs are bound by
the Commit B bundle, extent bias is zero for invalid and partial-H/W slices,
there is one canonical full-volume inference path, checkpoint inference loading
is self-contained, formal-resumable checkpoints are actually resumable, named
evidence is alive after the first step, formal runtime cannot use patch-local
fallback, Stage B/C transactional oracles pass, probe reservation is
crash-nonreclaimable and concurrent-safe, v7 no-regression evidence is real,
all new mutations are rejected, final-source reservations are at most five,
formal training has not started, outer access remains zero, and `origin/main`
is bound to Commit B.
