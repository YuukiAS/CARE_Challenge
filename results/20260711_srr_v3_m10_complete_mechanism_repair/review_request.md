# M10 Monitor Packet Review Boundary

This packet does not request normal M10 scientific review. It records an authorized same-executor Wave 2 replacement submission after successful compute-node preflight.

Current state: `NEEDS_MONITOR`

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
