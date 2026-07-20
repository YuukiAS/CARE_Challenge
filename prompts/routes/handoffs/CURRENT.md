# CARE 当前开发状态

本文件是当前 CARE 主线工作的机器真值。任何新的规划、实现、审查、训练、推理或评价任务，都必须先读取本文件。

## 当前状态

```text
state_id: srr_mainline_batch3_inference_closure_20260720
round_id: post_round04_main_only
date: 2026-07-20
active_development_branch: main
active_worktree: /users/a/e/aereinh/CARE
portfolio_mode: SUSPENDED
single_active_scientific_line: SRR_MyoPS_Cine_from_historical_Route_B
latest_reviewed_remote_commit: b38b1a045236d94045c48f12831a41b190abe691
batch1_review_status: PARTIAL_IMPLEMENTATION_CLOSED_ONLY_AT_SMOKE_LEVEL
batch2a_review_status: PARTIAL_SHARED_COMPONENT_CLOSURE_WITH_REMAINING_GAPS
batch2b_review_status: NNUNET_BASELINE_AND_IDENTITY_EVALUATOR_COMPLETE_SRR_INFERENCE_MISSING
batch3a_status: SRR_MODEL_IN_LOOP_UNTRAINED_DIAGNOSTIC
next_required_batch: BATCH_3B_REAL_CINE_MAINLINE
controller_authorized_now: 0
route_worktree_development_authorized: false
formal_training_authorized_now: false
slurm_authorized_now: false
validation_upload_authorized: false
hosted_metric_claim_authorized: false
```

## 开发边界

当前默认只在 `main` 开发。不得启动 Route A/B/C controller，不得继续 route worktree 开发，不得创建 Round05，不得写入：

```text
/overflow/htzhu/CARE
/users/a/e/aereinh/CARE_worktrees/route_A
/users/a/e/aereinh/CARE_worktrees/route_B
/users/a/e/aereinh/CARE_worktrees/route_C
```

Route A、Route B、Route C 只保留为历史证据来源。历史 Route B 已合并进入 `main`，但不再作为活动路线运行。

除非用户另行明确授权，本阶段只允许代码追踪、代码修复、真实病例单次前向/反向、完整推理正确性验证、checkpoint 恢复测试、评价器重算和单元测试。禁止持续训练、正式 fold0 训练、Slurm、validation package、上传和榜单结论。

## 当前权威文件顺序

按以下顺序读取：

```text
1. docs/plans/laneB_round04_active_srr_batch3_myops_inference_closure_and_cine_mainline.md
2. results/srr_production/code_maturity/batch2_critic_audit_and_batch3_decision.md
3. docs/plans/laneB_round04_active_srr_batch2_inference_and_fair_evaluation.md
4. docs/plans/laneB_round04_active_srr_batch1_myops_mainline_repair.md
5. docs/plans/laneB_round04_active_srr_plan_correction_addendum.md
6. docs/plans/laneB_round04_active_srr_code_completion_todo.md
7. docs/plans/laneB_round04_active_srr_mainline_production_execution.md
8. docs/plans/laneB_round04_active_srr_change_review_ledger.md
```

最新 Batch 3 修正计划覆盖旧文件中与以下内容冲突的表述：

- Batch 2B 已经建立真实 SRR 完整体积推理；
- 当前只差用户授权 fold0 训练；
- `infer_myops.py` 的三个模式都会运行 SRR 模型；
- `--checkpoint` 已经实际加载 checkpoint；
- 所有 known-bad 都已经进入真实生产 validator；
- 验证病例应按病例 ID 哈希并排除一个训练记忆分片。

## Batch 0 状态

```text
commit: 414427746e51e5d84918e57512619a2d3412326c
status: COMPLETE
```

Batch 0 完成了当前实现真相梳理、入口权威收束和旧 B3-B8 去授权。旧 Round04 B3-B8 Python 脚本及其 job wrapper 继续是：

```text
forbidden_formal_entrypoint
```

不得重新启用。

## Batch 1 状态

```text
commit: ef98e2d3e6808fd616d2732f4d6a645431a7a4ff
reported_status: BATCH_1_MYOPS_MAINLINE_COMPLETE_FOR_BATCH2
reviewed_status: PARTIAL_IMPLEMENTATION_CLOSED_ONLY_AT_SMOKE_LEVEL
```

Batch 1 的真实贡献：

1. 建立五折共 220 例 OOF nnU-Net 缓存清单。
2. 为 `SRRProposeRefineMyoPS` 增加明确的 `anchor_bounded_srr_correction` 输出模式。
3. 将跨折记忆查询接入候选区域和最终修正。
4. 证明有 T2 病例上主要水肿模块存在梯度。
5. 做了一次真实病例前向、反向和 checkpoint 保存/恢复烟雾验证。
6. 没有训练、Slurm 或性能结论。

Batch 1 没有形成完整训练、推理和评价共用的生产主干；相关问题由 Batch 2A 部分收口。

## Batch 2A 状态

```text
commit: b797a55f17b5e4c39a6cb97e8d1e295923f7b546
reported_status: BATCH_2A_BATCH1_CLOSURE_COMPLETE
reviewed_status: PARTIAL_SHARED_COMPONENT_CLOSURE_WITH_REMAINING_GAPS
```

Batch 2A 已真实解决：

- raw OOF anchor manifest 与病例对象保存；
- 病例级特征和 provenance；
- 空记忆槽不参与相似度；
- crossfit-exclusive 候选相似度；
- 无 T2 水肿候选概率、软区域、细化残差、修正、损失和所检查梯度为零；
- checkpoint schema v2 恢复模型、优化器和随机数状态。

Batch 2A 仍有以下缺口：

1. `M10CrossFittedPrototypeMemory.query` 对训练和验证/推理仍使用同一分片排除规则；验证/推理应使用全部冻结训练分片。
2. `sample_patch_with_anchor` 和 `full_case_anchor_tensors` 仍会将无 T2 安全上下文作为模型 anchor，raw anchor 与安全上下文尚未彻底分离。
3. 多数 known-bad 仍是构造错误字典后直接返回“已检测”，没有进入真实生产 validator。
4. 计划要求的 `tests/srr_production/test_myops_batch2_preflight.py` 未建立。
5. 原型/记忆资产仍是少病例单 patch 的烟雾证据，不是完整训练集冻结资产。

## Batch 2B 状态

```text
commit: b38b1a045236d94045c48f12831a41b190abe691
reported_status: BATCH_2_INFERENCE_EVALUATION_AUTHORITY_COMPLETE
reviewed_status: NNUNET_BASELINE_AND_IDENTITY_EVALUATOR_COMPLETE_SRR_INFERENCE_MISSING
```

Batch 2B 已真实解决：

1. 从 NIfTI prediction 和 GT 重算 nnU-Net fold0 44 例指标：
   - edema Dice `0.3944358976789887`
   - scar Dice `0.5601692281262312`
2. 评价器能输出逐病例、子组、HD/HD95、连通域、小假阳性、远端假阳性、体积和帮助/伤害表。
3. nnU-Net 标签复制的恒等对照 changed voxels 为零，并保持 NIfTI 几何。

Batch 2B 没有建立真实 SRR 推理：

```text
scripts/srr_production/infer_myops.py
-> 找到 nnU-Net prediction.nii.gz
-> shutil.copy2
-> 写到输出目录
```

该脚本目前没有读取 Dataset501 三模态影像，没有读取 availability，没有实例化 `SRRProposeRefineMyoPS`，没有加载原型/记忆库，没有加载 checkpoint，也没有执行完整体积或滑窗前向。`--checkpoint` 只是命令门；非恒等模式仍复制 nnU-Net 标签。

因此，当前不能直接进入正式训练。即使产生训练后 checkpoint，现有推理入口也不会使用它。

## 下一步：Batch 3A

Batch 3A 必须先建立真实 MyoPS 模型推理：

```text
Dataset501 [LGE,T2,C0] + availability
-> raw OOF anchor manifest
-> frozen fold0-train prototype/memory
-> schema v2 checkpoint
-> SRRProposeRefineMyoPS
-> full-volume or deterministic sliding-window forward
-> geometry-preserving NIfTI
-> unified evaluator
```

硬门：

- 三种模式调用同一个模型对象；
- `anchor_identity_control` 经过模型前向并恢复 raw OOF anchor；
- checkpoint、原型和记忆必须实际加载并核对哈希；
- 训练查询排除自身分片，验证/推理查询使用全部冻结训练分片；
- raw anchor 与安全上下文分离；
- 评价器不允许 SRR 目录回退到恒等目录；
- 每个 known-bad 进入真实 validator；
- 建立 `tests/srr_production/test_myops_batch2_preflight.py`。

Batch 3A 不授权训练。

## Batch 3A 状态

```text
commit: pending_batch3a_commit
status: SRR_MODEL_IN_LOOP_UNTRAINED_DIAGNOSTIC
```

Batch 3A 已在 `main` 建立真实 MyoPS 模型在环推理入口：

1. `scripts/srr_production/infer_myops.py` 读取真实 Dataset501 `[LGE,T2,C0]` 与 availability。
2. 三种模式 `anchor_identity_control`、`srr_no_anchor_control`、`anchor_bounded_srr_correction` 均实例化并调用同一个 `SRRProposeRefineMyoPS` 类。
3. checkpoint 通过 schema v2 实际加载；无训练后 checkpoint 时只生成/加载零步诊断 checkpoint，并将状态写为 `SRR_MODEL_IN_LOOP_UNTRAINED_DIAGNOSTIC`。
4. fold0 训练来源 prototype/memory 进入 checkpoint state dict；推理恢复后 `prototype_memory_actual_load_count=1`。
5. 训练 memory query policy 为 `training_crossfit_exclude_query_shard`，验证/推理为 `validation_inference_all_train_shards`。
6. raw OOF anchor 与 no-T2 safety context 已在模型接口分离；identity 模式模型前向后逐体素恢复 raw OOF anchor。
7. `evaluate_myops_fair.py` 的 SRR 比较禁止 identity 目录回退；`--srr-pred-dir` 必须配套 `--srr-contract` 并核对 prediction hashes。

主要证据：

```text
results/srr_production/inference/batch3a_anchor_identity_control_inference_contract.json
results/srr_production/inference/batch3a_srr_no_anchor_control_inference_contract.json
results/srr_production/inference/batch3a_anchor_bounded_srr_correction_inference_contract.json
results/srr_production/evaluation/batch2_completion.json
tests/srr_production/test_myops_batch2_preflight.py
```

Batch 3A 没有训练、没有 Slurm、没有 validation upload、没有 hosted metric claim、没有性能结论。由于 checkpoint 为零步诊断，正式训练仍需用户另行授权。

## 后续：Batch 3B

Batch 3A 已完成诊断门；下一步进入真实 4D Cine 主干：

```text
Dataset502 real 4D Cine
-> time-axis audit
-> ED/reference frame
-> real frame-pair registration and warping
-> frame-wise anatomy
-> warp to ED space
-> temporal aggregation
-> ED-space export and evaluation
```

历史 B7/B8 继续禁止正式使用。CineMA 若使用，必须实际加载官方权重并进入下游输出；单独特征探针不算接通。

## 权威边界

```text
controller_authorized_now: 0
formal_training_authorized_now: false
slurm_authorized_now: false
validation_upload_authorized: false
hosted_metric_claim_authorized: false
route_promotion_authorized: false
m11_authorized: false
final_scientific_decision_authorized: false
```
