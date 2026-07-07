# 20260707 M8: editor-grade SRR-v3 leaderboard sprint prompt

status: `NEW_SHARED_PROMPT_FOR_EXECUTOR_AND_REVIEWER`
source_result_dir: `results/20260705_srr_v3_m7_training_and_cine_utilization/`
source_review_decision: `M7_FOLLOWUP3_AUDITED_GO_FOR_NEXT_PLANNING`
planner: `ChatGPT/GPT thread`
priority: `MyoPS primary; Cine secondary but mandatory`
intended_merge_target:
  - `prompts/shared/EXECUTOR_PROMPTS.md`
  - `prompts/shared/REVIEWER_PROMPTS.md`

## 0. Editor-level judgment before M8

M7 follow-up3 is complete only as a planning gate. It fixed the two immediate follow-up2 failures: the monitor packet was re-aggregated after Slurm job completion, and the Cine branch executed a diagnostic temporal dictionary after a usable registration row appeared. It does **not** prove leaderboard readiness.

The latest M7 follow-up3 review explicitly records the remaining limits:

- the MyoPS probe ran only `3316` optimizer steps and about `900` train-loop seconds, far below a serious leaderboard training budget;
- hard subgroup evidence is narrow and does not establish T2-present / CenterB / CenterC superiority;
- per-case `anchor_delta_rate` is still not exported;
- Cine temporal dictionary evidence is one-case diagnostic proxy evidence with no hosted metric;
- no route promotion, validation upload, hosted metric claim, fold expansion, scientific stop, leaderboard readiness, or challenge-ready status is authorized.

M8 must therefore stop treating SRR-v3 as a runnable prototype and start treating it as a challenge-facing method under a top medical-imaging / AI / statistics journal standard. A packet that only adds more tables, smoke tests, monitor packets, or short probes is not an M8 completion.

M8 remains a milestone. It may implement code, run long training, run formal evaluation, and prepare a promotion decision packet. It must not upload validation, claim hosted metrics, package challenge validation, claim leaderboard readiness, or start M9 unless the reviewer explicitly grants the M8 audited decision. Any validation package or external upload still requires explicit human approval after M8 review.

---

# 1. Executor prompt: M8 editor-grade leaderboard sprint

```text
只执行 M8：editor-grade SRR-v3 leaderboard sprint after `M7_FOLLOWUP3_AUDITED_GO_FOR_NEXT_PLANNING`.

开始前必须确认：
- `results/20260705_srr_v3_m7_training_and_cine_utilization/review.md` 存在且包含 `M7_FOLLOWUP3_AUDITED_GO_FOR_NEXT_PLANNING`；
- `results/20260705_srr_v3_m6_myops_concrete_architecture_repair/review.md` 存在且包含 `M6_AUDITED_GO`；
- 当前任务是 M8，不是 validation packaging/upload，不是 hosted metric claim，不是 challenge submission，不是 scientific stop，不是 M9；
- 不要写 `review.md`，不要批准自己，不要启动 M9。

必须读取：
- `prompts/THREAD_BOOTSTRAP_ROUTE_IMAGE_PROTOCOL.md`
- `prompts/GPT_HARD_GATE_PROMPT.md`
- `prompts/HANDOFF_GATE_POLICY.md`
- `prompts/MILESTONE_REVIEW_PROTOCOL.md`
- `prompts/shared/EXECUTOR_PROMPTS.md`
- `prompts/shared/REVIEWER_PROMPTS.md`
- `results/20260705_srr_v3_m0_architecture_master_contract/architecture_contract.md`
- `results/20260705_srr_v3_m0_architecture_master_contract/interface_contract.md`
- `results/20260705_srr_v3_m0_architecture_master_contract/metric_contract.md`
- `results/20260705_srr_v3_m7_training_and_cine_utilization/review.md`
- `results/20260705_srr_v3_m7_training_and_cine_utilization/route_to_leaderboard_gap_report.md`
- `results/20260705_srr_v3_m7_training_and_cine_utilization/failure_interpretation.md`
- current SRR-v2, SRR-v2.5, SRR-v3 route diagrams from ChatGPT Project background / current thread visual materials, not merely repository filenames.

Before executing scientific work, restate the recovered route objective in `m8_route_objective.md`: SRR-MyoPS is availability-aware selective retrieval plus semantic representation retrieval bank, anatomy-guided lesion proposal, pathology-specific soft-ROI refinement, explicit loss/objective framework, and nnU-Net anchor/context/fallback. Cine is registration-aware temporal retrieval with warped non-reference evidence. Do not reduce SRR to postprocessing, table diagnostics, or a generic nnU-Net fallback.

## A. M8 hard rule: no short-run completion

M8 is a leaderboard sprint. The primary MyoPS training evidence must be a long, real run, not a short probe.

Minimum training budget for each promoted MyoPS candidate:

- `actual_optimizer_steps >= 12000`; and
- `train_loop_seconds >= 28800` (8 hours) for each primary promoted candidate; and
- at least `40` validation events or a documented validation interval schedule covering the full run; and
- at least one-batch overfit before the long run; and
- cache/provenance isolation for every candidate.

If local walltime policy requires splitting the run, use continuation checkpoints and aggregate cumulative train-loop seconds. Cumulative training for a promoted candidate must still be `>= 28800` seconds. If a job is pending/running, write `M8_NEEDS_MONITOR_NO_REVIEW`, do not write normal `review_request.md`, and do not mark complete. If a job finishes early before the 8-hour floor because of a bug, exception, resource loss, scheduler kill, or premature stopping, write `M8_NEEDS_REVISION_TRAINING_UNDERRUN` or `M8_RESOURCE_BLOCKED`, not ready.

Do not use loss plateau as an excuse for a sub-8-hour completion in M8. M8 may record plateau, but the route cannot be reviewed as leaderboard-sprint evidence unless the 8-hour floor or a user-approved resource exception is met.

## B. Implement every unresolved SRR-v3 architecture gap before or during training

Create `m8_architecture_gap_closure_table.csv` with fields:

`route_component, m7_status, required_m8_closure, code_path, runtime_evidence_path, closure_status, blocker_if_not_closed`

Every row below must be `CLOSED` before `M8_READY_FOR_REVIEW`; otherwise write `M8_NEEDS_REVISION_ARCHITECTURE_GAP`:

1. availability-aware modality handling and no-zero-fill semantics;
2. modality-specific stems for LGE/T2/C0 with exact modality-order contract;
3. strong encoder/context path with realistic channels, not tiny smoke;
4. nnU-Net anchor probability/logit/component/uncertainty interface;
5. shared/private/interaction semantic retrieval dictionary with runtime slot usage;
6. train/OOF prototype banks with non-empty scar positive/negative and T2-present edema positive/safe-negative evidence;
7. hard-negative memory refreshed from anchor/SRR false positives;
8. scar proposal with recall-safe local ROI and remote-FP control;
9. edema proposal with T2-conditioned larger context ROI and no-T2 block;
10. anatomy union/LV/RV distance/uncertainty support;
11. scar soft-ROI refinement with bounded crop and LGE-dominant evidence;
12. edema soft-ROI refinement with T2-dominant evidence and boundary uncertainty;
13. branch arbitration in which SRR, proposal, and refiner terms have measurable final-logit effect;
14. baseline-preserving fallback that exactly equals nnU-Net outside correction mask;
15. expanded loss objectives with graph-connected gradient evidence for each optimized component;
16. per-case tensor export for anchor delta, gate maps, proposal/refiner deltas, and final contribution;
17. no-T2 edema loss/proposal/refiner/final/decode/export safety;
18. formal same-split nnU-Net help/harm evaluator over broad hard subgroups;
19. Cine registration-aware temporal dictionary over a same-safe subset, not one-case proxy only.

A component cannot be marked closed by a natural-language claim or code-path existence alone. Each row must point to runtime evidence generated in M8 or a previously reviewed M7 artifact that remains valid and is explicitly reused.

## C. MyoPS implementation: fix the no-op route, then train serious variants

M8 must implement and train multiple real MyoPS variants. At minimum:

### Variant V1: `m8_full_srr_context_arbitration_longrun`

Purpose: full SRR-v3 route faithful to the diagrams.

Required features:
- full shared/private/interaction dictionary;
- nnU-Net anchor/context interface;
- train/OOF prototype banks;
- hard-negative memory from anchor/SRR false-positive components;
- correction-opportunity objective using anchor-error masks on training/OOF data;
- gate-opening curriculum on uncertain / anchor-error / remote-FP regions;
- proposal/refiner/arbitration final-logit contribution;
- no-T2 edema safety throughout.

### Variant V2: `m8_scar_precision_edema_safe_longrun`

Purpose: conservative leaderboard-safe route that protects scar and no-T2 stability while attempting T2-present edema improvement.

Required features:
- stronger scar hard-negative memory and remote-FP penalty;
- smaller scar ROI with recall floor;
- T2-present edema proposal/refiner with no-T2 inference block;
- conservative branch arbitration that falls back to nnU-Net when SRR evidence is weak;
- explicit component/HD95 guard.

### Variant V3: `m8_t2_centerC_edema_repair_longrun`

Purpose: attack the known edema bottleneck: T2-present complete cases and CenterB/CenterC edema.

Required features:
- deterministic oversampling of T2-present GT-positive edema and CenterB/CenterC cases;
- edema proposal threshold schedule with larger context ROI;
- T2-private and LGE-T2 interaction dictionary mass floor;
- safe edema negatives only from T2-present cases or non-myocardium/background; no no-T2 myocardium negatives;
- edema recall/precision/HD95 guard with scar non-regression.

If resources prevent all three 8-hour variants, run at least V1 and one of V2/V3 for 8 hours each, and mark the unrun variant `NOT_RUN_WITH_RESOURCE_REASON`. Do not rank an unrun or short-run variant as comparable. Cumulative MyoPS training for candidate selection must include at least two 8-hour primary runs unless the task ends with `M8_RESOURCE_BLOCKED`.

## D. Hardcase-aware sampler and batch-composition proof

Implement or harden a deterministic hardcase-aware sampler. It must record `m8_batch_composition.csv` with per-step/per-case rows.

Required sampling targets across the long run:

- T2-present complete cases: at least `30%` of training case selections when available;
- GT-positive edema cases: at least `20%` when available;
- CenterB/CenterC cases: at least `20%` when available;
- scar-positive / remote-FP-positive cases: at least `20%` when available;
- no-T2 cases: at least `10%` for safety checks, but no no-T2 myocardium may be used as edema negative supervision;
- LGE-only scar cases: included for scar robustness and missing-modality generalization.

If the dataset split cannot satisfy a quota, record exact counts and use the maximum feasible coverage. A long run with batches dominated by easy LGE-only empty-edema cases cannot be marked ready.

## E. Prototype, hard-negative, proposal, and refiner evidence

Before long training, build or refresh prototype banks and hard-negative memory. Write:

- `m8_prototype_bank_summary.json`
- `m8_hard_negative_memory_summary.csv`
- `m8_prototype_margin_by_case.csv`
- `m8_proposal_refiner_recall_precision.csv`

Required prototype evidence:

- scar positive count > 0;
- scar safe-negative count > 0;
- edema positive count > 0 from T2-present edema-positive cases;
- edema safe-negative count > 0 from T2-present safe negatives and/or non-myocardium/background;
- no no-T2 myocardium used as edema negative;
- hard-negative sources include at least remote FP, blood pool/background, normal myocardium, and artifact-like high-intensity cases when available.

Required proposal/refiner evidence:

- proposal recall proxy and precision proxy for scar and edema;
- ROI volume ratio;
- refiner delta magnitude;
- component count delta;
- remote FP delta;
- HD95 delta;
- Dice delta;
- case-level status.

If proposal recall is poor or ROI is full-volume/near-full-volume, the executor must repair proposal/ROI before claiming M8 ready.

## F. Loss graph, gradient, and contribution export

Write:

- `m8_loss_schedule.md`
- `m8_training_curves.csv`
- `m8_validation_events.csv`
- `m8_loss_component_by_step.csv`
- `m8_loss_component_gradient_sanity.csv`
- `m8_srr_contribution_by_case.csv`
- `m8_arbitration_opening_diagnostics.csv`

The loss schedule must include at least these stages:

1. evidence warmup;
2. proposal/dictionary learning;
3. soft-ROI refinement;
4. correction-opportunity and branch-arbitration calibration;
5. low-learning-rate stabilization.

Each optimized component must have graph-connected gradient evidence on real batches, including:

- scar proposal;
- T2-present edema proposal;
- scar refiner;
- T2-present edema refiner;
- branch arbitration / correction opportunity;
- anchor preservation outside ROI;
- remote-FP suppression;
- no-T2 edema safety;
- dictionary semantic / coverage / interaction losses;
- prototype margin / hard-negative loss.

`m8_srr_contribution_by_case.csv` must finally export per-case `anchor_delta_rate`, not `EVIDENCE_NOT_EXPORTED_PER_CASE`. Required fields:

`variant, checkpoint, decode_mode, case_id, center, modality_group, t2_present, class_name, anchor_delta_rate, final_delta_rate, correction_gate_open_rate, srr_weight_mean, proposal_weight_mean, refiner_weight_mean, fallback_weight_mean, final_logit_delta_abs_mean, roi_delta_abs_mean, proposal_recall_proxy, refiner_delta_magnitude, no_t2_edema_voxels, dice_delta, hd95_delta, remote_fp_delta, source_prediction_path`

If per-case contribution is not exported, M8 cannot be ready.

## G. Formal evaluation and candidate selection

M8 must evaluate on a broad same-split formal validation set, not only easy cases.

Minimum formal evaluation:

- full fold0 validation for Dataset501 if feasible; otherwise at least `24` stratified formal cases;
- must include T2-present complete cases;
- must include CenterB and CenterC if present in fold0 validation or a same-split formal evaluation pool;
- must include scar-positive and GT-positive edema cases when available;
- must include no-T2 safety cases;
- must include remote-FP-positive cases.

Write:

- `m8_formal_case_manifest.csv`
- `m8_same_split_help_harm.csv`
- `m8_hard_subgroup_metrics.csv`
- `m8_component_remote_fp_hd95_report.csv`
- `m8_best_variant_decision_table.csv`
- `m8_route_promotion_decision.md`

Primary metrics are exactly:

- `myops_scar`
- `myops_edema`
- `myocardium_cinemyops` as Cine diagnostic/secondary

Do not optimize or promote using foreground mean. Dice and HD95/remote-FP/component count must be read together.

A MyoPS candidate may be called `LOCAL_PROMOTION_CANDIDATE` only if it satisfies all of:

- scar Dice mean improves over same-split nnU-Net or scar HD95/remote-FP improves without Dice regression > 0.005;
- edema Dice mean on T2-present/GT-positive subgroup improves over same-split nnU-Net, or edema HD95/remote-FP improves without Dice regression > 0.005;
- no-T2 edema safety has zero new edema voxels / zero new no-T2 edema FP;
- component count and remote-FP do not catastrophically worsen;
- improvement is not confined to empty-GT cases;
- no label/export/compact-label artifact explains the gain;
- candidate was trained under the M8 long-run budget.

If no candidate passes, write `NO_PROMOTION_SCIENTIFIC_UNRESOLVED_OR_NEGATIVE` and a concrete next repair plan. Do not call the task complete by hiding negative results.

## H. Cine secondary but mandatory: expand temporal dictionary beyond one-case proxy

Cine is not optional. It does not block MyoPS training, but M8 cannot be `READY_FOR_REVIEW` unless Cine was advanced or honestly blocked with exact evidence.

M8 must expand follow-up3's one-case temporal dictionary into a small same-safe-subset diagnostic.

Minimum Cine work:

- at least `3` Cine cases if data allow;
- at least `2` non-reference frame pairs per case if frames allow;
- use ED/frame0 reference and selected non-reference frames;
- use the best available usable registration from follow-up3 or rerun registration if needed;
- produce warped non-reference image/probability/feature evidence;
- build temporal representer slots and aggregation output;
- compare frame0/ED control vs temporal aggregation;
- report local class-1 myocardium proxy and class-3 sanity where available;
- keep hosted metric caveat explicit.

Write:

- `m8_cine_case_manifest.csv`
- `m8_registration_same_subset_matrix.csv`
- `m8_temporal_dictionary_evidence.csv`
- `m8_temporal_aggregation_metrics.csv`
- `m8_frame0_vs_temporal_help_harm.csv`
- `m8_cine_decision.md`

If no usable non-reference registration remains, write `CINE_REGISTRATION_BLOCKED_AFTER_M8_ATTEMPT` with exact failed methods and metrics. If usable registration exists, temporal dictionary must be attempted. Descriptor-only, frame0-only, unwarped, one-case-only, or untrained VoxelMorph rows cannot be marked ready.

## I. Monitor, validation, and anti-laziness gates

Implement or update a strict M8 validator, e.g.:

`scripts/evaluation/validate_srr_v3_m8_leaderboard_sprint_packet.py`

It must accept `--packet <result_dir>` and exit nonzero on every blocker.

Known-bad fixtures must include:

- training run shorter than 8 hours marked ready;
- pending/running Slurm job with normal review request;
- completed job not re-aggregated into tracked CSVs;
- missing per-case `anchor_delta_rate`;
- same-split formal evaluation only on easy LGE-only empty-edema cases;
- no T2-present / CenterB / CenterC formal evidence when available;
- no-T2 edema safety violation;
- prototype bank lacks T2-present edema positives or safe negatives;
- proposal/refiner evidence is synthetic only;
- branch arbitration has no final-logit effect;
- Cine marked complete without same-safe-subset temporal dictionary or honest blocker;
- local promotion candidate without same-split nnU-Net comparison;
- route promotion based on empty-GT edema or foreground mean;
- validation packaging/upload or hosted metric claim without human approval.

Write:

- `m8_strict_validator_report.md`
- `m8_strict_validator_report.csv`
- `m8_validator_unit_test_report.md`

No `M8_READY_FOR_REVIEW` unless the validator passes on the real packet and fails closed on mutated known-bad fixtures.

## J. Required outputs

Write all outputs under:

`results/20260707_srr_v3_m8_editor_grade_leaderboard_sprint/`

Required files:

- `result.md`
- `completion_check.md`
- `review_request.md`
- `MANIFEST.md`
- `commands_run.md`
- `m8_route_objective.md`
- `m8_architecture_gap_closure_table.csv`
- `m8_training_plan.md`
- `m8_variant_matrix.csv`
- `m8_batch_composition.csv`
- `m8_prototype_bank_summary.json`
- `m8_hard_negative_memory_summary.csv`
- `m8_prototype_margin_by_case.csv`
- `m8_proposal_refiner_recall_precision.csv`
- `m8_loss_schedule.md`
- `m8_training_curves.csv`
- `m8_validation_events.csv`
- `m8_loss_component_by_step.csv`
- `m8_loss_component_gradient_sanity.csv`
- `m8_srr_contribution_by_case.csv`
- `m8_arbitration_opening_diagnostics.csv`
- `m8_formal_case_manifest.csv`
- `m8_same_split_help_harm.csv`
- `m8_hard_subgroup_metrics.csv`
- `m8_component_remote_fp_hd95_report.csv`
- `m8_best_variant_decision_table.csv`
- `m8_route_promotion_decision.md`
- `m8_cine_case_manifest.csv`
- `m8_registration_same_subset_matrix.csv`
- `m8_temporal_dictionary_evidence.csv`
- `m8_temporal_aggregation_metrics.csv`
- `m8_frame0_vs_temporal_help_harm.csv`
- `m8_cine_decision.md`
- `m8_strict_validator_report.md`
- `m8_strict_validator_report.csv`
- `m8_validator_unit_test_report.md`
- `m8_leaderboard_readiness_report.md`
- `m8_next_action.md`

If a required file is not applicable, it must exist and state `NOT_APPLICABLE_WITH_REASON`; but non-applicability cannot be used to bypass required MyoPS long-run training, broad formal evaluation, per-case contribution export, no-T2 safety, or mandatory Cine advancement.

## K. Completion states

`completion_check.md` may contain only:

- `M8_READY_FOR_REVIEW`
- `M8_NEEDS_MONITOR_NO_REVIEW`
- `M8_RESOURCE_BLOCKED`
- `M8_NEEDS_REVISION_TRAINING_UNDERRUN`
- `M8_NEEDS_REVISION_ARCHITECTURE_GAP`
- `M8_NEEDS_EVIDENCE_UNDERTRAINED`
- `M8_NEEDS_EVIDENCE_METRICS_INCOMPLETE`
- `M8_NEEDS_REVISION`
- `M8_BLOCKED_BY_M7`

Do not write `M8_READY_FOR_REVIEW` if:

- any primary MyoPS candidate used for decision trained for < 8 hours;
- fewer than two M8 primary MyoPS variants were trained for 8 hours each, unless the task is explicitly `M8_RESOURCE_BLOCKED`;
- required architecture gaps remain open;
- per-case contribution export is missing;
- formal evaluation lacks hard subgroup coverage when available;
- no-T2 edema safety regresses;
- all results are placeholders, smoke, synthetic, monitor, or stale M7 evidence;
- Cine was skipped or treated as optional;
- strict validator does not run real known-bad fixtures;
- route promotion, validation packaging/upload, hosted metric claim, fold expansion, challenge submission, scientific stop, leaderboard readiness, or challenge-ready status is claimed without the exact allowed gate.

Finish by force-adding and locally committing only lightweight evidence plus necessary first-party helper/source/test files. Do not commit checkpoints, NIfTI predictions, upload packages, raw data, secrets, environment dumps, whole runtime trees, or large logs. Do not write `review.md`. Do not push.
```

---

# 2. Reviewer prompt: M8 editor-grade leaderboard sprint audit

```text
这是独立只读 reviewer/auditor session。只审阅 `results/20260707_srr_v3_m8_editor_grade_leaderboard_sprint/` 的 M8 packet 和必要 first-party helper/source/test files。不要补 executor 缺失文件，不要改代码，不要训练，不要 validation packaging/upload，不要 hosted metric claim，不要 route promotion，不要启动 M9。最后只写该目录下的 `review.md`。

必须读取：

- `prompts/shared/20260707_M8_editor_grade_leaderboard_sprint_prompt.md`
- `prompts/shared/EXECUTOR_PROMPTS.md`
- `prompts/shared/REVIEWER_PROMPTS.md`
- `prompts/THREAD_BOOTSTRAP_ROUTE_IMAGE_PROTOCOL.md`
- `prompts/MILESTONE_REVIEW_PROTOCOL.md`
- `prompts/HANDOFF_GATE_POLICY.md`
- `prompts/GPT_HARD_GATE_PROMPT.md`
- latest M7 follow-up3 `review.md`
- all M8 required result files
- modified first-party model/training/evaluation/validator/test files

## A. Scope and route-fidelity gate

Reject if M8 claims validation upload, hosted metric, challenge submission, leaderboard readiness, scientific stop, or M9. Reject if SRR is reduced to a postprocess/fallback instead of the full SRR-v3 route. Verify `m8_route_objective.md` and `m8_architecture_gap_closure_table.csv` against SRR-v2/v2.5/v3 design intent.

## B. Long-run training gate

Reject if any promoted candidate trained for < 8 hours or lacks `actual_optimizer_steps >= 12000`, unless the packet is explicitly resource-blocked and does not request ready review. Reject if only one candidate was trained and the packet still ranks multiple variants as comparable. Reject if Slurm jobs are pending/running but a normal review request was created.

## C. Architecture gap closure gate

Reject if any required architecture row is not `CLOSED`, or if closure is code-path-only without runtime evidence. Pay special attention to train/OOF prototypes, hard-negative memory, branch arbitration final-logit effect, proposal/refiner runtime contribution, per-case anchor delta export, and no-T2 edema safety.

## D. MyoPS formal evidence gate

Reject if formal evaluation is narrow/easy-only, lacks T2-present/CenterB/CenterC/GT-positive/remote-FP coverage when available, or uses foreground mean/empty-GT edema to hide failure. Verify `m8_same_split_help_harm.csv`, `m8_hard_subgroup_metrics.csv`, and `m8_component_remote_fp_hd95_report.csv` against same-split nnU-Net.

A local promotion candidate is acceptable only if scar and edema evidence improves or safely preserves Dice while improving HD95/remote-FP/component burden, with no-T2 safety intact and no label/export artifact.

## E. Mechanism and contribution gate

Reject if `m8_srr_contribution_by_case.csv` lacks per-case `anchor_delta_rate`, final delta, gate opening, proposal/refiner weights, ROI delta, and no-T2 safety. Reject if proposal/refiner evidence is synthetic-only or stale. Reject if prototype banks lack T2-present edema positives/safe negatives.

## F. Cine mandatory secondary gate

Reject if Cine was skipped. Verify same-safe-subset registration and temporal dictionary expansion beyond one-case proxy when possible. If Cine is blocked, the blocker must be exact and evidence-based. If usable registration exists, temporal dictionary must be attempted.

## G. Strict validator gate

Reject unless the M8 strict validator exits 0 on the real packet and nonzero on real mutated known-bad fixtures covering short training, pending monitor packets, missing per-case contribution, missing hard subgroup evaluation, no-T2 violation, prototype failure, branch-arbitration no-op, skipped Cine, and unauthorized validation/hosted claims.

## H. Reviewer decision states

Allowed decisions:

- `M8_AUDITED_LOCAL_PROMOTION_CANDIDATE`
- `M8_AUDITED_GO_FOR_FOLD_EXPANSION_PLANNING`
- `M8_AUDITED_NO_PROMOTION_SCIENTIFIC_UNRESOLVED`
- `M8_AUDITED_NEEDS_REVISION`
- `M8_AUDITED_NEEDS_EVIDENCE`
- `M8_AUDITED_RESOURCE_BLOCKED`
- `M8_AUDITED_NEEDS_MONITOR`

`M8_AUDITED_LOCAL_PROMOTION_CANDIDATE` does not authorize validation upload or hosted metric claim. It only authorizes GPT/user planning for fold expansion, packaging design, or a separate human-approved validation submission milestone.
```

## 3. Merge note

This file is standalone. If accepted, merge the executor block into `prompts/shared/EXECUTOR_PROMPTS.md` after M7 follow-up3, and merge the reviewer block into `prompts/shared/REVIEWER_PROMPTS.md` after M7 follow-up3 reviewer. Keep earlier M7 sections as historical records.
