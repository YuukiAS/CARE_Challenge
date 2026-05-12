# `scripts/` — Evaluation and Utilities

This tree holds repository utilities that are not model implementations or Slurm entrypoints. Model-specific training, conversion, and export code lives in [`code/`](../code/README.md). Slurm job wrappers live in [`jobs/`](../jobs/README.md).

Evaluation scripts here are meant to be called from `jobs/*.sh` workflows or run directly for offline metrics.

## Layout

| Subfolder | Contents |
|-----------|----------|
| `benchmark/` | Protocol JSON generation, writing nnU-Net `splits_final` |
| `evaluation/` | Unified metric pipeline (`run_unified_eval_*.sh`, `evaluate_predictions.py`, …) |
| `leaderboard/` | CARE2026 validation leaderboard fetch/export helpers |
| `submission/` | CARE2026 validation inference and upload packaging helpers |

Do **not** treat paths here as the primary user interface; prefer `jobs/README.md` for runnable commands.
