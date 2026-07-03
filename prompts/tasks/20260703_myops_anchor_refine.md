---
task_key: "20260703_myops_anchor_refine"
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
mechanism_class: "proposal_refinement / nnU-Net anchored segmentation / cascade"
target_metric: "myops_scar, myops_edema"
same_split_baseline: "same-split nnU-Net fold0 reference, results/20260703_myops_audit, results/20260703_myops_fp_control, and optionally results/20260703_myops_srr_propose_refine; evidence not found if unavailable"
required_subgroups: ["all-case", "T2-present/complete", "GT-positive", "no-T2 empty-GT stability", "CenterB", "CenterC", "LGE-only", "complete"]
required_secondary_metrics: ["Dice", "HD", "HD95", "component_count", "remote_FP", "small_FP", "volume_ratio", "ROI coverage", "teacher/student delta"]
required_evidence: ["result.md", "review.md", "MANIFEST.md", "checkpoint", "prediction_path", "metric_csv", "run_log", "same_split_baseline", "cache_isolation", "label_export_QC", "train/val separation statement"]
forbidden_substitutes: ["continuing SRR parameter tuning", "copying nnU-Net as a selected custom route without measured delta", "preflight-only completion", "val-label-tuned thresholds as promoted method", "hard anatomy deletion", "compact-label-only gain", "validation upload or fold expansion"]
promotion_gate: "Audited evidence must compare directly against same-split nnU-Net. Promotion requires improvement in a target or critical secondary metric with no unacceptable pathology regression and clean label/export/T2 contract."
failure_escalation_policy: "If weak residual edits fail, escalate within this task to local ROI/high-resolution refiner. If nnU-Net artifacts or train/OOF separation are missing, stop at NEEDS_EVIDENCE. If no bounded variant can test the hypothesis, write NEEDS_GPT_PLANNER."
allowed_next_states: ["EXECUTED_UNAUDITED", "NEEDS_EVIDENCE", "NEEDS_REVISION", "NEEDS_GPT_PLANNER", "STOP"]
auto_git_commit: false
auto_git_push: false
allow_git_commit: false
allow_git_push: false
---

# Task: MyoPS nnU-Net Anchored Refine

## Goal

建立一个新的 MyoPS 主线机制：以 same-split nnU-Net/coarse anatomy 为 anchor，训练 pathology-specific postprocessor/refiner，专门解决 remote FP、component burden、HD95 和 class-specific scar/edema tradeoff。不要继续旧 SRR-v2 tuning ladder。

本任务必须在 `20260703_myops_audit` 给出证据后执行，并应优先读取 `20260703_myops_fp_control`、`20260703_myops_srr_propose_refine` 和 `20260703_myops_alignment_gate` 的结果。若这些证据缺失，先写 `NEEDS_EVIDENCE`，不要绕过前置 gate。

## Required Reads

读取 handoff rules、CARE overlay、medical-imaging skill、rescue final status、`results/20260703_myops_audit/`、`results/20260703_myops_fp_control/`、`results/20260703_myops_srr_propose_refine/`（若存在）、`results/20260703_myops_alignment_gate/`（若存在）、nnU-Net fold0 predictions/probabilities/checkpoints if available、Dataset501 split/evaluator/label export code。

## Authorized Scope

允许新增 first-party isolated code under `src/care_myocardium/refiner/` 或 `src/care_myocardium/postprocess/`，新增 training/evaluation scripts and Slurm jobs. 每个 GPU job 不超过 `08:00:00`，优先 `htzhulab`，最多四个并行 GPU tasks。所有 outputs 必须写入 `results/20260703_myops_anchor_refine/`。

## Mechanism Contract

必须是 nnU-Net anchored 或 anatomy/coarse-prior anchored，不得是 SRR-v2 参数变体。必须有以下机制：

- raw images + availability + nnU-Net/coarse prediction/probability/anatomy support as inputs, with source provenance recorded。
- soft myocardium/anatomy support; no hard deletion as the primary mechanism。
- scar and edema separate heads or separate candidate logic。
- edema supervision remains T2-aware; no no-T2 dense negative misuse。
- train/validation separation: promoted learned thresholds or component scoring must not train on fold0 validation labels。
- if `myops_srr_propose_refine` produced useful proposal metrics, the refiner may consume its proposal gates as inputs, but must still compare against unchanged nnU-Net.
- if `myops_alignment_gate` supports an alignment hypothesis, the refiner may consume aligned feature/probability inputs; otherwise do not add registration just because it is available.

## Required Variants

至少运行两个 formal variants，资源允许运行三个：

1. `nnunet_component_score_refiner`: conservative component scoring / residual correction around nnU-Net predictions。
2. `myocardium_roi_pathology_refiner`: soft ROI or cropped local refiner using myocardium/union support and raw LGE/T2/C0 context。
3. `scar_precision_edema_recall_dual_refiner`: class-specific heads; scar prioritizes precision/HD95, edema prioritizes T2-present recall with safe FP control。

如果 weak residual route 只产生 tiny deltas 或 harmful component growth，不能直接停止；必须尝试 local ROI/high-resolution refiner within this task, unless evidence or resources are missing and documented.

## Required Outputs

必须写：

- `results/20260703_myops_anchor_refine/result.md`
- `MANIFEST.md`
- `variant_matrix.md`
- `cache_contract.md`
- `training_summary.md`
- `metrics_summary.md`
- `subgroup_metrics.csv`
- `component_hd_by_case.csv`
- `teacher_student_delta.csv`
- `roi_coverage.csv`
- `label_export_qc.md`
- `failure_interpretation.md`
- checkpoints, prediction dirs, logs, config YAMLs for every formal variant

## Evaluation Gate

每个 variant 必须对照 unchanged nnU-Net fold0 reference。必须报告 scar all/positive/LGE-only/complete/CenterB/CenterC；edema all/GT-positive/T2-present/complete/CenterB/CenterC/no-T2 empty-GT stability；HD95/component/remote FP/small FP/volume ratio。

## Stop Conditions

只有以下情况可 stop：nnU-Net/coarse artifacts unavailable and cannot be safely generated; label/evaluator/export mismatch; train/validation separation cannot be maintained; predictions invalid; no-T2 edema contract violation cannot be fixed; single job exceeds 8h. Otherwise, variant failure triggers bounded escalation, not another smoke/preflight loop.

普通 executor 必须停在 `EXECUTED_UNAUDITED` and await review.
