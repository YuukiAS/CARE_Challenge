# CARE Challenge: Myocardium 任务汇报

## 1. 任务背景 (Challenge Description)

本任务的核心目标是从心脏磁共振 (CMR) 序列中精确分割心肌病理区域（具体包括瘢痕 Scar 和水肿 Edema）。针对临床实际需求，任务分为两个子课题：

*   **MyoPS (Multi-Sequence Myocardial Pathology Segmentation)**: 利用多序列 CMR 数据（包含 LGE、T2 和 bSSFP）同时分割瘢痕和水肿。
*   **CineMyoPS (Cine Myocardial Pathology Segmentation)**: 挑战仅利用单序列 Cine CMR 数据分割瘢痕区域。

**核心挑战：**
*   **多中心数据差异**：不同医疗机构采集的数据在成像协议和质量上存在显著差异。
*   **序列缺失**：在实际临床中，部分中心可能缺失关键序列（如 T2 或 bSSFP）。
*   **空间失配**：多序列 CMR 图像之间往往存在复杂的空间对齐问题，增加了多模态融合的难度。

**目标标签定义：**
*   瘢痕 (Scar) - 标签值: 2221
*   水肿 (Edema) - 标签值: 1220
*   左心室 (LV) - 标签值: 500
*   心肌 (Myocardium) - 标签值: 200
*   右心室 (RV) - 标签值: 600

**评估指标 (Metrics)：**
所有瘢痕与水肿分割结果以下列两项指标进行评估：
*   **Dice 相似性系数 (Dice Similarity Coefficient, Dice)**：衡量预测与真值的体积重叠程度，取值范围 [0, 1]，越大越好。
*   **豪斯多夫距离 (Hausdorff Distance, HD, mm)**：衡量预测与真值边界的最大偏差距离，单位为毫米，越小越好。

**子任务排行榜 (Leaderboard) 划分：**

| 子任务 | 目标 | 排行榜 |
| --- | --- | --- |
| MyoPS | Scar | Lb1 |
| MyoPS | Edema | Lb2 |
| CineMyoPS | Scar | Lb3 |

**数据集模态完整性统计 (基于 `MyoPS_train`，共 220 例)：**

| 模态组合 | 病例数 | 占比 | 主要来源中心 |
| --- | --- | --- | --- |
| C0 + LGE + T2 (三序列完整) | 80 | 36.4% | CenterB (35), CenterC (45) |
| C0 + LGE (缺 T2) | 24 | 10.9% | CenterE (7), CenterF (9), CenterG (8) |
| LGE only (缺 C0 与 T2) | 116 | 52.7% | CenterA (81), CenterH (35) |
| LGE + T2 (缺 C0) | 0 | 0.0% | — |

> 关键观察：**仅 36.4% 的训练病例为完整三序列**，超过半数为 LGE-only。这直接挑战了原始 MyoPS-Net / U-MyoPS 等论文模型对“完整多序列输入”的隐含假设。

CineMyoPS 子任务仅依赖 cine 单序列数据（`CineMyoPS_train` 共 64 例：center_alpha 40 例、center_beta 24 例），不存在多模态缺失问题，但需要从 4D 时序中精确选取舒张末期 (ED) 帧作为分割输入。

---

## 2. MyoPS-Net 表现分析与改进

### 2.1 表现不佳原因分析
1.  **数据协议不一致**：CARE 数据集存在大量序列缺失（220 例中仅 80 例完整），而原始模型设计基于完整三序列输入。实验表明，LGE-only 情况下的表现远低于完整序列。
2.  **指标定义差异**：原始代码将水肿定义为“水肿 ∪ 瘢痕”，而 CARE 评测要求严格的单类 Dice。这导致水肿指标在字面上看起来极低，但实际上模型具备一定的病理区域识别能力。
3.  **模型实现错配**：当前运行的是包含占位符（补零）的全模型，而非针对三序列优化的变体，导致模型在处理缺失模态时存在计算冗余和干扰。
4.  **实验规模不足**：目前仅完成 Fold 0 训练，且未进行多模型集成（Ensemble），与论文中的五折交叉验证结果存在基准差异。

### 2.2 已完成的改进措施
1.  **定制化 Challenge3 变体**：修改模型输入逻辑，将其调整为专门面向 C0, LGE, T2 的三模态任务，不再依赖缺失的 T1m / T2* 占位符。
2.  **结构精简**：去除了无效的 Mapping 分支（`encoder_mapping` / `decoder_mapping`），解决了因“强行运行全模型”导致的特征错配问题。
3.  **监督策略对齐**：将水肿的监督信号从“并集”改为“精确类”，并同步调整了损失函数（如禁用基于“瘢痕属于水肿”假设的 PI Loss），使训练目标与评测指标完全一致。
4.  **全链路适配**：更新了训练、验证及预测导出脚本，确保整个流水线均在新的 Challenge3 协议下运行。

### 2.3 缺失模态 (T1m / T2*) 的处理变更
| 维度 | 修复前 | 修复后 |
| --- | --- | --- |
| 模型结构 | 5 通道输入 `[C0, LGE, T2, T1m, T2*]`，并保留 `encoder_mapping` / `decoder_mapping` 与 max-fusion | 切换至 Challenge3 变体后退化为 3 通道输入 `[C0, LGE, T2]`，Mapping 编/解码分支整体禁用 |
| 数据落盘 | `T1m` / `T2*` 直接以 `np.zeros_like(LGE)` 写出，并随训练前向传播 | 仍保留零张量文件，但**仅作为文件名兼容占位**（dataloader glob 需要），不参与任何前向计算 |
| Loss / Fusion | 对全零的 mapping 分支计算 segmentation loss、Inclusive loss、PI loss，并参与最终 scar 融合 | mapping 分支全部禁用；scar 融合仅依赖 LGE 通道；PI loss 在 Challenge3 下关闭 |
| 影响 | 无效零信号污染 LGE / T2 特征，扰乱融合并稀释梯度 | 模型彻底不再“看到”不存在的模态，特征通道与监督信号严格匹配 CARE 协议 |

> 备注：对于 CARE 中仅有 LGE（116 例）或缺 T2（24 例）的病例，目前 C0 / T2 通道仍以零图填充进入 3 通道 UNet。该部分尚未做更细粒度的 modality dropout 或 mask-aware 处理，后续可作为优化方向。

---

## 3. U-MyoPS 表现分析与改进

### 3.1 表现不佳原因分析
1.  **病例采样策略缺陷**：原始实现将 3D 病例压成单个中心层进行处理，丢失了大量有效的切片数据。
2.  **训练集选择硬编码**：之前固定使用前 20 个病例，未遵循 CARE 官方划分的五折交叉验证协议。
3.  **维度处理错误**：在结果生成阶段存在 2D/3D 维度混淆，导致配准和变形操作（Warp）出现异常。
4.  **指标计算偏差**：评测脚本使用了固定的分辨率和裁剪参数，未根据每个病例的真实 NIfTI 空间信息进行动态调整。

### 3.2 已完成的改进措施
1.  **3D 采样优化**：引入 `subject_meta.json` 记录所有有效 Z 轴切片，实现按切片采样的全数据利用，不再局限于“中心层”。
2.  **数据流对齐**：接入 CARE 官方的 `splits_MyoPS.json`，支持标准的五折交叉验证训练模式。
3.  **预测链路重构**：重写了 `gen_res` 逻辑，采用逐切片推断并按原空间坐标聚合的方案，解决了维度匹配和空间对齐的 Bug。
4.  **动态指标评估**：修正了评估脚本，使其能够读取原始图像的 Spacing 信息，确保 Dice 和 HD 指标计算的准确性。

### 3.3 缺失模态的处理变更
> U-MyoPS 网络结构本身仅使用 C0 / T2 / DE(LGE) 三个分支，**不涉及 T1m / T2***。因此该模型的“缺失模态”问题特指 CARE 中部分病例缺失 C0 或 T2 的情况。

| 维度 | 修复前 | 修复后 |
| --- | --- | --- |
| 病例选择 | 硬编码 `subjects[:20]`，没有任何模态完整性检查 | 通过 `subject_meta.json` 显式记录 `modalities_present = {c0, t2, de}`，并默认仅保留三序列完整病例参与训练（环境变量 `UMYOPS_TRAIN_REQUIRE_ALL_MODALITIES=1`） |
| 数据落盘 | 缺失模态读到空文件直接报错 | staging 阶段以 `_blank_sitk` 写出零图保证 dataloader 不崩，但其使用范围被 manifest 严格控制 |
| 配准 (Stage1) | 缺失模态被零图喂入 TPS warp，污染配准学习 | 推断阶段读取 `modalities_present`，对缺失模态**跳过 TPS warp**，避免“拿零图配准”这种伪监督 |
| 推断覆盖 | 与训练耦合，缺失病例无法生成结果 | `gen_res` 覆盖全部 staged 病例（含缺模态），不再因模态缺失漏推断 |
| 兜底开关 | —— | 提供 `UMYOPS_TRAIN_REQUIRE_ALL_MODALITIES=0` 的可选项，允许在需要时把零填充病例也送入训练做对照实验 |

---

## 4. CineMyoPS 表现分析与改进

### 4.1 表现不佳原因分析
1.  **模型基准错位**：此前路径使用 nnU-Net v1 的通用分割器，未纳入 CineMyoPS 论文中的运动估计、解剖分割与病理分支的联合训练，难以利用心动周期内的形变信息。
2.  **关键帧与采样策略不当**：将 4D Cine 压成单帧时曾默认取**中间时刻**（更接近收缩末期 ES），与以**舒张末期 ED** 为参照的标签空间不一致，造成显著错配。
3.  **任务与监督口径**：论文管线面向多类病理；CARE Lb3 仅评瘢痕，需在损失与输出上与评测口径对齐（避免沿用全论文 head 的假设）。
4.  **指标解读**：若汇总多类的平均 Dice，会掩盖瘢痕类（紧凑映射下对应 scar）的真实难度；Lb3 应以瘢痕相关指标为主汇报。

### 4.2 已完成的改进措施
1.  **Task026（4D）数据管线**：新增 `Task026_Cine_4D` 导出流程（`prepare_task026_cine_4d.py`、`task026_utils.py`），将 CARE CineMyoPS 转为 **4D cine NIfTI + 3D 标签**，并按挑战赛标签做紧凑重映射；同时生成分通道的 nnU-Net v1 **raw** 任务目录供 planner / 训练读取。默认在完整心动周期内**均匀采样固定帧数**（可由环境变量配置），且 **首帧固定为 t=0（ED）**，替代原先「单帧 + 取中间层」的设定。
2.  **ED 假设校验**：`verify_ed_at_t0.py` 对「第一帧为 ED」做一次性统计门控，降低帧定义错误导致的全链路偏差。
3.  **导出质量门控**：`sanity_check_task026.py` 在导出后对维度、文件对齐与关键元数据做检查，避免 silent corruption 进入训练。
4.  **网络与训练器**：在 `third_party/CineMyoPS` 内新增 `CARECineMyoPSTrainer` 与 `care_cineloss.py`（`CARECineSegLoss`）。网络以 **`CineSegNet` 为基础**，经 `CARECineSegNet` 适配 CARE：**运动分支（encoder + ES-based motion decoder）+ 解剖分割（cardiac_seg，ED 帧）+ 瘢痕病理头（2D UNet；输入为 ED cine、运动场汇总与 ED 解剖特征拼接）**；损失在 CineSeg 组合形式基础上改为 **Lb3 瘢痕监督**，取代单帧 generic nnU-Net baseline。
5.  **评测与产物路径兼容**：预测仍写入统一约定路径下的 `results/predictions/CineMyoPS/fold_X/<case>.nii.gz`，与仓库内统一基准评测衔接；与旧 Task025 相关的脚本保留作对照或历史任务，**Lb3 主路径以 Task026 + CARE trainer 为准**。
6.  **工程配套**：补充 `code/CineMyoPS/README.md`、`sbatch_cinemyops.sh`、`scripts/CineMyoPS/smoke_test.sh` 等用于集群编排与训练前冒烟验证；具体操作见代码库说明，汇报稿不展开命令行。

### 4.3 后续工作
- 完成 **五折交叉验证** 与多 fold 指标汇总，形成可与 Lb1/Lb2 对齐的完整验证结论。
- 视验证表现决定是否加入 **后处理**（连通域、边界平滑）以改善 HD；必要时可将官方 CineMyoPS 预训练权重仅作 **对照实验**（注意类别与域差异）。
