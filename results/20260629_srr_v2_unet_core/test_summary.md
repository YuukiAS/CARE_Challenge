# SRR-v2 Test Summary

Task: `prompts/tasks/20260629_srr_v2_unet_core.md`

## CPU Tiny Smoke

Command class: inline Python smoke using `SRRV2MyoPSUNet(base_channels=2, proposal_mode="none")`.

Result: `SRR_V2_TINY_SMOKE_OK`

Observed output:

- loss: `3.0656`
- gate count: `9`
- forward/backward completed on a tiny tensor with shape `(2, 3, 4, 16, 16)`
- missing-modality case used availability `[1, 0, 0]`
- invalid T2-private and T2-interaction gate weights were asserted to be `0.0`

## Scope

This is not the task-required formal GPU preflight. The submitted Slurm job `57094446_[0]` still needs to run the task-scoped 2-step GPU preflight and formal fold0 training for `srr_v2_multiscale_private_basic`.

## Runner CPU Preflights

- Output root: `results/20260629_srr_v2_unet_core/cpu_preflight`
- Scope: 1 training step plus patch validation through `scripts/training/run_srr_myops_fold0.py`, CPU only, `--skip-export`.

| variant | train loss | best val patch loss | proposal mode | proposal mix | hardneg components | checkpoint |
| --- | ---: | ---: | --- | ---: | ---: | --- |
| `srr_v2_multiscale_private_basic` | `3.9514` | `2.4594` | `none` | `0.00` | `0` | written |
| `srr_v2_multiscale_private_proposal` | `4.2588` | `2.4000` | `proposal_uncertainty_gate` | `0.45` | `0` | written |
| `srr_v2_proposal_uncertainty_hardneg` | `4.3738` | `2.5234` | `proposal_uncertainty_gate` | `0.45` | `5728` | written |

This validates the task runner path for the three required SRR-v2 variants, including loss wiring, proposal wiring, hard-negative loading for the hardneg variant, retrieval usage logging, checkpoint writing, and task-scoped output paths. It is not a formal metric result.
