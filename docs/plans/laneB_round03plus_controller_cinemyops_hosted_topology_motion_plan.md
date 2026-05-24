# Lane B CineMyoPS Hosted/HD Repair and Motion Route Plan

Date: 2026-05-20

Plan metadata:
- Type: lane controller
- Lane: B, CineMyoPS / `myocardium_cinemyops`
- Round scope: Round3 and later
- Status: active controller; keep stable unless hosted metric interpretation changes
- Parent roadmap: `/overflow/htzhu/CARE/TODO.md`
- Parent plan: none
- Function: define Cine hosted/HD repair, topology gates, validation semantics, and later motion/strain/pretrained-cine route
- Do not: use this file as a per-round execution log; create `laneB_roundNN_status_topic_execution.md` for round-specific work

本计划是 CARE Myocardium Lane B 的执行控制文档。短期目标是修复当前 CineMyoPS branch 在 hosted `myocardium_cinemyops` 上的 HD/component 风险；中期目标是转向 motion/strain/pretrained-cine route，而不是继续围绕本地 `class_1` proxy 盲调。

## 1. 执行决策

- 建议提交或检查 round8 LCC HD-repair candidate，但只能作为 hosted calibration experiment：`results/submissions/care_myocardium_validation/upload_ready/nnUNet_MyoPS+CineMyoPS_pathology_direct_lcc_hd_repair_20260519_083839/CARE-Myocardium-OrganAgent.zip`。
- 该 hosted experiment 要回答的问题：hosted `myocardium_cinemyops` 是否主要惩罚 raw `2221` scar/pathology 的 disconnected components 与 HD，而不是本地 `class_1` myocardium proxy。
- 这不是最终模型：LCC 是 export-only topology repair；它没有增加 motion、strain 或 cine pathology 信息，也可能误删真实多灶 scar。若 hosted Dice/HD 仍低，应停止继续小 postprocess，转入 `src/` motion/strain/pretrained-cine route。
- 一次 validation zip 同时含 `MyoPS/` 与 `CineMyoPS/`，返回 `myops_scar`、`myops_edema`、`myocardium_cinemyops` 三项；不要规划 cine-only upload，除非平台明确支持。

## 2. 当前 Wrapper 审计

- 数据准备：
  - Legacy `Task025_Cine_Seg`：`code/CineMyoPS/prepare_task025_from_care.py` 抽单帧，默认 temporal midpoint，标签压缩为 `{0:bg,1:myocardium,2:LV_blood,3:scar}`。
  - Current `Task026_Cine_4D`：`code/CineMyoPS/prepare_task026_cine_4d.py` 和 `task026_utils.py` 从 4D cine 采样 `CINE_NUM_FRAMES=4`，ED 固定 `t=0`，写 split-channel nnU-Net v1 raw。
- 训练和推理入口：
  - 训练：`code/CineMyoPS/run_train.sh` -> `third_party/CineMyoPS/code/Lascar_3_train.py`，默认 `CARECineMyoPSTrainer` / `Task026_Cine_4D` / fold0。
  - 推理：`code/CineMyoPS/export_protocol_val_predictions.sh` -> `run_test.sh` -> `Lascar_4_test.py`；submission 推理由 `scripts/submission/prepare_care_myocardium_validation.py::run_cinemyops_predict` 调用。
  - Slurm：`jobs/CineMyoPS/*`；当前 packaging wrapper 是 `jobs/submission/prepare_care_myocardium_validation_cinemyops_pathology_direct.sh`。
- 标签与 paper mismatch：
  - CARE CineMyoPS label 只有 myocardium/LV/scar，无 RV、无 edema；compact map 是 `{0:0,1:1,2:2,5:3}`。
  - 原 paper 目标是 cine-only joint scar+edema pathology；当前 CARE trainer 的 pathology head 是 scar-only 2 类，`CARECineSegLoss` 明确要求 `pathology_pred.shape[1]==2`。
  - `cardiac_seg` 保留 4 channels，但 compact label 的 scar 在 anatomy target 中被映射回 myocardium；没有真实 RV supervision。
  - paper 的 time-series pathology aggregation 在 CARE wrapper 中基本丢失：模型使用多帧 motion summary，但推理输出由 ED anatomy softmax 和 scar-only pathology softmax 组合。
- 输出约定：
  - compact prediction：`0 bg, 1 myocardium, 2 LV_blood, 3 scar`。
  - submission raw conversion：`CINE_COMPACT_TO_RAW={0:0,1:200,2:500,3:2221}`；无 `600` RV、无 `1220` edema。
  - `--cine-combine-mode` 支持 `current`、`cardiac_only`、`myocardium_gated_scar`、`pathology_direct`；round7 hosted package 使用 `pathology_direct`。
- 本地 metric 与诊断：
  - `scripts/evaluation/run_unified_eval_model.sh CineMyoPS` 调用 `evaluate_predictions.py`，默认 foreground `1,2,3`；`class_1` 是 myocardium proxy，`class_3` 是 scar sanity。
  - HD/HD95 由 `evaluate_predictions.py --hd --hd95` 计算。
  - component/volume/bbox 诊断在 `scripts/evaluation/cinemyops_round8_hd_repair.py` 和新增 `scripts/evaluation/cinemyops_component_hd_audit.py`；后者用于统一 before/after compact + raw zip per-case diagnostics。

## 3. Hosted Metric 不确定性

| hypothesis | hosted `myocardium_cinemyops` 可能评分对象 | 必跟踪 local proxy |
| --- | --- | --- |
| H1 | raw `2221` scar/pathology，且 HD 极敏感 | compact `class_3` Dice/HD/HD95、raw `2221` components、small/remote FP、scar volume |
| H2 | myocardium `200`，但被 scar fallback/topology 间接影响 | compact `class_1` Dice/HD/HD95、raw `200` bbox/volume、scar-in-anatomy ratio |
| H3 | composite foreground/topology metric | class_1/class_2/class_3 Dice+HD95、component count、foreground bbox sanity |
| H4 | validator label semantics 与本地 compact/raw mapping 有差异 | raw label histogram、per-case non-empty labels、manifest mapping、one-voxel fallback cases |

最小 hosted calibration sequence，不在本轮执行：

1. Upload A：round8 `pathology_largest_component` candidate with unchanged nnU-Net MyoPS branch。若 hosted HD 大幅改善且 Dice 稳定或改善，则支持 H1。
2. Upload B：仅在 A 结果模糊时使用 round8 nnU-Net Cine 5-fold baseline package，并记录 fallback cases。它测试 hosted metric 是否更偏好 conservative anatomy branch。

两次以内停止；不要继续上传 small variants 做盲调。

## 4. 短期 Repair 计划

- 新增 `scripts/evaluation/cinemyops_component_hd_audit.py`，对 protocol fold0 与 validation prediction dirs 统一输出 before/after。
- Postprocess modes：
  - `pathology_largest_component`：保留最大 `class_3` / raw `2221` component。
  - `remove_small_remote_components`：删除低于 train fold0 scar volume percentile 或与 anatomy bbox 距离异常的小 component。
  - `volume_guard`：以 fold0 train scar volume p95/p99 和 validation predicted volume ratio 做上限，不删除主病灶。
  - `bbox_center_distance_guard`：记录 scar bbox 到 anatomy bbox 的 mm gap、center distance、z-span；超阈值删除或 fallback。
  - `myocardium_anatomy_guard`：scar 必须落在 myocardium/LV 扩张 ROI 附近；只作为 soft guard，不能硬删所有 myocardium 外 lesion。
  - `unsafe_fallback`：若 repair 后 scar 体积为 0、最大 component fraction 异常、或 bbox/volume 超出 train distribution，则 fallback 到原 CineMyoPS 或 nnU-Net Cine branch，并在 manifest 记录。
- 诊断表字段固定为：
  - `case, variant, dice_class_1, dice_class_3, hd_class_1, hd_class_3, hd95_class_1, hd95_class_3, scar_voxels, scar_components, largest_component_frac, removed_voxels, removed_components, bbox_distance_mm, center_distance_mm, anatomy_voxels, scar_to_anatomy_volume_ratio, fallback_used, action_reason`
- 短期 gate：`class_3` HD/HD95 必须下降；`class_3` Dice 不得明显下降；component count 必须下降且不能把 GT-positive plausible lesion 删除成 empty。

## 5. 中期 Model Route

- Pretrained cine anatomy route，快速优先：
  - CineMA：先做 frozen/import smoke 和 single-frame anatomy logits，不下载大权重除非下一执行 pass 获授权；目标是 ROI/anatomy feature，不直接当 scar model。
  - CorSeg-CineSAX / MedNeXt-L：优先做 anatomy mask + topology postprocess smoke；适合减少 bbox/component/HD failure。
  - nnU-Net Task114 M&Ms：仅作 anatomy warm start 或 ROI reference；大权重需单独批准下载。
- Motion/strain route，中风险：
  - Optical-flow/DVF features：先用 classical/轻量 flow 生成 ED-to-ES motion magnitude/strain proxy，作为 frozen feature channel。
  - VoxelMorph：只做 one-case registration audit，必须记录 Jacobian/folding、warped anatomy overlap、runtime；不能只看 Dice。
  - StrainNet：先做 frozen strain-map generation on one CARE cine case；若需要 contours 或外部格式复杂，立即 fail-fast。
  - MTI-style branch：reimplement concept using CARE-only data，不使用外部 supervised data。
- Anatomy route：把 robust myocardium/LV/RV segmentation 作为 ROI 或 auxiliary head；CARE Cine raw submission 仍只写 `{200,500,2221}`。
- Pathology route：scar/pathology head 必须用 HD-aware loss、component-aware postprocess、volume/bbox guards；不能只优化 local `class_1`。
- 高风险 future：SegMorph、MFD-V2V/LTMA、diffusion/video generative route 只做 paper/interface note；除非 postprocess 和 pretrained anatomy smoke 全失败，不进入实现。

## 6. Candidate Asset Screening Matrix

| name | URL | role | weights | license | pretrained data | compliance risk | benefit | difficulty | minimal smoke | fail-fast |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CineMA | https://huggingface.co/mathpluscode/CineMA / https://github.com/mathpluscode/CineMA | cine anatomy/foundation backbone | yes | MIT per local note; verify before use | UK Biobank cine; finetuned ACDC/M&Ms etc. | low if public weights only | strong anatomy/ROI feature | low-med | import config + run 1 CARE ED frame | no usable logits/ROI or license mismatch |
| CorSeg-CineSAX | https://github.com/RunhaoXu2003/CorSeg | cine anatomy + topology | yes | paper CC BY 4.0; repo license verify | 1555 multi-center cine SAX | low-med | reduce anatomy/topology HD errors | low-med | frozen anatomy mask on 1 fold0 case | topology deletes scar support or no license |
| ViTa | https://github.com/Yundi-Zhang/ViTa | 3D+T cine foundation backbone | yes/likely | MIT per local note; verify | 42k UKBB cine + tabular | low for weights, medium for integration | temporal representation | med | metadata/import-only smoke | requires tabular path or too heavy |
| StrainNet | https://github.com/EpsteinLabUVA/StrainNet | frozen strain feature route | yes/unclear | verify | cine contours/strain | medium | motion abnormality cue | med | one-case strain-map generation | contour/input mismatch or unstable output |
| MTI-MyoScarSeg | https://arxiv.org/abs/2501.05241 | motion-texture scar concept | no public code found | paper only | paper dataset | low if reimplemented CARE-only | direct scar cue | high | optical-flow feature prototype | no HD/component gain or runtime too high |
| VoxelMorph | https://github.com/voxelmorph/voxelmorph | frame registration/DVF features | generic possible | verify; package licensing can differ by source | mostly non-cardiac generic; cardiac checkpoints need provenance | medium | motion field feature | med | ED-ES registration + Jacobian audit | folding/topology failure |
| SegMorph | https://eprints.gla.ac.uk/332276/ | joint motion+segmentation concept | no clear public weights | article CC BY; code unclear | cardiac cine in paper | low if concept-only | temporal consistency | high | paper/interface review only | needs full reimplementation |
| cineCMR-SAM | https://github.com/zhennongchen/cineCMR-SAM | temporal SAM anatomy support | yes/unclear | verify | public cine CMR + SAM | medium | anatomy/ROI support | med | prompted anatomy on 1 case | prompt not automatable or license risk |
| InverseForm | https://github.com/Qualcomm-AI-research/InverseForm | HD/boundary-aware loss | no CARE weights | verify | none | low | HD/HD95 repair | low-med | loss gradient check on CARE tensors | Dice gain with HD regression |
| nnU-Net Task114 M&Ms | https://zenodo.org/records/4288362 | anatomy pretrained baseline | yes, large | Zenodo license verify | M&Ms cardiac MRI | low-med; large download | cross-center anatomy warm start | low | metadata-only; no download now | label mismatch or license unclear |
| current CineMyoPS paper repo | local `third_party/CineMyoPS` | baseline/paper reference | Baidu link in README | no local LICENSE found | paper multi-center cine | medium | compare intended paper vs CARE wrapper | already integrated | audit architecture/labels only | no edema/RV/time aggregation parity |

## 7. Experiment Plan, No Execution Now

| phase | future command/output | runtime | stop criteria |
| --- | --- | ---: | --- |
| Phase 0: reproduce diagnostics | `python scripts/evaluation/cinemyops_component_hd_audit.py --pred-dirs pathology_direct=results/predictions/CineMyoPS_R6_pathology_direct/fold_0 lcc=results/predictions/CineMyoPS_R8_hd_repair/pathology_largest_component/fold_0 --baseline-variant pathology_direct`; outputs `results/diagnostics/CineMyoPS_phase0_component_hd.{csv,md,json}` | CPU minutes | labels/geometry mismatch, missing fold0 cases, stale cache |
| Phase 1: postprocess-only repair | repair modes above; evaluate via `evaluate_predictions.py --hd --hd95`; no training | CPU <1h | HD/HD95 not improved or plausible lesions deleted |
| Phase 2: pretrained cine anatomy smoke | `python scripts/screening/check_cine_pretrained_candidate.py --candidate CineMA --output-dir results/diagnostics/cine_pretrained_screening`; authorized one-case inference only if weights local | metadata minutes; inference <2h | license/provenance unclear or output not mappable to ROI |
| Phase 3: motion/strain smoke | future `python scripts/screening/extract_cine_motion_features.py --case Case1001 --method optical_flow|voxelmorph|strainnet` | <2h one case | folding, wrong geometry, no useful motion contrast |
| Phase 4: trainable first-party model | future `src/care_myocardium/models/cine_motion_pathology.py`; fold0 <=8h Slurm only after Phase 0-3 gates | <=8h/job | no `class_3` Dice+HD gain over pathology_direct/LCC |
| Phase 5: fold/hosted submission | only after fold0 and compliance pass; one zip with both branches through `prepare_care_myocardium_validation.py` | packaging GPU budget | manifest/labels/fallback/package QA fail, or local gains not tied to hosted hypothesis |

## 8. Promotion Gates

- HD/HD95 must improve; Dice-only gains are insufficient.
- Component count and small/remote FP must decrease without deleting plausible scar.
- Any local proxy gain must map to H1-H4 hosted hypothesis.
- Compact and raw label encodings must match submission expectations: Cine compact `3 -> raw 2221` only.
- No method may be promoted based only on local `class_1` when hosted metric appears pathology/scar-sensitive.
- Public pretrained weights are allowed only with documented URL/license/pretrained data; no external supervised training data is allowed.
- Any validation use must be deterministic inference/BN-statistics only; no validation pseudo-label supervised scar training.

## 9. Deliverables for Next Codex Implementation Pass

- Create/extend files:
  - `scripts/evaluation/cinemyops_component_hd_audit.py`
  - `scripts/screening/check_cine_pretrained_candidate.py`
  - `docs/notes/baseline/CineMyoPS_improvement_round9_plan_execution.md`
  - update `results/experiments/CineMyoPS_iteration_log.md`
- Exact metric table: use the Phase 1 diagnostic columns listed above, plus aggregate rows for `mean`, `median`, `worst_hd`, `cases_with_removed_components`, `fallback_cases`.
- Packaging checks before future submission:
  - `manifest.json` records `cine.source`, `pred_dir`, `combine_mode`, `postprocess_mode`, fold/checkpoint, and `pathology_label_fallback.cases`.
  - Zip roots exactly `MyoPS/` and `CineMyoPS/`; 15 cases each; no extra files.
  - Cine raw labels subset `{0,200,500,2221}` and every case has non-empty `2221` unless fallback explicitly recorded.
  - Compare original vs repaired validation tree: raw label counts, `2221` components, largest fraction, bbox distance, volume ratio.
  - Do not upload automatically.
