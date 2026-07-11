# M10 Wave 2 Terminal Failure Receipt

Task key: `20260711_srr_v3_m10_complete_mechanism_repair`

Controller state: `NEEDS_EVIDENCE`

Formal monitor timestamp UTC: `2026-07-11T15:45:38Z`

## Slurm Accounting

| Phase | Job ID | State | Exit code | Elapsed | Node | Log |
| --- | ---: | --- | --- | --- | --- | --- |
| D0 static matched control | 58644072 | `FAILED` | `1:0` | `00:11:04` | `g180702` | `logs/M10D0MyoPS_58644072_20260711_110852.log` |
| D1 spatial BR2 | 58644073 | `FAILED` | `1:0` | `00:00:43` | `g180702` | `logs/M10D1MyoPS_58644073_20260711_112003.log` |
| D2 hierarchical PSIP | 58644074 | `FAILED` | `1:0` | `00:00:42` | `g180702` | `logs/M10D2MyoPS_58644074_20260711_112103.log` |
| D3 full memory PropRef | 58644106 | `FAILED` | `1:0` | `00:00:42` | `g180702` | `logs/M10D3MyoPS_58644106_20260711_112204.log` |
| Hard-negative refresh | 58644107 | `FAILED` | `1:0` | `00:00:43` | `g180702` | `logs/M10HardNeg_58644107_20260711_112305.log` |
| No-nnU-Net-context control | 58644108 | `FAILED` | `1:0` | `00:00:43` | `g180702` | `logs/M10NoCtx_58644108_20260711_112406.log` |
| Alignment control | 58644109 | `FAILED` | `1:0` | `00:00:42` | `g180702` | `logs/M10Align_58644109_20260711_112450.log` |

## Failure Cause

All seven logs fail on the same startup/runtime dependency path:

```text
ModuleNotFoundError: No module named 'mpmath'
ImportError: SymPy now depends on mpmath as an external library.
```

The failure occurs while PyTorch initializes `torch.optim.AdamW`, which imports `torch._dynamo`, `sympy`, and then `mpmath`.

## Local Environment Repair

The controller repaired the project-local environment after terminal accounting:

```text
./envs/env_CARE/bin/python -m pip install mpmath --cache-dir /tmp/codex-pip-cache
./envs/env_CARE/bin/python -m pip install 'mpmath<1.4,>=1.1.0' --force-reinstall --cache-dir /tmp/codex-pip-cache
./envs/env_CARE/bin/python -c 'import sympy, mpmath; ...'
./envs/env_CARE/bin/python -c 'import torch; ... torch.optim.AdamW(...)'
```

The first install selected `mpmath 1.4.1`, which was incompatible with `sympy 1.14.0`; it was corrected to `mpmath 1.3.0`. The minimal PyTorch optimizer check then passed.

`./envs/env_CARE/bin/pip check` still reports an unrelated existing dependency gap: `partd 1.4.2 requires locket, which is not installed`. This was not the M10 failure path and was not expanded in this packet.

## Aggregation

Fail-closed aggregation command:

```text
env PYTHONPATH=. python scripts/evaluation/aggregate_srr_v3_m10_myops.py --all --job-id ... --job-state ... --job-exit-code ... --job-log ...
```

Result: exit `2`, expected for `STARTUP_FAILED_NEEDS_EVIDENCE`.

The lightweight phase packets now record `slurm_state`, `slurm_exit_code`, and `slurm_log_path`. No terminal training runtime summaries, checkpoint selections, case metrics, or causal intervention evidence exist for wave 2.

## Decision

This is not M10 completion evidence and not a review request. The controller must not launch wave 3, request independent review, package/upload validation, claim hosted metrics, promote/stop a route, or start M11.

The safer next state is `NEEDS_EVIDENCE`: wave 2 terminal accounting exists, but the formal runtime evidence is missing because all jobs failed before producing valid summaries.
