---
task_key: 20260803_care_test_docker_official_submission_rehearsal_and_staging
project: CARE
status: AUTHORIZED_BY_USER
branch_policy: main-only
execution_mode: controller_supervised
requires_execution_controller: true
controller_is_coordinator: true
executor_slots: 1
executor_count: 1
parallel_execution_allowed: false
mapper_required: false
architecture_impact: none
wiki_update_required: true
diagram_update_required: false
slurm_runtime_continuity_required: false
planning_review_required: false
review_required: false
allow_git_commit: true
auto_git_commit: true
allow_git_push: true
auto_git_push: true
external_upload_authorized: conditional_after_all_local_docker_gates_pass
organizer_email_send_authorized: false
challenge_upload_authorized: false
validation_upload_authorized: false
---

# CARE 2026 Myocardium Docker Official-Format Rehearsal and Submission Staging

本任务是当前工位 Docker 构建任务完成后的下一轮。它不训练、不改模型、不重做 Docker 设计；只按 CARE 官方测试阶段说明做一次接近组织方运行方式的黑盒彩排，比较合作者 Docker 的接口行为，准备 Google Drive 上传和自然英文邮件草稿，但绝不发送邮件。

官方说明来源：

```text
https://zmic.org.cn/care_2026/instruction_myocardium/
```

官方页面当前明确要求：

- 每个参与任务提交一个独立 Docker image archive，格式 `.tar.gz` 或 `.tar`。
- 邮件地址可用 `care26challenge@163.com` 或 `care2026challenge@outlook.com`。
- 主题格式为 `[CARE-Myocardium Test] Team-Name – Docker Submission`。
- 邮件正文包含下载链接、任务名称和运行说明；CPU-only 优先。
- 容器从只读 `/input` 读取，写入 `/output`。
- 官方输入结构：`/input/myops/*_C0.nii.gz, *_LGE.nii.gz, *_T2.nii.gz`；`/input/cinemyops/*_Cine.nii.gz`。
- MyoPS 输出：`/output/myops/<CaseID>_pred.nii.gz`。
- CineMyoPS 输出：`/output/cinemyops/<CaseID>_pred.nii.gz`。
- 容器应尽可能非交互运行、无需用户输入，并正常退出。
- 多任务必须分开提交 Docker archive。
- 官方建议文件名形式为 `MyoPS-<Team>.tar.gz`、`CineMyoPS-<Team>.tar.gz`。
- 页面显示 Docker submission deadline 为 2026-08-03，但未给出时区；不得据此自行发送邮件。

## 一、前置条件

本任务只能在以下工位任务已经终态完成后启动：

```text
20260803_care_test_docker_workstation_build_validate_return
```

至少必须存在并通过：

- MyoPS 纯五折 nnU-Net image build/run/save/load。
- CineMyoPS 合作者原 archive load/run。
- 两个镜像 3-case CPU determinism。
- MyoPS host equivalence。
- final archives 已回传服务器。
- strict validator PASS。
- 轻量结果已 commit/push。

固定本地根目录：

```text
/home/yuukias/code/CARE
```

固定最终文件名：

```text
MyoPS-OrganAgent.tar.gz
CineMyoPS-OrganAgent.tar.gz
```

固定 image tags：

```text
care-myocardium-myops:organagent
care-myocardium-cinemyops:organagent
```

固定 Cine archive SHA：

```text
c02db56bd52d14d3b5bbda9d204a20b7e4c061fd5e6012ffa1cebc67fb92c136
```

MyoPS SHA 必须从刚完成的工位 `docker_export_manifest.json` 和服务器 final dist 双重读取，不得使用旧 bundle SHA。

若前一任务仍在下载、build、run、save/load、回传或等待人工 Docker 安装，本任务不得抢占、重启或重复下载。只报告前置条件未完成，然后退出为 `WAITING_FOR_CURRENT_WORKSTATION_TASK`；这不是失败，也不得改变 CURRENT。

## 二、执行边界

允许：

- 在 WSL 普通用户下运行 Docker。
- 读取 CARE 官方说明网页。
- 使用公开 validation/test image volumes 做本地黑盒彩排。
- 从服务器 rsync 合作者 MyoPS reference archive，仅作接口比较。
- 在本地用户目录安装或使用 `rclone`。
- 所有本地 Docker 门通过后，尝试上传最终两个 archive 和 `SHA256SUMS` 到用户自己的 Google Drive。
- 创建共享下载链接并做未登录访问检查。
- 生成邮件草稿和提交清单。
- 回传轻量验证包与上传 receipt 到学校服务器。
- commit/push 轻量源码和证据到 `origin/main`。

禁止：

- sudo；若 rclone 或其他工具需要 sudo，改为用户空间安装。
- 新训练、改 checkpoint、fold、TTA、阈值、decode、label map 或模型来源。
- 修改合作者 Cine archive 的任何字节。
- 把合作者 MyoPS reference 当作最终模型。
- 上传 challenge、validation 预测或给组织方上传 Docker。
- 发送邮件。
- 自动使用没有经过验证的共享链接。
- 提交 Docker archive、checkpoint、NIfTI、secret、rclone config 或大日志到 Git。
- 写入 `/overflow/htzhu/CARE`。

## 三、启动与同步

```bash
cd /home/yuukias/code/CARE
git fetch --all --prune
git status --short --branch
git rev-parse HEAD
git rev-parse origin/main
git log --oneline --decorate -20
git diff --check
```

若工作树干净且落后：

```bash
git pull --ff-only origin main
```

必须读取：

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
prompts/tasks/20260803_care_test_docker_official_submission_rehearsal_and_staging_controller.md
前一工位任务的全部轻量结果与 validator
```

结果目录：

```text
results/20260803_care_test_docker_official_submission_rehearsal_and_staging
```

本地 runtime：

```text
/home/yuukias/code/CARE/.local_runtime/20260803_care_test_docker_official_submission_rehearsal_and_staging
```

## 四、冻结官方运行合同

抓取官方页面并保存：

```text
official_instruction_snapshot.html
official_submission_contract.json
official_submission_contract.md
```

`official_submission_contract.json` 至少记录：

- source URL 和抓取时间。
- 邮件地址。
- subject pattern。
- CPU preference。
- `/input` 与 `/output` mount contract。
- MyoPS/CineMyoPS 输入目录。
- 两个输出目录和 filename pattern。
- archive format 和 naming convention。
- separate-image requirement。
- submission-attempt rule。
- deadline 原文及“页面未给出时区”。

若网页暂时不可达，使用本任务顶部冻结的要求继续本地验证，并记录 `live_page_fetch_status: unavailable`；不得因此跳过彩排或自动发送邮件。

## 五、准备组织方风格的公开输入树

从仓库中现有的公开 validation/test volumes 构造：

```text
<REHEARSAL_ROOT>/input/
├── myops/
│   ├── <CaseID>_C0.nii.gz
│   ├── <CaseID>_LGE.nii.gz
│   └── <CaseID>_T2.nii.gz
└── cinemyops/
    └── <CaseID>_Cine.nii.gz
```

不得复制 GT。

优先使用全部公开可用病例：

- MyoPS 预期 15 例完整三模态。
- CineMyoPS 预期 15 例。

若实际数量不同，记录真实 case list 和来源，不得伪造 15/15。

写：

```text
public_rehearsal_input_manifest.json
public_rehearsal_input_casewise.csv
```

每个输入记录：case ID、task、relative path、size、SHA256、shape、spacing、origin、direction、frame count（Cine）。

在任何 Docker run 前写全输入 SHA manifest；运行后再次校验输入完全未改变。

## 六、从最终 archive 做 clean load

只使用前一任务最终归档，不使用当前已加载 image 作为唯一来源。

```bash
docker image rm care-myocardium-myops:organagent || true
docker image rm care-myocardium-cinemyops:organagent || true

docker load --input <FINAL_DIST>/MyoPS-OrganAgent.tar.gz
docker load --input <FINAL_DIST>/CineMyoPS-OrganAgent.tar.gz
```

验证两个 image：

- tag 精确。
- `linux/amd64`。
- ENTRYPOINT 非空。
- 不要求额外 command。
- 非 privileged。
- 无声明的 host bind dependency。
- MyoPS 内含 5 个 checkpoint。
- Cine image ID/config 与服务器静态审计对应。

写：

```text
clean_archive_load_receipt.json
final_image_inspect.json
```

## 七、组织方命令黑盒彩排

必须使用接近官方的最小命令，不传额外 command，不使用 `-it`：

```bash
docker run --rm \
  --network none \
  -v "<REHEARSAL_ROOT>/input:/input:ro" \
  -v "<REHEARSAL_ROOT>/output:/output" \
  care-myocardium-myops:organagent

docker run --rm \
  --network none \
  -v "<REHEARSAL_ROOT>/input:/input:ro" \
  -v "<REHEARSAL_ROOT>/output:/output" \
  care-myocardium-cinemyops:organagent
```

每次运行前必须清空对应任务输出子目录，但不得删除另一个任务已经完成的结果。

必须验证：

### MyoPS

- exit code 0。
- 发现所有预期完整三模态病例。
- 只写 `/output/myops/`。
- 每例恰好一个 `<CaseID>_pred.nii.gz`。
- 不缺例、不重复、不多写未知病例。
- 文件可由 SimpleITK 和 nibabel 读取。
- 输出为 3D 整数标签图。
- label set subset 为 `{0,200,500,600,1220,2221}`。
- shape、spacing、origin、direction 与对应参考空间一致。
- 无 NaN/Inf。
- 不在 `/output` 根目录散落临时文件。
- 不写 `/output/cinemyops`。

### CineMyoPS

- exit code 0。
- 发现所有预期 Cine 病例。
- 只写 `/output/cinemyops/`。
- 每例恰好一个 `<CaseID>_pred.nii.gz`。
- 不缺例、不重复、不多写未知病例。
- 文件可由 SimpleITK 和 nibabel 读取。
- 输出为组织方 validation 阶段一致的 3D整数标签图。
- label set subset 为 `{0,200,500,2221}`；若合作者 archive 的已验证合同提供更窄集合，以实际合同为准但不得出现未知标签。
- 空间 geometry 与对应 Cine 空间合同一致。
- 无 NaN/Inf。
- 不写 `/output/myops`。

运行后再次校验输入 SHA，证明 `/input:ro` 未被修改。

写：

```text
official_command_rehearsal_casewise.csv
official_command_rehearsal_summary.json
output_tree_snapshot.txt
input_readonly_integrity_receipt.json
```

全部公开病例的这一轮只要求一次完整运行。前一任务同 archive/image ID 的 3-case 两次确定性 receipt 可以复用；若 image SHA、image ID 或运行代码变化，则必须重新做 3-case determinism。

## 八、对照合作者 MyoPS reference Docker

从服务器读取合作者 MyoPS reference 路径和 SHA：

```text
SHA256 81d19bbefd8f7cca46aee32b31a774f16222b6146b9eab6bc7265a6c214de2ff
```

下载后先验证 SHA。加载时原 tag 会与最终 MyoPS 冲突，必须立即：

1. 记录 reference image ID。
2. retag 为 `care-myocardium-myops:collaborator-reference`。
3. 删除 reference 的 `care-myocardium-myops:organagent` tag。
4. 重新 load 最终 MyoPS archive，确认 final tag 指向我们纯 nnU-Net image。

使用同一个官方输入树和空输出目录运行 reference：

```bash
docker run --rm \
  --network none \
  -v "<REHEARSAL_ROOT>/input:/input:ro" \
  -v "<REFERENCE_OUTPUT_ROOT>:/output" \
  care-myocardium-myops:collaborator-reference
```

比较范围仅限接口和提交格式：

- 是否无需额外 command。
- exit code。
- output root/subfolder。
- filename pattern。
- case count。
- NIfTI 可读性。
- dtype、维度、geometry。
- official label set。
- 是否修改输入。
- stdout/stderr 和总 runtime。

不得要求两个模型 voxel array 相同，也不得利用 reference 结果修改我们的模型、阈值或后处理。

写：

```text
collaborator_reference_interface_casewise.csv
collaborator_reference_interface_comparison.md
```

比较结论必须是“提交接口是否一致”，不是“模型谁更好”。

## 九、失败模式演练

在不改最终 image 的前提下做最小 known-bad：

1. 空 `/input/myops`：MyoPS 必须非零退出，不得静默成功。
2. 一个 MyoPS 病例缺 T2：必须非零退出并指出 case ID/缺失模态，不得 zero-fill。
3. 空 `/input/cinemyops`：Cine 应非零退出或明确报告无病例；不得生成伪输出。
4. `/output` 初始不存在的任务子目录：容器应自行创建正确子目录。
5. 输入目录只读：运行成功且输入 hash 不变。
6. 输出目录已有无关文件：容器不得删除另一个任务或用户文件。

这些是接口演练，不得由 known-bad 结果改模型。若发现纯端口 bug，只能修正路径、文件名、退出码、原子写入或依赖打包，然后重新执行全部受影响的正式门。

## 十、最终 archive 完整性与提交清单

检查：

- 文件名：`MyoPS-OrganAgent.tar.gz`、`CineMyoPS-OrganAgent.tar.gz`。
- 两个 archive `docker load --input` 均成功。
- clean load 后官方命令均成功。
- SHA256SUMS 正确。
- Cine archive SHA保持固定值。
- MyoPS local SHA 与服务器 final dist SHA一致。
- archive 不包含 secret、输入数据、GT 或宿主绝对路径依赖。
- 文件大小和预计下载时间记录。

写：

```text
pre_submission_archive_manifest.json
pre_submission_checklist.md
submission_readiness.json
```

`submission_readiness.json` 必须分别记录：

```text
local_docker_ready
official_format_ready
public_rehearsal_ready
collaborator_interface_checked
google_drive_upload_ready
email_draft_ready
email_send_authorized=false
```

Docker 本地门全部 PASS 与 Google Drive auth 是独立状态。Drive 未配置不得把已经完成的 Docker 验证降级为失败。

## 十一、Google Drive / rclone 非阻塞上传

只在全部本地 Docker、official-format 和 clean-load 门 PASS 后尝试。

先检查：

```bash
command -v rclone || true
rclone version 2>/dev/null || true
rclone listremotes 2>/dev/null || true
```

若未安装，使用用户空间安装到：

```text
/home/yuukias/.local/bin/rclone
```

不得 sudo。必须从 rclone 官方发布源下载，记录版本和二进制 SHA。

远端选择规则：

- 只接受 type 为 Google Drive 的 remote。
- 若恰好一个，使用它。
- 若多个，停止上传步骤并要求用户选择，不影响其他验收。
- 若没有 remote，写 `google_drive_upload_pending.md`，给出用户在普通可见终端执行 `rclone config` 的步骤，不得在隐藏终端等待浏览器授权。

上传目标必须是新目录，避免覆盖：

```text
CARE2026_Myocardium_Test_OrganAgent_20260803/
```

上传：

```text
MyoPS-OrganAgent.tar.gz
CineMyoPS-OrganAgent.tar.gz
SHA256SUMS
```

上传后使用 `rclone check` 或 provider hash/size 做完整性验证。不得只看 transfer exit code。

尝试生成每个 archive 的共享链接。共享链接必须做未登录检查：

- HTTP 状态不是 401/403。
- 页面或下载入口可访问。
- 文件名/ID 与目标文件对应。

大文件不要求从公网重新下载完整副本，但至少做未认证访问和文件元数据核对。

如果 remote/auth/link 任一步失败：

- 保存已完成进度。
- 写清楚人工动作和精确续跑命令。
- `google_drive_upload_ready=false`。
- 不得阻塞 email draft 生成，也不得自动使用占位链接发送邮件。

写：

```text
rclone_environment_receipt.json
google_drive_upload_receipt.json
google_drive_links.json
google_drive_upload_pending.md（仅需要时）
```

## 十二、自然英文邮件草稿

只有 Docker 本地门和官方格式门全部 PASS 后才生成正式草稿：

```text
results/20260803_care_test_docker_official_submission_rehearsal_and_staging/submission_email_draft.md
```

草稿必须自然、简洁，像参赛者本人写的邮件，不写宣传句、不重复解释模型历史、不声称 leaderboard 指标，不出现 AI 生成口吻。

固定结构：

```text
To: care26challenge@163.com
Alternative recipient: care2026challenge@outlook.com
Subject: [CARE-Myocardium Test] OrganAgent – Docker Submission

Dear CARE Myocardium organizers,

Please find below our Docker submissions for the MyoPS and CineMyoPS tasks.

1. MyoPS
   Download link: <verified link or [pending upload]>
   Archive: MyoPS-OrganAgent.tar.gz
   Loaded image: care-myocardium-myops:organagent
   SHA-256: <actual SHA>

2. CineMyoPS
   Download link: <verified link or [pending upload]>
   Archive: CineMyoPS-OrganAgent.tar.gz
   Loaded image: care-myocardium-cinemyops:organagent
   SHA-256: c02db56bd52d14d3b5bbda9d204a20b7e4c061fd5e6012ffa1cebc67fb92c136

Both images have an ENTRYPOINT and require no additional command, GPU, network access, interactive input, or other runtime instructions.

Example commands:

<exact docker load/run commands verified in the rehearsal>

The MyoPS predictions are written to /output/myops and the CineMyoPS predictions are written to /output/cinemyops.

Please let us know if any additional information is needed.

Best regards,
OrganAgent
```

最终文字必须根据真实验证结果删改：只有真实验证过的 `no additional command/GPU/network/input` 才能保留。若 Drive 未完成，保留 `[pending upload]`，并设置：

```text
email_draft_ready=true
email_ready_to_send=false
```

若链接已验证且其余字段完整：

```text
email_draft_ready=true
email_ready_to_send=true
```

无论如何：

```text
email_sent=false
```

同时生成：

```text
submission_email_fields.json
submission_manual_send_checklist.md
```

人工发送清单必须提醒用户：

- 选择一个官方邮箱地址，避免无意重复提交。
- 再次点击两个链接做未登录检查。
- 核对两个 SHA 和 archive 文件名。
- 核对任务名 MyoPS/CineMyoPS。
- 不附加预测结果或 GT。
- 发送前由用户本人审阅正文。

## 十三、回传服务器

将轻量验证包打包并回传：

```text
OFFICIAL_SUBMISSION_REHEARSAL_PACKET.tar.gz
```

包含本任务全部 JSON/CSV/Markdown、小型网页快照和邮件草稿，不包含 Docker archive、NIfTI、secret、rclone config 或大日志。

回传到：

```text
/users/a/e/aereinh/.tmp/codex-CARE/20260803_care_test_docker_official_submission_rehearsal_and_staging
```

若 Google Drive 已成功，另回传 `google_drive_links.json`。服务器只保存 receipt，不发送邮件、不重新上传。

## 十四、严格 validator

新增：

```text
scripts/validation/validate_care_test_docker_official_submission_rehearsal_and_staging.py
```

known-bad 至少覆盖：

- 只做 3-case smoke 就声称 official public rehearsal 完成。
- 使用 `/input/myops` 单独 mount，而没有测试官方 `/input` 根树。
- 输出写到 `/output` 根目录。
- 文件名不是 `<CaseID>_pred.nii.gz`。
- MyoPS/Cine 写错对方子目录。
- 输入被容器修改。
- 使用额外 command 或交互输入才能运行。
- clean archive load 未执行。
- 只检查 tar SHA、不运行 image。
- 合作者 reference 覆盖最终 MyoPS tag。
- 把不同模型的 voxel mismatch 当接口失败。
- Cine archive SHA变化。
- Google Drive auth 缺失导致 Docker readiness 被判失败。
- 未验证公共链接就写入可发送邮件。
- email draft 含未替换占位符却标记 ready_to_send=true。
- 邮件被实际发送。
- Docker archive、NIfTI、rclone config 或 secret staged 到 Git。
- 自动上传 challenge/validation。

validator 输出：

```text
strict_validator_report.json
```

## 十五、Git、状态与通知

更新：

```text
prompts/routes/handoffs/CURRENT.md
wiki/README.md
```

只有本任务真正完成后，顶部状态才写：

- 两个 final archive clean-load PASS。
- official `/input` root tree rehearsal PASS。
- 输出目录、文件名、label schema、geometry PASS。
- 合作者 MyoPS reference interface comparison PASS。
- Drive 状态为 uploaded 或 pending-manual-auth，二者不得混写。
- 邮件草稿已生成但未发送。
- challenge/validation 未上传。

只提交轻量源码和证据。明确拒绝 staged：

```text
*.pt
*.pth
*.nii
*.nii.gz
*.tar
*.tar.gz
rclone.conf
.local_runtime/
dist/
```

提交信息：

```text
package: rehearse official CARE Docker submission and stage email
```

推送：

```bash
git push origin main
```

禁止 force push。

push 成功后同步服务器仓库并调用既有 notifier。notifier 只报告本任务完成，不给组织方发邮件。

## 十六、最终回答

必须先用自然中文说明：

1. 官方页面要求的实际输入/输出格式。
2. 两个镜像是否用官方风格命令从 clean archive 成功运行。
3. 公开 MyoPS/Cine 各实际跑了多少病例。
4. 输出目录、文件名、NIfTI、label schema、geometry 是否全部通过。
5. 合作者 MyoPS reference 与最终 MyoPS 的接口是否一致；不得比较模型优劣。
6. 两个 archive 文件名、大小、SHA。
7. Google Drive 是否成功上传；若未成功，具体停在哪个人工认证步骤。
8. 两个共享链接是否完成未登录验证。
9. 邮件草稿路径和 `email_ready_to_send` 状态。
10. 服务器 rehearsal packet 路径和 SHA。
11. Git commit/push SHA。
12. 明确说明：未发送邮件，未上传 challenge/validation，未提交预测结果。
