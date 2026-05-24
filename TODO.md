# CARE Myocardium TODO: 从 failure landscape 到 repo portfolio integration 的阶段性路线图

Date: 2026-05-20

本文件用于给后续 Codex / ChatGPT / agent 提供一个长期可读的项目路线图。它不是一次性 prompt，也不是某个单独实验的执行说明，而是解释 CARE Myocardium 当前为什么不应该立刻无差别拉取大量 repo，当前到底处于什么阶段，后续什么时候进入大规模 repo portfolio integration，以及每个阶段的输入、输出、判断标准和退出条件。

当前项目的核心目标不是复刻某一篇 paper baseline，而是在 CARE Myocardium 的真实数据分布、真实 label semantics、真实 hosted metric 约束下，逐步构建一个 CARE-native segmentation system。这个 system 可以吸收 MyoPS-Net、U-MyoPS、CineMyoPS、Deep Research 中的新方法和预训练模型，但不能被任何一个外部 repo 的原始假设绑架。外部 repo 的角色应该是 mechanism source 或 module provider，而不是直接作为主 pipeline。

---

## 0. 当前战略判断

### 0.1 为什么现在没有立刻拉一堆 repo

最初设想是基于 Deep Research 的结果系统性拉取一批 repo，例如 CAA-Seg、YoloSAM、AdaMM、UniME、BiomedParse、CineMA、ViTa、StrainNet、VoxelMorph、SegMorph、InverseForm、Unified Focal Loss 等，然后让 Codex 大规模尝试把它们 adapt 到 CARE。这个方向本身是合理的，但不能在没有统一判别标准时直接启动。否则很容易出现大量不可解释的实验结果。

如果过早无差别拉 repo，会出现以下问题。不同 repo 使用不同 preprocessing、不同 fold、不同 label mapping、不同 spacing/interpolation、不同 output encoding 和不同 evaluator；结果可能无法和 nnU-Net501、nnU-Net502 或 official hosted metric 对齐。某个 repo 失败时，也无法判断失败原因是方法本身不适合 CARE，还是 adapter 写错、cache 污染、raw label 转换错误、postprocess 不一致、HD/HD95 计算不一致，或者 CARE 的真实瓶颈根本不是该方法解决的问题。

因此当前阶段优先做的不是“少做实验”，而是先建立后续大规模实验的判别器。只有先知道 CARE 的主要 failure mode，后面大规模拉 repo 才有意义。否则 token 和 GPU 时间会被消耗在一堆不可决策的失败记录上。

### 0.2 当前的核心路线

当前路线不是否定 repo portfolio integration，而是采用三层推进。

第一层是 CARE failure landscape mapping，已经基本完成。目标是确认 protocol anchor、label semantics、hosted/local mismatch、Dice 与 HD/HD95 的关系、modality/center 分层问题、failure registry，以及哪些简单修复有效或无效。

第二层是 CARE-native mechanism testing，当前正在进入。目标是把 Deep Research 中的方法拆成机制，例如小病灶 loss、boundary/HD-aware loss、modality-aware routing、T2-aware edema supervision、topology stabilization、raw label QC，然后在 CARE fold0 和 smoke setting 下验证这些机制是否真正有信号。

第三层才是 repo portfolio integration，也就是原先设想的大量拉取 repo、尝试 adapt 到 CARE。但这一步应该按机制槽位进行，而不是无差别尝试。每个 repo 必须先通过 compatibility audit、one-case smoke、fold0 smoke 和 metric/export gate，才能进入更大规模训练。

---

## 1. 当前项目阶段

当前阶段可以定义为：

CARE-native targeted mechanism testing, between Round2 and Round3.

也就是说，项目已经完成了 baseline chaos 阶段，也完成了第一轮 failure landscape mapping。现在不应再继续围绕 MyoPS-Net、U-MyoPS、CineMyoPS 的 third_party code 反复 patch，也不应马上进入大规模 repo race，而应开始基于已确认的 failure modes 做小规模、有明确判断标准的 trainable smoke 和 hosted calibration。

### 1.1 已确认的基础事实

CARE validation submission 是一个 zip，同时包含 `MyoPS/` 和 `CineMyoPS/` 两个分支。平台一次返回三个 leaderboard metrics，即 `myops_scar`、`myops_edema` 和 `myocardium_cinemyops`。不能把三个指标拆成三个独立上传，但可以构造 hybrid package，例如 MyoPS branch 使用 nnU-Net，CineMyoPS branch 使用 topology-repaired Cine prediction。

CARE MyoPS training set 不是标准完整多模态训练集。完整 $$C0+LGE+T2$$ cases 只有 $$80/220$$，$$C0+LGE$$ no-T2 有 $$24/220$$，LGE-only 有 $$116/220$$。完整 cases 主要来自 CenterB/CenterC，LGE-only 主要来自 CenterA/CenterH。官方 validation MyoPS 是完整 $$LGE+C0+T2$$，但训练监督被 incomplete cases 主导。这意味着 edema 的核心问题不是普通 scanner style shift，而是 T2 supervision、modality missingness、center confounding 和 pathology label availability 纠缠在一起。

MyoPS-Net 和 U-MyoPS 已经不应继续作为 mainline replacement candidate。它们的思想可以保留，例如 modality-specific routing、anatomy prior、alignment before fusion、prior reliability gating，但不应继续把 third_party code 当成主要改进对象。新模型或新机制应该逐步进入 `src/`。

CineMyoPS 当前最明确的问题不是 large backbone capacity，而是 pathology topology fragmentation 和 hosted/local metric mismatch。Round2 结果表明 topology LCC 可以显著改善 class $$3$$ scar sanity 的 HD95 和 component count，因此 Cine 侧短期应先做 hosted calibration，而不是马上上 CineMA、ViTa、StrainNet 或 MTI-MyoScarSeg。

---

## 2. Round2 已得到的关键结论

### 2.1 Lane A, MyoPS edema

Lane A Round2 只做了诊断 smoke，没有训练或改模型。结果显示，edema 小连通域/ROI 后处理不值得继续作为主线。删除 1-voxel edema 小岛后，component count 从 $$3.3182$$ 降到 $$1.7273$$，但 GT-positive edema 的 HD95 没有改善，反而从 $$20.0115$$ 轻微变差到 $$20.0234$$；Dice 也从 $$0.3944$$ 降到 $$0.3935$$。这个结果应被视为明确 fail。

这个负结果非常重要。它说明 edema 的主要问题不是少数远端微小假阳性，也不是推理后简单清理能解决的碎片问题。真正瓶颈仍在 T2-present complete cases 的 edema 质量。当前 T2-present edema Dice 约 $$0.3944$$，HD95 约 $$20.0115$$，component count 约 $$9.1250$$；CenterC 尤其差，edema Dice 约 $$0.3100$$，HD95 约 $$23.1833$$。因此问题更可能来自 edema boundary ambiguity、diffuse lesion morphology、loss objective 不适合、T2-conditioned learning 不充分、class imbalance、scar/edema objective conflict，而不是 inference suppression。

T2-aware routing 当前只支持 training-side strategy，不支持 inference-side suppression。fold0 里所有 edema GT-positive cases 都是 T2-present；no-T2 cases 都是 edema empty-GT，而且当前 nnU-Net 没有 no-T2 edema false positive。因此 no-T2 suppression 没有可修的推理错误。后续如果训练新模型，可以考虑对 no-T2 case 做 edema loss masking 或 downweighting，但不能把 no-T2 empty-GT 作为强负样本硬压制 edema head。

Lane A 下一步应从 postprocess smoke 转向 trainable smoke，优先做 edema-only loss、edema weighting、boundary/distance loss、T2-aware loss masking/downweighting 的 gradient/tiny-overfit smoke，然后才进入 fold0 short train。

### 2.2 Lane B, Cine topology

Lane B Round2 已经确认 topology LCC 是当前最强的 low-cost positive signal。`pathology_direct` 的 class $$3$$ Dice 约 $$0.4378$$，HD95 约 $$26.6533$$，scar components 约 $$5.5385$$；`topology_lcc` 的 class $$3$$ Dice 约 $$0.4441$$，HD95 约 $$18.7983$$，scar components 约 $$1.0000$$。Dice 没有下降，HD95 和 components 明显改善。

bbox-distance guard 有改善，但弱于 LCC，HD95 约 $$21.3008$$，components 约 $$2.0000$$。component-size、volume、myocardium-overlap、combined guard 都未超过 LCC。因此 Round2 默认 topology rule 应保持 `topology_lcc`。更复杂 guard 暂时只保留为 diagnostic evidence，不 promoted。

Lane B 下一步应该做 hosted calibration。具体是生成一个 validation-style candidate package，MyoPS branch 使用 conservative nnU-Net baseline，CineMyoPS branch 使用 `topology_lcc`，先做 packaging QA 和 raw-label QC，然后视 submission attempt 情况决定是否上传。这个 hosted calibration 的目的不是宣布最终模型，而是验证本地 class $$3$$ topology repair 是否真的能降低 hosted `myocardium_cinemyops` 的 HD 或改善 Dice。

---

## 3. Deep Research 的当前角色

Deep Research 不应再被理解为“找到哪个 paper，然后完整复现哪个 paper”。当前更合理的理解是 mechanism library。也就是说，Deep Research 提供的是可吸收的机制，而不是必须完整复刻的 pipeline。

### 3.1 Lane A 对应的 Deep Research 机制

Deep Research 中关于 small lesion、class imbalance、boundary quality、HD optimization 的内容，对应到 Lane A 应该变成以下机制。

ST-Loss、Unified Focal Loss、Focal Tversky、CATMIL、InverseForm、sub-differentiable Hausdorff loss、boundary-aware loss 等，当前都应被收缩成 class $$4$$ edema 的 trainable smoke。它们要回答的问题不是“能不能完整复现论文”，而是能不能在 CARE fold0 上改善 T2-present GT-positive edema 的 Dice、HD95、component count，并且不损伤 class $$5$$ scar。

AdaMM、UniME、CoPeDiT、missing-modality MoE、MMPL-Seg、I-MMSeg 等，当前都应被收缩成 T2-aware edema routing 和 explicit modality-mask conditioning 的机制测试。它们要回答的问题是 no-T2 cases 是否应 mask edema loss、downweight edema loss，或者使用 modality presence vector 避免模型把 missing T2 和 no edema 混为一谈。当前不应直接实现完整 AdaMM 或 UniME framework。

Cascaded FSN、MyoPS++、anatomy-aware loss、PT-Net 等，当前应被收缩成 soft anatomy prior 和 ROI plausibility guard，而不是 hard deletion。Lane A 的 Round2 postprocess 已经说明简单 ROI 删除不解决 edema，因此 anatomy prior 后续更适合作为 trainable auxiliary input 或 soft regularizer，而不是 inference hard mask。

### 3.2 Lane B 对应的 Deep Research 机制

Deep Research 中关于 CineMA、CorSeg-CineSAX、ViTa、StrainNet、MTI-MyoScarSeg、VoxelMorph、SegMorph、cineCMR-SAM 的内容，当前不应立即全量接入。Lane B 现在已经有一个更便宜、更直接的 positive signal，即 `topology_lcc`。因此在 hosted calibration 完成前，不应把主要精力放在大 temporal backbone。

CineMA、CorSeg-CineSAX 可作为 future anatomy backbone 或 robust cine myocardium feature provider。StrainNet、MTI-MyoScarSeg、VoxelMorph、SegMorph 可作为 future motion/strain route。ViTa 可作为 future temporal/cine pretrained backbone。但它们应进入 Round5 repo portfolio integration，而不是当前 Round3 immediate execution。

当前 Lane B 最重要的 Deep Research 吸收方式是 topology-aware and HD-aware postprocess。也就是说，先把 LCC、component count、raw label subset、bbox、volume、non-empty $$2221$$、hosted metric risk QC 做稳。如果 hosted calibration 证明 topology repair 有效，再考虑将 CineMA/CorSeg/StrainNet/MTI 作为下一阶段模块接入。

### 3.3 Domain adaptation 的当前角色

Domain adaptation 有用，但不能作为独立主线。它最适合解决 center/scanner/style shift、BN/statistics adaptation、feature consistency 和 target-test-time normalization。但它不能从 LGE-only 数据中凭空学到 T2 edema cue，也不能把 no-T2 empty-GT 当成可靠 edema negative。

因此 Lane C 当前只保留 watch。可做的方向包括 robust-z、percentile clipping、center/modality-specific BN、BN-stat adaptation、lightweight style augmentation。暂时不做 heavy adversarial DA、diffusion harmonization、validation pseudo-label supervised training、external data harmonization。

---

## 4. Roadmap 总览

### Round0, baseline interpretation and paper baseline exit-gate

状态：已基本完成。

目标是理解 MyoPS-Net、U-MyoPS、CineMyoPS 的原始 paper setting 与 CARE wrapper 之间的差异，确认哪些 baseline 还值得继续，哪些只保留为 negative evidence。结论是 MyoPS-Net 和 U-MyoPS 不应继续作为 mainline replacement；CineMyoPS 只作为 hosted/HD repair 和 topology calibration 的来源继续观察；nnU-Net 作为 operational baseline 保留。

### Round1, protocol anchor and failure landscape mapping

状态：已完成。

目标是建立 nnU-Net501 fold0 protocol anchor、unified evaluator、modality/center stratification、failure registry、Cine topology diagnostics。结果显示 MyoPS edema 是主要弱点，Cine HD/component 是主要可修点。这个阶段的产物包括 `results/diagnostics/care_myocardium/` 下的 audit 表格、failure registry 和 cross-lane decision table。

### Round2, targeted diagnostic smoke

状态：刚完成。

Lane A 通过 edema component/ROI postprocess smoke 得到负结果，确认 postprocess 不是 edema 主线。Lane B 通过 topology guard smoke 得到正结果，确认 LCC 是当前最好的 Cine topology rule。这个阶段完成后，项目应进入 Round3，而不是继续做同类 postprocess 诊断。

### Round3, targeted trainable smoke and hosted calibration

状态：下一步。

Round3 的核心任务是两个。Lane A 进入 training-side smoke，先做 loss/gradient/tiny-overfit，再做 fold0 short train。Lane B 进入 hosted calibration，生成并检查 `nnUNet_MyoPS + Cine topology_lcc` validation-style candidate package，视 submission budget 决定是否上传。

Round3 仍然不是大规模 repo integration 阶段。它是把 Deep Research 机制转化为最小可检验实验的阶段。

### Round4, CARE-first skeleton extraction

状态：Round3 出现正信号后启动。

目标是把已经通过 smoke 的模块抽取到 `src/`，而不是继续依赖 third_party patching。候选包括 `src/losses/edema_losses.py`、`src/modules/modality_mask.py`、`src/postprocess/topology_lcc.py`、`src/postprocess/component_filter.py`、`src/postprocess/anatomy_guard.py`、`src/diagnostics/component_stats.py`、`src/diagnostics/modality_center_eval.py`、`src/evaluation/raw_label_qc.py`。这一轮不是为了漂亮重构，而是为了让后续 repo integration 有统一 substrate。

### Round5, repo portfolio integration

状态：待 Round3/Round4 给出明确机制信号后启动。

这是原先设想的“大量拉取 repo 并尝试 adapt 到 CARE”的阶段，但必须按机制槽位进行，而不是无差别尝试。每个 repo 需要先经过 compliance audit、license check、pretrained data check、input/output shape check、label mapping check、one-case smoke、fold0 smoke，才能进入 larger run。

Lane A 的 repo 槽位包括 loss/HD/small-lesion、missing-modality conditioning、alignment/anatomy prior、pretrained backbone。Lane B 的 repo 槽位包括 cine anatomy backbone、motion/strain feature、temporal pretrained backbone、registration/motion consistency。Lane C 的 repo 槽位只保留 lightweight normalization/adapters，不做 heavy DA 主线。

### Round6, fold expansion and submission strategy

状态：最后阶段。

只有某个方法在 fold0 上同时改善目标 metric 和 HD/component guard，才扩展到 fold1-4 或 5-fold。只有本地结果通过 label/cache/metric/export gates，才生成 validation package。提交时必须记住一个 zip 返回三个指标，不能用 foreground mean 或 local proxy 掩盖单项失败。

---

## 5. Round3 具体 TODO

### 5.1 Lane B, hosted calibration first

优先级：立即执行。

原因是 Lane B 已经有明确正信号，且成本低。当前本地 evidence 表明 topology LCC 明显降低 class $$3$$ HD95 和 component count，且 Dice 不下降。下一步应验证这个本地 signal 是否能转化为 hosted metric 改善。

#### TODO B1: validation-style packaging QA

输入是现有 `topology_lcc` compact Cine predictions 和 conservative nnU-Net MyoPS predictions。输出一个 candidate package tree，但不要自动上传。必须检查 raw label subset 是否为合法集合 `{0,200,500,2221}`，每个 case 是否有 non-empty $$2221$$ 或明确 fallback，raw $$2221$$ component count、bbox、volume 是否正常，compact class $$3$$ 到 raw $$2221$$ 的 mapping 是否未被改变。

输出建议放在：

```text
results/diagnostics/care_myocardium/laneB_cine/round03_packaging_qc/