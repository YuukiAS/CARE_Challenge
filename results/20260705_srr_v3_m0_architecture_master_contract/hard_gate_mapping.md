# M0 Hard-Gate Mapping

status: `M0_READY_FOR_REVIEW`

## Gate Evidence

| gate | current evidence | M0 decision |
| --- | --- | --- |
| hard-gate repair review | `results/20260705_handoff_hard_gate_repair/review.md` contains `decision: AUDITED_GO` | `PASS` |
| current bad packet regression | `results/20260705_handoff_hard_gate_repair/current_bad_packet_regression.md`; live strict validator rerun exited `1` with `error_count: 18` | `PASS` |
| SRR-v2.5 evidence supplement | `results/20260705_srr_v25_evidence_supplement_audit/result.md` says `DIAGNOSTIC_ONLY_NEEDS_EVIDENCE` | `PASS_DIAGNOSTIC_INPUT` |
| missing evidence carried forward | `missing_evidence_and_next_questions.md` lists missing completion check, missing Cine temporal dictionary, 6-step checkpoints, empty edema prototypes, missing gate stats | `PASS_CARRIED_FORWARD` |
| milestone protocol | `prompts/MILESTONE_REVIEW_PROTOCOL.md` requires executor stop before review | `PASS` |

## Known Bad Packet Rerun

Command:

```bash
env PYTHONDONTWRITEBYTECODE=1 ./envs/env_CARE/bin/python scripts/validation/validate_srr_v25_anti_laziness.py --repo-root . --controller prompts/tasks/20260704_srr_v25_full_completion_goal.md --results-root results --json
```

Result: exit `1`, `error_count: 18`, `issue_count: 18`, `warning_count: 0`.

Required blocker codes observed:

- `REQUIRED_RESULT_DIR_MISSING`
- `CONTROLLER_REPORT_SUBTASK_MISSING`
- `TASK_GRAPH_RESULT_DIR_MISSING`
- `COMPLETION_CHECK_READINESS_MISSING`
- `SMOKE_SCALE_TRAINING_INADEQUATE`

## M0 Gate Consequence

Because hard-gate repair is audited and the known bad packet still fails strict validation, M0 may write an architecture contract and review request. M0 may not write `review.md`, may not mark `M0_AUDITED_GO`, and may not start M1.
