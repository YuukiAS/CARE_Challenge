# Result 20260704 SRR-v2.5 Anti-Laziness Acceptance Tests

status: `EXECUTED_UNAUDITED`
self_assessed_status: `PASS_VALIDATOR_IMPLEMENTED_CURRENT_CODE_NEEDS_REVISION`
domain_evidence_label: `PREFLIGHT_SMOKE_ONLY`

## Summary

Implemented the SRR-v2.5 anti-laziness validator under
`scripts/validation/validate_srr_v25_anti_laziness.py` and added CPU unit tests
under `src/care_myocardium/tests/test_srr_v25_anti_laziness_validator.py`.

The validator detects at least the three required known failure modes:

- unused prototype-bank utility / loader not called by formal runtime;
- exact required filename mismatch rather than accepting similar filenames;
- implementation claims unsupported by concrete runtime or source evidence.

It also detects missing baseline-preserving nnU-Net residual/gated correction
and unsafe prototype sources. Current code is therefore not declared complete by
this task.

## Files Changed

- `scripts/validation/validate_srr_v25_anti_laziness.py`
- `src/care_myocardium/tests/test_srr_v25_anti_laziness_validator.py`

## Commands

```bash
./envs/env_CARE/bin/python -m unittest src.care_myocardium.tests.test_srr_v25_anti_laziness_validator
```

Result: exit `0`, `Ran 4 tests`, `OK`.

```bash
./envs/env_CARE/bin/python scripts/validation/validate_srr_v25_anti_laziness.py \
  --repo-root . \
  --controller prompts/tasks/20260704_srr_v25_full_completion_goal.md \
  --results-root results \
  --json
```

Result: exit `0`; current scan reported open SRR-v2.5 issues as expected.

## Current Open Issues From Validator

- `UTILITY_ONLY_NOT_CALLED`
- `PROTOTYPE_SOURCE_NOT_FINAL`
- `BASELINE_PRESERVING_GATE_MISSING`
- `CLAIM_WITHOUT_RUNTIME_EVIDENCE`

The no-T2 toy decode/export check imports and runs successfully.

## Next State

next_state: `EXECUTED_UNAUDITED`
