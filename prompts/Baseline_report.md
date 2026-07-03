# Baseline Technical Report: MyoPS-Net, U-MyoPS, and CineMyoPS in CARE

**Date:** 2026-05-02

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Task Formulation](#2-task-formulation)
3. [Method Summaries](#3-method-summaries)
4. [Mapping to Code in This Repository](#4-mapping-to-code-in-this-repository)
5. [Paper-Reported Performance](#5-paper-reported-performance)
6. [Discussion: Paper Setting vs CARE nnU-Net Setting](#6-discussion-paper-setting-vs-care-nnu-net-setting)
7. [Sources Checked](#7-sources-checked)

## 1. Executive Summary

MyoPS-Net (Qiu et al., 2023) addresses myocardial pathology segmentation as a multi-sequence cardiac MR fusion problem in which the network may receive up to five end-diastolic CMR inputs: cine bSSFP C0, LGE, T2-weighted, T1 mapping, and T2* mapping. Its central claim is not merely that multiple sequences help, but that the **fusion mechanism should remain usable when some clinically desirable sequences are absent**. The paper therefore formulates scar and edema segmentation as a flexible multi-sequence pathology task, with separate pathology-oriented decoders and explicit structural priors. Relative to the other two works, MyoPS-Net is the broadest in modality coverage and the most explicit about missing-modality deployment scenarios, but it assumes that the different sequences are already aligned or can be treated as co-registered on the working grid.  -> **“多序列怎么融合、缺模态怎么办”** 的端到端病理分割网络

U-MyoPS (Ding et al., 2023) tackles a different bottleneck: in routine practice, multi-sequence CMR is often not spatially aligned because of respiratory motion and acquisition differences. The paper therefore reframes **MyoPS as a joint registration-and-segmentation problem over unaligned bSSFP cine, LGE, and T2 images**. Its output is still pathology segmentation, centered on scar and edema, but the contribution is architectural: alignment, anatomical extraction, and pathology inference are optimized together, with LGE used as a common reference image. Relative to MyoPS-Net, U-MyoPS narrows the input set to the clinically dominant three-sequence setting but makes the alignment problem first-class rather than assumed away.  -> **“未对齐的多序列怎么先在模型里对齐再分割”** 的联合框架

CineMyoPS (Ding et al., 2025) takes the strongest clinical simplification: it aims to segment myocardial pathologies from cine CMR alone, without requiring LGE or T2 at inference time. The paper argues that infarct-related motion abnormality and anatomical remodeling, if learned well across the cardiac cycle, contain enough information to support joint scar-and-edema prediction. Its output remains pathology segmentation, but the inference setting is fundamentally different from the two multi-sequence methods: CineMyoPS is a single-modality, contrast-free cine model whose supervision is derived from registered pathology labels but whose deployment does not require those contrast-enhanced sequences. This makes CineMyoPS the most clinically convenient setting of the three, while also making it the most demanding inferential leap.

## 2. Task Formulation

### 2.1 Comparative Overview


| Work      | Inputs used for inference                                                                        | Task output as claimed in paper                                                            | Alignment assumption                                                                                             |
| --------- | ------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------- |
| MyoPS-Net | ED cine bSSFP C0, LGE, T2, T1 mapping, T2* mapping; also variant settings with missing sequences | Scar and edema segmentation, with myocardium prior used to localize pathology              | Uses multi-sequence inputs on a common working grid; the paper does not present registration as the main problem |
| U-MyoPS   | bSSFP cine ED, LGE, T2                                                                           | Unified MyoPS in a common space, segmenting scar, edema, and healthy myocardium regionally | Explicitly designed for unaligned MS-CMR; registration is part of the model                                      |
| CineMyoPS | Cine CMR only                                                                                    | Joint scar and edema segmentation from cine alone in a reference-frame space               | No LGE/T2 needed at inference; motion normalizes cine frames to an ED reference                                  |


### 2.2 MyoPS-Net

The MyoPS-Net paper defines its primary input set as five clinically available end-diastolic CMR sequences: balanced steady-state free precession cine at the ED phase (called C0), LGE, T2-weighted CMR, T1 mapping, and T2* mapping. The paper is explicit that C0 provides anatomical boundary information, while LGE, T2, and mapping sequences provide complementary pathology cues, especially for scar and edema (Paper, Introduction; Section 3.1).

The task is not a generic five-class cardiac segmentation task. The paper formulates MyoPS around myocardial pathology, specifically scar and edema, and uses modality-specific pathology decoders: LGE-oriented scar decoding, T2-oriented edema decoding, and mapping-oriented scar decoding in the full model. The myocardium prior and consistency module predicts anatomical support information, but the headline reported results are pathology metrics rather than a standalone five-class label set (Paper, Sections 3.1-3.5; Tables 8-9).

The paper also defines four practical usage scenarios: full five-sequence MyoPS-Net, a three-sequence MyoPS-Net-L setting using C0/LGE/T2, a four-sequence MyoPS-Net-M setting using C0/T2/T1 mapping/T2* mapping, and a mixed model trained across these scenarios (Paper, Table 1; Section 3.5). This matters because the public MICCAI2020 MyoPS challenge comparison in the paper is performed with MyoPS-Net-L, not the full five-sequence model, since the challenge setting does not provide the full five-sequence acquisition described for the private dataset (Paper, Table 8; Table 9).

What the paper does not claim is equally important. It does not report a CARE-style label schema of background, myocardium, LV blood, RV blood, edema, and scar as its principal benchmark target. Its reported headline pathology numbers are scar and edema metrics, and those should not be conflated with later nnU-Net dataset conventions.

### 2.3 U-MyoPS

U-MyoPS uses three sequences: bSSFP cine at the end-diastolic phase, LGE, and T2. The paper emphasizes that bSSFP contributes anatomical boundaries, LGE visualizes scar, and T2 visualizes edema (Paper, Abstract; Introduction; Section III-A). This is therefore still a multi-sequence MyoPS problem, but unlike MyoPS-Net, the paper is centered on the fact that these sequences are often unaligned in practical clinical acquisition.

The task is defined as automatic myocardial pathology segmentation from unaligned MS-CMR, in which the network first registers the inputs into a common space, then extracts anatomy, and finally segments pathology. The paper describes the final result as a unified output containing scar, edema, and healthy myocardium regions. For evaluation in the common space, the overlap between scar and edema is assigned to scar, and the union of scar and edema is treated as edema in the subsequent evaluation and visualization protocol (Paper, Section III-D, especially the metric-definition paragraph immediately before Table II). That union rule is specific to this paper and must be preserved when interpreting its edema Dice.

The key contrast with MyoPS-Net is thus not simply architecture but task definition under acquisition conditions. MyoPS-Net is a multi-sequence fusion network that studies missing-modality use; U-MyoPS is a multi-sequence fusion network that studies unaligned multi-sequence use. Both remain multi-sequence MyoPS methods rather than cine-only pathology methods.

### 2.4 CineMyoPS

CineMyoPS is explicitly a single-modality cine method. Its inference input is a cine CMR sequence only; the paper uses the end-diastolic frame as the common reference image and estimates motion between the reference and the remaining cine frames across the cardiac cycle (Paper, Section II-A). This is the defining contrast with MyoPS-Net and U-MyoPS: no LGE, no T2, and no mapping sequence is required at inference in the paper setting.

The output task remains joint scar and edema segmentation. However, the labels used to supervise this task are constructed by first annotating scar on LGE and edema on T2w, then registering those pathology labels into the ED cine frame and fusing them into a cine-space pathology gold standard (Paper, Section III-A; Fig. 5). In other words, CineMyoPS is not trained from cine-native manual pathology delineation alone; it is supervised by transferred pathology labels, but it predicts directly from cine.

The paper also reports that cine sequences typically contain 25 to 30 frames per cycle and that the best trade-off in its validation experiments is to use 4/6 of the total frames, starting from the reference frame, for the time-series aggregation strategy (Paper, Section III-B; Fig. 6). This frame-subset choice is part of the task specification as actually evaluated by the paper.

What the paper does not claim is that cine inference is equivalent to multi-sequence LGE/T2 inference. The method is a contrast-free surrogate approach. It should therefore not be interpreted as a multi-sequence benchmark in disguise.

## 3. Method Summaries

### 3.1 MyoPS-Net

MyoPS-Net is presented as an end-to-end multi-sequence pathology segmentation network whose central difficulty is how to extract sufficiently informative features from heterogeneous CMR inputs while remaining usable under missing-sequence conditions. The architecture has three major components: a cross-modal feature fusion (CMFF) module, a myocardium prior and consistency (MPC) module, and a pathology inclusiveness (PI) loss (Paper, Section 3; Fig. 2).

The **CMFF module is the core fusion mechanism**. Rather than concatenate all sequences at the input and hope the encoder learns the interactions, MyoPS-Net uses layer-level fusion. For each pathology-oriented branch, it computes multi-scale features for each sequence, applies a pixelwise max-fusion over the other available sequences, and feeds those fused features into the corresponding pathology decoder through skip-like connections (Paper, Section 3.1; Fig. 3). In the full five-sequence setting, *the paper uses three pathology encoders: one for LGE, one for T2, and one for the mapping pair (T1 mapping and T2 mapping)**. **Decoder assignment is clinically biased: LGE and mappings are treated as scar-favoring sources, while T2 is treated as the edema-favoring source** (Paper, Section 3.1).

The **MPC module adds anatomical prior information.** Instead of running a completely separate myocardium segmentation stage and cropping regions of interest, the paper concatenates all five sequences and uses a U-Net backbone to estimate myocardium/LV-related probability maps as a shared structural prior. These maps are then concatenated back with raw pathology-bearing inputs before pathology decoding. The paper also imposes a cosine-similarity consistency loss between the myocardium prior output and the pathology decoders’ implied myocardium representation, so that pathology prediction remains structurally anchored inside myocardium rather than drifting into anatomically implausible regions (Paper, Section 3.2, equations 5-9).

The third idea is the pathology inclusiveness loss. **The paper encodes the clinical prior that scar lies inside edema.** For labeled data, this is implemented as a pair of losses that penalize scar outside edema and encourage edema to include scar; for unlabeled data, an analogous prediction-to-prediction form is proposed. The fully supervised experiments are the primary focus, but the loss is defined for both labeled and unlabeled data (Paper, Section 3.3, equations 10-15). The training loss in the supervised setting combines segmentation, consistency, and inclusiveness terms (Paper, Section 3.4).

At a protocol level, the paper evaluates MyoPS-Net on a 50-case private multi-sequence dataset and on the public MICCAI2020 MyoPS challenge data. Importantly, it treats missing-modality deployment as part of the method definition rather than a post hoc ablation. The MyoPS-Net, MyoPS-Net-L, MyoPS-Net-M, and MyoPS-Net-mix variants are therefore not side notes; they are the operational forms by which the method claims flexibility under practical scanning constraints (Paper, Section 3.5; Table 1).

### 3.2 U-MyoPS

U-MyoPS is best understood as a t**wo-part pipeline trained under a unified optimization framework**: **first, multi-sequence registration plus anatomical extraction; second, pathology segmentation in the aligned common space.** The paper is explicit that registration and pathology segmentation must be conceptually separated, even though both live inside the same end-to-end framework (Paper, Section II; Fig. 2).

The registration component takes three 2D short-axis inputs, `IbSSFP`, `ILGE`, and `IT2`, and sets `ILGE` as the common reference image. Two registration heads predict thin-plate-spline (TPS) control-point displacements that warp the bSSFP and T2 images into LGE space. The grid is parameterized by `m x m` control points, and the paper states that the experiments used 4 x 4 equally spaced control points (Paper, Section II-A; Section III-A). The registration loss is a multi-sequence Dice-based loss defined on anatomical structure labels rather than raw-intensity similarity alone. This is important: the alignment target is downstream task utility, not purely image similarity (Paper, Section II-A, equation 3).

The second stage within the joint block is anatomical structure extraction. A decoder in the LGE branch predicts myocardium structure in the common reference image, but the model does not restrict itself to LGE features. The multi-sequence fusion (MSF) block warps intermediate bSSFP and T2 feature maps into the reference feature space using the TPS parameters and fuses them with the LGE feature maps before anatomy decoding. The design logic is that alignment should occur before feature fusion, not after pathology prediction (Paper, Section II-B; Fig. 3). Additional myocardium decoders on the bSSFP and T2 branches provide consistency constraints, and the hybrid loss `Loss_Hyb = Loss_Reg + lambda (Loss_Cons + Loss_Myo)` jointly optimizes registration, myocardium extraction, and myocardium consistency (Paper, Section II-B, equations 5-7).

Pathology segmentation is handled by a prior-aware sub-network after the common-space myocardium has been estimated. The encoder-decoder pair `EMP` and `DMP` receives the aligned images and a myocardium prior. The spatial prior gate (SPG) uses the myocardium prediction as an attention-like guide to highlight informative regions and suppress anatomically implausible areas before final scar/edema prediction (Paper, Section II-C; Fig. 4). The pathology loss is standard Dice plus cross-entropy in the common space, but the crucial modeling point is that pathology is segmented after registration and after anatomical localization, not directly on unaligned inputs.

The paper’s evaluation protocol also affects interpretation. Scar and edema are originally delineated on different source sequences, then aligned into the common space. The overlap region is assigned to scar, while the union is treated as edema for evaluation (Paper, Section III-D). This means the paper’s “edema” metric is not identical to a naïve edema-only mask in all implementations; it is a union-based target consistent with the MyoPS challenge conventions referenced by the authors.

### 3.3 CineMyoPS

CineMyoPS **combines motion estimation, anatomy segmentation, and pathology segmentation from cine CMR alone**. Unlike the previous two methods, it is not trying to fuse multiple MR contrasts. Instead, it tries to distill pathology-relevant information from three feature families available within cine: motion, anatomy, and texture (Paper, Section II; Fig. 2).

The motion estimation module is a U-shaped registration-style network. Given a cine sequence `I = {Ii}`, it chooses the end-diastolic frame `Ir` as the common reference image and predicts a dense displacement field `Phi_i` between `Ir` and each other frame `Ii`. The transformed frame `I~i = Ii ⊗ Phi_i` allows the method to interpret motion in the reference-frame space. The training losses are an image matching term based on mean squared error between moved and reference images and a smoothness regularizer over the displacement fields (Paper, Section II-A, equations 1-5).

The anatomy segmentation module is another U-shaped subnet that predicts myocardial structure from cine frames. Because annotating all frames would be expensive, the paper supervises the anatomy segmentation on the ED frame and uses a cosine-similarity consistency loss after warping non-reference anatomy predictions into the reference space. This consistency loss ties the anatomy head to the motion estimation head: if motion is estimated well, the transformed anatomy should agree with the ED anatomy label (Paper, Section II-B, equations 6-8). The paper explicitly states that motion and anatomy rely on shared structural cues, which is why it trains them jointly.

The MyoPS module then fuses motion, anatomy, and texture. For each selected frame, the module concatenates three inputs in the ED reference space: the motion field `Phi_i`, the transformed anatomy prediction `Lhat_ai ⊗ Phi_i`, and the transformed cine texture `Ii ⊗ Phi_i`, then predicts a per-frame pathology result `Lhat_pi`. These per-frame results are aggregated across time by summation followed by a convolution and softmax to produce the final ED-space pathology segmentation (Paper, Section II-C, equations 9-10). The aggregation is not incidental. The paper explicitly investigates how much of the cardiac cycle should be used and reports that performance rises and then plateaus, with 4/6 of the cardiac cycle providing the best balance between information content and efficiency (Paper, Section III-B; Fig. 6).

The full loss is `LMyoPS + lambda1 Lanatomy + lambda2 Lcons + lambda3 Lmotion + lambda4 Lsmooth`, with tuned weights `lambda1 = 5`, `lambda2 = 2`, `lambda3 = 1`, and `lambda4 = 100` (Paper, Section II-C; Section III-B). The paper therefore frames CineMyoPS not as a single segmentation head but as a coordinated multitask system where cine-derived motion and cine-derived anatomy help stabilize a difficult surrogate pathology prediction task.

## 4. Mapping to Code in This Repository

### 4.1 Repository-Level Entry Points

The CARE repository groups the paper baselines under `jobs/`, with high-level orchestration described in `jobs/README.md`. That README states that `jobs/MyoPS-Net/`, `jobs/U-MyoPS/`, and `jobs/CineMyoPS/` are the entrypoints for the three paper methods, while `third_party/README.md` identifies the upstream repositories as `QJYBall/MyoPS-Net`, `NanYoMy/myops`, and `NanYoMy/CineMyoPS`, respectively. `env_nnunet.sh` defines active nnU-Net path conventions; the legacy server runbook is archived at `docs/archive/SERVER.md`.

### 4.2 MyoPS-Net Mapping

The CARE entry script is `jobs/MyoPS-Net/run.sh`. It first checks whether `data/benchmarks/MyoPS-Net/train.txt` exists; if not, it runs `code/MyoPS-Net/prepare_myops_net_layout.py` using `env_CARE/bin/python`, then dispatches training via `code/MyoPS-Net/run_train.sh`.

`code/MyoPS-Net/run_train.sh` changes directory into `third_party/MyoPS-Net` and executes `main.py` with `--path` pointing to the CARE-staged benchmark directory. Inside the upstream code, `third_party/MyoPS-Net/main.py` parses arguments and launches `MyoPSNetTrain(args)`. The upstream repository also exposes `predict.py` for inference.

The staging script is clinically important. Its own docstring states that CARE only provides `C0`, `LGE`, `T2`, and `gd`, so it writes zero-filled placeholders for `T1m` and `T2starm` on the LGE grid. It also resamples all available volumes to the LGE reference image. This means the CARE wrapper does not reproduce the full five-sequence acquisition of the paper unless real mapping data are supplied externally. Instead, it adapts CARE data into the file layout that upstream MyoPS-Net expects. That is a repository fact, not an inference.

Verified environment expectations are limited but concrete: `jobs/MyoPS-Net/run.sh` assumes `CARE_ROOT`, `env_CARE/bin/python`, and write access under `data/benchmarks/MyoPS-Net`. No separate `env_nnunet.sh` activation is required by this path. The public code URL stated in the paper and in `third_party/MyoPS-Net/README.md` is `https://github.com/QJYBall/MyoPS-Net`.

### 4.3 U-MyoPS Mapping

The CARE entry script is `jobs/U-MyoPS/run.sh`. It exports `CARE_ROOT`, sources `env_nnunet.sh`, resolves a legacy environment through `CARE_CineMyoPS_ENV` or `CARE_CINEMYOPS_ENV` (defaulting to `${CARE_ROOT}/env_CARE_nnUNet_v1`), and sets `LEGACY_PYTHON`/`UMYOPS_PYTHON` accordingly. It then runs three steps in sequence: `code/U-MyoPS/prepare_u_myops_from_care.py`, `code/U-MyoPS/run_stage1.sh`, and, only if `UMYOPS_RUN_STAGE2=1`, `code/U-MyoPS/run_stage2.sh`.

Stage 1 is the paper’s registration-plus-myocardium part. `code/U-MyoPS/run_stage1.sh` sets `PYTHONPATH` to include `third_party/U-MyoPS_myops/jrs` and executes `third_party/U-MyoPS_myops/jrs/joint_registration_myocardium_segmentation.py`. CARE forces the default stage-1 phase to `train`, because the upstream config otherwise defaults to `metric` and would not actually train. The upstream entry file instantiates `TpsSegNetConfigRJ_Myo` and `ExperimentRJ_Myo`, then branches on `args.phase`.

Stage 2 is the pathology nnU-Net part. `code/U-MyoPS/run_stage2.sh` sets classic nnU-Net v1 paths via `nnUNet_raw_data_base`, `nnUNet_preprocessed`, and `RESULTS_FOLDER`, rooted under `third_party/U-MyoPS_myops/outputs/nnunet/{raw,prepro,output}` unless overridden. It then executes `third_party/U-MyoPS_myops/jrs/pathology_segmentation_train.py`, which is a thin wrapper around the vendored nnU-Net training entrypoint.

The most important integration caveat is spelled out in `third_party/U-MyoPS_myops/README-CN.md`: Stage 1 outputs checkpoints and `gen_res` artifacts, but it does not itself generate the nnU-Net Task folder required by Stage 2; the repository does not provide a one-click exporter from Stage-1 outputs to Stage-2 raw nnU-Net data. The same document explicitly states that this missing transformation must be implemented separately or obtained from the authors. Therefore, the CARE wrapper exposes the two stages, but the exact paper-faithful bridge between them is incomplete in the current repository.

The data-preparation script also deserves attention. `code/U-MyoPS/prepare_u_myops_from_care.py` exports CARE cases into the `jrs` dataloader layout, but its docstring states that it uses a “unified gd for all three label paths (clinical approximation).” That is a concrete simplification relative to the original paper setting, where anatomy and pathology labels arise from sequence-specific annotation and common-space construction. The public upstream URL recorded in `third_party/README.md` is `https://github.com/NanYoMy/myops`.

### 4.4 CineMyoPS Mapping

The CARE entry script is `jobs/CineMyoPS/run.sh`. It exports `CARE_ROOT`, sources `env_nnunet.sh`, resolves a legacy environment via `CARE_CineMyoPS_ENV` or `CARE_CINEMYOPS_ENV` (again defaulting to `${CARE_ROOT}/env_CARE_nnUNet_v1`), runs `code/CineMyoPS/prepare_task025_from_care.py`, and then calls `code/CineMyoPS/run_train.sh`.

`code/CineMyoPS/run_train.sh` changes into `third_party/CineMyoPS/code`, prepends that directory to `PYTHONPATH`, and executes `Lascar_3_train.py` with defaults `CINE_NNUNET_DIM=2d`, `CINE_NNUNET_TRAINER=nnUNetTrainerV2`, `CINE_NNUNET_TASK=Task025_Cine_Seg`, and `CINE_NNUNET_EPOCHS=500`. `Lascar_3_train.py` is itself a wrapper around the vendored nnU-Net v1 training stack. For inference, CARE provides `code/CineMyoPS/run_test.sh`, which dispatches to `third_party/CineMyoPS/code/Lascar_4_test.py`.

The preprocessing dependency is explicit in `code/CineMyoPS/ensure_task025_v1_preprocessed.sh`: the CineMyoPS code expects an nnU-Net v1 raw task and corresponding planned/preprocessed files. That helper script will create raw data under `$nnUNet_raw/Task025_Cine_Seg` and run the old v1 planner if necessary, but `jobs/CineMyoPS/run.sh` itself does not call that helper automatically.

The CARE staging script again diverges from the paper setting in a verifiable way. `code/CineMyoPS/prepare_task025_from_care.py` extracts a single 3D frame from each 4D cine sequence, choosing the middle frame by default (`--time-index -1`) unless overridden. More importantly, its `dataset.json` defines a compact label schema with only `background`, `myocardium`, `LV_blood`, and `scar`. The script’s explicit compact map keeps only labels `0`, `1`, `2`, and `5 -> 3`, which means edema is not exported into this CARE task. Consequently, the current CARE wrapper is not a faithful implementation of the paper’s joint scar-and-edema cine-only target; it is a repository-specific nnU-Net v1 task adaptation built from CARE labels. That mismatch should be treated as factual when interpreting any future local runs.

The public upstream URL recorded in `third_party/README.md` is `https://github.com/NanYoMy/CineMyoPS`.

### 4.5 Environment Summary

The shared environment facts that can be verified from files are as follows.

- `env_nnunet.sh` defines `nnUNet_raw`, `nnUNet_preprocessed`, and `nnUNet_results` under `data/nnUNet/`, plus `UMYOPS_STAGE2_TASK=Task901_CARE_UmyopsPathology` and `UMYOPS_RUN_STAGE2=0` by default.
- `jobs/U-MyoPS/run.sh` and `jobs/CineMyoPS/run.sh` both assume an nnU-Net v1-style environment at `${CARE_ROOT}/env_CARE_nnUNet_v1` unless overridden.
- The archived `docs/archive/SERVER.md` runbook states that CARE’s own nnU-Net datasets `Dataset501_CAREMyoPS` and `Dataset502_CARECineMyoPS` use the label classes `0 background, 1 myocardium, 2 LV blood, 3 RV blood, 4 edema, 5 scar`, which is distinct from the paper-reported task semantics of the baseline papers.

Where the repository does not make the exact environment unambiguous, this report treats it as unclear rather than inferred.

## 5. Paper-Reported Performance

### 5.1 MyoPS-Net

The principal paper table for the private dataset is Table 8. It reports scar and edema metrics separately for the full model and the missing-sequence variants. On the public MICCAI2020 MyoPS challenge dataset, the directly reported single-model result is `MyoPS-Net-L`, which matches the three-sequence challenge setting rather than the full five-sequence private-dataset setting (Paper, Table 8).

#### Table 8. Quantitative evaluation of MyoPS-Net variants (paper-reported)


| Model                                  | Scar Dice     | Scar HD (mm) | Scar ACC      | Scar SEN      | Scar SPE      | Edema Dice    | Edema HD (mm) | Edema ACC     | Edema SEN     | Edema SPE     |
| -------------------------------------- | ------------- | ------------ | ------------- | ------------- | ------------- | ------------- | ------------- | ------------- | ------------- | ------------- |
| MyoPS-Net, private dataset             | 0.656 ± 0.113 | 11.4 ± 9.45  | 0.886 ± 0.049 | 0.626 ± 0.135 | 0.946 ± 0.045 | 0.741 ± 0.085 | 18.6 ± 10.6   | 0.829 ± 0.073 | 0.775 ± 0.160 | 0.858 ± 0.073 |
| MyoPS-Net-L, private dataset           | 0.622 ± 0.116 | 11.4 ± 8.17  | 0.881 ± 0.050 | 0.569 ± 0.153 | 0.952 ± 0.040 | 0.727 ± 0.102 | 21.2 ± 13.2   | 0.818 ± 0.082 | 0.763 ± 0.171 | 0.858 ± 0.084 |
| MyoPS-Net-M, private dataset           | 0.501 ± 0.181 | 27.5 ± 14.5  | 0.810 ± 0.060 | 0.609 ± 0.224 | 0.856 ± 0.065 | 0.676 ± 0.124 | 25.1 ± 11.9   | 0.772 ± 0.075 | 0.787 ± 0.173 | 0.763 ± 0.095 |
| MyoPS-Net-L, public MICCAI2020 dataset | 0.647 ± 0.258 | 15.5 ± 14.9  | 0.865 ± 0.089 | 0.713 ± 0.234 | 0.919 ± 0.054 | 0.722 ± 0.135 | 22.9 ± 16.2   | 0.791 ± 0.109 | 0.727 ± 0.172 | 0.827 ± 0.110 |


Source: Qiu et al., 2023, Table 8.

#### Table 9. Public MICCAI2020 challenge comparison (paper-reported)


| Method               | Scar Dice     | Edema Dice    | Avg   |
| -------------------- | ------------- | ------------- | ----- |
| AWSnet**             | 0.678 ± 0.242 | 0.735 ± 0.111 | 0.707 |
| Modified nnUNet**    | 0.672 ± 0.244 | 0.731 ± 0.109 | 0.702 |
| Modified nnUNet      | 0.645 ± 0.236 | 0.690 ± 0.128 | 0.668 |
| EfficientSeg**       | 0.647 ± 0.279 | 0.709 ± 0.122 | 0.678 |
| CMS-UNet             | 0.581 ± 0.268 | 0.725 ± 0.110 | 0.653 |
| MF&DFA-Net           | 0.605 ± 0.263 | 0.656 ± 0.138 | 0.631 |
| MyoPS-Net-L (ours)   | 0.647 ± 0.258 | 0.722 ± 0.135 | 0.685 |
| MyoPS-Net-L** (ours) | 0.661 ± 0.255 | 0.742 ± 0.124 | 0.702 |


Source: Qiu et al., 2023, Table 9. `*`* denotes ensemble learning in the original paper table.

**Metric-definition note.** The MyoPS-Net paper reports pathology metrics for scar and edema, with Dice, HD, ACC, SEN, and SPE as its main private/public quantitative measures. These are not presented as a six-label whole-heart segmentation benchmark (Paper, Section 4.1; Tables 8-9).

### 5.2 U-MyoPS

For U-MyoPS, the main private-dataset comparison is Table II on the pMM-CMR dataset, and the public benchmark comparison is Table VI on the MYOPS2020 challenge dataset. The PDF text layer is not cleanly machine-readable for these tables, so the values below were transcribed from rendered table images of the paper PDF rather than guessed from narrative prose. Only cells that could be read robustly are included.

#### Table II. pMM-CMR test performance of different MyoPS methods (paper-reported)


| Method         | bSSFP | LGE | T2  | Scar Dice (%) | Scar Sen (%)  | Scar Pre (%)  | Scar HD (mm)  | Edema Dice (%) | Edema Sen (%) | Edema Pre (%) | Edema HD (mm) |
| -------------- | ----- | --- | --- | ------------- | ------------- | ------------- | ------------- | -------------- | ------------- | ------------- | ------------- |
| nn-UnetUna     | ✓     | ✓   | ✓   | 44.16 (17.47) | 46.68 (20.30) | 44.05 (18.11) | 37.88 (21.84) | 66.48 (14.74)  | 70.97 (13.26) | 64.81 (18.47) | 38.28 (23.40) |
| PSNLGE         | ×     | ✓   | ×   | 55.99 (17.52) | 61.66 (20.21) | 53.25 (18.80) | 43.01 (23.08) | N/A            | N/A           | N/A           | N/A           |
| PSNT2          | ×     | ×   | ✓   | N/A           | N/A           | N/A           | N/A           | 67.82 (19.01)  | 79.42 (12.86) | 61.97 (22.94) | 31.07 (23.79) |
| MvMM+nn-Unet   | ✓     | ✓   | ✓   | 57.18 (11.18) | 62.29 (12.59) | 54.23 (13.31) | 36.93 (17.50) | 69.87 (14.13)  | 78.42 (12.66) | 65.25 (17.96) | 37.79 (22.29) |
| MvMM+AWSnet    | ✓     | ✓   | ✓   | 62.38 (14.47) | 68.02 (18.28) | 59.20 (13.52) | 36.56 (15.53) | 74.23 (12.87)  | 82.13 (8.875) | 70.03 (17.79) | 30.12 (22.97) |
| U-MyoPSbLT     | ✓     | ✓   | ✓   | 64.92 (9.816) | 68.30 (12.56) | 63.34 (11.71) | 29.16 (16.65) | 76.01 (9.784)  | 80.49 (8.942) | 73.53 (14.05) | 27.89 (18.45) |
| U-MyoPSw/o MSF | ✓     | ✓   | ✓   | 64.58 (9.762) | 64.76 (12.08) | 66.12 (11.77) | 33.61 (18.21) | 75.15 (11.21)  | 79.78 (10.56) | 72.56 (14.88) | 32.65 (21.38) |
| U-MyoPSw/o SPG | ✓     | ✓   | ✓   | 60.61 (10.11) | 65.03 (14.21) | 58.71 (12.36) | 34.17 (19.32) | 71.69 (13.56)  | 75.06 (11.97) | 70.94 (18.38) | 32.98 (19.61) |


Source: Ding et al., 2023, Table II.

#### Table VI. MYOPS2020 challenge Dice comparison (paper-reported)


| Method     | Scar (%) | Edema (%) | Average (%) |
| ---------- | -------- | --------- | ----------- |
| UESTC*     | 67.2     | 73.1      | 70.2        |
| UBA*       | 66.6     | 69.8      | 68.2        |
| NPU*       | 64.7     | 70.9      | 67.8        |
| UESTC      | 64.1     | 69.5      | 66.8        |
| NPU        | 62.6     | 69.5      | 66.1        |
| CQUPT II   | 58.1     | 72.5      | 65.3        |
| U-MyoPSbLT | 64.7     | 72.6      | 68.6        |


Source: Ding et al., 2023, Table VI.

**Metric-definition note.** U-MyoPS evaluates pathology in a common space after transferring source labels. For overlapping scar/edema regions, the overlap is counted as scar, and the union of scar and edema is referred to as edema in evaluation and visualization (Paper, Section III-D, metric-definition paragraph before Table II). This is a paper-specific label rule and should be preserved when interpreting the reported edema Dice.

### 5.3 CineMyoPS

The primary method-comparison table for CineMyoPS is Table V on the test dataset. The paper also includes Table VI, which is a literature summary contrasting contrast-enhanced and non-contrast MyoPS studies; it is useful for context but is not a same-dataset head-to-head benchmark in the strictest sense.

#### Table V. Test-set performance of cine-based MyoPS methods (paper-reported)


| Method     | Scar Dice   | Scar Pre    | Scar Sen    | Scar Spe    | Scar NPV    | Scar HD (mm)  | Edema Dice  | Edema Pre   | Edema Sen   | Edema Spe   | Edema NPV   | Edema HD (mm) |
| ---------- | ----------- | ----------- | ----------- | ----------- | ----------- | ------------- | ----------- | ----------- | ----------- | ----------- | ----------- | ------------- |
| nnUnet     | 0.42 ± 0.17 | 0.51 ± 0.21 | 0.42 ± 0.20 | 0.90 ± 0.04 | 0.85 ± 0.09 | 29.68 ± 11.14 | 0.47 ± 0.14 | 0.72 ± 0.17 | 0.42 ± 0.16 | 0.90 ± 0.06 | 0.68 ± 0.16 | 28.94 ± 10.50 |
| OFSeg      | 0.49 ± 0.15 | 0.53 ± 0.19 | 0.57 ± 0.21 | 0.87 ± 0.06 | 0.88 ± 0.08 | 25.51 ± 10.58 | 0.55 ± 0.12 | 0.72 ± 0.15 | 0.57 ± 0.17 | 0.86 ± 0.08 | 0.74 ± 0.15 | 26.01 ± 11.38 |
| ConvLSTM   | 0.47 ± 0.14 | 0.56 ± 0.19 | 0.52 ± 0.21 | 0.88 ± 0.09 | 0.87 ± 0.09 | 24.03 ± 9.92  | 0.56 ± 0.10 | 0.76 ± 0.13 | 0.54 ± 0.15 | 0.88 ± 0.09 | 0.73 ± 0.15 | 25.17 ± 9.81  |
| 2D+1D Unet | 0.50 ± 0.14 | 0.59 ± 0.17 | 0.54 ± 0.20 | 0.90 ± 0.06 | 0.87 ± 0.08 | 23.47 ± 11.74 | 0.56 ± 0.09 | 0.78 ± 0.13 | 0.53 ± 0.15 | 0.90 ± 0.07 | 0.72 ± 0.15 | 24.65 ± 11.19 |
| CineMyoPS  | 0.53 ± 0.12 | 0.60 ± 0.18 | 0.57 ± 0.19 | 0.90 ± 0.07 | 0.88 ± 0.09 | 21.40 ± 12.24 | 0.57 ± 0.08 | 0.79 ± 0.13 | 0.53 ± 0.14 | 0.91 ± 0.07 | 0.72 ± 0.14 | 24.24 ± 11.71 |


Source: Ding et al., 2025, Table V.

#### Table VI. Literature summary included in the CineMyoPS paper


| Study                         | Scar Dice | Edema Dice |
| ----------------------------- | --------- | ---------- |
| UESTC, contrast               | 0.64      | 0.70       |
| UMyoPS, contrast              | 0.65      | 0.73       |
| MyoPS-Net, contrast           | 0.66      | 0.74       |
| PSCGAN, non-contrast          | 0.93      | -          |
| MuTGAN, non-contrast          | 0.90      | -          |
| MI-Segmentation, non-contrast | 0.86      | -          |
| CineMyoPS, non-contrast       | 0.53      | 0.57       |


Source: Ding et al., 2025, Table VI.

**Metric-definition note.** CineMyoPS reports pathology Dice/HD and related classification metrics on cine-space scar and edema labels transferred from LGE/T2w by registration. The paper’s reference frame is the ED cine image, and its final segmentation is produced in that reference-frame space (Paper, Sections II-C and III-A).

## 6. Discussion: Paper Setting vs CARE nnU-Net Setting

The paper settings and the CARE repository settings should not be collapsed into a single benchmark narrative.

First, the CARE repository’s own nnU-Net datasets, as documented in the archived `docs/archive/SERVER.md` runbook and active conversion code, use a six-label schema: background, myocardium, LV blood, RV blood, edema, and scar. **None of the three papers reports its main results in that exact label schema.** MyoPS-Net and U-MyoPS report pathology-centric scar and edema performance, with auxiliary anatomy prediction supporting the model. CineMyoPS reports cine-space scar and edema prediction, not a six-class CARE label benchmark.

Second, the CARE wrappers for the paper baselines are adapters rather than perfect reproductions of the original paper protocols. `code/MyoPS-Net/prepare_myops_net_layout.py` zero-fills missing `T1m` and `T2starm` inputs when only CARE `C0/LGE/T2` are available. `code/U-MyoPS/prepare_u_myops_from_care.py` explicitly uses a unified ground truth as a “clinical approximation” for multiple label paths. `code/CineMyoPS/prepare_task025_from_care.py` exports a single-frame compact task that currently keeps myocardium, LV blood, and scar, but not the paper’s joint scar-and-edema target. These are repository facts and should be treated as methodological adaptation layers.

Third, because no validated CARE metrics files were supplied for this request, no numerical comparison should be made between the paper tables above and any local CARE training logs. The proper interpretation is narrower: the tables in Section 5 are paper-reported baselines, while the repository mapping in Section 4 explains how CARE attempts to stage and run related code paths. That is enough to support rigorous documentation, but not enough to claim replication or superiority of any local CARE run.

## 7. Sources Checked

- `literature/Qiu 等 - 2023 - MyoPS-Net Myocardial pathology segmentation with flexible combination of multi-sequence CMR images.pdf`
- `literature/Ding 等 - 2023 - Aligning Multi-Sequence CMR Towards Fully Automated Myocardial Pathology Segmentation.pdf`
- `literature/Ding 等 - 2025 - CineMyoPS Segmenting Myocardial Pathologies from Cine Cardiac MR.pdf`
- `jobs/README.md`
- `jobs/MyoPS-Net/run.sh`
- `jobs/U-MyoPS/run.sh`
- `jobs/CineMyoPS/run.sh`
- `third_party/README.md`
- `third_party/MyoPS-Net/README.md`
- `third_party/U-MyoPS_myops/README.md`
- `third_party/CineMyoPS/README.md`
- `code/MyoPS-Net/prepare_myops_net_layout.py`
- `code/MyoPS-Net/run_train.sh`
- `third_party/MyoPS-Net/main.py`
- `third_party/MyoPS-Net/predict.py`
- `code/U-MyoPS/prepare_u_myops_from_care.py`
- `code/U-MyoPS/run_stage1.sh`
- `code/U-MyoPS/run_stage2.sh`
- `third_party/U-MyoPS_myops/README-CN.md`
- `third_party/U-MyoPS_myops/jrs/joint_registration_myocardium_segmentation.py`
- `third_party/U-MyoPS_myops/jrs/pathology_segmentation_train.py`
- `code/CineMyoPS/prepare_task025_from_care.py`
- `code/CineMyoPS/run_train.sh`
- `code/CineMyoPS/run_test.sh`
- `code/CineMyoPS/ensure_task025_v1_preprocessed.sh`
- `third_party/CineMyoPS/code/Lascar_3_train.py`
- `third_party/CineMyoPS/code/Lascar_4_test.py`
- `third_party/CineMyoPS/code/nnunet/paths.py`
- `env_nnunet.sh`
- `docs/archive/SERVER.md`
