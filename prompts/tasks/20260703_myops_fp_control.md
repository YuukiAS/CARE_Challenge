---
task_key: "20260703_myops_fp_control"
project: "CARE_Challenge"
status: "READY"
task_type: "execution"
controller_mode: false
planner: "ChatGPT/GPT thread"
strategic_controller: "user-supervised GPT thread"
execution_controller: "Codex controller session via prompts/tasks/20260703_hardmode_goal.md"
executor: "separate Codex executor session/subagent"
auditor: "separate read-only Codex auditor session or ChatGPT reviewer"
risk_level: "high"
allow_code_change: true
allow_shell_command: true
allow_network: false
allow_external_upload: false
requires_human_approval: false
review_required: true
mechanism_class: "proposal_refinement / pathology postprocessor"
target_metric: "myops_scar, myops_edema"
same_split_baseline: "same-split nnU-Net fold0 artifacts and results/20260703_myops_audit; evidence not found if unavailable"
required_subgroups: ["all-case", "T2-present/complete", "GT-positive", "no-T2 empty-GT stability", "CenterB", "CenterC", "LGE-only"]
required_secondary_metrics: ["Dice", "HD", "HD95", "component_count", "remote_FP", "small_FP", "volume_ratio"]
required_evidence: ["result.md", "review.md", "MANIFEST.md", "prediction_path", "metric_csv", "postprocess_config", "same_split_baseline", "label_export_QC", "run_log"]
forbidden_substitutes: ["val-tuned threshold reported as challenge improvement", "hard deletion without full metrics", "compact-label-only gain", "preflight-only completion", "no-T2 samples as edema dense negatives"]
promotion_gate: "Audited fold0 evidence must show interpretable improvement over same-split nnU-Net on at least one target or secondary metric without unacceptable regression in the other pathology."
failure_escalation_policy: "If fixed rules fail, escalate within this task to train/OOF component scoring or route evidence to SRR-ProposeRefine / local refiner input generation. If evidence is missing, stop at NEEDS_EVIDENCE. If a new mechanism is needed, write NEEDS_GPT_PLANNER."
allowed_next_states: ["EXECUTED_UNAUDITED", "NEEDS_EVIDENCE", "NEEDS_REVISION", "NEEDS_GPT_PLANNER", "STOP"]
auto_git_commit: false
auto_git_push: false
allow_git_commit: false
allow_git_push: false
---

# Task: MyoPS nnU-Net-Anchored FP Control

## Goal

验证一个新的短期假设：当前实用起点仍是 nnU-Net；可增益空间应来自 pathology-specific component/remote-FP control、soft anatomy support、raw-label/export-safe postprocessing，而不是继续 SRR-v2 温度、gate、mix weight、threshold 微调。

本任务是 fast fixed-rule / component-scoring phase，不替代 `20260703_myops_srr_propose_refine` 或 `20260703_myops_anchor_refine`。如果固定规则失败，必须升级到 train/OOF component scoring，或把 component/action evidence 转交给 SRR-ProposeRefine / anchor-refine 的 local ROI/refiner inputs。不能只写“结果差”后停止。

## Dependencies

必须读取 handoff rules、`prompts/CARE_OVERLAY_GATES.md`、medical-imaging skill、`results/20260629_rescue_goal/final_status.md`、`results/20260703_myops_audit/next_route_gate.md`（若存在）。若 audit 缺失且 same-split baseline 路径无法确认，写 `NEEDS_EVIDENCE`。

## Authorized Scope

允许新增 `scripts/evaluation/run_myops_fp_control_20260703.py`、`scripts/evaluation/evaluate_myops_postprocess_20260703.py` 和 `results/20260703_myops_fp_control/`。允许读取现有 predictions、probabilities/logits、anatomy masks/priors、Dataset501 labelsTr for fold0 evaluation and train-side summaries. 不允许 validation upload 或 fold expansion。

## Required Variants

至少评估以下路线，并与 unchanged nnU-Net baseline 对照：

1. `fixed_soft_anatomy_support`: soft myocardium/union support、distance-to-anatomy、small/remote component rules；不做 hard deletion。
2. `scar_precision_component_score`: scar 专属 component scoring，目标是降低 scar remote FP/HD95，Dice 下降必须受限。
3. `edema_recall_safe_fp_control`: edema 专属 rule，保持 T2-present/GT-positive recall，禁止把 no-T2 myocardium 当 edema dense negative。
4. 若 1-3 没有正信号，升级到 `train_oof_component_score` 或写 `NEEDS_EVIDENCE`：只可用 train/OOF 或固定规则学习 component score；fold0 validation labels 只能评估，不能作为 promoted route 的训练来源。

## Required Outputs

必须写 `result.md`、`MANIFEST.md`、`postprocess_config.yaml`、`metrics_summary.md`、`subgroup_metrics.csv`、`component_hd_by_case.csv`、`component_action_table.csv`、`label_export_qc.md`、`failure_interpretation.md`。每个候选必须有 prediction directory，或写明 `no_prediction_exported` 原因。

必须报告 scar all/positive/LGE-only/complete/CenterB/CenterC；edema all/GT-positive/T2-present/complete/CenterB/CenterC/no-T2 empty-GT stability；HD/HD95/component/remote FP/small FP/volume ratio。

## Completion Definition

完成时给出：`AUDIT_FOR_PROMOTION`、`DIAGNOSTIC_ONLY` 或 `ROUTE_TO_ANCHOR_REFINE`。普通 executor 必须停在 `EXECUTED_UNAUDITED`。
