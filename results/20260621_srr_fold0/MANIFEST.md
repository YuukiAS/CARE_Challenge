# Artifact Manifest 20260621 SRR Fold0

task: `prompts/tasks/20260621_srr_fold0.md`
result: `results/20260621_srr_fold0/result.md`
decision: `results/20260621_srr_fold0/decision.md`

## Required Reports

- `results/20260621_srr_fold0/setup.md`: dependency, variant, budget, output-root, and constraint setup.
- `results/20260621_srr_fold0/metrics_summary.md`: combined fold0 metric summary and decision reasons.
- `results/20260621_srr_fold0/subgroup_metrics.csv`: combined subgroup Dice/HD/HD95 rows; 36 data rows.
- `results/20260621_srr_fold0/component_hd_by_case.csv`: combined case-level component/HD diagnostics; 176 data rows.
- `results/20260621_srr_fold0/retrieval_usage.csv`: combined retrieval usage log; 7973 data rows.
- `results/20260621_srr_fold0/retrieval_usage.md`: per-task SRR expert usage summary.

## Variant Artifacts

### conditional_dualhead_control

- `results/20260621_srr_fold0/variants/conditional_dualhead_control/summary.json`
- `results/20260621_srr_fold0/variants/conditional_dualhead_control/summary.md`
- `results/20260621_srr_fold0/variants/conditional_dualhead_control/training_log.csv`
- `results/20260621_srr_fold0/variants/conditional_dualhead_control/subgroup_metrics.csv`
- `results/20260621_srr_fold0/variants/conditional_dualhead_control/component_hd_by_case.csv`
- `results/20260621_srr_fold0/variants/conditional_dualhead_control/retrieval_usage.csv`
- `results/20260621_srr_fold0/variants/conditional_dualhead_control/checkpoints/fold_0/srr_fold0_config/checkpoint_best.pt`
- `results/20260621_srr_fold0/variants/conditional_dualhead_control/checkpoints/fold_0/srr_fold0_config/checkpoint_final.pt`
- `results/20260621_srr_fold0/variants/conditional_dualhead_control/predictions/fold_0/checkpoint_best/`: 44 validation predictions.

### srr_minimal

- `results/20260621_srr_fold0/variants/srr_minimal/summary.json`
- `results/20260621_srr_fold0/variants/srr_minimal/summary.md`
- `results/20260621_srr_fold0/variants/srr_minimal/training_log.csv`
- `results/20260621_srr_fold0/variants/srr_minimal/subgroup_metrics.csv`
- `results/20260621_srr_fold0/variants/srr_minimal/component_hd_by_case.csv`
- `results/20260621_srr_fold0/variants/srr_minimal/retrieval_usage.csv`
- `results/20260621_srr_fold0/variants/srr_minimal/checkpoints/fold_0/srr_fold0_config/checkpoint_best.pt`
- `results/20260621_srr_fold0/variants/srr_minimal/checkpoints/fold_0/srr_fold0_config/checkpoint_final.pt`
- `results/20260621_srr_fold0/variants/srr_minimal/predictions/fold_0/checkpoint_best/`: 44 validation predictions.

## Slurm Logs

- `logs/SRRCondF0_55720659_20260621_191600.log`: initial short control wiring run.
- `logs/SRRMinF0_55720658_20260621_191600.log`: initial short SRR wiring run.
- `logs/SRRCondF0_55723114_20260621_193914.log`: corrected formal control run.
- `logs/SRRMinF0_55723115_20260621_193914.log`: corrected formal SRR run.

## Code Paths

- `src/care_myocardium/models/srr_myops.py`
- `src/care_myocardium/losses/srr_losses.py`
- `scripts/training/run_srr_myops_fold0.py`
- `scripts/evaluation/report_srr_fold0.py`
- `jobs/src/run_srr_myops_fold0_conditional.sh`
- `jobs/src/run_srr_myops_fold0_srr.sh`
- `jobs/src/run_srr_myops_fold0_conditional_long.sh`: backup long-run wrapper, not submitted.
- `jobs/src/run_srr_myops_fold0_srr_long.sh`: backup long-run wrapper, not submitted.

## Gate

Final fold0 decision: `REVISE_ROUTING`.

No ablation, fold expansion, validation submission, upload-ready package, external data, external weights, network action, or third-party baseline patch was performed.
