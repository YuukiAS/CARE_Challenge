---
task_key: "20260703_hardmode_goal"
project: "CARE_Challenge"
status: "READY"
task_type: "controller"
controller_mode: true
planner: "ChatGPT/GPT thread"
strategic_controller: "user-supervised GPT thread"
execution_controller: "Codex controller session"
executor: "separate Codex executor sessions/subagents"
auditor: "separate read-only Codex auditor sessions or ChatGPT reviewer"
risk_level: "high"
allow_code_change: true
allow_shell_command: true
allow_network: false
allow_external_upload: false
requires_human_approval: false
review_required: true
mechanism_class: "controller / CARE rescue hardmode"
target_metric: "myops_scar, myops_edema, myocardium_cinemyops"
same_split_baseline: "nnU-Net fold0 reference and rescue final status artifacts; evidence not found if unavailable"
required_subgroups: ["MyoPS all-case", "MyoPS T2-present/complete", "MyoPS GT-positive", "MyoPS no-T2 empty-GT stability", "MyoPS CenterB/CenterC", "Cine safe/mismatch status"]
required_secondary_metrics: ["Dice", "HD", "HD95", "component_count", "remote_FP", "small_FP", "volume_ratio", "proposal_recall_precision", "alignment_sanity", "label_export_QC"]
required_evidence: ["executor_result", "auditor_review", "controller_report", "checkpoint_or_explicit_no-training", "prediction_path", "metric_csv", "run_log", "same_split_baseline", "cache_isolation", "label_export_QC"]
forbidden_substitutes: ["preflight-only completion", "smoke/dryrun as route evidence", "continuing SRR temperature/gate/threshold tuning as a new mechanism", "compact-label proxy as challenge improvement", "no-T2 myocardium as edema negative", "translation-only alignment as hardmode completion", "frame0-only Cine as temporal completion", "executor self-review", "audit bypass", "validation upload or package generation"]
promotion_gate: "Every executor claim is audited. A MyoPS route can be promoted only if same-split nnU-Net comparison and CARE overlay evidence support it; diagnostic-only gains over weak SRR do not promote. Cine can promote only as a secondary temporal route with non-reference frame evidence."
route_promotion_gate: "Every executor claim is audited. A MyoPS route can be promoted only if same-split nnU-Net comparison and CARE overlay evidence support it; diagnostic-only gains over weak SRR do not promote. Cine can promote only as a secondary temporal route with non-reference frame evidence."
minimum_effective_training:
  min_optimizer_steps: 1000
  min_train_loop_seconds: 1800
  require_one_batch_overfit: true
  require_prediction_sanity: true
  require_loss_decrease: true
  allow_stop_without_training: false
experiment_adequacy_gate: "A trainable route must report one-batch/tiny-overfit or explicit not-applicable rationale; train_loop_seconds, max_steps, actual_steps, optimizer_steps, validation_events, loss_decrease; prediction foreground/volume/component/empty-rate sanity; proposal recall/precision/lesion-wise recall/outside-myocardium FP ratio for proposal routes; logs/provenance; and same-split baseline comparability."
route_negative_gate: "STOP_NO_* conclusions require experiment_adequacy_decision PASS, absent forbidden substitutes, same-split baseline comparison, failure not explained by undertraining/smoke/preflight/decode/cache/label/log/pipeline issues, and explicit auditor approval."
scientific_completion_gate: "Controller operational completion is not scientific completion. Scientific resolution must be SCIENTIFIC_PROMOTED, SCIENTIFIC_STOP_SUPPORTED, SCIENTIFIC_UNRESOLVED, SCIENTIFIC_UNDERTRAINED, SCIENTIFIC_PIPELINE_BUG, SCIENTIFIC_NEEDS_EVIDENCE, or SCIENTIFIC_NEEDS_REVISION."
diagnostic_publication_gate: "If audit/re-audit passes but no route is promoted, publish only the reviewed diagnostic packet needed for GPT planner review."
diagnostic_publication_scope: ["controller_report", "execution_plan", "subtask_result_review", "small_reviewed_markdown", "reviewed_repro_scripts"]
blocked_after_diagnostic_publication: ["validation_upload", "validation_packaging", "fold_expansion", "hosted_metric_claim", "label_or_evaluator_or_fold_split_change", "next_stage_training"]
failure_escalation_policy: "Escalate only along the bounded task policies below. If label/evaluator evidence is missing, return NEEDS_EVIDENCE. If all authorized mechanisms fail, write NEEDS_GPT_PLANNER; do not invent another research route."
executor_subtasks: ["prompts/tasks/20260703_myops_audit.md", "prompts/tasks/20260703_myops_fp_control.md", "prompts/tasks/20260703_myops_srr_propose_refine.md", "prompts/tasks/20260703_myops_alignment_gate.md", "prompts/tasks/20260703_myops_anchor_refine.md", "prompts/tasks/20260703_cine_motion.md"]
auditor_subtasks: ["results/20260703_hardmode_goal/subagents/auditor_prompt.md"]
controller_report_path: "results/20260703_hardmode_goal/controller_report.md"
allowed_next_states: ["EXECUTION_PLANNED", "EXECUTOR_RUNNING", "EXECUTED_UNAUDITED", "AUDITOR_RUNNING", "AUDITED_GO", "AUDITED_DIAGNOSTIC_PUBLISH", "NEEDS_EVIDENCE", "NEEDS_REVISION", "NEEDS_SUBAGENT_LAUNCH", "NEEDS_HUMAN_APPROVAL", "NEEDS_GPT_PLANNER", "STOP"]
auto_git_commit: true
auto_git_push: true
allow_git_commit: true
allow_git_push: true
---

# CARE Hardmode Goal Controller

## 背景

上一轮 rescue goal 已完成并停止：MyoPS 为 `STOP_NO_ROUTE_BEATS_BASELINE_SIGNAL`，Cine 为 `CINE_REFERENCE_ONLY`。这不是继续同一条 SRR 参数梯子的授权。新的 goal 只能验证新的机制假设：MyoPS 优先转向 label/data/architecture mechanism audit、nnU-Net anchored false-positive control、SRR evidence-engine propose-refine、complete-case alignment gate、pathology-specific postprocessor/refiner；Cine 作为次线补 motion/warping/temporal aggregation 证据。

本 controller task 是给 Codex controller session 的入口。Controller 只负责执行 GPT 已写好的任务，不得成为战略规划者，不得在失败后自行发明新路线。

## 必读协议

必须读取：

- `AGENTS.md`
- `prompts/AGENT_RULES.md`
- `prompts/CHATGPT_RULES.md`
- `prompts/HANDOFF_ROLES.md`
- `prompts/HANDOFF_STATE_MACHINE.md`
- `prompts/CONTROLLER_TASK_PROTOCOL.md`
- `prompts/DIAGNOSTIC_PUBLICATION_GATE.md`
- `prompts/EXPERIMENT_ADEQUACY_GATE.md`
- `prompts/CARE_OVERLAY_GATES.md`
- `.agents/skills/domains-medical-imaging-medical-imaging-deep-learning/SKILL.md`
- `results/20260629_rescue_goal/final_status.md`
- `results/20260629_rescue_goal/completion_audit.md`
- `results/20260629_rescue_goal/gpu_action_status.md`
- `results/20260629_rescue_goal/route_status.csv`

## Controller 工作流

1. 读取本 controller task 和六个 executor subtasks。
2. 写 `results/20260703_hardmode_goal/execution_plan.md`，列出任务顺序、资源预算、cache isolation、审核计划。
3. 尝试创建或启动 separate executor sessions 和 read-only auditor sessions。若运行时不支持自动 subagent launch，则写：
   - `results/20260703_hardmode_goal/subagents/myops_audit_executor_prompt.md`
   - `results/20260703_hardmode_goal/subagents/myops_fp_control_executor_prompt.md`
   - `results/20260703_hardmode_goal/subagents/myops_srr_propose_refine_executor_prompt.md`
   - `results/20260703_hardmode_goal/subagents/myops_alignment_gate_executor_prompt.md`
   - `results/20260703_hardmode_goal/subagents/myops_anchor_refine_executor_prompt.md`
   - `results/20260703_hardmode_goal/subagents/cine_motion_executor_prompt.md`
   - `results/20260703_hardmode_goal/subagents/auditor_prompt.md`
   然后设置状态 `NEEDS_SUBAGENT_LAUNCH` 或 `NEEDS_HUMAN_APPROVAL`，不要假装已经完成 executor/auditor 分离。
4. 严格按顺序执行：
   - Phase 0/1: `20260703_myops_audit`。没有 audit 的机制结论，不允许启动 expensive route promotion。
   - Phase 2A: `20260703_myops_fp_control`。优先用现有 nnU-Net / first-party predictions 做 fast, auditable false-positive control。
   - Phase 2B: `20260703_myops_srr_propose_refine`。这是 SRR 的唯一继续方式：SRR 降位为 evidence engine，必须接病种 proposal dictionaries、negative-space learning、soft cascade refinement。不得再跑 dictionary-only/tuning-only variants。
   - Phase 2C: `20260703_myops_alignment_gate`。只在 complete tri-modal evidence 显示 cross-sequence mismatch 是主要瓶颈时推进 alignment expert；translation-only 负结果不能作为 hardmode completion。
   - Phase 3: `20260703_myops_anchor_refine`。只有 Phase 1/2 的证据支持 trainable refinement 时启动；否则写 `NEEDS_EVIDENCE` 或 `NEEDS_GPT_PLANNER`。
   - Phase 4: `20260703_cine_motion`。Cine 是次线；可在 MyoPS GPU 等待期间并行 CPU/轻 GPU 工作，但不得阻塞 MyoPS 主线。
5. 每个 executor 写自己的 `results/<task_key>/result.md` 和 `MANIFEST.md` 后，必须停在 `EXECUTED_UNAUDITED`。
6. 每个 auditor 对应写 `results/<task_key>/review.md`，只读审核 claim、files、commands、metrics、logs、label/export QC 和 forbidden substitutes。
7. Controller 汇总 `controller_report.md`，包括所有 subagent prompt/session/log/result/review 路径、claim ledger、audited decision、controller_run_status、operational_completion_status、experiment_adequacy_decision、route promotion decision、route negative decision、scientific_resolution_status、diagnostic publication decision、git commit/push decisions、published files、blocked actions、next_required_action，以及 no route promotion/no publication 的原因。

## MyoPS 主线优先级

第一优先级不是再跑 SRR-v2 参数变体，而是确认为什么 nnU-Net baseline 仍然是 practical baseline，并尝试可解释的 nnU-Net anchored improvement 与 SRR-ProposeRefine：

- raw/compact label 与 export QC
- T2/no-T2 edema supervision mechanism
- CenterB/CenterC 与 modality pattern failure audit
- nnU-Net prediction remote FP/component/HD95 error profile
- pathology-specific false-positive control
- SRR as evidence engine, not final dense segmenter
- scar/edema proposal dictionaries and negative prototype memory
- soft myocardium/anatomy support，不做 hard deletion
- complete-case alignment only when error audit supports it
- trainable component veto 或 ROI refiner 只能用 train/OOF evidence 训练；fold0 val label 只能评估，不能被当成调参训练源，除非结果显式标为 diagnostic-only

## Cine 次线优先级

Cine 不允许再以 frame0/reference-only 或 descriptor-only 作为 temporal completion。必须报告 reference frame、non-reference frames、motion/warping/aggregation/consistency route、target head 是否存在。若 translation/descriptor 失败，必须继续到 optical-flow/deformable/feature-level warp 或明确停止 Cine motion route。

## 禁止动作

- 不要 validation submission。
- 不要 upload-ready package。
- 不要 fold expansion。
- 不要改变 label mapping、fold split、evaluator。
- 不要把 no-T2 myocardium 当 edema negative。
- 不要用 compact-label proxy 当 challenge improvement。
- 不要用 executor 自评替代 review。
- 不要把 `STOP_*` 或 `selected_variant: none` 的旧路线改名后继续跑。
- 不要把 translation-only alignment、smoke、preflight、dryrun 当作 completion。

## Promotion / Stop 判定

MyoPS 可以进入下一轮候选，仅当：

- 与 same-split nnU-Net reference 直接对照；
- 至少一个 primary metric 或 critical secondary metric 有可解释正信号；
- 另一个 pathology 没有灾难性退化；
- HD95/component/remote FP 不是靠 hard deletion 或 val-label tuning 伪造；
- label/export QC 与 no-T2 edema contract 通过 review。

若只超过旧 SRR、没有接近或改善 nnU-Net，结果只能是 diagnostic，不得 promotion。

若 formal training 或 proposal/refinement 证据未通过 `experiment_adequacy_gate`，不得写 `STOP_NO_SIGNAL`、`STOP_NO_PROPREF_SIGNAL`、`STOP_NO_CLEAN_ANCHOR_SIGNAL`、`STOP_NO_ROUTE_BEATS_BASELINE_SIGNAL` 或等价科学负结论。此时 controller 可 operationally complete，但 scientific status 必须是 `SCIENTIFIC_UNDERTRAINED`、`SCIENTIFIC_UNRESOLVED`、`SCIENTIFIC_NEEDS_EVIDENCE`、`SCIENTIFIC_NEEDS_REVISION` 或 `SCIENTIFIC_PIPELINE_BUG`。

Cine 可以作为 secondary route 推进，仅当：

- non-reference frames 真实参与；
- motion/warping/temporal aggregation 证据存在；
- frame0/reference-only baseline 被明确对照；
- hosted metric caveat 写清楚。

## Git 策略

本 controller task 显式允许 controller 在 audit/re-audit 通过、无人类审批阻塞、且满足 `route_promotion_gate` 或 `diagnostic_publication_gate` 时按授权范围 commit 和 push。

若 `route_promotion_gate` 不满足但 `diagnostic_publication_gate` 满足，controller 可以只发布 reviewed diagnostic packet；commit message 和 `controller_report.md` 必须写明 `diagnostic publication only; no route promotion`。这不代表 route 被选中、不代表 validation-ready、不授权 validation packaging/upload、fold expansion、hosted metric claim、label/evaluator/fold split change 或 next-stage training。

若 no route promotion 且 no diagnostic publication gate，则不得 commit/push。若未 commit/push，必须在 `controller_report.md` 写明原因。
