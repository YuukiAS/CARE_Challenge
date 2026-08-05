---
task_key: 20260805_care_myops_attempt3_single_slice_hotfix
task_kind: hotfix
task_type: submission_runtime_hotfix
status: AUTHORIZED_BY_USER
risk_level: high
route_change: false
scientific_decision_scope: none
branch_policy: main-only
execution_mode: controller_supervised
requires_execution_controller: true
controller_is_coordinator: true
executor_slots: 1
executor_count: 1
parallel_execution_allowed: false
executor_plan_path: null
mapper_slots: 1
mapper_required: false
architecture_impact: none
wiki_update_required: true
diagram_update_required: false
slurm_runtime_continuity_required: false
continuity_backend: none
planning_review_required: false
review_required: false
allow_git_commit: true
auto_git_commit: true
allow_git_push: true
auto_git_push: true
allow_diagnostic_push: false
corrected_docker_drive_upload_authorized: true
organizer_email_send_authorized: false
challenge_upload_authorized: false
validation_prediction_upload_authorized: false
---

# CARE MyoPS Attempt 3 单层输入热修复、完整回归与重新打包

## 一、实际目标

组织方确认 Attempt 3 的 MyoPS Docker 与 Attempt 2 一样，在合法的单层输入 `(x, y, 1)` 上因 nnU-Net 重采样得到零尺寸而失败。本任务只修复 Attempt 3 已提交镜像中的这一运行时缺陷，不更换 Attempt 3 模型，不改变 CARE-ASE 选择、权重、阈值、nnU-Net 解剖基座、推理配置或标签映射。

Attempt 2 的修正版和测试证据只能作为测试方法参考，不能替代 Attempt 3 自己的复现、修复和完整验证。Attempt 3 包含额外 CARE-ASE 推理路径，必须以组织方实际测试失败的 Attempt 3 archive 为唯一基础重新验证。

任务达到终态后可以调用既有 CARE notifier；绝对不得给组织方发送邮件。只生成未发送草稿。

## 二、固定环境

Docker 工作站：

```text
/home/yuukias/code/CARE
```

远程服务器：

```text
/users/a/e/aereinh/CARE
```

禁止写入：

```text
/overflow/htzhu/CARE
```

工作站运行目录：

```text
/home/yuukias/code/CARE/.local_runtime/20260805_care_myops_attempt3_single_slice_hotfix
```

工作站结果目录：

```text
/home/yuukias/code/CARE/results/20260805_care_myops_attempt3_single_slice_hotfix
```

最终本地归档目录：

```text
/home/yuukias/code/CARE/dist/20260805_care_myops_attempt3_single_slice_hotfix
```

服务器回传目录：

```text
/users/a/e/aereinh/.tmp/codex-CARE/20260805_care_myops_attempt3_single_slice_hotfix/workstation_return
```

新的 Drive 目录：

```text
gdrive:/CARE2026_Myocardium_MyoPS_Attempt3_Corrected_20260805/
```

## 三、启动与必读文件

先同步最新 `origin/main`，再完整读取：

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
routes/README.md
wiki/README.md

results/20260804_care_ase_r2_deadline_recovery_training_docker/WORKSTATION_DOCKER_ATTEMPT3_REQUIREMENTS.md
results/20260804_care_ase_r2_deadline_recovery_training_docker/attempt3_workstation_handoff.json
results/20260804_care_ase_r2_deadline_recovery_training_docker/workstation_docker_attempt3_prompt.md

docker/CARE2026_Myocardium/MyoPS/Dockerfile
docker/CARE2026_Myocardium/MyoPS/predict.py
docker/CARE2026_Myocardium/MyoPS/requirements.lock

prompts/tasks/20260805_care_myops_single_slice_hotfix_repackage_controller.md
prompts/tasks/20260805_care_myops_single_slice_hotfix_provenance_addendum.md
prompts/tasks/20260805_care_myops_single_slice_hotfix_resume_authorization_addendum.md
results/20260805_care_myops_single_slice_hotfix_repackage/**
results/20260805_care_myops_single_slice_hotfix_server_audit/**
prompts/tasks/20260805_care_myops_attempt3_single_slice_hotfix_controller.md
```

Attempt 2 热修复只提供复现方法、合成输入和验证器设计参考。不得把 Attempt 2 修正版作为 Attempt 3 基础镜像，也不得复用 Attempt 2 的“已通过”结论作为 Attempt 3 完成证据。

## 四、Attempt 3 模型边界

Attempt 3 的科学内容必须原样保留：

- nnU-Net 五折 `checkpoint_best.pth` 负责解剖输出和几何恢复；
- CARE-ASE step500 的 fold1/fold4 checkpoint ensemble 负责 scar 与 pure-edema overlay；
- `selection.json`、两个 CARE-ASE checkpoint 及其 sidecar、推理设置保持不变；
- nnU-Net 数据集、trainer、configuration、fold、checkpoint、TTA、标签映射保持不变；
- 不重训、不换 checkpoint、不改阈值、不改 overlay 顺序、不改标签规则、不改病例发现逻辑。

必须冻结并核对的关键资产至少包括：

```text
五个 nnU-Net fold checkpoint_best.pth
两个 CARE-ASE step00500 checkpoint
两个 CARE-ASE checkpoint SHA sidecar
models/self_model/selection.json
nnUNet plans.json / dataset.json
/app/predict.py
/app/entrypoint.sh
/app/requirements.lock
CARE-ASE 推理源码和 decode 源码
ENTRYPOINT / Cmd / Env / WorkingDir
pip freeze --all
```

## 五、唯一允许的 Attempt 3 基础归档

必须先定位“组织方本次实际测试失败”的 Attempt 3 MyoPS archive，不能按文件名猜测。

按以下优先级绑定：

1. Attempt 3 已发送邮件中的 MyoPS 下载链接、文件名、SHA 和 image tag；
2. Attempt 3 Google Drive 上传 receipt；
3. Attempt 3 工作站最终 `docker save` receipt；
4. 本地和服务器中与上述三项 size/SHA 完全一致的 archive。

将识别过程写入：

```text
attempt3_submitted_artifact_resolution.json
```

必须记录：

- 组织方收到的 Attempt 3 文件名和链接；
- 本地 archive path、size、SHA256；
- Drive 远端 size/hash 或等价校验；
- load 后 image ID、tag、ENTRYPOINT；
- 两个 CARE-ASE step500 checkpoint SHA；
- 五个 nnU-Net checkpoint SHA；
- `selection.json` SHA；
- 明确证明它不是 Attempt 2 纯 nnU-Net archive，也不是 Attempt 2 corrected archive。

如果无法唯一确定组织方实际测试的 Attempt 3 archive，停止：

```text
ATTEMPT3_SUBMITTED_ARTIFACT_AMBIGUOUS
```

不得自行选择一个相似 archive 继续。

加载后冻结为：

```text
care-myocardium-myops:attempt3-failed-base
```

## 六、先在 Attempt 3 基础镜像上复现

必须使用 Attempt 2 阶段已经验证过的 aligned depth1/depth2 合成输入生成方法，或重新生成等价输入。可以复用合成输入文件，但必须重新记录 SHA、shape、spacing、origin、direction 和三模态几何一致性。

至少覆盖：

```text
depth=1: z-spacing 1, 4, 5, 9.9, 10, 20, 50
depth=2: z-spacing 1, 4, 5, 10, 20
小视野 64x64x1
```

先在 Attempt 3 基础镜像中直接调用 `compute_new_shape`，证明旧实现至少一个组合产生零维。

随后用基础镜像实际运行合成官方输入根，要求真实复现组织方同类失败，包括非零退出、不完整输出以及零尺寸/worker died 相关错误证据。

若直接函数产生零维但端到端未复现，继续根据 Attempt 3 plans target spacing 扩展输入组合；仍无法复现则停止：

```text
ATTEMPT3_REPRODUCER_MISMATCH_NEEDS_TRACE
```

## 七、实施最小派生镜像补丁

创建独立 context：

```text
docker/CARE2026_Myocardium/MyoPS_attempt3_single_slice_hotfix/
```

只允许包含：

```text
Dockerfile
apply_single_slice_hotfix.py
README.md
```

Dockerfile 必须直接从冻结的 Attempt 3 失败镜像派生：

```dockerfile
FROM care-myocardium-myops:attempt3-failed-base
COPY apply_single_slice_hotfix.py /tmp/apply_single_slice_hotfix.py
RUN python /tmp/apply_single_slice_hotfix.py \
 && rm /tmp/apply_single_slice_hotfix.py
LABEL org.opencontainers.image.description="CARE MyoPS Attempt3 single-slice preprocessing hotfix"
```

禁止 `pip install`、`apt`、网络下载、重新 COPY models、重新 COPY `predict.py`、重新构建当前可变 MyoPS context。

补丁必须与 Attempt 2 相同：保留原 rounding，只把最终重采样尺寸限制为每个方向至少一个体素：

```python
new_shape = np.maximum(new_shape, 1)
```

补丁脚本必须：

- 核对 `nnunetv2==2.7.0`；
- 核对原 source SHA 和函数文本；
- 要求匹配次数恰好为 1；
- 只修改 `compute_new_shape` 所在源文件；
- compile/import 成功；
- 写 `/app/hotfix/attempt3_single_slice_hotfix_receipt.json`；
- 记录旧/新 source SHA、精确 diff、时间和匹配次数；
- 任一前提不符即失败。

最终运行 tag 保持组织方原合同要求；内部测试可使用：

```text
care-myocardium-myops:attempt3-single-slice-hotfix
```

## 八、证明 Attempt 3 模型完全没有变化

分别对 Attempt 3 基础镜像和 corrected image 建立完整清单并比较。

硬门：

- 五个 nnU-Net checkpoint SHA 完全一致；
- 两个 CARE-ASE step500 checkpoint SHA 完全一致；
- sidecar 与 `selection.json` 完全一致；
- CARE-ASE 推理源码和 decode 源码完全一致；
- plans、dataset、`predict.py`、entrypoint、requirements 完全一致；
- `pip freeze --all` 完全一致；
- ENTRYPOINT、Cmd、Env、WorkingDir 完全一致；
- 基础镜像全部 rootfs layer 是 corrected image 的精确前缀；
- 唯一有效文件改动是 nnU-Net `compute_new_shape` 源文件和热修复 receipt；
- 没有第三个 CARE-ASE checkpoint、没有新阈值、没有 Attempt 2 模型替换。

任一不满足，停止：

```text
ATTEMPT3_MODEL_INVARIANCE_FAILED
```

## 九、必须重新运行的推理验证

Attempt 3 与 Attempt 2 是不同模型。以下推理必须真实重新运行，不能复用 Attempt 2 输出或结论。

### 9.1 15 个正常公开病例：基础镜像与修正版逐体素完全一致

分别运行 Attempt 3 基础镜像和修正版，每个镜像各一次完整 15-case 推理。

对每例要求：

- 输出集合一致；
- voxel array 完全一致；
- shape、spacing、origin、direction 完全一致；
- label set 完全一致；
- canonical array+geometry SHA 完全一致。

要求 15/15 全部 exact。任何一例变化都停止：

```text
ATTEMPT3_NORMAL_REGRESSION_CHANGED
```

### 9.2 depth1/depth2 合成矩阵

修正版一次运行全部 aligned synthetic cases，要求全部成功、全部输出、geometry 精确恢复、标签合法、无 NaN/Inf。

### 9.3 混合批次

同一 `/input/myops` 中放入：

- 15 个正常公开病例；
- 全部 depth1/depth2 合成病例。

一次运行修正版，要求所有病例完整输出，单层病例不得再杀死整批 worker；正常15例结果仍与基础镜像完全一致。

### 9.4 确定性

至少对完整 synthetic matrix 重复两次，要求逐体素和 geometry 完全一致。

### 9.5 最终 archive clean-load 回归

保存 corrected archive，删除 corrected 测试 tag，重新 load。

clean-load 后至少重新运行：

- 完整 depth1/depth2 synthetic matrix；
- 一个由全部 synthetic cases 加 3 个正常 sentinel 组成的 mixed batch；
- 3 个正常 sentinel 与基础镜像逐体素 exact。

clean-load 后无需第三次完整跑15个正常病例，但必须证明最终保存的 archive 仍包含同一模型资产、同一热修复和可运行输出。

## 十、时间和资源边界

本任务必须接受数小时 CPU 推理。不能因为推理耗时而用静态检查、直接函数测试或 Attempt 2 结果替代 Attempt 3 的真实推理。

可以通过以下方式避免无意义重复：

- 复用已生成的 aligned synthetic 输入和比较脚本；
- 15-case 正常回归只要求基础镜像一次、修正版一次；
- clean-load 后只复跑完整 synthetic 和 3 个正常 sentinel；
- 不重跑 Cine；
- 不训练模型。

不得删减 15/15 normal exact、完整 synthetic、完整 mixed batch 和 clean-load 回归四个核心门。

## 十一、失败模式边界

只把本次组织方报告的合法单层输入和合法对齐输入作为硬门。

人为制造的 LGE/T2/C0 geometry mismatch 继续记录为继承的非阻塞行为，不修改 `predict.py`，也不声称修复。

缺模态、空输入、非法 spacing、只读输入、输出目录不存在和无关文件保留应有测试。不得因畸形 geometry mismatch 阻止本次单层热修复。

## 十二、归档、Drive 和服务器审计

最终 archive 名称：

```text
MyoPS-OrganAgent-Attempt3-corrected.tar.gz
```

生成 `SHA256SUMS`，上传到新的 Drive 目录，不覆盖任何旧文件。只允许上传 corrected archive 与 `SHA256SUMS`。

上传后必须核对远端 size/hash，创建新公开链接，并进行未登录 HTTP 访问检查。

随后通过 SSH/rsync 将 archive 和轻量证据包传到服务器。服务器不运行 Docker，只独立核对：

- Attempt 3 原始 archive 身份；
- corrected archive size/SHA；
- 五个 nnU-Net 和两个 CARE-ASE checkpoint SHA；
- `selection.json`、推理源码、配置、依赖不变；
- 15/15 normal exact；
- synthetic、mixed、determinism、clean-load 结果；
- Drive 链接绑定；
- 邮件未发送。

## 十三、组织方回复草稿

只生成草稿，不发送。草稿必须明确：

1. corrected MyoPS 是 Attempt 3 原模型的运行时修正版，不是回退到 Attempt 2；
2. 两个 CARE-ASE step500 checkpoint、五个 nnU-Net checkpoint 和推理配置完全不变；
3. 唯一改动是把重采样空间尺寸限制为至少一个体素；
4. 15个正常公开病例修复前后逐体素完全一致；
5. 给出新的 archive 名称、SHA、Drive 链接和运行命令；
6. CineMyoPS archive 与上次相同是有意的，请继续把它作为当前 CineMyoPS submission；
7. `email_sent=false`。

不得发送邮件，不得调用 Gmail/SMTP。

## 十四、Git 与通知

允许提交并 push：

- 独立热修复 Docker context；
- 验证脚本；
- 小型 JSON/CSV/Markdown receipts；
- 未发送邮件草稿；
- CURRENT/wiki 的独立 Attempt 3 hotfix 状态。

禁止提交：

- Docker archive；
- checkpoint；
- NIfTI；
- prediction；
- 大日志；
- token/secret/rclone 配置；
- `.local_runtime/` 和 `dist/`。

提交信息：

```text
package: fix Attempt3 MyoPS single-slice preprocessing without model change
```

push `origin/main` 后核对本地 HEAD 与远端一致。

达到 complete 或 blocked 终态后，写合规 `notification_brief.json` 并调用既有：

```bash
./envs/env_CARE/bin/python controller_notifications/notify_goal_watcher.py --once
```

notifier 只向用户发送内部完成/阻塞提醒，不得给组织方发送邮件。

## 十五、完成条件

只有以下全部满足才可完成：

- 唯一识别组织方实际测试失败的 Attempt 3 archive；
- Attempt 3 基础镜像真实复现单层故障；
- 补丁只增加 `np.maximum(new_shape, 1)`；
- 五个 nnU-Net checkpoint 与两个 CARE-ASE checkpoint 不变；
- selection、源码、依赖、配置和运行入口不变；
- 15/15 normal exact；
- depth1/depth2 synthetic PASS；
- 15 normal + synthetic mixed batch PASS；
- determinism PASS；
- clean save/load 后 synthetic + mixed sentinel PASS；
- corrected archive、SHA 和新 Drive 公链完成；
- 服务器静态审计完成；
- 轻量 commit/push 完成；
- notifier 完成；
- 组织方邮件未发送。

最终回答先用自然中文说明结果，再给文件、SHA、链接和提交号。不得用内部状态标记代替结论。
