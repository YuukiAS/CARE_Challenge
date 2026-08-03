---
task_key: 20260804_care_ase_r2_emergency_9h_training_docker
task_kind: scientific_milestone
task_type: deadline_bounded_formal_training_inner_comparison_and_docker_staging
status: AUTHORIZED_BY_USER
risk_level: critical
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
planning_reviewer: none
planning_review_path: null
planning_review_token: null
planning_reviewed_commit: null
review_required: false
review_mode: none
reviewer: none
allow_git_commit: true
auto_git_commit: true
allow_git_push: true
auto_git_push: true
allow_diagnostic_push: false
formal_training_authorized: true
user_authorized_controller_training_permit: true
inner_evaluation_authorized: true
outer_access_authorized: false
validation_upload_authorized: false
docker_source_and_build_staging_authorized: true
docker_upload_authorized: false
organizer_email_send_authorized: false
hosted_metric_claim_authorized: false
fixed_interactive_jobs:
  fold1: 61794608
  fold4: 61830309
formal_steps_per_fold: 14000
hard_training_completion_hours_from_controller_t0: 9
hard_docker_staging_hours_from_controller_t0: 10
---

# CARE-ASE R2 截止日前 9 小时正式训练、连续公平比较与 Docker 并行准备 Controller

## 结论与执行姿态

这是 CARE-ASE 本次提交前的最后一个 Controller Goal。用户不再等待独立 Planner/GPT 复核：Controller 必须先直接检查当前实现，关闭下面列出的、会让训练变慢或让结果失真的明确缺口，随后在现有两个 interactive GPU allocation 中并行完成 fold1 与 fold4 的固定 14,000 optimizer-step 正式训练。

训练过程中必须在固定 inner 病例上多次产生与同病例、真正 held-out 的 nnU-Net OOF 基线之间的公平比较。低分本身不能成为随意改架构、改 loss 或提前停止 Stage B/C 的理由；只有明确的实现、数值、数据、推理或采样错误才允许在唯一的早期修复窗口内改源码并从 step0 重启。

Docker 准备从 Controller 启动时就并行进行，不能等训练结束才开始。必须保留已经完成 15+15 官方黑盒彩排的现有 MyoPS/CineMyoPS Docker 作为不可破坏的 fallback；新 CARE-ASE Docker 使用相同官方接口和已验证打包经验，但不得复制旧模型行为。训练结束后只需要注入冻结 checkpoint、完成黑盒等价性和导出，而不是从零搭环境。

用户已明确授权本 Controller 在完成源码检查、测试和 Controller 自验后直接签发本任务专用训练 permit；不得再等待外部 GPT。用户没有授权 outer、validation upload、Docker 上传或组织方邮件发送。

---

## 一、时间预算是硬合同

Controller 启动时记录：

```text
T0_utc
T0_local_Asia_Hong_Kong
hard_training_deadline = T0 + 9h
hard_docker_staging_deadline = T0 + 10h
```

时间分配：

```text
T0–T0+45min:
  最新源码审计、P0/P1小范围修复、target/cache与fair-eval准备、测试、Commit A/B、训练permit

最迟 T0+60min:
  fold1 与 fold4 都必须从 step0 开始正式训练

T0+60min–T0+8h45min:
  两折并行训练、每个2000-step逻辑chunk后的公平inner比较、checkpoint保存与resume

最迟 T0+9h:
  两折14000步终态或真实不可完成证据、候选checkpoint冻结、fair comparison聚合

T0起即并行，最迟 T0+9h30min:
  CARE-ASE Docker基础镜像、入口、依赖、预处理、后处理和无checkpoint黑盒骨架已经准备

最迟 T0+10h:
  selected CARE-ASE checkpoint可被注入Docker并开始最终build；
  或明确冻结现有已验证fallback Docker，不得继续无边界研究
```

任何阶段不得重新进行开放式研究、长 GPU debug、50-step以上独立 smoke、模型组件扩展或新的实验路线。源码检查和修复超出45分钟时，Controller只允许继续处理本文件列出的确定性 P0；其余记入风险，不得无限拖延正式训练。

---

## 二、启动、同步和机器真值

仓库：

```text
/users/a/e/aereinh/CARE
```

远端：

```text
YuukiAS/CARE_Challenge
```

分支：

```text
main only
```

执行：

```bash
cd /users/a/e/aereinh/CARE
source /users/a/e/aereinh/CARE/.care-codex-env.sh
source /users/a/e/aereinh/CARE/env_nnunet.sh
export PATH=/users/a/e/aereinh/codex-runtime/bin:/users/a/e/aereinh/CARE/envs/env_CARE/bin:$PATH

git fetch origin main --prune
git checkout main
git pull --ff-only origin main
git rev-parse HEAD
git rev-parse origin/main
git status --short --branch
git log --oneline --decorate -20
git diff --check
```

不得 reset、clean、force push、创建 route/task 分支或写 `/overflow/htzhu/CARE`。若工作树有非本任务修改，先保存证据并判断归属，不得覆盖。

已知 v9 基线：

```text
v9 implementation Commit A:
2069527d4d2f6357a0fddfa9df0c49223691a96f

v9 review packet Commit B:
953e02798ce38da804a87ff561fa260922f8d947

v9 diagnostic:
pytest 114 PASS
G1 PASS
fold1/fold4 short-smoke + resume PASS
4/10 optimizer-step reservations completed
formal training credit = zero
outer access = 0
```

后续文档/gitignore/leaderboard提交可能位于 Commit B 之后；必须保留。v9 receipt 是输入证据，不是本任务训练许可。

完整读取：

```text
AGENTS.md
START_HERE_FOR_GPT.md
GPT_PLANNER_CARE_PROTOCOL.md
prompts/FINAL_OUTPUT_READABILITY_POLICY.md
prompts/AGENT_FLOW_V2_PROTOCOL.md
prompts/HANDOFF_GATE_POLICY.md
prompts/GPT_HARD_GATE_PROMPT.md
prompts/routes/README.md
prompts/routes/route_portfolio_planner_prompt.md
prompts/routes/handoffs/CURRENT.md
prompts/routes/ROUTE_ANTI_LAZINESS_PROTOCOL.md
prompts/routes/ROUTE_HARD_REQUIREMENTS_MATRIX.md
routes/README.md
wiki/README.md
.agents/skills/slurm-routing-partition/SKILL.md
.agents/skills/care-mapper/SKILL.md
```

读取当前方法与实现：

```text
prompts/blueprints/CARE_ASE_final_model_blueprint_20260801.md
prompts/blueprints/CARE_ASE_exact_implementation_contract_20260801.yaml
prompts/blueprints/CARE_ASE_R2_effective_contract_v9_20260803.yaml
prompts/tasks/20260803_care_ase_r2_last_hotfix_v9.md
prompts/tasks/20260803_care_ase_r2_last_hotfix_v9_final_addendum.md
results/20260803_care_ase_r2_last_hotfix_v9/**

src/care_myocardium/models/care_ase.py
src/care_myocardium/training/care_ase_runtime.py
src/care_myocardium/training/care_ase_trainer.py
src/care_myocardium/training/care_ase_sampler.py
src/care_myocardium/training/care_ase_augmentation.py
src/care_myocardium/data/care_ase_splits.py
src/care_myocardium/inference/care_ase_r2_decode.py
src/care_myocardium/inference/care_ase_r2_full_volume.py
scripts/training/care_ase/run_care_ase_r2_chunk.py
scripts/evaluation/care_ase/monitor_care_ase_r2_inner_trend.py
scripts/evaluation/care_ase/select_care_ase_r2_inner_checkpoint.py
scripts/evaluation/care_ase/build_stock_oof_preprocessed_grid_predictions.py
scripts/evaluation/care_ase/build_care_ase_r2_hard_negative_manifest.py
scripts/evaluation/care_ase/build_care_ase_r2_full_case_target_manifest.py
scripts/evaluation/care_ase/evaluate_care_ase_r2_outer.py
jobs/care_ase_r2/run_fold_chunk_htzhulab.sh
tests/care_ase/**
```

读取 Docker 证据和源码：

```text
prompts/tasks/20260801_care_test_docker_rootless_unblock_controller.md
results/20260803_care_test_docker_official_submission_rehearsal_and_staging/**
results/20260803_care_test_docker_official_submission_resume_after_rclone/**
results/20260803_care_test_docker_server_final_submission_readiness_confirm/**
docker/CARE2026_Myocardium/MyoPS/**
docker/CARE2026_Myocardium/CineMyoPS/**
```

检查用户已下载的合作者/reference Docker archive、其 image ID、接口对照 receipt 和现有 final archive；只作接口与打包参照，不作为 CARE-ASE 模型来源。

Planner 已视觉读取并冻结以下图中表达的业务目标：

```text
SRR-v2
SRR-v2.5
SRR-v3
CARE-ASE
```

恢复的模型目标：成熟 stock nnU-Net encoder/bottleneck/shared low-mid decoder只运行一次；最高两级为 anatomy、scar、pure-edema 三条路径；scar由 LGE主导并解决小组件/错误定位/远端FP，edema由T2主导进行连续全体积重建；C0仅弱支持；no-T2不进入edema图和class4竞争；最终是单一端到端checkpoint和全体积连续推理。

---

## 三、官方 Docker 合同

Controller 必须把以下 CARE 2026 Myocardium 官方要求写入 Docker contract 和 validator：

```text
submission email:
care26challenge@163.com 或 care2026challenge@outlook.com

subject:
[CARE-Myocardium Test] <Team-Name> – Docker Submission

archive:
.tar 或 .tar.gz，提供公开下载链接

MyoPS input:
/input/myops/Case<ID>_C0.nii.gz
/input/myops/Case<ID>_LGE.nii.gz
/input/myops/Case<ID>_T2.nii.gz

MyoPS output:
/output/myops/Case<ID>_pred.nii.gz

CineMyoPS input:
/input/cinemyops/Case<ID>_Cine.nii.gz

CineMyoPS output:
/output/cinemyops/Case<ID>_pred.nii.gz

/input只读
/output可写
无交互
正常退出
多任务使用独立Docker image
CPU优先；如果需要GPU必须在邮件中明确说明
每个任务最多3次有效提交，runtime/invalid output失败不计次数
```

MyoPS官方输出标签：

```text
0 -> background
200 -> myocardium
500 -> LV
600 -> RV
1220 -> pure edema
2221 -> scar
```

内部 compact label 转换固定：

```text
0 -> 0
1 -> 200
2 -> 500
3 -> 600
4 -> 1220
5 -> 2221
```

不得通过 largest-component、case selector、手调threshold、scar优先覆盖或另一模型fallback改变 CARE-ASE canonical argmax。

---

## 四、执行前必须关闭的源码缺口

下面是当前 v9 源码中仍可直接定位、会影响结果或9小时可执行性的点。Controller 必须逐项检查真实代码；确认存在时在同一任务中修复，确认已被后续提交修复时记录具体 source path/test，不重复改。

### P0-A：canonical full-volume inference必须与stock nnU-Net语义完全一致

当前自写的 `starts_for`、end-only padding、Gaussian和默认 `use_mirroring=False` 不能仅凭同路径自洽测试声明公平。

必须：

1. 直接复用或逐值绑定当前安装 nnUNetv2 的：
   - `compute_steps_for_sliding_window`；
   - `pad_nd_image`及返回slicer，采用与stock相同的对称padding；
   - canonical Gaussian importance map；
   - stock checkpoint/trainer实际 `inference_allowed_mirroring_axes`；
   - mirror/inverse-mirror、dtype和denominator规则。
2. base logits、`p_wall`与四个extent evidence map使用同一tile、同一Gaussian、同一mirror/inverse mirror和同一denominator。
3. 每个tile只增加一次denominator。
4. tile forward必须 `disable_extent_wall=True`，全局聚合后只加一次extent bias。
5. inner monitor、checkpoint selection、outer evaluator和Docker只能调用这一条canonical full-volume path。
6. 在不读取outer的情况下，真实运行step0 full-volume parity：
   - fold1、fold4各至少一个tri-modal inner病例和一个no-T2 inner病例；
   - CARE-ASE step0 anatomy/scar及conditional decode与对应stock初始化预期一致；
   - 记录max-abs、argmax changed、inference settings和case IDs。

新增/更新强测试，不得继续用全零模型掩盖聚合错误：

```text
test_full_volume_uses_nnunet_steps_padding_gaussian.py
test_full_volume_nonzero_overlap_exact_average.py
test_full_volume_stock_mirror_axes_bound.py
test_full_volume_step0_real_case_parity.py
```

### P0-B：scar center不得被patch边缘重算

当前 `make_batch()` 的 transformed full-case center heatmap不能随后被 `_component_center_heatmap(final_seg, ...)` 覆盖。

固定：

- full-case component ID、volume、centroid和center heatmap是authority；
- center heatmap随image/seg同一个spatial transform；
- patch边缘裁断component时不得重新标号或重新计算patch-local centroid；
- augmented final patch只允许重算geometry/context/boundary等真正依赖变形后形态的字段；
- component metadata lookup必须保留full-case物理volume与identity。

真实测试必须包含跨patch边界的单个scar component，验证target峰值仍是变换后的full-case中心，而不是patch残片中心。

### P0-C：extent的source-z和H/W validity必须来自同一个真实transform

当前使用augmentation前 `initial_origin/full_hw_coverage` 和未变换的source-z推断不足。

必须把以下authority作为额外离散target与image/seg通过同一个stock transform：

```text
source_z_id
source_z_valid
source_inplane_footprint
```

要求：

- nearest interpolation；
- z mirror时source-z顺序真实翻转；
- padding保持invalid；
- spatial scale/rotation/crop后，从transformed footprint判断该输出slice是否完整覆盖源H/W；
- presence validity与area validity分开：合法source-z的full-case presence可以监督；只有完整H/W覆盖时area和area/wall-derived final bias才有效；
- partial-H/W slice的area loss、area bias和wall bias梯度为0；
- 不得用一个 `extent_valid_z` 同时关闭所有presence与area语义。

新增真实identity/mirror/scale/padding测试。

### P0-D：Sampler类别与坐标必须名实相符

修复当前候选生成中的语义降级：

- `oof_fn/oof_fp/edema_oof_fn_or_low_volume/edema_safe_fp`只能使用v9 direct held-out OOF manifest坐标；没有坐标时必须在抽病例前解析到下一真实类别，禁止用GT lesion/background冒充OOF。
- `small_component`使用full-case physical volume `<1000 mm3`，不得使用`voxel_count <1000`，不得在没有small component时退化为全部scar。
- edema boundary使用full-case physical boundary-valid map，不能使用固定voxel dilation/erosion替代。
- remote background使用距wall >10mm；blood-pool adjacent使用冻结物理距离定义，不能把所有background或blood voxel冒充。
- `requested_category/resolved_category/fallback_reason/eligible_case_count/candidate_coordinate_count/selected_coordinate/coordinate_source`必须与实际完全一致。
- 正式descriptor必须在materialization前已有selected coordinate；formal mode禁止`deterministic_center()`静默fallback。

对全部focus类别跑真实pool/coordinate membership测试。

### P0-E：9小时训练吞吐修复，禁止科学降级

当前短smoke没有正式ETA；正式训练前必须进行非科学语义的性能闭合：

1. full-case target cache：
   - 禁止8-case LRU随机抖动时重复运行全体积EDT/component/context；
   - 在node-local或任务专属本地runtime预构建actual-train target cache，或使用原子on-demand持久cache；
   - fold1/fold4共享只读cache时用atomic lock和payload SHA；
   - cache不存在可重建，但结果必须与manifest逐数组SHA一致；
   - 禁止通过删target、patch-local重算或降低精度加速。
2. image/seg I/O：允许受控CPU LRU、prefetch和pinned memory；不得改变case/patch/augmentation顺序。
3. GPU同步：
   - detailed metrics只在日志步、checkpoint和比较步收集；
   - 非日志step不得把每个loss逐项 `.cpu().item()`；
   - finite检查保持fail-closed，可聚合device flag后每step一次同步；
   - 每step最多同步一次必要loss/grad摘要。
4. I/O：CSV和JSON批量flush；heartbeat独立；checkpoint仍每1000步保存，完整reload验证至少在每个2000-step chunk terminal和最终step执行。
5. 禁止：缩小patch、减少4 microbatch、删除augmentation/loss/head、降低14000步、跳Stage、使用较小网络、改采样比例。

在正式step0后记录前20、50、100 optimizer steps的：

```text
median/p90 step time
case load time
target cache time
augmentation time
forward/backward/update time
checkpoint time
projected fold finish UTC
```

若100步外推任一fold无法在hard training deadline前完成，Controller先做本节允许的source-preserving优化；不能偷偷缩训练合同。

### P0-F：inner split、监控和selector当前不能依赖缺失或错字段

必须生成并冻结：

```text
results/20260804_care_ase_r2_emergency_9h_training_docker/split_case_lists.csv
```

来源只能是 `build_care_ase_case_roles(repo, fold)`，包含fold1/fold4全部 `actual-train/inner/outer`，并验证：

```text
inner与outer不重叠
actual-train与inner/outer不重叠
inner不进入formal sampler
outer access count始终0
```

修复 `monitor_care_ase_r2_inner_trend.py` 与 `select_care_ase_r2_inner_checkpoint.py` 的字段不一致。当前selector要求的 `help_harm_vs_nnunet/help_harm_vs_mosaic` 与monitor实际字段不一致，且旧selector公式不等于冻结蓝图。

新fair evaluator必须输出真实同病例数据：

```text
Dice
HD95 mm
exact HD mm（完整panel/full-inner时）
precision
sensitivity
lesion recall
small-lesion recall <1000mm3
component count
remote FP count/volume >10mm
blood-pool-adjacent FP
volume ratio
empty prediction
case-wise help/harm/neutral, threshold ±0.01
CenterB/CenterC
T2/no-T2
small scar
```

nnU-Net基线必须是该病例真正held-out的stock OOF：

- 优先复用有完整producer/checkpoint/array/hash证明的OOF artifact；
- 如果只有CSV指标，早期quick panel可以join其Dice/volume/component字段，但必须明确哪些物理指标不可用；
- 最终候选比较必须有实际prediction array并通过同一个physical evaluator，必要时只为frozen inner panel fresh运行held-out stock fold；
- 禁止同fold in-sample nnU-Net、不同case set、patch proxy、不同decode或不同几何。

### P0-G：用户授权的Controller permit

本任务不再等待外部 GPT。不得伪造“external reviewer”。

新增明确token，例如：

```text
PRETRAINING_CONTROLLER_USER_AUTHORIZED_PASS_20260804
```

permit必须由Controller在以下全部通过后生成：

```text
用户授权task SHA
Commit A source SHA
Commit B packet SHA
v9/v10 effective contract SHA
critical source manifest SHA
formal runtime input bundle SHA
fold-specific hardware/environment receipt SHA
split/case list SHA
hard-negative manifest SHA
full-case target manifest SHA
baseline/fair-eval contract SHA
pytest/G1/step0 parity PASS
outer access 0
```

formal verifier只能为本task接受该token；旧任务不能借此绕过外部review。两折分别生成permit并绑定各自allocation hardware receipt。不得接受placeholder SHA。

---

## 五、测试、Commit A/B和source freeze

本任务只允许针对上述源码做修复，不重新设计CARE-ASE。

运行优先级：

```text
1. targeted tests covering P0-A至P0-G
2. tests/care_ase critical subset
3. G1
4. 两折真实step0 full-volume parity（无optimizer step）
5. 每折最多1个optimizer-step short probe，仅在source变化后需要
```

不再运行长诊断训练。全部CPU测试可以与Docker base准备并行，但训练启动不得被非关键全套文档测试拖过T0+60min。

两阶段冻结：

```text
Commit A:
  source、tests、effective execution contract、validators、fair evaluator、Docker source skeleton

Commit B:
  static manifests、split lists、runtime input bundle、Controller permits、轻量receipts、CURRENT/wiki
```

Commit B不得修改任何critical source。push `origin/main` 后验证A是B祖先且A/B critical source manifest一致。

正式训练从clean detached Commit B语义运行；若使用main checkout，必须固定HEAD=B且所有动态写入只到source/fold runtime namespace。

---

## 六、现有 interactive allocations 的固定使用

用户已提供：

```text
fold1 job: 61794608  htzhulab  CareInteractive2d
fold4 job: 61830309  htzhulab  CareASEFold4Interactive2d
```

先检查：

```bash
scontrol show job -dd 61794608
scontrol show job -dd 61830309
squeue -j 61794608,61830309 -o '%.18i %.12P %.35j %.2t %.10M %.10l %.4D %R'
srun --jobid=61794608 --overlap --ntasks=1 bash -lc 'hostname; echo $CUDA_VISIBLE_DEVICES; nvidia-smi -L; nvidia-smi --query-gpu=name,memory.total,compute_cap --format=csv,noheader'
srun --jobid=61830309 --overlap --ntasks=1 bash -lc 'hostname; echo $CUDA_VISIBLE_DEVICES; nvidia-smi -L; nvidia-smi --query-gpu=name,memory.total,compute_cap --format=csv,noheader'
```

必须证明两allocation各自可见一块授权GPU；不能在同一GPU上重叠两个fold。若Slurm环境显示同一物理GPU，先修正`srun`绑定，禁止直接并发OOM。

固定映射不可交换：

```text
61794608 -> fold1
61830309 -> fold4
```

使用task专属tmux：

```text
care_ase_9h_controller
  controller
  fold1_train
  fold4_train
  fair_monitor
  docker_stage
  finalizer
```

训练命令必须通过各自job allocation中的`srun --jobid ... --overlap`或等价合法job-step执行，禁止在login node裸跑GPU进程，禁止提交新的长时间sbatch替代现有allocation，除非某allocation客观失效且同范围恢复必须。

fold runtime完全隔离：

```text
results/20260804_care_ase_r2_formal_training_<CommitA-short>/runtime/fold_1
results/20260804_care_ase_r2_formal_training_<CommitA-short>/runtime/fold_4
```

logs、locks、checkpoint、monitor packet、selection packet不得跨fold覆盖。

---

## 七、正式训练合同

每fold固定：

```text
optimizer: AdamW
weight decay: 1e-4
physical batch: 1
gradient accumulation: 4
effective batch: 4
patch: 20x256x256
checkpoint every 1000 optimizer steps
fixed total: 14000 optimizer steps
Stage A: 0–2000
Stage B: 2000–10000
Stage C: 10000–14000
no early stop
```

两个fold同时开始，从step0使用相同source/config但不同fold stock checkpoint、split、manifest、sampler state和runtime。

逻辑chunk：

```text
0–2000
2000–4000
4000–6000
6000–8000
8000–10000
10000–12000
12000–14000
```

每个chunk：

1. 启动前验证上一checkpoint/verified receipt/resume hash；
2. 完成2000真实optimizer steps；
3. step中间1000保存checkpoint；
4. terminal checkpoint full reload、optimizer/scheduler/sampler/RNG/next-bundle验证；
5. 运行对应quick fair comparison；
6. 立刻启动下一chunk，不等待人工确认。

任一job失败时，Controller执行同source、同fold、同checkpoint的操作性resume；失败startup/partial step无credit。不能因一个fold失败停止另一个正常fold。

---

## 八、训练期间的公平比较计划

### 8.1 冻结病例面板

每fold从inner病例中在训练前冻结两个面板：

```text
FAST_PANEL:
  10–12例，固定case IDs；
  覆盖CenterB、CenterC、tri-modal、no-T2、小scar、scar大病灶、edema低敏感病例；
  只能从该fold inner抽取；
  选择规则和case list在step0前冻结，后续不得按结果换病例。

FULL_INNER:
  该fold全部inner病例。
```

若某个历史hard case属于outer，不能放入任何monitor；只在结果中写 `OUTER_NOT_ACCESSED`。

### 8.2 比较轮次

每fold至少产生以下真实比较：

```text
step0:     real full-volume stock-init parity与基线sanity
step2000:  FAST_PANEL，Stage A终点
step4000:  FAST_PANEL；若全inner单折耗时<=12min，同时FULL_INNER
step6000:  FAST_PANEL
step8000:  FAST_PANEL
step10000: FAST_PANEL + FULL_INNER，Stage B终点
step12000: FAST_PANEL
step14000: FAST_PANEL + FULL_INNER，最终
```

若comparison累计耗时威胁9小时训练：

- FAST_PANEL仍必须保留至少step2000/4000/8000/10000/14000五轮；
- FULL_INNER最低保留step10000和14000；
- 不得减少正式训练步数；
- 不得换成patch proxy；
- 记录哪些计划轮次因deadline被跳过及真实原因。

### 8.3 每轮输出

```text
results/20260804_care_ase_r2_emergency_9h_training_docker/fair_comparison/
  fold_<fold>/step<step>/casewise.csv
  fold_<fold>/step<step>/summary.json
  fold_<fold>/step<step>/comparison_vs_nnunet.md
```

summary必须先给自然中文判断，再记录：

```text
checkpoint SHA
source SHA
case-list SHA
CARE inference contract SHA
nnU-Net OOF source/checkpoint/prediction SHA
metric implementation SHA
scar mean/median Dice和delta
pure-edema mean/median Dice和delta
HD95 delta
precision/sensitivity
lesion/small-lesion recall
remote FP
blood-adjacent FP
component count
volume ratio
help/harm/neutral
CenterB/CenterC
no-T2 scar
empty-prediction count
runtime
outer_access=0
```

fair monitor只读checkpoint，不修改训练model/optimizer/RNG/sampler。

### 8.4 早期实现异常门

以下不是“科学低分”，而是明确异常，必须检查实现：

```text
NaN/Inf loss、grad、parameter或Adam state
step0 canonical full-volume parity失败
no-T2出现class4输出或edema-owned gradient
anatomy在Stage A相对stock大面积改变
超过一半FAST_PANEL scar或T2-present edema预测为空
多数病例volume ratio <0.05 或 >10
sampler requested/resolved/coordinate不一致
某mandatory named evidence始终无gradient或无owned-logit intervention
checkpoint无法reload/resume
同一checkpoint重复推理不确定
CARE/nnU-Net使用不同case、geometry、decode或metric
```

### 8.5 唯一源码修复窗口

允许一次source-changing repair窗口：

```text
截止：T0+2h
触发：必须有上述具体异常和source-level root cause
最长：30分钟
动作：停止两个fold、保存失败证据、修source/tests、创建新Commit A/B/permit、两fold均从step0重启
```

禁止仅因Stage A Dice低就改architecture、loss权重、采样比例、extent系数、threshold或训练预算。T0+2h后不再允许科学/实现source改动；只允许不改变数值语义的crash/resume、I/O、lock和allocation恢复。任何T0+2h后的source变化都必须明确声明旧checkpoint作废并证明仍能在硬deadline内从0完成，否则不执行。

---

## 九、checkpoint候选和最终冻结

候选固定：

```text
4000, 6000, 8000, 10000, 12000, 14000
```

修复selector，使其消费实际monitor字段和冻结蓝图分数：

```text
scar_score = scar_Dice
           - 0.002 * max(0, scar_HD95_mm - stock_HD95_mm)
           - 0.00002 * remote_FP_volume_mm3
           - 0.05 * max(0, harm_fraction - 0.35)

edema_score = pure_edema_Dice
            + 0.20 * sensitivity
            - 0.05 * abs(volume_ratio - 1)
            - 0.002 * max(0, edema_HD95_mm - stock_HD95_mm)
```

两阶段、预先冻结选择：

1. 六个候选都在FAST_PANEL评分；
2. 每fold取FAST_PANEL joint排名前2，加上step14000，做FULL_INNER；
3. 单checkpoint部署，不允许scar/edema checkpoint拼接；
4. 在FULL_INNER候选中按以下lexicographic规则选每fold候选：
   - 两病种均无catastrophic collapse；
   - 最大化 `min(scar_score_delta_vs_stock, edema_score_delta_vs_stock)`；
   - 再最大化两者之和；
   - 再选择较晚step。
5. 在fold1/fold4两个候选中用相同规则选一个单一CARE-ASE deployment checkpoint。

禁止outer、public validation、threshold search、case selector、fold ensemble和pathology-specific模型拼接参与选择。

同时保留现有已验证MyoPS Docker作为fallback。最低部署安全门：

```text
scar与pure-edema均无大于0.03的FULL_INNER mean Dice下降
任一病种harm fraction不得>0.55
无大量empty prediction
无明显远端FP或volume collapse
checkpoint reload/重复推理/geometry全部PASS
```

若CARE-ASE不满足最低安全门：冻结fallback Docker，不得为了“新模型”提交更差candidate。是否最终上传由用户决定。

---

## 十、Docker准备必须从T0并行开始

Docker工作不得占用两块训练GPU；只允许CPU、磁盘和rootless Docker daemon准备基础层。最终checkpoint注入和GPU smoke在训练结束后进行。

### 10.1 不可破坏的fallback

记录并只读校验现有：

```text
MyoPS final archive SHA256:
638c1d54d1c75f3514f325695025c03bd8f43625c9f2877d72841db6ee2ac73b

CineMyoPS final archive SHA256:
c02db56bd52d14d3b5bbda9d204a20b7e4c061fd5e6012ffa1cebc67fb92c136
```

不得覆盖、重tag后误保存、删除Google Drive对象或修改现有邮件链接。CineMyoPS本轮不改模型，继续使用已验证archive。

### 10.2 CARE-ASE Docker staging

使用新目录，不能覆盖旧MyoPS：

```text
/users/a/e/aereinh/.tmp/codex-CARE/
20260804_care_ase_r2_emergency_9h_training_docker/
  docker/
    base-context/
    final-context/
    dist/
    rehearsal/
```

准备tracked source skeleton或固定runtime snapshot：

```text
Dockerfile
entrypoint.sh
predict.py
requirements.lock
README.md
asset_manifest.json
```

要求：

- 复用现有已验证Docker的 `/input` discovery、atomic output、geometry restoration、official label mapping、noninteractive ENTRYPOINT 和错误退出模式；
- 推理只使用 `load_care_ase_checkpoint_for_inference` 和canonical full-volume inference；
- Docker内包含固定plans/dataset topology及需要的nnUNet runtime；
- 无 `/users`、`/overflow`、`/nas` 绝对依赖；
- 无网络下载；
- 不依赖训练期stock checkpoint；
- checkpoint通过SHA绑定；
- 每case成功后atomic rename；任一case失败容器非零退出；
- 输入LGE geometry作为MyoPS输出reference；
- 输出labels严格为 `{0,200,500,600,1220,2221}`。

先构建不含最终checkpoint或含dummy-placeholder的base image，使依赖层提前完成。最终checkpoint必须是最后一个小层，避免重新安装全部依赖。

### 10.3 CPU/GPU声明

官方偏好CPU，但不得为CPU偷偷降级模型。

训练结束后测：

```text
1例CPU full-volume runtime
1例GPU full-volume runtime
峰值RAM/VRAM
65例线性保守外推
```

若CPU 65例外推不可接受或实际不稳定：

- 使用固定CUDA runtime image；
- 在邮件草稿中明确 `GPU required`、CUDA版本、显存要求和精确run命令；
- 不得声称CPU-only。

### 10.4 最终快速闭合

selected checkpoint冻结后：

1. inject checkpoint + SHA；
2. host vs Docker固定3例逐体素/geometry等价；
3. `/input:ro`、`--network none`、无额外command、非交互；
4. repeat determinism；
5. clean save/load/run；
6. `docker save | gzip -1`；
7. 写archive size/SHA、image ID和运行说明；
8. 只准备上传和邮件草稿，不执行上传/发送。

若CARE-ASE未过安全门，Docker staging仍保留，但final submission candidate标记为fallback existing MyoPS archive。

---

## 十一、Controller运行时连续性

Controller不得在训练submitted/running时结束。必须保持tmux watcher负责：

```text
job-step启动
每个chunk terminal accounting
checkpoint verified
fair monitor terminal
下一chunk自动resume
两fold异常隔离
最终aggregation
Docker staging
validator
commit/push
notification
```

每5分钟写轻量状态：

```text
results/20260804_care_ase_r2_emergency_9h_training_docker/live_status.json
```

字段：

```text
elapsed
hard deadlines
fold1 current step/chunk/job-step/state/ETA
fold4 current step/chunk/job-step/state/ETA
latest fair comparison per fold
source repair count
outer access
Docker base stage
fallback integrity
next action
```

不得每5分钟git commit/push。该文件可在runtime目录动态更新，最终聚合后只提交终态副本。

---

## 十二、严格禁止

```text
outer读取或评价
validation上传
Docker上传
组织方邮件发送
hidden test读取
缩短14000步
跳过Stage B/C
patch proxy冒充full volume
改threshold或postprocessing追inner分
使用Center ID进入forward
fold ensemble
scar/edema模型拼接
nnU-Net/MoSAIC inference fallback进入CARE-ASE candidate
删除loss/head换速度
改变patch或microbatch
训练过程中未冻结case panel
用in-sample baseline冒充OOF
用文件存在或PASS字符串冒充真实metric
因为早期Stage A低分直接停训
为了赶时间覆盖已验证fallback archive
```

---

## 十三、必须产出的结果

结果根：

```text
results/20260804_care_ase_r2_emergency_9h_training_docker/
```

至少包含：

```text
controller_context.json
controller_ledger.csv
controller_bootstrap_snapshot.md
source_audit_and_repairs.md
time_budget_contract.json
interactive_job_binding.json
hardware_receipt_fold1.json
hardware_receipt_fold4.json
implementation_commit_receipt.json
training_permit_fold1.json
training_permit_fold4.json
critical_source_manifest.json
formal_runtime_input_bundle.json
split_case_lists.csv
fast_panel_fold1.json
fast_panel_fold4.json
fair_baseline_manifest.json
step0_full_volume_parity_fold1.json
step0_full_volume_parity_fold4.json
throughput_projection_fold1.json
throughput_projection_fold4.json
formal_training_summary_fold1.json
formal_training_summary_fold4.json
checkpoint_manifest_fold1.json
checkpoint_manifest_fold4.json
fair_comparison/**
checkpoint_selection_fold1.json
checkpoint_selection_fold4.json
deployment_checkpoint_selection.json
promotion_and_fallback_decision.md
docker_official_contract.json
docker_fallback_integrity_receipt.json
docker_base_build_receipt.json
docker_asset_manifest.json
docker_runtime_benchmark.csv
docker_prediction_equivalence.csv
docker_output_geometry_audit.csv
docker_staging_status.json
submission_email_draft_care_ase.md
finalizer_state.json
mapper_report_draft.md
mapper_report_final.md
architecture_delta_final.md
strict_validator_report.json
known_bad_report.json
controller_report.md
completion_check.md
MANIFEST.md
notification_brief.json
```

不提交：checkpoint、NIfTI、Docker archive、raw probability、大日志、secret、rclone config或test data。

---

## 十四、Controller最终判断

Controller直接检查真实diff、runtime、casewise metrics、checkpoint和Docker，不得只相信Executor token。

成功完成必须满足：

```text
source P0全部关闭或有明确“不存在”的代码证据
Commit A/B和permits绑定
fold1/fold4每折14000真实optimizer steps
Stage A/B/C全部执行
checkpoint每1000保存
chunk terminal reload/resume PASS
至少5轮每折FAST_PANEL公平比较
step10000和14000每折FULL_INNER公平比较，除非有硬deadline真实豁免
nnU-Net baseline为same-case held-out OOF
outer access = 0
候选checkpoint按冻结规则选择
现有fallback Docker未破坏
CARE-ASE Docker base已提前准备
T0+10h前可以注入checkpoint并开始final Docker build
```

如果某fold无法在9小时内完成，必须写真实step、train-loop seconds、ETA、阻塞原因和已完成比较；不得声称训练完成。即便如此，T0+10h Docker staging/fallback仍必须完成。

终态科学分类只允许：

```text
CARE_ASE_DUAL_PATHOLOGY_CANDIDATE_INNER
CARE_ASE_SCAR_ONLY_SIGNAL_INNER
CARE_ASE_EDEMA_ONLY_SIGNAL_INNER
CARE_ASE_INNER_NO_GO_USE_FALLBACK
OPERATIONALLY_BLOCKED_DEADLINE_OR_RUNTIME
```

这些只基于inner，不是outer/hidden/test claim。

---

## 十五、提交、推送和通知

### 训练前

Commit A/B与permit完成后允许push `origin/main`。正式训练source随后冻结。

### 训练期间

不push中间runtime，不修改critical source；唯一早期实现修复窗口触发时按本合同重建A/B/permit并从0重启。

### 终态

聚合轻量结果，更新：

```text
prompts/routes/handoffs/CURRENT.md
wiki/README.md
```

创建单个轻量终态commit并push `origin/main`。确认：

```text
git rev-parse HEAD == git rev-parse origin/main
```

只有所有job-step terminal、比较聚合、Docker staging、validator、commit和push确认后，写 `notification_brief.json` 并调用：

```bash
./envs/env_CARE/bin/python controller_notifications/notify_goal_watcher.py --once
```

不得手写SMTP，不得在running/pending时通知。

---

## Executor Worker Contract

Executor只执行上述授权的源码热修、测试、正式训练启动/恢复、inner公平比较和Docker staging。Executor不能：

- 自行改变模型、loss、预算、case split、checkpoint规则；
- 访问outer；
- 宣布整个Goal完成；
- 上传Docker或发送邮件；
- 增加第二个LLM executor。

所有实现、命令、job-step、metrics和错误返回Controller验证。Controller发现本文件所列缺口时，在同一scope内退回Executor修复。

---

## Mapper Contract

Mapper只读检查最终：

```text
architecture/dataflow/loss/target/sampler
training/runtime/checkpoint/inference
inner fair comparison
Docker deployment call graph
CURRENT/wiki fingerprint
```

Mapper不得给训练许可、不得访问outer、不得改模型。只有Controller授权的wiki/fingerprint更新可写。

---

## 最终用户回传

最终回答先用自然中文说明：

1. 源码还发现并修了哪些会影响结果的问题；
2. fold1/fold4是否各完成14000步及真实用时；
3. 每轮fair comparison相对nnU-Net的scar/edema变化；
4. 是否触发早期源码修复和是否从0重启；
5. 选择了哪个fold/step，为什么；
6. CARE-ASE是双病种候选、单病种信号还是应使用fallback；
7. Docker base/final staging已完成到哪里；
8. outer、upload、email仍未执行；
9. Commit A/B、终态commit和origin/main状态。

不得只回状态token或日志。
