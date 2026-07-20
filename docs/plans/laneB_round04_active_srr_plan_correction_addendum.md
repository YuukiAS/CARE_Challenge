# CARE SRR 主线计划修正补充

Plan metadata:
- Type: authoritative correction addendum
- Lane: historical Route B merged into main; single active SRR mainline
- Round scope: post-Round04 main-only sprint; no Round05
- Status: active and authoritative over conflicting sections of the parent plan/TODO
- Parent roadmap: `docs/plans/`
- Parent plan: `docs/plans/laneB_round04_active_srr_mainline_production_execution.md`
- Function: 修正“另建整套 production 包”和“今天一次完成全部 C0-C14”可能导致的重复实现、缩水实现和勾表式完成风险
- Do not: 不得从零复制一个新的 SRR 模型；不得先按计划文件名创建空模块再声称完成；不得今天训练或提交 Slurm
- Rule exception: 用户要求五天内直接在 `main` 收束现有实现，且要求每次代码变化可人工核对。

## 1. 为什么需要本修正

原五天计划的核心方向仍然正确：停止旧 route/controller 循环、今天不训练、清除 synthetic/proxy、建立真实数据闭环和公平 nnU-Net 比较。

但有两处必须收紧：

1. 原计划列出 `src/care_myocardium/srr_production/` 全套新文件，可能诱导 Codex 复制一个新的简化模型，绕开已经积累的 `SRRProposeRefineMyoPS`、`M10TwoPassSpatialDictionary`、prototype/memory、loss 和 evaluator 代码。
2. 原 TODO 要求今天完成 C0-C14，范围过大，可能再次出现“文件都创建、测试都通过，但真实主干没有被理解和修好”的勾表式完成。

因此，本补充覆盖父计划中“默认新建整套 production package”和“Day0 一次完成全部 C0-C14”的表述。

## 2. 正确原则：先收束现有实现，不默认重写

当前主干已经包含从 nnU-Net fallback 演化而来的多个真实组件。默认 source of truth 是现有代码，而不是新目录：

```text
src/care_myocardium/models/srr_propref.py
src/care_myocardium/models/srr_spatial_dictionary.py
src/care_myocardium/models/srr_dictionary_memory.py
src/care_myocardium/models/srr_v2_unet.py
src/care_myocardium/models/pathology_heads.py
scripts/training/run_srr_propref_myops_fold0.py
scripts/evaluation/evaluate_predictions.py
```

执行者必须先逐文件确认这些代码当前实际做什么，再决定：

- `reuse_as_is`
- `repair_in_place`
- `deauthorize_legacy_entrypoint`
- `delete_duplicate`
- `thin_production_facade_only`

除非审计证明现有模块无法安全修复，否则不得新写第二套 encoder/router/dictionary/proposal/refiner。

允许新增的 `srr_production` 代码默认只能是薄适配层：统一 config、entrypoint、checkpoint、inference 和 evaluator 调用；不能重新实现网络主体。

## 3. 最终模型语义必须收束

当前同一模型类里混有：

- legacy nnU-Net residual；
- M6 branch arbitration；
- M9 pure SRR-main；
- M10 pure proposal-refinement；
- baseline-preserving gate。

生产候选必须只保留一个明确语义：

```text
真实原始模态 SRR 主干
-> retrieval / anatomy / real prototype proposal / refiner
-> pathology-specific bounded correction
-> same-case nnU-Net anchor logits
-> final logits
```

nnU-Net 是稳定 segmentation basis 和 safety anchor；SRR 必须真实拥有原始模态输入、retrieval、proposal、refiner 和可量化 correction，因此不能退化为仅基于 nnU-Net prediction 的普通后处理。

必须保留两个控制模式，但不能让它们成为两套模型：

```text
anchor_identity_control: correction 强制为 0，精确恢复 nnU-Net
srr_no_anchor_control: 仅用于诊断 SRR 自身 lesion signal，不作为默认部署候选
```

M9/M10 的 pure-SRR final-output 分支不得继续作为未经明确选择的 production 默认路径。

## 4. 今天改为四个连续代码批次

今天不要求一个 Codex goal 同时完成全部代码。每批完成后，用户可以阅读 diff 和 change ledger，再继续下一批。

### Batch 0：当前实现真相与 canonical authority 收束

这是现在必须立刻执行的任务。

目标不是只写报告，而是“先读清楚，再立即关闭已确认的错误入口”。

必须完成：

1. 从当前 `origin/main` 建立完整调用图：真实 data -> model -> loss -> checkpoint -> inference -> evaluator。
2. 列出所有能实例化 `SRRProposeRefineMyoPS` 的 variant，以及每个 variant 的 `final_logits` 语义。
3. 追踪 nnU-Net anchor 的真实来源，确认哪些入口使用真实 checkpoint/logits，哪些使用 random/placeholder。
4. 追踪 prototype 从生成、保存、加载到 proposal similarity；确认哪些 formal path 仍使用 deterministic/random prototype。
5. 追踪 Pattern-SIP、memory、proposal、refiner loss 是否真正参与 backward。
6. 追踪 B3/B4/B5/B6 是否连续加载 checkpoint。
7. 追踪所有真实/伪 metric 入口。
8. 追踪 CineMA、registration 和 temporal 的真实调用图。
9. 建立唯一 `configs/srr_production/entrypoints.yaml`，但它必须指向审计后选定的现有代码路径。
10. 将已确认 synthetic Round04 scripts 标记为 `forbidden_formal_entrypoint`，production validator 遇到它们必须失败。
11. 不新增第二套模型主体，不训练，不提交 Slurm。

必须提交：

```text
results/srr_production/code_maturity/current_implementation_truth.md
results/srr_production/code_maturity/canonical_call_graph.json
results/srr_production/code_maturity/variant_final_output_matrix.csv
results/srr_production/code_maturity/legacy_path_inventory.csv
configs/srr_production/entrypoints.yaml
scripts/srr_production/audit_formal_entrypoints.py
tests/srr_production/test_formal_entrypoint_authority.py
```

同时更新 change ledger，明确哪些代码仍未修复。Batch 0 不能把“发现问题”写成“完整实现已完成”。

### Batch 1：现有 MyoPS 主干原地修复

只在 Batch 0 的调用图确认后执行。优先原地修改当前模型、训练脚本和数据层：

- 收束唯一 final-output 语义；
- 真实 nnU-Net anchor；
- 三种 modality pattern 的真实 loader；
- missing slot mask；
- real OOF prototype builder/loader；
-真实 Pattern-SIP/memory/loss gradient；
- one-model checkpoint/resume；
- no-T2 edema exact zero。

Batch 1 允许真实病例单次 forward/backward、save/reload，不允许持续训练。

### Batch 2：真实 inference 与公平 evaluator

- 真实 full-volume NIfTI prediction；
- anchor-only、SRR-off、SRR-on；
- nnU-Net 与 SRR 同一 fold0 44 cases；
- 同一 label、spacing、resampling、empty-GT 和 postprocess；
- Dice、HD、HD95、components、remote FP、volume；
- 重现 nnU-Net fold0 tracked metrics；
- metric 必须从 prediction/GT 重算。

### Batch 3：Cine 主干与全面红队

- 真实 4D Cine；
- official CineMA downstream；
- 真实 registration backend；
- temporal aggregation；
- export；
- synthetic、hard-coded metric、wrong split、random prototype、broken checkpoint 等 known-bad。

## 5. 多 GPT 的正确用法

不让多个 GPT 分别设计新架构。所有线程读取同一个 exact main SHA：

- Integrator：唯一写代码；
- Model truth auditor：检查 variant、forward、loss、prototype、checkpoint；
- Data/evaluation auditor：检查 split、labels、anchor、NIfTI、metrics；
- Cine auditor：检查 real frames、CineMA、registration、temporal；
- Red-team auditor：寻找可绕过 formal authority 的旧 wrapper。

审计结果必须落到 change ledger；Integrator 在同一主线修复，不返回 route planner/controller。

## 6. 现在的硬边界

今天禁止：

```text
formal training
optimizer loop used as scientific evidence
Slurm
fold expansion
validation upload
new architecture search
parallel writers to main
new duplicate SRR model package
```

今天允许：

```text
read/trace current code
repair current canonical code
real case load
one forward/backward step
checkpoint save/reload
real inference/evaluator reproduction
unit/integration/known-bad tests
commit/push with change ledger
```

## 7. 当前唯一下一步

立即执行 Batch 0。不要先运行 C2-C14，不要先写完整新模型，不要先训练。Batch 0 的产物和代码 diff 将决定 Batch 1 具体修改哪些现有文件。
