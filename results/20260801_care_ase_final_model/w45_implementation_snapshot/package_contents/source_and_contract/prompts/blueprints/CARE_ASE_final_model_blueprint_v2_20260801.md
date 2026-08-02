# CARE-ASE v2：非对称瘢痕候选形成与水肿全体积重建

**日期：2026-08-01**  
**状态：DESIGN_REVISED_BY_GPT_CRITIC；尚未授权执行或训练**  
**取代：`CARE_ASE_final_model_blueprint_20260801.md` 作为后续 Controller 的架构真值**

## 0. 总体判断

CARE-ASE 的总体方向成立：保留 nnU-Net 已经成熟的全体积分割能力，但不再让 stock 病理 logit、冻结锚点或浅层残差头控制最终结果；同时把 scar 与 pure-edema 分成两条统计性质不同的直接输出路径。原草案仍有四个会重复历史失败的结构性漏洞：病种分支只复制最终分类器而没有继承最高两级成熟解码器、no-T2 病例仍可能通过最终六类损失反向压制 edema、fold 内 Stage C 可能误用全部 80 例完整病例、以及 scar/edema 分别选择 checkpoint 与共享主干不相容。v2 将这些漏洞全部封闭。

最终结构为：

```text
[LGE,T2,C0] + availability
  -> 完整 stock-compatible encoder
  -> 完整低/中分辨率 shared decoder
  -> 复制并继续训练的最高两级 stock decoder stages
       |-> anatomy/context path
       |-> scar path: LGE + C0 + proposal/center + safe negative space
       |-> edema path: T2 + C0 + weak LGE + injury/extent/boundary
  -> 单一 checkpoint 的条件六类竞争
  -> full-volume physical-space evaluation
```

Stock checkpoint 只提供权重初始化、网络拓扑和成熟训练能力。正常 CARE-ASE 推理不读取、不相加、不回退到 stock class-4/class-5 logits；MoSAIC 不作为 teacher、selector、ensemble 或运行时输入。

## 1. 证据约束与病例目标

必须以最新 `origin/main`、`prompts/routes/handoffs/CURRENT.md` 和下列证据为准：

- nnU-Net clean OOF：scar 约 `0.5610`，pure-edema 约 `0.4308`。
- MoSAIC clean OOF：scar 约 `0.3782`，pure-edema 约 `0.0528`。
- nnU-Net/MoSAIC 病例 oracle 相对 nnU-Net 仅 scar `+0.0220`、pure-edema `+0.0023`，不支持 selector 或概率融合。
- decoder-reset 证据显示：完整 decoder identity 约 `0.92/0.92`，重置 decoder 后 scar/pure-edema 降至约 `0.55/0.00`；只训练顶部仍明显不足。

必须单独报告以下病例：

```text
CenterC edema under-activation: Case3008, Case3009, Case3012
class competition collapse:     Case3027
edema under/over-extent:         Case2034, Case2025
remote false positive:           Case2019
small/wrong-location scar:       Case2012, Case1045, Case1029, Case8021
local pathology complementarity: Case2009
```

模型不是为这些病例手工写规则；这些病例是预先冻结的失效哨兵，用于确认机制是否真正解决对应错误。

## 2. 固定数据与划分

```text
Dataset: Dataset501_CAREMyoPS
input order: [LGE, T2, C0]
compact labels: 0 background, 1 healthy myocardium, 2 LV, 3 RV, 4 pure edema, 5 scar
wall union: labels 1|4|5
injury auxiliary: labels 4|5
small lesion: physical volume < 1000 mm3
```

开发 fold 固定为 `2` 和 `3`。每个 fold 使用 nnU-Net `splits_final.json`：

- `outer`：该 fold 原始 validation cases，只允许冻结 checkpoint 后读取一次。
- `development pool`：其余 folds 的 cases。
- `inner`：从 development pool 按 `center × availability × T2-present × scar-volume-bin` 分层，固定 seed `20260801 + fold` 抽取 20%，且 CARE-ASE 训练不得读取 inner 图像或标签。
- `actual-train`：development pool 减去 inner。
- Stage C 只使用 `actual-train` 中的真实完整三模态病例，绝不使用 inner、outer 或全体 80 例。

W0 必须写出 case list、分层字段、seed、SHA256 和集合交集检查。任何交集非空均 fail closed。

## 3. 成熟解码能力的保留方式

### 3.1 `StockCompatibleTrunk`

加载对应 fold 的完整 `nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres` checkpoint。必须覆盖 encoder、bottleneck、全部 decoder stages、deep-supervision heads，参数字节覆盖率 `>=0.99`。

兼容模式必须复现 stock 每尺度 logits：

```text
FP32 max_abs_error <= 1e-6
argmax_changed_voxels = 0
```

### 3.2 分叉不是随机重建 decoder

分叉点位于最高两个 decoder resolutions 之前。scar 与 edema 各自复制 stock 最高两级 decoder stage 的完整拓扑和全部 shape-compatible 权重，包括 transition、skip fusion、convolution blocks 和 deep-supervision classifier。通道、stride、kernel 和 residual/non-residual 结构全部由真实 plans/module introspection 得到，禁止固定写成猜测的 `64/32` 小头。

额外的 modality、proposal、soft-wall、extent 和 context 特征只能通过独立的零初始化投影形成残差注入：

```text
F_branch_l = StockDecoderStage_l(F_prev, stock_skip) + ZeroInitProjection_l(extra_features)
```

因此在所有新投影关闭或保持零初始化时：

```text
z_scar_step0 == stock_class5_logit
z_edema_step0 == stock_class4_logit
max_abs_error <= 1e-6
```

这项 parity 只证明初始化没有丢失成熟能力，不允许正常推理读取 stock pathology logits，也不允许 fallback。

## 4. 模态角色与软解剖上下文

最高两个病种尺度均使用原始单模态图像的 plan-aligned 下采样适配器：

```text
Conv3d(1,16,3,padding=1) -> InstanceNorm3d(16,affine=True) -> SiLU
-> Conv3d(16,C_scale,1), final projection zero initialized
```

固定角色：

```text
scar:  LGE mandatory; C0 gate sigmoid(-1.3863)=0.2; T2 forbidden in v2
edema: T2 mandatory when present; C0 gate 0.2; LGE tanh gate initialized 0
```

availability 来自 manifest。缺失模态在 adapter 输入和输出两处硬清零。center ID 不进入 forward。

解剖分支输出：`anatomy_logits_0_3`、`p_wall_union`、`p_lv`、`p_rv`、`signed_endo_distance`、`signed_epi_distance`、`wall_depth_rho`。距离 target 使用真实 spacing 的 EDT，clip 到 `[-10,+10] mm` 后除以 10。拓扑异常切片只 mask 距离与 rho 回归，不阻断病例。进入病理分支前全部 `detach()`；只能作为软通道或软偏置，不得 hard multiply、hard crop 或 fail-stop。

## 5. Scar 路径

scar 路径保留完整全图高分辨率 decoder，并增加两个尺度的辅助候选：

```text
occupancy_logit
component_center_heatmap
slice_presence_logit
```

每个 26-connectivity GT component 都生成物理质心 Gaussian：in-plane sigma `4 mm`，z sigma `1 slice`。候选只作为特征与深监督，不生成 bbox，不裁剪主路径。

训练期四类 context：

1. `scar`：GT label 5；
2. `normal_myocardium`：wall union 内、非 pathology，且距 LV/RV 与 GT pathology 均超过 `3 mm`；
3. `blood_pool_adjacent`：非 pathology 且距 LV 或 RV mask `<=3 mm`；
4. `remote_background`：距 GT wall union `>10 mm`。

优先级固定为 `scar > blood_pool_adjacent > normal_myocardium > remote_background`；其他像素 ignore。

canonical OOF component 定义：

```text
FN/low-overlap: GT component voxel recall < 0.50
FP component: predicted component precision < 0.10
remote FP: predicted component min physical distance to GT wall union > 10 mm
blood-pool FP: >=50% component voxels within 3 mm of LV/RV
```

采样比例固定：`35% GT component + 20% small component + 20% OOF FN + 15% OOF FP + 10% random`。OOF 预测必须来自未训练该病例的 stock fold；当前模型的 in-sample 错误不得在线刷新。

## 6. Edema 路径

edema 路径不做 bbox、hard proposal 或 local-only refiner。最高两个 cloned decoder stages 接收 T2/C0/LGE adapter、detached soft-wall 与 upsampled injury feature。额外上下文采用 dilation `1/2/4` 的残差上下文块，但通过零初始化投影接入，不替代 cloned decoder。

输出：

```text
z_pure_edema
z_injury_aux       # labels 4|5，只作训练与feature support
z_edema_boundary   # signed distance regression
```

edema boundary target 为 pure-edema signed EDT：内部为正、外部为负，clip `[-10,+10] mm`、除以 10，只在距边界 `<=10 mm` 或 GT positive voxels 上计算 SmoothL1。

edema context 类与 scar 相同，但正类为 pure-edema，且只在 T2-present 病例生成。采样比例固定：`35% positive + 20% OOF low-volume/FN + 20% boundary + 15% safe FP + 10% random`。complete-case sampler 只在各 fold actual-train 内做 CenterB/CenterC 1:1 有放回平衡。

## 7. Slice extent 的确定义

scar 与 edema 各有独立 extent head。输入为对应 `1/4` feature，对 H/W 做 detached `p_wall` 加权平均与 masked max，输出逐 z 切片 presence 和 pathology/wall area fraction。

- 若预测 wall 权重和 `<1.0`，pooling 回退为该切片全图 average+max；该回退必须计数。
- GT wall denominator 为 0 的切片：area loss ignore，presence 仍按 pathology non-empty 监督。
- inference 概率在取 logit 前 clamp 到 `[0.01,0.99]`。
- extent 只能加固定软偏置，不能 hard 清零切片。

```text
scar:  presence 0.30, area 0.20, wall 0.15
edema: presence 0.35, area 0.30, wall 0.10
```

## 8. no-T2 的条件竞争与零梯度

原草案的无条件 `L_final6` 会让 no-T2 病例把 class 4 当作负类，和“edema 分支梯度为 0”冲突。v2 使用条件最终损失：

```text
T2-present:
  L_final_comp = six-class DiceCE([z0,z1,z2,z3,z4,z5], y)

no-T2:
  L_final_comp = five-class DiceCE([z0,z1,z2,z3,z5], remap_without_class4(y))
  z4 is excluded from the graph
```

no-T2 病例的 `edema_dense/injury/boundary/extent/context/relation` 全部为 0，edema-exclusive 参数梯度最大绝对值必须精确为 0。shared trunk 仍可由 anatomy/scar 更新。no-T2 inference 的最终竞争同样排除 class 4；这不是把病例当 edema-negative，而是承认没有可靠 T2 证据。

## 9. 损失的确定义

- 多类 DiceCE：softmax；CE 使用有效类；Dice 仅前景类，smooth `1e-5`，先逐病例再对有效病例平均。
- 二元 Dice：sigmoid，smooth `1e-5`，逐病例；空 GT 通过 BCE/Focal 约束 FP，Dice 项记 0 denominator 并不伪造满分。
- Focal：scar `alpha=.25,gamma=2`；edema `alpha=.35,gamma=2`。
- component Tversky：每个 GT component 单独计算，`alpha=.3,beta=.7`，按 `clip(sqrt(1000/volume_mm3),1,4)` 加权；无 component 时该项为 0。
- center focal BCE：正负像素归一化后逐病例平均。
- context CE：只对非-ignore context voxels。
- relation：仅 T2-present，使用 `relu(max(stopgrad(p_scar),stopgrad(p_edema))-p_injury)`，只训练 injury 支撑，不反向压低 scar/edema。

总权重保持：

```text
1.00 final competition
0.50 anatomy4 + 0.25 wall + 0.10 distance
1.00 scar dense + 0.25 component + 0.10 center + 0.15 extent + 0.10 context
T2 * (1.00 edema dense + 0.40 injury + 0.10 boundary
      + 0.20 extent + 0.10 context + 0.05 relation)
```

禁止执行期新增 compactness、HD surrogate、prototype、SIP、distillation 或其它 loss。

## 10. 训练预算与单一 checkpoint

每 fold 固定 `14000 optimizer steps`：

```text
Stage A 0-2000:   冻结 encoder/shared low-mid decoder；训练 cloned top stages 的新注入、病种/解剖辅助头
Stage B 2000-10000: 解冻完整 shared decoder 与 upper two encoder stages
Stage C 10000-14000: 只用 fold actual-train complete tri-modal；所有层可训练
```

Stage A/B/C 均不可因早期 Dice、loss 或视觉结果跳过。optimizer 为 AdamW，weight decay `1e-4`，physical batch 1，accumulation 4，gradient clip 12。checkpoint 每 1000 步；full-volume inner 每 2000 步。

候选 step 固定 `[4000,6000,8000,10000,12000,14000]`。因为 encoder/shared decoder 是共享参数，禁止 scar、edema、anatomy 分别拼接不同 checkpoint。每 fold 只选择一个完整 checkpoint：

```text
joint_score = 0.5 * scar_score + 0.5 * edema_score
```

其中 scar_score/edema_score 沿用原草案的物理指标公式；同分时选择更晚 step。选择后必须重新加载整个 checkpoint，并验证 state-dict SHA、optimizer-independent inference parity、case list 与 decode hash。

## 11. Slurm、resume 与 No-Run

正式训练拆成每 fold 七个连续 `2000-step` chunk，每个单 job walltime `<=8h`：Stage A 1 个、Stage B 4 个、Stage C 2 个。训练 chunk 用 `afterok`；最终 accounting/finalizer 用 `afterany`。

每个 checkpoint 必须保存：model、optimizer、scheduler、precision scaler（如适用）、global/stage step、Python/NumPy/Torch/CUDA RNG、sampler cursor、batch descriptor cursor、split/config/code hashes。resume 必须验证 hash 和 next-batch descriptor，禁止 step reset、重复或跳过。

路由固定：

1. 首先提交 `htzhulab`；
2. 首次 2 小时检查仍未启动，则为同一 fold/chunk 提交隔离的 `a100-gpu` mirror；
3. atomic winner lock 决定唯一正式 attempt，启动后取消仍 pending mirror；
4. 不使用 V100，除非未来合同另行授权；
5. 所有已提交兼容分区连续 12 次、每 2 小时均无启动，才可判定 24 小时 scheduler block。

startup/preemption 同语义重试上限各 2 次；失败 attempt 训练 credit 为 0。Controller 不得在 submitted、pending、running、preempted、awaiting sacct 或 partial checkpoint 状态退出。W2 implementation PASS 后必须自动提交 W3，不等待新 prompt。

## 12. 评价、审阅与发布边界

inner 只用于单 checkpoint 选择。outer 在 `checkpoint_freeze_receipt.json` 后每 fold读取一次；不得调整阈值、系数、source、checkpoint 或后处理。

必须报告 Dice、HD95/exact HD mm、precision、sensitivity、lesion/small-lesion recall、component count、remote/blood-pool FP、volume ratio、help/harm、CenterB/CenterC 和全部 sentinel cases。

独立 reviewer 固定到 terminal commit 的只读 checkout，检查代码、runtime、14000 步、checkpoint reload、outer access count、no-T2 梯度、module intervention 与机器 gate。Reviewer 不能参与实现或选择。

当前 v2 仍不授权执行、训练、validation、Docker 或 hosted claim。未来用户一次性授权正式 Controller 时，授权字段必须在启动前冻结；Controller 完成 terminal aggregation、validator、review 后，不得再停下来索要第二次“是否 commit/push”的 prompt。若启动合同已授权 main commit/push，则由同一 Goal 完成 main push，再写 `notification_brief.json` 并调用既有 notifier；未授权则明确停在本地 terminal packet，不得伪造完成。
