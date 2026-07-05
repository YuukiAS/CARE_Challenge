# Result: 20260704 SRR-v2.5 Local Refinement Ablation

status: `EXECUTED_UNAUDITED`
self_assessed_status: `BOUNDED_CROP_VERIFIED_NEEDS_INPUT_ABLATION`
domain_evidence_label: `PARTIAL_MECHANISM_INCOMPLETE`

## 执行摘要

本轮补强了 local ROI refinement 的可审计输出：formal PropRef runner 现在会在
evaluation 时导出 `crop_bounds_<checkpoint>.csv`，记录 scar/edema crop bounds、
crop volume ratio、full-volume flag、ROI stats、residual magnitude 和 no-T2
blocking source code。随后运行了一个 1-step CPU one-case smoke，生成本任务的
`bounds_stats.csv`、`component_metrics.csv` 和 `ablation.csv`。

该任务没有通过 completion gate。当前只证明了 bounded crop plumbing 和一例
no-T2 edema blocking；required input ablations 和 hard-subgroup evidence 还没跑。

## 读取文件

- `prompts/tasks/20260704_srr_v25_local_refinement_ablation.md`
- `scripts/training/run_srr_propref_myops_fold0.py`
- `src/care_myocardium/models/srr_propref.py`
- `src/care_myocardium/tests/test_srr_anatomy_distance_roi_prior.py`
- `results/20260704_srr_v25_pathology_proposal_decoders/runtime_smoke/variants/srr_propref_shared_dual_dict/*`

## 修改文件

- `scripts/training/run_srr_propref_myops_fold0.py`
- `src/care_myocardium/tests/test_srr_anatomy_distance_roi_prior.py`
- `results/20260704_srr_v25_local_refinement_ablation/result.md`
- `results/20260704_srr_v25_local_refinement_ablation/roi_contract.md`
- `results/20260704_srr_v25_local_refinement_ablation/bounds_stats.csv`
- `results/20260704_srr_v25_local_refinement_ablation/local_loss.md`
- `results/20260704_srr_v25_local_refinement_ablation/ablation.csv`
- `results/20260704_srr_v25_local_refinement_ablation/component_metrics.csv`
- `results/20260704_srr_v25_local_refinement_ablation/hard_subgroup_effect.md`
- `results/20260704_srr_v25_local_refinement_ablation/MANIFEST.md`

## 运行命令

```bash
./envs/env_CARE/bin/python scripts/training/run_srr_propref_myops_fold0.py \
  --variant srr_propref_shared_dual_dict \
  --fold 0 \
  --device cpu \
  --base-channels 4 \
  --encoder-profile tiny_3scale \
  --max-steps 1 \
  --max-runtime-seconds 600 \
  --val-every 1 \
  --overfit-steps 1 \
  --min-overfit-loss-decrease -999 \
  --max-eval-cases 1 \
  --limit-train-cases 8 \
  --limit-val-cases 1 \
  --prototype-bank-cases 8 \
  --out-root results/20260704_srr_v25_local_refinement_ablation/runtime_smoke
```

Result: exit `0`. Summary reports `actual_optimizer_steps=1`,
`eval_cases=1`, `skip_export=False`, `stop_reason=max_steps`.

## 关键证据

- Scar crop bounds for `Case1002`: `z=0:9`, `y=95:150`, `x=99:149`.
- Scar crop volume ratio: `0.041961669921875`.
- Scar full-volume flag: `False`.
- Edema crop volume ratio: `0.0`; `crop_source_code=3.0`, meaning no-T2 blocked.
- Scar ROI GT coverage: `0.5484966052376333`.
- Scar ROI outside-myocardium ratio: `0.7041173893999124`.
- Initial `pathology_aware` scar output exposed a decode/export flooding bug.
  After constraining pathology-aware overrides to proposal-supported or
  already-argmax pathology voxels, `pathology_aware` now matches argmax on this
  smoke case: scar Dice `0.6161527165932452`, HD95 `4.323466070663145`,
  remote FP `0`. This verifies a one-case decode guard, not formal
  local-refinement benefit.

## 测试结果

```bash
./envs/env_CARE/bin/python -m py_compile \
  scripts/training/run_srr_propref_myops_fold0.py \
  src/care_myocardium/tests/test_srr_anatomy_distance_roi_prior.py
```

Result: exit `0`.

```bash
./envs/env_CARE/bin/python -m unittest \
  src.care_myocardium.tests.test_srr_anatomy_distance_roi_prior
```

Result: exit `0`, `Ran 5 tests`, `OK`.

```bash
./envs/env_CARE/bin/python -m unittest \
  src.care_myocardium.tests.test_srr_encoder_context_interface \
  src.care_myocardium.tests.test_srr_anatomy_distance_roi_prior \
  src.care_myocardium.tests.test_srr_runtime_prototype_bank \
  src.care_myocardium.tests.test_srr_proposal_prototypes \
  src.care_myocardium.tests.test_srr_baseline_gate \
  src.care_myocardium.tests.test_srr_v25_anti_laziness_validator \
  src.care_myocardium.tests.test_srr_v25_loss_contract \
  src.care_myocardium.tests.test_myops_decode_guardrails \
  src.care_myocardium.tests.test_srr_dictionary_bank
```

Result: exit `0`, latest targeted run `Ran 36 tests`, `OK`.

```bash
git diff --check -- \
  scripts/training/run_srr_propref_myops_fold0.py \
  src/care_myocardium/tests/test_srr_anatomy_distance_roi_prior.py
```

Result: exit `0`.

## 未完成事项

- Original modality crop, nnU-Net anchor, component input, prototype similarity,
  uncertainty, anatomy distance, ROI mask, and residual scale input ablations
  were not run.
- CenterC scar, CenterC edema, and T2-present GT-positive edema hard subgroups
  were not evaluated.
- No read-only audit has reviewed this result.

## Gate Decision

decision: `BOUNDED_CROP_VERIFIED_NEEDS_INPUT_ABLATION`

No validation package, external upload, git commit, or git push was performed.
