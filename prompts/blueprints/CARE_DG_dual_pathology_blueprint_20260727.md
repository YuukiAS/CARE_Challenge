# CARE-DG：双门控心肌病理错误修正蓝图

## 结论

`CARE-DG` 是当前 CARE 最终 validation/test 冲刺的唯一目标架构。运行时只有两部分：冻结的五折 nnU-Net 锚点，以及一个紧凑的 CARE 双病理错误修正网络。不得加载 MoSAIC、完整 CARE-MMRD、SRR dictionary/prototype memory、SIP、多个专家或完整旧 Cascade。

完整名称首次出现时使用：

```text
CARE-DG: Dual-Gated Residual Correction for Myocardial Scar and Edema Segmentation
```

后续只称 `CARE-DG`。

官方目标域已经固定：validation 15 例、test 65 例均为完整 `LGE + T2 + bSSFP/C0`。因此 complete-trimodal OOF 是竞赛部署主评价总体；all-220 mixed-modality OOF 继续作为鲁棒性和 limitation 证据。

## 科学动机

历史 Batch7 和旧 Cascade 并不是完全没有病理信号。完整三模态 fold0 中，Batch7/Cascade scar 距 nnU-Net 仅约 0.007–0.008 Dice；Cascade edema Dice/HD95 有小幅正信号。失败集中在：修正幅度太弱、错误体素采样不足、scar/edema 最终头语义混合、只修改病理 logit、硬 support、exact-HD 远端错误，以及风险门过于容易整体回退。

CARE-DG 不重新学习完整分割，而是学习：

```text
强 nnU-Net 锚点在哪里漏检（FN）
强 nnU-Net 锚点在哪里误检（FP）
需要多大修正才能翻转错误 logit margin
怎样在不破坏解剖和最坏病例安全的前提下修正
```

## 从历史路线继承什么

### MMRD 成熟思想

- LGE、T2、C0 使用浅层模态特异 stem；
- modality availability 显式输入；
- scar 与 edema 监督语义分离；
- edema 训练只使用 T2-present reliable labels；
- no-T2 病例 edema loss 为 0，推理修正严格为 0；
- 不继承完整 MMRD 大型 backbone、teacher runtime 或弱单通道 residual heads。

### SRR 成熟思想

- 只在存在明确错误证据时修正，避免无条件融合；
- 使用显式 FN/FP error gates 代替未验证的 dictionary/prototype memory；
- error-centric sampling 强制模型看到 anchor 错误；
- real-vs-zero prototype ablation 不是核心任务，本版不引入 prototype runtime。

### Cascade 成熟思想

- nnU-Net 是冻结强锚点；
- anatomy 类保持 identity；
- scar 与 edema 使用独立 correction decoder；
- 修正是 signed、bounded、pathology-specific；
- 只有明确安全违规时逐病种 exact fallback，不能默认整体退回 nnU-Net。

## 推理架构

### 输入

所有输入位于冻结 nnU-Net preprocessed grid：

```text
LGE image
T2 image
C0 / bSSFP image
3-channel modality availability broadcast map
6-class nnU-Net anchor logits or calibrated log-probabilities
nnU-Net ensemble uncertainty / disagreement
soft myocardium support
signed distance to myocardium support
```

官方 validation/test availability 全为 1，但 availability channel 仍保留以保证训练语义正确。

### 网络主体

```text
LGE shallow stem (8 ch) ─┐
T2 shallow stem  (8 ch) ─┼─> compact shared 3-scale encoder
C0 shallow stem  (8 ch) ─┘        channels 32 / 64 / 96
anchor-context stem (16 ch) ───────┘

shared encoder
   ├─> scar decoder 64 -> 32
   │      q_scar_FN, q_scar_FP
   │      m_scar_FN, m_scar_FP
   └─> edema-zone decoder 64 -> 32
          q_edema_FN, q_edema_FP
          m_edema_FN, m_edema_FP
```

网络采用 anisotropy-aware 3D residual blocks：浅层 kernel `(1,3,3)`，深层 kernel `(3,3,3)`；只做 in-plane downsampling `(1,2,2)`，避免小 Z 维度被过度压缩。

### 显式错误门

对病种 $$k\in\{scar, edema\}$$：

$$q_k^{FN}(x)=P(\text{anchor 在 }x\text{ 漏检}),$$

$$q_k^{FP}(x)=P(\text{anchor 在 }x\text{ 误检}).$$

修正幅度：

$$m_k^{FN}(x)=\operatorname{softplus}(a_k^{FN}(x)),$$

$$m_k^{FP}(x)=\operatorname{softplus}(a_k^{FP}(x)).$$

signed correction：

$$\delta_k(x)=q_k^{FN}(x)m_k^{FN}(x)-q_k^{FP}(x)m_k^{FP}(x).$$

修正上限由每个 outer-training fold 的 anchor error margin 95% 分位数加 1 决定，并截断到 `[2,8]`，不得读取 held-out case：

$$M_k=\operatorname{clip}\left(Q_{0.95}(|\mathrm{margin}_{anchor}|\mid error)+1,2,8\right).$$

### 竞争类别联动修正

仅增加 pathology logit 可能无法翻转 anchor。CARE-DG 同时调整当前最高非病理竞争类别：

$$z_k^{final}=z_k^{anchor}+s_k\,\operatorname{clip}(\delta_k,-M_k,M_k),$$

$$z_{c_k}^{final}=z_{c_k}^{anchor}-s_k\,\operatorname{clip}(\delta_k,-M_k,M_k),$$

其中 $$c_k$$ 是 voxel 当前最高非病理类别，$$s_k$$ 是 soft anatomy support。Scar support 使用 myocardium 与 6 mm soft shell；edema-zone 使用 myocardium 与 10 mm soft shell。support 是连续权重，不得作为硬裁剪 mask。

### 解剖与双病理组合

- background、myocardium、LV、RV 在 pathology support 外严格等于 anchor；
- scar 与 edema-zone 独立解码和校准；
- scar 优先；
- pure edema 为：

$$E_{pure}^{final}=E_{zone}^{final}\setminus S^{final}.$$

## 训练标签与损失

### OOF 错误标签

每个病例只能使用其 held-out nnU-Net fold prediction：

$$y_k^{FN}=\mathbf 1(y_k=1,\hat y_k^{anchor}=0),$$

$$y_k^{FP}=\mathbf 1(y_k=0,\hat y_k^{anchor}=1).$$

### Patch 采样

固定 patch shape `(Z,Y,X)=(8,128,128)`，batch size 8。每 batch：

```text
50% anchor-error-centered patches: FN 与 FP 等量
25% GT pathology / boundary-centered patches
25% hard-negative or random anatomy patches
```

Scar hard negatives优先包括 blood pool、myocardium 外 LGE bright islands 和历史 remote FP 区域。Edema hard negatives只来自 T2-present reliable cases。

### Loss

每个 active pathology：

```text
1.0 * final segmentation Dice + CE
0.5 * class-balanced FN/FP focal-BCE
0.25 * error-margin improvement loss
0.10 * identity loss on anchor-correct voxels
0.10 * soft-support / remote-positive penalty
```

scar 与 edema active 时等权。no-T2 病例 edema 全部损失权重为 0。

Margin loss要求在 anchor error voxel 上，final pathology-vs-competitor margin 相对 anchor 至少改善预注册 margin `m=1.0`；在 anchor-correct voxel 上不允许无必要大修正。

## 正式训练预算

每 fold 单 seed `20260727`：

```text
Stage A: 5,000 optimizer steps
  all reliable training cases
  complete-trimodal case sampling weight 4
  AdamW lr 3e-4, weight decay 1e-4

Stage B: 3,000 optimizer steps
  complete-trimodal training cases only
  encoder lr 2e-5
  pathology decoders/heads lr 1e-4

batch size 8
mixed precision
checkpoint at 1k-step intervals
```

五折全部执行，不能因 fold0 均值暂时不高而提前终止。只允许对 implementation collapse 做一次同范围修复；不得根据 held-out metrics 改网络、loss 权重或阈值。

OOF 结构、decode 和安全阈值冻结后，使用相同 Stage A/B schedule 训练一个 all-data deployment model；训练输入仍使用 220 例 OOF anchor evidence，validation/test 推理使用 nnU-Net 五折 ensemble anchor。

## Anti-identity 机制门

正式 OOF 必须证明：

```text
FN/FP maps 非常数
>= 30% complete held-out GT-positive cases 有非零 changed voxels
>= 10% anchor error voxels 接受到正确方向修正
scar 与 edema 至少各在一个 held-out case 真实激活
zero-correction known-bad 被 validator 拒绝为 promoted candidate
```

若失败，状态是 `MECHANISM_COLLAPSE_NEEDS_REPAIR`，Controller 必须检查 sampling、loss wiring、gradient 和 margin clipping；不得直接 fallback 到 nnU-Net 并宣称 CARE 完成。

## 安全与 fallback

Fallback 不是默认路径。每病种只在以下情况独立触发：

```text
NaN/Inf 或 geometry mismatch
checkpoint/config/hash mismatch
no-T2 edema changed voxels > 0
corrected pathology volume、component count、remote distance 超出 outer-training OOF 1%-99% envelope 加 20% margin
new infinite HD-risk sentinel
```

Scar fallback 不影响 edema；edema fallback 不影响 scar。若 validation 中任一病种 fallback case rate > 30%，该 package 视为 mechanism inactive，不得作为最终 CARE candidate。

## 评价总体

Primary competition estimand：

```text
80 complete C0+LGE+T2 OOF cases
```

Robustness estimand：

```text
all 220 mixed-modality OOF cases
```

Edema 主评价只使用 T2-present reliable GT-positive cases，同时报告 edema-zone 与 pure edema。no-T2 只做 identity safety。

固定指标：Dice、leaderboard-compatible HD、HD95、exact HD、precision、recall、remote FP mm3、component count、volume ratio、empty prediction、changed voxels、case-wise help/harm、fallback rate。

## Candidate 门

Paper-ready pathology：

```text
complete-target Dice gain >= +0.005 over nnU-Net
HD95 non-worse within 5%
exact-HD 95th percentile increase <= 5 mm
remote FP non-increased
help > harm
non-zero mechanism activation
```

Exploratory dual-pathology validation candidate：

```text
scar complete-target Dice delta >= -0.005
pure-edema complete-target Dice delta >= -0.005
edema-zone Dice delta >= -0.005
at least one pathology Dice gain >= +0.005
HD95 <= 1.05 * anchor for both pathologies
no new infinite exact-HD case
remote FP increase <= 10%
help cases >= harm cases - 1 per pathology
both pathology mechanisms activate
no-T2 edema changed voxels = 0
```

若不通过，终态是 `NO_CARE_DG_CANDIDATE_SAFE_FOR_VALIDATION`，不得生成纯 nnU-Net 或旧模型冒充 CARE。

## Validation / test 适配

Validation 15 例和 test 65 例均为完整三模态，CARE-DG 的 Stage B 和 primary OOF 都与该目标一致。匿名中心风险通过 per-case robust percentile normalization、强 gamma/bias-field/intensity augmentation、无 center ID 和 frozen OOF thresholds 控制。

## 明确禁止

```text
MoSAIC runtime
完整 MMRD runtime/teacher
prototype dictionary/memory/SIP
完整 SRR-v3
多个专家模型或 learned arbiter
新的 full segmentation backbone
scar/edema shared final head
hard anatomy crop
默认整体 fallback
只报告 component F1 或 mean Dice
根据 validation hosted score 调参
```
