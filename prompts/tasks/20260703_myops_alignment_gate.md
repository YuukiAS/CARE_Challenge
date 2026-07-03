---
task_key: "20260703_myops_alignment_gate"
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
mechanism_class: "registration / feature alignment / MyoPS complete-case gate"
target_metric: "myops_scar, myops_edema"
same_split_baseline: "complete tri-modal subset, nnU-Net fold0 reference, and results/20260703_myops_audit; evidence not found if unavailable"
required_subgroups: ["complete C0+LGE+T2", "CenterB", "CenterC", "scar-positive", "edema GT-positive", "T2-present"]
required_secondary_metrics: ["Dice", "HD", "HD95", "component_count", "remote_FP", "alignment_sanity", "warp_smoothness", "Jacobian/folding proxy", "slice correspondence"]
required_evidence: ["result.md", "review.md", "MANIFEST.md", "alignment_diagnosis.md", "registration_metrics.csv", "warp_sanity.csv", "subgroup_metrics.csv", "visual_sanity_index.md", "run_log"]
forbidden_substitutes: ["translation-only completion", "image-similarity-only success", "registration without pathology delta", "warping labels into leakage", "preflight-only completion", "fold expansion or validation upload"]
promotion_gate: "Alignment can be promoted only if complete-case evidence shows cross-sequence mismatch is a major failure mode and a non-translation method improves pathology or critical secondary metrics without invalid warps."
failure_escalation_policy: "Start with diagnosis. If translation is near zero, escalate to slice/TPS/BSpline/Demons/feature-level warp within this task. If alignment is not the main bottleneck, write STOP_ALIGNMENT_NOT_PRIMARY rather than forcing registration."
allowed_next_states: ["EXECUTED_UNAUDITED", "NEEDS_EVIDENCE", "NEEDS_REVISION", "NEEDS_GPT_PLANNER", "STOP"]
auto_git_commit: false
auto_git_push: false
allow_git_commit: false
allow_git_push: false
---

# Task: MyoPS Complete-Case Alignment Gate

## Goal

不要再把 “registration” 当成一句泛泛建议，也不要用 translation negative result 结束。MyoPS 的 cross-sequence alignment 只在 complete C0+LGE+T2 子集上被证明确实是主要错误源时才进入主线；若进入，必须使用 slice/TPS/BSpline/Demons/feature-level warp 等 harder method，并用 pathology metrics 证明，不只看 image similarity。

本任务补上前一轮没有覆盖充分的问题：U-MyoPS/CAA-Seg 这类方法把 alignment 放在 pathology 前面，而当前 repo 主要只做了 Cine translation/descriptor 或 weak cascade。若目前低分来自 LGE/T2/C0 错位，现有四个 subtask 不足以证明或排除它。

## Required Reads

必须读取 handoff rules、CARE overlay、medical-imaging skill、`results/20260703_myops_audit/`（若存在）、rescue final status、Dataset501 complete tri-modal case list、nnU-Net and first-party predictions, U-MyoPS/CAA-Seg mechanism notes if available, evaluator/label export code。

## Phase 1: Diagnosis Before Registration

先做只读/CPU 诊断，不得直接上训练：

- complete tri-modal cases only.
- 对 LGE/C0/T2 做 header/spacing/origin/direction/shape audit.
- 计算 anatomy or intensity proxy 的 slice correspondence / center-of-mass / mutual information / edge alignment.
- 把 worst pathology failures 与 alignment mismatch 相关性写入 `alignment_diagnosis.md`。
- 如果 mismatch 与 failure 无关，输出 `STOP_ALIGNMENT_NOT_PRIMARY`，不要强行注册。

## Phase 2: Harder Alignment Candidates

若 Phase 1 支持 alignment hypothesis，至少尝试两类：

1. `slice_or_tps_alignment`: selective slice correspondence or TPS-style feature/image alignment.
2. `deformable_or_feature_warp`: SimpleITK BSpline/Demons 或 feature-level warp/STN; translation alone cannot count.
3. optional `alignment_expert_probe`: if safe, feed aligned features/predictions into a small pathology probe without changing evaluator.

必须记录 warp sanity: smoothness, folding/Jacobian proxy, runtime, failure cases, invalid warps.

## Evaluation

必须与 no-alignment baseline 和 translation baseline 对照。必须报告 scar/edema Dice, HD, HD95, component, remote FP, complete-modality CenterB/CenterC, and alignment sanity. Image similarity only is not success.

## Required Outputs

必须写：

- `results/20260703_myops_alignment_gate/result.md`
- `MANIFEST.md`
- `alignment_diagnosis.md`
- `registration_metrics.csv`
- `warp_sanity.csv`
- `subgroup_metrics.csv`
- `component_hd_by_case.csv`
- `visual_sanity_index.md`
- `failure_interpretation.md`

## Stop Conditions

可 stop 情况：complete-case geometry/evaluator evidence missing; non-translation candidates invalid and no safe fallback; alignment not correlated with pathology failure; invalid warps cannot be controlled; single job >8h. Otherwise, translation failure triggers escalation, not completion.

普通 executor 必须停在 `EXECUTED_UNAUDITED` and await review.
