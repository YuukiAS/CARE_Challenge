---
task_key: "20260621_cine_retrieval"
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

# Task 20260621 Cine Retrieval

## 目标

作为 MyoPS SRR 主线的次要并行任务，依据 `Result4.pdf` 和已完成的 CineMA pilot，建立一个 CARE CineMyoPS 的 anatomy-first temporal retrieval fold0 对照：在不复活旧 single-frame wrapper、不重写完整 CineMyoPS motion-registration pipeline 的前提下，比较 reference-frame control 与关键帧/anatomy/motion-summary selective retrieval，验证 4D cine 信息是否能稳定改善本地 `class_1` myocardium proxy 或 `class_3` scar sanity，并控制 HD/HD95。

## 背景和必读材料

开始前读取：

- `AGENTS.md`
- `prompts/AGENT_RULES.md`
- `prompts/tasks/20260621_cine_retrieval.md`
- `docs/notes/deep_research/Result4.pdf`
- `prompts/Baseline_report.md`
- `results/20260620_cinema_adapter_pilot/result.md`
- `results/20260620_cinema_adapter_pilot/MANIFEST.md`
- `results/20260620_cinema_adapter_pilot/review.md`
- `docs/plans/laneB_round03plus_controller_cinemyops_hosted_topology_motion_plan.md`
- CineMyoPS raw 4D data、fold split、Dataset502/Task026 和现有 evaluator/trainer相关文件

用 `pdftotext` 抽取 Result4 中 Cine/temporal retrieval 相关段落到：

- `results/20260621_cine_retrieval/Result4_cine_excerpt.txt`

Result4 的明确建议优先于本任务对模块的示例描述；但不得超出 8 小时/job、不得外部上传或重写完整 U-MyoPS/CineMyoPS pipeline。

现有证据：CineMA ACDC SAX checkpoint已成功处理 64 train和15 validation；frame0 myocardium Dice mean/median约 `0.5723/0.6861`，LV Dice约 `0.7779/0.9092`。当前固定 center crop/pad 到 `192x192x16`，尚未做 geometry-aware heart crop；非frame0没有真实逐帧GT，不能直接用reference label评估时序表现。

## 允许动作

- 复用已下载的 CineMA repo、weights、predictions 和 isolated dependencies；不得联网下载新资源。
- 在 `src/care_myocardium/cine/`、`scripts/training/`、`scripts/evaluation/`、`jobs/src/` 新增first-party temporal retrieval代码和独立入口。
- 先完成 geometry-aware heart crop/reference-frame audit，再提交最多两个并行单GPU fold0 jobs；每个不超过8小时。
- 使用全部64 train cases按现有protocol split训练/评估；validation 15 cases只做无标签结构检查，不进入训练。
- 写 task-scoped result、manifest、metrics和diagnostics。

## 禁止动作

- 不要 official validation submission、upload-ready package 或外部上传。
- 不要联网、下载新checkpoint、外部数据或新repo。
- 不要把非reference frame与单一GT直接计算的Dice当作真实temporal性能。
- 不要继续旧single-frame compact wrapper作为所谓CineMyoPS正式故事。
- 不要重写完整motion registration + pathology pipeline，除非Result4明确给出可在本任务预算内实现的最小模块。
- 不要以LCC或普通postprocess作为本任务核心贡献。
- 不要覆盖现有CineMA/nnU-Net/CineMyoPS predictions或cache。

## Phase 1：reference和geometry contract

必须确认并报告：

- raw label对应的reference frame是否能从metadata、文件约定、LV volume curve或现有代码确定；
- frame0是否可安全视作ED/reference；若不能，定义可复现的reference detection方法；
- geometry-aware heart crop方法，优先使用可靠的CineMA anatomy union、coarse heart bbox或物理坐标ROI；
- crop前后shape、spacing、direction、affine和inverse mapping；
- heart foreground是否被截断；
- Center α/β或实际中心分组的crop失败率。

若reference语义或inverse geometry无法确认，停止训练，只写result。

## Phase 2：两个可比variant

两个variant使用相同split、seed、backbone capacity、training budget、sampler、optimizer、validation cadence和best-checkpoint rule。

### Variant C0：`reference_frame_control`

输入仅包含：

-确定的reference frame；
- geometry-aware crop；
- 可选冻结CineMA reference anatomy prior，是否使用由Result4最小contract决定。

目的：建立修复geometry后的强single-reference control，而不是复用旧middle-frame wrapper。

### Variant C1：`temporal_selective_retrieval`

按Result4实现最小temporal retrieval。至少必须满足：

- 选择固定数量关键帧，包含reference和覆盖收缩/舒张变化的frames；
- frame选择规则不使用GT或validation metrics；
- 每帧获得texture/anatomy feature，或Result4指定的motion summary；
- availability/time-position编码；
- learned或contract指定的selective retrieval/attention聚合；
- 最终预测位于reference geometry；
- 使用reference GT进行监督；非reference帧仅通过冻结anatomy prior、self/temporal consistency或无监督motion summary参与；
- 记录每个case/frame的retrieval weights；
- 防止全部权重collapse到reference frame。

如果dense未配准frame feature直接融合不合理，允许改为只检索global/context/motion descriptors来调制reference decoder；不得默默把错位feature逐像素相加。

## 训练资源策略

- 两个variant可并行提交独立GPU jobs，每个`--time<=08:00:00`。
- 在one-batch和tiny-overfit通过后，应充分使用4-6小时有效训练预算，不要停在几个epoch。
- 必须使用独立checkpoint/prediction/cache/log路径。
- 优先`htzhulab`，fallback按AGENTS执行。

## 评估

按AGENTS在本地同时报告：

- `class_1` myocardium proxy：Dice、HD、HD95；
- `class_3` scar sanity：Dice、HD、HD95；
- LV sanity若label可用；
- component count、remote components、volume ratio、empty rate；
- center分层；
- reference detection/crop失败率；
- retrieval entropy、frame usage、reference dominance、temporal diversity；
- parameter count、memory、runtime和inference cost。

不要把这些本地指标直接宣称为hosted `myocardium_cinemyops`。

## 决策门

写 `results/20260621_cine_retrieval/decision.md`，状态只能是：

- `GO_TEMPORAL`
- `KEEP_REFERENCE_CONTROL`
- `REVISE_GEOMETRY`
- `REVISE_RETRIEVAL`
- `STOP_CINE_ROUTE`
- `STOP_LABEL_SEMANTICS`

`GO_TEMPORAL` 至少要求：

- C1相对C0在class_1或class_3至少一个目标上有稳定正信号；
- 另一个目标无明显崩溃；
- HD/HD95和components不恶化；
- 增益不来自label/geometry错误；
- retrieval不完全collapse到reference；
- 多中心均无明显系统性失败。

若CineMA prior有效但temporal retrieval无增益，选择`KEEP_REFERENCE_CONTROL`或`REVISE_RETRIEVAL`，不要为统一故事强保留无效temporal模块。

## 预期产出

必须写：

- `results/20260621_cine_retrieval/result.md`
- `results/20260621_cine_retrieval/MANIFEST.md`
- `results/20260621_cine_retrieval/decision.md`
- `results/20260621_cine_retrieval/Result4_cine_excerpt.txt`
- `results/20260621_cine_retrieval/reference_geometry_contract.md`
- `results/20260621_cine_retrieval/metrics_summary.md`
- `results/20260621_cine_retrieval/case_metrics.csv`
- `results/20260621_cine_retrieval/frame_retrieval.csv`
- `results/20260621_cine_retrieval/efficiency.csv`
- scripts/jobs/checkpoints/predictions/logs索引

result 必须记录job IDs、commands、runtime、GPU、epochs、best checkpoints、stop reasons、diff和下一步。

## 停止条件

- reference frame或label geometry无法确认。
- crop/inverse mapping不可靠。
- one-batch/tiny-overfit失败。
- dense错位feature无法合理融合且没有安全context-only替代。
- job预计超过8小时且无法截断。
- 需要联网、external upload、外部数据或高风险主pipeline修改。

## 人工决策点

- 是否接受 temporal retrieval 的本地证据。
- 是否将Cine任务继续作为次线投入。
- 是否允许未来与MyoPS SRR共享retrieval实现。
