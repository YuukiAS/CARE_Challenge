# CineMyoPS (paper baseline)

Wrappers for `third_party/CineMyoPS` nnU-Net v1 training on Task025 data produced by `code/CineMyoPS/prepare_task025_from_care.py`.

- `run.sh` — prepare + train locally.
- `sbatch.sh` — Slurm (set `#SBATCH` for your cluster).

Environment knobs: `CINE_NNUNET_DIM`, `CINE_NNUNET_TRAINER`, `CINE_NNUNET_TASK`, `CINE_NNUNET_EPOCHS`, `FOLD`.

## CineMyoPS (paper replication)

`Task025_Cine_Seg` keeps the old single-frame nnU-Net v1 baseline for comparison.
`Task026_Cine_4D` is the CARE paper-replication path: ED is fixed to `t=0`, the exporter keeps sampled cine frames, raw nnU-Net input is split into per-frame channels, and `CARECineMyoPSTrainer` drives `CineSegNet` with scar-only supervision.

Key environment variables:
- `CINE_NNUNET_TASK`: default `Task026_Cine_4D`
- `CINE_NNUNET_TRAINER`: default `CARECineMyoPSTrainer`
- `CINE_NNUNET_DIM`: default `2d`
- `CINE_NUM_FRAMES`: sampled frames per cycle, default `4`
- `CINE_NNUNET_EPOCHS`: trainer epoch cap, default `500`
- `FOLD`: protocol fold index, `0..4`
- `CINE_SKIP_SANITY`: set `1` to skip `sanity_check_task026.py`

Recommended five-fold launch:

```bash
for f in 0 1 2 3 4; do FOLD=$f sbatch jobs/CineMyoPS/sbatch_cinemyops.sh; done
```

Single-fold launch:

```bash
sbatch jobs/CineMyoPS/sbatch_cinemyops.sh
FOLD=2 sbatch jobs/CineMyoPS/sbatch_cinemyops.sh
```

Validation export still lands in `results/predictions/CineMyoPS/fold_X/<case>.nii.gz`, so the existing evaluator stays unchanged:

```bash
bash scripts/evaluation/run_unified_eval_model.sh CineMyoPS
```

Expected validation behavior:
- `validation_raw/` and protocol exports are written in the compact CARE label space `{0:bg,1:myocardium,2:LV_blood,3:scar}`
- unified evaluation should be read from scar `class_3` rather than `foreground_mean`
- smoke-test-scale runs only validate pipeline health, not final Dice quality
