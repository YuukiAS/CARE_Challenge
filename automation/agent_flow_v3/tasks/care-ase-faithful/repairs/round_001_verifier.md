# CARE-ASE 第 1 轮 Verifier 返修

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
production_verifier_thread_id: 019fd7c1-2d99-74b2-8c95-68ed129613e8
```

恢复上述精确 Verifier 线程。不得新建替代角色，不得使用 `--last`，不得修改模型、训练、推理、配置或 Executor 证据生成代码。

## 本轮目标

现有 Verifier 已能重算部分文件哈希并检查部分源码拓扑，但仍主要相信 Executor 写出的运行收据。必须把关键判定升级为 Verifier 自己执行、自己观察、自己生成证据，确保伪造的 PASS 字段、随机输入、重复调用和失效代码路径无法通过。

## 必须完成的修复

### 1. 独立执行精确集成版本

新增 Verifier-owned 执行入口，绑定当前或后续精确集成提交，并至少独立执行：

- 模型构建和 stock checkpoint parity；
- 真实 train-only Dataset501 forward/backward；
- 完整 `care_ase_loss`；
- T2-present 与 no-T2 混合批；
- 每个 required module 的 final-logit intervention；
- schema-v4 checkpoint save/load/next-step continuity；
- deployment loader；
- evaluator interface；
- 单 tile 与真正强制多 tile 的 full-volume inference。

Verifier 生成的命令、标准输出、标准错误和结果文件必须绑定：nonce、冻结合同、集成 SHA、实现指纹、Verifier 指纹、Python、运行资产 SHA 和病例/划分 SHA。

### 2. 拒绝伪造的运行收据

必须使以下当前实现形式确定失败：

- 用 `torch.randn` 构造输入，却在收据中填入真实 case ID；
- 输入尺寸等于 patch size，并以完全相同参数调用两次，却声称完成 single-versus-forced-multi-tile；
- `global_bias_application_count`、tile count 或 PASS 状态直接写常量；
- deployment probe 未调用 deployment loader；
- evaluator probe 未调用 evaluator；
- 每个 loss denominator 都被替换为常数 1；
- checkpoint probe 只注入人工梯度，而不复现 canonical next batch/total loss step；
- fold0 实现使用 fold1 hard-negative manifest，却没有跨 fold OOF 合法性证明。

### 3. 修复并执行 step0 parity 验证

当前 `CAREASE.step0_parity_report` 仍引用已经不存在的：

```text
component_heads.edema_extent_presence
component_heads.edema_extent_area
```

Verifier 必须新增导入并执行该报告的回归测试。测试不能捕获后忽略 `AttributeError`。还必须对真实 T2-present 和 no-T2 train-only 病例验证：

- stock-compatible logits 最大误差不超过 `1e-6`；
- compatible argmax changed voxels 为 0；
- no-T2 行所有当前 edema-owned 模块调用数为 0；
- class 4 不进入 no-T2 竞争。

### 4. 把 protected known-bad 升级为执行级变异

至少为以下类别加入真实源码、monkeypatch 或运行行为变异，而不是只翻转 JSON 字段：

- extent head 被 Conv3d/occupancy alias 代替；
- dilation residual addition 被删除；
- injury initialization 改为随机；
- required projection 或 context 不再影响 final logits；
- no-T2 仍调用 edema-owned module；
- single/multi-tile 实际为同一次调用；
- global bias 在 tile 内多次应用；
- deployment loader 重开 stock checkpoint 或依赖未声明路径；
- evaluator 的病例、TTA、decode 或 metric population 不一致；
- checkpoint reload 后 next descriptor、scheduler、RNG、sampler cursor 或下一步参数不同；
-真实 artifact 字节与收据 SHA 不一致。

每个关键类别至少有一个执行级变异被真实运行并返回非零。

### 5. 精确事务门

Verifier 必须拒绝：

- Planner packet、CI receipt、runtime manifest 或 CURRENT 不是同一个精确集成 SHA；
- hosted CI 不存在或只属于前一轮；
- review round、nonce、实现指纹或 Verifier 指纹过期；
-新关键提交后继续复用旧 Planner 结论。

## 必须提交的证据

- 更新后的验证器与测试；
- executable verifier receipt；
- runtime mutation manifest；
-每项关键 mutation 的命令、退出码和输出哈希；
-新的 `verifier_fingerprint.json`；
-新的 `verifier_freeze_receipt.json`；
-完整本地测试结果。

## 禁止事项

- 不得编辑 `src/**`、训练/推理实现、Executor 收据或冻结合同；
- 不得通过增加更多布尔字段、源码字符串 token 或 64 位占位哈希满足要求；
- 不得训练、访问 outer、构建或上传 Docker、合并 develop 到 main；
- 不得自行宣布 Planner PASS。

完成后提交到 Verifier 本地分支，返回精确 role commit，由 Controller 机械检查作用域并先行集成。