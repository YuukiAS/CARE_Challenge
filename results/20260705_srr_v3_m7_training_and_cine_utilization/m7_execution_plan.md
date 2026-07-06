# M7 Execution Plan

M7 runs the three required MyoPS variants from the M6 concrete architecture repairs. Each array task performs one-batch overfit first, then formal fold0 training with expanded M6 loss components, nnU-Net anchors, runtime prototype fitting, validation events, and fold0 prediction export.

M7 also starts the secondary Cine diagnostic subline by carrying the M5 audited CineMA/registration evidence into a M7 same-subset matrix and keeping temporal dictionary construction blocked unless a qualified non-reference registration option exists.

| routing job | partition | status snapshot |
| --- | --- | --- |
| `58003931` | `a100-gpu` | `58004740_0 COMPLETED 00:32:04; 58005318_1 COMPLETED 00:32:18; 58005318_2 COMPLETED 00:31:50` |
| `58003950` | `htzhulab` | `58004740_0 COMPLETED 00:32:04; 58005318_1 COMPLETED 00:32:18; 58005318_2 COMPLETED 00:31:50` |

Routing safety: `jobs/src/run_srr_v3_m7_myops_training.sh` uses a per-variant atomic lock under `runtime/routing_locks/` so a duplicate partition start exits instead of writing the same variant directory.
