---
review_id: CARE_ASE_R2_EXTERNAL_GPT_TRAINING_READINESS_20260803
reviewed_implementation_commit_sha: e21a410d39e7d7e7c65ae566a62f13b0e06399fa
reviewed_review_request_commit_sha: 5f20bdef2a62edfed147821018ee33b24d1560fd
decision: CODE_REVIEW_REVISE
formal_training_authorized: false
formal_training_started_by_review: false
outer_access_fold1: 0
outer_access_fold4: 0
review_scope: source_contract_formal_entrypoint_checkpoint_sampler_target_and_gpu_smoke
next_action: REPAIR_CURRENT_IMPLEMENTATION_THEN_RETURN_TO_EXTERNAL_GPT
---

# CARE-ASE R2 外部训练就绪审阅

## 结论

当前版本**不能启动 fold1 / fold4 的正式 14,000-step 训练**。这不是要求再设计模型，也不是要求增加新组件；阻断原因是当前正式训练入口、合同绑定、checkpoint、no-T2 parity、extent padding、target 语义、sampler 与 GPU smoke 仍存在可直接影响训练正确性或导致训练中途失败的实现缺口。

当前代码已经保留了若干关键修复：共享 low/mid decoder 单次前向、anatomy/scar/edema 三条高分辨率路径、单输出 pathology classifier、named evidence projections、非零 modality adapters、零初始化 residual projections、no-T2 edema 子图按样本排除、stock initial-patch augmentation、full-case target cache 基础结构与 schema v3。这些内容不得回退。

但 `code_review_request.json` 中的 `remaining_known_code_blocker_count: 0` 与实际源码和 receipt 不一致，因此该请求不能作为训练许可。

## P0：启动正式训练前必须关闭

### 1. Formal checkpoint 必然因缺失 effective-contract provenance 失败

正式入口调用 `save_care_ase_checkpoint(...)` 时没有传入 `effective_contract_sha256`。`save_care_ase_checkpoint` 在 `formal_resumable=true` 时又明确拒绝 `effective_contract_sha256=UNSET`。

因此，正式 chunk 即使前向和反向能运行，也会在第一次 checkpoint 保存时失败。当前保存频率为每 1,000 步或 chunk 末尾；对于 2,000-step chunk，可能先浪费约 1,000 步训练后才暴露问题。

同时，`prompts/blueprints/CARE_ASE_R2_effective_contract_v6_20260803.yaml` 在 commit `e21a410...` 中被删除，而 `code_review_request.json` 仍声明一个 effective-contract SHA。当前 main 上不存在可重新计算和核验的 v6 contract 文件。

必须满足：

- current main 存在唯一有效的 CARE-ASE effective contract；
- formal permit 重新计算该文件 SHA；
- formal entrypoint 把同一 SHA 写入 checkpoint；
- checkpoint load/resume 重新计算并逐项比较；
- 不允许仅在 request JSON 中记录一个已删除文件的旧 SHA。

### 2. External permit 没有核验 effective contract

`verify_external_review_permit()` 只要求 permit 中出现 `effective_contract_sha256` 字段，但没有读取当前 contract、重新计算 SHA，也没有比较 permit 值与当前文件值。当前 critical-source manifest 也不包含 effective contract。

结果是：即使 permit 中填写任意非空 contract SHA，formal entrypoint 仍可能通过 permit 检查。

### 3. Cross-fold resume 仍未 fail closed

`_load_previous()` 只加载 checkpoint 并拒绝少数 invalidated source SHA；正式入口没有核验：

- `payload.fold == --fold`；
- `model.config.fold == --fold`；
- stock checkpoint 是否属于请求 fold；
- resume checkpoint 的 split、actual-train case list、manifest、contract 与当前 fold 是否一致。

因此 fold1 入口仍可能加载 fold4 checkpoint，再配 fold1 sampler 和 fold1日志继续运行。

### 4. Formal optimizer-step 不是唯一完整正式数据管线

`run_formal_optimizer_step()` 接收的是已经构造好的 `microbatches`。Sampler、eligible-pool draw、coordinate draw、case loading、initial patch、stock augmentation、full-case target build 和 RNG 消费均发生在函数外。

这不满足“formal training、GPU probe、atomic checkpoint、exact resume 使用同一个完整函数”的要求，也允许测试或 resume oracle 使用预构造 batch，而正式训练走另一条路径。

此外，该函数仍缺少：

- 每个 micro loss 的 finite 检查；
- 所有 trainable gradient 的 finite 检查；
- `clip_grad_norm_(..., error_if_nonfinite=True)`；
- optimizer 更新后参数与 Adam state 的 finite 检查；
- non-finite 时禁止保存 checkpoint 的明确失败路径。

当前实现会无条件执行 `optimizer.step()`，NaN/Inf 可以污染参数和 optimizer state。

### 5. GPU smoke 自身记录 augmentation RNG 未推进，却仍标记 PASS

fold1 与 fold4 的 `gpu_code_smoke_*.json` 都记录：

```text
augmentation_rng_advanced: false
status: PASS
```

这直接违反 exact-resume 所要求的 augmentation RNG 消费与恢复。更严重的是，两个 receipt 把 no-T2 图排除写为：

```text
covered_by_tests/care_ase/test_no_t2_five_class_step0_parity.py
```

但当前仓库中不存在该测试文件。由此可见 smoke PASS 不能支持“所有 required behavior 已真实覆盖”的结论。

### 6. no-T2 step-0 parity 仍使用错误比较语义

`CAREASE.step0_parity_report()` 仍把 stock class-4 logit乘以 availability 后参与六类拼接和 argmax。对于 no-T2，CARE-ASE class-4 被置为约 `-1e4`，stock class-4 被置为 `0`；两者既不是同一 logit，也没有按要求共同 decode `[0,1,2,3,5]`。

正确门必须分别验证：

- anatomy logits 0–3；
- scar class-5 logit；
- CARE-ASE 与 stock 均排除 class 4 后的五类 decoded labels；
- no-T2 edema-owned module call count 为 0。

### 7. Extent bias 仍会读取 padding / invalid 区域

`compute_slice_extent_statistics()` 虽增加了 valid mask，但 all-invalid slice 的 fallback 路径会在 `fallback_max` 非有限时退回 `value.amax(...)`，重新把无效像素引入统计。

同时，模型 `_extent_bias()` 调用该函数时没有传入 `valid_spatial_mask`，模型 forward 也没有接收该 mask。因此从 step > 500 起，训练的 final competition / dense pathology logits 和单窗口 padded inference 仍可能受到 padding 区域的 extent prediction 影响。

必须保证：

- all-invalid slice 的 presence、area、bias、loss 和 gradient 全为 0；
- padding 不进入 weighted mean、masked max 或 fallback；
- training forward 与 inference 均显式消费同一 valid mask 语义。

### 8. Full-edema degenerate boundary 的旧错误分支仍存在

`_edema_boundary_numpy()` 对 `edema.all()` 仍返回：

```text
target = 1
raw_distance = 0
valid = 1
```

这与 frozen requirement 冲突。若无法由 full-case context 观察到外部边界，应为 `target=0, raw=0, valid=0`；若能观察到真实边界，应使用 full-case boundary map，而不是 patch 边框。

### 9. Hard-negative OOF grid proof 仍是自证式绑定

`read_prediction_from_anchor()` 对 validation probability artifact 无条件设置：

```text
preprocessed_grid_binding = true
preprocessed_shape = probability array shape
```

随后 `probability_npz_exact` 又用这些由当前函数自行写入的字段证明 array 已在 preprocessed grid。原 anchor entry 本身没有 per-case preprocessed geometry proof，也没有 per-case checkpoint SHA。

当 shape 不同时，代码仅按 spacing 和 target shape 调用 nnU-Net resampler，没有完整验证 orientation、transpose、crop bbox、round-trip landmarks 或 array equality。该路径不能被称为严格 preprocessed-grid proof。

另外，per-case `source_checkpoint_sha256` 仍来自 fold-level `checkpoints[source_fold].checkpoint_final_*`，而不是 probability entry 对实际生成 checkpoint 的直接绑定。当前 anchor entry 只记录 source fold 和 prediction/probability artifact，不证明该 artifact 一定由 checkpoint_final 产生。

### 10. Sampler eligible pool 与 resolved fallback 仍不完整

`_eligible_cases()` 只对 OOF 类别和 scar small-component 做了明显的 case eligibility 过滤；edema positive、edema boundary 等类别仍可从整个 group 抽病例。

当 requested OOF/small pool 为空时，函数回退到全 group；如果 manifest 对所抽病例没有对应坐标，descriptor 仍可能保留原 `within_focus` / requested category，而不是明确改变为实际 fallback category。

这会使采样统计声称执行 OOF FN、safe FP、positive 或 boundary，实际中心却来自 GT component、remote background 或普通 wall。

### 11. Lock heartbeat 和 step-level ownership 未实现

正式 lock owner 仍缺少 `SLURM_STEP_ID`，训练循环没有每 300 秒更新 heartbeat。Live-owner 判断只检查 allocation job ID，而不是具体 `srun` step。Stale recovery 使用普通 `shutil.move` 后重新建目录，没有原子 recovery-claim/race-loser 机制。

该问题可能导致：

- 具体训练 step 已死但 allocation 仍活时锁永不恢复；
- 两个恢复进程同时争抢；
- chunk 被重复训练或错误覆盖。

## P1：在发出正式训练许可前需要一并闭合

### 12. Full-case target cache provenance 只是 recipe hash，不是实际数据 manifest

正式 checkpoint 写入的 `full_case_target_*_manifest_sha256` 仅 hash：builder 名称、case IDs 和 spacing source。它没有绑定每病例 segmentation SHA、properties SHA、cache array SHA、shape、spacing 和 schema。

当前 cache 还是进程内 LRU 动态构造，不是 frozen per-case manifest。代码或数据变化后，相同 recipe hash 仍可能对应不同 target arrays。

### 13. 空间 scale 后的物理距离 target 值没有重新标定

代码先在 full-case grid 计算 signed distances / boundary distances，再把这些连续值当普通 regression maps 经过 stock rotation/scale。几何缩放后，距离场数值本身应随 scale 变化；单纯插值旧值不能保持以毫米为单位的 target 语义。

至少需要固定并验证：在 stock scale transform 后，signed-distance、boundary-distance 和 wall-depth target 与变换后 segmentation / effective spacing 一致。

### 14. Formal evidence 仍写入共享 preflight result root

`RESULT_DIR` 固定为：

```text
results/20260803_care_ase_r2_final_code_blocker_closure
```

正式入口把 augmentation binding、parameter coverage 和 reload summary 写到该共享目录，而 checkpoint/runtime 又写到 source-SHA-specific formal root。这样 smoke、preflight 和未来 formal evidence 仍可能互相覆盖或混用。

### 15. CURRENT / Wiki 没有反映当前 candidate

最新 `CURRENT.md` 仍把 CARE-ASE 主状态写成 v5、implementation `f4ecd...`、review packet `51b9...`。它没有记录 `e21a...` / `5f20...`，也没有记录当前外部 `CODE_REVIEW_REVISE`。

这意味着机器真值与当前源码、request packet 不一致。任何 formal Controller 在启动前必须先以新的、真实存在的 contract 和 review decision 更新 CURRENT；不得继续沿用 v5 状态。

## 对当前 PASS 证据的判断

以下证据不能被删除，但必须标为被本次外部审阅取代：

- `code_review_request.json` 中 `remaining_known_code_blocker_count: 0`；
- `g1_static_implementation_gate_receipt.json` 的 `remaining_gap_count: 0`；
- fold1/fold4 GPU smoke 的 `status: PASS`。

原因不是 smoke 没有任何价值，而是它们没有覆盖上述 formal checkpoint、contract、cross-fold resume、no-T2 parity、augmentation RNG、extent padding、boundary、strict OOF provenance 和 lock 语义。

## 训练许可边界

本审阅不要求再增加新模型模块、新 loss 或重新设计 CARE-ASE。下一次返回外部 GPT 时，只需证明上述 P0/P1 已在当前 main 的真实 formal entrypoint 中关闭。

在此之前：

```text
formal_training_authorized: false
fold1_14000_step_started: false
fold4_14000_step_started: false
outer_access_fold1: 0
outer_access_fold4: 0
```

不得生成 formal training goal，不得签发 external PASS permit，不得启动 W3。
