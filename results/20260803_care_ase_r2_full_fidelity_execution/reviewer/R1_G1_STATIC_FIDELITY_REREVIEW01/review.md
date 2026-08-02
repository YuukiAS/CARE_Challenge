# R1 G1 Static Fidelity Rereview 01

Decision: PASS_CONTINUE

Candidate: `7ab4a2511b9e319363e2bb59d41f34518aebe8e2`

Reviewer session: `019fc386-dba4-7b72-a29f-06a657b4fc5f`

Effective contract SHA256: `b3ea5986b7a2458f758f7353ab023cea85a9cb67a6fb7c7bf12e5bc10e61d09c`

## Scope Reviewed

Reviewed only the immutable detached checkout:

`/users/a/e/aereinh/CARE_reviewers/care_ase_r2/R1_G1_STATIC_FIDELITY_REREVIEW01/7ab4a2511b9e319363e2bb59d41f34518aebe8e2`

and the specified controller submission:

`/users/a/e/aereinh/CARE/results/20260803_care_ase_r2_full_fidelity_execution/reviewer/R1_G1_STATIC_FIDELITY_REREVIEW01/controller_submission.json`

No main mutable worktree review or modification was performed. No fold1/fold4 outer data were read.

## R1-G1-F001 Repair Verdict

PASS. The repaired G1 validator now exposes `--known-bad-fixture`, constructs 31 known-bad fixture IDs, executes each fixture through a subprocess command array, records the actual exit code in `validator_exit_if_mutated`, records `observed_decision`, `stdout_tail`, and `stderr_tail`, and requires every fixture to return nonzero with `REJECTED_AS_EXPECTED`.

Independent detached rerun:

```bash
PYTHONDONTWRITEBYTECODE=1 /users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/validation/validate_care_ase_r2_g1.py --output-dir /tmp/care_ase_r2_r1_g1_rereview01_validator_probe
```

Result: validator exit `0`, `decision: PASS`, `failures: []`.

Regenerated known-bad summary from `/tmp/care_ase_r2_r1_g1_rereview01_validator_probe/known_bad_validator_report.json`:

- `status`: `PASS`
- `required_known_bad_count`: `31`
- `known_bad_count_passed`: `31`
- nonzero fixture exits: `31`
- `REJECTED_AS_EXPECTED`: `31`
- failed rows: `[]`

## Regression Check

No regression found in formal wrapper, formal entrypoint, model, target builder, sampler, loss, optimizer/scheduler, checkpoint save/resume, evaluator, or decode static coverage. The source SHA review confirms the prior implementation files are unchanged except for the repaired G1 validator. Static evidence files for call chain, coverage, semantic loss, sampler, scheduler, and checkpoint remain PASS.
