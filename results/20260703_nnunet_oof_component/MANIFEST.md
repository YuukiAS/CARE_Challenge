# Manifest 20260703 nnU-Net OOF Component

- task: `prompts/tasks/20260703_nnunet_oof_component.md`
- result: `results/20260703_nnunet_oof_component/result.md`
- review: `results/20260703_nnunet_oof_component/review.md` (pending separate read-only audit; not written by executor)

| artifact | purpose |
| --- | --- |
| `results/20260703_nnunet_oof_component/result.md` | Executor result and decision fields. |
| `results/20260703_nnunet_oof_component/MANIFEST.md` | Artifact index. |
| `results/20260703_nnunet_oof_component/train_oof_protocol.md` | Leakage-safe train/OOF split and feature protocol. |
| `results/20260703_nnunet_oof_component/component_feature_table.csv` | Component decision features plus evaluation-prefixed GT annotations. |
| `results/20260703_nnunet_oof_component/component_action_table.csv` | Frozen-threshold component actions for train OOF and fold0 eval. |
| `results/20260703_nnunet_oof_component/oof_training_summary.md` | Selected threshold and OOF training summary. |
| `results/20260703_nnunet_oof_component/oof_threshold_grid.csv` | Full train-side OOF threshold sweep. |
| `results/20260703_nnunet_oof_component/metrics_summary.md` | Fold0 metric summary and deltas. |
| `results/20260703_nnunet_oof_component/subgroup_metrics.csv` | Fold0 subgroup metrics. |
| `results/20260703_nnunet_oof_component/component_hd_by_case.csv` | Fold0 case-level Dice/HD/HD95/component/FP metrics. |
| `results/20260703_nnunet_oof_component/label_export_qc.md` | Compact-label and hosted-export caveats. |
| `results/20260703_nnunet_oof_component/failure_interpretation.md` | Decision interpretation and blocked actions. |
| `results/20260703_nnunet_oof_component/command_transcript.md` | Command transcript for this executor run. |

## Prediction Directory

- `results/20260703_nnunet_oof_component/variants/oof_scar_component_score/predictions/fold_0/checkpoint_best/`
