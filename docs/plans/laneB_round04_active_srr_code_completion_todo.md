# CARE SRR 今日代码补全 TODO

Plan metadata:
- Type: executable code-completion TODO
- Lane: historical Route B merged into main; single active SRR mainline
- Round scope: Round04 recovery label only; no Round05
- Status: active for 2026-07-20
- Parent roadmap: `docs/plans/`
- Parent plan: `docs/plans/laneB_round04_active_srr_mainline_production_execution.md`
- Function: 指导 Codex 在今天内完成 SRR 生产代码闭环；每个批次可单独开 plan/goal 执行，但全部写入 `main`，由单一 integrator 顺序提交
- Do not: 今天不得正式训练、不得提交 Slurm、不得上传、不得建立新 controller/critic/reviewer handoff、不得只修文档或 validator、不得以 proxy/packet/token 宣称代码完成
- Rule exception: 用户明确要求暂停旧 portfolio/route 流程，直接在 `main` 完成唯一 SRR 主线。

## 使用方法

1. 每次只执行一个批次，或执行明确列出的无冲突组合。
2. 开始前记录当前 `origin/main` SHA；结束时提交到 `main`。
3. 每个批次必须更新 `docs/plans/laneB_round04_active_srr_change_review_ledger.md`。
4. 不能把未完成项标成完成；使用 `[ ]`、`[x]` 和 `BLOCKED:`。
5. 所有“完成”都必须给出代码路径、真实输入路径、真实输出路径、测试命令和 exit code。
6. 今天允许单次真实 forward/backward、真实 inference、metric reproduction 和 save/reload；禁止持续 optimizer loop、正式 fold training 和 Slurm。

## P0：开始任何代码前必须完成

### C0. 主线与 legacy 权限清理

- [ ] 确认 `main` 包含 `078c3548645b14224b997e41995520ec865d4b62` 及本计划。
- [ ] 新建 `configs/srr_production/entrypoints.yaml`，列出唯一 production model/train/infer/evaluate/export/Cine 入口。
- [ ] 新建 `scripts/srr_production/audit_legacy_paths.py`。
- [ ] 扫描所有 `jobs/route_B_round04/`、`scripts/training/route_B_round04/`、M8/M9/M10 wrapper，分类为：`production_reused`、`legacy_reference`、`known_bad_fixture`、`forbidden_formal_entrypoint`。
- [ ] formal entrypoint 调用旧 Round04 synthetic script 时必须失败。
- [ ] 明确保留已有真实组件，不复制第二套同义模型。

必须输出：

```text
results/srr_production/code_maturity/legacy_path_inventory.csv
results/srr_production/code_maturity/formal_entrypoint_audit.json
```

验收重点：不是“旧文件删除了多少”，而是以后正式命令无法再误调用旧 synthetic 路径。

### C1. Production 静态 anti-synthetic 扫描

- [ ] 扫描 production/config/job/train/infer/evaluate 路径中的 `torch.randn`、`randn_like`、`np.random`、手工 cube/sphere target、`torch.roll` synthetic pair、固定 Dice/AUC/HD 常数。
- [ ] tests/fixtures 可以保留 synthetic known-bad，但必须在 allowlist 中。
- [ ] 所有 production synthetic fallback 必须删除或改成直接报错。
- [ ] 测试故意把旧 B6/B8 设为 formal entrypoint，validator 必须非零退出。

必须输出：

```text
results/srr_production/code_maturity/synthetic_science_scan.json
```

## P0：真实 MyoPS 数据与 anchor

### C2. 真实 MyoPS Dataset/DataLoader

建议目标文件：

```text
src/care_myocardium/srr_production/data.py
configs/srr_production/myops.yaml
```

- [ ] 从 frozen manifest 和 Dataset501 split 读取真实病例。
- [ ] 输入顺序固定 `[LGE,T2,C0]`。
- [ ] 缺失模态以 availability 控制计算图；不得把零填充本身当“模态可用”。
- [ ] 返回 image、label、availability、edema_label_available、center、case_id、spacing、affine、source paths。
- [ ] 明确 compact labels 0-5 与 raw labels 0/200/500/600/1220/2221。
- [ ] 支持 full-volume inference 与 patch training 两种读取方式。
- [ ] 用真实 LGE-only、LGE+C0、LGE+C0+T2 各一个病例做读取测试。
- [ ] 对缺文件、shape mismatch、affine mismatch、unknown label 直接失败。

必须输出：

```text
results/srr_production/code_maturity/real_data_case_receipts.json
results/srr_production/code_maturity/modality_pattern_roundtrip.csv
```

### C3. 真实 nnU-Net anchor adapter

建议目标文件：

```text
src/care_myocardium/srr_production/anchor.py
```

- [ ] 读取现有 Dataset501 nnU-Net fold checkpoint 或可复现 logits/prediction。
- [ ] 记录 checkpoint SHA256、plans、trainer、fold、preprocessing、split。
- [ ] 提供 logits/probabilities/hard prediction/anatomy context/uncertainty。
- [ ] 不允许随机 anchor。
- [ ] `srr_enabled=false` 时直接返回 anchor prediction。
- [ ] zero-initialize scar/edema correction gate。
- [ ] 在一个真实病例上证明 SRR-off raw label 与 anchor 相同。
- [ ] 在 44-case fold0 上准备 baseline identity 命令；今天可以执行 inference/evaluation，但不得训练。

必须输出：

```text
results/srr_production/code_maturity/anchor_provenance.json
results/srr_production/code_maturity/baseline_identity_receipt.json
```

## P0：统一完整 SRR 模型

### C4. 单一 production model

建议目标文件：

```text
src/care_myocardium/srr_production/model.py
src/care_myocardium/srr_production/routing.py
```

- [ ] 复用/修复已有 `SRRProposeRefineMyoPS`、spatial dictionary、pathology heads，而不是重写缩水版。
- [ ] 一个 model object 同时包含 stems、四尺度 encoder、router、dictionary、anatomy、prototypes、proposal、soft ROI、refiner、bounded correction。
- [ ] 四尺度 channel 与 shared/private/interaction slot 结构写入 config 和 runtime receipt。
- [ ] router 同时读取 availability、局部特征、anatomy/proposal/context，不得只有 global pooled gate。
- [ ] missing private/interaction slot 在逐 batch/task/slot 上严格 masked。
- [ ] scar 与 edema 使用独立 routed features、proposal 和 refiner。
- [ ] no-T2 时 edema proposal、ROI、refiner delta、final correction exact zero。
- [ ] final logits 使用真实 nnU-Net anchor + bounded SRR correction。
- [ ] SRR correction 关闭时精确恢复 baseline；打开时真实改变 final logits。
- [ ] 删除 Round04 `RouteBRound03MyoPS()` 每阶段重新初始化模式的 production 权限。

必须输出：

```text
results/srr_production/code_maturity/model_tensor_contract.json
results/srr_production/code_maturity/router_invalid_slot_receipt.csv
results/srr_production/code_maturity/final_correction_intervention.json
```

### C5. Anatomy/soft ROI/refiner 真实数据流

- [ ] anatomy target 为 union/LV/RV，明确 pathology 替代 myocardium label 的处理。
- [ ] anatomy logits 真正进入 proposal 和 soft ROI。
- [ ] scar 使用小 ROI、高精度、LGE-oriented refinement。
- [ ] edema 使用大 ROI、T2-conditioned、context-preserving refinement。
- [ ] ROI 不能 hard delete 所有低分区域；保留软 gate 和 bounded residual。
- [ ] 对 `proposal_off`、`scar_refiner_off`、`edema_refiner_off`、`both_on` 实现真实 forward toggle。
- [ ] 同一真实 batch 上 toggle 必须改变正确的 tensor/final logits，不允许只改 summary。

## P0：prototype、negative-space 与 loss

### C6. 真实 OOF prototype builder

建议目标文件：

```text
src/care_myocardium/srr_production/prototypes.py
scripts/srr_production/build_myops_oof_prototypes.py
```

- [ ] formal bank 不得使用 `deterministic_axis_prototypes` 或 random tensor。
- [ ] 从真实 train feature 抽取 scar positive、scar safe-negative、edema positive、edema T2-present safe-negative。
- [ ] four-shard split 与当前 case exclusion。
- [ ] validation/test label 不得进入。
- [ ] no-T2 myocardium 不得成为 edema negative。
- [ ] 保存 source case IDs、checkpoint/config/preprocess/feature hash。
- [ ] builder 可在 2-4 个真实病例上 smoke；今天不跑全量 fitting。
- [ ] model load 时 source/hash 不完整直接失败。
- [ ] 证明 bank similarity 真实进入 proposal logits。

必须输出：

```text
results/srr_production/code_maturity/prototype_small_real_smoke.json
results/srr_production/code_maturity/prototype_leakage_known_bad.json
```

### C7. Loss 与梯度闭环

建议目标文件：

```text
src/care_myocardium/srr_production/losses.py
```

- [ ] anatomy DiceCE。
- [ ] scar proposal/refiner loss。
- [ ] edema proposal/refiner loss 只在 T2-present 且 edema label available 时启用。
- [ ] negative-space/hard-negative loss，edema 仅使用 safe negatives。
- [ ] soft anatomy prior/ROI regularization。
- [ ] bounded residual/gate loss。
- [ ] dictionary sparsity/coverage/load balance。
- [ ] Pattern-SIP 必须使用 forward router usage 分组量，并参与 loss；不得仅写 post-hoc CSV。
- [ ] 所有 loss 分类为 `optimized`、`monitor_only` 或 `control_only`。
- [ ] 禁止 alias loss 与 placeholder zero loss 冒充实现。
- [ ] 一个真实 batch 完成 finite loss 和 backward；检查梯度到 stems/router/dictionary/anatomy/proposal/refiner/gate。
- [ ] no-T2 batch 的 edema-owned gradient exact zero。

必须输出：

```text
results/srr_production/code_maturity/loss_contract.csv
results/srr_production/code_maturity/real_batch_gradient_receipt.csv
```

### C8. 连续 checkpoint 与 resume

建议目标文件：

```text
src/care_myocardium/srr_production/checkpoint.py
```

- [ ] 一个 checkpoint 保存完整模型、optimizer、scheduler、AMP、prototype provenance、config、split、global step、best metric state。
- [ ] parent checkpoint SHA256 和 source commit 必须记录。
- [ ] reload 后同输入输出一致。
- [ ] 禁止只验证“上游 completion token 存在”。
- [ ] 禁止 B3/B4/B5/B6 每阶段重新初始化。
- [ ] resume 不重置 step、prototype 或 calibration state。

## P0：公平评价和真实 inference

### C9. 统一 MyoPS inference/export

建议目标文件：

```text
src/care_myocardium/srr_production/inference.py
scripts/srr_production/infer_myops.py
```

- [ ] 真实 full-volume inference。
- [ ] 输出 compact NIfTI 和 raw-label NIfTI。
- [ ] 保持 spacing/origin/direction/affine。
- [ ] 输出 prediction manifest，含 model/checkpoint/config/case/source hash。
- [ ] 同时支持 anchor-only、SRR-off、SRR-on。
- [ ] raw/postprocess 分开保存；不得覆盖。
- [ ] inference 不允许读取 GT、case-specific threshold 或 post-hoc Dice。

### C10. Route/nnU-Net 共用公平 evaluator

建议目标文件：

```text
src/care_myocardium/srr_production/evaluation.py
scripts/srr_production/evaluate_myops_fair.py
configs/srr_production/evaluation.yaml
```

- [ ] 底层复用同一个 prediction-based metric implementation。
- [ ] fold0 同一 44 cases 为首个正式比较。
- [ ] classes 4/5。
- [ ] 相同 nearest-neighbor resampling、spacing、label map、empty-GT。
- [ ] raw vs raw；相同 postprocess vs 相同 postprocess。
- [ ] Dice、HD、HD95、component count、small FP、remote FP、volume ratio。
- [ ] 输出 per-case、aggregate、T2-present、no-T2、CenterB、CenterC、scar-positive。
- [ ] 重新计算 nnU-Net fold0，目标重现 edema `0.3944358977`、scar `0.5601692281`，容差预先固定。
- [ ] 5-fold mean 只作背景，不冒充 same-split。
- [ ] evaluator 忽略训练脚本自报 metric CSV。
- [ ] 修改 summary CSV 数字不应改变重算结果；known-bad 必须验证这一点。

必须输出：

```text
results/srr_production/code_maturity/nnunet_fold0_reproduction.json
results/srr_production/code_maturity/fair_evaluation_contract.json
```

## P1：Cine 真实生产路径

### C11. Cine 真实 4D 数据和 anatomy source

建议目标文件：

```text
src/care_myocardium/srr_production/cine.py
scripts/srr_production/infer_cine.py
configs/srr_production/cine.yaml
```

- [ ] 读取真实 4D cine，明确时间轴、ED/reference 和关键帧。
- [ ] official CineMA weight/code/license/SHA provenance。
- [ ] official model logits、features、uncertainty 真正进入 downstream，不是独立 probe。
- [ ] matched-random 仅作为未来 control，不阻塞今天 production dataflow。
- [ ] label/export 语义与 challenge Cine scar 指标一致。

### C12. 可 Docker 化 registration 与 temporal aggregation

- [ ] 生产默认 registration 使用仓库环境可安装、Docker 可带入的真实 backend。
- [ ] ANTs/SyN 为离线 control，不作为 production 必需 executable。
- [ ] 禁止 synthetic pair、copy input、identity receipt 冒充 warp。
- [ ] 保存 transform、registered frames、failure matrix。
- [ ] temporal module 消费 registered anatomy/features/uncertainty/motion/position/valid mask。
- [ ] frame0 control 与 temporal output 使用同一病例和 evaluator。
- [ ] export 为真实 ED-space prediction。

## P1：防绕过、测试和可解释提交

### C13. Production maturity validator

建议目标文件：

```text
scripts/srr_production/validate_code_maturity.py
tests/srr_production/
```

必须 fail 的 known-bad：

- [ ] production entrypoint 指向旧 Round04 B6/B8。
- [ ] formal path 包含 synthetic data。
- [ ] metric 来自硬编码 summary。
- [ ] prediction NIfTI 缺失。
- [ ] wrong split/case list。
- [ ] empty-GT 规则不一致。
- [ ] postprocessed Route 对 raw nnU-Net。
- [ ] random/deterministic prototype 进入 formal bank。
- [ ] checkpoint parent/hash 断裂。
- [ ] no-T2 edema loss/correction 非零。
- [ ] invalid slot weight 非零。
- [ ] official CineMA 未进入 downstream。
- [ ] Cine registration 未真实执行。
- [ ] old wrapper 绕过 production entrypoints。

注意：validator 不是主要完成依据；它只是确保最常见绕过会失败。最终仍需人类/GPT 读 code diff 和 ledger。

### C14. 每批提交的人类可读解释

每个 commit 必须在 change ledger 中回答：

```text
本次到底改了什么？
修改前为什么是假/不完整？
修改后真实数据从哪里来、流到哪里？
哪些旧入口被停用？
哪些组件现在仍然没写好？
测试为什么足以证明这次改动，而不是证明模型性能？
下一步具体修改哪些文件？
```

## 今天结束时的人工检查顺序

1. 阅读 `entrypoints.yaml`，确认只有一套 production path。
2. 阅读 change ledger，逐 commit 检查真实变化。
3. 搜索 production path 是否仍有 synthetic science。
4. 从真实 manifest 跟到 Dataset/DataLoader。
5. 从真实 nnU-Net checkpoint/logits 跟到 final bounded correction。
6. 从真实 feature 跟到 prototype/proposal/refiner/final logits。
7. 从 prediction NIfTI 跟到统一 evaluator。
8. 检查 no-T2 edema 全链路。
9. 检查 Cine 真实 frame/warp/temporal/export。
10. 运行 red-team known-bad。

今天完成后仍然保持：

```text
formal_training_authorized: false
slurm_authorized: false
validation_upload_authorized: false
```

明天只有在代码、真实数据流、公平 evaluator 和 change ledger 全部可读且无关键缺口后，才讨论真实训练。
