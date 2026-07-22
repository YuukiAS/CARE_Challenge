# Result 20260722_srr_batch7_minimal_pathology_decomposition

status: terminal_executor_evidence
self_assessed_status: COMPLETE_FOR_EXECUTOR_SCOPE

## Scientific Meaning

本轮六组 400-step matched 实验已经完整跑完并聚合。scar 方向没有可用收益：minimal 已低于 anchor，BR2 no-SIP 和 BR2 SIP 都退化为空 scar 预测，因此 scar minimal 退役，BR2/SIP 不适用。edema 方向有小幅正增益，但 minimal 正例 Dice 增量只有 `+0.0013426793`，未达到 `+0.003` 的保留门；BR2 相对 minimal 还有 `+0.0016204931`，但因为 minimal 本身未过门，BR2/SIP 仍不进入保留。

## Runtime Evidence

- Scar formal job: `59992434`, `htzhulab`, `g180702`, `COMPLETED`, exit `0:0`, elapsed `00:18:16`, log `logs/srr_batch7_minimal_decomposition/B7MinDec_scar_59992434_20260722_041831.log`.
- Edema formal job: `59994167`, `htzhulab`, `g180702`, `COMPLETED`, exit `0:0`, elapsed `00:25:18`, log `logs/srr_batch7_minimal_decomposition/B7MinDec_edema_59994167_20260722_045917.log`.
- Aggregation command completed with exit code 0:
  `./envs/env_CARE/bin/python scripts/evaluation/aggregate_srr_batch7_minimal_decomposition.py --scar-attempt-label batch7_minimal_decomposition_scar_htzhulab_rngrestore_20260722_041704 --edema-attempt-label batch7_minimal_decomposition_edema_htzhulab_formal_20260722_045900`.

## Contract Evidence

- `minimal_decomposition_aggregation_status.json`: `PASS`, completed pathologies `scar` and `edema`.
- `matched_run_manifest.csv`: all six rows are `TERMINAL_AGGREGATED_PASS`.
- Source semantics: `center_modality_inventory.csv` records `source_semantics=metadata.center` and `availability_semantics=observation_set_not_training_source`.
- Edema no-T2 exclusion: `pathology_source_eligibility.csv` marks no-T2 centers ineligible for edema beta/SIP/loss; only CenterB and CenterC enter edema SIP calibration.
- SIP formula: `sip_formula_unit_tests.json` is `PASS` and rejects the batch-average gate proxy.
- BR2 initialization and gradients: `representer_scale_checks.csv` and `br2_staged_gradient_checks.json` pass pre-beta RMS, missing-zero, initial zero-delta, and staged gradient-chain checks.
- Slurm accounting: `slurm_attempts.csv` records terminal accounting rows for all attempts, including the final scar and edema winners.

## Decisions

- `scar_minimal`: `RETIRE`
- `scar_br2`: `NOT_APPLICABLE`
- `scar_sip`: `NOT_APPLICABLE`
- `edema_minimal`: `RETIRE`
- `edema_br2`: `NOT_APPLICABLE`
- `edema_sip`: `NOT_APPLICABLE`

## Metric Snapshot

| experiment | gt-positive Dice delta | complete-trimodal Dice delta |
|---|---:|---:|
| scar_minimal | -0.0049928620 | -0.0078458089 |
| scar_br2_no_sip | -0.5731964195 | -0.6933346102 |
| scar_br2_sip | -0.5731964195 | -0.6933346102 |
| edema_minimal | +0.0013426793 | +0.0013426793 |
| edema_br2_no_sip | +0.0029631724 | +0.0029631724 |
| edema_br2_sip | +0.0029631724 | +0.0029631724 |

## Scope Boundary

No Batch8, old M10 dictionary/prototype/memory continuation, refiner training, source arbiter training, production gate training, fold expansion, Cine, validation upload, hosted metric claim, or route promotion was started.
