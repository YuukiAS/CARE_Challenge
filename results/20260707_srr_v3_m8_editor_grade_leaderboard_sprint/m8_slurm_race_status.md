# M8 Slurm Race Status

status: `RESOLVED_COMPLETED_AND_REAGGREGATED`

This file is a final routing summary for reviewer context. Earlier monitor states were superseded by completed Slurm accounting and post-completion aggregation into the tracked M8 evidence packet.

## MyoPS Training Race Resolution

- primary array job: `58081007`
- a100 mirror job: `58081025`
- task2 a100 mirror: `58081494`
- budget top-up htzhulab job: `58105084`
- budget top-up a100 mirror: `58105082`

Final accounting evidence recorded in `commands_run.md`:

- MyoPS task0 completed with exit `0:0`, elapsed `02:02:09`.
- MyoPS task1 completed with exit `0:0`, elapsed `02:02:00`.
- MyoPS task2 completed with exit `0:0`, elapsed `02:01:58`.
- budget top-up job `58105084` completed with exit `0:0`, elapsed `02:01:59`.
- a100 mirrors were cancelled after the htzhulab side started or completed under the lock/race policy.

The completed runtime summaries are aggregated into:

- `m8_training_budget_ledger.csv`
- `m8_training_curves.csv`
- `m8_validation_events.csv`
- `m8_loss_component_by_step.csv`
- `m8_srr_contribution_by_case.csv`
- `m8_same_split_help_harm.csv`

## Broad Evidence Supplement

Additional eval-only broad fold0 evidence was run as job `58123097` on `htzhulab`.

Final accounting:

- state: `COMPLETED`
- exit code: `0:0`
- elapsed: `00:01:33`
- log: `logs/M8BroadEval_58123097_20260707_061559.log`
- runtime output root: `results/20260707_srr_v3_m8_editor_grade_leaderboard_sprint/runtime/broad_eval/`

This broad eval added 12 fold0 validation cases: 7 CenterB and 5 CenterC, all `C0+LGE+T2`, T2-present, scar-positive, and edema-positive. It was eval-only and did not launch training, create a validation package, upload, or make hosted metric claims.
