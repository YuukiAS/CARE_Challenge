# SCR-R1 W3 阻塞复盘与运行闭环修复决定

## 结论

Controller 本次阻塞是正确行为，不是偷懒。当前 `main` 已经有 CARE-SRR-Cascade 的模型骨架、损失、原型 helper、source-cache job、Slurm 壳与监控器，但正式 Python 入口明确把真实 `--formal-job` 写成 `NEEDS_REPAIR_FORMAL_ENTRYPOINT_MISSING`，调度器也被写死为任何 cache 终态都不得提交四个正式训练 job。因此，继续执行旧 W3 只能得到 dry-run 或 monitor packet，不能形成真实 6250-step matched training。

本轮授权一项同范围运行闭环修复：`SCR-R1 Runtime Closure Repair 1`，简称 `SCR-R1-RC1`。它不是 SCR-R2，不改变科学假设、模型名称、随机种子、训练预算、calibration/audit 划分、病种门槛、上传权限或 Cine 边界；它只把已经冻结的 SCR-R1 设计补成可执行、可恢复、可评价、可打包和可严格验证的生产链。

## 绑定基线

```text
repository: YuukiAS/CARE_Challenge
branch: main
blocked_remote_commit: a1b55ba3525cdca0578ec6fbee59f392e27fdde0
repair_id: SCR-R1-RC1
repair_task_key: 20260725_care_myops_srr_cascade_runtime_closure_repair
parent_task_key: 20260724_care_myops_srr_cascade_submission_rescue
result_root: results/20260724_care_myops_srr_cascade_submission_rescue
repair_result_root: results/20260724_care_myops_srr_cascade_submission_rescue/runtime_closure_repair_rc1
```

冲突优先级固定为：

```text
SCR-R1-RC1 runtime closure config
> SCR-R1 preexecution amendment
> SCR-R1 base config / executor plan
> historical controller-generated resolved contract
```

旧 `resolved_execution_contract.json` 是当时 Controller 对规划文件的解析结果，不包含后来发现缺失的正式运行实现，不能覆盖本修复。

## 阻塞根因

1. `scripts/training/run_care_srr_cascade_rescue.py --formal-job` 只校验参数并写 dry-run receipt；真实调用主动以退出码 2 停止。
2. `scripts/evaluation/orchestrate_care_srr_cascade_w3.py` 固定声明 `NEEDS_REPAIR_FORMAL_ENTRYPOINT_MISSING`，硬编码 source-cache job ID，并且在 cache PASS 后仍拒绝提交正式 job。
3. `jobs/care_mm/run_care_srr_cascade_formal_training.sh` 只是调用上述缺失入口，不包含真实 sampler、cache patch loader、optimizer、checkpoint、validation 或 resume 实现。
4. W4 checkpoint selection、冻结 audit、W5 official inference/package 和 W6 strict validator 仍没有正式入口；即使临时补出 W3，后续还会再次 block。

## 前序 Wave 审计

### Wave -1：保留 PASS

四份合同路径、SHA 和 amendment precedence 已记录。该部分不需要重做，只需在修复启动时把本文件、修复 config 和修复 executor plan 加入新的 authority chain。

### Wave 0：条件保留，必须补实证

可保留：220 例 OOF manifest、五折分布、两个 frozen checkpoint 的路径和 SHA、22/22 calibration/audit split、plans 指纹。

必须修复：

- 旧 `anchor_grid_roundtrip_checks.csv` 主要证明 manifest 中 prediction/label 的几何元数据相等，没有证明每例 probability tensor 映射到 ResEncM 预处理网格、再由官方 inverse export 返回后与冻结 OOF prediction 零体素差异。
- Controller 启动时工作树存在预先已有的 untracked Batch10 audit 文件。修复开始时必须分类记录，不得把未知脏文件静默混入 SCR-R1 commit。
- source-cache race 的 job ID 与 lock 状态写死在脚本里，不可用于后续 retry/resume。

### Wave 1：代码可复用，但必须原位修复

可保留：bounded correction 公式、0–3 通道 identity、no-T2 edema identity、冻结 source 语义、基础 loss 公式。

必须修复：

- 当前 `CARESRRCascadeRescue` 使用一个共享 `input_projection + residual_blocks` 同时产生 scar 与 edema 输出，不符合“独立病种纠错头”。正式实现必须具有完全独立的 scar trunk 与 edema trunk；scar job 不得更新或计算 edema branch，反之亦然。
- 当前 prototype record 将多个 safe-negative 类别压成一个病例均值，并截取 mask 中前 N 个 voxel，存在类别信息丢失和空间顺序偏差。正式 bank 必须按病例×病种×正负类别保存独立向量，使用由 `sha256(case_id|category|seed)` 驱动的无放回确定性采样。
- 当前代码没有生产级 anchor/cache patch loader、匹配 schedule、真实 augmentation 或 formal trainer。

### Wave 2：仅保留诊断价值，正式授权必须重跑

旧 preflight 在约 8 秒内完成，主要使用 `[B,4,2,4,4]` 合成 source feature。旧 fiducial check 只是复制相同 tensor 并检查坐标，没有实际调用空间增强；旧 overfit 不是基于真实 32 通道 frozen feature、真实 OOF anchor 和真实标签；多个 known-bad 条目通过“该阶段没有执行相关动作”而标为 rejected。它们不能授权 W3。

修复后必须重新完成：

- 真实 OOF anchor 全 220 例 tensor/grid/export roundtrip；
- full source cache 或经过严格 adoption 的现有 cache；
- 真实 32 通道 patch 上 scar/edema 各 200 optimizer-step overfit；
- actual shared augmentation function 的 fiducial；
- 每项 active pathology loss 独立 backward；
- category-aware prototype intervention；
- 两 partition GPU preflight；
- 真实 validator known-bad 注入。

### Wave 3：当前 BLOCKED，修复后重启

此前没有任何正式训练 credit。已提交的 source-cache job 是 prerequisite attempt，不是 formal model training。修复 Controller 必须刷新 `squeue/sacct`：

- 已完成 cache 只能在通过新 adoption validator 后复用；
- pending 的旧 cache attempt 可以取消并由新状态驱动 orchestrator 重建；
- running attempt可以完成，但失败、残缺或 stale lock 不得阻止 repaired cache job；
- 不得重复记账或把旧 monitor receipt 写成 W3 PASS。

## 冻结科学设计

方法仍为 `CARE-SRR-Cascade`。最终每个病种都从冻结 nnU-Net anchor 出发：

$$z_{scar}^{final}=z_{scar}^{anchor}+r_{scar}\,2\tanh(\Delta_{scar}),$$

$$z_{edema}^{final}=z_{edema}^{anchor}+m_{T2}r_{edema}\,2\tanh(\Delta_{edema}).$$

通道 0–3 始终逐体素等于 anchor。scar job 中 edema 通道等于 anchor；edema job 中 scar 通道等于 anchor。Control 与 SRR 只允许在病种 prototype similarity maps 是否为零上不同。

## 生产运行闭环

本修复必须实现并验收以下固定入口：

```text
src/care_myocardium/srr_production/anchor_runtime.py
src/care_myocardium/data/care_srr_cascade_runtime.py
src/care_myocardium/training/care_srr_cascade_trainer.py
scripts/training/run_care_srr_cascade_formal.py
scripts/inference/run_care_srr_cascade_inference.py
scripts/evaluation/evaluate_care_srr_cascade.py
scripts/evaluation/select_care_srr_cascade.py
scripts/evaluation/validate_care_srr_cascade_packet.py
```

并修复：

```text
src/care_myocardium/models/care_srr_cascade_rescue.py
src/care_myocardium/srr_production/case_prototypes.py
jobs/care_mm/precompute_care_srr_cascade_source_cache.sh
jobs/care_mm/run_care_srr_cascade_formal_training.sh
scripts/evaluation/orchestrate_care_srr_cascade_w3.py
```

所有 API、算法、输出 schema、job 拓扑、retry、selection、audit、package 和 validator 细节以 `configs/care_mm/srr_cascade_runtime_closure_repair.yaml` 为机器权威，Executor 不再需要补科学设计。

## 防止后续再次阻塞

修复不是只补 W3 train loop。它同时预定义：

1. 全 220 例 anchor/source/prototype cache 的生成与 adoption；
2. 四个 formal logical run 的状态驱动 submission/resume；
3. 5 个 checkpoint 的 calibration 推理与机械选择；
4. 固定六候选、病种独立 audit 和 fallback；
5. official 15+15 inference/package dry-run；
6. strict validator、known-bad、Mapper、CURRENT/wiki 和本地轻量 commit。

只有真实服务器资产或集群状态不满足合同，Controller 才能返回 `OPERATIONALLY_BLOCKED`。普通缺失实现、错误 schema、失败测试、cache 格式、训练 bug、评价 bug和打包 bug均属于本修复范围，必须退回同一 Executor 修复，不能再次以“缺少无歧义设计”为由终止。
