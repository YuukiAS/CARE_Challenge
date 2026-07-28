# CARE-DPR Pre-execution Architecture Amendment

本文件是 `20260728_care_dpr_fold0_global_redesign` 的最高优先级执行补充。它不改变任务目标、fold0 split、总训练预算、单一共享 encoder、双病理边界或唯一 allocation；它关闭当前蓝图中仍可能重复 CARE-DG 失败的三个结构缺口：仅靠错误图生成 ROI、proposal/refiner 联合训练的正样本饥饿、组件 utility 动作与监督定义不清。

优先级：

```text
本 amendment
> prompts/blueprints/CARE_DPR_dual_pathology_proposal_refine_arbitrate_20260728.md
> prompts/tasks/20260728_care_dpr_fold0_global_redesign_controller.md
> prompts/tasks/20260728_care_dpr_fold0_global_redesign_executor_plan.yaml
```

除本文件明确修改的字段外，原合同继续有效。

## 一、设计判断

CARE-DPR 不是“在 CARE-DG 后面只加一个 refiner”。正式结构必须是：

```text
一个共享 availability-aware CARE encoder
-> 每病种 direct coarse lesion proposal + FN/FP error proposal
-> anatomy-guided dense local refinement
-> full-volume candidate construction
-> component utility arbitration
-> bounded per-pathology write-back / exact fallback
```

Scar 与 edema-zone 使用结构同构、参数独立的分支。不得删减 edema 分支，也不得用 scar 指标或 composite mean 替代 edema-zone / pure-edema 证据。

## 二、每病种必须有三类输出，而不是只有 q_FN/q_FP

ScarBranch 与 EdemaZoneBranch 必须各自输出：

1. `p_coarse`：直接病灶范围 proposal，监督目标分别为 scar 与 edema-zone；
2. `q_fn` / `q_fp`：anchor 错误 proposal；
3. `p_refined`：在 soft ROI 内的完整局部病灶概率。

旧 CARE-DG 的 q_FN/q_FP 只允许初始化错误 proposal，不得承担唯一病灶 proposal。完全漏检病灶必须可以由 `p_coarse` 进入候选 ROI。

Soft ROI 固定为：

```text
ROI_k = support_k * soft_union(
  anchor_probability_k,
  p_coarse_k,
  q_fn_k,
  q_fp_k * anchor_probability_k,
  uncertainty
)
```

`q_fp` 只在 anchor pathology 邻域参与 ROI，禁止在全图制造删除候选。

Scar refinement 使用以组件为中心的 `8x96x96` 高分辨率上下文；edema-zone 使用 `8x128x128` 上下文。两者读取同一个共享 encoder feature pyramid，不得新增第二个 encoder/backbone。

## 三、训练必须使用 teacher-forced ROI curriculum，避免 proposal 饥饿

总预算仍为 4000 optimizer steps，不增加训练预算：

### Stage A1：proposal/refiner bootstrap，500 steps

- actual-train reliable cases；
- direct coarse proposal、q_FN/q_FP 正常训练；
- refiner ROI 中 `75%` 使用 actual-train GT/anchor-error 派生 teacher ROI，`25%` 使用模型预测 ROI；
- component utility 同时训练，但不得参与 checkpoint selection；
- encoder lr `2e-5`；proposal/refiner/utility lr `1e-4`。

### Stage A2：scheduled predicted-ROI training，2000 steps

- actual-train reliable cases；
- teacher ROI 比例从 `75%` 线性下降到 `0%`；
- 最后 500 steps 必须 predicted-ROI only；
- encoder lr `2e-5`；proposal/refiner/utility lr `1e-4`。

### Stage B：target-domain arbitration calibration，1500 steps

- complete-trimodal actual-train only；
- freeze modality stems、shared encoder、`p_coarse`、q_FN/q_FP；
- predicted-ROI only；
- 只训练 scar/edema refiners 与 component utility heads；
- lr `5e-5`。

Inner checkpoint/threshold evaluation 和 outer fold0 inference 必须始终 predicted-ROI only。Teacher ROI 只能来自 actual-train GT，不得用于 inner/outer 评价或推理。

## 四、全体积推理必须先聚合概率/特征，再形成组件

正式 inference 固定：

- sliding-window overlap `0.5`；
- Gaussian blending；
- 聚合 shared full-resolution feature、`p_coarse`、q_FN/q_FP、`p_refined`；
- 禁止平均 patch final labels；
- 禁止在 patch 内独立做 component accept/reject；
- 所有候选组件只在完整体积聚合后构建。

每病种候选分两类：

1. `ADD/FN candidate`：`p_refined` 或 `p_coarse/q_fn` 在 anchor pathology 外形成的连通组件；
2. `REVISE/FP candidate`：anchor pathology component 与 q_FP/低 utility evidence 相交形成的局部 replacement ROI。

重叠候选按同病种确定性合并。每个候选只有两种合法动作：

- `KEEP_ANCHOR_LOCAL_MASK`；
- `REPLACE_WITH_REFINED_LOCAL_MASK`。

对于 ADD candidate，anchor local mask 为空；对于 REVISE candidate，refined local mask允许保留、缩小或删除原 anchor component。禁止未经 utility 接受的局部概率部分写回。

## 五、Component utility 监督和接受规则必须精确定义

对 actual-train candidate ROI，定义 anchor local mask `A`、refined local mask `R`、可靠 GT `G`。

```text
E(M) = 2*FN(M,G) + 1*FP(M,G) + 0.25*boundary_error(M,G)
U = clip((E(A)-E(R)) / max(|A union R union G|, 1), -1, 1)
```

若 `R` 新增距离 GT 大于 20 mm 的 remote component，或产生 GT-positive empty prediction，则强制 `accept_target=0`。

否则：

```text
accept_target = 1 if U >= 0.02 else 0
```

Utility head 同时训练：

- accept BCE；
- clipped utility Huber regression；
- 两项总权重 `0.5`，scar 与 edema-zone 相同。

推理时每病种 utility threshold 只能用 fixed train-side inner cases 冻结。阈值候选固定：

```text
0.30, 0.40, 0.50, 0.60, 0.70
```

不得使用 outer fold0 选择阈值。

## 六、双病理一致性与安全

Edema-zone 监督目标固定为 scar union edema。增加对称之外唯一必要的层级约束：

```text
L_containment = mean(ReLU(p_scar_refined - p_edema_zone_refined))
```

只在 T2-present reliable cases 上启用，权重 `0.1`。它不能替代 edema segmentation loss。

最终顺序仍为：

```text
edema-zone arbitration
-> scar arbitration
-> scar priority
-> pure edema = final edema-zone minus final scar
```

No-T2 时 edema proposal、refiner、utility、loss、gradient、component construction 和 write-back全部为零；scar 可独立工作，最终 edema-zone mask按定义包含 final scar，但 pure-edema 保持 anchor pure-edema。

## 七、必须增加的 known-bad 与机制证据

W1/W2 必须拒绝：

- q_FN/q_FP 是唯一 proposal，缺少 `p_coarse`；
- teacher ROI 在 inner/outer evaluation 中使用；
- component decision 在 patch 内完成；
- patch final labels averaging；
- utility target读取 outer fold0；
- ADD 与 REVISE candidate混为一个无法区分的动作；
- 未接受 candidate 部分写回；
- no-T2 edema component被构建或接受；
- scar/edema 任一分支缺少 proposal、refiner或utility真实梯度；
- scar 指标通过而 edema 机制为空仍宣称通过。

正式 preflight 必须报告：

- `p_coarse` lesion/component recall；
- q_FN/q_FP AUCPR；
- teacher-ROI 与 predicted-ROI refiner Dice；
- predicted-ROI coverage；
- utility accept AUROC/AUPRC；
- oracle utility gain与realized gain；
- scar/edema各自 accepted/rejected candidate数量；
- full-volume component arbitration parity；
- zero accepted candidates = exact anchor。

## 八、人工邮件门

### Gate DPR-A：实现与 preflight 后、formal fold0 前

触发条件：W0、W1、W2全部完成，所有 GPU进程terminal，tests、known-bad、strict validator和preflight机制证据通过。

邮件：

```text
Subject: [CARE-DPR][A/2] 双病理 proposal-refine-arbitrate 实现完成，等待 Fold0 正式训练验收
State: AWAITING_HUMAN_ACCEPTANCE_DPR_GATE_A
Approval token: APPROVE_DPR_GATE_A
```

邮件必须包含：单一 encoder 证明、scar/edema三类输出、teacher-to-predicted ROI curriculum、proposal/refiner/utility梯度、no-T2 exact-zero、component arbitration、checkpoint/resume、机制上限和关键 hash。

邮件发送后必须暂停 W3。未经 `APPROVE_DPR_GATE_A` 不得运行 formal fold0。

### Gate DPR-B：Fold0 评价后

触发条件：W3 4000 steps terminal，W4 complete16/outer44及完整机制诊断完成。

邮件：

```text
Subject: [CARE-DPR][B/2] Fold0 双病理结果完成，等待下一轮决策
State: AWAITING_HUMAN_ACCEPTANCE_DPR_GATE_B
Approval token: APPROVE_DPR_GATE_B
```

邮件必须先用中文说明：是否超过同划分 nnU-Net、scar与edema分别如何、差距来自proposal/refinement/arbitration中的哪一层、oracle ceiling是否支持继续。附完整指标、per-pathology help/harm、remote FP、component、exact-HD、accepted/rejected components、source/config/checkpoint/prediction hashes。

Gate B 后不得自动扩 folds、all-data fit、validation package或上传。

## 九、资源与继续规则

唯一 GPU allocation仍为 `60657290`。禁止 sbatch、salloc、新 Slurm job、并行GPU进程、validation/Docker upload和runtime push。

若结果未过科学门：

- `EXECUTION_FAILURE`：同范围修复并重跑；
- `PROPOSAL_LIMITED`：返回 Planner重设计 proposal，不得只调 refiner；
- `REFINEMENT_LIMITED`：返回 Planner重设计 local reconstruction；
- `ARBITRATION_LIMITED`：返回 Planner重设计 utility/action，但不得加新 backbone；
- `ARCHITECTURE_CEILING_LOW`：返回 Planner全局重设计，不得宣布项目放弃。

任何状态都不允许自动终止 CARE 自研主线。