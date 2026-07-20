# CARE SRR 今日代码补全 TODO

Plan metadata:
- Type: executable code-completion TODO
- Lane: historical Route B merged into main; single active SRR mainline
- Round scope: post-Round04 main-only sprint; no Round05
- Status: active for 2026-07-20
- Parent roadmap: `docs/plans/`
- Parent plan: `docs/plans/laneB_round04_active_srr_mainline_production_execution.md`
- Authoritative correction: `docs/plans/laneB_round04_active_srr_plan_correction_addendum.md`
- Function: 顺序收束现有 SRR 实现，禁止复制缩水版；今天只补代码和真实评价闭环，不训练
- Do not: 不得从零另写第二套 SRR 模型，不得提交 Slurm，不得正式训练，不得以文件存在、测试数量、validator PASS 或 token 代替代码事实
- Rule exception: 用户明确暂停旧 route/controller 周期，直接在 `main` 完成唯一 SRR 主线。

## 0. 使用规则

1. 当前唯一写入者是 main integrator；其他 GPT/Codex 线程只读 exact SHA。
2. 每次只执行一个 Batch，完成后 commit/push，并追加 change ledger。
3. 不得跳过 Batch 0 直接重写模型或训练。
4. 默认修复现有代码：

```text
src/care_myocardium/models/srr_propref.py
src/care_myocardium/models/srr_spatial_dictionary.py
src/care_myocardium/models/srr_dictionary_memory.py
src/care_myocardium/models/srr_v2_unet.py
src/care_myocardium/models/pathology_heads.py
scripts/training/run_srr_propref_myops_fold0.py
scripts/evaluation/evaluate_predictions.py
```

5. `src/care_myocardium/srr_production/` 若新增，只能是薄 adapter/config/checkpoint/inference facade；不得复制 encoder/router/dictionary/proposal/refiner。
6. 今天允许真实病例 load、单次 forward/backward、save/reload、真实 inference/evaluation；禁止持续 optimizer loop 和 Slurm。

## Batch 0：当前实现真相 + formal authority 收束【现在立即执行】

### 0A. 当前调用图

- [ ] 记录当前 `origin/main` SHA、工作树状态和未推送提交；不干净时先提交/push或明确远端可能过时。
- [ ] 从真实数据入口追踪到 Dataset/DataLoader、model、loss、checkpoint、inference、evaluator。
- [ ] 列出全部 `SRRProposeRefineMyoPS` variant。
- [ ] 对每个 variant 记录：encoder profile、dictionary config、spatial dictionary、Pattern-SIP、memory、anchor role、`final_logits` 公式、是否可能成为 formal entrypoint。
- [ ] 明确 M6 residual/arbitration、M9 pure SRR、M10 pure proposal-refinement 和 baseline-preserving gate 的冲突关系。

### 0B. Anchor/prototype/loss/checkpoint 真相

- [ ] 追踪 nnU-Net anchor 的实际来源：真实 checkpoint/logits、cached prediction、random、placeholder 或 missing passthrough。
- [ ] 追踪 prototype 的生成、保存、加载和 proposal similarity；标出 deterministic-axis/random formal 路径。
- [ ] 追踪 `SafePrototypeMemoryBank` 是否进入真实训练/proposal。
- [ ] 追踪 Pattern-SIP、dictionary、memory、proposal、refiner、bounded correction loss 是否真实参与 forward/backward，还是 alias/monitor-only。
- [ ] 追踪 B3/B4/B5/B6 checkpoint 是否连续加载，还是每阶段重新初始化。
- [ ] 追踪所有 metric 的真实来源，标记 hard-coded/proxy/self-reported 与 prediction-derived。

### 0C. Cine 真相

- [ ] 追踪真实 4D Cine、ED/reference、CineMA weights/features/logits/uncertainty、registration、temporal aggregation 和 export。
- [ ] 标出 synthetic pair、copy/identity warp、独立 probe 未进入 downstream、missing ANTs executable 等路径。

### 0D. 立即关闭 formal 绕过

- [ ] 新建 `configs/srr_production/entrypoints.yaml`，只指向审计后选中的现有 canonical 代码。
- [ ] 新建 `scripts/srr_production/audit_formal_entrypoints.py`。
- [ ] 将旧 Round04 B3-B8 synthetic/proxy scripts 分类为 `forbidden_formal_entrypoint`。
- [ ] formal entrypoint 指向旧 B6/B8 时必须非零退出。
- [ ] 禁止新增第二套模型主体。

### Batch 0 必须提交

```text
results/srr_production/code_maturity/current_implementation_truth.md
results/srr_production/code_maturity/canonical_call_graph.json
results/srr_production/code_maturity/variant_final_output_matrix.csv
results/srr_production/code_maturity/anchor_prototype_loss_checkpoint_matrix.csv
results/srr_production/code_maturity/cine_call_graph.md
results/srr_production/code_maturity/legacy_path_inventory.csv
configs/srr_production/entrypoints.yaml
scripts/srr_production/audit_formal_entrypoints.py
tests/srr_production/test_formal_entrypoint_authority.py
docs/plans/laneB_round04_active_srr_change_review_ledger.md
```

Batch 0 不得声称完整模型已经修好。最终必须列出 Batch 1 的精确现有文件/函数修改清单。

## Batch 1：现有 MyoPS 主干原地修复

仅在 Batch 0 完成、用户/下一 GPT 能读懂 diff 后执行。

### 1A. 唯一 final-output 语义

- [ ] 生产候选固定为：真实 SRR 主干产生 scar/edema bounded correction，叠加 same-case nnU-Net anchor logits。
- [ ] `anchor_identity_control` 强制 correction 为 0，逐体素恢复 nnU-Net。
- [ ] `srr_no_anchor_control` 只作为诊断，不是默认候选。
- [ ] M9/M10 pure-SRR 分支不得继续作为隐式 production 默认。
- [ ] SRR 必须真实读取原始 LGE/T2/C0、retrieval、prototype、proposal、refiner；不能退化为只读 nnU-Net prediction 的后处理。

### 1B. 真实数据和 availability

- [ ] 使用 Dataset501 相同 fold/split/preprocessing。
- [ ] 支持 LGE-only、LGE+C0、LGE+C0+T2。
- [ ] 返回真实 GT、spacing、affine、center、availability、edema-label availability。
- [ ] missing modality private/interaction slot 严格 masked。
- [ ] no-T2 edema loss、prototype negative、proposal、ROI、refiner 和 correction exact zero。

### 1C. 真实 OOF prototype/memory

- [ ] formal bank 禁止 deterministic/random bootstrap。
- [ ] four-shard train/OOF provenance。
- [ ] current case 和 validation/test exclusion。
- [ ] scar/edema positive 与 safe-negative 分开。
- [ ] no-T2 不得进入 edema negative。
- [ ] `memory -> similarity -> proposal -> refiner -> final correction` 可追踪。

### 1D. Loss 与 checkpoint

- [ ] anatomy、scar proposal/refiner、T2-present edema proposal/refiner、negative-space、dictionary/load balance/Pattern-SIP、bounded correction 真实进入 backward。
- [ ] alias/zero placeholder 不得算完成。
- [ ] 一个 checkpoint 保存完整 model/optimizer/scheduler/AMP/prototype/config/split/global-step/parent SHA。
- [ ] reload 输出一致，resume 不重置。

### Batch 1 允许证据

真实病例单次 forward/backward、非零目标梯度、no-T2 exact zero、save/reload。不得持续训练。

## Batch 2：真实 inference + nnU-Net 公平评价

- [ ] full-volume NIfTI inference。
- [ ] anchor-only、SRR-off、SRR-on 同时支持。
- [ ] compact/raw label roundtrip，保持 geometry。
- [ ] 同一 fold0 44 cases、GT、label map、resampling、spacing、empty-GT。
- [ ] raw vs raw；相同 postprocess vs 相同 postprocess。
- [ ] Dice、HD、HD95、component、small FP、remote FP、volume ratio。
- [ ] T2-present、no-T2、CenterB、CenterC、scar-positive 子组。
- [ ] 重现 nnU-Net fold0 edema `0.3944358977`、scar `0.5601692281`，容差事先固定。
- [ ] evaluator 只信 prediction/GT，不信训练脚本 summary CSV。

## Batch 3：Cine 真实路径 + 全面红队

- [ ] 真实 4D Cine、ED/reference、关键帧。
- [ ] official CineMA weights/logits/features/uncertainty 真实进入 downstream。
- [ ] Docker 可用的真实 registration 生产后端；ANTs/SyN 可作为离线 control。
- [ ] temporal aggregation 消费 registered evidence。
- [ ] ED-space official export。
- [ ] known-bad 覆盖 synthetic input、hard-coded metric、wrong split、random prototype、broken checkpoint、no-T2 leakage、invalid slot、CineMA disconnected、fake warp、old wrapper bypass。

## 每批必须更新 change ledger

每个 commit 必须说明：

```text
base/head SHA
修改文件与函数
修改前实际行为
修改后真实数据流
关闭的 synthetic/proxy/bypass
运行命令和 exit code
真实输入/输出路径
关键 tensor/hash/delta
未解决项
下一批精确文件范围
```

禁止只写 `implemented`、`tests pass`、`validator pass` 或 completion token。

## 当前状态

```text
next_batch: Batch 0
formal_training_authorized_today: false
slurm_authorized_today: false
validation_upload_authorized: false
```
