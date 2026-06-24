# Result 20260621 SRR Goal

status: `MYOPS_REVISE_SRR`

## Summary

Executed the authorized MyoPS SRR path through the handoff protocol:

1. `20260621_srr_spec` completed with `GO_FOLD0`.
2. `20260621_srr_fold0` completed with `REVISE_ROUTING`.
3. Ablation and fold expansion were not started because fold0 did not reach `GO_ABLATION`.

The separate Cine retrieval line is recorded as `REVISE_GEOMETRY` in its independent worktree and did not submit training jobs.

## Primary Artifacts

- `results/20260621_srr_goal/progress.md`
- `results/20260621_srr_goal/final_status.md`
- `results/20260621_srr_goal/MANIFEST.md`
- `results/20260621_srr_spec/result.md`
- `results/20260621_srr_spec/MANIFEST.md`
- `results/20260621_srr_fold0/result.md`
- `results/20260621_srr_fold0/MANIFEST.md`
- `results/20260621_srr_fold0/decision.md`
- `results/20260621_srr_fold0/metrics_summary.md`
- `results/20260621_srr_fold0/retrieval_usage.md`

## Gate Outcome

Fold0 decision: `REVISE_ROUTING`.

Reason: `srr_minimal` improved fold0 edema GT-positive Dice and scar all-case Dice versus the conditional control, and improved edema GT-positive HD95, but the retrieval gate showed row-level expert weights at `1.0000` and scar usage concentrated on expert1 with mean `0.9431`.

## Constraints Observed

- no network
- no external upload
- no validation submission or upload-ready package
- no external data or new weights
- no patches to `third_party/MyoPS-Net`, `third_party/U-MyoPS`, or old baseline defaults
- no no-T2 edema hard-negative dense supervision
- all single Slurm jobs were `<=08:00:00`
- final formal jobs used task-scoped, variant-scoped, fold-scoped, checkpoint/config-scoped outputs

## Final Status

See `results/20260621_srr_goal/final_status.md`.
