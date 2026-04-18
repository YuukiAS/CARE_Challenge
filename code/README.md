# `code/` — Slurm and benchmark entrypoints

| Path | Role |
|------|------|
| `run_unified_benchmark.sh` | Protocol, nnU-Net split injection, submit helpers, `print-all` |
| `run_unified_benchmark_test.sh` | Splits + submit **all** models for **one** fold (default 0) |
| `run_unified_benchmark_all.sh` | Splits + submit **all** models for **each** fold (default 0–4) |
| `nnUNet/` | nnU-Net **v2** Slurm scripts (501 / 502 / both) |
| `MyoPS-Net/` | `sbatch.sh` (+ upstream `run.sh` if present) |
| `U-MyoPS/` | `run.sh`, `sbatch.sh` → `scripts/U-MyoPS/` + `third_party/U-MyoPS_myops` |
| `CineMyoPS/` | `run.sh`, `sbatch.sh` → `scripts/CineMyoPS/` + `third_party/CineMyoPS` |
| `PaperBaselines/run_all.sh` | Orchestrate the three paper methods locally |

Edit `#SBATCH` headers (partition, account, GPU) on your cluster. See [SERVER.md](../SERVER.md).
