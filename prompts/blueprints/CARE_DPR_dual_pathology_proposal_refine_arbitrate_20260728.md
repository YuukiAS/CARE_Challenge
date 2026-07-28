# CARE-DPR：双病理 Proposal–Refine–Arbitrate 全局重设计蓝图

## 1. 为什么需要全局重设计

CARE-DG Gate B-R1/R2 已经证明两件事：第一，原始多模态图像中确实存在能够预测 nnU-Net 病例外错误的信号；第二，把这些信号直接变成逐体素 bounded correction，只能得到很小的 Dice 增益，并且容易在没有 Gaussian blending 时形成碎片化组件。当前问题不是“完全没有信号”，而是“错误证据没有被转化为完整、稳定、可接受的病灶修正”。

因此下一轮不再继续调 correction scale，也不再给现有网络追加零散部件。方法整体改为一个统一的双病理 proposal–refine–arbitrate 系统：一个共享 CARE 多模态编码器，两条独立但结构对称的 scar 与 edema-zone 分支，每条分支同时负责错误 proposal、局部病灶 refinement 和组件级接受/拒绝。nnU-Net 只作为冻结 anchor、解剖上下文和 exact fallback，不是模型唯一主体；MoSAIC 不进入 runtime。

## 2. 历史经验如何继承，但不复刻旧失败系统

### 2.1 从 CARE-MMRD 继承

保留：

- LGE、T2、C0 modality-specific stems；
- availability mask，缺失模态特征严格归零；
- scar 监督使用所有 scar-reliable 病例；
- edema-zone 监督只在 T2-present 可靠病例上启用；
- no-T2 病例的 edema 分支监督、梯度和最终改写严格为零。

不继承：

- 完整 CARE-MMRD backbone 或 teacher runtime；
- 伪 T2、伪 edema 标签或把 no-T2 当 edema negative；
- 多个完整 segmentation backbone。

### 2.2 从 Batch7 / SRR proposal-refiner 思想继承

保留：

- scar 与 edema 分开建模；
- pathology-specific proposal 与 pathology-specific local refinement；
- anatomy-guided soft ROI；
- 明确的 FN/FP 错误监督；
- small-ROI scar refinement 与 larger-context edema refinement 的差异。

不继承：

- dictionary、prototype memory、router、多个 expert backbone；
- proposal 直接在整幅图上无限制写回；
- 一次性塞入过多难以归因的机制。

### 2.3 从 CARE-SRR-Cascade 继承

保留：

- 冻结强 anchor；
- 只改 pathology 通道；
- scar 与 edema 独立安全决策；
- bounded composition；
- per-pathology exact fallback；
- remote FP、component count、exact HD、help/harm 进入正式 gate。

不继承：

- frozen MMRD teacher、prototype bank、多个 source backbone；
- control/SRR 多模型 runtime；
- 把 anchor 变成唯一真正工作的主体。

## 3. 最终架构

### 3.1 输入

每例输入：

- LGE、T2、C0；
- modality availability；
- 冻结 nnU-Net anchor logits/probabilities；
- anchor uncertainty；
- myocardium/pathology-capable soft support；
- distance-to-support map。

禁止 center ID、hosted validation 标签、MoSAIC 权重、MMRD teacher、prototype/dictionary。

### 3.2 单一共享 CARE 编码器

只使用一个紧凑三尺度 encoder：

- 三个浅层 modality-specific stems；
- availability-aware masked fusion；
- anchor context stem；
- 一个 shared three-scale encoder。

不允许第二个完整 U-Net、第二个 nnU-Net、MoSAIC coarse/fine backbone、多个 expert encoder。

### 3.3 两条对称但病理特异的分支

ScarBranch 与 EdemaZoneBranch 具有相同的三段结构，但参数独立：

1. **Error proposal head**
   - 输出 `q_fn` 与 `q_fp`；
   - scar 使用 LGE-dominant evidence；
   - edema-zone 使用 T2-conditioned evidence；
   - 这些 map 只定义候选错误区域，不直接决定最终标签。

2. **Local refinement head**
   - 读取 full-resolution shared feature、原始病理模态、anchor pathology margin、q_fn/q_fp、support、uncertainty；
   - 在 soft ROI 内输出 refined pathology logit；
   - scar ROI 采用较小高分辨率上下文；
   - edema-zone ROI 采用更大上下文；
   - refinement 是完整局部病灶重建，不是逐体素 correction magnitude 放大。

3. **Component utility head**
   - 对候选组件池化局部 feature、refined probability、anchor margin、q_fn/q_fp、uncertainty、support distance、组件体积与形状；
   - 输出组件级 expected utility / accept probability；
   - scar 与 edema-zone 分别训练、分别校准、分别 fallback。

### 3.4 候选 ROI 与组件

训练时使用 soft ROI：

`ROI_k = soft_union(anchor_prob_k, q_fn_k, q_fp_k, uncertainty) * support_k`

推理时，候选组件来自：

`connected_components(anchor pathology union refined proposal)`

每个组件只能执行两种动作之一：

- 接受 refined component；
- 完整保留 anchor component / anchor background。

不允许组件未通过 utility gate 却部分写回，不允许全图阈值后处理替代 acceptor。

### 3.5 双病理最终组合

顺序固定：

1. edema-zone component arbitration；
2. scar component arbitration；
3. scar priority；
4. pure edema = accepted edema-zone minus accepted scar。

无 T2 时：

- edema proposal、refiner、acceptor 输出全部置零；
- edema 通道与 anchor 完全相同；
- scar 仍可独立工作。

Anatomy channels 0–3 默认保持 anchor；只有被接受的 pathology component 才允许 bounded pathology write-back。任一病理分支没有安全候选时，精确 fallback 到 anchor。

## 4. 训练目标

Scar 与 edema-zone 的总权重对称，不得用 composite mean 掩盖任一病种。

每个病理分支包含：

- reliable segmentation Dice + BCE：1.0；
- FN/FP proposal focal BCE：0.5；
- boundary / surface surrogate：0.1；
- component utility BCE + utility regression：0.5；
- anchor-correct identity / remote negative penalty：0.1。

Edema-zone 全部损失逐病例乘 T2-reliable mask。No-T2 edema loss、梯度、proposal、refinement、utility 和最终改写均为零。

组件 utility target 由 actual-train GT 计算：比较“采用 refined component”与“保留 anchor”在该候选区域的错误数、Dice、remote FP 和组件安全。utility target 不读取 outer held-out。

## 5. 采样

使用八槽平衡循环，scar 与 edema 各占一半：

1. scar FN component；
2. scar FP component；
3. scar hard negative；
4. scar pathology component；
5. edema-zone FN component；
6. edema-zone FP component；
7. edema-zone hard negative；
8. edema-zone pathology component。

Hard negative 必须显式包括：

- LV/RV blood pool；
- support 外亮岛；
- remote anchor FP；
- 高强度但无可靠病灶的区域。

No-T2 病例不得进入 edema 槽。

## 6. 初始化与训练预算

Fold0 pilot 使用当前 fold0 CARE-DG train-side 选出的 checkpoint step4000 初始化：

- modality stems；
- anchor context；
- shared encoder；
- q_fn/q_fp proposal weights。

新的 local refiner 与 component utility heads 随机初始化。旧 CARE-DG checkpoint 只是初始化资产，不是 runtime ensemble。

正式 fold0 预算：

- Stage A：2500 optimizer steps，actual-train 全部可靠病例；encoder lr `2e-5`，proposal/refiner/utility lr `1e-4`；
- Stage B：1500 optimizer steps，仅 complete-trimodal actual-train；冻结 stems、shared encoder 与 q proposal，只训练 scar/edema local refiner 和 component utility heads，lr `5e-5`；
- batch size 4；
- patch `8×128×128`；
- AdamW，weight decay `1e-4`；
- bfloat16；
- grad clip norm 1.0；
- seed `20260728`。

Checkpoint 每 500 steps 保存。选择只使用 fixed train-side complete inner cases；outer fold0 只评价一次。

## 7. 先诊断再训练：区分执行问题与设计问题

在正式训练前，必须用旧 CARE-DG fold0 checkpoint 和 train-side inner cases 生成 mechanism ceiling packet：

- FN component recall；
- FP component recall；
- q_fn/q_fp AUCPR；
- soft ROI GT coverage；
- oracle component acceptor gain；
- oracle local replacement gain；
- 当前 realized gain。

分类规则：

### EXECUTION_FAILURE

任一测试、梯度、mask、scar-priority、no-T2、checkpoint、ROI 对齐、outer leakage、component target 构造失败。Controller 必须同范围修复并重跑，不得转成科学失败。

### PROPOSAL_LIMITED

任一病种 train-side inner FN component recall `<0.70` 或 FP component recall `<0.70`。正式训练仍继续，但必须把 proposal loss、hard-negative exposure 和候选 coverage 列为首要机制验收；不得只调 refiner。

### REFINEMENT_LIMITED

proposal recall `>=0.70` 且 oracle local replacement Dice gain `>=+0.01`，但 realized gain `<+0.005`。说明信号存在，主要检查 refiner、utility target 和 Stage B。

### ARCHITECTURE_CEILING_LOW

oracle component/local replacement gain `<+0.005`。这不允许终止项目；Controller 必须返回 Planner 进行下一次全局架构重设计，禁止写 `NO_CANDIDATE` 作为项目终态。

## 8. Fold0 科学门

Complete-trimodal 16 例为主要目标，同时报告 outer44 robustness。

必须同时满足：

- scar Dice delta `>= -0.005`；
- edema-zone Dice delta `>= -0.005`；
- pure-edema Dice delta `>= -0.005`；
- 至少一个病种 Dice gain `>= +0.005`；
- scar、edema-zone、pure-edema 各自 help `>= harm - 1`；
- HD95 `<= 1.05 × anchor`；
- 无新增 infinite exact-HD；
- remote FP 增加 `<=10%`；
- component count 不得数量级爆炸；
- 两条 proposal/refiner/utility 机制均真实激活；
- no-T2 edema changed voxels = 0；
- exact per-pathology fallback PASS。

如果不通过，不得宣布放弃。必须输出：执行缺口、proposal 缺口、refinement 缺口、arbitration 缺口、oracle ceiling 和下一轮全局重设计建议。

## 9. 资源和权限

唯一 GPU 资源：interactive allocation `60657290`。

只允许：

`srun --jobid=60657290 --overlap --ntasks=1 bash -lc '<command>'`

禁止：

- `sbatch`；
- `salloc`；
- 新 Slurm job；
- 并行两个 GPU 进程；
- 写 `/overflow/htzhu/CARE`；
- validation/Docker upload；
- runtime push；
- MoSAIC/MMRD teacher/prototype/dictionary/multi-backbone。

若 allocation 终止，只能返回 operational block 和精确 resume 点，不能把资源中断解释为科学失败。

## 10. 图视觉交接

```text
diagram_versions_read:
  - SRR-v2
  - SRR-v2.5
  - SRR-v3
  - CARE-MMRD
  - CARE-SRR-Cascade
visual_read_status: PASS_PROJECT_BACKGROUND_IMAGES_VISUALLY_READ
recovered_route_objective: one compact availability-aware multimodal encoder -> pathology-specific proposal -> anatomy-guided local refinement -> component utility arbitration -> bounded per-pathology anchor fallback
```
