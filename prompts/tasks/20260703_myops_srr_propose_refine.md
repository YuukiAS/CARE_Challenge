---
task_key: "20260703_myops_srr_propose_refine"
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
mechanism_class: "proposal_refinement / SRR evidence engine / soft cascade"
target_metric: "myops_scar, myops_edema"
same_split_baseline: "same-split nnU-Net fold0 reference plus rescue final status and results/20260703_myops_audit; evidence not found if unavailable"
required_subgroups: ["all-case", "scar-positive", "edema GT-positive", "T2-present/complete", "no-T2 empty-GT stability", "CenterB", "CenterC", "LGE-only"]
required_secondary_metrics: ["Dice", "HD", "HD95", "component_count", "remote_FP", "small_FP", "volume_ratio", "proposal_recall", "proposal_precision", "lesion-wise recall", "outside-myocardium FP ratio"]
required_evidence: ["result.md", "review.md", "MANIFEST.md", "architecture_contract.md", "checkpoint", "prediction_path", "metric_csv", "run_log", "proposal_metrics", "hardneg_memory", "cache_isolation", "label_export_QC"]
forbidden_substitutes: ["dictionary-only variant", "temperature/gate/mix-weight tuning as mechanism", "full-image dense head as final route", "compactness-only fix", "preflight-only completion", "no-T2 myocardium as edema negative", "hard ROI deletion", "fold expansion or validation upload"]
promotion_gate: "Audited evidence must show that proposal and refinement improve more than weak SRR: proposal recall/precision, component/remote-FP, HD95, and Dice must be reported against same-split nnU-Net. No promotion for gains that only beat old SRR while remaining far below nnU-Net without mechanism benefit."
failure_escalation_policy: "If proposal dictionaries collapse or recall fails, adjust within the three-stage schedule and negative memory policy. If soft ROI refinement fails after required variants, write NEEDS_GPT_PLANNER rather than another SRR tuning ladder."
allowed_next_states: ["EXECUTED_UNAUDITED", "NEEDS_EVIDENCE", "NEEDS_REVISION", "NEEDS_GPT_PLANNER", "STOP"]
auto_git_commit: false
auto_git_push: false
allow_git_commit: false
allow_git_push: false
---

# Task: SRR-ProposeRefine Hardmode

## Goal

这是 SRR 继续的唯一授权方式。SRR 不再作为最终 full-volume dense segmenter，而降位为 stage-one evidence engine。必须新增 pathology-specific proposal dictionaries、negative prototype memory、safe hard-negative replay、soft ROI crop/refinement、scar/edema 双 refinement heads。

本任务针对目前最好 scar Dice 仍约 0.3 的不合理现象：如果思想正确但实现低分，最大嫌疑不是“SRR思想错”，而是当前实现只做 evidence selection，没有 lesion proposal、negative-space discrimination 和 local lesion formation。

## Required Reads

必须读取 handoff rules、CARE overlay、medical-imaging skill、`results/20260629_rescue_goal/final_status.md`、`results/20260629_srr_v2_unet_core/*/selection.md`、`results/20260703_myops_audit/`（若存在）、`src/care_myocardium/models/srr_v2_unet.py`、`src/care_myocardium/models/srr_myops.py`、`src/care_myocardium/models/pathology_heads.py`、`scripts/training/run_srr_myops_fold0.py`、hard-negative mined components、nnU-Net same-split artifacts。

## Mechanism Contract

必须实现或明确记录不可实现原因：

1. `shared_evidence_trunk`: 可以复用 SRR-v2/UNet/nnU-Net-like encoder，但只输出 evidence features，不直接决定 final pathology。
2. `scar_proposal_dictionary`: LGE-driven positive and negative prototypes; scar uses small high-precision candidates.
3. `edema_proposal_dictionary`: T2-conditioned positive prototypes; edema uses larger recall-oriented candidates; no-T2 myocardium is not an edema dense negative.
4. `negative_prototype_memory`: separate safe negatives for outside myocardium, normal myocardium, blood pool, LGE bright artifact, T2 texture noise, remote FP islands.
5. `soft_roi_refinement`: scar uses smaller high-resolution myocardium-neighborhood crop; edema uses larger dilated ROI and boundary uncertainty. No hard deletion.
6. `three_stage_schedule`: evidence warmup, proposal dictionary learning, refinement learning, then short low-LR calibration.

## Required Variants

至少跑三个 formal variants，每个 job 不超过 8 小时，优先 `htzhulab`：

1. `srr_propref_shared_dual_dict`: shared evidence trunk + scar/edema proposal dictionaries + soft ROI refinement.
2. `srr_propref_scar_precision`: scar negative memory and small ROI emphasized, edema conservative shared proposal.
3. `srr_propref_no_proto_cascade`: no prototype control, conservative anatomy-first soft cascade baseline; this proves whether prototype dictionaries matter.

若任一 variant proposal recall < baseline 或 component burden 不降，必须解释是 positive prototype collapse、negative over-suppression、ROI too strict、or evidence trunk failure。不得直接再开 temperature/mix-weight tuning。

## Loss And Sampling Requirements

必须实现安全负样本策略：

- scar negatives may include outside myocardium, normal myocardium, blood pool, LGE bright artifacts, remote FP islands.
- edema safe negatives include outside myocardium, blood pool, and T2-present myocardium sufficiently far from GT edema.
- no-T2 myocardium is never an edema dense negative.

必须报告 proposal-level metrics before final Dice：proposal recall, proposal precision, lesion-wise recall, outside-myocardium FP ratio, component count, remote FP, volume ratio.

## Required Outputs

必须写：

- `results/20260703_myops_srr_propose_refine/result.md`
- `MANIFEST.md`
- `architecture_contract.md`
- `variant_matrix.md`
- `training_schedule.md`
- `metrics_summary.md`
- `proposal_metrics.csv`
- `subgroup_metrics.csv`
- `component_hd_by_case.csv`
- `hardneg_memory.csv`
- `roi_coverage.csv`
- `label_export_qc.md`
- `failure_interpretation.md`
- checkpoints, prediction dirs, logs, configs for every formal variant

## Completion Definition

完成时必须给出 `AUDIT_FOR_PROMOTION`、`DIAGNOSTIC_ONLY`、`ROUTE_TO_ANCHOR_REFINE`、`NEEDS_EVIDENCE` 或 `STOP_NO_PROPREF_SIGNAL`。普通 executor 必须停在 `EXECUTED_UNAUDITED` and await review.
