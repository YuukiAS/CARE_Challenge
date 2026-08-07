# CARE-ASE Planner repair — Executor — round 1 re-entry 001

Bind this repair to:

- task: `care-ase-faithful`
- request nonce: `care-ase-20260806T090955Z`
- frozen contract SHA256: `a4758fd3125cdfaac4cf044fd4fa948472558cca231c0429a26e63e5d7d1e11d`
- reviewed integration SHA: `edb4f2e290c72e92e1bcbd74295c525fef924f11`
- reviewed implementation fingerprint: `3eabfb0be9eda776da6dd6fe3068004894ea7a5b4c30966941fc05bdc412e0dc`
- reviewed verifier fingerprint: `847263d0afd1f34e81c49a981ea33dae5c12f53114c543d50830d077d9a7e167`
- Planner review: `results/agent_flow_v3/care-ase-faithful/planner_reviews/round_001_reentry_001.json`

You are the exact production Executor session. Start only after Controller has integrated and frozen the repaired Verifier from this review. Do not edit verifier-owned tests/validators/protected fixtures, the frozen contract, or orchestration policy.

## Blocking defects to close

### 1. Partial-H/W extent validity is wrong

The frozen contract requires padding, all-invalid slices and partial-H/W slices to contribute exactly zero extent bias, loss and gradient. Current implementation treats a slice as valid whenever `valid_HxW_sum > 0`, so a partially padded slice remains active in `compute_slice_extent_statistics`, `CAREASE._extent_bias`, `per_slice_extent_loss` and `global_extent_bias`.

Repair this with one shared, explicit full-H/W-valid slice semantic. For any partial-H/W or all-invalid output slice:

- scar and edema extent presence/area statistics must not contribute;
- extent bias must be zero;
- presence/area loss denominator and contribution must be zero;
- gradient to the corresponding extent head through that slice must be zero.

A fully valid neighboring slice must remain supervised and retain final-logit authority. Preserve full-case target construction and physical-bin downsampling; do not remove the extent mechanism.

### 2. Multi-tile equivalence evidence uses a noncanonical full-context override

The current real-case probe is improved, but the forced multi-tile call passes `exact_context_patch_size` equal to the single-window full-cover patch. Every output tile therefore sees full-volume-like context, while canonical `CAREASEFullVolumeInferenceSettings` does not declare this override and normal deployment does not use it.

Regenerate the single-versus-multi-tile proof through the exact declared canonical deployment settings/path with a genuinely smaller tile and without a probe-only larger-context override. If larger context is already an explicit frozen deployment requirement, it must be represented in canonical settings and used identically by real deployment; otherwise remove it from evidence generation. Record actual tile/context settings, forward count, aggregation path, one-time global-bias count, logit difference and decode difference for T2-present and no-T2 cases.

### 3. Evidence/fingerprint binding is stale

After the repaired Verifier is frozen and integrated, regenerate Executor evidence and the implementation fingerprint against that exact new verifier fingerprint. Do not retain the hardcoded superseded `9fbed451...` verifier fingerprint. All implementation evidence, source manifest, runtime receipts and implementation fingerprint must bind the same current nonce, frozen contract, integrated source and repaired verifier fingerprint.

## Required regression evidence

- A deliberately partial-H/W slice gives exactly zero scar/edema extent bias, zero extent loss denominator/contribution and zero extent-head gradient; a fully valid slice remains active.
- Canonical multi-tile inference is actually multi-tile and uses no hidden evidence-only context override; global extent/wall bias is observed exactly once after aggregation.
- The repaired independent Verifier can reproduce these properties from executable code rather than trusting Executor booleans.
- The regenerated implementation fingerprint embeds the exact newly frozen verifier fingerprint.
- Step-0 parity, real total-loss denominators, canonical checkpoint/resume, deployment loader, evaluator and valid OOF hard-negative evidence remain passing after the repair.

## Forbidden workarounds

- Do not redefine partial-H/W as valid because any pixel is valid.
- Do not mask only reported metrics while allowing bias or gradients through.
- Do not remove extent/context modules or weaken final authority.
- Do not use full-volume context per tile solely to force numerical equality.
- Do not weaken or modify Verifier tests/validators.
- Do not train, access outer data, merge develop to main, deploy or upload.

Commit locally in the Executor branch according to the existing role contract and return exact implementation commit/fingerprint/runtime receipts to Controller. Controller must integrate Verifier then Executor, regenerate the current runtime manifest and CI packet, increment the next Planner transaction to review round 2, and only then request another Planner review.
