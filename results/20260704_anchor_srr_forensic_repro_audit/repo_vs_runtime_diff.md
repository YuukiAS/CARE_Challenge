# Repo vs Runtime Diff

## Git State

- `HEAD`: `39f9a573b1db33bbf99880d63c0d40a9cd7a1d8e`
- recent commit: `39f9a57 Implement anchored SRR v2.5 diagnostics`
- branch status at audit start: `## main...origin/main [ahead 1]`
- tracked worktree dirt: none reported by `git status --short --branch`

## Committed Evidence

These are tracked by git and sufficient for lightweight diagnostic publication if selected with explicit `git add -f` rules for ignored result paths:

- `src/care_myocardium/models/srr_propref.py`
- `src/care_myocardium/models/srr_v2_unet.py`
- `src/care_myocardium/losses/srr_losses.py`
- `scripts/training/run_srr_propref_myops_fold0.py`
- `jobs/src/run_myops_anchor_srr_fold0_formal.sh`
- `scripts/evaluation/aggregate_myops_anchor_srr_fold0_formal_20260704.py`
- `results/20260704_myops_anchor_srr_fold0_formal/result.md`
- `results/20260704_myops_anchor_srr_fold0_formal/review.md`
- `results/20260704_myops_anchor_srr_fold0_formal/job_status.md`
- `results/20260704_myops_anchor_srr_fold0_formal/experiment_adequacy_report.md`
- `results/20260704_myops_anchor_srr_fold0_formal/metrics_summary.md`
- `results/20260704_myops_anchor_srr_fold0_formal/no_t2_decode_sanity.csv`
- `results/20260704_myops_anchor_srr_fold0_formal/variants/*/summary.json`
- `results/20260704_myops_anchor_srr_fold0_formal/variants/*/configs/run_config.env`
- `results/20260704_anchor_srr_v25_goal/audit_summary.md`
- `results/20260704_anchor_srr_v25_goal/controller_report.md`

## Runtime/Heavy Evidence Not Committed

The following are local runtime/heavy artifacts and should not be published wholesale:

- `logs/MyoPSAnchorSRRF0_*_57782211_*.log`
- `logs/MyoPSAnchorSRRF0_*_57782213_*.log`
- `logs/MyoPSAnchorSRRF0_*_57782214_*.log`
- `results/20260704_myops_anchor_srr_fold0_formal/variants/*/checkpoints/`
- `results/20260704_myops_anchor_srr_fold0_formal/variants/*/predictions/`

`git check-ignore -v` confirms logs are ignored by `.gitignore:6:logs/`, and checkpoints/predictions under `results/20??????_*/` are ignored by `.gitignore:195`.

## Runtime Evidence Caveat

The three Slurm log files found for `57782211`, `57782213`, and `57782214` are 0 bytes. Therefore they are only path/provenance placeholders. Training behavior must be reviewed from committed summaries and CSVs, not from stdout/stderr.

