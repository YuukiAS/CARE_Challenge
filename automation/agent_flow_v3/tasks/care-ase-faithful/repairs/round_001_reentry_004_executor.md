# CARE-ASE Planner → Executor 精确返修

你是本任务已经绑定的 production Executor。只有在 Controller 确认 Verifier 本轮已完成 loss semantic oracle 修复并冻结新的 verifier fingerprint 后，才恢复原 Executor thread / CODEX_HOME / worktree。不得新建替代角色，不得修改 Verifier。

## 本轮 Planner 绑定

- task_id: `care-ase-faithful`
- request_nonce: `care-ase-20260806T090955Z`
- frozen contract SHA256: `a4758fd3125cdfaac4cf044fd4fa948472558cca231c0429a26e63e5d7d1e11d`
- Planner 审阅的 integration: `491ba697e7a51712d9d04fc27824e4efa018827a`
- Planner 审阅的 implementation fingerprint: `25828c210776d499613a872754d39290cf9df416a747fb9f0f86c56f91711dc6`
- Planner 审阅的 verifier fingerprint: `1cce33fdfe102efb63979870f190bfc1a2584385a07f6f2db2ccddcb14e69aaa`
- Planner review: `results/agent_flow_v3/care-ase-faithful/planner_reviews/round_001_reentry_004.json`
- decision: `PLANNER_REVISE_BOTH`

注意：上述 verifier fingerprint 是 Planner 发现问题时的输入。Executor 真正返修时必须使用 Controller 提供的、经过本轮 Verifier 修复后**新冻结的精确 verifier fingerprint**，并把它写入新的 implementation evidence/fingerprint transaction。不得继续使用旧 verifier fingerprint。

## 必须修复的实现问题

### 1. Injury loss 必须恢复为合同规定的 Dice+BCE

冻结合同唯一允许的 injury 项是：

`0.40 * injury Dice+BCE`

当前 `src/care_myocardium/training/care_ase_trainer.py::care_ase_loss` 实际调用 `binary_dice_focal(..., alpha=0.35, gamma=2.0)`，这属于错误公式。

必须改为真正的 Dice+BCE，并保持：

- injury target = label 4 或 label 5；
- 只在 T2-present row 上监督；
- no-T2 row 对 injury loss 和 edema-owned gradient 为零；
- fp32 sensitive reduction 与现有有效 mask/denominator 语义不降级；
- 0.40 权重不变。

不得只修改 metric 名称或 receipt 标签。

### 2. Scar 0.25 component 项必须是纯 component-adaptive Tversky

冻结合同唯一允许的是：

`0.25 * scar component-adaptive Tversky(alpha=0.3, beta=0.7)`

当前实现把：

`scar_component_supervision = 0.5 * scar_component + 0.5 * scar_occupancy`

再作为 0.25 项加入总 loss，其中 `scar_occupancy` 是额外 quarter/half Dice+Focal objective。该 occupancy auxiliary loss 不在冻结合同唯一允许 loss 集中。

必须：

- 让 0.25 项只等于合同定义的 per-GT-component adaptive Tversky；
- 保留合同规定的 component volume 自适应规则、`alpha=0.3`、`beta=0.7`；
- 删除总 loss 中未授权的 scar occupancy auxiliary objective；
- 不得把 occupancy loss 藏到 Tversky helper、其它 term、regularizer 或 receipt builder 中。

Proposal/occupancy head 若需要学习，只能通过冻结合同已经允许的普通 final reconstruction authority/其它明确允许路径获得梯度；不得自行新增 loss。

### 3. 让 loss receipt 与真实数学一致

同步修正 `care_ase_loss_with_term_details` 与相关 evidence builder，确保：

- `injury_dice_bce` 数值真的是 Dice+BCE；
- `scar_component_adaptive_tversky` 数值真的是纯 adaptive Tversky；
- `weighted_contribution` 与总 loss 中实际相加的张量一致；
- 总 loss 精确由冻结合同允许的 15 个 term 组成；
- 不存在额外 weighted auxiliary term；
- denominator/eligible rows/voxel count 使用真实执行值，不能伪造常量。

## 不得回退上一轮已经修好的实现

必须保留当前已经关闭的问题：

- `CAREASE.forward` 中不得重新出现 disable/test/intervention flag 触发的额外 final-logit signal；
- disable flags 只能移除/归零正常路径已有贡献；
- partial-H/W extent 必须真实零 bias/loss/gradient，fully-valid 邻近切片继续保留真实目标；
- canonical full-volume inference 必须逐 tile 真正执行模型，不得退回 full-support pseudo-tiling；
- extent/wall global bias 只在 tile aggregation 后应用一次；
- no-T2 五类竞争和 edema graph/gradient 零执行语义不变；
- injury classifier 的 stock class4/class5 mean 初始化、dilation 1/2/4 residual、独立 SliceExtentHead、named evidence projections 等现有合同实现不得降级；
- checkpoint/resume、augmentation full-case physical target、OOF hard-negative、deployment/evaluator 等已建立的实现证据不得退化。

## 必须在新冻结 Verifier 下重建 evidence

修复代码后，不得沿用当前 `25828c...` implementation fingerprint 或旧 source manifest。

必须重新生成并绑定：

1. 当前全部 critical source 的 source manifest；
2. implementation evidence；
3.真实 train-only forward/backward receipt；
4. 新 implementation fingerprint；
5. 新冻结 verifier fingerprint；
6. 当前 nonce、frozen contract SHA、review round；
7. Controller 后续形成的新精确 integration SHA。

当前 integrated validator 已明确发现 source manifest 对 `core.py` 的 hash 失配；这一问题必须消失。新的 implementation fingerprint/source manifest 必须嵌入本轮新冻结的 Verifier fingerprint，而不是旧的 `a1c660...` 或 `1cce33...`。

## 必须通过的回归证据

- Verifier 独立重算的 injury Dice+BCE 与实现中的 0.40 contribution 一致；
- Verifier 独立重算的 scar adaptive Tversky 与实现中的 0.25 contribution 一致；
- injury BCE→focal known-bad 必须失败；
- scar Tversky 混入 occupancy known-bad 必须失败；
- 真实 mixed T2/no-T2 batch 仍满足 no-T2 edema loss/grad/graph 为零；
- 完整允许 loss 集所有项 finite、denominator真实且总和闭合；
- 现有 authority、extent、tile-local inference、checkpoint、deployment/evaluator、hard-negative probes 不得出现回归。

## 禁止的修复方式

- 不得改冻结合同；
- 不得修改 Verifier 或 protected tests；
- 不得根据 test/mutation ID 走特殊路径；
- 不得用 receipt 字段伪造正确公式；
- 不得新增未授权 auxiliary loss；
- 不得通过 epsilon/noise/特殊 disable 信号制造测试差异；
- 不得 formal training；
- 不得访问 outer；
- 不得 Docker build/upload、validation upload、organizer email；
- 不得 develop -> main。

完成后把 Executor role commit 与新 evidence/fingerprint交回 Controller。Controller 必须重新集成、针对新精确 integration 运行冻结 Verifier、重建 runtime transaction，并对新的 integration 重新跑 hosted CI 后才能再次进入 Planner review。
