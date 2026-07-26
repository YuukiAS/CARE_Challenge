---
task_key: 20260726_care_nnunet5f_control
task_kind: scientific_milestone
task_type: validation_calibration_control
controller_mode: coordinator_acceptance_owner
milestone_number: null
milestone_id: null
status: READY_FOR_CONTROLLER
risk_level: high
route_change: false
scientific_decision_scope: calibration_control
execution_mode: controller_supervised
requires_execution_controller: true
controller_is_coordinator: true
executor_slots: 1
executor_count: 1
parallel_execution_allowed: false
executor_plan_path: prompts/tasks/20260726_care_nnunet5f_control_executor_plan.yaml
mapper_slots: 1
mapper_required: false
architecture_impact: none
wiki_update_required: false
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
experiment_adequacy_gate: "Must prove Dataset501 folds 0-4 checkpoint_best.pth exist, share trainer/plans/configuration/channel/label semantics, and are invoked through nnUNetv2_predict probability ensemble."
route_negative_gate: NOT_AUTHORIZED
scientific_completion_gate: "This task only calibrates the strong baseline; it cannot become the final CARE method."
diagnostic_publication_gate: LOCAL_LIGHTWEIGHT_PACKET_ONLY
diagnostic_publication_scope: ["Markdown", "CSV", "JSON", "SHA256 text", "local package manifest"]
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

# 第 1 次：5-fold nnU-Net 强基线校准包

## Execution Contract

本任务只回答一个问题：此前排行榜上的 fold0-only nnU-Net 是否低估了强基线。这里的 full data nnU-Net 只能写成“5-fold full-training-information probability ensemble”，不能写成单个 fold0，也不能虚假写成 220 例训练出的 fold_all single model。最终产物是一个本地 upload-ready control 包，供用户手动上传；Controller 不得自动上传、不得 claim hosted metric、不得把这个 control 包包装成最终 CARE 方法。

启动前如果当前界面支持 Plan Mode，先进入 Plan Mode；若不支持，在 `controller_bootstrap_snapshot.md` 记录原因。随后同步并记录：

```bash
git fetch origin main --prune
git status --short
git rev-parse HEAD
git rev-parse origin/main
git log -5 --oneline origin/main
```

如果工作树存在与本任务冲突的未提交修改，不得覆盖，先报告并使用隔离输出目录或安全 worktree。本任务写入统一根目录：

```text
results/20260726_care_fullinfo_nnunet_and_care_scf/nnunet5f_control/
results/submissions/care_myocardium_validation/workspaces/<timestamp>__nnUNet5F-control/
results/submissions/care_myocardium_validation/upload_ready/<timestamp>__nnUNet5F-control/
```

## Controller Prompt

你是第 1 次提交控制包的 Controller。先读取 `AGENTS.md`、`START_HERE_FOR_GPT.md`、`GPT_PLANNER_CARE_PROTOCOL.md`、`prompts/FINAL_OUTPUT_READABILITY_POLICY.md`、`prompts/AGENT_FLOW_V2_PROTOCOL.md`、`prompts/HANDOFF_GATE_POLICY.md`、`prompts/GPT_HARD_GATE_PROMPT.md`、`prompts/routes/README.md`、`prompts/routes/handoffs/CURRENT.md`、`prompts/routes/ROUTE_ANTI_LAZINESS_PROTOCOL.md`、`prompts/routes/ROUTE_HARD_REQUIREMENTS_MATRIX.md`、`routes/README.md`、`wiki/README.md`、`.agents/skills/slurm-routing-partition/SKILL.md`、`scripts/submission/README.md`、`scripts/submission/prepare_care_myocardium_validation.py` 和 `jobs/submission/prepare_care_myocardium_validation.sh`。

必须审计 Dataset501 的五折 checkpoint：

- `fold_0/checkpoint_best.pth`
- `fold_1/checkpoint_best.pth`
- `fold_2/checkpoint_best.pth`
- `fold_3/checkpoint_best.pth`
- `fold_4/checkpoint_best.pth`

五折必须来自相同 trainer、plans、configuration、Dataset501、channel order 和 label mapping。必须检查 `splits_final.json` 或当前协议 split 是否确认为每折 176 train / 44 val。必须审计是否存在真正 fold_all checkpoint；若不存在，不得启动 fold_all 长训练，不得把五折 ensemble 称作 all-data single model。

MyoPS control 推理必须使用 `folds: [0,1,2,3,4]`、`checkpoint_best.pth`、`nnUNetTrainer_500epochs`、`nnUNetPlans`、`3d_fullres` 和 nnU-Net 原生 softmax/probability ensemble。先确认 `scripts/submission/prepare_care_myocardium_validation.py` 会把五个 folds 传入 `nnUNetv2_predict -f 0 1 2 3 4`，由 nnU-Net 原生逻辑完成概率集成；不得实现五个硬标签的 majority vote。

CineMyoPS 分支必须与此前可信提交中的 Cine pathology-direct 分支完全一致：相同模型、相同 checkpoint、相同预测、相同后处理、相同 NIfTI hash。如果旧 Cine prediction tree 仍存在，直接复用并核对 SHA256；如果不存在，按旧 manifest 的真实配置重建。不得顺便更换 Cine 模型，因为本次 control 实验必须只改变 MyoPS 分支。

注意 `jobs/submission/prepare_care_myocardium_validation.sh` 当前默认 `CARE_ROOT=/overflow/htzhu/CARE` 与本工作树规则冲突。若使用该 wrapper，必须显式设置 `CARE_ROOT=/users/a/e/aereinh/CARE`，或修复为安全默认并记录 diff；不得写入 `/overflow`。

必须生成但不上传：

```text
results/submissions/care_myocardium_validation/upload_ready/<timestamp>__nnUNet5F-control/CARE-Myocardium-OrganAgent.zip
```

本任务至少输出：

```text
results/20260726_care_fullinfo_nnunet_and_care_scf/nnunet5f_control/nnunet5f_checkpoint_manifest.json
results/20260726_care_fullinfo_nnunet_and_care_scf/nnunet5f_control/nnunet5f_inference_receipt.json
results/20260726_care_fullinfo_nnunet_and_care_scf/nnunet5f_control/nnunet5f_geometry_audit.csv
results/20260726_care_fullinfo_nnunet_and_care_scf/nnunet5f_control/nnunet5f_label_audit.json
results/20260726_care_fullinfo_nnunet_and_care_scf/nnunet5f_control/nnunet5f_package_manifest.json
results/20260726_care_fullinfo_nnunet_and_care_scf/nnunet5f_control/nnunet5f_zip_sha256.txt
results/20260726_care_fullinfo_nnunet_and_care_scf/nnunet5f_control/control_vs_previous_submission_delta.md
results/20260726_care_fullinfo_nnunet_and_care_scf/nnunet5f_control/validation_upload_instruction.md
```

manifest 必须明确写：

```yaml
model_role: calibration_control
myops_model: nnUNet_5fold_probability_ensemble
folds: [0, 1, 2, 3, 4]
checkpoint: checkpoint_best.pth
single_all_data_model: false
validation_upload_performed: false
```

Controller 最终报告必须先用自然中文说明：control 是否真实完成、是否确实使用 folds 0-4、它是 five-fold probability ensemble 还是存在真正 fold_all、Cine 是否保持不变、ZIP 路径是什么、哪些上传动作仍未授权。只允许本地轻量 commit，不允许 push。

完全结束、validator/aggregation/commit 状态确认后，写 `results/20260726_care_fullinfo_nnunet_and_care_scf/nnunet5f_control/notification_brief.json`，并由既有 notifier 向 `1155246312@link.cuhk.edu.hk` 发送一封中文短邮件；不得为本任务另开 notifier，不得在 submitted、pending、running、monitor 包或未完成 aggregation 阶段通知。

## Executor Worker Contract

Executor 只能执行五折 checkpoint 审计、Cine hash 复用或重建、MyoPS 5-fold probability ensemble 推理、submission tree/zip 生成、几何/标签/SHA 审计和轻量报告写入。Executor 不能上传 validation，不能声明 hosted 分数，不能把 control 包命名为 CARE-SCF，不能启动 fold_all 长训练。

## Mapper Contract

本任务 `mapper_required: false`。如果 Executor 修改了 submission/export 行为或 wrapper 默认路径，Controller 必须把 architecture/export 影响升级为 mapper 检查，或在 `controller_report.md` 解释为什么没有 architecture impact。
