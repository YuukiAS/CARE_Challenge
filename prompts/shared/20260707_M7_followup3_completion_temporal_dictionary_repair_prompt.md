# 20260707 M7 follow-up3: completion-safe aggregation and temporal-dictionary repair prompt

status: `NEW_SHARED_PROMPT_FOR_EXECUTOR_AND_REVIEWER`
source_result_dir: `results/20260705_srr_v3_m7_training_and_cine_utilization/`
source_review_decision: `M7_FOLLOWUP2_AUDITED_NEEDS_EVIDENCE`
planner: `ChatGPT/GPT thread`
intended_merge_target:
  - `prompts/shared/EXECUTOR_PROMPTS.md`
  - `prompts/shared/REVIEWER_PROMPTS.md`

## 0. Why follow-up3 exists

M7 follow-up2 did not fail because the scientific idea was completed and negative. It failed because the executor committed a monitor packet and requested review before the submitted primary MyoPS probe was incorporated into the tracked lightweight evidence. The reviewer found that live Slurm accounting later showed job `58021931` completed successfully, but the committed packet still contained `PENDING_MONITOR` rows for training adequacy, loss components, gradient sanity, and batch composition. The reviewer also found a separate Cine blocker: `registration_same_subset_matrix.csv` contained a row with `usable_for_temporal_dictionary=True`, while `temporal_dictionary_evidence.csv` said `TEMPORAL_DICTIONARY_FOLLOWUP2_REQUIRED_NOT_EXECUTED`.

Therefore follow-up3 is not allowed to be another prompt-only or monitor-only packet. It must either produce a fully regenerated, reviewable M7 packet from the completed runtime artifacts and resolve the Cine temporal-dictionary gate, or stop with a non-reviewable monitor/evidence-blocked state that explicitly forbids review, route promotion, validation packaging/upload, hosted metric claims, M8, fold expansion, challenge submission, scientific stop, and leaderboard readiness.

Follow-up3 remains M7. It is not M8, not route promotion, not validation packaging/upload, not hosted metric claim, not challenge submission, not fold expansion, not scientific stop, and not leaderboard readiness. Its purpose is to turn the already submitted/completed follow-up2 work into auditable evidence, close the temporal-dictionary inconsistency, and make it impossible for Codex to mark a pending Slurm job or placeholder CSVs as completion.

---

# 1. Executor prompt: M7 follow-up3 completion-safe aggregation and temporal-dictionary repair

```text
只执行 M7 follow-up3：completion-safe aggregation and temporal-dictionary repair after `M7_FOLLOWUP2_AUDITED_NEEDS_EVIDENCE`.

开始前必须确认：
- `results/20260705_srr_v3_m7_training_and_cine_utilization/review.md` 存在且包含 `M7_FOLLOWUP2_AUDITED_NEEDS_EVIDENCE`；
- `results/20260705_srr_v3_m6_myops_concrete_architecture_repair/review.md` 存在且包含 `M6_AUDITED_GO`；
- 当前任务仍是 M7 follow-up3，不是 M8，不是 route promotion，不是 validation packaging/upload，不是 hosted metric claim，不是 challenge submission，不是 leaderboard readiness；
- 不要写 `review.md`，不要启动 M8。

必须读取：
- `results/20260705_srr_v3_m7_training_and_cine_utilization/review.md`
- `results/20260705_srr_v3_m7_training_and_cine_utilization/result.md`
- `results/20260705_srr_v3_m7_training_and_cine_utilization/completion_check.md`
- `results/20260705_srr_v3_m7_training_and_cine_utilization/followup2_training_adequacy.csv`
- `results/20260705_srr_v3_m7_training_and_cine_utilization/registration_same_subset_matrix.csv`
- `results/20260705_srr_v3_m7_training_and_cine_utilization/temporal_dictionary_evidence.csv`
- `prompts/shared/EXECUTOR_PROMPTS.md`
- `prompts/shared/REVIEWER_PROMPTS.md`
- `prompts/MILESTONE_REVIEW_PROTOCOL.md`
- `prompts/HANDOFF_GATE_POLICY.md`
- `prompts/GPT_HARD_GATE_PROMPT.md`

## A. Completion safety preflight: monitor packets cannot be review packets

The core follow-up3 rule is fail-closed completion safety.

Before doing any aggregation, inspect the current tracked packet and detect monitor placeholders. If any of the following files contain `PENDING_MONITOR`, `NEEDS_MONITOR`, `PRIMARY_PROBE_SUBMITTED_NEEDS_MONITOR`, or equivalent placeholder rows, the executor must treat the packet as not reviewable until the corresponding runtime output is regenerated:

- `followup2_training_adequacy.csv`
- `followup2_loss_component_by_step.csv`
- `followup2_loss_component_gradient_sanity.csv`
- `followup2_batch_composition.csv`
- `followup2_same_split_help_harm.csv`
- `followup2_hard_subgroup_metrics.csv`
- `srr_contribution_by_case.csv`
- `arbitration_opening_diagnostics.csv`
- `proposal_refiner_effectiveness.csv`
- `completion_check.md`
- `result.md`

If a Slurm job id is recorded, the executor must query both active and accounting state before writing a reviewable packet:

```bash
squeue -j <job_id> -o '%i|%P|%j|%T|%M|%l|%R'
sacct -j <job_id> --format=JobID,JobName,Partition,State,Elapsed,ExitCode,Start,End -P
```

If the job is still `PENDING`, `RUNNING`, `CONFIGURING`, `COMPLETING`, or cannot yet be resolved in `sacct`, do not write `review_request.md`, do not write `*_READY_FOR_REVIEW`, and do not commit a reviewable packet. Instead write or update only:

- `m7_followup3_monitor_state.md`
- `result.md` with `status: M7_FOLLOWUP3_NEEDS_MONITOR_NO_REVIEW`
- `completion_check.md` with `M7_FOLLOWUP3_NEEDS_MONITOR_NO_REVIEW`
- `commands_run.md`
- `MANIFEST.md`

In this monitor-only state, `review_request.md` must be absent or must explicitly say `DO_NOT_REVIEW_MONITOR_PACKET`. If any pending/running job is packaged with a normal review request, the task fails.

If the job completed with nonzero exit code or runtime artifacts are missing, write `M7_FOLLOWUP3_NEEDS_EVIDENCE_RUNTIME_ARTIFACT_MISSING` or `M7_FOLLOWUP3_RUNTIME_FAILED`, not ready.

## B. Regenerate the tracked MyoPS evidence from completed runtime artifacts

For job `58021931` or any superseding job explicitly justified in `commands_run.md`, the executor must read the completed runtime directory and regenerate the tracked lightweight M7 packet. Do not leave old monitor placeholders in tracked files.

Required regenerated files:

- `followup2_training_adequacy.csv`
- `followup2_loss_component_by_step.csv`
- `followup2_loss_component_gradient_sanity.csv`
- `followup2_batch_composition.csv`
- `followup2_same_split_help_harm.csv`
- `followup2_hard_subgroup_metrics.csv`
- `srr_contribution_by_case.csv`
- `arbitration_opening_diagnostics.csv`
- `proposal_refiner_effectiveness.csv`
- `m7_followup3_runtime_ingestion_report.md`
- `m7_followup3_probe_summary.json`

`m7_followup3_runtime_ingestion_report.md` must record:

- job id;
- Slurm state;
- exit code;
- start/end/elapsed;
- runtime summary path;
- checkpoint path or explicit no-checkpoint reason;
- actual optimizer steps;
- train loop seconds;
- validation event count;
- eval case ids;
- batch composition source;
- every tracked CSV regenerated from runtime evidence;
- whether any runtime artifact was missing.

`followup2_training_adequacy.csv` must no longer contain monitor placeholders. It must include at least:

`variant, job_id, slurm_state, exit_code, optimizer_steps, train_loop_seconds, validation_event_count, eval_case_count, one_batch_overfit_status, loss_decrease, adequacy_decision, issue, runtime_summary_path`

Minimum probe adequacy for follow-up3 is inherited from follow-up2 unless runtime proves otherwise:

- minimum: `optimizer_steps >= 1200` and `train_loop_seconds >= 900`;
- preferred: `optimizer_steps >= 3000` and `train_loop_seconds >= 1800`;
- at least one validation event;
- batch composition must include T2-present / GT-positive edema evidence when available;
- no-T2 safety rows must be retained.

If minimum adequacy fails, write `M7_FOLLOWUP3_NEEDS_EVIDENCE_UNDERTRAINED` or `M7_FOLLOWUP3_NEEDS_MONITOR` as appropriate, and do not claim mechanism success. Do not call an undertrained probe a scientific negative stop.

## C. Mechanism evidence must be runtime evidence, not stale or placeholder evidence

The regenerated mechanism files must answer whether SRR actually contributed on the completed primary probe.

`srr_contribution_by_case.csv` must contain per-case/per-class rows with at least:

`case_id, center, modality_group, t2_present, scar_gt_positive, edema_gt_positive, class_name, anchor_delta_rate, final_delta_rate, correction_gate_open_rate, srr_weight_mean, proposal_weight_mean, refiner_weight_mean, final_logit_delta_abs_mean, roi_delta_abs_mean, no_t2_edema_voxels, source_runtime_path`

`arbitration_opening_diagnostics.csv` must contain runtime rows, not only synthetic unit rows. Required fields:

`case_id, class_name, subgroup, anchor_uncertainty_mean, anchor_error_proxy, correction_gate_open_rate, proposal_weight_mean, refiner_weight_mean, final_logit_delta_in_roi, chosen_source, fallback_reason, no_t2_status, runtime_or_synthetic, blocker_reason`

At least one runtime row is required for scar and at least one runtime row is required for T2-present edema when such cases exist. Synthetic rows may remain, but they cannot substitute for runtime evidence.

`proposal_refiner_effectiveness.csv` must report runtime proposal/refiner effectiveness with:

`case_id, class_name, proposal_recall_proxy, proposal_precision_proxy, roi_volume_ratio, refiner_delta_magnitude, component_delta, remote_fp_delta, hd95_delta, dice_delta, source_runtime_path, status`

If SRR remains near-zero/no-op after regeneration, do not hide this. Write `m7_followup3_noop_or_harm_interpretation.md` and mark:

- `MYOPS_NO_PROMOTION_NEAR_IDENTITY` if final deltas are near-zero;
- `MYOPS_NO_PROMOTION_HARMFUL` if same-split help/harm is worse than nnU-Net;
- `MYOPS_NEEDS_NEXT_ARCHITECTURE_REPAIR` if proposal/refiner/arbitration still have weak runtime effect;
- `MYOPS_NEEDS_EVIDENCE_UNDERTRAINED` only if adequacy failed.

Do not write a new best-variant promotion table if the regenerated formal evidence is still too small, undertrained, near-identity, or harmful. Keep non-rerun variants marked `NOT_COMPARABLE_AFTER_FOLLOWUP2_REPAIR` unless they were rerun under the same repaired mechanism.

## D. Cine temporal dictionary gate: usable registration forces temporal dictionary attempt

Read `registration_same_subset_matrix.csv`. If any row has `usable_for_temporal_dictionary=True`, the executor must not leave `temporal_dictionary_evidence.csv` as `TEMPORAL_DICTIONARY_FOLLOWUP2_REQUIRED_NOT_EXECUTED`.

There are only two valid paths:

### D1. Execute minimal temporal dictionary follow-up

If the usable row is truly usable, implement or run a minimal diagnostic temporal dictionary builder, for example:

`scripts/evaluation/run_srr_v3_m7_temporal_dictionary_followup3.py`

The temporal dictionary must use at least one usable non-reference registration row and write `temporal_dictionary_evidence.csv` with runtime rows containing:

`status, method, case_id, reference_frame_id, selected_non_reference_frame_id, ed_reference_anchor_feature, non_reference_feature, warped_source, registration_quality, frame_quality, motion_saliency, temporal_representer_slot_usage, aggregation_output_summary, local_class_1_myocardium_proxy, ed_only_control_proxy, temporal_delta_proxy, hosted_metric_caveat, temporal_dictionary_attempted, failure_reason`

It must also write:

- `temporal_dictionary_followup3_report.md`
- `temporal_dictionary_unit_tests.md` or `temporal_dictionary_validator_report.md`

A ready temporal dictionary row cannot be descriptor-only, frame0-only, one-case SyN-only, unwarped, or unregistered. It must use a warped non-reference image/probability/feature or explicitly fail.

### D2. Reclassify registration usability with evidence

If the row with `usable_for_temporal_dictionary=True` is not actually usable under the contract, update `registration_same_subset_matrix.csv` to set `usable_for_temporal_dictionary=False`, fill `failure_reason`, and explain in `cine_registration_followup3_reclassification.md` why the previous usable decision was wrong. This must be based on metrics or missing warp artifacts, not convenience.

If no usable row remains after reclassification, `temporal_dictionary_evidence.csv` may contain only blocked rows and must say `CINE_REGISTRATION_BLOCKED_AFTER_FOLLOWUP3_RECLASSIFICATION` or `TEMPORAL_DICTIONARY_BLOCKED_BY_REGISTRATION_GAP_AFTER_FOLLOWUP3`.

The executor must not choose neither path. If a usable registration row exists and no temporal dictionary is attempted or reclassification is made, write `M7_FOLLOWUP3_NEEDS_REVISION_TEMPORAL_DICTIONARY_GATE` and do not request ready review.

## E. Validator and unit-test repair: no fake fail-closed, no monitor-ready pass

Keep the follow-up2 strict validator repair, but extend it with monitor and temporal-dictionary gates. Update or create:

- `scripts/evaluation/validate_srr_v3_m7_continued_packet.py`
- `strict_validator_report.md`
- `strict_validator_report.csv`
- `strict_validator_known_bad_cases/README.md`
- `validator_unit_test_report.md`

The validator must accept `--packet <result_dir>` and return:

- exit `0` only for a fully reviewable packet;
- nonzero exit for bad packets.

Required known-bad fixtures now include all follow-up2 fixtures plus these follow-up3-specific cases:

- monitor packet with `PENDING_MONITOR` rows and normal `review_request.md`;
- `completion_check.md` says ready while job is still pending/running;
- completed Slurm job exists but tracked training adequacy still says `PENDING_MONITOR`;
- `srr_contribution_by_case.csv` contains only `PENDING_FOLLOWUP2_PROBE` rows;
- `arbitration_opening_diagnostics.csv` contains only synthetic rows and no runtime rows;
- usable registration row exists but temporal dictionary is not attempted;
- temporal dictionary row marked ready without warped non-reference evidence;
- registration usability reclassified without failure reason;
- non-rerun variants ranked as comparable after a single repaired probe.

Every row in `strict_validator_report.csv` must include:

`known_bad_case, fixture_or_mutation, validator_command, expected_exit_code, actual_exit_code, expected_failure, actual_failure_reason, pass_fail_closed`

Rows that do not execute a real validator command do not count.

## F. Required outputs

Write or update all outputs under:

`results/20260705_srr_v3_m7_training_and_cine_utilization/`

Required new or updated files:

- `result.md`
- `completion_check.md`
- `review_request.md` only if fully reviewable; otherwise absent or explicitly `DO_NOT_REVIEW_MONITOR_PACKET`
- `MANIFEST.md`
- `commands_run.md`
- `m7_followup3_runtime_ingestion_report.md`
- `m7_followup3_probe_summary.json`
- `followup2_training_adequacy.csv`
- `followup2_loss_component_by_step.csv`
- `followup2_loss_component_gradient_sanity.csv`
- `followup2_batch_composition.csv`
- `followup2_same_split_help_harm.csv`
- `followup2_hard_subgroup_metrics.csv`
- `srr_contribution_by_case.csv`
- `arbitration_opening_diagnostics.csv`
- `proposal_refiner_effectiveness.csv`
- `m7_followup3_noop_or_harm_interpretation.md` if no-op/harm is observed
- `best_variant_decision.md`
- `route_to_leaderboard_gap_report.md`
- `registration_same_subset_matrix.csv`
- `cine_registration_followup3_reclassification.md` if registration usability is changed
- `temporal_dictionary_evidence.csv`
- `temporal_dictionary_followup3_report.md` if temporal dictionary is attempted
- `temporal_dictionary_unit_tests.md` or `temporal_dictionary_validator_report.md` if temporal dictionary is attempted
- `strict_validator_report.md`
- `strict_validator_report.csv`
- `strict_validator_known_bad_cases/README.md`
- `validator_unit_test_report.md`

If a required file is not applicable, it must exist with `NOT_APPLICABLE_WITH_REASON` and must not hide a mandatory gate. For example, temporal dictionary is not applicable only if no usable registration row remains after evidence-based reclassification.

## G. Completion states

`completion_check.md` may contain only:

- `M7_FOLLOWUP3_READY_FOR_REVIEW`
- `M7_FOLLOWUP3_NEEDS_MONITOR_NO_REVIEW`
- `M7_FOLLOWUP3_NEEDS_EVIDENCE_RUNTIME_ARTIFACT_MISSING`
- `M7_FOLLOWUP3_RUNTIME_FAILED`
- `M7_FOLLOWUP3_NEEDS_EVIDENCE_UNDERTRAINED`
- `M7_FOLLOWUP3_NEEDS_REVISION_TEMPORAL_DICTIONARY_GATE`
- `M7_FOLLOWUP3_NEEDS_REVISION`
- `M7_BLOCKED_BY_M6`

Do not write `M7_FOLLOWUP3_READY_FOR_REVIEW` if:

- any tracked CSV still has `PENDING_MONITOR`, `PRIMARY_PROBE_SUBMITTED_NEEDS_MONITOR`, or `PENDING_FOLLOWUP2_PROBE` placeholders in required evidence fields;
- the Slurm job is not complete with exit code `0:0`;
- runtime artifacts are missing;
- strict validator does not run real known-bad fixtures;
- current training evidence is under the required minimum and not explicitly marked undertrained;
- mechanism evidence is stale old-M7 evidence rather than regenerated runtime evidence;
- a usable registration row exists but temporal dictionary was not attempted;
- temporal dictionary is marked ready without warped non-reference evidence;
- route promotion, hosted metric claim, validation packaging/upload, M8, fold expansion, challenge submission, scientific stop, or leaderboard readiness is claimed.

`M7_FOLLOWUP3_READY_FOR_REVIEW` only means the follow-up3 packet is ready for independent read-only review. It does not authorize M8, route promotion, validation packaging/upload, hosted metric claim, fold expansion, challenge submission, scientific stop, or leaderboard readiness.

Finish by force-adding and locally committing only lightweight evidence plus necessary first-party helper/source/test files. Do not commit checkpoints, NIfTI predictions, upload packages, raw data, secrets, environment dumps, whole runtime trees, or large logs. Do not write `review.md`. Do not push.
```

---

# 2. Reviewer prompt: M7 follow-up3 audit

```text
这是独立只读 reviewer/auditor session。只审阅 `results/20260705_srr_v3_m7_training_and_cine_utilization/` 的 M7 follow-up3 packet 和必要 first-party helper/source/test files。不要补 executor 缺失文件，不要改代码，不要训练，不要 validation packaging/upload，不要 hosted metric claim，不要 route promotion，不要启动 M8。最后只写该目录下的 `review.md`。

必须读取：

- `prompts/shared/EXECUTOR_PROMPTS.md`
- `prompts/shared/REVIEWER_PROMPTS.md`
- `prompts/shared/20260707_M7_followup3_completion_temporal_dictionary_repair_prompt.md` if present
- `prompts/MILESTONE_REVIEW_PROTOCOL.md`
- `prompts/HANDOFF_GATE_POLICY.md`
- `prompts/GPT_HARD_GATE_PROMPT.md`
- latest M7 follow-up2 `review.md`
- M7 follow-up3 result files
- modified first-party evaluation/training/Cine/validator/test files

## A. Scope gate

Reject if the packet claims M8, route promotion, hosted metric, validation packaging/upload, fold expansion, challenge submission, scientific stop, or leaderboard readiness.

## B. Monitor/completion safety gate

Reject if a normal review request was created while Slurm job evidence is still pending/running/unresolved.

Reject if any required tracked evidence file still contains monitor placeholders such as `PENDING_MONITOR`, `NEEDS_MONITOR`, `PRIMARY_PROBE_SUBMITTED_NEEDS_MONITOR`, or `PENDING_FOLLOWUP2_PROBE`, unless the packet explicitly uses `M7_FOLLOWUP3_NEEDS_MONITOR_NO_REVIEW` and does not request review.

Reject if `completion_check.md` says ready but job status is not complete with exit code `0:0`, runtime artifacts are missing, or regenerated tracked CSVs are absent.

## C. Runtime ingestion gate

Reject unless `m7_followup3_runtime_ingestion_report.md` and `m7_followup3_probe_summary.json` trace the completed job and regenerated tracked evidence. The reviewer must verify actual optimizer steps, train-loop seconds, validation events, eval case ids, batch composition, and regenerated file paths.

If the minimum probe budget is not met, do not grant audited-go for completed evidence. Use an undertrained/evidence decision.

## D. MyoPS mechanism evidence gate

Reject if `srr_contribution_by_case.csv`, `arbitration_opening_diagnostics.csv`, or `proposal_refiner_effectiveness.csv` are stale, placeholder, or only synthetic. At least one runtime scar row and one runtime T2-present edema row are required when such cases exist.

The reviewer must check:

- anchor delta rate;
- final delta rate;
- correction gate opening;
- SRR/proposal/refiner weights;
- final-logit delta in ROI;
- proposal recall proxy;
- remote FP suppression or worsening;
- component/HD95/Dice deltas;
- no-T2 edema voxel safety.

If SRR is still near-zero or harmful, this is acceptable only as negative/no-promotion evidence, not as route promotion or leaderboard readiness. The packet must contain `m7_followup3_noop_or_harm_interpretation.md` and `route_to_leaderboard_gap_report.md`.

## E. Cine temporal dictionary gate

Reject if `registration_same_subset_matrix.csv` contains `usable_for_temporal_dictionary=True` and temporal dictionary follow-up3 was not attempted.

Reject if temporal dictionary is marked ready without warped non-reference evidence.

If the executor reclassifies the usable registration row as not usable, verify `cine_registration_followup3_reclassification.md` and the updated `failure_reason`. Convenience reclassification without evidence is not acceptable.

If no usable registration remains after evidence-based reclassification, a blocked temporal dictionary state is acceptable only if it is explicit and honest.

## F. Strict validator gate

Reject unless a real validator was run against real mutated known-bad fixtures and each bad fixture has actual nonzero exit code or equivalent CLI failure. A current-packet boolean checklist is not acceptable.

The reviewer must verify follow-up3-specific known-bad fixtures, especially:

- monitor packet with normal review request;
- completion ready while job pending/running;
- completed job but tracked files still pending;
- only synthetic arbitration diagnostics;
- usable registration but no temporal dictionary;
- temporal dictionary ready without warped non-reference evidence.

## G. Reviewer decision states

Allowed decisions:

- `M7_FOLLOWUP3_AUDITED_GO_FOR_NEXT_PLANNING`
- `M7_FOLLOWUP3_AUDITED_NEEDS_REVISION`
- `M7_FOLLOWUP3_AUDITED_NEEDS_EVIDENCE`
- `M7_FOLLOWUP3_AUDITED_NEEDS_MONITOR`
- `M7_FOLLOWUP3_AUDITED_NO_PROMOTION_SCIENTIFIC_UNRESOLVED`

`M7_FOLLOWUP3_AUDITED_GO_FOR_NEXT_PLANNING` only means GPT planner can inspect a complete, non-monitor, reviewable follow-up3 packet. It does not authorize M8, route promotion, validation packaging/upload, hosted metric claim, fold expansion, challenge submission, scientific stop, or leaderboard readiness.
```

## 3. Merge note

This file is intentionally standalone so the GPT planner/user can inspect it before merging. If accepted, merge the executor block into `prompts/shared/EXECUTOR_PROMPTS.md` after the current M7 follow-up2 section, and merge the reviewer block into `prompts/shared/REVIEWER_PROMPTS.md` after the current M7 follow-up2 reviewer section. Keep earlier M7, M7 continued, and follow-up2 sections as historical records.
