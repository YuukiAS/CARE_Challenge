---
task_key: "20260625_cine_geometry"
project: "CARE-Myocardium"
status: "ready"
executor: "Codex"
risk_level: "medium"
allow_code_change: true
allow_shell_command: true
allow_network: false
allow_external_upload: false
requires_human_approval: false
max_single_job_walltime: "08:00:00"
max_parallel_gpu_jobs: 2
---

# Task 20260625 Cine Geometry

## 目标

继续推进 CineMyoPS 次线。上一轮 `20260621_cine_retrieval` 停在 `REVISE_GEOMETRY`，原因是 frame0/reference evidence plausibly correct，但 strict metadata match only `59/64`，存在4个origin mismatch和1个spacing mismatch，geometry-aware crop/inverse mapping未证明。本任务目标是修复或分层处理 reference/geometry/crop 问题，并在safe subset上继续reference-frame control或temporal retrieval preflight；不要让5个mismatch cases阻塞整个Cine路线。

## 必读材料

- `AGENTS.md`
- `prompts/AGENT_RULES.md`
- `prompts/tasks/20260625_cine_geometry.md`
- `docs/notes/deep_research/Result4.pdf`
- `results/20260621_srr_goal/final_status.md`
- `/overflow/htzhu/mingcheng_new/temp/care_worktrees/20260621_cine_retrieval/results/20260621_cine_retrieval/result.md`，若存在
- `/overflow/htzhu/mingcheng_new/temp/care_worktrees/20260621_cine_retrieval/results/20260621_cine_retrieval/decision.md`，若存在
- `results/20260620_cinema_adapter_pilot/result.md`
- `results/20260620_cinema_adapter_pilot/MANIFEST.md`
- CineMyoPS raw 4D data、Dataset502、Task026、existing evaluator和CineMA adapter scripts

若旧worktree结果路径不存在，不要停止；重跑最小Cine geometry audit并记录。

## 允许动作

- 新增或修改Cine geometry audit、reference detection、safe/mismatch split、crop/inverse mapping和report scripts。
- 复用已下载CineMA code/weights和已有adapter outputs；不得联网。
- 对safe 59/64 train cases继续preflight或训练一个reference-frame control；对mismatch 5 cases只做诊断/修复，不强行纳入训练。
- 若geometry contract通过，可提交最多两个单GPU jobs，每个<=8小时。
- 写 `results/20260625_cine_geometry/result.md`、`MANIFEST.md`和`decision.md`。

## 禁止动作

- 不要validation submission、upload package或external upload。
- 不要联网、外部数据、新repo、新weights。
- 不要将非reference frame与single reference GT直接算Dice当作temporal效果。
- 不要恢复旧single-frame wrapper作为正式故事。
- 不要因5个geometry mismatch而停止整个Cine路线；必须先safe/mismatch分层。
- 不要覆盖已有CineMA/nnU-Net/CineMyoPS outputs。

## 执行步骤

### 1. 复盘旧结果

尝试读取旧worktree result/decision。提取：

- 59/64 safe cases列表；
- 4 origin mismatch cases；
- 1 spacing mismatch case；
- strict match定义；
- crop/inverse mapping未证明的具体原因。

若无法读取旧文件，重新运行metadata audit。

### 2. Safe/mismatch 分层

生成：

- `results/20260625_cine_geometry/safe_cases.csv`
- `results/20260625_cine_geometry/mismatch_cases.csv`
- `results/20260625_cine_geometry/geometry_audit.md`

对mismatch cases，不要丢弃；记录是否可通过resampling/header repair/safe reference selection修复。

### 3. Geometry-aware crop

实现或修复heart crop：

- 使用CineMA anatomy union、coarse foreground、LV/MYO/RV bbox或物理坐标ROI；
- 证明crop不会截断heart foreground；
- 证明inverse mapping回原NIfTI geometry；
- 保存before/after shape/spacing/direction/origin；
- 记录失败case。

### 4. Reference-frame control

如果safe subset geometry通过，至少运行reference-frame control preflight或fold0 short train，不要停在报告：

- 输入reference frame + geometry-aware crop；
- 可使用冻结CineMA anatomy prior作为input/teacher，但不得下载新权重；
- 输出位于reference geometry；
- 评估class_1 myocardium proxy、class_3 scar sanity、LV sanity、HD/HD95/components；
- 与旧Dataset502/single-frame弱参照比较时保持caveat。

### 5. Temporal retrieval preflight

若reference control通过且时间允许，运行轻量temporal retrieval preflight：

- 只在safe subset；
- 关键帧选择不使用GT；
- 非reference帧只作为context/motion/anatomy summary，不直接与reference label算逐帧Dice；
- 记录frame weights、entropy、reference dominance。

## 决策门

写 `results/20260625_cine_geometry/decision.md`，状态只能是：

- `GO_CINE_REFERENCE`
- `GO_CINE_TEMPORAL_PREFLIGHT`
- `REVISE_GEOMETRY_SAFE_SUBSET_ONLY`
- `REVISE_MISMATCH_REPAIR`
- `STOP_CINE_GEOMETRY`

不要因为全量64/64没有一次性完美通过而stop。如果59/64 safe subset可可靠训练，应给出`GO_CINE_REFERENCE`或`GO_CINE_TEMPORAL_PREFLIGHT`，并把5个mismatch作为后续repair。

## 预期产出

必须写：

- `results/20260625_cine_geometry/result.md`
- `results/20260625_cine_geometry/MANIFEST.md`
- `results/20260625_cine_geometry/decision.md`
- `results/20260625_cine_geometry/geometry_audit.md`
- `results/20260625_cine_geometry/safe_cases.csv`
- `results/20260625_cine_geometry/mismatch_cases.csv`
- `results/20260625_cine_geometry/crop_roundtrip.csv`
- 若训练/推理：`metrics_summary.md`、`case_metrics.csv`、logs和prediction索引

## 停止条件

- 无法定位raw CineMyoPS data或labels。
- safe subset也无法建立可靠reference/inverse geometry。
- crop显著截断heart且无法修复。
- one-batch/preflight失败且无法修复。
- 需要联网、external upload、外部数据或单job>8小时。

## 人工决策点

- 是否接受safe-subset先行策略。
- 是否继续Cine temporal route。
- 是否把Cine从次线升级或继续watch。
