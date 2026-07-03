# Result 20260703 SRR Failure Audit

self_assessed_status: EXECUTED_UNAUDITED
experiment_adequacy_decision: FAIL
route_promotion_decision: NO_PROMOTION
route_negative_decision: STOP_NOT_SUPPORTED
scientific_resolution_status: SCIENTIFIC_UNDERTRAINED
recommended_next_state: NEEDS_REVISION
role: executor
review_required: true

## Execution Summary

I audited the previous `results/20260703_myops_srr_propose_refine/` packet and the code paths that produced it. The prior `STOP_NO_PROPREF_SIGNAL` is not scientifically supported under the current CARE adequacy gates. The evidence supports an undertrained and checkpoint-policy-limited result requiring bounded revision before any route stop or promotion decision.

No network, upload, training, validation packaging, fold expansion, git commit, or git push was performed. This executor stops at `EXECUTED_UNAUDITED`; `review.md` is reserved for a separate auditor.

## Evidence-Indexed Findings

claim.experiment_adequacy_fails: The formal runs used `max_steps=120`, logged only step `1`, `50`, and `100` training rows plus a step-1 validation row, reported train-loop times of `6.02`, `6.05`, and `29.66` seconds, and do not record explicit `actual_steps`, `optimizer_steps`, or `validation_events` keys in `summary.json`.

- Evidence: `results/20260703_myops_srr_propose_refine/result.md:21-25`; `results/20260703_myops_srr_propose_refine/variants/*/summary.json`; `results/20260703_myops_srr_propose_refine/variants/*/training_log.csv`; `experiment_adequacy_report.md`.

claim.checkpoint_best_is_step1: All three variants record `best_step: 1`. Code validates at step 1 and then every `val_every`; the default `val_every=300` exceeds the formal `max_steps=120`, so no post-warmup validation could replace the step-1 checkpoint.

- Evidence: `scripts/training/run_srr_propref_myops_fold0.py:519-537`; `scripts/training/run_srr_propref_myops_fold0.py:592-593`; `results/20260703_myops_srr_propose_refine/training_schedule.md:22-26`; `checkpoint_policy_audit.md`.

claim.predictions_use_step1_best_checkpoint: Evaluation loads `checkpoint_best` if present and writes predictions under `predictions/fold_0/checkpoint_best`. No same-run `checkpoint_final` prediction/metric comparison was found.

- Evidence: `scripts/training/run_srr_propref_myops_fold0.py:541-549`; `results/20260703_myops_srr_propose_refine/variant_matrix.csv`; `checkpoint_policy_audit.md`.

claim.loss_decrease_not_supported: Logged training loss increased from first to last logged row for all variants: `2.713 -> 4.196`, `2.968 -> 4.280`, and `2.586 -> 3.797`.

- Evidence: `results/20260703_myops_srr_propose_refine/variants/*/training_log.csv`; `experiment_adequacy_report.md`.

claim.logs_provenance_partial: Slurm accounting, configs, checkpoints, predictions, and metrics exist, but the configured tee logs are zero bytes and are explicitly marked `evidence not found`.

- Evidence: `results/20260703_myops_srr_propose_refine/provenance_reconciliation.md:46-56`; `results/20260703_myops_srr_propose_refine/command_transcript.md:68-78`.

claim.proposal_failure_is_real_but_not_route_negative: Proposal precision is near zero at fixed threshold `0.50`; outside-myocardium FP ratio is around `0.95-0.97`; no PR/threshold sweep was found. This supports a repair diagnosis, not a scientific stop, because the training/checkpoint evidence is inadequate.

- Evidence: `results/20260703_myops_srr_propose_refine/proposal_metrics.csv`; `scripts/training/run_srr_propref_myops_fold0.py:260-299`; `proposal_failure_audit.md`.

claim.decode_sanity_partial: The model did not simply predict all background; subgroup empty prediction rates are `0.0`. The final argmax decode produced near-zero Dice with many components and remote FPs, while pathology-aware decode alternatives and checkpoint-specific decode comparisons are evidence not found.

- Evidence: `scripts/training/run_srr_propref_myops_fold0.py:227-250`; `results/20260703_myops_srr_propose_refine/subgroup_metrics.csv`; `decode_sanity_audit.md`.

claim.same_split_baseline_present_but_not_sufficient: Same-split nnU-Net fold0 references exist (`scar all-case Dice 0.5602`, `edema GT-positive Dice 0.3944`), but the PropRef experiment is too undertrained and checkpoint-limited to support a route-negative stop against that baseline.

- Evidence: `results/20260703_myops_srr_propose_refine/metrics_summary.md:3-12`; `prompts/EXPERIMENT_ADEQUACY_GATE.md:56-73`.

## Files Read

- `AGENTS.md`
- `prompts/AGENT_RULES.md`
- `prompts/HANDOFF_STATE_MACHINE.md`
- `prompts/EXPERIMENT_ADEQUACY_GATE.md`
- `prompts/DIAGNOSTIC_PUBLICATION_GATE.md`
- `prompts/CONTROLLER_TASK_PROTOCOL.md`
- `prompts/CARE_OVERLAY_GATES.md`
- `.agents/skills/agent-task-executor/SKILL.md`
- `.agents/skills/domains-medical-imaging-medical-imaging-deep-learning/SKILL.md`
- `.agents/skills/domains-medical-imaging-medical-imaging-deep-learning/references/reference.md`
- `prompts/tasks/20260703_srr_failure_audit.md`
- required prior packet files under `results/20260703_hardmode_goal/` and `results/20260703_myops_srr_propose_refine/`
- `src/care_myocardium/models/srr_propref.py`
- `scripts/training/run_srr_propref_myops_fold0.py`
- `scripts/evaluation/aggregate_srr_propref_20260703.py`
- `jobs/src/run_srr_propref_myops_fold0.sh`

## Files Written

- `results/20260703_srr_failure_audit/result.md`
- `results/20260703_srr_failure_audit/MANIFEST.md`
- `results/20260703_srr_failure_audit/experiment_adequacy_report.md`
- `results/20260703_srr_failure_audit/checkpoint_policy_audit.md`
- `results/20260703_srr_failure_audit/decode_sanity_audit.md`
- `results/20260703_srr_failure_audit/proposal_failure_audit.md`
- `results/20260703_srr_failure_audit/required_revision_plan.md`

## Commands Run

- Local read-only inspection with `sed`, `nl`, `rg`, `ls`, and structured Python CSV/JSON summarization.
- `mkdir -p results/20260703_srr_failure_audit`
- No training, network, upload, validation packaging, fold expansion, git commit, or git push.

## Required Next Action

Route this to a bounded `20260703_srr_propref_repair` task or equivalent GPT-planned revision. The repair must fix checkpoint/validation policy, record explicit training counters, run one-case or one-batch overfit sanity, use a materially effective fold0 training budget, add proposal PR sweeps, and compare best/final/pathology-aware decode outputs before any future stop claim.
