# Manifest 20260704 Cine Temporal Motion Resume

task: `prompts/tasks/20260704_cine_temporal_motion_resume.md`
result: `results/20260704_cine_temporal_motion_resume/result.md`
review: `results/20260704_cine_temporal_motion_resume/review.md`

## Required Artifacts

| path | purpose |
| --- | --- |
| `result.md` | executor summary, commands, changed files, final decision |
| `reference_frame_policy.md` | frame0/ED reference policy and non-reference usage boundary |
| `cinema_adapter_status.md` | CineMA asset, label, preprocessing, and current-env blocker evidence |
| `registration_option_matrix.md` | ranked registration/warping option matrix and post-run comparator outcome |
| `temporal_dictionary_contract.md` | principle-level Cine temporal dictionary contract |
| `temporal_evidence.md` | non-reference temporal evidence comparison and decision rationale |
| `motion_or_warp_sanity.csv` | required-name CSV for current SimpleITK fallback sanity summary |
| `metrics_summary.md` | local diagnostic metric summary |
| `label_export_qc.md` | compact label/export QC caveats |
| `review.md` | read-only auditor review and gate decisions |

## Supporting Artifacts

| path | purpose |
| --- | --- |
| `simpleitk_demons_case_metrics.csv` | per-case/per-class SimpleITK fallback diagnostic metrics |
| `simpleitk_demons_summary.csv` | per-class SimpleITK fallback summary |
| `simpleitk_demons_command.json` | command parameters and SimpleITK version |

## Code Artifact

| path | purpose |
| --- | --- |
| `scripts/evaluation/cine_temporal_motion_resume_20260704.py` | narrow Cine-only diagnostic helper for SimpleITK fallback registration probe |

No validation package, upload-ready package, checkpoint, heavy prediction export, git commit, or git push was produced.
