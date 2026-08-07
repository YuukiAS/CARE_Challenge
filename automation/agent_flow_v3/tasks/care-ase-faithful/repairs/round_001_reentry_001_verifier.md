# CARE-ASE Planner repair — Verifier — round 1 re-entry 001

Bind this repair to:

- task: `care-ase-faithful`
- request nonce: `care-ase-20260806T090955Z`
- frozen contract SHA256: `a4758fd3125cdfaac4cf044fd4fa948472558cca231c0429a26e63e5d7d1e11d`
- reviewed integration SHA: `edb4f2e290c72e92e1bcbd74295c525fef924f11`
- reviewed implementation fingerprint: `3eabfb0be9eda776da6dd6fe3068004894ea7a5b4c30966941fc05bdc412e0dc`
- reviewed verifier fingerprint: `847263d0afd1f34e81c49a981ea33dae5c12f53114c543d50830d077d9a7e167`
- Planner review: `results/agent_flow_v3/care-ase-faithful/planner_reviews/round_001_reentry_001.json`

You are the exact production Verifier session. Do not edit model, training, inference, jobs, configs, the frozen contract, or Executor-owned implementation evidence. Repair only verifier-owned validation/test/runtime-verification assets.

## Blocking defect to close

The current verifier is still receipt replay rather than independent executable verification. Its recorded verifier environment has `torch_available=false` and `nnunetv2_available=false`, while `receipt_bound_probe_results` converts Executor-authored receipts into PASS probes. `mutation_result` returns predetermined nonzero failure payloads without applying and executing the mutations. This does not satisfy the frozen independent-verification contract.

## Required repair

1. Run the verifier-owned executable runner in the isolated production Verifier environment with the actual CARE runtime binding, including PyTorch, nnU-Net and declared train-only assets. Do not substitute `/usr/bin/python` when it lacks the runtime.
2. Independently execute against the exact integrated source:
   - model construction and step-0 stock parity;
   - canonical total loss, real train-only forward/backward and expected gradients;
   - mixed T2/no-T2 row execution, supervision and class-4 competition exclusion;
   - required-module interventions that change intended final logits;
   - schema-v4 checkpoint save/reload and canonical next-step continuity;
   - canonical full-volume single/multi-tile inference;
   - self-contained deployment loader;
   - evaluator interface/fair population checks.
3. Executor receipts may be cross-checked for provenance, but they must not be the source of the verifier's runtime conclusion. The verifier must generate its own observed outputs and hashes.
4. Replace predetermined `mutation_result` failures with real executable mutations/interceptions. At minimum execute the current mutation families for extent topology, dilation residual, injury initialization, final-authority bypass, no-T2 edema calls, single/multi-tile path, tile-local bias, deployment stock-checkpoint reopening, evaluator mismatch, checkpoint drift and artifact/source drift.
5. Add a protected executable regression for the frozen partial-H/W rule: a partially valid H/W output slice must have zero extent bias, zero extent-loss denominator/contribution and zero gradient to scar/edema extent heads; a fully valid neighboring slice must remain active.
6. Add a protected executable regression rejecting any inference-equivalence proof that relies on a probe-only context override not present in canonical `CAREASEFullVolumeInferenceSettings` / deployment semantics.
7. Bind every verifier-owned command/output to the current nonce, contract SHA, exact source/integration SHA, implementation fingerprint and new verifier fingerprint. Record actual runtime executable, environment and input hashes.
8. Freeze a new verifier fingerprint only after the independent executable suite and real mutations pass. Controller must then integrate this exact Verifier commit before Executor repair.

## Required evidence

The new verifier receipt must show a runtime capable of executing PyTorch/nnU-Net and independently produced probe results. A forged or internally self-consistent Executor PASS receipt must not pass when the executable graph is defective. Mutation reports must identify the mutation actually applied, the mutated fingerprint/command, and the observed nonzero verifier result.

## Forbidden workarounds

- Do not treat receipt/hash validation as independent runtime execution.
- Do not copy Executor payload values into verifier PASS probes.
- Do not predeclare mutation failure from a mutation ID.
- Do not weaken existing protected tests or change the scientific contract.
- Do not implement CARE-ASE source, train, access outer data, merge to main, deploy or upload.

Commit locally in the Verifier branch according to the existing role contract, leave the worktree clean, and return the exact commit/fingerprint/receipt to Controller for Verifier-first integration.
