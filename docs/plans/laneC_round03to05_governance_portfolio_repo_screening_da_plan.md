# Lane C Portfolio Repo Screening and DA Plan

Date: 2026-05-19

Plan metadata:
- Type: portfolio/governance controller
- Lane: C, repo portfolio / pretrained assets / losses / postprocess / DA-normalization
- Round scope: Round3 through Round5
- Status: active governance plan
- Parent roadmap: `/overflow/htzhu/CARE/TODO.md`
- Parent plan: none
- Function: define candidate screening, compliance, fail-fast gates, and when external repos/weights may enter CARE experiments
- Do not: treat Lane C as a standalone heavy DA training lane; it only supports Lane A/B unless Round5 portfolio integration is explicitly opened

本文件是 CARE Myocardium 下一轮自动化实验的控制文档。目标不是继续“拼积木”式尝试外部 repo，而是先把候选方法、合规风险、实验可比性、失败门槛和 Lane A/B/C 的优先顺序固定下来。

## 1. 执行摘要

推荐攻击顺序：

1. **Phase 0/1 先做可比性与冒烟测试**：统一 fold、label、Dice+HD/HD95、connected components、small/remote false positives、modality/center 分层、artifact 命名和 cache 隔离。下一轮 Codex 只应实现这些低成本检查，不启动完整训练 campaign。
2. **Lane A MyoPS 优先**：nnU-Net 仍是 operational baseline。MyoPS-Net 和 U-MyoPS 已经完成 baseline exit-gate，不再作为主线替代候选；后续 MyoPS 工作应进入 `src/`，以 modality-mask-aware、anatomy/pathology cascade、T2-aware edema route、HD/component diagnostics 为核心。
3. **Lane B CineMyoPS 次优先**：只围绕 hosted `myocardium_cinemyops` 语义、HD 爆炸、connected components、motion/anatomy ideas 继续。若 round8 LCC/HD repair 的 hosted 结果仍低，应停止小 postprocess，转向 `src/` motion/strain route。
4. **Lane C DA/normalization 是辅助机制**：只做 intensity/statistics/adapters/source-free BN 级别的轻量实验。Domain adaptation 不能作为独立主线，不能替代模态缺失、T2 supervision 不足和小病灶 HD/outlier 问题。

明确不做：

- 不用外部数据做 supervised scar/edema 训练。
- 不对外部数据做 pseudo-labeling。
- 不训练外部数据 generative/diffusion harmonization 模型。
- 不把 validation pseudo-label 加入 scar/edema supervised loss。
- 不继续 patch MyoPS-Net/U-MyoPS 作为主线替代候选。
- 不把 foreground_mean、LV、myocardium aggregate 当成主目标；主结论只看 `myops_scar`、`myops_edema`、`myocardium_cinemyops`。

下一轮 Codex 只应实现 Phase 0/1 的原因：

- 当前最大风险不是缺一个复杂模型，而是实验不可比、hosted/local 语义不完全一致、HD/component 失败没有统一记录。
- Phase 0/1 可在无训练或极短 smoke 下筛掉不合规、不可集成、会破坏 HD/component 的候选。
- 只有通过 Phase 0/1 gate 的候选，才允许进入 pretrained backbone smoke 或 `src/` first-party model implementation。

## 2. 统一实验治理

| 项 | 固定规则 |
| --- | --- |
| fold protocol | fold0 先行；只在 fold0 预测非空、label 正确、cache 隔离、Dice+HD gate 通过后扩展 fold1-4；最终报告 folds 0-4。 |
| label mapping | MyoPS compact `4=edema/1220`, `5=scar/2221`；Cine compact `1=myocardium`, `2=LV`, `3=scar/2221`；validation raw label 由 `scripts/submission/prepare_care_myocardium_validation.py` 统一转换。 |
| output packaging | 保持一个 `CARE-Myocardium-OrganAgent.zip`，同时含 `MyoPS/` 和 `CineMyoPS/`；一次上传返回三项 hosted metrics。 |
| local metrics | 必报 Dice、HD、HD95、component count、small/remote FP、lesion volume ratio；MyoPS 分 `myops_scar`/`myops_edema`，Cine 同时报 class_1 proxy 与 class_3 scar sanity。 |
| hosted metrics | 只以 `myops_scar`、`myops_edema`、`myocardium_cinemyops` 做主结论。 |
| baseline comparison | MyoPS 对 `nnUNet501` fold0/5-fold；Cine 对 `nnUNet502` 和 current CineMyoPS `pathology_direct`/LCC。 |
| artifact naming | `results/predictions/<lane>_<candidate>_<phase>_<config>/fold_k`；metrics 同名写入 `results/metrics/unified/...`；禁止覆盖 baseline。 |
| cache isolation | checkpoint、postprocess、normalization、fold、label-remap 必须进入目录名或 manifest。 |
| 防止不可比 | 所有候选必须通过同一 evaluator、同一 fold JSON、同一 GT、同一 remap、同一 empty-GT 规则；不允许用单独脚本私算主结论。 |

## 3. 候选筛查矩阵

| candidate | source URL or local note path | task | role | pretrained weights? | license | pretrained data | external-data risk | implementation complexity | expected benefit | first smoke test | fail-fast rule | decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CAA-Seg / SSA | `docs/notes/deep_research/Result2.pdf`; https://papers.miccai.org/miccai-2025/0009-Paper2655.html | MyoPS scar / edema | selective slice alignment + multimodal fusion idea | unclear | unclear | unclear | low if code-only or reimplemented | medium | reduce C0/LGE/T2 misalignment and scar/edema localization error | complete-case fold0 SSA/alignment audit only | no complete-case Dice/HD gain or alignment cannot be reproduced | prioritize |
| YoloSAM | `docs/notes/deep_research/Result2.pdf`; https://papers.miccai.org/miccai-2025/0788-Paper2947.html | MyoPS scar | detect-then-segment lesion ROI | unclear | unclear | YOLO/SAM assets likely public pretrained | medium | medium | reduce tiny scar false positives and label-noise sensitivity | frozen ROI proposal on nnU-Net scar maps, no training | FP reduction lowers scar-positive Dice or creates missed small scars | watch |
| I-MMSeg | `docs/notes/deep_research/Result1.pdf` | MyoPS scar / edema | intensity-prior multimodal model | unclear | unclear | MyoPS380 / CLIP-like components mentioned | medium | high | potentially strong multimodal pathology model | metadata/interface review only | requires external supervised data, LLM-generated assets, or incompatible training path | defer |
| AdaMM | `docs/notes/deep_research/Result2.pdf`; https://github.com/Quanato607/AdaMM | MyoPS missing-modality | knowledge-distillation strategy for missing modalities | unclear | unclear | brain tumor / BraTS-style pretraining in original work | low if code-only | high | improve LGE-only and incomplete-modality robustness | port idea into CARE-only teacher/student sketch, no training | requires external data teacher or worsens T2-present edema | watch |
| CoPeDiT | `docs/notes/deep_research/Result2.pdf` | MyoPS / DA | diffusion transformer for missing modality synthesis | unclear | unclear | likely external MRI | high | high | theoretical missing-modality synthesis | no implementation smoke; paper-only note | requires generative model training or external data | reject |
| UniME | `docs/notes/deep_research/Result2.pdf` | MyoPS missing-modality | MIM/pretrained missing-modality robust backbone | unclear | unclear | BraTS/cardiac mixed, unclear | medium | high | modality robustness | metadata/license/provenance screen | cannot separate pretrained external-data risk from method | watch |
| BiomedParse | `docs/notes/deep_research/Result2.pdf`; https://github.com/microsoft/BiomedParse | MyoPS / Cine | foundation segmentation prompt model | yes | code likely Apache-2.0; weight license must be verified | broad biomedical images | medium/high | medium | anatomy prior or promptable QA | frozen inference on 2-3 CARE cases only after license check | license forbids challenge use or output cannot map to CARE labels | defer |
| MS-CaReCNN / MyoPS++ concept | `docs/notes/deep_research/Result1.pdf` | MyoPS scar / edema | two-stage anatomy-first pathology cascade | no public weights | paper/concept | none if reimplemented | low | medium/high | better lesion localization and HD | simulate with existing nnU-Net anatomy masks and pathology maps | no complete-case gain or HD worsens | prioritize |
| Cascaded FSN / anatomy-first pathology segmentation | `docs/notes/deep_research/Result2.pdf`; https://cinc.org/archives/2024/pdf/CinC2024-148.pdf | MyoPS scar / Cine scar | coarse anatomy probability into lesion head | no | unclear | none if reimplemented | low | medium | reduce remote pathology components | deterministic anatomy-constrained postprocess on existing predictions | HD worsens or scar-positive Dice drops | prioritize |
| nnU-Net Task114 / M&Ms pretrained weights | `docs/notes/deep_research/Result2.pdf`; https://zenodo.org/records/4288362 | MyoPS / Cine anatomy | public pretrained initialization | yes | Zenodo license must be verified | M&Ms cardiac MRI | low if initialization/frozen only | low | better anatomy warm start | metadata-only check; no large download in screening | license unclear, label mismatch, or download too large without approval | prioritize after Phase 1 |
| MedNeXt | `src/README.md`; https://github.com/MIC-DKFZ/MedNeXt | MyoPS / Cine backbone | robust segmentation backbone | maybe | verify repo license | none if trained CARE-only | low | medium | stronger pathology head than old paper baselines | import/config smoke only | cannot wrap into unified export/eval | watch |
| CineMA | `docs/notes/deep_research/Result1.pdf`; https://huggingface.co/mathpluscode/CineMA | CineMyoPS | cine anatomy foundation model | yes | MIT per local note; verify HF card | cine CMR | low if frozen/init only | low/medium | improve cine anatomy mask and ROI | frozen anatomy inference on fold0 sample | no class_1/component benefit or license mismatch | prioritize |
| CorSeg-CineSAX | `docs/notes/deep_research/Result1.pdf`; https://www.researchgate.net/publication/403490811_CorSeg-CineSAX_An_OpenSource_Deep_Learning_Framework_for_Fully_Automatic_Segmentation_of_ShortAxis_Cine_Cardiac_MRI_Across_Multiple_Cardiac_Diseases | CineMyoPS | cine anatomy + topology postprocess | yes | CC BY 4.0 per local note; verify repo | 1555 multi-center cine | low if public pretrained allowed | low/medium | reduce Cine anatomy/component/HD failures | frozen anatomy mask on local fold0 | topology postprocess deletes scar support | prioritize |
| ViTa | `docs/notes/deep_research/Result2.pdf`; https://github.com/Yundi-Zhang/ViTa | CineMyoPS | 3D+T cine pretrained backbone | yes | MIT in repo note, verify | UKBB cine / large cardiac data | low if init/frozen only | medium | temporal features and cine representation | metadata/interface smoke only | requires tabular/external training path or too heavy | watch |
| StrainNet / StrainNet-Transformer | `docs/notes/deep_research/Result2.pdf`; https://github.com/EpsteinLabUVA/StrainNet | CineMyoPS | strain feature side branch | yes/unclear | verify | cine contours/strain | low if frozen feature only | medium | motion abnormality cue for scar | frozen strain-map generation on one case | geometry mismatch, slow runtime, or unreliable output | watch |
| MTI-MyoScarSeg | `docs/notes/deep_research/Result1.pdf` | CineMyoPS | motion-texture fusion concept | no public code noted | unclear | none if reimplemented | low | high | direct cine scar cue | optical-flow channel prototype only | no component/HD improvement or too slow | watch |
| VoxelMorph | `docs/notes/deep_research/Result1.pdf`; https://github.com/voxelmorph/voxelmorph | Cine / registration | DVF / motion feature extractor | possible | verify | generic / ACDC if checkpoint used | medium | medium | motion cue | one-case registration audit with Jacobian/folding check | folding or topology failure; no downstream signal | watch |
| cardiac registration checkpoint | `docs/notes/deep_research/Result2.pdf` | Cine / registration | pretrained cardiac DVF | yes/unclear | unclear | ACDC or similar | medium | medium | motion prior | metadata/provenance check only | no license/provenance | defer |
| SegMorph | `docs/notes/deep_research/Result1.pdf` | CineMyoPS | joint motion+segmentation concept | no/unclear | unclear | unclear | low if concept-only | high | temporal consistency | paper/interface review | full reimplementation required before any smoke | defer |
| cineCMR-SAM | `docs/notes/deep_research/Result1.pdf` | CineMyoPS | temporal SAM anatomy model | yes/unclear | unclear | SAM + cine data | medium | medium | anatomy localization | prompted anatomy smoke only | prompt dependency not automatable or license mismatch | watch |
| MFD-V2V / LTMA | `docs/notes/deep_research/Result2.pdf` | CineMyoPS | latent temporal motion / video diffusion | unclear | unclear | diffusion/video data | high | high | motion consistency | none beyond paper note | requires generative training or external data | reject |
| InverseForm | `docs/notes/deep_research/Result2.pdf`; https://github.com/Qualcomm-AI-research/InverseForm | loss | boundary / HD-aware loss | no | verify | none | low | low/medium | reduce HD/HD95 | loss-only gradient check on CARE tensors | Dice gain with HD regression or unstable gradients | prioritize |
| ST-Loss / HFEF | `docs/notes/deep_research/Result2.pdf` | loss | high-frequency boundary loss | no | verify | nuclei data code only if reused | low | medium | sharper boundaries | loss import + one-batch gradient check | pathology FP or component count increases | watch |
| Unified Focal Loss | `docs/notes/deep_research/Result2.pdf`; https://github.com/mlyg/unified-focal-loss | loss | Dice/Tversky/Focal family | no | verify | none | low | low | imbalance handling | first-party plug-in loss smoke | no fold0 gain vs existing loss | prioritize |
| Focal Tversky | standard loss / local implementation | loss | small lesion imbalance | no | first-party | none | low | low | scar/edema recall | first-party loss + tiny overfit | recall gain creates remote FP/HD regression | prioritize |
| CATMIL | `docs/notes/deep_research/Result1.pdf` | loss | component-adaptive lesion loss | yes/code noted | verify | brain MRI small lesions | low if code-only | medium | lesion-level recall | component term on CARE labels only | component count or HD worsens | watch |
| differentiable Hausdorff / boundary loss | `docs/notes/deep_research/Result1.pdf` | loss | direct boundary / HD surrogate | no | implement first-party or verify code license | none | low | low | HD repair | loss smoke + 2-case overfit | HD flat or Dice drops >1 point | prioritize |
| center/modality-aware normalization audit | `docs/notes/domain_adaptation/domain_adaptation_relevance_20260519.md` | DA | diagnosis and preprocessing | no | first-party | CARE only | low | low | identify center shortcut and intensity shift | histogram/error report | no center/modality signal | prioritize |
| domain-specific BN/adapters | DA note | DA | light style adaptation | no | first-party | CARE only | low | medium | center/style robustness | BN-stat only smoke | breaks label metrics or unstable | prioritize |
| robust z-score / percentile clipping | DA note | DA | preprocessing | no | first-party | CARE only | low | low | simple style control | fold0 normalized input audit | Dice/HD regression | prioritize |
| histogram matching to complete-case reference | DA note | DA | intensity harmonization | no | first-party | CARE train only | low/medium | low | reduce center shift | LGE/C0/T2 per-center audit | lesion contrast reduced or HD worse | watch |
| Fourier style augmentation / RandConv / BACON-like DG | DA note / Result2 | DA | augmentation / domain generalization | no | first-party/code-only | CARE only | low | medium | robustness | augmentation-only mini-overfit | scar/edema precision collapse | watch |
| source-free / test-time BN/statistics adaptation | DA note | DA | validation/test style calibration | no | first-party | validation images only, unlabeled | medium | low/medium | target style calibration | update BN/statistics only, no head update | requires pseudo-label or head update | watch |

## 4. 合规矩阵

| 方案类型 | pretrained-only ok? | requires external data? | uses validation images? | updates model on validation? | uses pseudo-labels? | safe alternative if risky | final risk rating |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Public pretrained weights for initialization/frozen features | yes, if license permits | no additional external data | no by default | no | no | freeze or initialize then train on CARE only | medium |
| Code-only external repository | yes | no | no | no | no | port minimal module into `src/` and use CARE dataloader/eval | low |
| Methods requiring external supervised datasets | no | yes | no | yes | possible | reimplement method using CARE train only | high / reject |
| External diffusion or generative harmonization | no for current phase | usually yes | maybe | yes | no | percentile clipping, robust-z, Fourier/RandConv augmentation | high / reject |
| Validation pseudo-label supervised scar/edema training | no | no | yes | yes | yes | uncertainty-masked consistency only; no pathology supervised loss | high / reject |
| Test-time BN/statistics adaptation | conditionally | no | yes, unlabeled | BN/stats only | no | freeze heads, log all changed params, manifest adaptation mode | medium |
| Semi-supervised consistency on validation | conditionally | no | yes, unlabeled | limited adapters only | no hard pseudo-labels | high-confidence anatomy or uncertainty-mask consistency | medium/high |
| Deterministic anatomy/postprocess | yes | no | can apply to predictions | no | no | manifest-recorded postprocess, same evaluator | low |

## 5. DA / Normalization Audit Plan

目标：判断现有 nnU-Net 和 adapted baselines 的错误是否与 center、modality group、intensity style、normalization drift 相关；只允许 CARE train 数据和无标签 validation image statistics，不允许 validation pathology pseudo-label。

### 5.1 Intensity histogram by modality group and center

- 对 MyoPS `LGE`、`C0`、`T2` 分别统计 foreground/nonzero histogram、percentiles、mean/std、robust median/IQR。
- 分组：`C0+LGE+T2`、`C0+LGE`、`LGE-only`，并按 center 汇总。
- CineMyoPS 统计 4D/selected frame intensity drift、frame index、spacing、volume shape。
- 输出：`results/diagnostics/da_normalization_audit/intensity_by_center_modality.csv` 和中文摘要。

### 5.2 Current nnU-Net error by modality group and center

- MyoPS：对 `nnUNet501`、current MyoPS candidates 报告 scar/edema Dice、HD、HD95、component count、small/remote FP、pred/GT volume ratio。
- Cine：对 `nnUNet502`、CineMyoPS `pathology_direct`、round8 LCC candidate 报告 class_1 proxy、class_3 scar sanity、component count、HD/HD95。
- 必须区分 all-cases、GT-positive-only、T2-present/complete subsets。

### 5.3 Normalization and light DG comparison

候选：

- existing preprocessing baseline。
- percentile clipping。
- z-score。
- robust z-score。
- histogram matching to complete-case reference。
- Fourier style perturbation / RandConv-style perturbation。

Gate：

- `myops_scar` 和 `myops_edema` Dice 不低于 nnU-Net fold0 reference。
- HD/HD95 不恶化。
- connected components、remote FP、lesion volume ratio 不恶化。
- histogram matching 不得系统性压低 LGE scar contrast 或 T2 edema contrast。

### 5.4 Domain-specific BN/adapters

- Backbone 共享，按 center 或 modality group 使用 BN/adapters。
- Scar/edema heads 分离；edema route 必须 T2-aware。
- Validation target adaptation 只允许 BN/statistics 或 adapters，不更新 final pathology classifier。
- 每次 adaptation 必须记录 changed parameters、target images count、random seed、checkpoint、fold。

### 5.5 Target BN/statistics adaptation constraints

- 只使用 validation images，不使用 validation labels。
- 不做 scar/edema pseudo-label supervised training。
- 不做 hard pseudo-label self-training。
- 如果使用 consistency，只能是 uncertainty-masked soft consistency，且必须冻结或严格限制 pathology head 更新。

## 6. 集成架构

### 6.1 First-party `src/` layout

建议新建：

```text
src/care_myocardium/
  data/
  models/
  losses/
  postprocess/
  normalization/
  adapters/
  experiments/
  reporting/
```

职责：

- `data/`：统一 CARE fold、case metadata、modality mask、center、label map。
- `models/`：first-party MyoPS/Cine wrappers，不放第三方原始 dataloader。
- `losses/`：Focal Tversky、boundary/HD surrogate、component-aware losses。
- `postprocess/`：component filters、LCC、anatomy ROI、volume guard。
- `normalization/`：robust-z、histogram matching、Fourier perturbation。
- `adapters/`：BN/statistics/domain-specific adapters。
- `reporting/`：统一 CSV/MD summary。

### 6.2 External repositories

- 外部 repo 如需使用，放 `third_party/candidates/<name>/` 并保持 read-only。
- 不继承外部 dataloader、fold split、metric、export、submission logic。
- 只包装模型 forward、loss 或 deterministic postprocess。
- 每个外部候选必须有 metadata：URL、commit、license、weights URL、pretrained data、allowed use、integration status。

### 6.3 Shared pipeline

所有候选必须接入：

- CARE shared dataloader/preprocessing。
- shared label map。
- `scripts/evaluation/evaluate_predictions.py`。
- `scripts/evaluation/run_unified_eval_model.sh` 或等价统一 wrapper。
- `scripts/submission/prepare_care_myocardium_validation.py`。

### 6.4 Unified config and reporting schema

每个实验至少记录：

| field | meaning |
| --- | --- |
| `experiment_id` | unique artifact prefix |
| `lane` | A MyoPS / B Cine / C DA-loss-postprocess |
| `candidate` | screened method name |
| `folds` | evaluated folds |
| `model_source` | first-party / third-party wrapper / pretrained init |
| `weights_source` | none / public URL / local checkpoint |
| `pretrained_data` | known dataset or unknown |
| `normalization` | preprocessing config |
| `postprocess` | deterministic postprocess config |
| `loss` | training loss if any |
| `pred_dir` | prediction artifact path |
| `metrics_dir` | unified metrics path |
| `target_metrics` | scar/edema/cine Dice + HD/HD95 |
| `component_metrics` | component count, remote FP, small FP |
| `modality_group` | MyoPS group if applicable |
| `center` | center if available |
| `compliance_status` | low/medium/high/reject |
| `pass_fail` | gate result |
| `stop_reason` | if failed |

## 7. Prioritized Roadmap

| phase | deliverables | expected commands for future runs | expected runtime | pass/fail criteria |
| --- | --- | --- | --- | --- |
| Phase 0: audit and reproducibility | baseline metric snapshot、modality/center error table、label/package/cache QA、candidate license/provenance table | `python scripts/leaderboard/fetch_care2026_scores.py`; `bash scripts/evaluation/run_unified_eval_model.sh nnUNet501`; future `python scripts/evaluation/report_portfolio_phase0_audit.py` | CPU minutes to <1h | all baseline paths reproducible; no stale cache; labels and raw package valid |
| Phase 1: postprocess/normalization/loss smoke | MyoPS component/HD postprocess report、Cine LCC diagnostics、normalization audit、loss gradient checks | future `python scripts/evaluation/report_myops_component_hd_audit.py`; existing `python scripts/evaluation/cinemyops_round8_hd_repair.py`; future `python scripts/evaluation/run_da_normalization_audit.py` | CPU/GPU <2h; no real training except tiny gradient/overfit smoke | Dice non-regression, HD/HD95 non-regression, components reduced or unchanged |
| Phase 2: pretrained backbone smoke | metadata-only then tiny frozen-feature/import tests for CineMA、CorSeg、Task114、ViTa、StrainNet | future `python scripts/screening/check_pretrained_candidate.py --candidate CineMA` | metadata minutes; tiny inference <2h; no large download without approval | license/data provenance clear; output can map to CARE labels |
| Phase 3: first-party model implementation | `src/` modality-mask-aware MyoPS cascade and Cine motion/anatomy wrapper | future `sbatch jobs/src/<candidate>_fold0_smoke.sh` with <=8h walltime | <=8h per fold0 job | beats nnU-Net fold0 target metric without HD/component regression |
| Phase 4: fold expansion | folds 1-4 only for candidates that pass fold0 | future all-fold wrapper for selected `src/` candidate | <=8h/job by default | mean across folds beats baseline; no hidden subgroup failure |
| Phase 5: hosted submission | one validation zip with both branches, manifest proof, QA tables | `sbatch jobs/submission/prepare_care_myocardium_validation.sh` only after gates | GPU inference budget | hosted package only if local gates and compliance pass |

## 8. Stop Criteria

立即停止候选，如果出现任一情况：

- label semantics 不清楚或 raw/compact encoding 不兼容。
- output 不能被 unified CARE evaluator/export 检查。
- empty-GT handling 制造人工 Dice gain。
- HD/HD95 在 Dice gain 下变差。
- connected components、small remote false positives 或 lesion volume ratio 恶化。
- compliance、license、pretrained-data provenance 不确定。
- 方法需要外部数据、外部 pseudo-labeling、外部 generative training。
- 使用 validation images 做 scar/edema supervised training。
- 只改善一个 hosted metric，同时破坏另一个 branch 的 one-zip submission。
- 无法集成到 `src/` + shared dataloader/metric/export pipeline，必须继承外部 repo 的 incompatible dataloader/eval。

## 9. Recommended Follow-up Prompts

### MyoPS Phase 0/1

在 CARE repo 只做 MyoPS Phase 0/1：实现 modality/center 分层的 nnU-Net vs current candidates Dice+HD+HD95+component audit，并加一个不训练的 postprocess/loss smoke 报告；不要提交 Slurm，不要扩 folds。

### Cine postprocess diagnostics

继续 CineMyoPS hosted/HD 诊断：基于 round8 LCC candidate，统一输出 validation/local fold0 的 connected component、HD95、bbox/volume QA，并给出是否停止 Cine postprocess 的中文结论；不要上传 validation zip。

### DA normalization audit

实现 CARE MyoPS/Cine 的 DA normalization audit：按 modality group 和 center 比较 clipping、z-score、robust-z、histogram matching、Fourier perturbation 的 intensity 与现有 error 关联，只写诊断表和中文报告，不训练模型。
