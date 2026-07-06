# 20260706 M7 follow-up2: leaderboard-oriented repair prompt

status: `NEW_SHARED_PROMPT_FOR_EXECUTOR_AND_REVIEWER`
source_result_dir: `results/20260705_srr_v3_m7_training_and_cine_utilization/`
source_review_decision: `M7_CONTINUED_AUDITED_NEEDS_REVISION`
planner: `ChatGPT/GPT thread`
intended_merge_target:
  - `prompts/shared/EXECUTOR_PROMPTS.md`
  - `prompts/shared/REVIEWER_PROMPTS.md`

## 0. Why this follow-up2 exists

The M7 continued packet repaired several major earlier blockers, but it is still not sufficient for a leaderboard-oriented SRR route.

The latest M7 continued review says:

- gradient sanity improved: `loss_component_gradient_sanity.csv` has 107 rows, 93 `PASS`, 14 `PASS_ZERO_JUSTIFIED`, no `BACKWARD_FAILED`, and a T2-present batch fraction of 0.5;
- formal validation subgroup coverage improved: selected formal-val rows now cover CenterA/CenterB/CenterC and T2-present rows;
- best-variant decision remains non-promotional: all rows are `NO_PROMOTION_SCIENTIFIC_UNRESOLVED`, scar Dice deltas are tiny and edema Dice deltas are tiny;
- Cine registration repair was attempted, but no non-reference row is usable for temporal dictionary;
- strict validator still fails the reviewer contract because it does not create mutated known-bad packets and prove nonzero exit/fail status. It only runs boolean checks on the current good packet and labels that as known-bad fail-closed.

Therefore the next task must not be another narrow table repair. It must both close the strict-validator blocker and convert the useful M7 evidence into an actual next repair step aimed at leaderboard performance. If the packet only repairs validator bookkeeping while leaving the SRR route scientifically inert, it is not enough.

## 1. Route objective restatement

This follow-up2 remains M7. It is not M8, not validation packaging/upload, not route promotion, not hosted metric claim, not fold expansion, and not challenge readiness.

However, it must be designed as a serious step toward a first-place method:

- MyoPS: SRR must become a baseline-preserving, error-targeted correction system over nnU-Net anchor, with real dictionary/prototype/proposal/refiner/arbitration contributions on hard cases, especially T2-present edema, CenterB/CenterC, remote-FP-positive cases, and small/large lesion strata.
- Cine: Cine must not remain descriptor-only or frame0-only. Registration-aware temporal retrieval is required by the route diagrams. If classical registration fails, the executor must attempt a stronger cropped/anatomy-guided registration escalation before preserving a gap.

The follow-up2 executor must treat the latest M7 continued packet as evidence, not as success.

---

# 2. Executor prompt: M7 follow-up2 leaderboard repair

```text
只执行 M7 follow-up2：leaderboard-oriented repair after `M7_CONTINUED_AUDITED_NEEDS_REVISION`.

开始前必须确认：
- `results/20260705_srr_v3_m7_training_and_cine_utilization/review.md` 存在且包含 `M7_CONTINUED_AUDITED_NEEDS_REVISION`；
- `results/20260705_srr_v3_m6_myops_concrete_architecture_repair/review.md` 存在且包含 `M6_AUDITED_GO`；
- 当前任务仍是 M7 follow-up2，不是 M8，不是 route promotion，不是 validation packaging/upload，不是 hosted metric claim，不是 challenge submission；
- 不要写 `review.md`，不要启动 M8。

本任务有两个层次。第一层是关闭最新 reviewer 指出的 strict-validator blocker。第二层是利用 M7/continued 的真实证据做 leaderboard-oriented method repair，不允许只修 validator 表格后停止。

## A. 修复 strict validator：必须是真 known-bad fail-closed

当前 strict validator 是假的 fail-closed：它读取当前 good packet 的布尔状态，然后把 known-bad 名称标成 `PASS_FAIL_CLOSED`。这不满足 reviewer gate。

必须实现或新增一个可运行的 M7 continued validator，例如：

`scripts/evaluation/validate_srr_v3_m7_continued_packet.py`

要求：

1. 接收 `--packet <result_dir>`。
2. 对真实 packet 成功时 exit code 为 0。
3. 对 bad packet 失败时 exit code 非 0。
4. 输出 JSON 或 Markdown summary。
5. 检查至少以下 gates：
   - loss gradient sanity rows 不得全 `BACKWARD_FAILED`；
   - `loss_graph_training_validity_report.md` 必须存在且说明 original training graph validity；
   - hard subgroup 不得全 CenterA/LGE-only/no-T2；
   - diagnostic hardcase rows 不得混入 formal best-variant decision；
   - Cine branch 必须有 M7 continued registration repair attempt；
   - frame0-only / one-case SyN / untrained VoxelMorph 不得标为 usable registration；
   - temporal dictionary 不得在无 usable non-reference registration 时标 ready；
   - `completion_check.md` 不得在 blocker 未关闭时写 ready。

必须构造真实 known-bad fixtures。可以用临时目录复制当前 packet 后进行小范围 mutation。必须覆盖：

- `all_gradient_rows_backward_failed`;
- `missing_loss_graph_training_validity_report`;
- `hard_subgroup_all_centerA_lge_only_no_t2`;
- `diagnostic_rows_mixed_into_formal_best_variant`;
- `cine_copies_m5_no_new_registration_attempt`;
- `frame0_or_one_case_syn_marked_usable`;
- `untrained_voxelmorph_marked_usable`;
- `temporal_dictionary_ready_without_usable_registration`;
- `completion_ready_with_unresolved_blocker`.

Required output:

- `strict_validator_report.md`
- `strict_validator_report.csv`
- `strict_validator_known_bad_cases/README.md` or equivalent fixture summary; do not commit large fixture directories.

Each row must include:

`known_bad_case, fixture_or_mutation, validator_command, expected_exit_code, actual_exit_code, expected_failure, actual_failure_reason, pass_fail_closed`

Do not mark M7 follow-up2 ready unless every known-bad fixture fails with nonzero exit or controlled fail status.

## B. Training evidence validity and rerun decision

The latest M7 continued packet states that old training used graph-connected total loss and only logging metrics were detached. That may be true, but it is not enough for leaderboard-oriented repair because the metric deltas are negligible.

Update or create:

`loss_graph_training_validity_report.md`
`m7_followup2_training_rerun_decision.md`

The rerun decision must answer:

1. Did the original M7 training truly optimize the expanded loss graph?
2. Did each proposal/refiner/arbitration/dictionary component receive nonzero gradient on any real batch?
3. Did SRR actually open correction gates on hard cases, or did it remain near-anchor/no-op?
4. Did the trained variants materially change predictions in T2-present / CenterB / CenterC / remote-FP-positive rows?
5. If not, what architecture/training mechanism must be repaired before further training?

Hard rule:

If the original M7 training is graph-invalid, rerun at least the primary variant after fixing the loss. If graph-valid but scientifically no-op, do not pretend it succeeded. Instead run the targeted mechanism repair in Sections C/D and a short but real retraining/probe of the repaired primary variant.

Minimum retraining/probe requirement for follow-up2:

- Train at least one pre-specified primary variant after mechanism repair.
- The default primary variant is `m7_full_srr_context_arbitration` unless the M7 evidence shows it is unsafe; if unsafe, choose `m7_scar_precision_edema_safe` and justify.
- Minimum: `optimizer_steps >= 1200` and `train_loop_seconds >= 900`, or explicit `M7_FOLLOWUP2_NEEDS_MONITOR` if the job is still running.
- Preferred: `optimizer_steps >= 3000` and `train_loop_seconds >= 1800`.
- Use hardcase-aware sampling or batch construction so that T2-present and GT-positive edema appear in gradient sanity and validation events when available.
- Do not rank all variants if only one is retrained. Mark non-rerun variants `NOT_COMPARABLE_AFTER_FOLLOWUP2_REPAIR`.

Required files:

- `m7_followup2_training_rerun_decision.md`
- `followup2_training_adequacy.csv`
- `followup2_loss_component_by_step.csv`
- `followup2_loss_component_gradient_sanity.csv`
- `followup2_same_split_help_harm.csv`
- `followup2_hard_subgroup_metrics.csv`

## C. MyoPS mechanism no-op diagnosis and repair

The current M7/continued evidence is not enough because best-variant deltas are tiny and every row remains `NO_PROMOTION_SCIENTIFIC_UNRESOLVED`. The next executor must diagnose why SRR is not materially helping.

Create:

`m7_followup2_mechanism_noop_diagnosis.md`
`srr_contribution_by_case.csv`
`arbitration_opening_diagnostics.csv`
`proposal_refiner_effectiveness.csv`

Required diagnostics:

1. `anchor_delta_rate`: fraction of voxels changed vs nnU-Net anchor by class and case.
2. `correction_gate_open_rate`: scar/edema gate opening by case, subgroup, and variant.
3. `proposal_recall_proxy`: whether GT-positive scar/edema regions are inside proposal/ROI.
4. `remote_fp_suppression_proxy`: whether SRR reduces or increases remote false positives.
5. `refiner_delta_magnitude`: whether bounded delta is nonzero inside ROI.
6. `arbitration_chosen_source`: distribution over anchor/SRR/proposal/refiner per class and subgroup.
7. `prototype_margin`: positive-vs-safe-negative similarity margins on GT-positive and hard-negative regions.
8. `dictionary_family_mass`: shared/private/interaction mass by class and subgroup.
9. `T2_signal_use`: whether T2-private / T2 interaction evidence is active on T2-present edema rows and masked on no-T2 rows.
10. `hardcase_effect`: deltas on T2-present, CenterB/CenterC, remote-FP-positive, GT-positive edema, small lesion and large lesion strata.

Mechanism repair candidates, choose at least one if diagnosis shows no-op:

### C1. Gate opening calibration

If `anchor_delta_rate` and `correction_gate_open_rate` are near zero on high-uncertainty/hard cases, add a controlled gate-opening curriculum:

- initialize arbitration bias to open SRR only in high anchor-uncertainty or remote-FP-positive regions;
- add `loss_correction_opportunity` on train/OOF anchor-error masks;
- keep exact anchor fallback outside correction mask;
- prove no-T2 edema safety remains.

### C2. Hardcase-aware sampler

If training batches do not contain T2-present/GT-positive edema/CenterB/CenterC cases often enough, add deterministic hardcase-aware sampling:

- oversample T2-present complete and GT-positive edema cases;
- oversample remote-FP-positive scar cases;
- keep no-T2 cases for safety but do not let them dominate edema learning;
- record batch composition in `followup2_batch_composition.csv`.

### C3. Prototype / hard-negative memory repair

If prototype margins are weak or remote FP persists:

- refresh scar-safe-negative and edema-safe-negative banks from hard FP components;
- for edema, only use T2-present safe negatives;
- add margin loss on hard negatives;
- report prototype source and leakage checks.

### C4. Proposal/refiner ROI repair

If proposals miss GT-positive pathology or ROI is too small/too large:

- scar: smaller but recall-safe ROI with remote-FP penalty;
- edema: larger T2-conditioned context ROI, lower threshold, boundary uncertainty;
- report ROI volume ratio, recall proxy, precision proxy, and component burden.

The executor must not silently choose no repair. If all diagnostics show no-op, at least one repair is required. If no repair is feasible, write `M7_FOLLOWUP2_NEEDS_REVISION` and explain exact blocker.

## D. Formal validation and diagnostic hardcase decision boundary

Update:

`m7_case_pool_audit.csv`
`formal_val_coverage_limitations.md`
`hard_subgroup_coverage_report.md`

Formal-val rows may be used for metric decision. Diagnostic train/hardcase rows may only support mechanism diagnosis.

Required fields remain:

`case_id, split_role, center, modality_group, t2_present, c0_present, scar_gt_voxels, edema_gt_voxels, scar_gt_positive, edema_gt_positive, anchor_remote_fp_scar, anchor_remote_fp_edema, small_lesion_flag, large_lesion_flag, selected_for_formal_val, selected_for_diagnostic_hardcase, eligible_for_best_variant_decision, exclusion_reason`

Additional required fields:

`used_in_gradient_sanity, used_in_retraining, used_in_mechanism_diagnosis, eligible_for_promotion_decision`

Hard rule:

If formal-val coverage is still too small for T2-present/CenterB/CenterC conclusions, `best_variant_decision.md` must remain `NO_PROMOTION_SCIENTIFIC_UNRESOLVED` or `NEEDS_EVIDENCE`. Diagnostic hardcases cannot be used to select a challenge candidate.

## E. Cine registration follow-up2 escalation

The current continued packet attempted SimpleITK/ANTsPy/VoxelMorph availability, but no non-reference registration row was usable. That is honest but not enough for a leaderboard-oriented Cine route.

The follow-up2 executor must attempt a stronger cropped/anatomy-guided registration escalation before preserving the gap again.

Create or update:

`scripts/evaluation/run_srr_v3_m7_cine_registration_followup2.py`
`cine_registration_followup2_report.md`
`registration_same_subset_matrix.csv`
`temporal_dictionary_evidence.csv`

Required new registration candidates:

1. `heart_crop_center_of_mass_affine`
   - Crop to a heart/anatomy bounding box.
   - Align reference and moving anatomy by center of mass / translation / scale if possible.
   - This is a simple but robust baseline and must be attempted if masks/probabilities exist.

2. `heart_crop_SimpleITK_BSpline_or_Demons_tuned`
   - Run multi-resolution registration inside cropped ROI.
   - Use anatomy/probability distance maps if available.
   - Report before/after anatomy Dice/HD95 and image NCC.

3. `ANTsPy_SyN_cropped_subset`
   - If ANTsPy is installed, rerun on cropped ROI for at least 3 cases x 2 non-reference pairs when feasible.
   - If not installed, record import failure and environment.

4. `optical_flow_proxy_warp`
   - Still only proxy, but report whether it improves anatomy metrics.
   - It cannot be the only usable registration unless explicitly reclassified by reviewer in a later task.

5. `trained_or_trainable_voxelmorph_probe`
   - Only if trained weights exist or a short self-supervised training run is feasible.
   - Untrained VoxelMorph remains negative control.

A usable row must include:

`method, case_id, reference_frame_id, moving_frame_id, before_myo_dice, after_myo_dice, before_lv_dice, after_lv_dice, before_hd95, after_hd95, before_ncc, after_ncc, displacement_smoothness, jacobian_or_fold_proxy, roundtrip_proxy, runtime_seconds, usable_for_temporal_dictionary, failure_reason`

If at least one usable row exists, temporal dictionary follow-up2 is mandatory and must include warped non-reference evidence. If none exists, write `CINE_REGISTRATION_BLOCKED_AFTER_FOLLOWUP2_ESCALATION`, not ready.

## F. Temporal dictionary anti-cheat

If no usable non-reference registration row exists, `temporal_dictionary_evidence.csv` must contain only blocked rows.

If usable registration exists, temporal dictionary must contain:

- ED/reference anchor feature;
- selected non-reference frame id;
- warped image/probability/feature source;
- registration quality;
- frame quality;
- motion saliency;
- temporal representer slot usage;
- aggregation output summary;
- local class_1 myocardium proxy;
- hosted metric caveat.

Descriptor-only, no-warp, frame0-only dictionary cannot be marked ready.

## G. Required follow-up2 outputs

Write all outputs under:

`results/20260705_srr_v3_m7_training_and_cine_utilization/`

Required new or updated files:

- `result.md`
- `completion_check.md`
- `review_request.md`
- `MANIFEST.md`
- `commands_run.md`
- `strict_validator_report.md`
- `strict_validator_report.csv`
- `strict_validator_known_bad_cases/README.md` or equivalent fixture summary
- `loss_graph_training_validity_report.md`
- `m7_followup2_training_rerun_decision.md`
- `followup2_training_adequacy.csv`
- `followup2_loss_component_by_step.csv`
- `followup2_loss_component_gradient_sanity.csv`
- `followup2_batch_composition.csv` if retraining/probe uses hardcase-aware sampling
- `followup2_same_split_help_harm.csv`
- `followup2_hard_subgroup_metrics.csv`
- `m7_followup2_mechanism_noop_diagnosis.md`
- `srr_contribution_by_case.csv`
- `arbitration_opening_diagnostics.csv`
- `proposal_refiner_effectiveness.csv`
- `m7_case_pool_audit.csv`
- `formal_val_coverage_limitations.md`
- `hard_subgroup_coverage_report.md`
- `cine_registration_followup2_report.md`
- `registration_same_subset_matrix.csv`
- `temporal_dictionary_evidence.csv`
- `cine_metrics_summary.csv` if computed
- `failure_interpretation.md`

If a file is not applicable, it must exist with an explicit `NOT_APPLICABLE_WITH_REASON` section. Missing required files are not allowed.

## H. Completion states

`completion_check.md` may contain only:

- `M7_FOLLOWUP2_READY_FOR_REVIEW`
- `M7_FOLLOWUP2_NEEDS_REVISION`
- `M7_FOLLOWUP2_NEEDS_EVIDENCE`
- `M7_FOLLOWUP2_NEEDS_MONITOR`
- `M7_FOLLOWUP2_BLOCKED_BY_REVIEW_STATE`
- `M7_BLOCKED_BY_M6`

Do not write `M7_FOLLOWUP2_READY_FOR_REVIEW` if:

- strict validator does not run real known-bad fixtures;
- current training evidence is graph-invalid and no rerun/probe was done;
- mechanism no-op diagnosis is missing;
- SRR contribution remains near-zero and no repair was attempted;
- formal/diagnostic rows are mixed in formal decision;
- Cine registration follow-up2 escalation was not attempted;
- temporal dictionary is marked ready without usable registration;
- no-promotion/scientific unresolved boundary is missing;
- route promotion, hosted metric claim, validation packaging/upload, M8, fold expansion, challenge submission, scientific stop, or leaderboard readiness is claimed.

Finish by force-adding and locally committing only lightweight evidence plus necessary first-party helper/source/test files. Do not commit checkpoints, NIfTI predictions, upload packages, large logs, raw data, secrets, environment dumps, or runtime trees. Do not write `review.md`. Do not push.
```

---

# 3. Reviewer prompt: M7 follow-up2 audit

```text
这是独立只读 reviewer/auditor session。只审阅 `results/20260705_srr_v3_m7_training_and_cine_utilization/` 的 M7 follow-up2 packet 和必要 first-party helper/source/test files。不要补 executor 缺失文件，不要改代码，不要训练，不要 validation packaging/upload，不要 hosted metric claim，不要 route promotion，不要启动 M8。最后只写该目录下的 `review.md`。

必须读取：

- `prompts/shared/20260706_M7_followup2_leaderboard_repair_prompt.md`
- `prompts/shared/EXECUTOR_PROMPTS.md`
- `prompts/shared/REVIEWER_PROMPTS.md`
- `prompts/MILESTONE_REVIEW_PROTOCOL.md`
- `prompts/HANDOFF_GATE_POLICY.md`
- `prompts/GPT_HARD_GATE_PROMPT.md`
- latest M7 continued `review.md`
- M7 follow-up2 result files
- modified first-party loss/training/evaluation/Cine/validator/test files

## A. Scope gate

Reject if the packet claims M8, route promotion, hosted metric, validation packaging/upload, fold expansion, challenge submission, scientific stop, or leaderboard readiness.

## B. Strict validator gate

Reject unless a real validator is run against real mutated known-bad fixtures and returns nonzero exit/fail status. A current-packet boolean checklist is not acceptable.

Required known-bad fixtures:

- all gradients backward failed;
- missing loss graph validity report;
- all hard subgroup evidence CenterA/LGE-only/no-T2;
- diagnostic hardcases mixed into formal best-variant decision;
- Cine copied M5 without registration repair;
- frame0/one-case SyN marked usable;
- untrained VoxelMorph marked usable;
- temporal dictionary ready without usable registration;
- completion ready with unresolved blocker.

## C. Training validity / rerun gate

Reject if `loss_graph_training_validity_report.md` and `m7_followup2_training_rerun_decision.md` do not prove whether original M7 training was graph-connected.

If original training was not graph-valid, reject unless at least one primary variant was retrained/probed after repair and the packet does not rank non-rerun variants as comparable.

If original training was graph-valid but scientifically no-op, reject unless mechanism diagnosis and at least one targeted repair/probe are present, or a clear `NEEDS_EVIDENCE` state is used.

## D. MyoPS mechanism gate

Reject if `m7_followup2_mechanism_noop_diagnosis.md`, `srr_contribution_by_case.csv`, `arbitration_opening_diagnostics.csv`, and `proposal_refiner_effectiveness.csv` are missing or only natural language.

The reviewer must check:

- SRR correction gate opening on hard cases;
- anchor delta rate;
- proposal recall proxy;
- remote FP suppression proxy;
- refiner delta magnitude;
- prototype margins;
- dictionary family mass;
- T2 evidence use and no-T2 masking;
- T2-present / CenterB / CenterC / GT-positive edema / remote-FP-positive effects.

If SRR remains near-zero/no-op and no repair was attempted, reject.

## E. Formal validation / hardcase boundary gate

Reject if diagnostic hardcases are used for formal best-variant decision or promotion-style ranking.

Reject if formal-val coverage limitations are not explicit. Diagnostic hardcases may support mechanism interpretation only.

## F. Cine registration / temporal dictionary gate

Reject if follow-up2 does not attempt a stronger cropped/anatomy-guided non-reference registration escalation.

Reject if frame0-only, one-case SyN, untrained VoxelMorph, or optical-flow proxy is marked usable registration.

Reject if temporal dictionary is marked ready without at least one usable non-reference registration row.

If no usable registration remains after follow-up2 escalation, `CINE_REGISTRATION_BLOCKED_AFTER_FOLLOWUP2_ESCALATION` is acceptable only if the repair attempt is real and fully documented.

## G. Reviewer decision states

Allowed decisions:

- `M7_FOLLOWUP2_AUDITED_GO_FOR_NEXT_PLANNING`
- `M7_FOLLOWUP2_AUDITED_NEEDS_REVISION`
- `M7_FOLLOWUP2_AUDITED_NEEDS_EVIDENCE`
- `M7_FOLLOWUP2_AUDITED_NEEDS_MONITOR`
- `M7_FOLLOWUP2_AUDITED_NO_PROMOTION_SCIENTIFIC_UNRESOLVED`

`M7_FOLLOWUP2_AUDITED_GO_FOR_NEXT_PLANNING` only means GPT planner can inspect the repaired evidence. It does not authorize M8, route promotion, validation packaging/upload, hosted metric claim, fold expansion, challenge submission, scientific stop, or leaderboard readiness.
```

## 4. Merge note

This file is intentionally standalone so the GPT planner can inspect it before merging. If accepted, merge the executor block into `prompts/shared/EXECUTOR_PROMPTS.md` after the current M7 continued section, and merge the reviewer block into `prompts/shared/REVIEWER_PROMPTS.md` after the current M7 continued reviewer section. Keep the earlier M7 and M7 continued sections as historical records.
