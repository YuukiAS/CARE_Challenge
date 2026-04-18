# CineMyoPS (paper baseline)

Wrappers for `third_party/CineMyoPS` nnU-Net v1 training on Task025 data produced by `scripts/CineMyoPS/prepare_task025_from_care.py`.

- `run.sh` — prepare + train locally.
- `sbatch.sh` — Slurm (set `#SBATCH` for your cluster).

Environment knobs: `CINE_NNUNET_DIM`, `CINE_NNUNET_TRAINER`, `CINE_NNUNET_TASK`, `CINE_NNUNET_EPOCHS`, `FOLD`.
