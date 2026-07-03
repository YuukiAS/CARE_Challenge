# MANIFEST: 20260703_srr_failure_audit

- Task: `prompts/tasks/20260703_srr_failure_audit.md`
- Result: `results/20260703_srr_failure_audit/result.md`
- Review: `results/20260703_srr_failure_audit/review.md` (not written by this executor; reserved for separate auditor)

| artifact | purpose |
| --- | --- |
| `result.md` | executor result with decision fields and evidence-indexed findings |
| `MANIFEST.md` | artifact index for this audit packet |
| `experiment_adequacy_report.md` | adequacy gate review of training budget, steps, validation, losses, logs, and same-split evidence |
| `checkpoint_policy_audit.md` | audit of `checkpoint_best`, `best_step=1`, `val_every`, and final-vs-best checkpoint policy |
| `decode_sanity_audit.md` | review of full-volume argmax decode, compact-label QC, empty rate, component/remote-FP burden, and missing pathology-aware decode evidence |
| `proposal_failure_audit.md` | review of proposal recall/precision, flooding, fixed-threshold limitation, and required PR sweep evidence |
| `required_revision_plan.md` | bounded next-step requirements before any future PropRef route-negative or promotion decision |

## Scope

This executor did not write `review.md`, did not train, did not run validation packaging, did not upload, did not expand folds, did not use network access, and did not commit or push.
