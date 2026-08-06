# CARE-ASE 第 1 轮 Executor 返修

## 精确绑定

```text
task_id: care-ase-faithful
request_nonce: care-ase-20260806T090955Z
review_round: 1
planner_review_commit: 38dbbb0e32556e5f12127699c67ff31d45e5e934
reviewed_integration_commit: 885d5db3089e109136e52c9cbde4d349a62c9092
frozen_contract_sha256: a4758fd3125cdfaac4cf044fd4fa948472558cca231c0429a26e63e5d7d1e11d
reviewed_implementation_fingerprint_sha256: b0db561e7a40c0e52c8363b8b43e96bc2441184a7ce28bc17681d41bededa1a1
reviewed_verifier_fingerprint_sha256: 5c5dd6f431f2cb0c1d2fe6a7927f3679eea47b8ec7c82e4f2a4227e8ab2c7773
production_executor_thread_id: 019fd7c1-8358-7632-9022-367e62ecfbd1
```

必须等待 Controller 先集成并冻结本轮新的 Verifier 指纹，然后恢复上述精确 Executor 线程。不得新建替代角色，不得使用 `--last`，不得修改测试、验证器、冻结合同或 protected fixtures。

## 已确认关闭的源码问题

以下源码拓扑修复已经成立，必须保持：

- scar/edema 各自拥有独立 `SliceExtentHead`；
- extent head 使用 Conv1d、GroupNorm、SiLU 和独立 presence/area 输出；
- scar extent 不再复用 occupancy；
- dilation 1/2/4 均有真实 residual addition；
- injury classifier 来自 stock class-4/class-5 行均值。

本轮不得回退这些修复。

## 必须完成的修复

### 1. 修复并真实运行 step0 parity

`CAREASE.step0_parity_report` 仍引用不存在的：

```text
component_heads.edema_extent_presence
component_heads.edema_extent_area
```

改为当前真实模块，例如 `component_heads.edema_extent_head`，并确保所有 edema-owned 模块均被完整计数。随后在实际 train-only T2-present 和 no-T2 病例上运行，证明：

- stock trunk/class row parity 最大误差不超过 `1e-6`；
- compatible argmax changed voxels 为 0；
- no-T2 行 edema-owned 调用为 0；
- no-T2 class 4 从最终竞争中排除。

### 2. 重写 full-volume inference probe

当前 probe 使用 `torch.randn`，输入尺寸与 patch size 相同，而且两次调用参数完全一致。这不构成真实病例或强制多 tile 证据。

必须：

- 加载一个真实 train-only 预处理完整病例；
-绑定 case ID、split、数组、几何、availability 和预处理网格 SHA；
- 单 tile 运行使用覆盖完整体积的 patch；
- forced multi-tile 运行使用至少一个维度严格小于体积的 patch，并观察 tile count 大于 1；
-通过 hook/counter 真实记录 tile base-logit 调用数和 post-aggregation global bias 调用数；
- global bias 必须只在聚合后执行一次；
-比较最终 logits 和 decode，使用冻结容差；
-实际运行 T2-present 与 no-T2 两种语义；
-不得用 synthetic logits 替代模型输出证明 class 4/5 decode。

### 3. 导出真实 loss 组成与资格分母

当前 `_loss_terms_from_metrics` 将所有 denominator 写成 1，并把 `conditional_final_dice_ce` 映射到总 loss。必须修改 canonical loss/runtime 输出，使每个冻结 loss term 直接返回：

-未加权值；
-权重；
-加权贡献；
- eligible row count；
- eligible voxel/count denominator；
-是否正确排除及排除原因；
-是否进入总 loss。

这些值必须来自实际 `care_ase_loss` 计算，不能由 evidence builder 二次猜测。混合批中 no-T2 行不得进入任何 edema term 的分母或监督。

### 4. 真实 checkpoint/resume next-step probe

不得只给单个参数注入人工梯度。必须：

- 使用 canonical train-only batch descriptor、target construction 和完整 total loss；
-执行一个零信用控制步骤；
-保存 schema-v4 checkpoint；
-从 checkpoint 恢复模型、optimizer、scheduler、AMP/precision状态、RNG、sampler cursor、batch descriptor cursor 和 extent ramp step；
-在 uninterrupted 与 reload 两边执行相同的下一 canonical batch/total-loss backward/update；
-比较下一 descriptor、loss、梯度、参数、optimizer、scheduler、RNG 和 cursor；
-所有临时更新不得写入正式训练 checkpoint，也不得计入训练。

### 5. 真实 deployment loader probe

当前 `run_deployment_load_probe` 只是返回常量 PASS。必须实际：

-创建临时可迁移部署目录；
-复制或声明合同允许的最小 tracked assets；
-调用 `load_care_ase_checkpoint_for_inference`；
-在加载开始前移除或阻断原 stock checkpoint 和仓库私有路径访问；
-执行一次真实 inference；
-记录打开的文件清单或受控文件访问审计；
-证明没有重开 stock checkpoint、未声明 host path 或旧 wrapper。

### 6. 真实 evaluator smoke

当前 evaluator probe 只是返回 metric 名称和 PASS。必须调用实际 evaluator，对一个小型 train-only CARE/baseline prediction pair：

-使用完全相同病例集合；
-相同 TTA；
-相同 decode；
-相同 label/metric population；
-实际计算并返回合同要求的 metric keys；
-记录被调用模块、输入 prediction SHA 和结果 SHA；
-故意改变 population/TTA/decode 时应由 Verifier fixture 拒绝。

### 7. 修复 hard-negative fold 与 OOF 绑定

当前候选代码只寻找 `hard_negative_manifest_fold1.json`，但实现和 probe 使用 fold0。必须：

-优先使用当前 fold 对应的 canonical OOF manifest；
-绑定 case ID、source train split、source validation fold、prediction artifact、actual checkpoint SHA、grid SHA、mask SHA 和 coordinate descriptor SHA；
-证明该病例未用于训练 source checkpoint；
-若确需跨 fold 证据，必须显式证明 OOF 合法性，不能只复用 fold1 文件名；
- requested/resolved category 和 fallback 必须真实记录。

### 8. 重新生成全部证据

所有 PASS 字段必须从上述真实执行结果派生。重新生成：

- source manifest；
- architecture signature；
- parameter owner registry；
- forward/backward receipt；
- inference receipt；
- step0 parity receipt；
- checkpoint/resume receipt；
- deployment receipt；
- evaluator receipt；
- hard-negative receipt；
- implementation evidence；
- implementation fingerprint。

必须绑定新的 Verifier fingerprint、精确 Executor commit、nonce 和冻结合同。

## 必须通过的回归证据

- Verifier-owned tests 和 executable mutations 全部通过；
-真实病例 forward/backward 的每个 required projection 第一轮梯度非零有限；
-临时 projection 更新后 adapter/gate/dilation/context 上游梯度非零有限；
- no-T2 行 edema call、supervision、denominator和gradient均为0；
-真正 forced multi-tile 的 tile count 大于1且global bias只执行一次；
-step0 parity 报告可执行且无 stale attribute；
- deployment/evaluator/checkpoint probes 实际调用目标代码；
-same-fold OOF hard-negative绑定完整；
-没有正式训练、outer、Docker/upload或main合并。

## 禁止事项

- 不得修改或削弱 `tests/**`、`validators/**`、Verifier fingerprint、protected fixtures 或冻结合同；
-不得用随机张量冒充真实 case；
-不得用常量 PASS、占位哈希、人工 denominator 或人工梯度冒充执行证据；
-不得启动 14,000-step 正式训练；
-不得访问 outer、部署/上传、发送组织方邮件或合并 develop 到 main。

完成后提交到 Executor 本地分支，返回精确 role commit 和实现指纹，由 Controller 在 Verifier commit 之后集成。