---
task_key: 20260726_care_scf_v2_docker_alignment
task_kind: scientific_milestone
task_type: care_scf_v2_hosted_result_directed_docker_alignment
controller_mode: coordinator_acceptance_owner
milestone_number: null
milestone_id: null
status: BLOCKED_UNTIL_CARE_SCF_V1_HOSTED_RESULT_RECORDED
risk_level: high
route_change: false
scientific_decision_scope: promotion_candidate
execution_mode: controller_supervised
requires_execution_controller: true
controller_is_coordinator: true
executor_slots: 1
executor_count: 1
parallel_execution_allowed: false
executor_plan_path: prompts/tasks/20260726_care_scf_v2_docker_alignment_executor_plan.yaml
mapper_slots: 1
mapper_required: true
architecture_impact: system
wiki_update_required: true
diagram_update_required: false
slurm_runtime_continuity_required: true
continuity_backend: slurm_dependency
review_mode: none
reviewer: none
review_required: false
allow_git_commit: true
auto_git_commit: true
allow_git_push: false
auto_git_push: false
allow_diagnostic_push: false
route_promotion_gate: NOT_AUTHORIZED
experiment_adequacy_gate: "CARE-SCF v2 may only change disease-specific deterministic thresholds/prototype selection/postprocessing based on recorded hosted v1 scar/edema results plus train-side OOF evidence."
route_negative_gate: NOT_AUTHORIZED
scientific_completion_gate: "Controller may produce a v2 candidate and Docker equivalence evidence; final upload/release remains user decision."
diagnostic_publication_gate: LOCAL_LIGHTWEIGHT_PACKET_ONLY
diagnostic_publication_scope: ["source/config/tests", "Docker smoke receipts", "Markdown", "CSV", "JSON", "SHA256 text", "local package manifest"]
blocked_after_diagnostic_publication: ["validation_upload", "docker_upload", "hosted_metric_claim", "route_promotion", "scientific_stop", "git_push"]
planning_review_required: false
planning_reviewer: none
planning_review_path: null
planning_review_token: null
planning_reviewed_commit: null
validation_upload_authorized: false
docker_upload_authorized: false
hosted_metric_claim_authorized: false
---

# 第 3 次：CARE-SCF v2 与最终 Docker 一致性

## Execution Contract

本任务只能在 CARE-SCF v1 已本地完成、用户手动上传第 2 次 validation、并记录 hosted scar/edema 分项结果后启动。它的目标不是重新发明架构，而是根据第 2 次的 `myops_scar` / `myops_edema` 分项结果做病种定向 CARE-SCF v2，并让本地候选、upload-ready ZIP 和最终 Docker 默认方法完全一致。

必须存在以下前置文件：

```text
results/20260726_care_fullinfo_nnunet_and_care_scf/care_scf_v1/completion_check.md
results/20260726_care_fullinfo_nnunet_and_care_scf/care_scf_v1/care_scf_package_manifest.json
results/20260726_care_fullinfo_nnunet_and_care_scf/hosted/validation_attempt_2_care_scf_v1.json
```

第三个文件必须记录官方返回的 `myops_scar`、`myops_edema` 和 `myocardium_cinemyops`。若 hosted 结果不存在或字段缺失，立即停止为 `BLOCKED_HOSTED_RESULT_REQUIRED_FOR_V2`，不得用本地 OOF 结果假装 hosted 结果。

本任务写入：

```text
results/20260726_care_fullinfo_nnunet_and_care_scf/care_scf_v2/
results/submissions/care_myocardium_validation/workspaces/<timestamp>__CARE-SCF-v2/
results/submissions/care_myocardium_validation/upload_ready/<timestamp>__CARE-SCF-v2/
docker/CARE-SCF/
```

## Controller Prompt

你是 CARE-SCF v2 和最终 Docker 对齐任务的 Controller。启动前如果当前界面支持 Plan Mode，先进入 Plan Mode；若不支持，在 bootstrap 中记录原因。先同步 `origin/main`，读取第 1 次 control packet、第 2 次 CARE-SCF v1 packet、官方 hosted v1 分项结果记录、submission 入口、Docker 相关文件、Slurm skill 和 Mapper skill。

病种定向规则：

- 如果 v1 scar 优于或持平 control 且 edema 退化，只允许调整 edema 的组件阈值、negative prototype selection 或确定性后处理；scar 默认冻结为 v1，除非本地安全门发现 v1 scar 有明确运行缺陷。
- 如果 v1 edema 优于或持平 control 且 scar 退化，只允许调整 scar 的组件阈值、negative prototype selection 或确定性后处理；edema 默认冻结为 v1。
- 如果 scar 和 edema 都退化，必须返回 `BLOCKED_CARE_SCF_V1_HOSTED_UNSAFE`，不得用 v2 强行包装 baseline。
- 如果 scar 和 edema 都有改善或持平，只允许小范围稳定性修复和 Docker 对齐，不得扩展成新训练。
- 任何 v2 参数仍必须能由训练 OOF grid、v1 组件 receipt 和 hosted 分项方向解释；不得用官方 validation case 级 GT 调参。

v2 仍必须满足 CARE-SCF 的核心机制：组件级 positive/negative prototype evidence、retain/suppress/replace、MMRD 可靠标签约束、no-T2 edema safety、病种独立 exact fallback、机制激活非零、逐病例逐病种 receipt。若 v2 最终所有病例 exact fallback 到 anchor，必须返回 `BLOCKED_MECHANISM_INACTIVE`。

本地候选通过后，生成但不上传：

```text
results/submissions/care_myocardium_validation/upload_ready/<timestamp>__CARE-SCF-v2/CARE-Myocardium-OrganAgent.zip
```

Docker 要求：

- 最终 Docker 默认执行 CARE-SCF v2，不是 nnU-Net control，也不是 CARE-SCF v1 的旧配置。
- Docker 内包含 5-fold nnU-Net inference、MoSAIC proposal inference、CARE-SCF component retrieval and arbitration、pathology-specific exact fallback、official raw label export、MyoPS 与既有 Cine branch 完整输出。
- `predict.sh` 必须覆盖原始输入到最终 NIfTI 全链路。
- 不得依赖 `/users/a/e/aereinh/...`、`/overflow/htzhu/CARE` 或外部绝对 runtime 路径。
- 权重随 Docker 或按官方允许方式正确提供；输入、输出、标签、目录符合官方规范。
- GPU/CPU fallback 行为必须明确。
- 单病例峰值显存、时间和总运行时间要实测。
- Docker 输出必须与非 Docker CARE-SCF v2 输出逐病例 hash 或 voxel equality 一致。

必须生成：

```text
results/20260726_care_fullinfo_nnunet_and_care_scf/care_scf_v2/care_scf_v2_config.yaml
results/20260726_care_fullinfo_nnunet_and_care_scf/care_scf_v2/hosted_v1_result_binding.json
results/20260726_care_fullinfo_nnunet_and_care_scf/care_scf_v2/disease_directed_change_log.md
results/20260726_care_fullinfo_nnunet_and_care_scf/care_scf_v2/mechanism_activation_audit.csv
results/20260726_care_fullinfo_nnunet_and_care_scf/care_scf_v2/component_decisions.csv
results/20260726_care_fullinfo_nnunet_and_care_scf/care_scf_v2/oof_casewise_metrics.csv
results/20260726_care_fullinfo_nnunet_and_care_scf/care_scf_v2/oof_model_summary.csv
results/20260726_care_fullinfo_nnunet_and_care_scf/care_scf_v2/help_harm.csv
results/20260726_care_fullinfo_nnunet_and_care_scf/care_scf_v2/geometry_audit.csv
results/20260726_care_fullinfo_nnunet_and_care_scf/care_scf_v2/label_audit.json
results/20260726_care_fullinfo_nnunet_and_care_scf/care_scf_v2/care_scf_v2_package_manifest.json
results/20260726_care_fullinfo_nnunet_and_care_scf/care_scf_v2/care_scf_v2_zip_sha256.txt
docker/CARE-SCF/
results/20260726_care_fullinfo_nnunet_and_care_scf/care_scf_v2/docker_build_receipt.json
results/20260726_care_fullinfo_nnunet_and_care_scf/care_scf_v2/docker_runtime_benchmark.csv
results/20260726_care_fullinfo_nnunet_and_care_scf/care_scf_v2/docker_prediction_equivalence.csv
results/20260726_care_fullinfo_nnunet_and_care_scf/care_scf_v2/docker_smoke_report.md
results/20260726_care_fullinfo_nnunet_and_care_scf/care_scf_v2/strict_validator_report.json
results/20260726_care_fullinfo_nnunet_and_care_scf/care_scf_v2/controller_report.md
results/20260726_care_fullinfo_nnunet_and_care_scf/care_scf_v2/completion_check.md
```

Controller 最终报告必须先用中文回答：v2 是否根据第 2 次 hosted scar/edema 分项结果做了病种定向调整；哪些病种改善、持平或恶化；哪些病例被帮助或伤害；v2 是否仍真实激活 CARE-SCF 机制；Docker 是否真的运行 v2；Docker 与非 Docker 输出是否一致；v2 是否值得占用第三次 validation submission；两个上传/上传 Docker 动作仍未授权；v2 ZIP 路径是什么。

完全结束、validator/aggregation/commit 状态确认后，写 `results/20260726_care_fullinfo_nnunet_and_care_scf/care_scf_v2/notification_brief.json`，并由既有 notifier 向 `1155246312@link.cuhk.edu.hk` 发送一封中文短邮件；不得在 submitted、pending、running、monitor 包或未完成 aggregation 阶段通知。

## Executor Worker Contract

Executor 只能做病种定向的小范围 v2 修复、validation prediction/zip、Docker build/smoke/equivalence 和证据写入。不得引入新大型训练、不得上传 validation、不得上传 Docker、不得 push、不得把 v1 hosted 失败包装成成功。

## Mapper Contract

Mapper 必须核对最终生产调用图和 Docker 调用图完全一致：默认入口、配置、权重、nnU-Net folds、MoSAIC proposal、CARE-SCF v2 arbitration、fallback、raw-label export、Cine branch、输入输出布局和路径依赖。wiki 只能记录本地候选和 Docker smoke/equivalence 状态，不得写 hosted metric claim 或最终 release claim。
