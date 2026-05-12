# nnU-Net v2 (CARE)

Slurm entrypoints for Dataset **501** (MyoPS) and **502** (Cine). They `source env_nnunet.sh` and call `code/nnUNet/run_full_train.sh` with `TRAIN_MYOPS` / `TRAIN_CINE`.

- Edit `#SBATCH` (partition, account, GPU type, memory) for your site.
- Training uses `-tr "${CARE_NNUNET_TRAINER}"` (default **500 epochs**).
- Optional: `MYOPS_CONVERT_INPUT` / `CINE_CONVERT_INPUT` to point converters at a fold-specific tree (see `code/nnUNet/run_full_train.sh`).
