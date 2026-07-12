# M10 Wave 2 Replacement Preflight Receipt

Task key: `20260711_srr_v3_m10_complete_mechanism_repair`

Controller state: `NEEDS_MONITOR`

Timestamp UTC: `2026-07-12T02:04:11Z`

## Authorization Boundary

This is the same `m10_myops_training_executor` and the same M10 Wave 2 contract. It is a replacement attempt for startup-failed Wave 2 jobs, not a new milestone, not a new executor, not Wave 3, and not follow-up planning.

No variant definitions, formulas, budgets, split, case set, evaluation rules, checkpoint-selection rules, result paths, executor count, or wave graph were changed.

## Old Jobs

Old failed jobs are permanently recorded in `wave2_startup_failed_jobs.csv` with:

```text
state: STARTUP_FAILED
training_credit: 0
optimizer_steps_credit: 0
train_loop_seconds_credit: 0
```

They must not count toward M10 minimum-effective-training.

## Preflight

Preflight script:

```text
results/20260711_srr_v3_m10_complete_mechanism_repair/wave2_env_preflight.sh
```

The script uses the same environment initialization as the formal Wave 2 job wrappers:

```text
cd "${CARE_ROOT}"
source "${CARE_ROOT}/.care-codex-env.sh"
source "${CARE_ROOT}/env_nnunet.sh"
export PATH=/users/a/e/aereinh/codex-runtime/bin:${CARE_ROOT}/envs/env_CARE/bin:${PATH}
```

Preflight command inside the Slurm job:

```bash
env_CARE/bin/python - <<'PY'
import mpmath
import sympy
import torch

p = torch.nn.Parameter(torch.ones(1))
torch.optim.AdamW([p], lr=1e-3)

print("mpmath", mpmath.__version__)
print("sympy", sympy.__version__)
print("optimizer_ok")
PY
```

Submission command:

```text
sbatch --parsable results/20260711_srr_v3_m10_complete_mechanism_repair/wave2_env_preflight.sh
```

Preflight job ID: `58682781`

Current preflight state at submission check:

```text
58682781|M10W2Preflight|PENDING|0:00|1|(Priority)|htzhulab
```

Formal replacement jobs were not submitted yet because the preflight has not returned exit code `0`.

## Hashes

| Item | SHA256 |
| --- | --- |
| `scripts/training/run_srr_v3_m10_complete_repair.py` | `dea785502dc2aa2e44f9d9cc7ad5acdfae155fe94a20ccf8ab9444f15060520d` |
| `scripts/evaluation/evaluate_srr_v3_m10_full_case.py` | `c418afc5ab734b506ebc4e15d5515b73edb65831b81ec7971e81d0ec02c4b615` |
| `scripts/evaluation/aggregate_srr_v3_m10_myops.py` | `87dd829e9908e09cf69e512df681a8c89c5a6560eca0a0693bde23128f801be5` |
| `configs/srr_v3_m10_complete_repair.yaml` | `df42f9ee55a3ba6ac616a37b2455cb7bca67c5f751f0c5a31c4a18938b107a9b` |
| `prompts/tasks/20260711_srr_v3_m10_complete_mechanism_repair_executor_plan.yaml` | `e11f985c2e58ab291c5197ea3843f7c20d944d4d6b288d6242fe8375e432d31c` |
| `wave2_env_preflight.sh` | `6c3971fe7201366df75fdd3618255a2c0fc649a8a4f102597a959fe0bab5a643` |
| fold0 split payload | `483dfcd0736d00a87adc24b3a9a22de0a0ec3a8980f8f2ee068430672bcf7f96` |

Fold0 split counts: 176 train cases, 44 validation cases.

## Next Action

Wait for terminal preflight accounting. If and only if preflight exits `0`, submit the seven Wave 2 formal replacement jobs with training-to-training `afterok` dependencies. The Wave 2 finalizer must use `afterany` over every old and replacement job ID.
