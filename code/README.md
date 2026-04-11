# CARE `code/` entrypoints

| Path | Purpose |
|------|---------|
| **nnUNet/** | nnU-Net **v2** (CARE challenge baselines): Dataset 501 / 502 |
| **MyoPS-Net/** | [MyoPS-Net](https://github.com/QJYBall/MyoPS-Net) paper code |
| **U-MyoPS/** | [U-MyoPS / myops](https://github.com/NanYoMy/myops) |
| **CineMyoPS/** | [CineMyoPS](https://github.com/NanYoMy/CineMyoPS) paper repo (legacy nnU-Net v1), **not** the same as `nnUNet/run_CineMyoPS.sh` (v2 dataset 502) |
| **PaperBaselines/** | `run_all.sh` — optional orchestration of MyoPS-Net + U-MyoPS + CineMyoPS |
| **lib/slurm_nnUNet.sh** | Shared logging / env / nnU-Net v2 convert+train helpers for Slurm jobs |

**Slurm:** use `sbatch` on the `run_*.sh` scripts under `nnUNet/`, or `*/sbatch.sh` for paper methods.
