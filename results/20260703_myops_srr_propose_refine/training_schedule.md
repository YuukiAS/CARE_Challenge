# Training Schedule

Each formal variant is fold0 only and must run under an 8-hour job budget.

| stage | runner condition | trained objective |
| --- | --- | --- |
| evidence_warmup | first 20% of steps | anatomy, scar evidence, T2-masked edema evidence, retrieval regularization |
| proposal_dictionary | 20-60% of steps | evidence plus proposal BCE/Dice and positive-vs-negative prototype margin |
| soft_roi_refinement | 60-90% of steps | final refined logits plus proposal and ROI coverage losses |
| low_lr_calibration | final 10% of steps | same refined objective at 20% base learning rate |

Default Slurm entrypoint:

```bash
sbatch --array=0-2 jobs/src/run_srr_propref_myops_fold0.sh
```

Default job settings: `htzhulab`, `gpu:1`, `--time=07:30:00`, `max_runtime_seconds=25200`, `max_steps=1800`.

## Formal Run Schedule Evidence

The formal evidence runs recorded in `run_config.env` used `max_steps=120`, `patch_shape=8,64,64`, `batch_size=1`, and `base_channels=8` for each variant.

The code path implements `low_lr_calibration`: `stage_for_step()` assigns the final 10% of steps to this stage and the optimizer LR is reduced to 20% of the base LR while that stage is active. For `max_steps=120`, this stage is confined to the last 11 steps. The formal `training_log.csv` files only emit rows at step 1 and every 50 steps, with validation every 300 steps. As a result, the observed training logs contain only `evidence_warmup`, `proposal_dictionary`, and `soft_roi_refinement`.

No formal variant has a logged `low_lr_calibration` row. This package should not claim logged low-LR calibration evidence; the supported claim is that the low-LR path was implemented in code but not captured as a logged row in these formal runs.

| variant | max_steps | logged stages | low-LR calibration evidence |
| --- | ---: | --- | --- |
| `srr_propref_shared_dual_dict` | 120 | `evidence_warmup`, `proposal_dictionary`, `soft_roi_refinement` | implemented in code; no logged row |
| `srr_propref_scar_precision` | 120 | `evidence_warmup`, `proposal_dictionary`, `soft_roi_refinement` | implemented in code; no logged row |
| `srr_propref_no_proto_cascade` | 120 | `evidence_warmup`, `proposal_dictionary`, `soft_roi_refinement` | implemented in code; no logged row |
