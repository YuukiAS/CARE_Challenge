# Deep Research Prompt — CARE Myocardium Track（2024 至今）

> 用途：直接喂给 deep research agent（如 Perplexity Pro Search、ChatGPT Deep Research、Claude Research、Gemini Deep Research、Elicit、Consensus 等），用于检索我们参加 **MICCAI CARE Challenge 2025 — Myocardium track**（含 MyoPS 与 CineMyoPS 两个子任务）所需的最新文献、方法与可复用资源。
>
> **检索时间窗：2024-01-01 至今**（如某关键工作发表于 2023 末但被 2024 以后的工作高频引用，可保留）。
>
> 请把回答按下面三个 section 严格组织，每条建议都要带：(1) 论文/项目名 + 年份 + venue + 一句话方法摘要；(2) 是否开源（GitHub/HuggingFace/Modelscope 链接）；(3) 与 CARE 任务的具体相关点；(4) 可能的接入难度与预期增益判断。

---

## 0. 项目背景（Agent 必读，决定相关性的判据）

我们正在参赛 **MICCAI 2025 CARE Challenge — Myocardium track**，包含三个 leaderboard：

| Leaderboard | 任务 | 输入 | 输出 | Baseline 现状 |
| --- | --- | --- | --- | --- |
| **Lb1** | MyoPS Scar | C0 + LGE + T2 多序列 CMR（**部分模态可能缺失**） | 心肌梗死（scar） | MyoPS-Net challenge3 变体, scar Dice ≈ 0.50–0.55 |
| **Lb2** | MyoPS Edema | 同上 | 心肌水肿（edema） | 严格 edema Dice ≈ 0.30–0.40 |
| **Lb3** | CineMyoPS Scar | 单一 cine bSSFP 序列（30 帧） | 心肌梗死（scar，**无 LGE**） | nnUNet generic baseline, Dice ≈ 0.26 |

**数据规模**：MyoPS 训练 220 例（其中 80 例三序列完整、24 例 C0+LGE、116 例 LGE-only）；CineMyoPS 训练 64 例（两个中心，每例 30 帧 cine）。

**规则约束**：
1. 允许使用 **pre-trained model**（必须公开可获取）；
2. **不允许** 在训练时混入外部公开数据集（即不能直接拿 MyoPS 2020 / EMIDEC / ACDC / M&Ms 当训练数据）；
3. 灰区：用外部数据 self-pretrain 后 fine-tune 的合规性不明确，**保守应避免**。

**已识别的核心 bottleneck**：
- **B1 — 多序列 CMR 缺模态训练 / 推理**（Lb1/Lb2 主要瓶颈）：220 例里只有 36% 三序列完整，传统多模态分割模型对缺模态敏感。
- **B2 — Cine 序列上的运动建模与帧间一致性**（Lb3 主要瓶颈）：cine 单序列推 scar 的关键是建模心动周期内的运动模式（如 ED→ES 的形变与 strain），单帧 nnUNet 缺这一信息。
- **B3 — 病灶（scar/edema）类别极不平衡**：体素占比 <2%，常规 Dice/CE loss 收敛差。
- **B4 — 跨中心域偏移 + 小样本**：MyoPS 三中心、CineMyoPS 两中心，数据风格与采集协议不一致；总样本量小（64–220）使大模型 fine-tune 风险大。
- **B5 — 心肌细分割（scar/edema 在心肌内的精细定位）**：scar/edema 必须落在心肌区域内，背景预测会显著拉低 HD。
- **B6 — 标注口径与边界质量**：scar/edema 边界主观性强，HD 指标对 outlier 敏感，需要专门的边界感知 loss 或后处理。

---

## 1. 任务一：2024 以来的心肌（MyoPS / CineMyoPS）相关分割模型

请检索并综述 **2024 年至今** 在以下方向的新工作：

### 1.1 心肌病理分割（scar / edema / fibrosis / LGE-based pathology）
- 优先关注同样使用 LGE / multi-sequence CMR 做 scar/edema 分割的论文。
- 重点报告：**MICCAI 2024/2025、MIA、IEEE TMI、Medical Image Analysis、IPMI、ISBI、CVPR/ECCV medical workshop** 上的相关工作。
- 关键词建议：`myocardial scar segmentation`, `myocardial pathology segmentation 2024`, `LGE CMR segmentation`, `multi-sequence cardiac MRI segmentation`, `MyoPS 2020/2024`, `MyoPS challenge follow-up`。

### 1.2 Cine MR 上的心肌运动 / strain / 病理推断（特别针对 LGE-free 推 scar）
- 报告任何用 cine 单序列预测 scar / strain abnormality / fibrosis 的工作。
- 关键词建议：`cine CMR scar inference`, `cine-based pathology segmentation`, `LGE-free scar`, `cardiac strain deep learning 2024`, `cine motion analysis pathology`, `temporal CMR segmentation transformer`。

### 1.3 通用心脏分割架构创新（可迁移到上面两个任务）
- 优先报告：扩散模型用于 cardiac segmentation、Mamba/SSM 用于 cardiac segmentation、3D + temporal transformer、video segmentation 模型用于 cine。
- 但要明确指出"是否在 myocardium / pathology 上有具体验证"，避免给纯 architecture 论文。

**输出格式（每条）**：
```
- [论文名](DOI 或 arXiv link)（年份, venue）
  方法摘要：…
  与 Lb1/Lb2/Lb3 的相关性：…
  开源：是/否（链接）；预训练权重：是/否
  接入难度：低/中/高；预期增益（仅供参考）：…
```

---

## 2. 任务二：针对我们已识别的 bottleneck，2024 以来有哪些 SOTA 解决方案

**对每个 bottleneck（B1–B6），分别列 3–5 条最相关的 2024+ 工作**。

### 2.1 B1 — 多模态 CMR 缺模态训练 / 推理
- 关键词：`missing modality medical image segmentation 2024`, `modality dropout`, `modality-aware segmentation`, `incomplete multi-modal MRI`, `Brats missing modality`（BraTS 缺模态方法常可迁移），`prompt-based modality robustness`。
- 重点关注：modality dropout 训练策略、modality-aware attention、cross-modal distillation、modality reconstruction (用现有模态生成虚拟缺失模态)、SAM/MedSAM 在缺模态情境下的应用。
- 是否有针对 cardiac 多序列（C0/LGE/T2）的专门工作？

### 2.2 B2 — Cine 时序建模 + 运动估计
- 关键词：`cardiac motion estimation deep learning 2024`, `cine MRI temporal segmentation`, `optical flow cardiac MRI`, `voxelmorph cardiac 2024`, `learned registration cardiac`, `4D cardiac segmentation`, `temporal transformer cine`。
- 重点关注：可微分 registration、joint motion + segmentation、cycle-consistency、cardiac strain 估计。
- 是否有可以直接 plug-in 到 V6WithoutIMG / CineMyoPS 风格架构的 motion module？

### 2.3 B3 — 类别极不平衡（小病灶分割）
- 关键词：`small lesion segmentation loss 2024`, `boundary-aware loss`, `Tversky focal cardiac`, `region-mining`, `hard example mining segmentation`, `compound loss medical`。
- 重点关注：boundary-aware loss、Hausdorff loss、unified focal-Tversky 变体、curriculum learning。

### 2.4 B4 — 跨中心域偏移 + 小样本
- 关键词：`domain generalization cardiac MRI 2024`, `cardiac MRI harmonization`, `Fourier-based domain randomization`, `style transfer CMR`, `low-shot cardiac segmentation`, `nnU-Net cross-center fine-tune`。
- 重点关注：在 ACDC / M&Ms / CMRxRecon 上做过 domain generalization 的方法，是否可以用 model-only 方式（不引入外部数据）应用。

### 2.5 B5 — 心肌细分割 + pathology routing
- 关键词：`cascaded cardiac segmentation 2024`, `myocardium-restricted pathology`, `region-of-interest segmentation cardiac`, `two-stage cardiac segmentation`。
- 重点关注：anatomy → pathology 两阶段策略、anatomy-aware loss。

### 2.6 B6 — 边界质量 / HD 优化
- 关键词：`Hausdorff distance loss 2024`, `boundary-aware segmentation`, `topology-preserving cardiac`, `post-processing connected components cardiac`。
- 重点关注：可微 HD loss、形态学后处理 pipeline、test-time augmentation。

**对每个 bottleneck 给一个综述性 paragraph，再列出 3–5 条 paper bullets**（同上格式）。**最重要：明确判断哪些是真的可以拿来用、哪些只是漂亮的 paper**。

---

## 3. 任务三：可用的 pre-trained model 资产盘点

> **重要规则**：CARE Myocardium track 允许 pre-trained model，但**不允许混入外部数据训练**。所以我们关心的不是"什么是大模型"，而是"什么 pre-trained checkpoint 能让我**只在 CARE 数据上 fine-tune**就有显著增益"。
> **不要再列 MedSAM 和 CineMyoPS 百度云 checkpoint**（这两个已知）。

请围绕以下方向检索 **公开可用的 pre-trained model** 或 **pre-trained 数据集 + 训练好的 checkpoint**：

### 3.1 Cardiac-specific 预训练 backbone（最相关）
- 在 **ACDC / M&Ms / M&Ms-2 / CMRxRecon / Decathlon Heart / EMIDEC / MyoPS 2020** 上预训练并**公开发布 checkpoint** 的工作（不是论文，是真的能下载的 checkpoint）。
- 关键词：`pretrained cardiac segmentation checkpoint`, `cardiac foundation model`, `nnUNet ACDC pretrained`, `nnUNet MnMs pretrained release`, `MedNeXt cardiac`, `CMR foundation model 2024`。
- 重点：找到至少 3 个**可直接下载**的 cardiac segmentation checkpoint，并说明类别 mapping 是否兼容（LV/Myo/RV/scar/edema）。

### 3.2 心血管 foundation model
- 关键词：`cardiac foundation model 2024`, `CMR foundation model`, `echocardiography foundation model`（虽然是 echo 但可能转 cine 有用）, `EchoCLIP`, `BiomedCLIP cardiac`。
- 重点：是否有专为 CMR / cine 训练的 foundation model（self-supervised / contrastive），可作为 anatomy backbone。

### 3.3 缺模态友好的预训练
- 关键词：`missing modality pretrained`, `modality-agnostic pretrained 2024`, `flexible-modality medical foundation`, `M3D-LaMed`（多模态 LLM）, `MICCAI BraTS 2024 missing modality winners`。
- 重点：是否有 pre-trained 模型显式设计支持缺模态推理（例如训练时随机 dropout 输入 channel）。

### 3.4 心脏 registration / motion 的预训练资产
- 关键词：`pretrained cardiac registration network`, `VoxelMorph cardiac checkpoint`, `LapIRN cardiac`, `learned registration pretrained 2024`。
- 重点：是否有可直接 plug-in 到 cine motion module 的预训练 registration network。

### 3.5 通用医疗大模型（仅作辅助评估，不是主线）
- MedSAM 2 / SAM2-UNet-Med / SAM-Med3D-2024 / Universeg / IRIS / BMC-VL / RadFM 等。
- **明确指出哪些对 cardiac segmentation 真的有过验证**，避免推销那些只在 lung/liver 上 demo 过的"通用医疗大模型"。

### 3.6 自监督预训练（在 CARE 数据上自己跑 SSL，再 fine-tune）
- 关键词：`self-supervised pretraining medical 2024`, `MAE cardiac MRI`, `SimMIM cardiac`, `contrastive cine MRI`, `SwAV medical 2024`。
- 重点：在 64–220 例数据上做 SSL pretrain 是否有意义？哪些 SSL 框架对小数据友好？

**输出格式（每条）**：
```
- [Checkpoint / Model 名]（论文 link + 下载 link）
  训练数据：…（必须明确，否则没用）
  类别 mapping / 输入要求：…
  许可证：是否允许用于挑战赛 fine-tune
  与 CARE Lb1/Lb2/Lb3 的相关性：…
  接入难度：低/中/高；预期增益（仅供参考）：…
  规则合规性自查：(允许/有风险/不允许)
```

---

## 4. 必须回避的内容（提高检索质量）

请在回答中**明确避免**以下内容，因为它们对我们没有增量信息：

1. ❌ MedSAM / SAM 的通用介绍（已知，且对 cardiac pathology 增益有限）。
2. ❌ CineMyoPS 论文本身（Ding et al., 2025）和它的百度云 checkpoint（已知）。
3. ❌ MyoPS-Net (Qiu 2023) 和 U-MyoPS (Ding 2023) 论文本身（已读）。
4. ❌ 纯 architecture 创新但没在 cardiac pathology 上验证的工作（如纯 CV 的 Mamba SOTA）。
5. ❌ 2023 及更早的论文（除非是 2024+ 工作中高频引用的奠基性工作）。
6. ❌ 任何"花哨但没开源"的方法（我们**只关心 reproducibility**）。

---

## 5. 最终 deliverable 期望

请给我一个 **markdown 报告**，按 section 1–3 组织。每个 section 末尾给一段 **"For CARE team — Top-3 picks"**，明确推荐三件最值得我们立即试的事，并标注：
- 投入估计（人/天）；
- 风险等级（低/中/高）；
- 预期对哪个 leaderboard 增益最大。

最终我会基于这份报告决定：
- 哪些 pre-trained checkpoint 立即下载并加进 ablation；
- 哪些方法值得让 Codex agent 立即开发；
- 哪些方向我们直接放弃（节省精力）。

请尽量给真实可获取的链接（GitHub / arXiv / HuggingFace / Modelscope / OpenReview / 百度网盘），避免 hallucinate。如果某条信息不确定，请明确标注 "未验证"。
