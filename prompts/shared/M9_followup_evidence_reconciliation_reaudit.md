# M9 Follow-up Evidence Reconciliation + Validator Re-audit Staging Prompt

This is a GPT-authored staging file for the post-M9 reviewer repair. It must be split by a later Codex maintenance step into `prompts/shared/EXECUTOR_PROMPTS.md` and `prompts/shared/REVIEWER_PROMPTS.md`, then deleted after the split/merge is verified.

This file is not M10. It is not route promotion, fold expansion, validation packaging, validation upload, hosted metric claim, leaderboard claim, or scientific stop. It exists because the independent M9 review returned `M9_AUDITED_NEEDS_REVISION` for evidence/validator inconsistency.

## Route Bootstrap Evidence

```yaml
previous_m9_result_path: "results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/result.md"
previous_m9_executor_state: "M9_READY_FOR_REVIEW"
previous_m9_executor_route_decision: "M9_NO_PROMOTION_DIAGNOSTIC_ONLY"
previous_m9_review_path: "results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/review.md"
previous_m9_review_decision: "M9_AUDITED_NEEDS_REVISION"
review_blocker_class: "evidence_state_and_validator_consistency"
staging_file: "prompts/shared/M9_followup_evidence_reconciliation_reaudit.md"
next_stage: "M9_FOLLOWUP_REAUDIT_BEFORE_ANY_M10"
```

M9 executor directionally supports no-promotion: the formal SRR-main candidates remain negative against the tracked M8 nnU-Net anchor, and Cine remains local proxy final-output evidence only. However, the independent reviewer found that the packet is not auditable because required tracked evidence files still contain pending/runtime-needed states while `completion_check.md` claims `M9_READY_FOR_REVIEW`. Therefore the next step is a bounded M9 follow-up repair and re-audit, not M10.

## Executor Prompt

You are the Codex executor/controller for exactly one bounded M9 follow-up milestone: reconcile M9 evidence state, harden the validator, rerun aggregation/validation, and prepare the packet for a separate read-only re-audit.

Required protocol sentence: This is an executor/controller session for one M9 follow-up only. Stop after writing completion_check.md and review_request.md, force-add/commit the lightweight required result files and validator/code changes, then stop. Do not push automatically. Do not write review.md and do not start M10. The packet must be reviewed by a separate read-only reviewer before any continuation.

### 1. Required reading before execution

Read these files before editing code or evidence:

```text
START_HERE_FOR_GPT.md
GPT_PLANNER_CARE_PROTOCOL.md
AGENTS.md
README.md
prompts/CHATGPT_RULES.md
prompts/GPT_HARD_GATE_PROMPT.md
prompts/MILESTONE_REVIEW_PROTOCOL.md
prompts/THREAD_BOOTSTRAP_ROUTE_IMAGE_PROTOCOL.md
prompts/shared/M9_followup_evidence_reconciliation_reaudit.md
prompts/shared/M9_srr_dictionary_fidelity_repair_training.md
results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/review.md
results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/result.md
results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/completion_check.md
results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/m9_route_promotion_decision.md
results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/m9_next_required_action.md
results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/m9_dictionary_fidelity_matrix.csv
results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/m9_code_patch_summary.md
results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/m9_rrl_brr2_adaptation_contract.md
results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/m9_nnunet_role_audit.md
results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/m9_pathology_specific_refiner_contract.md
results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/m9_prototype_memory_summary.json
results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/m9_strict_validator_report.md
results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/m9_validator_selftest_report.md
scripts/evaluation/aggregate_srr_v3_m9_dictionary_fidelity_packet.py
scripts/evaluation/validate_srr_v3_m9_dictionary_fidelity_packet.py
```

If `review.md` is missing or its decision is not `M9_AUDITED_NEEDS_REVISION`, write a blocked follow-up packet and stop. Do not infer from chat summaries.

### 2. Task identity and result policy

Continue using the M9 result directory:

```text
results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/
```

This follow-up repairs the existing M9 packet. Do not create a new route result directory unless the validator architecture requires temporary fixtures. Do not launch new long training. Do not submit new Slurm jobs unless a required runtime artifact is genuinely missing and the packet cannot be reconciled from terminal M9 runtime outputs. If any new Slurm job is unavoidable, it must be justified in `m9_followup_commands_run.md` and the packet must remain non-ready until terminal accounting and aggregation are complete.

### 3. Scientific and protocol interpretation

The executor must separate three questions:

1. Evidence consistency: can the M9 packet be made internally consistent and fail-closed?
2. Scientific direction: do current M9 metrics support no-promotion, undertraining, or evidence insufficiency?
3. Next planning state: should GPT plan M10, replan after no-promotion, request more evidence, or request implementation revision?

Do not collapse these questions. A validator repair does not make the route good. Negative metrics do not excuse stale pending evidence. A no-promotion executor direction is not an audited route-stop decision.

### 4. Required repairs

#### 4.1 Reconcile stale pending evidence

Replace or correct stale pending/runtime-needed statuses in the required tracked evidence files. At minimum inspect and reconcile:

```text
m9_dictionary_fidelity_matrix.csv
m9_code_patch_summary.md
m9_rrl_brr2_adaptation_contract.md
m9_nnunet_role_audit.md
m9_pathology_specific_refiner_contract.md
m9_prototype_memory_summary.json
m9_route_promotion_decision.md
m9_next_required_action.md
completion_check.md
result.md
```

If runtime evidence exists, update statuses from `PENDING_RUNTIME`, `PARTIAL_CODE_REPAIR_NEEDS_RUNTIME_EVIDENCE`, `PARTIAL_ONE_BATCH_PROTOTYPE_EVIDENCE_FORMAL_TRAINING_RUNNING`, `FORMAL_TRAINING_RUNNING`, or equivalent stale tokens to runtime-derived states with exact evidence paths.

If runtime evidence does not exist, do not mark ready. Set completion to `M9_FOLLOWUP_NEEDS_EVIDENCE` and explain the missing evidence.

Required matrix rows must be evidence-backed:

```text
true_br2_runtime_slot_usage
invalid_slot_mask_runtime
final_metric_causal_effect
prototype_memory_runtime_status
pathology_specific_refiner_runtime_status
cine_final_output_runtime_status
```

Each row must have a non-pending status and a concrete tracked evidence path. Do not invent evidence.

#### 4.2 Harden validator to scan all required evidence types

Update `scripts/evaluation/validate_srr_v3_m9_dictionary_fidelity_packet.py` so a ready packet fails closed when unresolved tokens appear anywhere in required Markdown, CSV, or JSON files, not just top-level Markdown.

The unresolved-token scan must include at least:

```text
PENDING_RUNTIME
PARTIAL_CODE_REPAIR_NEEDS_RUNTIME_EVIDENCE
PARTIAL_ONE_BATCH_PROTOTYPE_EVIDENCE_FORMAL_TRAINING_RUNNING
FORMAL_TRAINING_RUNNING
NEEDS_RUNTIME_EVIDENCE
RUNTIME_EVIDENCE_PENDING
SLURM JOBS PENDING
JOBS PENDING
AWAITING_SACCT
NEEDS_MONITOR
PENDING_MONITOR
JOB_SUBMITTED
PENDING_PRIORITY
RUNNING
not sufficient for M9_READY_FOR_REVIEW
```

A ready packet may contain historical narrative about these tokens only if the row is explicitly marked `HISTORICAL_NONREADY_STATE_RESOLVED` and the same file contains the final resolved runtime status and evidence path. Simpler is better: remove stale non-ready language from final packet files.

#### 4.3 Add validator known-bad self-tests for this exact failure

Add known-bad fixtures that must fail closed:

```text
stale_pending_runtime_in_dictionary_fidelity_matrix
stale_partial_code_repair_in_code_patch_summary
stale_partial_brr2_contract_pending_runtime
stale_nnunet_controls_need_post_job_rows
stale_pathology_refiner_pending_runtime
stale_formal_training_running_in_prototype_memory_json
ready_packet_with_csv_pending_runtime_token
ready_packet_with_json_running_token
```

The self-test report must show one good fixture passes and all known-bad fixtures fail. If any known-bad mutation passes, completion must be `M9_FOLLOWUP_NEEDS_REVISION_VALIDATOR_NOT_FAIL_CLOSED`.

#### 4.4 Re-run post-job aggregation if necessary

If the tracked evidence can be refreshed from existing terminal runtime roots, rerun the M9 aggregator. Record the exact command, exit status, runtime roots, and changed files. Do not alter metrics by hand except to repair stale status text that clearly contradicts existing runtime-derived evidence. If metric tables are regenerated, cite the runtime source paths.

#### 4.5 Produce a follow-up reconciliation report

Add these lightweight files to the existing result directory:

```text
m9_followup_reconciliation_report.md
m9_followup_stale_status_scan.csv
m9_followup_validator_repair_summary.md
m9_followup_reaudit_request.md
m9_followup_commands_run.md
```

`m9_followup_reconciliation_report.md` must state whether the corrected packet is:

```text
M9_FOLLOWUP_READY_FOR_REAUDIT
M9_FOLLOWUP_NEEDS_EVIDENCE
M9_FOLLOWUP_NEEDS_REVISION
M9_FOLLOWUP_NEEDS_MONITOR
```

`m9_followup_stale_status_scan.csv` must include one row per scanned file with fields:

```text
file_path, scanned_type, unresolved_token_count, unresolved_tokens, final_status, action_taken
```

`m9_followup_validator_repair_summary.md` must explain the validator bug and the new fail-closed behavior.

`m9_followup_reaudit_request.md` must request independent re-audit and explicitly state that the executor did not write review.md or start M10.

#### 4.6 Scientific interpretation after reconciliation

After the packet is internally consistent, write a short but explicit scientific interpretation in `m9_route_promotion_decision.md` and `m9_next_required_action.md`.

Allowed route decisions:

```text
M9_NO_PROMOTION_DIAGNOSTIC_ONLY
M9_NEEDS_EVIDENCE
M9_NEEDS_REVISION
M9_SCIENTIFIC_UNDERTRAINED
M9_NEEDS_MONITOR
```

Do not write route promotion. Based on the current M9 metrics, the likely decision remains `M9_NO_PROMOTION_DIAGNOSTIC_ONLY`, but this must be supported by reconciled evidence.

Allowed next actions:

```text
GPT_REPLAN_AFTER_M9_NO_PROMOTION
NEEDS_EVIDENCE_BEFORE_NEXT_TASK
NEEDS_REVISION_BEFORE_REVIEW
NEEDS_MONITOR
GPT_PLAN_M10_AFTER_AUDITED_REVIEW_ONLY
```

Do not select `GPT_PLAN_M10_AFTER_AUDITED_REVIEW_ONLY` unless the separate reviewer later audits the corrected packet. The executor should normally stop at `GPT_REPLAN_AFTER_M9_NO_PROMOTION` or a non-ready state.

### 5. Completion states

Allowed executor completion states:

```text
M9_FOLLOWUP_READY_FOR_REAUDIT
M9_FOLLOWUP_NEEDS_EVIDENCE
M9_FOLLOWUP_NEEDS_REVISION
M9_FOLLOWUP_NEEDS_MONITOR
M9_FOLLOWUP_RESOURCE_BLOCKED
M9_FOLLOWUP_BLOCKED_PREREQUISITE_REVIEW_MISSING
```

`M9_FOLLOWUP_READY_FOR_REAUDIT` requires:

1. reviewer blocker files reconciled or packet marked non-ready;
2. validator scans required Markdown/CSV/JSON for stale unresolved states;
3. validator real-packet pass with `error_count=0`;
4. self-tests include the exact stale-pending known-bad fixtures and all fail closed;
5. completion_check.md no longer conflicts with tracked evidence;
6. no validation packaging/upload/hosted claim/fold expansion/M10.

### 6. Git and artifact policy

Commit only first-party validator/aggregator changes and lightweight Markdown/CSV/JSON result files. Do not commit checkpoints, predictions, NIfTI files, upload zips, raw data, large logs, secrets, or full runtime trees.

Recommended local commit command:

```bash
git add -f \
  scripts/evaluation/aggregate_srr_v3_m9_dictionary_fidelity_packet.py \
  scripts/evaluation/validate_srr_v3_m9_dictionary_fidelity_packet.py \
  results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/*.md \
  results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/*.csv \
  results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/*.json
git commit -m "Repair M9 evidence reconciliation and validator"
```

Do not push automatically.

## Reviewer Prompt

You are the separate read-only reviewer/auditor for the M9 follow-up evidence reconciliation and validator re-audit.

Required protocol sentence: This is a separate read-only reviewer/auditor session. Do not fix code, do not generate missing artifacts, do not train, and do not start M10. Review only the completed M9 follow-up packet, write review.md with the controlled decision, then force-add/commit review.md. Do not push automatically.

### 1. Review scope

Review:

```text
prompts/shared/M9_followup_evidence_reconciliation_reaudit.md
results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/review.md
results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/result.md
results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/completion_check.md
results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/m9_dictionary_fidelity_matrix.csv
results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/m9_code_patch_summary.md
results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/m9_rrl_brr2_adaptation_contract.md
results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/m9_nnunet_role_audit.md
results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/m9_pathology_specific_refiner_contract.md
results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/m9_prototype_memory_summary.json
results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/m9_followup_reconciliation_report.md
results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/m9_followup_stale_status_scan.csv
results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/m9_followup_validator_repair_summary.md
results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/m9_followup_reaudit_request.md
scripts/evaluation/validate_srr_v3_m9_dictionary_fidelity_packet.py
scripts/evaluation/aggregate_srr_v3_m9_dictionary_fidelity_packet.py
```

You may read other M9 evidence files as needed to verify source paths and metrics.

### 2. Required review checks

Check that the executor did not start M10, fold expansion, validation packaging, validation upload, or hosted metric claiming.

Check that the previous reviewer blockers are resolved or the packet is explicitly non-ready. The following exact stale states must not remain in ready evidence:

```text
PENDING_RUNTIME
PARTIAL_CODE_REPAIR_NEEDS_RUNTIME_EVIDENCE
PARTIAL_ONE_BATCH_PROTOTYPE_EVIDENCE_FORMAL_TRAINING_RUNNING
FORMAL_TRAINING_RUNNING
Slurm jobs pending
not sufficient for M9_READY_FOR_REVIEW
```

Check `m9_followup_stale_status_scan.csv`. It must scan Markdown, CSV, and JSON files. If it scans only Markdown, return needs revision.

Check `m9_dictionary_fidelity_matrix.csv`. The rows for true-BR2 runtime slot usage, invalid-slot mask runtime, and final metric causal effect must be backed by actual runtime-derived evidence paths or the packet must be non-ready.

Check `m9_prototype_memory_summary.json`. A ready packet cannot retain `PARTIAL_ONE_BATCH_PROTOTYPE_EVIDENCE_FORMAL_TRAINING_RUNNING` or equivalent.

Check the validator. It must fail ready packets with stale unresolved tokens in Markdown, CSV, and JSON files. Known-bad self-tests must include stale pending/runtime states in the exact M9 evidence files and must fail closed.

Check the science separately from protocol. If the packet is consistent and current metrics remain negative, the audited decision may acknowledge directionally supported no-promotion. Do not let negative metrics excuse unresolved evidence.

### 3. Review decisions

Write `results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/review.md` with exactly one of:

```text
M9_FOLLOWUP_AUDITED_READY_NO_PROMOTION_DIAGNOSTIC_ONLY
M9_FOLLOWUP_AUDITED_NEEDS_EVIDENCE
M9_FOLLOWUP_AUDITED_NEEDS_REVISION
M9_FOLLOWUP_AUDITED_NEEDS_MONITOR
M9_FOLLOWUP_AUDITED_PROTOCOL_BLOCKED
```

`M9_FOLLOWUP_AUDITED_READY_NO_PROMOTION_DIAGNOSTIC_ONLY` means only this: M9 is now internally consistent and its no-promotion diagnostic direction is auditable. It does not authorize route promotion, validation packaging/upload, hosted metric claims, fold expansion, scientific stop, or automatic M10 execution. GPT/user must decide any future M10 design separately.

Use `M9_FOLLOWUP_AUDITED_NEEDS_EVIDENCE` if required runtime evidence is still missing or stale status rows remain unreconciled.

Use `M9_FOLLOWUP_AUDITED_NEEDS_REVISION` if validator scanning, self-tests, evidence reconciliation, or completion-state logic remains broken.

Use `M9_FOLLOWUP_AUDITED_NEEDS_MONITOR` only if genuinely running/pending jobs are required and not terminal.

Use `M9_FOLLOWUP_AUDITED_PROTOCOL_BLOCKED` if the executor wrote review.md, started M10, packaged/uploaded validation, claimed hosted metrics, or altered route conclusions beyond the bounded reconciliation task.

### 4. Commit policy

Commit only the review file:

```bash
git add -f results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/review.md
git commit -m "Add M9 follow-up evidence reconciliation review"
```

Do not push automatically.
