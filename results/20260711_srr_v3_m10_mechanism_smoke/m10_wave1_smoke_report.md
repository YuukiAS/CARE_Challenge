# M10 Wave 1 Mechanism Smoke

status: `READY_FOR_CONTROLLER_MERGE`

## Commands

- `./envs/env_CARE/bin/python -m pytest -q src/care_myocardium/tests/test_srr_v3_m10_fidelity.py`
  - result: `5 passed in 58.29s`
- `./envs/env_CARE/bin/python -m py_compile src/care_myocardium/models/srr_blocks.py src/care_myocardium/models/srr_spatial_dictionary.py src/care_myocardium/models/srr_dictionary_memory.py src/care_myocardium/models/srr_propref.py src/care_myocardium/losses/srr_losses.py src/care_myocardium/tests/test_srr_v3_m10_fidelity.py`
  - result: exit `0`
- `./envs/env_CARE/bin/python -m pytest -q src/care_myocardium/tests/test_srr_v3_m10_fidelity.py src/care_myocardium/tests/test_srr_dictionary_bank.py src/care_myocardium/tests/test_srr_losses.py src/care_myocardium/tests/test_srr_runtime_prototype_bank.py`
  - result: `15 passed, 3 warnings in 2.42s`
- `git diff --check -- <wave1 allowed source/config/test files>`
  - result: exit `0`

## Known-Bad / Guard Checks

- T2-private and T2-interaction slots are asserted invalid when T2 is absent.
- Invalid T2-dependent expert outputs are zero.
- Invalid T2-dependent spatial gate weights are zero.
- Invalid T2-dependent expert gradients are zero.
- Pattern-SIP is tested as non-identical to semantic retrieval loss.
- No-T2 edema memory updates are rejected with accepted count zero.
- No-T2 M10 final edema probability is exactly zero.

## Non-Blocking External Observation

The broader compatibility command including
`src/care_myocardium/tests/test_srr_proposal_prototypes.py` produced two
failures in `scripts/training/run_srr_propref_myops_fold0.py` because existing
test fixtures call `propref_loss` without `args.variant`. That script is outside
the wave 1 write scope and was not modified.
