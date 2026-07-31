# CARE-MyoWall-IF Interactive Execution

Formal arm training is intentionally not an `sbatch` job. The controller must run
one active step at a time inside an interactive allocation:

```bash
srun --jobid="$INTERACTIVE_JOB_ID" --overlap \
  --ntasks=1 --cpus-per-task=16 --gres=gpu:1 \
  bash -lc '/users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/training/myowall_if/run_pilot_arm.py --arm C0'
```

`run_pilot_arm.py` refuses formal training unless
`results/20260731_care_metric_truth_reconciliation/metric_truth_receipt.json`
has already been reconciled into `metric_dependency_receipt.json` with PASS.
