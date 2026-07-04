# Uncommitted Required Evidence

## Safe To Keep Uncommitted

These files exist locally or are referenced by committed manifests, but are intentionally ignored/heavy and should not be committed as diagnostic publication:

- `logs/MyoPSAnchorSRRF0_0_57782213_20260704_022627.log`
- `logs/MyoPSAnchorSRRF0_1_57782214_20260704_022627.log`
- `logs/MyoPSAnchorSRRF0_2_57782211_20260704_022627.log`
- `results/20260704_myops_anchor_srr_fold0_formal/variants/*/checkpoints/`
- `results/20260704_myops_anchor_srr_fold0_formal/variants/*/predictions/`

Reason: logs are under ignored `logs/`; checkpoints and NIfTI predictions are heavy runtime outputs under ignored `results/20??????_*/`. Publishing them would violate the diagnostic publication boundary.

## Evidence Missing Or Weak

- Slurm logs are 0 bytes, so they do not prove the command transcript.
- `results/20260704_myops_anchor_srr_fold0_formal/command_transcript.md` records only aggregation command and says formal training command evidence was not recorded.
- No committed evidence was found that formal fold0 loaded a real train/OOF data-derived prototype bank before training. The code has `load_prototype_bank`, but formal evidence shows deterministic bootstrap/prototype update sanity and hard-negative memory rather than a complete prototype-cache provenance chain.
- No complete registration option matrix was found for this task. Controller evidence records a Cine registration gap.

## Committed Substitutes

The following committed evidence is acceptable for current-packet forensic review:

- `jobs/src/run_myops_anchor_srr_fold0_formal.sh`
- `results/20260704_myops_anchor_srr_fold0_formal/job_status.md`
- `results/20260704_myops_anchor_srr_fold0_formal/experiment_adequacy_report.md`
- `results/20260704_myops_anchor_srr_fold0_formal/metrics_summary.md`
- `results/20260704_myops_anchor_srr_fold0_formal/no_t2_decode_sanity.csv`
- `results/20260704_myops_anchor_srr_fold0_formal/variants/*/summary.json`
- `results/20260704_myops_anchor_srr_fold0_formal/variants/*/configs/run_config.env`

