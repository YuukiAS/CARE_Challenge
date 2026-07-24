# CARE 架构 Wiki

architecture_version: `care-srr-cascade-submission-rescue-planned`
latest_verified_runtime: `Batch10 fair rescue terminal packet; no new rescue runtime yet`
latest_scientific_status: `CARE-MMRD direct route stopped; user-authorized anchor-bounded pathology-specific rescue ready for Controller`
latest_controller_task: `20260724_care_myops_srr_cascade_submission_rescue`
route_status: `MAIN_ONLY_SRR_CASCADE_SUBMISSION_RESCUE_READY`

本页是 GPT、Controller、Executor、Mapper 和 Planner 读取当前架构状态的根入口。当前代码仍以 Batch10 终态为最近已验证实现；新的目标架构尚未由 Controller 实现。下一步不是继续 CARE-MMRD，也不是恢复旧 SRR 全链，而是以现有 nnU-Net 为最终安全底座，分别训练 scar 与 edema 的窄纠错模块，并让任何未通过独立审计的病种自动回退基线。

## 当前判断

```text
Batch10 CARE-MMRD: 终止，保留为历史公平负结果
新主线: CARE-SRR-Cascade submission rescue
开发位置: /users/a/e/aereinh/CARE, main
旧 Route A/B/C: 历史证据，不恢复
validation/Docker upload: 未授权
```

当前任务入口：

```text
results/srr_production/code_maturity/srr_cascade_submission_rescue_planner_decision_20260724.md
configs/care_mm/srr_cascade_submission_rescue.yaml
prompts/tasks/20260724_care_myops_srr_cascade_submission_rescue_controller.md
prompts/tasks/20260724_care_myops_srr_cascade_submission_rescue_executor_plan.yaml
results/20260724_care_myops_srr_cascade_submission_rescue/
```

## 为什么不再做直接六类替换

Batch10 已修复滑窗推理、checkpoint-plans 恢复、正式 inverse preprocessing 和同评价基线比较。最佳非 nnU-Net 候选仍在 audit 上低于基线，scar 的主要问题是边界和远端假阳性，edema 则已有接近基线的完整三模态信号。继续让一个共享网络重新生成 anatomy、scar 和 edema，风险大于剩余时间内的潜在收益。

新任务保留 Batch10 有价值的 frozen feature/evidence，同时恢复 SRR-v3 的安全原则：强基线拥有最终输出权，创新模块只在有证据时做病种特异、有界的局部修改。

## 目标数据流

```text
[LGE,T2,C0] + availability
-> frozen five-fold OOF nnU-Net logits/probabilities
-> frozen CARE-MMRD full-view feature/anatomy/edema evidence
-> frozen CARE-MMRD scar margin evidence
-> clean four-shard cross-fitted pathology prototype similarity
-> soft myocardium-union, uncertainty, physical distance support
-> scar control / scar SRR correction
-> edema-zone control / edema SRR-zone correction
-> bounded pathology-channel composition
-> per-pathology calibration selection
-> frozen audit retain-or-fallback decision
```

目标类：

```text
src/care_myocardium/models/care_srr_cascade_rescue.py
CARESRRCascadeRescue
```

固定最终语义：

```text
background, myocardium, LV, RV logits: exact anchor
scar: anchor + support * 2*tanh(delta_scar)
edema: anchor + T2_presence * support * 2*tanh(delta_edema)
no-T2 edema: exact anchor
```

## 冻结 source 与 prototype

新头不重新训练 source backbone。规划绑定两个已有 checkpoint，但 Wave0 必须重新核验路径、SHA256 和 clean-checkout load：

```text
teacher full-view epoch50 e92521fc...: features, anatomy, edema evidence
reliable-distill epoch25 36672249...: scar final-margin evidence
```

Prototype evidence 是新的一方窄实现，不得调用旧 `ProposalDictionary` 或旧 BR2/SIP production path。训练病例只能查询其他 shard；验证和推理只查询全部训练 shard。Edema 安全负样本必须来自 T2-present 可靠标注病例，no-T2 myocardium 不能成为 edema negative。

## 训练前硬门

正式 Slurm 前必须通过：

```text
anchor identity <=1e-6
channels 0-3 exact identity
no-T2 edema exact identity
source parameter/normalization freeze
shared spatial transform across image, label, anchor, source, prototype, distance maps
200-step scar and edema fixed overfit, loss decrease >=30%, zero formal credit
single-loss backward reaches declared outputs
prototype on/off and bank-swap change final output
checkpoint roundtrip <=1e-6
real known-bad fixtures fail closed
```

任何 gate 失败都由 Controller 在同一范围内退回 Executor 修复；不能提交训练后再解释。

## 正式运行与评价

固定两个 seed：`20260724`、`20260725`。每个 seed job 内按顺序运行四个 matched variants，每组 6250 optimizer steps。Calibration 只用于 checkpoint 和病种候选冻结；audit 只用于最终 retain/fallback。

评价必须同时报告：Dice、官方 exact HD、HD95、precision/recall、remote FP、component、volume ratio、help/harm、empty prediction、changed voxels、CenterB/CenterC、no-T2 safety。Positive-GT 与 all-case-empty-safe 指标分开，selection 与 deployment 必须使用同一 composed-logit argmax。

## 病种独立 fallback

每个病种只能选择：

```text
USE_SRR_CASCADE
USE_CASCADE_CONTROL
FALLBACK_TO_NNUNET
```

一个病种失败不允许拖垮另一个，也不允许通过平均值掩盖。至少一个 custom 病种通过 audit，才允许本地构建 submission-ready package。否则终态是 baseline-only，不得包装成 custom success。

## Cine 与提交边界

本任务不训练 Cine。只有 MyoPS 至少一个 custom 病种通过，才允许把现有 Dataset502 nnU-Net 五折链作为固定 Cine 来源做本地 package/Docker dry-run。必须检查 15+15 病例、官方标签值、几何、目录结构、两次确定性 hash 和无 GT 访问。

本地构建不等于上传。Validation upload、Docker upload 和 hosted 成绩声明仍需用户明确授权。

## 当前图与后续 Mapper 责任

现有 `wiki/figures/` 仍描述 Batch10 已验证实现，不代表目标模型已落地。任务设置 `diagram_update_required: true`；实现完成后 Mapper 必须更新：

```text
wiki/MODEL.md
wiki/EXECUTION.md
wiki/COMPONENTS.csv
wiki/LINEAGE.md
wiki/architecture.yaml
wiki/current_state.yaml
wiki/figures/
```

未实现前不得把目标架构写成“已验证”。

## 入口

- [MODEL.md](MODEL.md)
- [EXECUTION.md](EXECUTION.md)
- [COMPONENTS.csv](COMPONENTS.csv)
- [LINEAGE.md](LINEAGE.md)
- [architecture.yaml](architecture.yaml)
- [current_state.yaml](current_state.yaml)
- [history/README.md](history/README.md)
