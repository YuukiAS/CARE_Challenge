# Phase0/Phase1 execution results

Date: 2026-05-20

## Scope

本轮按 `docs/plans/next_phase0_phase1_execution_plan.md` 执行诊断治理任务：不训练新模型，不提交 Slurm，不创建 validation zip，不下载外部权重。所有生成表格都写入：

- `results/diagnostics/phase0_phase1/`

注意：`results/diagnostics/` 当前被 `.gitignore` 忽略，因此本文件作为可跟踪摘要保留关键结论和产物路径。

## Outputs

| lane | output |
| --- | --- |
| Lane A MyoPS | `results/diagnostics/phase0_phase1/laneA_myops/myops_baseline_protocol_audit.csv` |
| Lane A MyoPS | `results/diagnostics/phase0_phase1/laneA_myops/myops_baseline_protocol_audit.md` |
| Lane A MyoPS | `results/diagnostics/phase0_phase1/laneA_myops/myops_modality_center_metrics.csv` |
| Lane A MyoPS | `results/diagnostics/phase0_phase1/laneA_myops/myops_modality_center_metrics.md` |
| Lane B CineMyoPS | `results/diagnostics/phase0_phase1/laneB_cine/cinemyops_postprocess_before_after.csv` |
| Lane B CineMyoPS | `results/diagnostics/phase0_phase1/laneB_cine/cinemyops_postprocess_before_after.md` |
| Lane C normalization/DA | `results/diagnostics/phase0_phase1/laneC_da/normalization_intensity_by_center_modality.csv` |
| Lane C normalization/DA | `results/diagnostics/phase0_phase1/laneC_da/normalization_error_correlation.csv` |
| Lane C normalization/DA | `results/diagnostics/phase0_phase1/laneC_da/normalization_audit.md` |
| Failure registry | `results/diagnostics/phase0_phase1/failure_registry/` |
| Cross-lane | `results/diagnostics/phase0_phase1/next_round_decision_table.md` |

The reproducible builder is:

```bash
./envs/env_CARE/bin/python scripts/diagnostics/build_phase0_phase1_diagnostics.py
```

Syntax check:

```bash
./envs/env_CARE/bin/python -m py_compile scripts/diagnostics/build_phase0_phase1_diagnostics.py
```

## Key Findings

### Lane A: MyoPS protocol anchor

- `nnUNet501` fold0 has 44/44 validation predictions, `checkpoint_best.pth`, and unified Dice/HD/HD95 metrics.
- fold1-4 also have 44/44 validation predictions and `checkpoint_best.pth`, but this smoke pass did not recompute HD/HD95 for folds 1-4.
- fold0 local reference:
  - `myops_scar`: Dice `0.5602`, HD95 `13.6005`.
  - `myops_edema`: Dice `0.3944`, HD95 `7.2769`.
- Label semantics are fixed as compact MyoPS labels: `4=edema/myops_edema`, `5=scar/myops_scar`; raw submission labels map edema/scar to `1220/2221`.

### Lane A: modality/center stratification

The stratified table shows actionable center/modality signals rather than a single aggregate:

- `CenterC` complete cases have scar Dice `0.7557` but edema Dice `0.3100` and edema HD95 `23.1833`, suggesting edema localization remains the weak target even with T2.
- `CenterA` LGE-only cases have scar Dice `0.5202`, scar HD95 `16.1565`, and many small FP components.
- `CenterG` has one C0+LGE case with no scar GT but scar prediction FP, producing a large volume-ratio artifact.

### Lane B: Cine postprocess

Existing round8 before/after diagnostics support keeping LCC as a watch/go candidate:

| variant | cases | class_3 Dice | class_3 HD95 | scar components |
| --- | ---: | ---: | ---: | ---: |
| pathology_direct | 13 | 0.4378 | 26.6533 | 5.5385 |
| lcc | 13 | 0.4441 | 18.7983 | 1.0000 |

This is not a submission decision. It only confirms that topology repair improves local class_3 HD/HD95 without class_3 Dice loss on the smoke set.

### Lane C: normalization/DA audit

- MyoPS smoke statistics used 15 fold0 cases sampled across modality_group/center buckets, so the table covers LGE-only, C0+LGE, and C0+LGE+T2 groups without expanding into a full validation-wide pass.
- Cine smoke statistics used 10 training cases and recommends only BN-stat/intensity diagnostics.
- No external harmonization, diffusion, foundation checkpoint, validation pseudo-label, or architecture rewrite is justified by this phase.

## Failure Registry

Created compact Markdown registries for:

- `remote_false_positive`
- `small_false_positive`
- `hd95_outlier`
- `edema_no_t2_gap`

The strongest immediate examples are LGE-only `Case1029` and `Case1045`, both with scar HD95 outliers and remote/small false-positive components.

## Decision Table

| candidate | decision | reason |
| --- | --- | --- |
| `nnUNet501` protocol anchor | go | fold0 protocol/cache/label/evaluator gate passes. |
| MyoPS modality/center normalization smoke | watch | stratified error exists, but needs candidate-specific smoke before implementation. |
| Cine pathology LCC | go | class_3 HD95 and component count improve without Dice loss on the smoke set. |
| CARE-only robust-z / BN-stat smoke | watch | diagnostic direction only; no training evidence yet. |
| unstructured baseline patching | stop | future work must pass target-specific metric and cache/label gates. |

## Stop Rules Preserved

- Do not train or expand folds until candidate-specific fold0 smoke outputs are isolated under `results/diagnostics/phase0_phase1/`.
- Do not report aggregate-only success; keep `myops_scar`, `myops_edema`, and `myocardium_cinemyops` separated.
- Do not alter label semantics, spacing handling, connected-component rules, or evaluator implementation without explicitly recording the change.
- Do not create validation zip or use validation pseudo-labels in this phase.
