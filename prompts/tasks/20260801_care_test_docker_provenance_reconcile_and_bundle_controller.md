---
task_key: 20260801_care_test_docker_provenance_reconcile_and_bundle
task_kind: scientific_milestone
task_type: provenance_reconciliation_and_cross_machine_docker_bundle
status: AUTHORIZED_BY_USER
risk_level: high
route_change: false
scientific_decision_scope: promotion_candidate
execution_mode: controller_supervised
requires_execution_controller: true
controller_is_coordinator: true
executor_slots: 1
executor_count: 1
parallel_execution_allowed: false
executor_plan_path: null
mapper_slots: 1
mapper_required: true
architecture_impact: system
wiki_update_required: true
diagram_update_required: false
slurm_runtime_continuity_required: true
continuity_backend: tmux_watcher
planning_review_required: false
review_required: false
allow_git_commit: true
auto_git_commit: true
allow_git_push: true
auto_git_push: true
allow_diagnostic_push: true
new_training_authorized: false
frozen_inference_authorized: true
one_gpu_inference_job_authorized: true
workstation_bundle_generation_authorized: true
validation_upload_authorized: false
docker_upload_authorized: false
organizer_email_send_authorized: false
hosted_metric_claim_authorized: false
supersedes_task: 20260801_care_test_docker_server_bundle
supersedes_terminal_token: NNUNET_PROVENANCE_REPLAY_MISMATCH
---

# CARE 测试 Docker：nnU-Net 来源纠偏与跨机器 Bundle 继续执行 Controller

## 一、Planner 判断

上一任务正确证明了一个有限结论：当前 `Dataset501` 五折 `checkpoint_best.pth` fresh 推理无法逐体素复现历史 package A 的完整六类数组，15 例中只有 4 例完整数组相同；这意味着历史 `0.6691` edema 行不能继续直接绑定到当前 fresh 资产。

但旧合同把“历史完整六类数组逐体素一致”错误地设成了整个 Docker 打包的唯一入口。生产 MyoPS 组合实际只消费 nnU-Net 的 anatomy 类 `1/2/3` 和 pure-edema 类 `4`，scar 类 `5` 会被 MoSAIC scar 替换。因此必须先做病种/通道级来源审计，而不能用完整数组差异直接判定所有被消费的 nnU-Net 来源都不可用。

即使历史 package A 的 used channels 仍无法复现，也必须把两件事拆开：

```text
historical hosted lineage
!=
current deployable source reproducibility
```

历史 hosted lineage 可以保持未闭合；当前冻结五折模型只要能够从明确的 checkpoint/config/source 两次确定性重放，就可以作为一个新的、诚实标注的测试 Docker 候选继续打包。此时严禁把它声称为历史 `0.6691` 的复现。

本任务的目标不是为旧数字找借口，而是：

1. 用有限、可审计的来源矩阵查明完整数组不一致主要来自哪些标签；
2. 尽最大合理努力追溯 package A 的原始生成命令与现有冻结资产；
3. 分别给出历史来源状态和当前部署来源状态；
4. 不再让历史 lineage 未闭合阻止 Cine、生产源码、sentinel、transfer bundle 和工位 Docker 构建；
5. 最终生成真实 `SERVER_BUNDLE_READY.json`，但其中必须诚实记录 hosted lineage 是否仍未闭合。

## 二、硬边界

必须遵守：

- 当前仓库 `/users/a/e/aereinh/CARE`，只在 `main` 工作。
- 不写 `/overflow/htzhu/CARE`；只有现有 manifest 明确指向历史只读资产且当前 `/users` 无对应证据时，才允许只读检查，不得形成运行依赖。
- 不使用 sudo，不修改 `/etc`，不再尝试服务器 Docker/rootless Docker、Podman、Buildah、Apptainer。
- 不进行新训练，不选择新 checkpoint，不做阈值搜索，不使用 validation GT。
- 不上传网盘，不发送组织方邮件，不上传 validation/Docker，不作 hosted metric claim。
- 允许使用现有 GPU allocation；若不存在，只允许一个冻结推理 Slurm 作业，所有候选 replay 串行执行。
- 不得因 MyoPS 历史 lineage 未闭合而再次停止 Cine 15/15、生产源码和 bundle 准备。
- 不得把历史 package A prediction 当作 unseen test 的模型替代品。
- 不得把“与历史 package 更接近”当成选择模型的标准。候选只有“精确复现”或“不复现”；若没有精确复现，生产仍使用原冻结 `checkpoint_best.pth`，不得改选最接近的 variant。
- Git 只提交轻量源码、prompt、validator、Markdown/JSON/CSV；权重、checkpoint、NIfTI、bundle、tar、日志不得进入 Git。

## 三、启动与读取

```bash
cd /users/a/e/aereinh/CARE
source /users/a/e/aereinh/CARE/.care-codex-env.sh
source /users/a/e/aereinh/CARE/env_nnunet.sh
export PATH=/users/a/e/aereinh/codex-runtime/bin:/users/a/e/aereinh/CARE/envs/env_CARE/bin:$PATH

git fetch --all --prune
git status --short --branch
git rev-parse HEAD
git rev-parse origin/main
git log --oneline --decorate -20
git diff --check
```

若 main 落后且工作树干净，只允许：

```bash
git pull --ff-only origin main
```

完整读取：

```text
AGENTS.md
START_HERE_FOR_GPT.md
GPT_PLANNER_CARE_PROTOCOL.md
prompts/FINAL_OUTPUT_READABILITY_POLICY.md
prompts/AGENT_FLOW_V2_PROTOCOL.md
prompts/HANDOFF_GATE_POLICY.md
prompts/GPT_HARD_GATE_PROMPT.md
prompts/routes/ROUTE_ANTI_LAZINESS_PROTOCOL.md
prompts/routes/ROUTE_HARD_REQUIREMENTS_MATRIX.md
prompts/routes/handoffs/CURRENT.md
wiki/README.md
.agents/skills/care-mapper/SKILL.md
.agents/skills/slurm-routing-partition/SKILL.md
prompts/tasks/20260801_care_test_docker_packaging_controller.md
prompts/tasks/20260801_care_test_docker_rootless_unblock_controller.md
prompts/tasks/20260801_care_test_docker_server_bundle_controller.md
results/20260801_care_test_docker_packaging/**
results/20260801_care_test_docker_rootless_unblock/**
results/20260801_care_test_docker_server_bundle/**
```

复用 runtime：

```text
/users/a/e/aereinh/.tmp/codex-CARE/20260801_care_test_docker_cross_machine
```

新结果目录：

```text
results/20260801_care_test_docker_provenance_reconcile_and_bundle
```

## 四、W1：先做 label-wise 差异审计，不重新推理

读取上一任务已经生成的：

- fresh nnU-Net 15 例输出；
- historical package A 的 15 例输出；
- `fresh_nnunet_vs_historical_casewise.csv`；
- package A/B 解包目录和 manifest；
- production asset manifest。

不得先提交新推理。先逐病例计算以下完全相等关系与 changed voxels：

```text
full_array_equal
background_mask_equal
myocardium_class1_equal
lv_class2_equal
rv_class3_equal
pure_edema_class4_equal
scar_class5_equal
anatomy_123_multiclass_equal
anatomy_union_equal
used_channels_1234_equal
```

并生成交叉混淆表：对每个历史标签到 fresh 标签组合统计 voxel count，重点判断完整数组差异是否主要来自 `4 <-> 5`、anatomy/pathology priority 或其他类别变化。

输出：

```text
results/20260801_care_test_docker_provenance_reconcile_and_bundle/nnunet_labelwise_equivalence_casewise.csv
results/20260801_care_test_docker_provenance_reconcile_and_bundle/nnunet_label_transition_counts.csv
results/20260801_care_test_docker_provenance_reconcile_and_bundle/nnunet_used_channel_equivalence_summary.json
```

第一层通过条件：

```text
15/15 geometry equal
15/15 pure_edema class4 mask equal
15/15 anatomy classes1/2/3 multiclass equal
```

若满足，写：

```text
NNUNET_USED_CHANNELS_PROVENANCE_REPRODUCED
```

完整六类数组 mismatch 继续记录为 scar/priority 非生产通道差异，不再阻止 MyoPS bundle。

注意：仅 anatomy union 相同但 classes `1/2/3` 互换，不算通过，因为最终官方 anatomy 标签不同。

## 五、W2：历史命令与资产追溯

无论 W1 是否通过，都必须完成一次有边界的来源追溯，但不得无限搜索。

检查：

```text
results/submissions/care_myocardium_validation/upload_ready/20260519_084057__nnUNet_MyoPS+nnUNet_CineMyoPS_5fold_baseline_round8/**
results/submissions/care_myocardium_validation/upload_ready/20260520_113408__nnUNet5fold_MyoPS+Cine_topology_lcc_round03_RECOMMENDED/**
results/submissions/care_myocardium_validation/**
scripts/submission/**
jobs/submission/**
docs/notes/baseline/**
results/experiments/**
```

并执行只读 Git 历史检索：

```bash
git log --all --oneline --decorate -- scripts/submission jobs/submission results/submissions docs/notes/baseline
git log -S'nnUNetv2_predict' --all --oneline -- .
git log -S'checkpoint_best.pth' --all --oneline -- .
git log -S'checkpoint_final.pth' --all --oneline -- .
rg -n "20260519_084057|20260520_113408|nnUNetv2_predict|checkpoint_(best|final)|disable_tta|apply_postprocessing|postprocess" \
  results scripts jobs docs README.md SERVER.md 2>/dev/null
```

若 runtime/log 目录中存在历史轻量命令记录，可只读搜索；不得把大日志提交 Git。

冻结并记录：

- package A/B 文件时间、内部 manifest、README、命令记录；
- nnU-Net Python package version、源码路径/commit；
- Python、PyTorch、NumPy、SimpleITK、nibabel 版本；
- 当前 `nnUNetPlans.json`/`plans.json`、`dataset.json`、trainer source SHA256；
- 当前 best/final checkpoint SHA256；
- 是否存在 archived cached prediction 与对应命令 receipt；
- 是否有直接证据说明 package A 使用 best、final、TTA、no-TTA 或 postprocessing。

输出：

```text
results/20260801_care_test_docker_provenance_reconcile_and_bundle/historical_package_generation_trace.md
results/20260801_care_test_docker_provenance_reconcile_and_bundle/historical_environment_fingerprint.json
results/20260801_care_test_docker_provenance_reconcile_and_bundle/historical_asset_candidate_manifest.json
```

不得把推测写成事实。每条候选必须标记：

```text
DIRECT_EVIDENCE
INDIRECT_EVIDENCE
NO_EVIDENCE
```

## 六、W3：有限 replay 矩阵

只有 W1 未通过时才运行。不得重新运行已完成的 `best + default TTA` 基线。

最多允许三个新增 replay variant，固定顺序：

```text
V1: checkpoint_final.pth + default TTA + current postprocessing rule
V2: checkpoint_best.pth + TTA disabled + current postprocessing rule
V3: checkpoint_final.pth + TTA disabled + current postprocessing rule
```

如果 W2 找到 package A 的直接命令证据，允许用该 exact variant 替换 V3；总新增 variant 仍不得超过三个。

所有 variant 必须：

- 同一 15 cases；
- folds `0-4`；
- 同一 plans、dataset、preprocess 和输出几何；
- 仅冻结推理；
- 记录命令、环境、checkpoint hashes、wall time；
- 逐病例计算 W1 的所有 label-wise equality 字段。

候选通过标准只有两种：

```text
FULL_ARRAY_EXACT_15_OF_15
USED_CHANNELS_1234_EXACT_15_OF_15
```

不得按 changed voxel 少、Dice proxy 高或“最接近 package A”选择候选。

若某 variant 达到 used-channel exact 15/15，将其冻结为 Docker nnU-Net source，并写：

```text
NNUNET_USED_CHANNELS_PROVENANCE_REPRODUCED_BY_VARIANT
```

若没有 variant 精确通过，保持原先合同冻结的：

```text
checkpoint_best.pth + folds 0-4 + default TTA
```

不得改选其他 variant。

输出：

```text
results/20260801_care_test_docker_provenance_reconcile_and_bundle/nnunet_replay_variant_manifest.json
results/20260801_care_test_docker_provenance_reconcile_and_bundle/nnunet_replay_variant_casewise.csv
results/20260801_care_test_docker_provenance_reconcile_and_bundle/nnunet_replay_variant_decision.json
```

## 七、W4：拆分历史 lineage 与部署可复现性

若 W1/W3 找到 exact used-channel source：

```text
historical_hosted_lineage_status: USED_CHANNELS_REPRODUCED
production_nnunet_source: exact reproduced variant
```

若仍找不到：

```text
historical_hosted_lineage_status: UNRESOLVED
historical_0_6691_claim_authorized: false
production_nnunet_source: checkpoint_best folds0-4 default_TTA
```

此时必须对生产 source 做独立确定性重放：

- 使用新的空输出目录；
- 再跑 15/15；
- 与上一任务同一生产 source 的 fresh 15/15 比较；
- 要求 15/15 array 与 geometry 完全一致。

通过后写：

```text
NNUNET_DEPLOYABLE_SOURCE_REPRODUCED
```

这只证明当前冻结 source 可部署和可重放，不证明它对应历史 `0.6691`。

若同一冻结 source 两次 fresh 运行仍不一致，终止 MyoPS：

```text
NNUNET_DEPLOYABLE_SOURCE_NONDETERMINISTIC
```

只有该状态才继续阻止 MyoPS bundle。

输出：

```text
results/20260801_care_test_docker_provenance_reconcile_and_bundle/nnunet_deployable_repeat_casewise.csv
results/20260801_care_test_docker_provenance_reconcile_and_bundle/nnunet_deployable_source_receipt.json
results/20260801_care_test_docker_provenance_reconcile_and_bundle/nnunet_lineage_vs_deployment_decision.json
```

## 八、W5：完成 MoSAIC Cine，不得再提前停止

复用已经完成的 MoSAIC MyoPS 15/15，不重复运行。

把 CineMyoPS 从现有 4/15 继续到 15/15：

```text
coarse.pt
fine_v1.pt
fine_v2.pt
z-spacing branches 4/8/16
frozen TTA and final decode
```

不得因 historical nnU-Net lineage unresolved 再次停止 Cine。

输出并验证：

```text
results/20260801_care_test_docker_provenance_reconcile_and_bundle/fresh_mosaic_cine_15case_manifest.json
results/20260801_care_test_docker_provenance_reconcile_and_bundle/fresh_mosaic_cine_15case_receipt.json
```

## 九、W6：继续生产源码、sentinel 与 transfer bundle

生产策略保持：

```text
MyoPS scar       = MoSAIC repo-final scar
MyoPS pure edema = frozen deployable nnU-Net class 4
MyoPS anatomy    = frozen deployable nnU-Net classes 1/2/3
priority         = scar > pure edema > anatomy
CineMyoPS        = repo-final MoSAIC Cine recipe
```

若 historical lineage unresolved，README、bundle manifest、controller report 和 email draft 必须明确：

```text
The packaged nnU-Net source is a newly frozen, independently reproducible deployment source.
It is not claimed to reproduce or inherit the historical 0.6691 hosted metric.
```

继续完成上一任务尚未完成的：

- 两套 `docker/CARE2026_Myocardium/...` production source；
- vendor/source/license provenance；
- 3 个 MyoPS sentinel 与 3 个 Cine sentinel；
- host expected baseline；
- MyoPS source intervention；
- transfer bundle；
- deterministic tar 与 SHA256；
- bundle validator。

sentinel expected outputs 必须来自本任务最终冻结的部署 source，不再使用 package A 作为 Docker equivalence oracle。package A 只保留为历史 lineage 诊断参考。

MyoPS source intervention保持：

```text
CARE_DISABLE_MOSAIC_SCAR=1    -> scar 必须改变
CARE_DISABLE_NNUNET_EDEMA=1   -> pure edema 必须改变
CARE_ENABLE_MOSAIC_EDEMA=0/1  -> 完整最终数组必须相同
```

MyoPS context 中禁止包含或加载：

```text
coarse_edema.pt
edema.pt
```

## 十、SERVER_BUNDLE_READY 新语义

只要满足：

- `NNUNET_USED_CHANNELS_PROVENANCE_REPRODUCED*`，或 `NNUNET_DEPLOYABLE_SOURCE_REPRODUCED`；
- MoSAIC MyoPS 15/15 完成；
- MoSAIC Cine 15/15 完成；
- production source、sentinel、intervention 和 bundle validator 通过；
- deterministic archive SHA256 通过；
- lightweight commit/push 完成；

即可写：

```text
/users/a/e/aereinh/.tmp/codex-CARE/20260801_care_test_docker_cross_machine/transfer/SERVER_BUNDLE_READY.json
```

marker 必须增加：

```json
{
  "historical_hosted_lineage_status": "USED_CHANNELS_REPRODUCED | UNRESOLVED",
  "historical_0_6691_claim_authorized": false,
  "nnunet_deployment_source_status": "REPRODUCED",
  "nnunet_deployment_source_variant": "...",
  "nnunet_deployment_source_hashes": {},
  "package_a_full_array_equal_count": 4,
  "package_a_used_channel_equal_count": 0,
  "workstation_build_authorized": true
}
```

`package_a_used_channel_equal_count` 必须写真实审计值，不得预填。

历史 lineage unresolved 不再使 `workstation_build_authorized` 为 false；只有部署 source 非确定性、资源缺失、MoSAIC replay 不完整、bundle 校验失败才阻止工位。

## 十一、验证与 known-bad

新增：

```text
scripts/validation/validate_care_test_docker_provenance_reconcile_and_bundle.py
```

至少覆盖：

- 完整数组 mismatch 但 classes1/2/3/4 全部一致时被错误阻塞；
- anatomy union 一致但 1/2/3 互换时被错误放行；
- 只比较 class4、不比较 anatomy 时被错误放行；
- 选择“最接近 package A”但不 exact 的 variant；
- 新增 replay variant 超过三个；
- historical lineage unresolved 被错误写成 hosted confirmed；
- deployable source 只跑一次却写 reproduced；
- 两次 deployable replay array/geometry 不一致仍生成 ready；
- Cine 仍停在 4/15 却生成 ready；
- sentinel expected output仍来自 package A而不是最终 deployment source；
- MyoPS context 含 MoSAIC edema 权重；
- MoSAIC edema toggle 改变 final output；
- bundle 内有服务器绝对路径、软链接或缺失 SHA；
- archive/bundle/weights/NIfTI 进入 Git staged files；
- marker 在 commit/push 前生成；
- 上传网盘、发送邮件或 hosted metric claim。

## 十二、结果与 Git

结果目录至少包含：

```text
controller_context.json
controller_ledger.csv
nnunet_labelwise_equivalence_casewise.csv
nnunet_label_transition_counts.csv
nnunet_used_channel_equivalence_summary.json
historical_package_generation_trace.md
historical_environment_fingerprint.json
historical_asset_candidate_manifest.json
nnunet_replay_variant_manifest.json
nnunet_replay_variant_casewise.csv
nnunet_replay_variant_decision.json
nnunet_deployable_repeat_casewise.csv
nnunet_deployable_source_receipt.json
nnunet_lineage_vs_deployment_decision.json
fresh_mosaic_cine_15case_manifest.json
fresh_mosaic_cine_15case_receipt.json
source_intervention_receipt.json
sentinel_manifest.json
transfer_bundle_receipt.json
mapper_report_final.md
finalizer_state.json
strict_validator_report.json
controller_report.md
completion_check.md
MANIFEST.md
notification_brief.json
```

提交前：

```bash
git diff --check
git status --short
./envs/env_CARE/bin/python scripts/validation/validate_care_test_docker_provenance_reconcile_and_bundle.py
```

提交轻量文件：

```text
prompts/tasks/20260801_care_test_docker_provenance_reconcile_and_bundle_controller.md
docker/CARE2026_Myocardium/** source only
scripts/validation/validate_care_test_docker_provenance_reconcile_and_bundle.py
results/20260801_care_test_docker_provenance_reconcile_and_bundle/** lightweight only
prompts/routes/handoffs/CURRENT.md
wiki/README.md
```

提交信息：

```text
package: reconcile nnunet provenance and prepare Docker bundle
```

推送：

```bash
git push origin main
```

禁止 force push。

commit/push 验证后运行既有 notifier：

```bash
./envs/env_CARE/bin/python controller_notifications/notify_goal_watcher.py --once
```

## 十三、最终回答

必须先用自然中文说明：

1. 11/15 完整数组 mismatch 最终来自哪些标签；
2. nnU-Net used channels 是否精确复现 package A；
3. 若没有，历史 `0.6691` lineage 是否保持 unresolved；
4. 当前 deployable source 是否经过两次 15/15 重放并完全一致；
5. MoSAIC Cine 是否完成 15/15；
6. transfer bundle 是否 ready，路径、大小、SHA256；
7. 工位是否可以开始执行 WSL prompt；
8. Git commit/push SHA；
9. 明确说明未上传网盘、未发送组织方邮件、未作 hosted metric claim。

不得把 `NNUNET_DEPLOYABLE_SOURCE_REPRODUCED` 表述为历史 `0.6691` 已复现。