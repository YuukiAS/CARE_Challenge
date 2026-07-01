# Repaired Proposal CPU Preflight Summary

Task: `prompts/tasks/20260629_repaired_proposal_repeat.md`

## CPU Smokes

- Output root: `results/20260629_repaired_proposal_repeat/cpu_preflight`
- Scope: 1 training step plus patch validation per variant, CPU only, `--skip-export`.
- Purpose: verify repaired proposal loss path, hard-negative replay loading, proposal mix configuration, checkpoint writing, and task-scoped output paths.

## Results

| variant | train loss | best val patch loss | hardneg cases | hardneg components | proposal mode | proposal mix | checkpoint |
| --- | ---: | ---: | ---: | ---: | --- | ---: | --- |
| `repaired_uncertainty_hardneg` | `4.7372` | `3.3294` | `39` | `1561` | `proposal_uncertainty_gate` | `0.45` | written |
| `repaired_posneg_scar_hardneg` | `5.1300` | `3.5163` | `44` | `4167` | `proposal_pos_neg_basic` | `0.40` | written |
| `repaired_joint_calibrated_proposal` | `4.7866` | `3.3479` | `44` | `5728` | `proposal_uncertainty_gate` | `0.50` | written |

All variants used `results/20260629_proposal_memory_hardneg/mined_components.csv`, wrote best/final checkpoints under task-scoped preflight output, and skipped full prediction export.

## Scope Caveat

This is not the task-required formal GPU preflight or a formal metric result. The submitted Slurm array `57094448_[0-2]` still needs to run the task-scoped GPU preflight and 6-7 hour formal jobs.
