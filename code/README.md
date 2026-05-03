# `code/` — Benchmark Entrypoints

**Convention:** `code/` holds shells you **run or `sbatch` directly** (workflows, cluster headers). **`scripts/`** holds **implementation** (Python and helper shell) invoked by those entrypoints. See [`scripts/README.md`](../scripts/README.md).

This folder contains the benchmark runbook for:

- `nnUNet501` vs `MyoPS-Net` vs `U-MyoPS`
- `nnUNet502` vs `CineMyoPS`

Do **not** compare Dataset501 and Dataset502 against each other.

## Files

| Path | Role |
|------|------|
| `benchmark_protocol_helpers.sh` | **Helper:** generate CARE protocol JSON, inject nnU-Net v2 / v1 splits, print current split status |
| `run_unified_benchmark_test.sh` | Single-fold workflow entrypoint (default `fold 0`) |
| `run_unified_benchmark_all.sh` | Multi-fold workflow entrypoint (default `0 1 2 3 4`) |
| `collect_benchmark_weights.sh` | Collect trained weights into canonical `models/<model>/fold_k/` layout |
| `evaluation/sbatch_unified_eval.sh` | Slurm GPU job for unified offline eval (calls `scripts/evaluation/run_unified_eval_all.sh`) |
| `nnUNet/` | nnU-Net **v2** Slurm scripts (Dataset501 / Dataset502) |
| `MyoPS-Net/` | Slurm wrapper for fold-isolated MyoPS-Net training |
| `U-MyoPS/` | Stage1 / Stage2 wrappers for vendored U-MyoPS |
| `CineMyoPS/` | Slurm wrapper for CineMyoPS Task025 training |

Edit `#SBATCH` headers (partition, account, GPU) on your cluster. See [SERVER.md](../SERVER.md).

## What `benchmark_protocol_helpers.sh` Does

`benchmark_protocol_helpers.sh` is a low-level **protocol/split helper**. It is not the main workflow entrypoint.

It handles:

- generating CARE protocol case lists and 5-fold split JSON
- writing `splits_final.json` into `Dataset501_CAREMyoPS`
- writing `splits_final.json` into `Dataset502_CARECineMyoPS`
- writing `splits_final.pkl` into `Task025_Cine_Seg`
- printing current split/protocol state

Typical direct usage:

```bash
bash code/benchmark_protocol_helpers.sh print-all
```

## Main Entry Scripts

### `run_unified_benchmark_test.sh`

Single-fold workflow. Default action is `full`, which means:

1. `prep`
2. `submit`

Supported actions:

- `prep`
- `submit`
- `collect`
- `eval`
- `post` = `collect + eval`
- `full` = `prep + submit`
- `print`

Examples:

```bash
# Default single-fold smoke test: prep + submit fold 0
bash code/run_unified_benchmark_test.sh

# Same, explicit
bash code/run_unified_benchmark_test.sh full --fold 0

# Only prepare protocol / splits / Task025
bash code/run_unified_benchmark_test.sh prep --fold 0

# Only submit one fold
bash code/run_unified_benchmark_test.sh submit --fold 3

# After training finishes: collect weights + run unified eval on one fold
bash code/run_unified_benchmark_test.sh post --fold 3

# Only collect trained weights for one fold
bash code/run_unified_benchmark_test.sh collect --fold 3

# Only run unified eval for one fold
bash code/run_unified_benchmark_test.sh eval --fold 3
```

Model selection is controlled in one place near the top of the script:

```bash
BENCHMARK_MODEL_PLAN=(
  "nnUNet=run"
  "MyoPS-Net=run"
  "U-MyoPS=run"
  "CineMyoPS=run"
)
```

Modes:

- `run`: submit training, then later collect/eval
- `eval`: do not submit; only collect/eval existing results
- `skip`: ignore completely

Example when `nnUNet` is already finished and the remaining models still need training:

```bash
BENCHMARK_MODEL_PLAN=(
  "nnUNet=eval"
  "MyoPS-Net=run"
  "U-MyoPS=run"
  "CineMyoPS=run"
)
```

You can also comment out entries entirely if you do not want the script to touch them.

### `run_unified_benchmark_all.sh`

All-fold workflow. Default folds are `0 1 2 3 4`. Default action is `full`, which means:

1. `prep`
2. `submit`

Supported actions:

- `prep`
- `submit`
- `collect`
- `eval`
- `post` = `collect + eval`
- `full` = `prep + submit`
- `print`

Examples:

```bash
# Default full benchmark: prep + submit folds 0..4
bash code/run_unified_benchmark_all.sh

# Explicit full 5-fold run
bash code/run_unified_benchmark_all.sh full --folds "0 1 2 3 4"

# Only submit selected folds
bash code/run_unified_benchmark_all.sh submit --folds "0 1 2 3 4"

# After training finishes: collect weights + run unified eval on all folds
bash code/run_unified_benchmark_all.sh post

# Only collect all trained weights
bash code/run_unified_benchmark_all.sh collect

# Only run unified evaluation on all folds
bash code/run_unified_benchmark_all.sh eval
```

Model selection is controlled by the same `BENCHMARK_MODEL_PLAN` block near the top of the script. A practical configuration after `nnUNet` is complete:

```bash
BENCHMARK_MODEL_PLAN=(
  "nnUNet=eval"
  "MyoPS-Net=run"
  "U-MyoPS=run"
  "CineMyoPS=run"
)
```

Then:

- `full` / `submit` only launches the `run` models
- `collect` / `eval` / `post` process both `run` and `eval` models
- `skip` models are ignored throughout

## Recommended Workflows

### Single-fold smoke test

```bash
bash code/run_unified_benchmark_test.sh full --fold 0
# wait until jobs finish
bash code/run_unified_benchmark_test.sh post --fold 0
```

### Full 5-fold benchmark

```bash
bash code/run_unified_benchmark_all.sh full
# wait until jobs finish
bash code/run_unified_benchmark_all.sh post
```

## Weight Collection

Canonical output layout after collection:

```text
models/
  nnUNet501/fold_0/
  nnUNet501/fold_1/
  ...
  nnUNet502/fold_0/
  ...
  MyoPS-Net/fold_0/
  ...
  CineMyoPS/fold_0/
  ...
  U-MyoPS/fold_0/stage1/
  U-MyoPS/fold_0/stage2/
```

One-line commands:

```bash
# Collect all models for all folds
bash code/collect_benchmark_weights.sh --folds "0 1 2 3 4"

# Collect only nnUNet501 + nnUNet502
bash code/collect_benchmark_weights.sh --folds "0 1 2 3 4" --only nnUNet

# Copy files instead of symlinks
COLLECT_MODE=copy bash code/collect_benchmark_weights.sh --folds "0 1 2 3 4"
```

If `nnUNet501` / `nnUNet502` were already trained, this is the one-line collection command:

```bash
bash code/collect_benchmark_weights.sh --folds "0 1 2 3 4" --only nnUNet
```

## Unified Offline Evaluation

Per-model commands:

```bash
bash scripts/evaluation/run_unified_eval_model.sh nnUNet501
bash scripts/evaluation/run_unified_eval_model.sh MyoPS-Net
bash scripts/evaluation/run_unified_eval_model.sh nnUNet502
bash scripts/evaluation/run_unified_eval_model.sh CineMyoPS
```

All supported models:

```bash
bash scripts/evaluation/run_unified_eval_all.sh
```

Main output paths:

```text
results/predictions/<model>/fold_k/
results/metrics/unified/<model>/fold_k/
results/metrics/unified/<model>/aggregate.json
results/metrics/unified/<model>/aggregate.md
```

## Important Notes

- `nnUNet501` and `nnUNet502` are already compatible with the unified evaluation flow.
- `MyoPS-Net` training is now fold-isolated:
  - data staging: `data/benchmarks/MyoPS-Net/fold_k/`
  - outputs/checkpoints: `results/checkpoints/MyoPS-Net/fold_k/`
- `CineMyoPS` unified evaluation can export predictions on protocol val cases even if historical `validation_raw` was produced with a different split.
- `U-MyoPS` unified benchmark submit mode is controlled by **`UMYOPS_BENCHMARK_STAGES`** (set near **`BENCHMARK_MODEL_PLAN`** in `run_unified_benchmark_all.sh` / `run_unified_benchmark_test.sh`, or export before running): **`stage1`** (default), **`stage2`** only, or **`both`** / **`all`** (Stage 1 then Stage 2 with Slurm `afterok`). Only applies when **`U-MyoPS=run`** in the plan. Local `code/U-MyoPS/run.sh` still uses **`UMYOPS_RUN_STAGE2`** from `env_nnunet.sh`.

```bash
# Example: submit Stage 1 + Stage 2 chained (after nnU-Net v1 Task + preprocessing exist)
UMYOPS_BENCHMARK_STAGES=both bash code/run_unified_benchmark_all.sh submit
```

- For cross-model comparison, `U-MyoPS` should ultimately be compared using **Stage 2 pathology predictions**, not Stage 1.
