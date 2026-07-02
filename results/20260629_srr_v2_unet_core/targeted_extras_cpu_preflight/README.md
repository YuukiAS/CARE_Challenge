# SRR-v2 Targeted Extras CPU Preflight

Generated: `2026-07-02 00:32 EDT`

These are CPU-only two-step preflights for the two targeted SRR-v2 extra
variants queued on GPU partitions. They validate argument wiring, data loading,
loss computation, checkpoint writing, and hard-negative component loading while
the GPU partitions are unavailable. They are not route-quality evidence because
export/evaluation was intentionally skipped.

| variant | base variant | stop reason | budget status | best val patch loss | elapsed seconds | note |
| --- | --- | --- | --- | ---: | ---: | --- |
| `srr_v2_edema_t2_focus` | `srr_v2_multiscale_private_proposal` | `max_steps` | `OK` | `2.0601760347684226` | `27.6` | Edema-weighted T2-positive focus; hard-negative probability `0.05`; proposal final mix `0.30`. |
| `srr_v2_scar_precision_nointeract` | `srr_v2_proposal_uncertainty_hardneg` | `max_steps` | `OK` | `3.3605021437009177` | `19.3` | Scar-weighted precision probe; hard-negative probability `0.70`; proposal final mix `0.18`; SRR-v2 interactions disabled. |

Tracked evidence files:

- `variants/srr_v2_edema_t2_focus/summary.md`
- `variants/srr_v2_edema_t2_focus/summary.json`
- `variants/srr_v2_edema_t2_focus/training_log.csv`
- `variants/srr_v2_edema_t2_focus/retrieval_usage.csv`
- `variants/srr_v2_scar_precision_nointeract/summary.md`
- `variants/srr_v2_scar_precision_nointeract/summary.json`
- `variants/srr_v2_scar_precision_nointeract/training_log.csv`
- `variants/srr_v2_scar_precision_nointeract/retrieval_usage.csv`

Ignored local files:

- `variants/*/checkpoints/`
- `variants/*/predictions/`

The queued GPU jobs remain the authoritative route-quality runs because they
perform the full training/export/evaluation path under isolated output roots.
