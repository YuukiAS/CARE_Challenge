# CARE Benchmark Runbook

Benchmark training / collection / unified evaluation commands live in [code/README.md](/overflow/htzhu/CARE/code/README.md).

Most common entrypoints:

```bash
# Single-fold smoke test (default fold 0): prep + submit
bash code/run_unified_benchmark_test.sh

# Single-fold postprocessing after jobs finish: collect + unified eval
bash code/run_unified_benchmark_test.sh post --fold 0

# Full 5-fold benchmark: prep + submit
bash code/run_unified_benchmark_all.sh

# Full 5-fold postprocessing after jobs finish: collect + unified eval
bash code/run_unified_benchmark_all.sh post

# nnUNet501 + nnUNet502 were already trained: collect all 5 folds into models/
bash code/collect_benchmark_weights.sh --folds "0 1 2 3 4" --only nnUNet
```

Notes:

- `code/run_unified_benchmark.sh` is a helper for protocol generation and split injection. You usually do not call it directly except for inspection/debugging.
- `code/run_unified_benchmark_test.sh` and `code/run_unified_benchmark_all.sh` each contain a single `BENCHMARK_MODEL_PLAN` block near the top. Edit that list to mark each model as `run`, `eval`, or `skip`.
- `U-MyoPS` Stage 2 is off by default. Enable only after its nnU-Net v1 task + preprocessing are ready:

```bash
UMYOPS_RUN_STAGE2=1 bash code/run_unified_benchmark_all.sh
```
