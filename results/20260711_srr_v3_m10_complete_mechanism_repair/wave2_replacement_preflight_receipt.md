# M10 Wave 2 Replacement Preflight Receipt

Task key: `20260711_srr_v3_m10_complete_mechanism_repair`

Controller state: `NEEDS_MONITOR`

Timestamp UTC: `2026-07-12T02:16:58Z`

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

The active preflight wrapper is now an enhanced superset required by the current
Slurm skill. It keeps the user-required optimizer/import block exactly and adds
CUDA visibility, config parse, phase contract print, output/log/lock
writability, and code/config/split fingerprints. No formal training command,
variant definition, budget, split, or result root was changed.

User-required preflight command inside the Slurm job:

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

Current active preflight submission command:

```text
sbatch --parsable results/20260711_srr_v3_m10_complete_mechanism_repair/wave2_env_preflight.sh
```

Active preflight job ID: `58683497`

Current active preflight state at submission check:

```text
58683497|M10W2Preflight|PENDING|0:00|1|(Priority)|htzhulab
```

Formal monitor check at `2026-07-12T04:17:34Z`:

```text
squeue: 58683497|M10W2Preflight|PENDING|0:00|1|(Priority)|htzhulab
sacct:  58683497|M10W2Preflight|PENDING|0:0|00:00:00|Unknown|Unknown|None assigned
```

This is pending-only monitor evidence, not a scheduler block. It is the first
2-hour monitor check after active enhanced preflight submission. No submitted
routing partition has started, and the next legal pending-only monitor check is
`2026-07-12T06:17:34Z` unless the scheduler state changes through an external
notification before then.

Formal monitor check at `2026-07-12T06:18:01Z`:

```text
squeue: 58683497|M10W2Preflight|PENDING|0:00|1|(Priority)|htzhulab
sacct:  58683497|M10W2Preflight|PENDING|0:0|00:00:00|Unknown|Unknown|None assigned
```

This is the second consecutive pending-only 2-hour monitor check after active
enhanced preflight submission. No submitted routing partition has started. It
remains `NEEDS_MONITOR`, not scheduler saturation; the next legal pending-only
monitor check is `2026-07-12T08:18:01Z` unless the scheduler state changes
through an external notification before then.

Formal monitor check at `2026-07-12T08:18:34Z`:

```text
squeue: 58683497|M10W2Preflight|PENDING|0:00|1|(Priority)|htzhulab
sacct:  58683497|M10W2Preflight|PENDING|0:0|00:00:00|Unknown|Unknown|None assigned
```

This is the third consecutive pending-only 2-hour monitor check after active
enhanced preflight submission. No submitted routing partition has started. It
remains `NEEDS_MONITOR`, not scheduler saturation; the next legal pending-only
monitor check is `2026-07-12T10:18:34Z` unless the scheduler state changes
through an external notification before then.

Prior preflight job `58682781` used the same environment initialization and the
user-required import/optimizer block, but it was superseded before formal job
submission because the current Slurm skill requires the enhanced preflight
checks listed above. It is not a formal replacement-job gate.

Formal replacement jobs were not submitted yet because the active enhanced
preflight has not returned exit code `0`.

## Hashes

| Item | SHA256 |
| --- | --- |
| `scripts/training/run_srr_v3_m10_complete_repair.py` | `dea785502dc2aa2e44f9d9cc7ad5acdfae155fe94a20ccf8ab9444f15060520d` |
| `scripts/evaluation/evaluate_srr_v3_m10_full_case.py` | `c418afc5ab734b506ebc4e15d5515b73edb65831b81ec7971e81d0ec02c4b615` |
| `scripts/evaluation/aggregate_srr_v3_m10_myops.py` | `87dd829e9908e09cf69e512df681a8c89c5a6560eca0a0693bde23128f801be5` |
| `configs/srr_v3_m10_complete_repair.yaml` | `df42f9ee55a3ba6ac616a37b2455cb7bca67c5f751f0c5a31c4a18938b107a9b` |
| `prompts/tasks/20260711_srr_v3_m10_complete_mechanism_repair_executor_plan.yaml` | `e11f985c2e58ab291c5197ea3843f7c20d944d4d6b288d6242fe8375e432d31c` |
| `wave2_env_preflight.sh` | `dcc3f5348b187bd40d3ad80b416883e7cdf5967fce78c8967738ba065d637632` |
| fold0 split payload | `483dfcd0736d00a87adc24b3a9a22de0a0ec3a8980f8f2ee068430672bcf7f96` |

Fold0 split counts: 176 train cases, 44 validation cases.

## Next Action

Wait for terminal accounting for active enhanced preflight job `58683497`. If
and only if it exits `0`, submit the seven Wave 2 formal replacement jobs with
training-to-training `afterok` dependencies. The Wave 2 finalizer must use
`afterany` over every old and replacement job ID.


## Three-Partition Preflight Race And Replacement Submission

Update timestamp UTC: `2026-07-12T10:16:12Z`

The user explicitly authorized a three-partition preflight race across `htzhulab`, `a100-gpu`, and `volta-gpu`. The controller cancelled still-pending mirrors as soon as a candidate started, per AGENTS/slurm-routing policy.

Race outcome:

| Job ID | Partition | State | Notes |
| ---: | --- | --- | --- |
| `58682781` | `htzhulab` | `CANCELLED_SUPERSEDED` | earlier weaker preflight, not a formal gate |
| `58683497` | `htzhulab` | `CANCELLED_RACE_MIRROR` | cancelled after a mirror started |
| `58700697` | `a100-gpu` | `CANCELLED_RACE_MIRROR` | cancelled after a mirror started |
| `58700698` | `volta-gpu` | `FAILED 127:0` | stale wrapper failed before early logging |
| `58700726` | `volta-gpu` | `FAILED 127:0` | diagnosed stale relative `env_CARE/bin/python` path |
| `58700727` | `a100-gpu` | `CANCELLED_STALE_WRAPPER` | cancelled before start after wrapper path fix |
| `58700728` | `htzhulab` | `CANCELLED_STALE_WRAPPER` | cancelled before start after wrapper path fix |
| `58700749` | `a100-gpu` | `CANCELLED_RACE_MIRROR` | fixed mirror cancelled after `58700751` started |
| `58700750` | `htzhulab` | `CANCELLED_RACE_MIRROR` | fixed mirror cancelled after `58700751` started |
| `58700751` | `volta-gpu` | `COMPLETED 0:0` | successful enhanced compute-node preflight; log `logs/M10W2Preflight_volta-gpu_58700751_20260712_060557.log` |

Successful preflight evidence includes `mpmath 1.3.0`, `sympy 1.14.0`, `optimizer_ok`, CUDA visibility, config parse, writable output/log/lock/runtime roots, code/config/split fingerprints, phase listing, and per-phase print-contract output.

After preflight exit code `0`, the controller submitted the original seven Wave 2 formal replacement jobs as a serial `afterok` chain without changing variants, formulas, budgets, split, case set, evaluation rules, checkpoint-selection rules, result paths, executor count, or wave graph.

| Phase | Old job | Replacement job | Dependency | Partition |
| --- | ---: | ---: | --- | --- |
| d0_control | `58644072` | `58700815` | `none after preflight` | `htzhulab` |
| d1_spatial_br2 | `58644073` | `58700821` | `afterok:58700815` | `htzhulab` |
| d2_hierarchical_psip | `58644074` | `58700822` | `afterok:58700821` | `htzhulab` |
| d3_full_propref | `58644106` | `58700826` | `afterok:58700822` | `htzhulab` |
| hard_negative_refresh | `58644107` | `58700827` | `afterok:58700826` | `htzhulab` |
| no_context_control | `58644108` | `58700828` | `afterok:58700827` | `htzhulab` |
| alignment_control | `58644109` | `58700832` | `afterok:58700828` | `htzhulab` |

Wave 2 accounting finalizer job: `58700842` with `afterany` over every old and replacement job ID.

Current state remains `NEEDS_MONITOR`: D0 is pending on `htzhulab` resources, downstream jobs are dependency-pending, and finalizer is dependency-pending. This is not completion evidence and not reviewable.
