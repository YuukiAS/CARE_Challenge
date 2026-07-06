# M7 Execution Plan

M7 runs the three required MyoPS variants from the M6 concrete architecture repairs. Each array task performs one-batch overfit first, then formal fold0 training with expanded M6 loss components, nnU-Net anchors, runtime prototype fitting, validation events, and fold0 prediction export.

| routing job | partition | status snapshot |
| --- | --- | --- |
| `58003931` | `a100-gpu` | `a100:PD(Priority); htzhulab:PD(Resources)` |
| `58003950` | `htzhulab` | `a100:PD(Priority); htzhulab:PD(Resources)` |

Routing safety: `jobs/src/run_srr_v3_m7_myops_training.sh` uses a per-variant atomic lock under `runtime/routing_locks/` so a duplicate partition start exits instead of writing the same variant directory.
