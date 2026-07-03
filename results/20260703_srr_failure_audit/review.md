# Review 20260703 SRR Failure Audit

audit_decision: AUDITED_DIAGNOSTIC_PUBLISH
claim_audit_decision: SUPPORTED
experiment_adequacy_decision: FAIL
route_promotion_decision: NO_PROMOTION
route_negative_decision: STOP_NOT_SUPPORTED
scientific_resolution_status: SCIENTIFIC_UNDERTRAINED
recommended_next_state: NEEDS_REVISION
srr_repair_may_proceed: YES_BOUNDED_REPAIR_ONLY
role: separate read-only auditor
audited_task: `prompts/tasks/20260703_srr_failure_audit.md`
audited_result: `results/20260703_srr_failure_audit/result.md`

## Audit Scope

I reviewed the executor packet under `results/20260703_srr_failure_audit/` against the task, handoff rules, CARE overlay gates, medical-imaging deep-learning evidence standard, and the referenced prior SRR-ProposeRefine evidence. I did not edit code, generate missing artifacts, train, upload, package validation, expand folds, commit, or push.

## Claim Ledger

| claim | status | audit finding |
| --- | --- | --- |
| `experiment_adequacy_decision: FAIL` | SUPPORTED | The prior formal runs used `max_steps=120`, logged only steps `1`, `50`, and `100` plus a step-1 validation row, had `best_step=1`, and reported train-loop seconds `6.05`, `6.02`, and `29.66`. The executor correctly classifies this as inadequate for a route-negative scientific stop. |
| `route_negative_decision: STOP_NOT_SUPPORTED` | SUPPORTED | The task and gates require adequacy before accepting `STOP_NO_PROPREF_SIGNAL`. Because the run is undertrained and checkpoint-best is step 1, the old stop is not supported even though final metrics are very poor. |
| `scientific_resolution_status: SCIENTIFIC_UNDERTRAINED` | SUPPORTED | The evidence points to insufficient optimization/checkpoint policy rather than an adequately trained route failure. |
| `recommended_next_state: NEEDS_REVISION` | SUPPORTED | The required revision plan is bounded and tied to missing adequacy evidence: explicit counters, valid validation cadence, final/best checkpoint comparison, overfit sanity, PR sweeps, and decode sanity. |
| checkpoint-best selected at step 1 | SUPPORTED | `summary.json` for all three variants records `best_step: 1`; the runner validates at step 1 and then every `val_every`, with default `val_every=300`, while formal configs used `max_steps=120`. |
| predictions evaluated from `checkpoint_best` | SUPPORTED | The runner loads `checkpoint_best` when present and evaluates into `predictions/fold_0/checkpoint_best`; no same-run `checkpoint_final` metric comparison was found. |
| loss decrease not supported | SUPPORTED | Training logs show increasing logged loss from first to last training row for all variants, matching the executor's table. |
| proposal failure exists but is not route-negative evidence | SUPPORTED | Proposal precision is near zero and outside-myocardium FP ratio is high, but only threshold `0.50` is represented and the run is undertrained/step-1-best. This supports repair, not scientific stop. |
| decode sanity is partial rather than all-background collapse | SUPPORTED | Subgroup rows report `empty_prediction_rate: 0.0`; the observed failure is noisy non-empty pathology output with near-zero Dice, many components, and remote FP burden. |
| same-split baseline present but not sufficient | SUPPORTED | nnU-Net fold0 references are present, but route-negative use is blocked by the failed adequacy gate. |

## Evidence Coverage

- Gate requirements: `prompts/EXPERIMENT_ADEQUACY_GATE.md` requires train-loop seconds, steps, optimizer steps, validation events, loss decrease, prediction/proposal sanity, provenance, and same-split baseline before route-negative conclusions; `prompts/CARE_OVERLAY_GATES.md` rejects seconds-scale or very short runs as stop evidence.
- Executor decision fields: `results/20260703_srr_failure_audit/result.md:3-8` states the exact decisions under audit; `result.md:20-50` indexes the main claims and evidence.
- Adequacy details: `experiment_adequacy_report.md:8-32` supports `FAIL` with short train-loop seconds, missing explicit counters, step-1-only validation evidence, no loss decrease, no overfit sanity, partial proposal evidence, and zero-byte tee logs.
- Checkpoint policy: `checkpoint_policy_audit.md:7-24` supports `NEEDS_REVISION` and `STOP_NOT_SUPPORTED`; runner code validates/saves best at `scripts/training/run_srr_propref_myops_fold0.py:519-537`, reloads best before evaluation at `541-549`, and defaults to `val_every=300` at `592-593`.
- Formal run settings: `results/20260703_myops_srr_propose_refine/training_schedule.md:22-26` records `max_steps=120`, log rows at step 1/every 50, validation every 300, and no logged low-LR row.
- Decode/proposal evidence: `decode_sanity_audit.md:7-35` and `proposal_failure_audit.md:7-43` cover the non-empty noisy decode and fixed-threshold proposal failure.
- Prior conflicting stop review: `results/20260703_myops_srr_propose_refine/review.md:3-22` supported `STOP_NO_PROPREF_SIGNAL`, but that review accepted artifact/provenance completeness and poor metrics; it did not satisfy the newer/current adequacy-gate question posed by this task.

## Contradictions Or Caveats

- The prior SRR re-review recommends `STOP_NO_PROPREF_SIGNAL`, while this failure audit rejects that stop. This is a decision conflict, not a raw-evidence conflict: the same raw facts include fold0 metrics, checkpoints, and predictions, but the current task applies the adequacy and route-negative gates more strictly.
- `scripts/evaluation/aggregate_srr_propref_20260703.py` still contains stale generated wording that would claim low-LR calibration rows are recorded if rerun; the current checked artifacts corrected that wording. This is a reproducibility caveat, not a blocker for this audit decision.
- The evidence does not prove a pure decode bug. It proves the stop decision is premature because undertraining/checkpoint policy and incomplete proposal/decode evidence remain plausible explanations.

## Audit Decision

The executor's requested decisions are supported:

- `experiment_adequacy_decision=FAIL`
- `route_negative_decision=STOP_NOT_SUPPORTED`
- `scientific_resolution_status=SCIENTIFIC_UNDERTRAINED`
- `recommended_next_state=NEEDS_REVISION`

SRR repair may proceed only as a bounded GPT-planned revision task. It must not proceed as route promotion, validation packaging, validation upload, fold expansion, hosted metric claim, or next-stage broad training from the old `STOP_NO_PROPREF_SIGNAL`.
