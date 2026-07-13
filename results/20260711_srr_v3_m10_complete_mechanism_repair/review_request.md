# M10 Monitor Packet Review Boundary

This packet does not request normal M10 scientific review. It records an authorized same-executor Wave 2 replacement submission after successful compute-node preflight.

Current state: `NEEDS_MONITOR`

## Current Retry11 Monitor Update

As of `2026-07-13T06:02:30Z`, retry11 is the active same-executor Wave 2 replacement after an owned-wrapper gate-usage evidence logging repair. Htzhulab preflight `58775059` completed `0:0`; a100 preflight `58775057` was cancelled unused while pending; volta preflight `58775058` failed `1:0` because the current PyTorch CUDA build cannot execute kernels on V100.

Formal retry11 jobs are:

| Phase | Replacement job | State at submission check |
| --- | ---: | --- |
| D1 spatial BR2 | `58775065` | `RUNNING` |
| D2 hierarchical PSIP | `58775066` | `PENDING (Dependency)` |
| D3 full memory PropRef | `58775067` | `PENDING (Dependency)` |
| Hard-negative refresh | `58775068` | `PENDING (Dependency)` |
| No-nnU-Net-context control | `58775069` | `PENDING (Dependency)` |
| Alignment control | `58775070` | `PENDING (Dependency)` |

Finalizer job `58775071` is pending with `afterany` over old and retry11 job IDs. This is still a monitor packet. Do not perform normal M10 review yet.

Formal replacement jobs submitted:

| Phase | Replacement job | State at submission check |
| --- | ---: | --- |
| D0 static matched control | `58700815` | `PENDING (Resources)` |
| D1 spatial BR2 | `58700821` | `PENDING (Dependency)` |
| D2 hierarchical PSIP | `58700822` | `PENDING (Dependency)` |
| D3 full memory PropRef | `58700826` | `PENDING (Dependency)` |
| Hard-negative refresh | `58700827` | `PENDING (Dependency)` |
| No-nnU-Net-context control | `58700828` | `PENDING (Dependency)` |
| Alignment control | `58700832` | `PENDING (Dependency)` |

Finalizer job `58700842` is pending with `afterany` over all old and replacement jobs.

Blocked actions until terminal post-job aggregation exists: write `review.md`, launch Wave 3, package/upload validation, claim hosted metrics, claim route promotion or scientific stop, or start M11.

## Latest Monitor Update

The single-partition replacement chain was superseded by an explicitly user-authorized three-partition race. `volta-gpu` won: preflight `58701110` completed `0:0`, D0 `58701111` is running, watcher `58701118` cancelled `htzhulab` and `a100-gpu` pending mirrors, and finalizer `58701119` is pending on `afterany`.

This is still a monitor packet. Do not perform normal M10 review yet.

## Latest Retry Update

`volta-gpu` was excluded after D0 `58701111` failed with unsupported V100 CUDA kernel execution. A same-scope `htzhulab`/`a100-gpu` retry race is pending under preflight jobs `58701195` and `58701203`, watcher `58701211`, and finalizer `58701212`.

This remains a monitor packet. Do not perform normal M10 review yet.

## Retry3 Volta Add-On Update

After the user explicitly authorized adding `volta-gpu` back into this same current goal, the controller submitted a three-partition retry3 packet without changing the Wave 2 scientific contract. Existing htz/a100 jobs remain active; added volta jobs are preflight `58701281` and afterok formal chain `58701282`-`58701288`.

The hardened volta preflight failed `1:0` in `00:00:47` on `g0303` because the CUDA kernel probe hit the known PyTorch/V100 incompatibility: `CUDA error: no kernel image is available for execution on the device`. The formal volta jobs were cancelled by the failed `afterok` dependency and receive zero training credit.

The active monitor jobs are watcher `58701289` and finalizer `58701290`. htz preflight `58701195` and a100 preflight `58701203` remain pending; this is still `NEEDS_MONITOR`, not a normal review request.

## Retry3 Monitor Check 1

At `2026-07-12T12:53:05Z`, retry3 remained pending-only: htz preflight `58701195` and a100 preflight `58701203` were still `PENDING (Priority)`, and both formal chains remained dependency-pending. Watcher `58701289` was running and finalizer `58701290` was dependency-pending.

This is checkpoint `1/12` for the 24-hour scheduler saturation threshold. It remains a monitor packet. Do not perform normal M10 review yet.

## Retry3 Terminal Update

The retry3 Slurm graph is no longer pending or running. It is terminal but not successful:

- `58701195` htz preflight completed `0:0`.
- `58701196` htz D0 failed `1:0` after `00:00:56`.
- `58701197`-`58701202` were cancelled by unmet `afterok`.
- `58701203`-`58701210` a100 mirror jobs were cancelled by the watcher after htz D0 started first.
- `58701289` watcher completed `0:0`.
- `58701290` finalizer failed `1:0`.
- Local aggregation replay wrote `wave2_partition_race_retry3_finalization.json` and exited `2`.

Failure cause: `logs/M10D0MyoPS_58701196_20260712_090210.log` raises `KeyError: 'correction_opportunity_loss'` while training writes metrics in `scripts/training/run_srr_propref_myops_fold0.py`.

This retry3 packet did not request normal M10 review. It was `NEEDS_EVIDENCE`; Wave 2 had produced no valid formal training evidence, Wave 3 could not start, and no `review.md` should be written for that packet.

## Retry4 Monitor Update

After a same-scope owned-wrapper operational repair and successful repaired-code `htzhulab` preflight `58706079`, the controller submitted the unchanged retry4 Wave 2 formal chain: `58706293`-`58706299`. D0 `58706293` is currently `RUNNING`; the downstream jobs are dependency-pending, and finalizer `58706300` is dependency-pending with `afterany`.

This packet still does not request normal M10 review. Current state is `NEEDS_MONITOR`; Wave 2 has not reached terminal aggregation, Wave 3 must not start, and no `review.md` should be written for this packet.

## Retry4 Terminal Update

Retry4 is terminal but not complete. D0 `58706293` completed and produced formal D0 evidence. D1 `58706294` failed with a nested gate-usage logging error, D2-through-alignment were cancelled by `afterok`, and finalizer `58706300` failed fail-closed.

The controller applied a same-scope owned-wrapper logging repair and has not requested normal review. Current state is `NEEDS_EVIDENCE` pending repaired-code compute-node preflight and D1-through-alignment replacement submission. Wave 3 must not start, and no `review.md` should be written for this packet.

## Retry5 Monitor Update

Repaired-code compute-node preflight `58714000` completed `0:0`, and retained upstream D0 `58706293` was verified as `COMPLETED 0:0`. The controller submitted the D1-through-alignment replacement chain:

- D1 `58714023` is currently `RUNNING`.
- D2-D3 and controls `58714024`-`58714028` are `PENDING (Dependency)`.
- Finalizer `58714029` is `PENDING (Dependency)` with `afterany`.

Current state is `NEEDS_MONITOR`, not a normal review request. Wave 2 terminal aggregation has not completed; Wave 3 must not start, and no `review.md` should be written for this packet.

## Retry6 Monitor Update

Retry5 is terminal but not complete: D1 `58714023` failed as `OUT_OF_MEMORY 0:125` with `ReqMem=64G` and batch `MaxRSS=67107264K`; downstream jobs were cancelled by `afterok`; finalizer `58714029` failed fail-closed.

The controller submitted same-scope retry6 with only the Slurm memory request increased to `96G`. Preflight `58714615` completed `0:0`. D1 `58714634` is currently `RUNNING`, D2-through-alignment `58714635`-`58714639` are dependency-pending, and finalizer `58714640` is dependency-pending.

Current state remains `NEEDS_MONITOR`, not a normal review request. Wave 2 terminal aggregation has not completed; Wave 3 must not start, and no `review.md` should be written for this packet.

## Retry8 Monitor Update

Retry7 is terminal but not complete: D1 `58719835` failed as `OUT_OF_MEMORY 0:125` with `ReqMem=128G` and batch `MaxRSS=134216104K`; downstream jobs were cancelled by `afterok`; finalizer `58719841` failed fail-closed. Local replay wrote `wave2_partition_race_retry7_finalization.json` with `NEEDS_EVIDENCE`.

The controller submitted same-scope retry8 with `--qos=gpu_access_patron --mem=160G` after `gpu_access` rejected 160G via `QOSMaxMemoryPerJob`. Preflight `58720440` completed `0:0`. D1 `58720458` is currently `RUNNING`, D2-through-alignment `58720459`-`58720463` are dependency-pending, and finalizer `58720464` is dependency-pending.

Current state remains `NEEDS_MONITOR`, not a normal review request. Wave 2 terminal aggregation has not completed; Wave 3 must not start, and no `review.md` should be written for this packet.

## Retry7 Monitor Update

Retry6 is terminal but not complete: D1 `58714634` failed as `OUT_OF_MEMORY 0:125` with `ReqMem=96G` and batch `MaxRSS=100661736K`; downstream jobs were cancelled by `afterok`; finalizer `58714640` failed from an aggregation-command argument-format issue. Local replay wrote `wave2_partition_race_retry6_finalization.json` with `NEEDS_EVIDENCE`.

The controller submitted same-scope retry7 with only the Slurm memory request increased to `128G`. Preflight `58719811` completed `0:0`. D1 `58719835` is currently `RUNNING`, D2-through-alignment `58719836`-`58719840` are dependency-pending, and finalizer `58719841` is dependency-pending.

Current state remains `NEEDS_MONITOR`, not a normal review request. Wave 2 terminal aggregation has not completed; Wave 3 must not start, and no `review.md` should be written for this packet.
