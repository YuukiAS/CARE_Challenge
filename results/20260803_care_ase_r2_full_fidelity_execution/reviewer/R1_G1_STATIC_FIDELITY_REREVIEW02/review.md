# R1 G1 Static Fidelity Rereview 02

Decision: PASS_CONTINUE

Candidate: `13bd50c839d0b8494956ad5247a4672f77ce7479`

Reviewer session: `019fc386-dba4-7b72-a29f-06a657b4fc5f`

Effective contract SHA256: `b3ea5986b7a2458f758f7353ab023cea85a9cb67a6fb7c7bf12e5bc10e61d09c`

## Scope Reviewed

Reviewed only the immutable detached checkout:

`/users/a/e/aereinh/CARE_reviewers/care_ase_r2/R1_G1_STATIC_FIDELITY_REREVIEW02/13bd50c839d0b8494956ad5247a4672f77ce7479`

and the specified controller submission:

`/users/a/e/aereinh/CARE/results/20260803_care_ase_r2_full_fidelity_execution/reviewer/R1_G1_STATIC_FIDELITY_REREVIEW02/controller_submission.json`

No mutable main worktree review or modification was performed. No fold1/fold4 outer data were read.

## Sampler Runtime Repair

PASS. In `src/care_myocardium/training/care_ase_sampler.py`, `CAREASEDeterministicSampler.__init__` now initializes `by_group` with `complete_centerB` and `complete_centerC`, and maps source metadata centers with:

```python
center_group = {"CenterB": "complete_centerB", "CenterC": "complete_centerC"}[row.center]
```

`descriptor_for_step()` Stage C selects from `stage_c_cycle = ("complete_centerB", "complete_centerC")`, so the runtime keys now match the populated dictionaries.

The new test `tests/care_ase/test_sampler_runtime_contract.py::test_sampler_stage_c_center_groups_are_runtime_selectable` directly covers the failure mode: it advances through steps `0..9999`, calls steps `10000` and `10001`, and asserts `complete_centerB`/`CenterB` then `complete_centerC`/`CenterC`.

Direct pytest execution from the detached checkout exited `1` before reaching those assertions because the detached checkout lacks non-versioned `data/benchmarks/protocol/cases_MyoPS.json`. To avoid reading the mutable main worktree or outer data, I also ran an in-memory reviewer probe that monkeypatched the sampler data loaders with actual-train CenterB/CenterC rows. That probe passed and selected:

- step `10000`: `complete_centerB`, `CenterB`
- step `10001`: `complete_centerC`, `CenterC`

## Known-Bad Validator

PASS. Independent detached rerun:

```bash
PYTHONDONTWRITEBYTECODE=1 /users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/validation/validate_care_ase_r2_g1.py --output-dir /tmp/care_ase_r2_r1_g1_rereview02_validator_probe
```

Result: exit `0`, `decision: PASS`, `failures: []`.

The regenerated `/tmp` known-bad report has:

- `required_known_bad_count`: `31`
- `known_bad_count_passed`: `31`
- nonzero fixture exits: `31`
- `REJECTED_AS_EXPECTED`: `31`
- failed rows: `[]`

## Regression Check

No regression found in formal wrapper, entrypoint, model, target builder, sampler contract, loss, optimizer groups, scheduler, checkpoint save/resume, evaluator, or decode static coverage. Static receipts for call chain, coverage, semantic loss, sampler, scheduler, and checkpoint remain PASS. Source SHA changes versus the prior accepted R1 candidate are limited to the sampler source and regenerated evidence receipts.
