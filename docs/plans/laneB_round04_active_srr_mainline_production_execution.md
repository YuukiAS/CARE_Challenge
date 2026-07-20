# CARE SRR 五天主线生产化计划

Plan metadata:
- Type: mainline production recovery plan
- Lane: historical Route B merged into main; single active SRR mainline
- Round scope: Round04 recovery label only; this document does not open Round05
- Status: active
- Parent roadmap: `docs/plans/`
- Parent plan: `prompts/routes/portfolio_round04_route_B_planner_plan_20260719.md`
- Function: 在五天截止窗口内，把当前声明式/合成式 Route B 实现重构为真实、可训练、可推理、可公平比较和可部署的 SRR-MyoPS/Cine 系统
- Do not: 今天不得正式训练、不得提交 Slurm、不得上传 validation、不得创建新 round、不得恢复 Route A/C、不得用 controller token 或 packet PASS 替代真实代码与真实指标
- Rule exception: 用户于 2026-07-20 明确决定只保留 Route B 科学主线，把已审阅 Route B 代码和证据合并进入 `main` 直接开发，并暂停旧 route portfolio、critic/controller/reviewer 周期。文件名保留 `laneB_round04` 仅用于兼容 `docs/plans` registry，不表示继续旧 Round04 执行图。

## 1. 当前判断

当前 `main` 已包含 Route B Round04 controller packet、独立 reviewer audit 和合并提交 `078c3548645b14224b997e41995520ec865d4b62`。该 reviewer 只确认了作业终态、packet 完整性和 validator 可运行，没有确认模型科学有效。Round04 的 B3-B6 formal 路径仍包含随机张量、手工目标、固定公式 proxy、阶段间重新初始化和非真实病例评价；B8 也使用合成 frame pair。因此旧 packet 只能作为“失败的工程证据与反例”，不能继续作为生产训练入口。

未来五天不再使用以下组织方式：

```text
planner -> critic -> controller -> B3/B4/B5/B6 分阶段训练 -> reviewer -> 下一轮
```

改为：

```text
一个 main 分支
一个写入主线的 integrator
多个只读 GPT/Codex 审计线程
若干可独立验收的代码补全批次
一个 MyoPS 生产训练入口
一个 Cine 生产训练/推理入口
一套 Route/nnU-Net 共用评价器
代码冻结后才开始真实训练
```

今天只补代码、做静态检查、真实病例 forward/backward 单步检查、真实 prediction/evaluator 检查和 save/reload；不运行持续 optimizer loop，不提交 Slurm。

## 2. 从 SRR-v2、SRR-v2.5、SRR-v3 恢复的不可删除结构

本计划已视觉核对当前 ChatGPT Project 材料中的 SRR-v2、SRR-v2.5、SRR-v3。主线目标保持为：在部分观测的 LGE/C0/T2 条件下，从共享、模态私有和交互表示中选择可靠证据；使用解剖先验生成 scar/edema 病灶 proposal；通过 pathology-specific soft ROI refiner 形成最终病灶；使用强 nnU-Net 作为 anchor/context/safety source，并用有界 SRR correction 保护已经正确的区域。

必须保留：

1. 输入顺序 `[LGE,T2,C0]` 与显式 availability；缺失模态不得伪装成可用零图像。
2. 四尺度编码与 shared/private/interaction retrieval。
3. availability + spatial/pathology-conditioned router，而不是只有全局模态组合查表。
4. anatomy union/LV/RV 预测和距离/不确定性先验。
5. 真实 train/OOF scar/edema positive/negative prototype provenance。
6. no-T2 样本不参与 edema positive loss、edema negative、edema proposal/refiner correction。
7. scar/edema 分开的 proposal、soft ROI、refiner 和指标。
8. bounded residual correction；SRR 关闭时必须精确恢复 nnU-Net。
9. Cine 使用真实多帧、ED/reference、真实 anatomy features、真实 registration/control 和 temporal aggregation。
10. Dice、HD、HD95、component、remote FP 和 volume 均由 prediction 与 GT 重新计算。

可以在五天内删减的只有治理和重复工程：旧 round wrapper、旧 token、重复 packet、重复模型入口、learned registration 作为生产必需依赖。不得删减上述科学数据流。

## 3. 唯一生产代码边界

后续代码应收束到以下一方入口；旧 Round03/Round04/M8/M9/M10 脚本只能作为历史来源或测试反例，不再拥有 formal authority。

### 3.1 生产包

```text
src/care_myocardium/srr_production/
  data.py
  anchor.py
  model.py
  routing.py
  prototypes.py
  losses.py
  checkpoint.py
  inference.py
  evaluation.py
  cine.py
```

允许复用和修复已有：

```text
src/care_myocardium/models/srr_propref.py
src/care_myocardium/models/srr_spatial_dictionary.py
src/care_myocardium/models/srr_dictionary_memory.py
src/care_myocardium/models/pathology_heads.py
src/care_myocardium/cine/*
```

但生产入口不得同时存在两套互不一致的同名模型。Integrator 必须明确哪些旧模块被直接复用、哪些被替换、哪些只保留为 legacy。

### 3.2 生产命令

```text
scripts/srr_production/audit_legacy_paths.py
scripts/srr_production/build_myops_oof_prototypes.py
scripts/srr_production/train_myops.py
scripts/srr_production/infer_myops.py
scripts/srr_production/evaluate_myops_fair.py
scripts/srr_production/infer_cine.py
scripts/srr_production/validate_code_maturity.py
```

今天必须至少把接口、真实数据流和 fail-closed 验证写全；正式训练命令可以存在，但今天不得执行正式训练。

### 3.3 配置

```text
configs/srr_production/entrypoints.yaml
configs/srr_production/myops.yaml
configs/srr_production/cine.yaml
configs/srr_production/evaluation.yaml
```

`entrypoints.yaml` 是唯一 formal authority，列明 production model、train、infer、evaluation、export 和 Docker 入口。任何旧 wrapper 不在该文件中就没有正式资格。

## 4. 今天必须完成的代码生产化目标

今天结束时，必须达到“代码可进入真实训练前审计”，不是“模型已经训练好”。具体包括：

### 4.1 清除假实现

在所有 formal/production 路径中禁止：

- `torch.randn`、`np.random` 生成训练或评价影像；
- 手工 cube/sphere target；
- `torch.roll` 合成 Cine pair；
- 固定公式填写 Dice/AUC/HD/component；
- seeded deterministic prototype 进入 formal inference；
- 只读取上游 token、不加载上游 checkpoint；
- 每阶段重新初始化模型后声称连续训练；
- CSV/JSON 中的指标被 validator 直接相信而不重算。

静态扫描应区分 tests/fixtures 与 production；测试可以构造 synthetic known-bad，生产代码不可以。

### 4.2 真实 MyoPS 数据闭环

Dataset/DataLoader 必须从 manifest 读取真实 LGE/T2/C0、GT、spacing、affine、center 和 availability，明确：

- LGE-only；
- LGE+C0；
- LGE+C0+T2；
- edema supervision availability；
- compact/raw label 双向映射；
- 与 nnU-Net Dataset501 相同 fold split。

单个真实 batch 必须能完成 forward、finite loss、backward、目标模块非零梯度和 checkpoint save/reload，但今天不得持续优化。

### 4.3 nnU-Net anchor 与恒等保护

实现真实 nnU-Net fold checkpoint/logit adapter。必须支持：

```text
SRR disabled -> final logits/prediction exactly equal to nnU-Net
SRR enabled  -> final = anchor + bounded scar correction + bounded edema correction
```

测试必须覆盖：

- SRR-off voxel identity；
- max logit delta；
- raw label identity；
- no-T2 edema correction exact zero；
- scar/edema gate zero initialization；
- checkpoint reload identity。

### 4.4 真实 prototype/negative-space

正式 prototype 不得来自 deterministic axis 或 random tensor。必须实现：

- fold-safe train/OOF feature extraction；
- four-shard provenance；
- source case IDs、feature/checkpoint/config hash；
- current case exclusion；
- validation/test exclusion；
- scar positive/safe-negative；
- edema positive/T2-present safe-negative；
- no-T2 myocardium 禁止进入 edema negative；
- memory -> similarity -> proposal -> refiner -> final logits 可追踪。

今天只要求 builder、loader、hash/provenance 与真实小样本抽取 smoke 可运行；不要求跑全量 OOF fitting。

### 4.5 真实统一模型和 loss

一个模型对象必须同时拥有 representation、anatomy、proposal、refiner 和 final correction，不再把 B3/B4/B5/B6 当四个互相独立模型。

Loss 必须明确分类：

```text
real optimized loss
monitor-only metric
control-only term
```

不得保留 alias loss 冒充 Pattern-SIP、memory 或 refinement。至少写通：

- anatomy DiceCE；
- scar proposal/refiner；
- T2-present edema proposal/refiner；
- negative-space/hard-negative；
- soft anatomy/ROI prior；
- bounded residual/gate；
- dictionary/load balance/Pattern-SIP 的真实 forward dependency。

每项都需要单项关闭测试，确认关闭前后 loss、gradient 或 final logits 确实变化。

### 4.6 公平评价闭环

Route SRR 与 nnU-Net 必须共用同一个 prediction-based evaluator。主比较是相同 fold0 的 44 cases，不是 Route local proxy 对 nnU-Net 5-fold mean。

固定：

- 同一 GT 与 case list；
- classes 4/5；
- 相同 compact/raw label map；
- 相同 nearest-neighbor resampling；
- 相同 spacing；
- 相同 empty-GT 规则；
- raw vs raw；
- 若使用 postprocess，则相同 postprocess vs 相同 postprocess；
- Dice、HD、HD95、component count、small FP、remote FP、volume ratio；
- T2-present、no-T2、CenterB、CenterC、scar-positive 子组。

Evaluator 必须读取 NIfTI prediction 与 GT 重新计算，不允许接收训练脚本自报分数作为真值。

### 4.7 Cine 真实路径

Cine 今日代码目标是把真实 4D case、ED/reference、关键帧选择、CineMA anatomy/features/uncertainty、registration interface、temporal aggregation 和 official export 写通。

生产环境不得依赖当前缺失的 shell ANTs executable 才能启动。应支持一个可 Docker 化的真实 classical registration 后端作为生产默认；ANTs/SyN 作为离线 control。任何 fallback 必须真实 warp，不得复制输入、合成 pair 或只写 receipt。

## 5. 多 GPT/Codex 参与方式

不再让多个写入线程同时修改 `main`。角色改为：

- **Integrator**：唯一有权在 `main` 写代码、合并和提交。
- **模型审计 GPT**：只读当前 main，逐文件检查 SRR architecture、checkpoint continuity、prototype、loss、gradient 和 legacy bypass。
- **数据/评价审计 GPT**：只读检查 Dataset501 split、label、empty-GT、NIfTI evaluator、baseline identity、公平比较。
- **Cine 审计 GPT**：只读检查真实 4D input、CineMA、registration、temporal、export 和 Docker dependency。
- **红队 GPT**：只读寻找能绕过 validator 的路径，给出具体文件/函数/复现命令。

所有审计必须绑定当前 commit SHA，不写泛泛意见。Integrator 修复后直接进入下一批，不重新走 planner/critic/controller/reviewer。

## 6. 每次代码补全必须怎样报告

每个代码批次都必须同步更新：

```text
docs/plans/laneB_round04_active_srr_change_review_ledger.md
```

报告必须包含：

1. base/head commit；
2. 本次目标；
3. 修改、删除、停用的文件；
4. 修改前真实行为；
5. 修改后真实数据流；
6. 明确删除了哪些 synthetic/proxy/bypass；
7. 运行的精确命令和 exit code；
8. 真实输入/输出路径；
9. 未解决项；
10. 下一批允许修改什么；
11. 人类可直接理解的“这次改动对最终模型意味着什么”。

禁止只写“tests pass”“validator pass”“implemented”。必须说明具体 tensor、checkpoint、prediction 和 metric 来源。

## 7. 五天时间表

### Day 0：今天——只补代码，不训练

完成 companion TODO 中全部 P0/P1 项：真实数据、anchor、统一模型、prototype builder、loss、checkpoint、inference、fair evaluator、Cine real path、anti-bypass tests。允许真实病例单次 forward/backward 和 evaluator inference；禁止正式 optimizer loop 与 Slurm。

### Day 1：代码成熟度与小规模真实性验证

上午完成多 GPT 只读审计和修复；随后运行真实 4-8 case micro-overfit、44-case baseline identity 和 nnU-Net fold0 metric reproduction。只有这些通过后才冻结 production entrypoints。这里仍不是 leaderboard 结论。

### Day 2：一次真实 fold0 训练与同分割评价

用完整 production pipeline 进行一次 fold0 训练。评价必须生成真实 NIfTI 和完整 Dice/HD/HD95/component/remote-FP 表。若失败，先判断是代码/优化错误还是科学不足；允许同一实现内修复确定性 defect，不创建新 round。

### Day 3：固定架构后的 folds 与 Cine

冻结架构后并行运行剩余 MyoPS folds 和 Cine production path。不得再新增模型模块，只允许运行时、显存、I/O 和确定性 bug 修复。

### Day 4：OOF 校准、五折 ensemble、Docker dry-run

基于 OOF 固定全局 scar/edema correction scale、threshold 和 component rule。不得按验证病例 GT 单独选择 gate。完成 raw/postprocessed 对称比较、五折 ensemble 和 Docker inference。

### Day 5：最终冻结、paper、package

只处理最终 inference、Docker、表格、图、论文和 submission QA。不得新增架构或 loss。任何 validation upload 仍需用户单独明确授权。

## 8. 训练前不可绕过的实质条件

以下条件不是 token，而是执行事实；任一不满足，今天不得训练：

- production formal path 静态扫描无 synthetic science；
- 真实 Dataset/DataLoader 能覆盖三种 modality pattern；
- SRR-off 精确恢复 nnU-Net；
- 下游真实加载 parent checkpoint；
- prototype 有真实 source/provenance；
- no-T2 edema loss/correction exact zero；
- one model end-to-end forward 含 retrieval->proposal->refiner->final；
- prediction NIfTI 能被统一 evaluator 读取；
- nnU-Net fold0 指标可由同一 evaluator 重现；
- raw/postprocess 比较对称；
- Cine 使用真实 frame 和真实 warp；
- 故意插入 synthetic input、hard-coded metric、random prototype、wrong split、broken checkpoint 时测试非零退出；
- change ledger 完整解释所有代码变化。

## 9. 成功标准

今天的成功不是 Dice 上升，而是：以后任何训练都会真正训练完整 SRR，并且结果能与 nnU-Net 公平比较；任何 GPT/Codex 都无法再通过填表、token、随机数据或旧 wrapper 获得“PASS”。

五天最终成功是：完整 SRR 在真实五折/OOF 与 Cine 路径上形成可 Docker 化候选，具备冲榜资格。不能在训练前承诺榜一，但必须确保 baseline 不被无条件破坏、SRR correction 可被独立量化、所有指标来自真实 prediction。
