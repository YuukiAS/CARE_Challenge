# Anti-Laziness Report

Latest command:

```bash
./envs/env_CARE/bin/python scripts/validation/validate_srr_v25_anti_laziness.py \
  --repo-root . \
  --controller prompts/tasks/20260704_srr_v25_full_completion_goal.md \
  --results-root results \
  --json
```

Result: exit `0`, `error_count: 10`.

All current findings are legacy `CLAIM_WITHOUT_RUNTIME_EVIDENCE` issues in
older reports:

- `results/20260703_hardmode_goal/controller_report.md`
- `results/20260703_cine_temporal_resume/review.md`
- `results/20260704_myops_anchor_srr_fold0_formal/review.md`
- `results/20260703_srr_failure_audit/result.md`

The validator did not report new `UTILITY_ONLY_NOT_CALLED`,
`PROTOTYPE_SOURCE_NOT_FINAL`, or `BASELINE_PRESERVING_GATE_MISSING` blockers
for the current SRR-v2.5 packet.
