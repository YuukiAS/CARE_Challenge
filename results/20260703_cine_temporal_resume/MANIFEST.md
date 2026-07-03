# MANIFEST

- Task: `prompts/tasks/20260703_cine_temporal_resume.md`
- Controller task: `prompts/tasks/20260703_mainline_resume_goal.md`
- Result: `results/20260703_cine_temporal_resume/result.md`
- Review placeholder: `results/20260703_cine_temporal_resume/review.md` (not written by executor)

## Artifacts

- `resource_audit.md`: dependencies, resource use, and variant coverage.
- `safe_cases_used.csv`: safe case list with reference/non-reference frame usage.
- `mismatch_cases_heldout.csv`: held-out mismatch cases requiring header/resample repair before supervised scoring.
- `reference_frame_contract.md`: reference frame and non-reference frame route statement.
- `motion_or_warp_metrics.csv`: per-case/per-class anatomy consistency and frame-to-reference similarity summary.
- `warp_sanity.csv`: dense optical-flow/descriptor runtime, smoothness, folding, and similarity diagnostics.
- `temporal_metrics_summary.md`: aggregate proxy metrics and temporal diagnostics.
- `case_metrics.csv`: per-case local proxy Dice, HD95, components, and volume ratio.
- `summary_metrics.csv`: aggregate case metric table.
- `center_summary_metrics.csv`: per-center subgroup metrics for available safe-case centers.
- `anatomy_prior_adapter_audit.md`: local CineMA license/provenance/adapter sanity.
- `label_export_qc.md`: compact-label local proxy and non-export caveat.
- `failure_interpretation.md`: route decision, caveats, and missing evidence.
- `command_transcript.md`: command, exit status, environment, and elapsed time.
- `motion_or_warp_summary.csv`: aggregate motion/warp diagnostic table.
- Source script: `scripts/evaluation/cine_motion_hardmode_20260703.py`
