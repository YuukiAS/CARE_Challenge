# Third-party reference implementations

Cloned read-only baselines for CARE myocardium benchmarks. Prefer **not** editing upstream code here; use patches in-repo or fork externally.

| Directory | Repository | Role |
|-----------|------------|------|
| `MyoPS-Net/` | [QJYBall/MyoPS-Net](https://github.com/QJYBall/MyoPS-Net) | MedIA 2023 — flexible multi-sequence MyoPS |
| `U-MyoPS_myops/` | [NanYoMy/myops](https://github.com/NanYoMy/myops) | TMI 2023 — U-MyoPS (registration + pathology)；**CARE 中文集成说明：** [`U-MyoPS_myops/README-CN.md`](U-MyoPS_myops/README-CN.md) |
| `CineMyoPS/` | [NanYoMy/CineMyoPS](https://github.com/NanYoMy/CineMyoPS) | TMI 2025 — cine-only scar/edema |

**nnU-Net** v2 is installed via `pip` / `env_CARE` (not cloned). Dataset folders live under `data/nnUNet/nnUNet_raw` (etc.); see `env_nnunet.sh`.

Run entrypoints: see [`code/README.md`](../code/README.md) (`MyoPS-Net/run.sh`, `U-MyoPS/run.sh`, `CineMyoPS/run.sh`, matching `sbatch.sh`).
