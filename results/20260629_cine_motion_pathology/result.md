# Result 20260629 Cine Motion Pathology

## Summary

Ran the safe-subset Cine temporal/pathology preflight on `59` geometry-safe train cases, holding out `5` mismatch cases. The tested motion/context variants did not improve over the frame0 reference control on local class_1 myocardium or class_2 LV proxies, and no scar signal is available from the frozen CineMA anatomy source.

## Key Metrics

| variant | class_1 myocardium Dice | class_2 LV Dice | class_3 scar sanity Dice |
| --- | ---: | ---: | ---: |
| `reference_control_safe` | 0.5626 | 0.7709 | 0.0000 |
| `keyframe_context_retrieval` | 0.5623 | 0.7709 | 0.0000 |
| `anatomy_consistency_temporal` | 0.4662 | 0.6955 | 0.0000 |

## Decision

Selection: `SELECT_REFERENCE_CONTROL_ONLY`.

This does not prove Cine motion is useless; it shows this first-party keyframe/context fallback is dominated by reference control without motion-aligned pathology features.

## Artifacts

- `results/20260629_cine_motion_pathology/selection.md`
- `results/20260629_cine_motion_pathology/metrics_summary.md`
- `results/20260629_cine_motion_pathology/summary_metrics.csv`
- `results/20260629_cine_motion_pathology/case_metrics.csv`
- `results/20260629_cine_motion_pathology/motion_descriptor_summary.csv`
- `results/20260629_cine_motion_pathology/failure_interpretation.md`

## Commands

- `./envs/env_CARE/bin/python -u scripts/evaluation/cinemyops_temporal_preflight.py --output-dir results/20260629_cine_motion_pathology`

No external upload or validation packaging was performed.
