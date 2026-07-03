---
task_key: "20260703_cine_motion"
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
mechanism_class: "cine_temporal / registration / motion_descriptor / anatomy prior"
target_metric: "myocardium_cinemyops or explicitly caveated local proxy"
same_split_baseline: "frame0/reference control and prior Cine motion results; evidence not found if unavailable"
required_subgroups: ["safe cases", "mismatch held out", "per-center if available", "reference-only", "non-reference-frame route"]
required_secondary_metrics: ["Dice", "HD", "HD95", "component_count", "volume_ratio", "warp_sanity", "runtime", "reference dominance", "temporal consistency"]
required_evidence: ["result.md", "review.md", "MANIFEST.md", "reference_frame_statement", "non_reference_frame_usage", "transform_or_motion_descriptor_path", "metric_csv", "run_log", "hosted_metric_caveat", "external_weight_license_or_evidence_not_found"]
forbidden_substitutes: ["frame0-only as temporal completion", "translation-only failure as final hardmode conclusion", "motion descriptor reported as registration", "non-reference frames scored directly against reference pathology GT without caveat", "preflight-only completion", "validation upload"]
promotion_gate: "Audited Cine route must use non-reference frames through motion/warping/temporal aggregation and beat reference-only local proxy without geometry or label caveat. Otherwise it is diagnostic-only."
failure_escalation_policy: "If translation or descriptor route fails, escalate to optical-flow, deformable, feature-level warp, anatomy-prior temporal aggregation, or temporal consistency route. If geometry/evaluator evidence is missing, stop at NEEDS_EVIDENCE. New scientific direction requires NEEDS_GPT_PLANNER."
allowed_next_states: ["EXECUTED_UNAUDITED", "NEEDS_EVIDENCE", "NEEDS_REVISION", "NEEDS_GPT_PLANNER", "STOP"]
auto_git_commit: false
auto_git_push: false
allow_git_commit: false
allow_git_push: false
---

# Task: Cine Motion Hardmode

## Goal

Cine 是次线，但不能再停在 frame0/reference-only、translation-only 或 descriptor-only。目标是给 `myocardium_cinemyops` 或明确 caveated local proxy 建立最小 hardmode temporal evidence：reference frame、non-reference frames、motion/warping/aggregation/consistency route、target head availability 都必须明确。

本任务不得阻塞 MyoPS 主线；可以在 MyoPS GPU 等待时推进。不要 validation upload，不要 upload-ready package。

## Required Reads

读取 handoff rules、CARE overlay、medical-imaging skill、`results/20260629_cine_motion_alignment/selection.md`、`results/20260629_cine_motion_pathology/selection.md`、`results/20260629_rescue_goal/final_status.md`、Cine safe cases and mismatch case list、Dataset502/Task026 evaluator/proxy code、existing Cine raw 4D data loaders、any local CineMA/CorSeg/Cine anatomy adapter artifacts if already present。

## Hardmode Contract

必须满足：

- 写明 reference frame selection。默认 ED/frame0 必须有依据。
- 至少一个 non-reference frame route 真实进入模型或 postprocessor。
- 若使用 descriptor，只能称 descriptor；不能称 completed registration。
- 若 translation baseline 接近零收益，必须继续 optical-flow/deformable/feature-level warp/temporal consistency 中至少一种 harder route，或者明确 `STOP` alignment route with evidence。
- frame0/reference-only control 只能是 baseline，不是 temporal completion。
- 若本地已有 CineMA/CorSeg/other cine anatomy prior，必须做 license/provenance check and adapter sanity；若没有，写 `evidence not found`，不要联网下载。

## Required Variants

至少完成两条 formal/proxy variants 和一个 baseline：

1. `cine_reference_control_recheck`: baseline only，用来确认 label/geometry/evaluator。
2. `cine_deformable_or_feature_warp`: SimpleITK Demons/BSpline、optical-flow displacement、VoxelMorph-style first-party unsupervised warp、或 feature-level warp 任选其一；必须有 warp sanity。
3. `cine_motion_descriptor_temporal_refiner`: frame difference / motion magnitude / strain-like descriptor + temporal aggregation/refiner。若 route 只做 descriptor，必须同时跑 reference-control delta。
4. optional `cine_anatomy_prior_temporal_adapter`: only if local licensed anatomy prior artifacts exist; use frame-wise anatomy prior + keyframe aggregation + temporal consistency. It is not a replacement for non-reference frame evidence.

如果 2 失败，不能直接结束；必须尝试 3。若 3 也失败，写 mechanism failure。若所有 registration/warping 工具不可用，必须写 dependency/resource audit 和 first-party descriptor fallback，但 selection 不能叫 registration success。

## Authorized Scope

允许新增 `scripts/evaluation/cine_motion_hardmode_20260703.py`、`scripts/training/run_cine_motion_refiner_20260703.py`、`src/care_myocardium/cine/` first-party helpers、`results/20260703_cine_motion/`。允许 CPU/GPU jobs，每个不超过 8 小时，最多两个 Cine GPU tasks in parallel and only when MyoPS budget is not blocked.

`allow_network: false`，不要下载外部 weights。若本地已有 external model artifacts，可只读使用并记录 license/provenance；否则写 `evidence not found`。

## Required Outputs

必须写：

- `results/20260703_cine_motion/result.md`
- `MANIFEST.md`
- `resource_audit.md`
- `safe_cases_used.csv`
- `reference_frame_contract.md`
- `motion_or_warp_metrics.csv`
- `warp_sanity.csv`
- `temporal_metrics_summary.md`
- `case_metrics.csv`
- `anatomy_prior_adapter_audit.md`
- `failure_interpretation.md`

必须报告 safe case count、mismatch held out count、runtime、warp smoothness/folding proxy if applicable、frame-to-reference similarity、anatomy consistency、reference dominance、component/HD95/volume ratio、hosted metric caveat。

## Stop Conditions

只有 safe subset geometry/evaluator 无法复现、所有 hardmode candidates 都无法运行且 no first-party fallback、predictions invalid、需要外部上传/不可审计权重、或单 job 超过 8 小时，才可 stop。Translation-only negative result is not a stop condition by itself.

普通 executor 必须停在 `EXECUTED_UNAUDITED` and await review.
