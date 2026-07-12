# M10 Wave 2 Retry3 Volta Failure Receipt

Status: `NEEDS_MONITOR`

This receipt records the user-authorized addition of `volta-gpu` to the current M10 Wave 2 routing race. It is not a new milestone, not a new executor, and not a scientific contract change.

## Jobs

| Stage | Job ID | State | Credit |
| --- | ---: | --- | --- |
| volta compute preflight | `58701281` | `FAILED 1:0` | zero training credit |
| D0 static matched control | `58701282` | `CANCELLED` | zero |
| D1 spatial BR2 | `58701283` | `CANCELLED` | zero |
| D2 hierarchical PSIP | `58701284` | `CANCELLED` | zero |
| D3 full memory PropRef | `58701285` | `CANCELLED` | zero |
| hard-negative refresh | `58701286` | `CANCELLED` | zero |
| no-context control | `58701287` | `CANCELLED` | zero |
| alignment control | `58701288` | `CANCELLED` | zero |

## Failure Cause

Log: `logs/M10W2Preflight_volta-gpu_58701281_20260712_065303.log`

The preflight confirmed:

- `mpmath 1.3.0`
- `sympy 1.14.0`
- `optimizer_ok`
- visible GPU: `Tesla V100-SXM2-16GB`

It failed at the CUDA kernel execution probe with:

```text
CUDA error: no kernel image is available for execution on the device
```

The log reports that the current `torch 2.11.0+cu130` build supports compute capability `>=7.5`, while the V100 device is compute capability `7.0`. The formal training chain was protected by `afterok:58701281`, so no volta training stage started.

## Active Race

The active effective routing race remains:

- htz preflight `58701195`, formal chain `58701196`-`58701202`
- a100 preflight `58701203`, formal chain `58701204`-`58701210`
- retry3 watcher `58701289`
- retry3 finalizer `58701290`

Current state remains `NEEDS_MONITOR`, not complete and not reviewable.
