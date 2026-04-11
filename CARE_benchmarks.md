# CARE 基准论文笔记

以下三篇论文按**发表年份**排序（2023 年两篇：Ding et al. 在前，Qiu et al. 在后；2025：Ding et al.）。内容来自文献阅读笔记，已去除导出元数据与插件落款。

---
## 1. U-MyoPS — Unaligned Multi-sequence Myocardial Pathology Segmentation

**Ding et al., 2023**（多序列未对齐场景下的心肌瘢痕/水肿分割）

### 论文主要解决的问题

这篇论文聚焦于 **多序列心脏磁共振（MS-CMR）下的心肌病理分割**，目标是实现对 **瘢痕（scar）和水肿（edema）** 的**全自动分割**。核心难点主要有三类：

1. **多序列之间天然不对齐**
    

- 不同序列（如 bSSFP、LGE、T2）来自同一受试者，但采集时存在位置偏差、形变差异。
    
- 如果直接融合这些序列，像素级语义会错位，影响病灶分割。
    

2. **病灶分割本身困难**
    

- 心肌病灶区域小、形态不规则、边界模糊。
    
- 单一序列对某一类病灶敏感，但信息不完整，因此需要跨序列互补。
    

3. **病灶应受心肌解剖先验约束**
    

- 瘢痕和水肿发生在心肌区域内，如果没有解剖结构先验，模型容易产生假阳性或漏检。
    

论文的核心思想是：**把多序列配准、心肌结构提取和病灶分割放到统一框架中联合建模**，从而让“对齐后的多序列信息”和“心肌结构先验”一起服务于病理分割。

文中对多序列未对齐问题的描述和解决思路很明确：

> The size of each extracted image is H × W . To align these images, we can set one of them as the common reference image (CRI), and register the rest images to it. For convenience, we set ILG E as the CRI in this section.

(Ding 等, 2023, page 3473)

同时，论文强调对齐对分割的重要性：

> The reason is that MvMM+nn-Unet utilized aligned MS-CMR images, and the pathological and anatomical information from the aligned images could complement each other for segmentation.

(Ding 等, 2023, page 3479)

以及作者方法进一步说明：

> This is because U-MyoPSbLT aligned MS-CMR images for MyoPS. Segmentation methods could obtain more robust pixel-wise classification based on the intensity information from aligned scarring and edema regions.

(Ding 等, 2023, page 3479)

---

### 提出的整体架构：U-MyoPS

论文提出的方法叫 **U-MyoPS**，本质上是一个面向 **Unaligned Multi-sequence Myocardial Pathology Segmentation** 的统一框架。它不是简单先配准、再分割的串联流程，而是把以下几部分结合起来：

- **多序列配准模块**
    
- **解剖结构提取模块**
    
- **病灶分割模块（带先验）**
    
- **多序列特征融合机制**
    

作者在配准部分明确说明了核心组件：

> In U-MyoPS, we introduce three encoders (EbSSF P , ELG E and ET 2) to capture underlying structural information from I, and two registration heads (RbSSF P and RT 2) to estimate TPS transformations for registration.

(Ding 等, 2023, page 3473)

并使用 TPS 变换完成跨序列对齐：

> A TPS transformation is parameterized via a grid of control points [25]. Briefly, we set an imaginary grid of control points on IbSSF P and IT 2, and warp the images according to the displacements of control points.

(Ding 等, 2023, page 3473)

#### 1\. 多序列配准模块

##### 目标

把 bSSFP、T2 对齐到 LGE（LGE 作为公共参考图像 CRI）。

##### 做法

- 为三个序列分别设置编码器，提取结构信息。
    
- 为 bSSFP 和 T2 设置注册头，预测 TPS 控制点位移。
    
- 将 bSSFP、T2 通过 TPS 变换 warp 到 LGE 坐标系。
    

训练细节中，作者给了 TPS 网格设置：

> For MS-CMR image registration, TPS grids were initially set with 4 × 4 equally-spaced control points

(Ding 等, 2023, page 3478)

以及训练策略：

> We first jointly trained the multi-sequence registration and anatomical structure extraction with the hybrid loss [see (7)] by setting λ to 0.1. After converging, we froze the parameters for multi-sequence registration and anatomical structure extraction, and then optimized the parameters of prior-aware sub-network by minimizing pathology segmentation loss [see (8)].

(Ding 等, 2023, page 3478)

##### 意义

这一步让多序列在空间上更一致，从而支持更可靠的像素级融合。论文可视化也表明，对齐前后 LV epicardium 和病灶轮廓明显改善：

> One can that observe LV epicardium contours of original source images are initially misaligned [see (c)], and become aligned after registering [see (d)].

(Ding 等, 2023, page 3473)

---

#### 2\. 解剖结构提取模块

这部分的作用是从多序列图像中抽取更稳定的心肌及相关结构信息，为后续病灶分割提供结构基础。论文把它和配准一起先联合训练，说明作者并不把“结构提取”看作附属任务，而是整个框架中的关键中间层。

从实验结果看，作者指出一些设计是为了提升**myocardium structure extraction**，例如 MSF 的引入：

> Notably, as MSF was also proposed to improve the myocardium structure extraction for MyoPS, one can refer to Section III-F.2 for the ablation study of MSF on myocardium structure extraction.

(Ding 等, 2023, page 3480)

这说明 U-MyoPS 的一个重要思想是：**先得到更合理的心肌结构表征，再利用这种结构信息约束病灶定位**。

---

#### 3\. 先验感知的病灶分割子网络

这是最终输出瘢痕和水肿分割结果的模块。其关键点在于：**病灶分割不是孤立进行，而是利用心肌先验（myocardium prior information）**。

作者在消融实验中清楚说明了这个先验的重要性：

> Without SPG, U-MyoPSw/o SPG bLT suffered performance degradation.

(Ding 等, 2023, page 3480)

并解释原因：

> This is because the scarring and edema regions are in myocardium. It would turn out to be harder for U-MyoPSw/o SPG bLT to find more pathology regions without myocardium prior information.

(Ding 等, 2023, page 3480)

##### 这意味着什么？

- U-MyoPS 会利用“病灶位于心肌内部”这一医学先验；
    
- 相比纯语义分割网络，它减少了不合理预测；
    
- 对小病灶、边界模糊区域尤其有帮助。
    

---

#### 4\. 多序列融合机制：MSF

论文中特别强调了 **MSF** 的作用。它不是普通的拼接或 max-fusion，而是考虑了多序列错位后再做融合的问题。作者认为如果直接融合未对齐的特征，不同序列在同一空间点上的语义可能并不对应。

原文对此说明得很直接：

> Initially, the semantic information of FbSSF P , FT 2 and FLG E in q could be incorrectly integrated via existing fusion operations, such as channel-wise concatenation [40] and max-fusion [41].

(Ding 等, 2023, page 3481)

而 MSF 的改进在于先将特征变换到一致空间再融合：

> Whereas MSF could fuse FbSSF P (or FT 2) with FLG E by transforming FbSSF P (or FT 2) into F ̃bSSF P (or F ̃T 2). Therefore, MSF provided a more appropriate and reliable way to fuse multi-sequence information.

(Ding 等, 2023, page 3481)

##### 作用总结

- 避免“错位特征硬融合”；
    
- 提高多序列互补信息利用效率；
    
- 既改善结构提取，也帮助病灶分割细节。
    

作者也在消融中指出，使用 MSF 后分割和结构提取更稳健：

> The underlying reason is that U-MyoPSbLT obtained more plausible myocardium structures by using MSF (see Section III-F.2), which facilities segmentation details.

(Ding 等, 2023, page 3480)

---

### 可以怎样理解这套架构

可以把 U-MyoPS 理解成一个 **“先对齐，再结构化理解，再带先验分割”的统一系统**：

#### 输入

- bSSFP
    
- LGE
    
- T2
    

#### 中间过程

1. **编码器提取各序列结构信息**
    
2. **以 LGE 为参考进行 TPS 配准**
    
3. **在对齐基础上做多序列特征融合（MSF）**
    
4. **提取心肌结构 / 解剖先验**
    
5. **利用心肌先验做瘢痕与水肿分割**
    

#### 输出

- scar segmentation
    
- edema segmentation
    

---

### 这套方法相对已有方法的核心改进

#### 相比单序列分割

单序列方法只能看到某一种对比度信息，信息不足。U-MyoPS 利用了多序列互补信息，因此对 scar / edema 都更稳健。

#### 相比“先独立配准，再喂给分割网络”

作者认为直接使用外部预配准方法不如在框架内部联合建模。文中结果显示，U-MyoPS 优于基于预对齐图像的若干方案：

> U-MyoPSbLT achieved better performance than the semantic segmentation method (i.e., MvMM+nn-Unet and MvMM+AWSnet) which consumed pre-aligned MSCMR images.

(Ding 等, 2023, page 3479)

#### 相比普通多模态特征融合

作者认为直接 concat 或 max-fusion 会把不对应位置的语义混在一起；MSF 通过先对齐特征再融合，使跨序列信息整合更可靠。

---

### 论文实验结论的主线

从你给出的这篇论文整体结果看，作者想证明三件事：

#### 1\. 配准是必要的

对齐后的多序列信息比未对齐输入更有利于病灶分割。

> One of the reasons is that U-MyoPSbTL aligned MS-CMR for segmentation.

(Ding 等, 2023, page 3479)

#### 2\. 心肌先验是必要的

如果去掉 SPG，性能明显下降，尤其是敏感度。

> compared to U-MyoPSbLT, U-MyoPSw/o SPG bLT decreased Sen by almost 4% ( p < 0.05) and 5% ( p = 0.01) for scar and edema segmentation, respectively.

(Ding 等, 2023, page 3480)

#### 3\. 合理的多序列融合方式是必要的

MSF 让模型不仅数值更稳，也能得到更合理的结构和细节。

> Therefore, MSF provided a more appropriate and reliable way to fuse multi-sequence information.

(Ding 等, 2023, page 3481)

---

### 一句话概括这篇论文

**这篇论文解决的是：如何在未对齐的多序列心脏 MRI 中，联合利用跨序列互补信息和心肌结构先验，实现更准确、更自动化的心肌病灶分割。**

其提出的 **U-MyoPS** 架构核心由以下三点组成：

- **用 TPS 做多序列可学习配准**
    
- **用 MSF 做对齐感知的特征融合**
    
- **用心肌先验引导 scar / edema 分割**
    

---

### 这篇文章本身有开源吗？

**有，作者公开了代码。**

> Source codes has been released publicly at https://github.com/NanYoMy/myops.

(Ding 等, 2023, page 3478)

---

### 文中列出的 GitHub 仓库汇总

> 说明：按论文中脚注/链接出现的项目汇总；**加粗行**表示这篇论文作者自己的开源仓库。

| 类型 | 项目 | GitHub 链接 | 作用 |
| --- | --- | --- | --- |
| **作者开源** | **U-MyoPS / myops** | **https://github.com/NanYoMy/myops** | **本文方法的官方代码** |
| 对比方法 | PSN / UNet-family | https://github.com/ShawnBIT/UNet-family | 单序列分割相关实现 |
| 对比方法 | nnU-Net | https://github.com/MIC-DKFZ/nnUNet | 通用分割基线 / 对比方法 |
| 对比方法 | AWSnet | https://github.com/soleilssss/AWSnet/tree/master | 粗到细的 MyoPS 对比方法 |
| 对比方法 | ANTsPy | https://github.com/ANTsX/ANTsPy | 配准对比方法 |
| 对比方法 | VoxelMorph | https://github.com/voxelmorph/voxelmorph | 配准对比方法 |
| 对比方法 | MvMM-RegNet | https://github.com/xzluo97/MvMM-RegNet | 配准对比方法 |

---
## 2. MyoPS-Net — 五序列 CMR 灵活组合的端到端 MyoPS

**Qiu et al., 2023**（*Medical Image Analysis*；跨模态融合、心肌先验与病灶包含关系）

---

### 论文主要解决的问题

这篇论文关注的是**心肌病灶分割**（myocardial pathology segmentation, MyoPS），具体是从**多序列心脏磁共振 CMR** 中自动分割：

- **心肌瘢痕**（scar）
    
- **心肌水肿**（edema）
    

作者强调，这个任务在临床上很重要，因为它是心肌梗死诊断和治疗规划的前提之一。

论文对问题动机的概括非常明确：

> Myocardial pathology segmentation (MyoPS) can be a prerequisite for the accurate diagnosis and treatment planning of myocardial infarction.

(Qiu 等, 2023, page 1)

同时，作者指出困难主要来自：

- 单张图像信息不足或边界模糊
    
- 病灶形态和表现多样
    
- 多序列信息难以有效融合
    
- 真实临床里经常**模态缺失**，例如没有 LGE 或没有 mapping 序列
    

论文摘要里直接点出了这个临床痛点：

> Note that in practical clinics, the subjects may not have full sequences, such as missing LGE CMR or mapping CMR scans.

(Qiu 等, 2023, page 1)

所以，这篇论文要解决的核心问题可以概括为：

#### 1\. 如何融合多序列 CMR，提高 scar / edema 分割精度

作者考虑了 5 种临床可用序列：

- bSSFP（C0）
    
- LGE
    
- T2
    
- T1 mapping
    
- T2\* mapping
    

这些序列提供的信息不同，互补性很强。

#### 2\. 如何在模态组合不固定、甚至缺失模态时仍能工作

这是论文非常突出的贡献点：作者不是只做“全模态最好结果”，而是强调**灵活组合**与**临床可用性**。

#### 3\. 如何把解剖和病理先验融入分割

作者引入了两个关键先验：

- 病灶出现在**心肌内部**
    
- **scar 位于 edema 内部**
    


---


### 提出的整体架构：MyoPS-Net

作者提出了一个端到端网络 **MyoPS-Net**。摘要中这样定义：

> In this work, we develop an end-to-end deep neural network, referred to as MyoPS-Net, to flexibly combine five-sequence cardiac magnetic resonance (CMR) images for MyoPS.

(Qiu 等, 2023, page 1)

方法总览部分也明确说：

> Fig. 2 provides an overview of the proposed MyoPS-Net that can combine different CMR images, such as C0, LGE, T2, T1 mapping and T2\* mapping CMR images for MyoPS. MyoPS-Net is an end-to-end architecture consisting of a cross-modal feature fusion module (Section 3.1), two assisting modules for imposing myocardium prior and consistency (Section 3.2) and pathology inclusiveness constraints (Section 3.3).

(Qiu 等, 2023, page 3)

也就是说，**MyoPS-Net** 的核心由三部分组成：

1. **Cross-Modal Feature Fusion (CMFF)**：跨模态特征融合模块
    
2. **Myocardium Prior and Consistency (MPC)**：心肌先验与一致性模块
    
3. **Pathology Inclusiveness (PI)**：病灶包含关系约束
    

下面分别讲。


---


### 一、CMFF：跨模态特征融合模块

这是主干架构，解决“多序列怎么融合”的问题。

作者的出发点是：不同序列对不同病灶的作用不同，例如：

- **LGE** 对 scar 很关键
    
- **T2** 对 edema 更关键
    
- mapping 也能提供补充病理信息
    

论文原文：

> Each of the multi-sequence CMR images has a specific influence on the final results of MyoPS.

(Qiu 等, 2023, page 3)

> For example, LGE CMR is promising in discriminating myocardial scars, but it also provides complementary information for edema segmentation.

(Qiu 等, 2023, page 3)

#### CMFF 的做法

CMFF 的工作方式是：

- 为不同 CMR 序列设置编码器，抽取各自特征
    
- 在多尺度层面进行跨模态特征融合
    
- 再将融合后的特征送入针对特定病灶的解码器
    

作者概括为：

> We propose a cross-modal feature fusion (CMFF) module to fuse multi-sequence information.

(Qiu 等, 2023, page 3)

> CMFF is the main architecture of MyoPSNet, as Fig. 2 shows, and is designed to effectively extract the features contained in the CMR images (via CMR encoders), and fuse them for pathology segmentation (via scar/ edema decoders).

(Qiu 等, 2023, page 3)

#### 融合方式

CMFF 主要采用两种操作：

- **pixel-wise max operation**
    
- **skip connection**
    

原文：

> For feature fusion, CMFF adopts two operations, namely max operation and skip connection.

(Qiu 等, 2023, page 3)

其思想是：对某个序列的分支，融合“其他序列”的同层特征，帮助当前分支利用跨模态互补信息。

#### 编码器/解码器设计

在本文设置中，作者实际用于病灶分割的序列是：

- LGE
    
- T2
    
- mappings（T1 mapping + T2\* mapping）
    

并采用：

- 一个 LGE encoder
    
- 一个 T2 encoder
    
- 一个 mappings encoder
    

原文：

> In our application, we have four CMR sequences to perform pathology segmentation, i.e., LGE, T2, T1 mapping and T2\* mapping CMR. We adopt three encoders for these four CMR sequences, i.e., one for LGE, another for T2 and a third for mappings (T1 mapping and T2\* mapping), to extract pathological features.

(Qiu 等, 2023, page 4)

作者还特别强调，**解码器不是一刀切的**，而是按临床知识和实验结果为不同序列配置更适合的病灶输出头。最终采用的是：

- **LGE → scar decoder**
    
- **T2 → edema decoder**
    
- **mapping → scar decoder**
    

原文：

> For example, in this work we propose to couple a scar decoder to LGE CMR, an edema decoder to T2 CMR, and a scar decoder to mapping CMR according to the clinical knowledge and experimental results from Section 4.3.

(Qiu 等, 2023, page 4)

这是这篇论文一个很有意思的点：**不是让每个序列都同时分 scar 和 edema**，而是让不同序列承担更擅长的任务。


---


### 二、MPC：心肌先验与一致性模块

这个模块解决“病灶怎么更准确定位”的问题。

因为 scar 和 edema 都应该位于**心肌区域内**，所以作者认为应该显式加入“心肌”这一解剖先验，而不是像很多两阶段方法那样先独立分心肌，再裁剪 ROI。

作者写道：

> Since scars and edema lie in the myocardium, it is straightforward to consider the myocardium as a prior.

(Qiu 等, 2023, page 4)

#### MPC 的设计

作者把 5 个序列直接拼接输入一个 U-Net backbone，预测包含：

- myocardium
    
- left ventricle
    

信息的概率图 $\psi_{MPC}$，然后把这个概率图再拼到病灶分割分支输入里。

原文：

> The input of the MPC module, as shown in Fig. 2, is obtained by directly concatenating these five-sequence images

(Qiu 等, 2023, page 4)

> Therefore, the MPC module which employs U-Net (Ronneberger et al., 2015) as the backbone can merge distinct features of cardiac structure from the five images and achieve the probability map containing the myocardium (Myo) and left ventricle (LV) information, which is represented as ψMPC.

(Qiu 等, 2023, page 4)

这样做的意义是：

- 病灶网络获得明确的心肌定位提示
    
- 有助于把预测限制在更合理的解剖区域
    

#### 一致性约束

作者进一步设计了一个**consistency loss**，约束 MPC 输出的心肌概率与各个 scar/edema 分支中的心肌相关概率保持一致。

原文：

> Therefore, we propose a consistency loss on the MPC module, to regularize the invariability of the myocardium.

(Qiu 等, 2023, page 4)

这里本质上是用**解剖一致性**来约束病灶预测。


---


### 三、PI：病灶包含关系约束

这是论文另一个关键先验：**scar 在 edema 内部**。

作者直接写道：

> As shown in Fig. 4, scars lie inside of edema.

(Qiu 等, 2023, page 4)

基于此，作者提出了 **pathology inclusiveness loss**，把这种空间关系作为正则项。

#### 为什么有用？

因为 scar 和 edema 不是完全独立的类别，它们有明确的拓扑/空间关系。把这种病理知识融入训练，可以减少不合理预测。

作者说：

> To embed this prior knowledge, we introduce a pathology inclusiveness (PI) loss in the MyoPS-Net which can be applied to both labeled and unlabeled data.

(Qiu 等, 2023, page 4)

这点也很重要：  
PI loss 不只适用于监督学习，还可以用于**半监督设置**。

#### 两种形式

作者给了两套定义：

1. **有标注数据**上的 inclusiveness loss
    
2. **无标注数据**上的 inclusiveness loss
    

因此方法不仅适合 fully supervised，也能自然扩展到 semi-supervised。


---


### 四、总体损失函数

对于有标注数据，论文整体 loss 为：

$$\mathcal{L}^L = \mathcal{L}_{seg} + \lambda_{con}\mathcal{L}_{con} + \lambda_{inc}\mathcal{L}_{inc}^L$$

原文：

> The overall loss function for labeled data is defined as,  
> $\mathcal{L}^L = \mathcal{L}_{seg} + \lambda_{con}\mathcal{L}_{con} + \lambda_{inc} \mathcal{L}^L_{inc}$

(Qiu 等, 2023, page 5)

其中包括：

- 分割损失
    
- 心肌一致性损失
    
- 病灶包含关系损失
    

对无标注数据则去掉分割损失，只保留一致性和包含关系约束。


---


### 五、这篇论文的方法到底“新”在哪里？

可以把贡献总结成 4 点：

#### 1\. 灵活的多序列组合

论文不是只研究“全模态输入”，而是特别面向临床现实中常见的**模态缺失**场景。

原文：

> This architecture can tackle different numbers of CMR images and complex combinations of modalities, with output branches targeting specific pathologies.

(Qiu 等, 2023, page 1)

#### 2\. 针对病灶类型的专门解码器设计

不是每个模态都输出所有病灶，而是按序列特点选择 scar / edema decoder。

#### 3\. 引入心肌先验

通过 MPC 模块把病灶定位限制在心肌区域附近。

#### 4\. 引入 scar ⊂ edema 的病理关系

通过 PI loss 把病理空间关系编码到训练中。


---


### 六、论文考虑了哪些实际临床场景？

作者非常明确地设计了 4 种应用场景。

原文：

> Therefore, there are four scenarios for practical usage of the proposed MyoPS-Net, as follows.

(Qiu 等, 2023, page 5)

这 4 种分别是：

#### 1\. MyoPS-Net / MyoPS-Net-F

- 训练：完整五序列
    
- 测试：完整五序列
    

#### 2\. MyoPS-Net-L

- 训练：C0 + LGE + T2
    
- 测试：同样三序列
    
- 适合缺失 mapping 的情况
    

#### 3\. MyoPS-Net-M

- 训练：C0 + T2 + T1 mapping + T2\* mapping
    
- 测试：同样四序列
    
- 适合缺失 LGE 的情况
    

#### 4\. MyoPS-Net-mix

- 用多种组合混合训练
    
- 可以在不同组合上统一测试
    

这个设计很贴近临床：不是强制每位病人都必须有相同采集协议。


---


### 七、实验结果说明了什么？

#### 1\. 单序列结果：不同模态擅长不同任务

作者先验证了不同序列的单独作用：

- **LGE** 对 scar 最有效
    
- **T2** 对 edema 最有效
    
- **mapping** 单独效果较弱，但可提供补充信息
    

例如论文中总结：

> As for LGE CMR, both networks achieved evidently better Dice scores on scar segmentation than the other two sequences.

(Qiu 等, 2023, page 6)

> For T2 CMR, its edema segmentation was reliable by both two models, but the scar segmentation had a great drop in Dice scores.

(Qiu 等, 2023, page 6)

> For mapping CMR, the segmentation of either two types of pathologies was not accurate enough, thus more information from other sequences would be needed for reliable MyoPS.

(Qiu 等, 2023, page 6)

这就解释了为什么作者最终选择：

- LGE 做 scar decoder
    
- T2 做 edema decoder
    
- mapping 做 scar decoder
    

#### 2\. 架构消融：三模块都有贡献

作者做了模块消融，最终完整模型最好。

论文总结道：

> Finally, integrating the proposed three modules, we had the proposed MyoPS-Net, which achieved the best Dice scores and HDs for MyoPS.

(Qiu 等, 2023, page 8)

#### 3\. 模态缺失情况下仍然有效

MyoPS-Net-L、MyoPS-Net-M、MyoPS-Net-mix 都有竞争力，说明框架对实际临床场景具有适应性。

#### 4\. 在公开数据集上达到 SOTA 级别

作者写道：

> The experimental results proved that the proposed MyoPS-Net-L achieved comparable MyoPS performance towards the state-of-the-art results.

(Qiu 等, 2023, page 10)


---


### 八、用一句话概括这篇论文

如果要一句话概括：

**这篇论文提出了一个能够灵活处理多序列/缺失序列 CMR 的端到端病灶分割框架，通过跨模态特征融合、心肌解剖先验和 scar-in-edema 病理关系约束，提高心肌瘢痕与水肿分割的准确性和临床可用性。**


---


### 文中列出的 GitHub 仓库汇总

> 以下为论文/摘要中指向的代码仓库；**加粗行**为官方实现。

| 论文/方法 | Repo | 说明 | 开源状态 |
| --- | --- | --- | --- |
| **MyoPS-Net** | **https://github.com/QJYBall/MyoPS-Net** | **论文摘要中明确给出的官方代码仓库** | **已开源** |

---

## 3. CineMyoPS — 仅基于 Cine CMR 的瘢痕与水肿联合分割

**Ding et al., 2025**（*IEEE TMI*；运动估计、解剖分割与时间聚合）

---

### 论文主要解决的问题

这篇论文要解决的是：

**能不能只用 cine CMR（电影心脏磁共振）这一种快速、无对比剂的序列，自动分割心肌梗死相关病灶，包括 scar（瘢痕）和 edema（水肿）？**

传统上，心肌梗死（MI）的病灶评估通常依赖多序列 CMR：

- **LGE** 用来识别瘢痕
    
- **T2w** 用来识别水肿
    

但这些序列有几个明显问题：

1. **采集时间长**
    
2. **LGE 需要注射对比剂**
    
3. **对急性重症患者不够友好**
    
4. **钆对比剂存在潜在风险和争议**
    

论文明确指出了这一临床动机：

> Although combining complementary information from multi-sequence CMR is useful, acquiring these sequences can be time-consuming and prohibitive, e.g., due to the administration of contrast agents. Cine CMR is a rapid and contrast-free imaging technique that can visualize both motion and structural abnormalities of the myocardium induced by acute MI.

(Ding 等, 2025)

也就是说，作者想用 **cine CMR 替代部分传统多序列检查能力**，做到：

- 不打对比剂
    
- 只靠 cine
    
- 同时分割 **scar + edema**
    
- 并且是**全自动**
    

论文还强调这是其创新点之一：

> To the best of our knowledge, CineMyoPS is the first fully automatic network for joint scars and edema segmentation from cine CMR images.

(Ding 等, 2025)


---


### 论文的核心思路

作者认为，虽然 cine CMR 没有 LGE/T2w 那样直接显示病灶的对比，但它仍然包含与心梗相关的三类重要信息：

1. **运动信息（motion）**
    

梗死区域的运动异常、壁运动减弱

2. **解剖结构信息（anatomy）**
    

心梗会导致心肌壁变薄、左室重构

3. **纹理信息（texture）**
    

cine 图像也可能包含一定的 T1/T2 相关表现

因此，他们提出一个端到端网络，把这些信息结合起来做病灶分割。


---


### 提出的整体架构：CineMyoPS

论文提出的总体框架叫 **CineMyoPS**。作者在文中这样概括：

> Therefore, we present a new end-to-end deep neural network, referred to as CineMyoPS, to segment myocardial pathologies, i.e., scars and edema, solely from cine CMR images.

(Ding 等, 2025)

并且其结构由三个模块组成：

> Fig. 2 shows the network architecture of CineMyoPS, which consists of three modules: a myocardial motion estimation module (see Section II-A), an anatomy segmentation module (see Section II-B), and a MyoPS module (see Section IIC).

(Ding 等, 2025)


---


#### 1\. 模块一：心肌运动估计模块

##### 作用

这个模块从 cine 序列中提取**心肌运动信息**。

作者将 ED（舒张末期）帧设为参考帧，对每一帧估计其相对 ED 的位移场 DDF（dense displacement field）。

论文原文：

> We set the end-diastolic (ED) frame of I as a common reference image (i.e., Ir), and introduce a network to estimate the motion between Ir and each Ii.

(Ding 等, 2025)

##### 形式化定义

运动模块预测：

$$\Phi_i = F_{motion}(I_r, I_i)$$

其中 $\Phi_i$ 是第 $i$ 帧相对于参考帧的位移场。

然后用这个位移场把当前帧变换到参考空间：

$$\tilde I_i = I_i \otimes \Phi_i$$

##### 训练目标

运动模块主要有两部分损失：

- 图像重建误差：让变换后的帧接近参考帧
    
- 平滑正则：约束位移场的平滑性
    

对应论文中的：

$$L_{motion} = \sum_i MSE(\tilde I_i, I_r)$$

和

$$L_{smooth} = \sum_i \|\nabla \Phi_i\|_2^2$$

##### 直观理解

这个模块的目标是回答：

- 心肌每个位置在整个心动周期里怎么动？
    
- 哪些区域动得不正常？
    

因为 infarct 区域通常运动减弱，所以这是病灶判断的重要依据。


---


#### 2\. 模块二：解剖分割模块

##### 作用

这个模块负责从 cine 图像中提取**解剖结构信息**，例如心肌轮廓等。

论文中指出：

> MI often induces geometric remodeling of the left ventricle, leading to myocardial wall thinning [32]. We introduce an anatomy segmentation module to extract myocardial structures from the cine CMR sequences.

(Ding 等, 2025)

##### 监督方式

这个模块使用 U-shaped segmentation subnetwork（本质上是 U-Net 风格结构）。

不过一个实际问题是：  
cine 一整个序列有 25–30 帧，如果每帧都标注解剖结构，非常费时。

所以作者只标注 **ED 帧**，然后引入了一个**一致性损失（consistency loss）**，约束其它时间帧的解剖分割与参考帧保持一致。

论文原文：

> However, delineating all frames in a cine CMR sequence is time-consuming, as each sequence typically contains 25 to 30 frames. To address this, we delineate only the anatomical label of the ED frames, and introduce a consistency loss to regularize the segmentation results across the cardiac cycle.

(Ding 等, 2025)

##### 一致性损失的核心思想

对任意一帧 $I_i$，先预测其解剖分割 $\hat L_i^a$，再用运动场 $\Phi_i$ 把它变换到参考帧空间，要求它和参考帧分割 $\hat L_r^a$ 保持一致。

作者写道：

> we assume the anatomy of Ii (i.e., Lˆa i ), should be consistent with that of Ir (i.e. Lra), after transforming it with Φi.

(Ding 等, 2025)

一致性损失采用 cosine distance：

$$L_{cons} = 1 - cos(\hat L_i^a \otimes \Phi_i, \hat L_r^a)$$

##### 这个设计为什么重要？

因为它把：

- **运动估计**
    
- **解剖分割**
    

绑在一起联合学习。  
运动场更准，可以帮助多帧解剖一致；解剖分割更准，也能反过来帮助运动学习。

论文中对此有明确说明：

> Given that both modules rely on structural features, we introduce a consistency loss to improve the feature extraction of the two modules.

(Ding 等, 2025)


---


#### 3\. 模块三：MyoPS 病理分割模块

##### 作用

这是最后真正输出 **scar / edema** 的模块。

它把三类特征融合起来：

- motion：$\Phi_i$
    
- anatomy：$\hat L_i^a$
    
- texture：$I_i$
    

论文原文：

> We introduce a MyoPS module that integrates these features to segment scarring and edema areas.

(Ding 等, 2025)

##### 输入方式

对第 $i$ 帧，MyoPS 模块输入的是：

$$[\Phi_i,\ \hat L_i^a \otimes \Phi_i,\ I_i \otimes \Phi_i]$$

也就是：

- 运动特征直接使用
    
- 解剖和纹理先通过运动场对齐到参考空间
    
- 再进行拼接输入
    

作者解释这么做是为了：

> The MyoPS module transforms the anatomy (Lˆa i ) and texture Ii by the motion field (Φi) to mitigate spatial misalignment with the reference image Ir.

(Ding 等, 2025)

##### 时间序列聚合策略

这是论文架构的另一个关键点。

每一帧都可以得到一个病灶预测结果 $\hat L_i^p$，然后把整个心动周期内的这些结果做聚合，得到最终分割：

$$\hat L^p = Softmax(conv(\sum_i \hat L_i^p))$$

对应论文原文：

> Furthermore, the MyoPS module can aggregate time-series information for segmentation. Given n sets of Φi, Lˆa i , and Ii, the module generates n potential results across the cardiac cycle. These time-series results are subsequently integrated to obtain the final segmentation

(Ding 等, 2025)

##### 直观理解

这一步是在利用 cine 的“电影”特性，而不是把它当成单张图像：

- 某一帧可能不明显
    
- 但综合多个时相，病变模式更稳定
    
- 从而提高 scar / edema 分割准确性
    


---


### 整体训练方式

CineMyoPS 是一个**端到端联合训练**框架。

论文明确写到：

> Finally, we jointly train the myocardial motion estimation, anatomy segmentation, and MyoPS modules in an end-to-end manner.

(Ding 等, 2025)

总损失函数是：

$$L = L_{MyoPS} + \lambda_1 L_{anatomy} + \lambda_2 L_{cons} + \lambda_3 L_{motion} + \lambda_4 L_{smooth}$$

这表示模型同时优化：

- 病灶分割
    
- 解剖分割
    
- 时序一致性
    
- 运动估计
    
- 运动场平滑性
    


---


### 这篇论文的方法亮点

#### 1\. 只用 cine CMR 做 joint scar + edema segmentation

这是论文最主要的定位。  
现有很多非增强方法只关注 scar，而作者要同时做 scar 和 edema。

> existing cine CMR-based methods primarily focus on scar segmentation. Limited attention has been paid to edema pathology

(Ding 等, 2025)


---


#### 2\. 显式建模 motion + anatomy + texture

不是简单把整段 cine 喂给时空网络，而是把病理相关因素显式拆开：

- motion
    
- anatomy
    
- texture
    

然后再组合。


---


#### 3\. 用 consistency loss 联合约束运动和解剖

这点比较有特点。  
它有点像联合学习 / co-training 的思想，让两个模块互相约束。


---


#### 4\. 在参考帧空间中做对齐和分割

先用运动场把各帧对齐到 ED 参考空间，再做病灶分割，有利于消除时相间空间错位。


---


#### 5\. 利用整个心动周期做 time-series aggregation

不是只看单帧，而是聚合多帧结果。


---


### 消融实验告诉了我们什么？

#### 1\. 用多少帧最好？

作者做了 frame interval study，结论是：

> The results indicate that CineMyoPS initially improved with an increasing number of frames and reached a plateau when 4/6 of the total frames were used.

(Ding 等, 2025)

所以后续实验选用 **4/6 的心动周期帧数**，在信息量和计算效率之间较平衡。


---


#### 2\. 哪类特征最有效？

作者比较了单独使用和组合使用不同特征的效果，结果很有意思：

##### 单特征时

**motion 最强**，优于 anatomy 和 texture。

论文中总结：

> These results demonstrated that motion is more effective than texture and anatomy features.

(Ding 等, 2025)

##### 多特征时

最佳组合是 **motion + anatomy**。

> Among all combinations, MyoPSΦL achieved the best performance (i.e., Dice, Pre, Sen, NPV, and HD) by leveraging motion and anatomy features.

(Ding 等, 2025)

##### texture 不一定有帮助

加入 texture 反而可能变差：

> Interestingly, incorporating more features did not always benefit MyoPS.

(Ding 等, 2025)

以及

> This discrepancy arises because the texture feature may become redundant when anatomy and motion features are already present.

(Ding 等, 2025)

这说明作者的方法不只是“多加特征就更好”，而是做了较清晰的特征有效性分析。


---


#### 3\. consistency loss 和时间聚合是否有效？

答案是：**有效**。

对于 consistency loss：

> Without using consistency loss, CineMyoPS suffered performance degradation (scar: 0.05, p < 0.01). This indicates the benefit of the consistency loss.

(Ding 等, 2025)

对于时间聚合：

> This reveals that the time-series aggregation strategy can improve MyoPS.

(Ding 等, 2025)


---


### 和其他方法相比表现如何？

在测试集上，CineMyoPS 与 nnUnet、OFSeg、ConvLSTM、2D+1D Unet 做了比较。

总体结果：

- **scar segmentation** 上，CineMyoPS 表现最好
    
- **edema segmentation** 上，也略优或接近最优
    
- 尤其在 scar 的 Dice 上，相比 nnUnet 提升明显
    

例如论文写道：

> CineMyoPS achieved a 0.11 (p < 0.01) higher Dice score for scar segmentation compared to nnUnet.

(Ding 等, 2025)

但作者也非常坦诚地指出：

- 整体性能仍低于一些依赖对比增强 CMR 的方法
    
- edema 仍较难
    
- apical slices 尤其困难
    
- transmurality 在 nonviable myocardium 上估计较差
    

比如：

> However, CineMyoPS was unsuccessful in estimating scar transmurality in nonviable myocardium (R=0.22, p = 0.17).

(Ding 等, 2025)

以及：

> CineMyoPS encounters substantial challenges when processing apical slices

(Ding 等, 2025)


---


### 论文结论可以怎么概括？

可以用一句话概括：

**CineMyoPS 证明了：只依赖 cine CMR，也有可能实现无对比剂的心肌病灶自动分割，尤其是通过联合建模运动、解剖及时间信息来识别 scar 和 edema。**

论文结尾也强调了这个方向的意义：

> It explores the potential of replacing LGE and T2-weighted images with cine CMR images, aiming to shorten the acquisition time of MS-CMR and eliminate the injection of contrast agents.

(Ding 等, 2025)


---


### 你可以如何理解这篇论文的“方法贡献”？

如果从研究贡献角度总结，我会概括成 4 点：

1. **提出了首个仅基于 cine CMR 的全自动 joint scar + edema 分割框架**
    
2. **把运动估计、解剖分割、病理分割联合到一个端到端框架中**
    
3. **设计 consistency loss，提升运动和解剖特征的协同学习**
    
4. **设计 time-series aggregation，在整个心动周期内融合信息**
    


---


### 文中列出的 GitHub 仓库汇总

> 说明：正文可明确出现的 **GitHub 代码链接**主要为本文 CineMyoPS 仓库；对比方法（nnUnet、OFSeg 等）在文中**未给出**具体 repo 地址，下表据文意归纳。

| 方法/项目 | 是否开源 | GitHub / Repo 链接 | 文中说明 |
| --- | --- | --- | --- |
| **CineMyoPS** | **是（计划公开）** | **https://github.com/NanYoMy/CineMyoPS** | **“Source code will be released publicly … once the manuscript is accepted.”** |
| nnUnet | 文中未提供 | 未提供 | 只引用了论文 [38] |
| OFSeg | 文中未提供 | 未提供 | 只作为对比方法描述 |
| ConvLSTM | 文中未提供 | 未提供 | 只引用了论文 [23] |
| 2D+1D Unet | 文中未提供 | 未提供 | 只引用了论文 [41] |
| MvMM tool | 文中未提供 GitHub | 未提供 | 只引用了文献 [37] |

---
