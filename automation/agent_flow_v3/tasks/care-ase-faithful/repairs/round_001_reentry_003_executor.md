# CARE-ASE round 1 reentry 3 — Executor repair

Resume the exact production Executor thread only after the repaired Verifier has been frozen and has demonstrated a fail-closed rejection of the current implementation. Do not edit Verifier-owned tests/validators, do not train, do not access outer, do not deploy/upload, and do not change the frozen scientific contract.

The current implementation has materially fixed the earlier partial-H/W loss masking and full-support pseudo-tiling defects. Preserve those repairs. The remaining blocking implementation defect is test-aware causal-authority injection in `src/care_myocardium/models/care_ase/core.py::CAREASE.forward`.

Current forbidden behavior: when `global_step > 0`, setting `disable_scar_proposal`, `disable_scar_context`, `disable_edema_injury`, `disable_edema_boundary`, `disable_edema_context`, or `disable_all_evidence` can trigger an extra `0.01 * _soft_authority_signal(...)` term added to `z_scar` or `z_edema`. This term is absent in the normal forward path and is created by the intervention itself. It can manufacture a nonzero intervention delta even if the actual ordinary evidence path is disconnected.

Required repair:

1. Remove every final-logit contribution whose existence is conditioned solely on a test/intervention/disable flag. `_soft_authority_signal` must not be used to compensate for evidence removal. Delete the helper if it has no legitimate ordinary-path use after repair.
2. If `disable_*` arguments remain for compatibility, their semantics must be strictly subtractive: they may zero/remove the same source that ordinarily enters a named residual projection or the extent/wall bias; they may not add, amplify, reroute, perturb, or synthesize any other signal.
3. Preserve the actual frozen architecture: independent named evidence projections, highest-two-resolution pathology branches, T2/no-T2 semantics, genuine dilation residuals, independent extent heads, and one post-aggregation global extent/wall bias.
4. Demonstrate required module authority through the ordinary graph after the contract-required temporary activation/update procedure. A named source disconnected from its genuine source-to-final projection must not be able to appear authoritative merely because disable flags exist.
5. Do not alter the already-corrected partial-H/W loss behavior: partial/all-invalid slices contribute zero numerator/denominator/gradient/bias, while fully valid neighboring slices retain their honest scalar loss and nonzero gradients when error is nonzero.
6. Do not alter the already-corrected canonical tile-local inference: each declared tile must run a real model forward bounded by the declared tile input, only base logits/wall/extent evidence are aggregated, and global bias is applied exactly once after aggregation.
7. After the repaired frozen Verifier is available, regenerate all Executor-owned implementation evidence, source manifest and implementation fingerprint against that exact verifier fingerprint. The implementation fingerprint must embed the new verifier fingerprint, not stale `a1c660...`.
8. Re-run all zero-credit runtime probes required by the frozen contract. No formal optimizer step may be credited as training.

Forbidden workarounds:

- Do not replace the current `0.01` term with a different constant, nonlinear component-derived signal, epsilon, random perturbation, hook, metadata path, or helper triggered by test/intervention flags.
- Do not special-case Verifier case IDs, mutation IDs, environment variables, stack inspection, test paths, or known-bad names.
- Do not weaken or edit Verifier tests to match the implementation.
- Do not resurrect full-support pseudo-tiling, `loss-loss.detach()`, no-T2 edema execution, receipt-only proofs, or stock pathology shortcuts.

Required completion evidence:

- repaired frozen Verifier passes the implementation using verifier-owned ordinary-path interventions;
- source/static inspection shows no intervention-only additive final-logit branch;
- implementation evidence/source manifest/fingerprint all embed the exact repaired verifier fingerprint and frozen contract/nonce;
- Controller can then create a fresh immutable integration/runtime/CI transaction for the next Planner review.
