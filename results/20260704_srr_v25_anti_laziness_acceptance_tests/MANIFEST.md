# MANIFEST: 20260704_srr_v25_anti_laziness_acceptance_tests

task_source: `prompts/tasks/20260704_srr_v25_anti_laziness_acceptance_tests.md`
result: `results/20260704_srr_v25_anti_laziness_acceptance_tests/result.md`
review: `results/20260704_srr_v25_anti_laziness_acceptance_tests/review.md` (not yet created)

## Artifacts

- `validator_manifest.md` - validator implementation and CLI.
- `claim_to_runtime_trace.md` - claim evidence policy and current findings.
- `unused_utility_scan.md` - utility-only prototype findings.
- `unit_test_report.md` - unit test command/result.
- `forbidden_substitute_report.md` - forbidden substitute coverage.
- `result.md` - executor self-assessment.

## Code

- `scripts/validation/validate_srr_v25_anti_laziness.py`
- `src/care_myocardium/tests/test_srr_v25_anti_laziness_validator.py`

## Boundary

No training, validation packaging, upload, commit, or push was performed.
