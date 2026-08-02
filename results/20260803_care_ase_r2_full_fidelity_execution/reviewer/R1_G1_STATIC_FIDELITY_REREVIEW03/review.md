# R1 G1 Static Fidelity Rereview 03

Decision: PASS_CONTINUE

Candidate: `51863825b286269f554b5c74010ad24f02121c6a`

Reviewer session: `019fc386-dba4-7b72-a29f-06a657b4fc5f`

Effective contract SHA256: `b3ea5986b7a2458f758f7353ab023cea85a9cb67a6fb7c7bf12e5bc10e61d09c`

## Scope Reviewed

Reviewed only the immutable detached checkout:

`/users/a/e/aereinh/CARE_reviewers/care_ase_r2/R1_G1_STATIC_FIDELITY_REREVIEW03/51863825b286269f554b5c74010ad24f02121c6a`

and the specified controller submission:

`/users/a/e/aereinh/CARE/results/20260803_care_ase_r2_full_fidelity_execution/reviewer/R1_G1_STATIC_FIDELITY_REREVIEW03/controller_submission.json`

No mutable main worktree review or modification was performed. No fold1/fold4 outer data were read. Actual fold1/fold4 manifest files were not required for this R1 rereview.

## Manifest Builder Provenance

PASS. `scripts/evaluation/care_ase/build_care_ase_r2_hard_negative_manifest.py` still limits manifest construction to `actual-train` roles, and the payload no longer claims stock-only provenance. It now records:

- `source`: `actual_train_only_hard_negative_manifest_from_configured_prediction_roots`
- `prediction_root_count`
- `prediction_roots`
- per-case `prediction_sources` with prediction path and SHA256

This accurately represents mixed configured prediction roots while preserving actual-train-only manifest scope.

## Known-Bad Validator

PASS. Independent detached rerun:

```bash
PYTHONDONTWRITEBYTECODE=1 /users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/validation/validate_care_ase_r2_g1.py --output-dir /tmp/care_ase_r2_r1_g1_rereview03_validator_probe
```

Result: exit `0`, `decision: PASS`, `failures: []`.

The regenerated `/tmp` known-bad report has:

- `required_known_bad_count`: `31`
- `known_bad_count_passed`: `31`
- nonzero fixture exits: `31`
- `REJECTED_AS_EXPECTED`: `31`
- failed rows: `[]`

## Regression Check

No regression found in formal wrapper, entrypoint, model, target builder, sampler, loss, optimizer groups, scheduler, checkpoint save/resume, evaluator, or decode static coverage. Static receipts for call chain, contract coverage, semantic loss, sampler, scheduler, and checkpoint remain PASS. Source SHA changes versus REREVIEW02 are limited to the manifest builder and regenerated evidence receipts.
