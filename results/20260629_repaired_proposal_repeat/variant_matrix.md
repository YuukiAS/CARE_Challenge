# Repaired Proposal Repeat Variant Matrix

| variant | route | hard-negative use | proposal mix | job |
| --- | --- | --- | ---: | --- |
| `repaired_uncertainty_hardneg` | uncertainty-gated edema/no-T2 stability | edema-safe mined FP components | 0.45 | `57094448_0` |
| `repaired_posneg_scar_hardneg` | scar positive/negative prototype | scar-safe mined FP components | 0.40 | `57094448_1` |
| `repaired_joint_calibrated_proposal` | joint scar/edema proposal | replay-safe mined FP components | 0.50 | `57094448_2` |

Each Slurm task first runs a 2-step preflight under `results/20260629_repaired_proposal_repeat/preflight/` and then runs the formal fold0 job under `results/20260629_repaired_proposal_repeat/`.
