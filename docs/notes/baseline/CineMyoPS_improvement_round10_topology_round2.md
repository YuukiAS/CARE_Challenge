# CineMyoPS improvement round10: Lane B Round2 topology diagnostics

Date: 2026-05-20

## Scope

- Executed `docs/plans/laneB_round2_topology_execution.md`.
- No training, no Slurm submission, no hosted upload, no validation zip creation, no inference rerun, no external weight download.
- Goal: formalize the round8 LCC repair as an auditable topology module and compare conservative topology guards on existing compact fold0 CineMyoPS predictions.

All Round2 outputs were written under:

```text
results/diagnostics/care_myocardium/laneB_cine/round02_topology_lcc/
```

## Implementation

Added:

- `scripts/diagnostics/laneB_round2_topology_diagnostics.py`

The script reads existing compact predictions from:

```text
results/predictions/CineMyoPS_R6_pathology_direct/fold_0
```

It evaluates variants in memory only:

- `pathology_direct`
- `topology_lcc`
- `component_size_guard`
- `myocardium_overlap_guard`
- `bbox_distance_guard`
- `volume_guard`
- `combined_topology_guard`

It also writes raw-label QA by compact-to-raw conversion in memory only; no zip is created.

## Commands

Syntax check:

```bash
./envs/env_CARE/bin/python -m py_compile scripts/diagnostics/laneB_round2_topology_diagnostics.py
```

Execution:

```bash
./envs/env_CARE/bin/python scripts/diagnostics/laneB_round2_topology_diagnostics.py
```

## Outputs

| output | purpose |
| --- | --- |
| `topology_lcc_before_after.csv` | per-case before/after metrics for baseline vs formalized LCC |
| `topology_lcc_summary.md` | aggregate LCC gate summary |
| `topology_guard_grid.csv` | per-case metrics for all topology guards |
| `topology_guard_grid.md` | aggregate guard grid and promotion decision |
| `topology_component_actions.csv` | per-component keep/remove action reason |
| `topology_thresholds.json` | train/fold0-derived thresholds |
| `raw_label_topology_qc.csv` | raw `{0,200,500,2221}` topology and label validity QA |

Failure registry categories added under `results/diagnostics/care_myocardium/failure_registry/`:

- `cine_remote_pathology_island.md`
- `cine_fragmented_pathology.md`
- `cine_volume_outlier.md`
- `cine_anatomy_guard_risk.md`
- `cine_empty_repair_risk.md`
- `hosted_local_metric_mismatch.md`

## Thresholds

Thresholds were derived from CARE train/fold0 distributions, not handwritten constants:

| threshold | value |
| --- | ---: |
| train scar volume p95 | 4838.6500 |
| train scar volume p99 | 6521.8000 |
| train scar/anatomy ratio p95 | 0.294148 |
| train component volume p10 | 1.0000 |
| fold0 pred component volume p10 | 1.0000 |
| small component volume threshold | 1.0000 |
| train bbox gap p95 | 0.0000 |
| train center distance p95 | 27.3341 |

## Results

| variant | cases | class_3 Dice | class_3 HD95 | scar comps | removed voxels | fallback | gate |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| pathology_direct | 13 | 0.4378 | 26.6533 | 5.5385 | 0.0000 | none | baseline |
| topology_lcc | 13 | 0.4441 | 18.7983 | 1.0000 | 222.1538 | none | pass_vs_baseline |
| component_size_guard | 13 | 0.4378 | 26.6533 | 5.5385 | 0.0000 | none | keep_lcc_default |
| myocardium_overlap_guard | 13 | 0.4378 | 26.6533 | 5.4615 | 0.0769 | none | keep_lcc_default |
| bbox_distance_guard | 13 | 0.4477 | 21.3008 | 2.0000 | 96.4615 | none | keep_lcc_default |
| volume_guard | 13 | 0.4378 | 26.6533 | 5.5385 | 0.0000 | none | keep_lcc_default |
| combined_topology_guard | 13 | 0.4378 | 26.6533 | 5.4615 | 0.0769 | none | keep_lcc_default |

## Interpretation

`topology_lcc` remains the best Round2 default. It reduces component count to one, improves class_3 HD95 from `26.6533` to `18.7983`, and slightly improves class_3 Dice without changing class_1 behavior or introducing fallback.

`bbox_distance_guard` is directionally useful but weaker than LCC on HD95 and component count. Component-size, volume, myocardium-overlap, and combined guards do not beat plain LCC under the current train/fold0-derived thresholds. The correct decision is therefore to keep LCC as the default topology stabilization rule and retain the more complex guards as diagnostic evidence, not promoted production behavior.

Raw-label QA showed legal raw labels and non-empty raw `2221` for evaluated variants. No validation zip was created.

## Stop Reason

Round2 topology diagnostics completed. The near-term topology rule should remain `topology_lcc` unless hosted calibration contradicts the H1 pathology/topology hypothesis. Larger temporal or pretrained cine backbones should remain postponed for this round.
