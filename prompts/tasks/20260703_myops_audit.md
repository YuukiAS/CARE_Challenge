---
task_key: "20260703_myops_audit"
project: "CARE_Challenge"
status: "READY"
task_type: "execution"
controller_mode: false
planner: "ChatGPT/GPT thread"
strategic_controller: "user-supervised GPT thread"
execution_controller: "Codex controller session via prompts/tasks/20260703_hardmode_goal.md"
executor: "separate Codex executor session/subagent"
auditor: "separate read-only Codex auditor session or ChatGPT reviewer"
risk_level: "medium"
allow_code_change: true
allow_shell_command: true
allow_network: false
allow_external_upload: false
requires_human_approval: false
review_required: true
mechanism_class: "audit / label-data-mechanism / architecture adequacy / missing_modality"
target_metric: "myops_scar, myops_edema"
same_split_baseline: "nnU-Net fold0 reference and rescue final status artifacts; evidence not found if unavailable"
required_subgroups: ["all-case", "T2-present/complete", "GT-positive", "no-T2 empty-GT stability", "CenterB", "CenterC", "LGE-only", "C0+LGE", "C0+LGE+T2"]
required_secondary_metrics: ["Dice", "HD", "HD95", "component_count", "remote_FP", "small_FP", "volume_ratio", "empty_prediction_rate"]
required_evidence: ["result.md", "review.md", "MANIFEST.md", "mechanism_audit.md", "label_export_qc.md", "architecture_gap_audit.md", "route_gap_table.csv", "failure_case_table.csv", "same_split_baseline", "code_path_audit", "cache_isolation"]
forbidden_substitutes: ["intention-only audit", "metrics without file paths", "compact-label proxy as challenge evidence", "missing evidence inferred from logs", "preflight-only conclusion", "executor self-review"]
promotion_gate: "Read-only review supports all audit claims and explicitly marks missing evidence as evidence not found."
failure_escalation_policy: "If same-split baseline, label/export path, architecture evidence, or evaluator evidence is missing, stop at NEEDS_EVIDENCE. If the audit shows a new scientific direction is needed, write NEEDS_GPT_PLANNER."
allowed_next_states: ["EXECUTED_UNAUDITED", "NEEDS_EVIDENCE", "NEEDS_REVISION", "NEEDS_GPT_PLANNER", "STOP"]
auto_git_commit: false
auto_git_push: false
allow_git_commit: false
allow_git_push: false
---

# Task: MyoPS Label/Data/Architecture Mechanism Audit

## Goal

在启动新训练或 postprocessor 前，给 MyoPS 做一次 evidence-gated 机制审计。上一轮 rescue final status 已经证明当前 custom SRR/cascade 路线没有超过 nnU-Net-relative gate；本任务要回答：问题是否来自 label/export/evaluator、T2/no-T2 监督机制、CenterB/CenterC data mechanism、architecture too shallow / wrong head design、prediction failure distribution，还是确实需要新的 nnU-Net anchored pathology postprocessor/refiner 或 SRR-ProposeRefine。

本任务是 MyoPS 主线的 Phase 1。它不做 validation upload、不做 fold expansion、不做新模型训练。允许新增只读/汇总脚本和审计表。

## Protocol And Gate References

必须读取 `AGENTS.md`、`prompts/AGENT_RULES.md`、`prompts/CHATGPT_RULES.md`、`prompts/HANDOFF_STATE_MACHINE.md`、`prompts/CARE_OVERLAY_GATES.md`、`.agents/skills/domains-medical-imaging-medical-imaging-deep-learning/SKILL.md`。

必须读取当前证据：`results/20260629_rescue_goal/final_status.md`、`completion_audit.md`、`route_status.csv`、SRR-v2/cascade selection 文件、Dataset501 split、evaluator、label/export code、same-split nnU-Net reference artifacts。

## Required Audit Questions

1. 当前所有 MyoPS route 是否确实完成？列出 result、selection、metric、prediction、log 证据路径。
2. raw label 与 compact label 的映射是否在 train/eval/export 中一致？写 `label_export_qc.md`，包括 evaluator path、decode mode、raw/compact mapping path、prediction label value set、challenge-facing caveat。
3. T2/no-T2 edema contract 是否被当前代码和结果满足？审查 loss、hard-negative mining、sampling、subgroup metrics。若发现违反，必须标为 `CONTRADICTED`。
4. CenterB/CenterC 与 modality pattern 是否解释 edema failure？必须报告 CenterB/CenterC、T2-present、complete、GT-positive、LGE-only/C0+LGE/C0+LGE+T2 的 Dice/HD95/component/remote FP。
5. nnU-Net fold0 reference 与 custom routes 的主要差距是否来自 remote FP/component burden、volume ratio、CenterC collapse、scar LGE-only failure、edema recall/precision，还是 label/evaluator问题？
6. architecture adequacy: 当前实现是否仍存在 shallow stem、1x1 pathology heads、proposal logits mixed directly into final logits、no independent lesion candidate/refinement、insufficient local ROI/high-resolution decoder、or no true trainable alignment expert。必须写 `architecture_gap_audit.md`。
7. 当前代码机制中哪些已经被实验证伪？不要只说“低于 baseline”，必须写机制解释。
8. 下一步是否应启动 `20260703_myops_fp_control`、`20260703_myops_srr_propose_refine`、`20260703_myops_alignment_gate`、`20260703_myops_anchor_refine`？分别写 GO/NO-GO 条件和所需证据。

## Authorized Scope

允许新增审计脚本和结果文件，例如 `scripts/evaluation/audit_myops_mechanism_20260703.py` 与 `results/20260703_myops_audit/`。允许读取现有 predictions、metrics、logs、json/csv summaries。允许运行 CPU 汇总和 evaluator 检查。不要改训练代码，除非只是为了让审计脚本可读地导入既有 helper。

## Forbidden Substitutes

不要训练、不要 validation upload、不要 upload-ready package、不要 fold expansion、不要改 label mapping/fold split/evaluator、不要用 compact-label proxy 当 challenge improvement、不要推断不存在的证据。缺失必须写 `evidence not found` 或 `未找到证据`。

## Evidence Requirements

必须写 `results/20260703_myops_audit/result.md`、`MANIFEST.md`、`mechanism_audit.md`、`label_export_qc.md`、`architecture_gap_audit.md`、`route_gap_table.csv`、`failure_case_table.csv`、`code_path_audit.md`、`next_route_gate.md`。

如果生成 review，请写 `results/20260703_myops_audit/review.md`。普通 executor 必须停在 `EXECUTED_UNAUDITED`。

## Completion Definition

完成是：审计表可复核、路径齐全、missing evidence 显式标出，并给出是否允许进入 `myops_fp_control` / `myops_srr_propose_refine` / `myops_alignment_gate` / `myops_anchor_refine` 的证据门。
