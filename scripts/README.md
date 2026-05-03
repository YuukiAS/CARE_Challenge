# `scripts/` — Implementation

This tree holds **libraries of concrete steps**: Python entrypoints, helper shell that train/export/prepare data, and evaluation glue. They are meant to be called from:

- `code/*.sh` — benchmark workflows you run locally or via `sbatch`
- `code/<model>/run.sh` / `sbatch*.sh` — per-model Slurm/local wrappers

## Layout

| Subfolder | Contents |
|-----------|----------|
| `benchmark/` | Protocol JSON generation, writing nnU-Net `splits_final` |
| `evaluation/` | Unified metric pipeline (`run_unified_eval_*.sh`, `evaluate_predictions.py`, …) |
| `MyoPS-Net/` | Layout prep, training shell, export predictions |
| `CineMyoPS/` | Task025 prep, train/test shell, val export |
| `U-MyoPS/` | Stage1/2 prep and run scripts, exports |
| `nnUNet/` | Dataset conversion, full-train wrapper, smoke tests |

Do **not** treat paths here as the primary user interface; prefer `code/README.md` for runnable commands.
