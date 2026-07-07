# 20260707 M7 follow-up3: completion-safe re-aggregation and temporal dictionary repair prompt

status: `NEW_SHARED_PROMPT_FOR_EXECUTOR_AND_REVIEWER`
source_result_dir: `results/20260705_srr_v3_m7_training_and_cine_utilization/`
source_review_decision: `M7_FOLLOWUP2_AUDITED_NEEDS_EVIDENCE`
planner: `ChatGPT/GPT thread`
intended_merge_target:
  - `prompts/shared/EXECUTOR_PROMPTS.md`
  - `prompts/shared/REVIEWER_PROMPTS.md`

## 0. Why follow-up3 exists

M7 follow-up3 remains M7. It is not M8, not route promotion, not validation packaging/upload, not a hosted metric claim, not challenge submission, not fold expansion, not scientific stop, and not leaderboard readiness.

Follow-up3 only repairs two hard follow-up2 problems:

1. The follow-up2 executor committed a monitor packet as if it were a reviewable completion packet. The tracked packet still contained `M7_FOLLOWUP2_NEEDS_MONITOR` / `PENDING_MONITOR` evidence after submitting Slurm job `58021931`, while live Slurm accounting later showed that the job completed successfully.
2. Cine follow-up2 produced at least one registration row with `usable_for_temporal_dictionary=True`, but temporal dictionary execution did not happen and `temporal_dictionary_evidence.csv` contained `TEMPORAL_DICTIONARY_FOLLOWUP2_REQUIRED_NOT_EXECUTED`.

Follow-up3 must not execute a new M7 scientific direction. It must convert the completed follow-up2 runtime outputs into tracked lightweight evidence, close the temporal dictionary gate, and make it impossible to treat a monitor packet as completion.

---

# 1. Executor prompt: M7 follow-up3 completion-safe re-aggregation and temporal dictionary repair

```text
只执行 M7 follow-up3：completion-safe re-aggregation and temporal dictionary repair after `M7_FOLLOWUP2_AUDITED_NEEDS_EVIDENCE`.

Scope:

- This is still M7.
- It is not M8.
- It is not route promotion.
- It is not validation packaging/upload.
- It is not a hosted metric claim.
- It is not challenge submission.
- It is not fold expansion.
- It is not scientific stop.
- It is not leaderboard readiness.
- Do not train a new route unless the already-submitted follow-up2 probe must be re-aggregated from completed runtime outputs.
- Do not write `review.md`.
- Do not push.

Start gates:

- `results/20260705_srr_v3_m7_training_and_cine_utilization/review.md` must exist and contain `M7_FOLLOWUP2_AUDITED_NEEDS_EVIDENCE`.
- `results/20260705_srr_v3_m6_myops_concrete_architecture_repair/review.md` must exist and contain `M6_AUDITED_GO`.
- If either prerequisite is missing, write `M7_FOLLOWUP3_BLOCKED_BY_REVIEW_STATE` or `M7_BLOCKED_BY_M6` and stop.

Must read before edits:

- `results/20260705_srr_v3_m7_training_and_cine_utilization/review.md`
- `results/20260705_srr_v3_m7_training_and_cine_utilization/result.md`
- `results/20260705_srr_v3_m7_training_and_cine_utilization/completion_check.md`
- `results/20260705_srr_v3_m7_training_and_cine_utilization/followup2_training_adequacy.csv`
- `results/20260705_srr_v3_m7_training_and_cine_utilization/commands_run.md`
- `results/20260705_srr_v3_m7_training_and_cine_utilization/registration_same_subset_matrix.csv`
- `results/20260705_srr_v3_m7_training_and_cine_utilization/temporal_dictionary_evidence.csv`
- runtime output path and logs for Slurm job `58021931` or any explicitly superseding job
- `prompts/shared/EXECUTOR_PROMPTS.md`
- `prompts/shared/REVIEWER_PROMPTS.md`
- `prompts/MILESTONE_REVIEW_PROTOCOL.md`
- `prompts/HANDOFF_GATE_POLICY.md`
- `prompts/GPT_HARD_GATE_PROMPT.md`

## A. Monitor packet is not completion

Executor must read and report:

- `completion_check.md`
- `followup2_training_adequacy.csv`
- `commands_run.md`
- Slurm job id, normally `58021931`
- `sacct` or equivalent Slurm completion record
- active queue state if still visible in `squeue`
- runtime output path / logs
- whether the tracked follow-up2 packet already contains re-aggregated job-completion outputs

Required Slurm checks:

```bash
squeue -j 58021931 -o '%i|%P|%j|%T|%M|%l|%R'
sacct -j 58021931 --format=JobID,JobName,Partition,State,Elapsed,ExitCode,Start,End -P
```

If `completion_check.md` is `M7_FOLLOWUP2_NEEDS_MONITOR`, or `followup2_training_adequacy.csv` still contains `PENDING_MONITOR`, or `commands_run.md` only shows submitted/pending job state without completed-job aggregation outputs, the packet is not reviewable. It must not be marked ready. Executor must first re-aggregate the completed job results, or write a non-ready follow-up3 state.

If the job is pending/running/unresolved, write `M7_FOLLOWUP3_NEEDS_MONITOR`. Do not write a normal review request. If a monitor packet is committed, `review_request.md` must say `DO_NOT_REVIEW_MONITOR_PACKET`.

## B. Completed Slurm job re-aggregation

If Slurm job `58021931` or a clearly documented superseding job completed with exit code `0:0`, executor must:

1. Find the job runtime outputs and logs.
2. Re-run or invoke the M7 follow-up2 aggregator against the completed runtime outputs.
3. Aggregate runtime outputs into tracked lightweight files.
4. Remove stale monitor placeholders from tracked follow-up2 files.
5. Record job id, job state, exit code, runtime seconds, output/log path, aggregation command, and aggregation exit code.

Required updated tracked files:

- `result.md`
- `completion_check.md`
- `followup2_training_adequacy.csv`
- `followup2_loss_component_by_step.csv`
- `followup2_same_split_help_harm.csv`
- `followup2_hard_subgroup_metrics.csv`
- `m7_followup2_training_rerun_decision.md`
- `failure_interpretation.md`
- `commands_run.md`
- `MANIFEST.md`

Also update these when runtime evidence is available:

- `followup2_loss_component_gradient_sanity.csv`
- `followup2_batch_composition.csv`
- `srr_contribution_by_case.csv`
- `arbitration_opening_diagnostics.csv`
- `proposal_refiner_effectiveness.csv`
- `followup2_repair_summary.md`
- `route_to_leaderboard_gap_report.md`

Create:

- `m7_followup3_runtime_reaggregation_report.md`
- `m7_followup3_slurm_completion_record.md`

`m7_followup3_runtime_reaggregation_report.md` must include:

`job_id, job_state, exit_code, runtime_seconds, start_time, end_time, runtime_output_path, log_path, aggregation_command, aggregation_exit_code, regenerated_files, files_still_missing, tracked_packet_monitor_placeholders_remaining`

If the Slurm job completed but runtime outputs are missing, corrupted, not written, or cannot be recovered by the aggregator, write `M7_FOLLOWUP3_NEEDS_EVIDENCE`. Do not write ready.

## C. MyoPS follow-up2 result aggregation gate

If the primary MyoPS probe remains incomplete or monitor-only after re-checking Slurm/runtime outputs, follow-up3 cannot be audited as M7 follow-up2 completion.

Required decision fields in `completion_check.md` and `result.md`:

- `myops_decision: M7_FOLLOWUP3_NEEDS_MONITOR` or `myops_decision: M7_FOLLOWUP3_NEEDS_EVIDENCE` if MyoPS remains incomplete;
- separate `cine_decision`;
- separate `combined_decision`.

`combined_decision` must not package MyoPS monitor/evidence-blocked state plus Cine progress as overall success.

If the MyoPS probe completed but metrics remain no-op or near-identity, update:

- `m7_followup2_mechanism_noop_diagnosis.md`
- `srr_contribution_by_case.csv`
- `arbitration_opening_diagnostics.csv`
- `proposal_refiner_effectiveness.csv`
- `failure_interpretation.md`
- `route_to_leaderboard_gap_report.md`

Those files must state whether the completed probe supports `NO_PROMOTION_SCIENTIFIC_UNRESOLVED`, needs another mechanism repair, or remains undertrained/evidence-blocked. Do not convert a no-op result into route promotion or scientific stop.

## D. Temporal dictionary forced closure

Executor must inspect `registration_same_subset_matrix.csv`. If any row satisfies either condition:

- `usable_for_temporal_dictionary=True`
- equivalent controlled field such as `m7_continued_decision=USABLE_NONREFERENCE_REGISTRATION_ROW`

then temporal dictionary follow-up3 is mandatory. Executor must not write `TEMPORAL_DICTIONARY_FOLLOWUP2_REQUIRED_NOT_EXECUTED` and then ready.

Required outputs or updates:

- `temporal_dictionary_evidence.csv`
- `temporal_dictionary_index.json`
- `temporal_dictionary_case_summary.csv`
- `temporal_aggregation_metrics.csv`
- `frame0_vs_temporal_help_harm.csv`
- `cine_metrics_summary.csv`
- `cine_temporal_dictionary_followup3_report.md`

Every usable registration row must have a corresponding temporal dictionary attempt. If only a subset of usable rows is attempted, write the deterministic selection rule and the reason each unattempted usable row was not attempted.

## E. Temporal dictionary minimum content

If any usable non-reference registration row exists, temporal dictionary rows cannot be descriptor-only, no-warp, or frame0-only. They must include:

- ED/reference anchor feature;
- selected non-reference frame id;
- warped image/probability/feature source;
- registration method and registration quality;
- frame-quality score;
- motion-saliency score;
- temporal representer slot usage;
- temporal aggregation output summary;
- local `class_1` myocardium proxy;
- `class_3` sanity if available;
- hosted metric caveat;
- frame0/control comparison.

If warped evidence cannot be generated, executor must either:

1. revoke the usable registration judgment in `registration_same_subset_matrix.csv`, with evidence and `failure_reason`; or
2. write `TEMPORAL_DICTIONARY_BLOCKED_BY_USABLE_ROW_INVALIDATED`, with evidence.

Executor must not simultaneously keep a usable registration row and skip temporal dictionary execution.

## F. Strict validator

Add or update an M7 follow-up3 validator, for example:

`scripts/evaluation/validate_srr_v3_m7_followup3_packet.py`

The validator must accept `--packet <result_dir>` and return exit code `0` only for a reviewable follow-up3 packet. It must return nonzero for known-bad packets.

Known-bad fixtures must be real mutated fixtures, not current-good boolean checks. They must include at least:

- `completion_check.md` is `M7_FOLLOWUP2_NEEDS_MONITOR` but packet is marked ready;
- `followup2_training_adequacy.csv` contains `PENDING_MONITOR` but packet is marked ready;
- Slurm job submitted/pending only, with no completed aggregation;
- Slurm job completed but runtime output not aggregated into tracked packet;
- `usable_for_temporal_dictionary=True` but `temporal_dictionary_evidence.csv` is not executed;
- temporal dictionary ready but only frame0/no-warp/descriptor evidence exists;
- diagnostic hardcase is used for formal best-variant decision;
- completion ready while MyoPS or Cine blocker remains.

Validator outputs:

- `strict_validator_report.md`
- `strict_validator_report.csv`
- `strict_validator_known_bad_cases/README.md`
- `validator_unit_test_report.md`

Each `strict_validator_report.csv` row must include:

`known_bad_case, fixture_or_mutation, validator_command, expected_failure, expected_exit_code, actual_exit_code, actual_status, actual_failure_reason, pass_fail_closed`

Rows that do not run a real validator command do not count. Any known-bad fixture with exit code 0 fails the validator gate.

## G. Required output set

All follow-up3 outputs live under:

`results/20260705_srr_v3_m7_training_and_cine_utilization/`

Required new or updated files:

- `result.md`
- `completion_check.md`
- `review_request.md` only when fully reviewable; monitor packets must say `DO_NOT_REVIEW_MONITOR_PACKET`
- `MANIFEST.md`
- `commands_run.md`
- `m7_followup3_runtime_reaggregation_report.md`
- `m7_followup3_slurm_completion_record.md`
- `followup2_training_adequacy.csv`
- `followup2_loss_component_by_step.csv`
- `followup2_loss_component_gradient_sanity.csv`
- `followup2_batch_composition.csv`
- `followup2_same_split_help_harm.csv`
- `followup2_hard_subgroup_metrics.csv`
- `m7_followup2_training_rerun_decision.md`
- `m7_followup2_mechanism_noop_diagnosis.md`
- `srr_contribution_by_case.csv`
- `arbitration_opening_diagnostics.csv`
- `proposal_refiner_effectiveness.csv`
- `failure_interpretation.md`
- `followup2_repair_summary.md`
- `route_to_leaderboard_gap_report.md`
- `registration_same_subset_matrix.csv`
- `temporal_dictionary_evidence.csv`
- `temporal_dictionary_index.json`
- `temporal_dictionary_case_summary.csv`
- `temporal_aggregation_metrics.csv`
- `frame0_vs_temporal_help_harm.csv`
- `cine_metrics_summary.csv`
- `cine_temporal_dictionary_followup3_report.md`
- `strict_validator_report.md`
- `strict_validator_report.csv`
- `strict_validator_known_bad_cases/README.md`
- `validator_unit_test_report.md`

If a file is not applicable, it must exist with `NOT_APPLICABLE_WITH_REASON`, and the reason must not hide a mandatory gate. Temporal dictionary outputs are not applicable only if no usable registration row remains after evidence-based invalidation.

## H. Completion states

`completion_check.md` may contain only:

- `M7_FOLLOWUP3_READY_FOR_REVIEW`
- `M7_FOLLOWUP3_NEEDS_MONITOR`
- `M7_FOLLOWUP3_NEEDS_EVIDENCE`
- `M7_FOLLOWUP3_NEEDS_REVISION`
- `M7_FOLLOWUP3_BLOCKED_BY_REVIEW_STATE`
- `M7_BLOCKED_BY_M6`

Do not write `M7_FOLLOWUP3_READY_FOR_REVIEW` if:

- follow-up2 training adequacy still contains `PENDING_MONITOR`;
- Slurm job completion outputs are not aggregated into tracked lightweight evidence;
- a usable registration row exists but temporal dictionary was not executed;
- temporal dictionary contains only descriptor/frame0/no-warp evidence;
- strict validator is not real known-bad fail-closed;
- MyoPS/Cine decisions are mixed together as overall success;
- route promotion, hosted metric claim, validation packaging/upload, M8, fold expansion, challenge submission, scientific stop, leaderboard readiness, or challenge readiness is claimed.

Finish by force-adding and locally committing only lightweight evidence plus necessary first-party helper/source/test files. Do not commit checkpoints, NIfTI predictions, upload packages, raw data, secrets, environment dumps, whole runtime trees, or large logs. Do not write `review.md`. Do not push.
```

---

# 2. Reviewer prompt: M7 follow-up3 audit

```text
这是独立只读 reviewer/auditor session。只审阅 `results/20260705_srr_v3_m7_training_and_cine_utilization/` 的 M7 follow-up3 packet 和必要 first-party helper/source/test files。不要补 executor 缺失文件，不要改代码，不要训练，不要 validation packaging/upload，不要 hosted metric claim，不要 route promotion，不要启动 M8。最后只写该目录下的 `review.md`。

必须读取：

- `prompts/shared/20260707_M7_followup3_completion_temporal_dictionary_repair_prompt.md`
- `prompts/shared/EXECUTOR_PROMPTS.md`
- `prompts/shared/REVIEWER_PROMPTS.md`
- `prompts/MILESTONE_REVIEW_PROTOCOL.md`
- `prompts/HANDOFF_GATE_POLICY.md`
- `prompts/GPT_HARD_GATE_PROMPT.md`
- latest M7 follow-up2 `review.md`
- M7 follow-up3 result files
- modified first-party aggregation/Cine/validator/test files

## A. Scope gate

Reject if the packet claims M8, route promotion, hosted metric, validation packaging/upload, fold expansion, challenge submission, scientific stop, leaderboard readiness, or challenge readiness.

## B. Monitor packet is not completion gate

Reject if a monitor packet is treated as completion.

Reject if:

- `completion_check.md` is ready while `followup2_training_adequacy.csv` still contains `PENDING_MONITOR`;
- `commands_run.md` only shows Slurm submitted/pending state;
- completed Slurm job outputs were not re-aggregated into tracked lightweight evidence;
- `review_request.md` asks for normal review while the packet is still monitor/evidence-blocked.

Reviewer must inspect Slurm job id, job state, exit code, runtime seconds, runtime output path/log path, aggregation command, and aggregation exit code in `m7_followup3_runtime_reaggregation_report.md` and `m7_followup3_slurm_completion_record.md`.

## C. Completed Slurm job re-aggregation gate

Reject if job `58021931` or the justified superseding job completed but tracked files still reflect pre-completion monitor evidence.

Reject if any of these files are missing or stale after completed aggregation:

- `result.md`
- `completion_check.md`
- `followup2_training_adequacy.csv`
- `followup2_loss_component_by_step.csv`
- `followup2_same_split_help_harm.csv`
- `followup2_hard_subgroup_metrics.csv`
- `m7_followup2_training_rerun_decision.md`
- `failure_interpretation.md`
- `commands_run.md`
- `MANIFEST.md`

If runtime outputs are missing/corrupt/unrecoverable, reviewer must use an evidence/revision decision, not audited-go.

## D. MyoPS/Cine decision separation gate

Reject if MyoPS and Cine decisions are merged into overall success.

If MyoPS remains monitor/evidence-blocked, `myops_decision` must be `M7_FOLLOWUP3_NEEDS_MONITOR` or `M7_FOLLOWUP3_NEEDS_EVIDENCE`, and `combined_decision` must not imply success.

If MyoPS completed but remains no-op, reviewer must check updated `m7_followup2_mechanism_noop_diagnosis.md`, `srr_contribution_by_case.csv`, `arbitration_opening_diagnostics.csv`, `proposal_refiner_effectiveness.csv`, and `route_to_leaderboard_gap_report.md`. No-op may support no-promotion evidence only; it cannot support route promotion, leaderboard readiness, or scientific stop.

## E. Temporal dictionary gate

Reject if `registration_same_subset_matrix.csv` contains `usable_for_temporal_dictionary=True` or equivalent `USABLE_NONREFERENCE_REGISTRATION_ROW` and temporal dictionary was not executed.

Reject if `temporal_dictionary_evidence.csv` still says `TEMPORAL_DICTIONARY_FOLLOWUP2_REQUIRED_NOT_EXECUTED` while a usable row exists.

Reject if temporal dictionary is marked ready but contains only descriptor, frame0, or no-warp evidence.

Required temporal dictionary outputs:

- `temporal_dictionary_evidence.csv`
- `temporal_dictionary_index.json`
- `temporal_dictionary_case_summary.csv`
- `temporal_aggregation_metrics.csv`
- `frame0_vs_temporal_help_harm.csv`
- `cine_metrics_summary.csv`
- `cine_temporal_dictionary_followup3_report.md`

The reviewer must confirm at least one temporal dictionary attempt for each usable registration row, or a deterministic subset rule plus explicit unattempted-row reasons.

If warped evidence cannot be generated, reviewer must verify that the usable registration judgment was revoked or that `TEMPORAL_DICTIONARY_BLOCKED_BY_USABLE_ROW_INVALIDATED` is supported by evidence. It is invalid to keep a usable row and skip temporal dictionary.

## F. Strict validator gate

Reject unless a real follow-up3 validator was run against mutated known-bad fixtures. A current-good packet boolean checklist is not acceptable.

Known-bad fixtures must include:

- ready completion while `completion_check.md` was `M7_FOLLOWUP2_NEEDS_MONITOR`;
- ready completion while `followup2_training_adequacy.csv` contained `PENDING_MONITOR`;
- Slurm job submitted/pending only;
- Slurm job completed but runtime output not aggregated into tracked files;
- usable registration row but no temporal dictionary;
- temporal dictionary ready with only frame0/no-warp/descriptor evidence;
- diagnostic hardcase used for formal best-variant decision;
- ready completion while MyoPS or Cine blocker remains.

Reject if any known-bad fixture has actual exit code 0 or if `strict_validator_report.csv` lacks expected failure, actual exit code/status, and failure reason.

## G. Reviewer decision states

Allowed decisions:

- `M7_FOLLOWUP3_AUDITED_GO_FOR_NEXT_PLANNING`
- `M7_FOLLOWUP3_AUDITED_NEEDS_REVISION`
- `M7_FOLLOWUP3_AUDITED_NEEDS_EVIDENCE`
- `M7_FOLLOWUP3_AUDITED_NEEDS_MONITOR`
- `M7_FOLLOWUP3_AUDITED_NO_PROMOTION_SCIENTIFIC_UNRESOLVED`

`M7_FOLLOWUP3_AUDITED_GO_FOR_NEXT_PLANNING` only means GPT planner can inspect a complete, non-monitor, reviewable follow-up3 packet. It does not authorize M8, route promotion, validation packaging/upload, hosted metric claim, fold expansion, challenge submission, scientific stop, leaderboard readiness, or challenge readiness.
```

## 3. Merge note

This file is intentionally standalone so the GPT planner/user can inspect it before merging. If accepted, merge the executor block into `prompts/shared/EXECUTOR_PROMPTS.md` after the current M7 follow-up2 section, and merge the reviewer block into `prompts/shared/REVIEWER_PROMPTS.md` after the current M7 follow-up2 reviewer section. Keep earlier M7, M7 continued, and follow-up2 sections as historical records.
