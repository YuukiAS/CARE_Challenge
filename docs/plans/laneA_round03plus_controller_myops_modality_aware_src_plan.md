# Lane A：CARE MyoPS Modality-Aware First-Party Model Plan

Date: 2026-05-20

Plan metadata:
- Type: lane controller
- Lane: A, MyoPS scar/edema
- Round scope: Round3 and later
- Status: active controller; keep stable unless the Lane A direction changes
- Parent roadmap: `/overflow/htzhu/CARE/TODO.md`
- Parent plan: none
- Function: define the durable MyoPS first-party `src/` route, Dataset501/fold/label/eval constraints, candidate mechanisms, and promotion gates
- Do not: use this file as a per-round execution log; create `laneA_roundNN_status_topic_execution.md` for round-specific work

本计划落实 Lane C 中对 Lane A 的结论：MyoPS 后续主线不再继续 patch `third_party/MyoPS-Net` 或 `third_party/U-MyoPS`，而是在 `src/` 里实现一个 CARE-specific、modality-aware、scar/edema 分离、HD-aware 的 first-party 模型路线。本文只定义实施计划和 gate，不启动训练、不提交 Slurm、不下载权重。

## 1. 执行决策

此 lane **应该推进**，但只能作为新的 first-party `src/` 模型推进。

原因：

- 当前 operational baseline 仍是 nnU-Net。Dataset501 local 5-fold 参考为 edema `0.4197`、scar `0.5592`；官方 validation 中 nnU-Net MyoPS branch 为 `myops_scar 0.5969 / HD 16.2536`、`myops_edema 0.6496 / HD 22.0125`。
- MyoPS-Net round8 complete-case expert 未超过 nnU-Net：all-case edema `0.2779`、scar `0.2426`；round4-scar hybrid edema `0.3293`、scar `0.5048`。
- U-MyoPS round8 最可靠 variant `component_hd_guard` scar `0.5553`，仍低于 nnU-Net fold0 `0.5602` 和 5-fold `0.5592`；`tiny_c0_lge_no_t2_suppression` 的 apparent gain 只来自一个 empty-GT false positive case，属于诊断信号。
- MyoPS-Net 和 U-MyoPS 的有用部分应转化为 first-party idea：modality-specific scar/edema routing、alignment before fusion、anatomy prior as reliability signal、scar-inside-edema/inclusiveness idea、HD/component diagnostics。不要继续继承其 dataloader、export、training loop 作为主线。

## 2. Repository Audit

### 2.1 Dataset501、fold、eval、output 路径

| 项 | 当前 repo 事实 |
| --- | --- |
| Dataset501 raw | `data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS/` |
| Dataset501 preprocessed | `data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/` |
| nnU-Net results | `data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/${CARE_NNUNET_TRAINER}__nnUNetPlans__3d_fullres/fold_k/validation` |
| fold protocol | `data/benchmarks/protocol/splits_MyoPS.json`，5-fold，fold0 先行 |
| unified eval wrapper | `scripts/evaluation/run_unified_eval_model.sh` |
| metric core | `scripts/evaluation/evaluate_predictions.py` |
| metrics output | `results/metrics/unified/<model>/fold_k/` 与 `results/metrics/unified/<model>/aggregate.{json,md}` |
| prediction output | `results/predictions/<model>/fold_k/` |
| benchmark runbook | `README.md`, `jobs/README.md` |
| submission script | `scripts/submission/prepare_care_myocardium_validation.py` |
| submission job | `jobs/submission/prepare_care_myocardium_validation.sh` |
| submission output | `results/submissions/care_myocardium_validation/upload_ready/<model_combo>_<timestamp>/CARE-Myocardium-OrganAgent.zip` |

Fold0 smoke commands for a future implementation pass, not to run in this planning pass:

```bash
bash jobs/run_unified_benchmark_test.sh prep --fold 0
bash scripts/evaluation/run_unified_eval_model.sh nnUNet501 --folds "0" --hd --hd95
```

### 2.2 Label mapping

Dataset501 compact labels:

| compact id | semantic | hosted task use |
| ---: | --- | --- |
| 0 | background | none |
| 1 | myocardium | sanity/anatomy only |
| 2 | LV_blood | sanity/anatomy only |
| 3 | RV_blood | sanity/anatomy only |
| 4 | edema | `myops_edema` |
| 5 | scar | `myops_scar` |

Raw CARE labels used for submission:

| raw id | semantic |
| ---: | --- |
| 200 | myocardium |
| 500 | LV_blood |
| 600 | RV_blood |
| 1220 | edema |
| 2221 | scar |

Files encoding this:

- `data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS/dataset.json`
- `data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/dataset.json`
- `code/nnUNet/nnunet_label_utils.py`
- `scripts/submission/prepare_care_myocardium_validation.py` (`MYOPS_COMPACT_TO_RAW`)
- `scripts/evaluation/evaluate_predictions.py` maps `class_4` to `myops_edema` and `class_5` to `myops_scar` when foreground classes are `4,5`.

## 3. Proposed Model Family

Recommended initial model name: `CAREMyoPSModalityAwareUNetV1`.

Architecture:

- Backbone: nnU-Net/MedNeXt-like 3D encoder-decoder. Phase 1 should start with a PlainConvUNet-like first-party wrapper using nnU-Net spacing/patch conventions. MedNeXt is a Phase 2/3 backbone replacement candidate, not the first dependency.
- Inputs: `LGE`, `T2`, `C0` plus a modality-presence vector/mask `[lge_present, t2_present, c0_present]`. Zero-filled missing modalities must never be interpreted as real images without the mask.
- Fusion: every fusion block receives modality presence metadata; missing channels are masked/gated before feature fusion.
- Scar route: LGE-driven scar head, optionally helped by C0/anatomy context. Scar supervision remains valid for LGE-only and C0+LGE groups.
- Edema route: T2-aware edema head. T2-missing cases must not be treated as reliable edema negatives; use them only for scar/anatomy or very low-weight consistency.
- Heads: separate scar and edema logits/routes, merged into compact output label `4/5` at export. This avoids hiding scar/edema tradeoffs behind foreground mean.
- Anatomy soft prior: myocardium probability or ROI used as input channel, attention bias, or loss regularizer. It must not be a hard deletion rule in the model path.
- Optional alignment: CAA-Seg/SSA or U-MyoPS-style light alignment before fusion, staged after Phase 1. It should first be audited on complete C0+LGE+T2 fold0 cases before training with it.
- Loss: start with CE/Dice-compatible baseline plus scar/edema class balancing; then add Focal/Tversky and boundary/HD surrogate only after the baseline is reproducible.

## 4. Candidate Repo / Pretrained Asset Screening Matrix

| candidate | URL / local source | intended role | expected CARE benefit | difficulty | license | pretrained weights | pretrained data | compliance risk | requires external training data? | minimal smoke-test | fail-fast criterion |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CAA-Seg / SSA | `docs/notes/deep_research/Result2.pdf`; https://papers.miccai.org/miccai-2025/0009-Paper2655.html; local note mentions GitHub | alignment/fusion | reduce C0/LGE/T2 slice mismatch and pathology localization error | medium | unclear | unclear | likely CMR/in-house, unclear | low if reimplemented from idea | no | complete-case fold0 alignment audit only | no complete-case Dice/HD gain or alignment not reproducible |
| YoloSAM | `Result2.pdf`; https://papers.miccai.org/miccai-2025/0788-Paper2947.html | ROI / detect-then-seg | reduce tiny scar false positives and noisy label sensitivity | medium | unclear | likely YOLO/SAM assets | SAM/YOLO sources, unclear | medium | no if frozen/proposal only | frozen ROI proposal on nnU-Net scar maps | scar-positive Dice drops or small scars missed |
| I-MMSeg | `docs/notes/deep_research/Result1.pdf` | intensity-prior multimodal model | potentially strong scar/edema multimodal prior | high | unclear | unclear | MyoPS380 / CLIP-like components mentioned | high | likely unclear/yes | metadata/interface review only | requires external supervised data, generated assets, or incompatible training |
| AdaMM | `Result2.pdf`; https://github.com/Quanato607/AdaMM | missing-modality distillation | complete-modality teacher to missing-modality student using CARE-only data | high | unclear | unclear | original brain/BraTS-style setting | low if concept-only CARE KD | no if CARE-only | sketch CARE-only teacher/student API, no training | requires external teacher/data or worsens T2-present edema |
| UniME | `docs/notes/deep_research/Result2.pdf` | missing-modality robust backbone | robustness for LGE-only cases | high | unclear | unclear | BraTS/cardiac mixed, unclear | medium/high | unclear | metadata/license/provenance screen | pretrained source/license cannot be verified |
| BiomedParse | `Result2.pdf`; https://github.com/microsoft/BiomedParse | foundation anatomy/ROI QA | frozen anatomy prior or promptable QA | medium | code likely Apache-2.0; weight license must be verified | yes | broad biomedical image/text data | high | no for frozen inference, but weights risky | license check + 2-3 CARE cases frozen inference | license forbids challenge use or output cannot map to CARE labels |
| InverseForm | `Result2.pdf`; https://github.com/Qualcomm-AI-research/InverseForm | boundary / HD-aware loss | reduce HD/HD95 without postprocess-only pruning | low/medium | verify repo license | no needed | none | low | no | loss-only one-batch gradient check | unstable gradients or Dice gain with HD regression |
| Unified Focal / Tversky loss | `Result2.pdf`; https://github.com/mlyg/unified-focal-loss | imbalance loss | improve scar/edema recall under small lesion imbalance | low | verify repo license | no | none | low | no | first-party loss unit test + tiny overfit | no fold0 gain or remote FP increases |
| CATMIL / lesion-level loss | `Result1.pdf` | lesion/component-level loss | small scar/edema lesion recall | medium | unclear | code/pretrained noted | brain MRI small lesions | medium | no if code-only | component term on CARE labels only | component count or HD worsens |
| nnU-Net Task114 / M&Ms weights | `Result2.pdf`; https://zenodo.org/records/4288362 | pretrained anatomy initialization | myocardium/LV/RV warm start | low | Zenodo license must verify | yes | M&Ms cardiac MRI | low/medium | no | metadata-only first; no large download without approval | license unclear, label mismatch, or large download not approved |
| MedNeXt or equivalent | `src/README.md`; https://github.com/MIC-DKFZ/MedNeXt | backbone | stronger 3D segmentation head than old paper baselines | medium | verify repo license | maybe | none if trained CARE-only | low | no | import/config smoke only | cannot wrap into unified export/eval |

Default screening rule: Phase 1 uses CARE data only and no large download. Public pretrained weights are only allowed after license, weight provenance, pretrained data source, and challenge compliance are recorded.

## 5. Experiment Plan, No Execution

### Phase 0：reproducibility and metric audit

Purpose:

- Freeze the nnU-Net Dataset501 local reference used by all later gates.
- Audit label semantics, fold case lists, cache isolation, component/HD diagnostics, modality group and center grouping.

Future commands:

```bash
bash scripts/evaluation/run_unified_eval_model.sh nnUNet501 --folds "0" --hd --hd95
python scripts/evaluation/report_laneA_phase0_audit.py \
  --pred-dir results/predictions/nnUNet501/fold_0 \
  --gt-dir data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS/labelsTr \
  --fold-json data/benchmarks/protocol/splits_MyoPS.json \
  --fold 0 \
  --output-dir results/diagnostics/laneA_phase0_myops_audit
```

Estimated runtime: CPU minutes to <1h.

Expected outputs:

- `results/diagnostics/laneA_phase0_myops_audit/baseline_metrics_by_case.csv`
- `results/diagnostics/laneA_phase0_myops_audit/modality_center_metrics.csv`
- `results/diagnostics/laneA_phase0_myops_audit/component_hd_by_case.csv`
- `results/diagnostics/laneA_phase0_myops_audit/phase0_summary.md`

Stop criteria:

- nnU-Net fold0 metrics cannot be reproduced.
- `class_4`/`class_5` label semantics or compact/raw mapping are inconsistent.
- Prediction caches are stale or output directories do not encode model/config/fold.

### Phase 1：fold0 first-party nnU-Net-compatible baseline with modality mask

Purpose:

- Implement `CAREMyoPSModalityAwareUNetV1` with explicit modality mask but without adding complex external modules.
- Match nnU-Net-like data preprocessing/export/eval behavior in first-party `src/`.

Future command:

```bash
sbatch jobs/src/laneA_myops_masked_unet_fold0_smoke.sh
```

The job wrapper must run with <=8h walltime and write a timestamped `logs/LaneA_MyoPSMaskedUNet_<jobid>_<timestamp>.log`.

Expected outputs:

- `results/checkpoints/laneA_masked_unet_v1/fold_0/`
- `results/predictions/laneA_masked_unet_v1/fold_0/`
- `results/metrics/unified/laneA_masked_unet_v1/fold_0/`
- `results/diagnostics/laneA_masked_unet_v1/fold_0/modality_center_metrics.csv`
- `results/diagnostics/laneA_masked_unet_v1/fold_0/component_hd_by_case.csv`

Stop criteria:

- Predictions are empty or invalid compact labels.
- Scar or edema is below nnU-Net fold0 without an explainable pipeline bug.
- HD/HD95 or remote component count regresses.
- Edema gain comes from treating no-T2 cases as clean negatives.

### Phase 2：scar/edema dual-head and T2-aware edema route

Purpose:

- Add separate scar and edema routes.
- Make edema loss/gate explicitly T2-present aware.
- Keep scar primarily LGE-driven.

Future command:

```bash
sbatch jobs/src/laneA_myops_dualhead_t2gate_fold0_smoke.sh
```

Estimated runtime: <=8h fold0.

Expected outputs:

- `results/predictions/laneA_dualhead_t2gate_v1/fold_0/`
- `results/metrics/unified/laneA_dualhead_t2gate_v1/fold_0/`
- `results/diagnostics/laneA_dualhead_t2gate_v1/fold_0/subgroup_metrics.csv`
- `results/diagnostics/laneA_dualhead_t2gate_v1/fold_0/gate_summary.md`

Stop criteria:

- Scar improves while edema regresses, or edema improves while scar regresses.
- Complete/T2-present subgroup improves but all-case LGE-only scar collapses.
- GT-positive-only edema does not improve.

### Phase 3：add one module only

Choose exactly one of:

1. anatomy soft-prior loss/input,
2. boundary/HD surrogate loss such as InverseForm-style or differentiable HD,
3. light SSA/alignment preprocessing for complete cases.

Recommended first Phase 3 candidate: anatomy soft prior or boundary/HD loss before heavy alignment.

Future command example:

```bash
sbatch jobs/src/laneA_myops_dualhead_t2gate_hd_loss_fold0_smoke.sh
```

Estimated runtime: <=8h fold0.

Expected outputs:

- same unified prediction/metric layout as Phase 2;
- plus `component_delta_vs_phase2.csv` and `hd95_delta_vs_phase2.md`.

Stop criteria:

- Dice gain is accompanied by HD/HD95 regression.
- Component count improves only by deleting scar-positive small lesions.
- Anatomy prior hard-deletes true lesion voxels.

### Phase 4：5-fold expansion

Only expand after fold0 passes all gates.

Future command:

```bash
sbatch jobs/src/laneA_myops_selected_5fold.sh
```

Estimated runtime: <=8h/job by default.

Expected outputs:

- `results/metrics/unified/<selected_laneA_config>/aggregate.json`
- `results/metrics/unified/<selected_laneA_config>/aggregate.md`
- `results/diagnostics/<selected_laneA_config>/5fold_modality_center_metrics.csv`
- `results/diagnostics/<selected_laneA_config>/5fold_gate_summary.md`

Stop criteria:

- Mean scar and edema do not both beat nnU-Net local reference.
- Any modality group or center shows a hidden collapse that explains the aggregate gain.
- HD/HD95 regresses across folds.

## 6. Gates

Every candidate must satisfy:

- Beat nnU-Net local reference on both `myops_scar` and `myops_edema`; never accept a one-metric win.
- HD and HD95 must not regress against the corresponding nnU-Net reference.
- Report by modality group: `C0+LGE+T2`, `C0+LGE`, `LGE-only`.
- When possible, report by center: CenterA/B/C/E/F/G/H.
- Report component count, small components, remote components, pred/GT volume ratio, and bbox distance.
- Report all-case, GT-positive-only, T2-present, and complete-modality subsets for edema.
- Report all-case, scar-positive-only, complete/T2-present, and missing-modality subsets for scar.
- Flag any gain caused by empty-GT case handling as diagnostic, not primary.
- Ensure artifact naming includes model, phase, config, fold, checkpoint, and postprocess status.

## 7. Deliverables for Future Implementation

Create first-party code under:

```text
src/care_myocardium/
  data/myops_dataset.py
  data/case_metadata.py
  models/modality_aware_unet.py
  models/heads.py
  losses/pathology_losses.py
  losses/boundary_losses.py
  postprocess/component_diagnostics.py
  reporting/myops_phase0_report.py
  configs/laneA_masked_unet_v1.yaml
  configs/laneA_dualhead_t2gate_v1.yaml
```

Add script/job entrypoints:

```text
scripts/evaluation/report_laneA_phase0_audit.py
scripts/evaluation/report_myops_component_hd_audit.py
scripts/training/run_laneA_myops.py
jobs/src/laneA_myops_masked_unet_fold0_smoke.sh
jobs/src/laneA_myops_dualhead_t2gate_fold0_smoke.sh
jobs/src/laneA_myops_selected_5fold.sh
```

Required output tables:

```text
results/diagnostics/laneA_phase0_myops_audit/baseline_metrics_by_case.csv
results/diagnostics/laneA_phase0_myops_audit/modality_center_metrics.csv
results/diagnostics/laneA_phase0_myops_audit/component_hd_by_case.csv
results/diagnostics/<experiment_id>/subgroup_metrics.csv
results/diagnostics/<experiment_id>/component_hd_by_case.csv
results/diagnostics/<experiment_id>/gate_summary.md
```

Each experiment manifest must include:

| field | required value |
| --- | --- |
| `experiment_id` | unique artifact prefix |
| `folds` | evaluated folds |
| `config` | exact config name |
| `checkpoint` | checkpoint selected/exported |
| `modality_mask_policy` | how missing C0/T2 are represented |
| `edema_loss_policy` | T2-present / GT-positive handling |
| `scar_loss_policy` | LGE-driven route definition |
| `anatomy_prior_policy` | soft input/loss/attention only |
| `normalization` | preprocessing config |
| `postprocess` | deterministic postprocess config or `none` |
| `pred_dir` | prediction artifact path |
| `metrics_dir` | unified metric path |
| `diagnostics_dir` | component/subgroup diagnostics path |
| `compliance_status` | low/medium/high/reject |
| `pass_fail` | gate result |
| `stop_reason` | required if failed |

Validation packaging requirements:

- Predictions must be Dataset501 compact labels `0..5` before packaging.
- Use `scripts/submission/prepare_care_myocardium_validation.py` as the single validation entrypoint.
- One upload zip only: `CARE-Myocardium-OrganAgent.zip` containing both `MyoPS/` and `CineMyoPS/`.
- Use explicit MyoPS prediction dir and selected Cine branch; do not plan separate uploads for scar/edema/cine.
- Manifest must prove MyoPS model/config/folds/checkpoint and Cine model/config/folds/checkpoint.

Future packaging command shape:

```bash
./envs/env_CARE/bin/python scripts/submission/prepare_care_myocardium_validation.py \
  --team-name OrganAgent \
  --myops-model nnUNet \
  --cine-model CineMyoPS \
  --myops-pred-dir results/predictions/<selected_laneA_config>/validation_or_ensemble \
  --cine-combine-mode pathology_direct \
  --folds 0 1 2 3 4 \
  --checkpoint checkpoint_best.pth
```

The `--myops-model nnUNet` placeholder above is only acceptable if the implementation pass has not yet added a first-party model selector to the packaging script; otherwise add a first-party `LaneA` selector or use `--myops-pred-dir` with manifest metadata that identifies the Lane A model.

## 8. Risks

| risk | mitigation |
| --- | --- |
| overfitting complete cases | fold0 gate must report all modality groups; do not train only complete cases as final model |
| learning center shortcut | report by center; use modality/center-aware sampling and normalization audit |
| edema treated as negative on no-T2 cases | T2-missing edema loss masked or very low confidence; report T2-present and GT-positive subsets |
| hard anatomy prior deleting true lesions | anatomy prior only soft input/loss/attention; no hard deletion as model logic |
| HD improving via over-pruning | always report scar-positive/edema-positive Dice, component count, volume ratio, bbox distance |
| pretrained compliance risk | metadata-first screening; no external training data; no large weight download without explicit approval |
| local/hosted metric mismatch | local gate must use `myops_scar`/`myops_edema` class 5/4 and package only after one-zip manifest QA |

## 9. Immediate Implementation Order for Next Codex Pass

1. Implement Phase 0 audit script only.
2. Generate no training jobs until Phase 0 proves baseline paths, label mapping, subgroup metadata, and HD/component diagnostics are reproducible.
3. Implement Phase 1 first-party dataset/model skeleton under `src/care_myocardium/`.
4. Add the fold0 smoke Slurm wrapper with `htzhulab` default header and <=8h walltime.
5. Run fold0 only, then expand only if both scar and edema beat nnU-Net without HD/subgroup regression.
