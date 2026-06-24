# Artifact Manifest 20260621 SRR Spec

task: `prompts/tasks/20260621_srr_spec.md`
result: `results/20260621_srr_spec/result.md`
review: `results/20260621_srr_spec/review.md`

## Required Artifacts

- `results/20260621_srr_spec/Result4.txt`: local `pdftotext` extraction of `docs/notes/deep_research/Result4.pdf`.
- `results/20260621_srr_spec/architecture_contract.md`: frozen human-readable SRR-MyoPS-Lite architecture contract.
- `results/20260621_srr_spec/architecture_contract.yaml`: machine-readable contract and gate.
- `results/20260621_srr_spec/test_summary.md`: command and test evidence.
- `results/20260621_srr_spec/result.md`: execution report and final gate.

## Additional Smoke Artifacts

- `results/20260621_srr_spec/one_batch_smoke.json`: synthetic one-batch forward/backward output.
- `results/20260621_srr_spec/smoke_report.md`: short report generated from smoke JSON.

## First-Party Code Added

- `src/care_myocardium/data/case_metadata.py`: CARE MyoPS modality metadata and label mapping helpers.
- `src/care_myocardium/data/myops_dataset.py`: minimal Dataset501 preprocessed loader.
- `src/care_myocardium/models/srr_blocks.py`: shared/private expert bank, router, and strict missing-modality fusion.
- `src/care_myocardium/models/pathology_heads.py`: anatomy/scar/edema heads with soft anatomy prior.
- `src/care_myocardium/models/srr_myops.py`: `SRRMyoPSLite` model.
- `src/care_myocardium/losses/srr_losses.py`: T2-masked edema loss, scar loss, anatomy loss, retrieval regularization.
- `src/care_myocardium/configs/srr_myops_minimal.yaml`: minimal configuration.
- `src/care_myocardium/tests/test_srr_shapes.py`: shape and gate tests.
- `src/care_myocardium/tests/test_srr_missingness.py`: strict missing-modality tests.
- `src/care_myocardium/tests/test_srr_losses.py`: loss/gradient/label mapping tests.

## Entrypoints

- `scripts/training/run_srr_myops.py`: spec-safe synthetic smoke entrypoint; fold0 training is gated by the next task.
- `scripts/evaluation/report_srr_myops.py`: report helper for smoke artifacts.
- `jobs/src/run_srr_myops_fold0.sh`: gated fold0 job wrapper, `06:00:00`, `htzhulab`, script-level log style. It currently runs only the smoke command until the fold0 task replaces/extends it.

## Notes

- No validation submission or upload-ready package was created.
- No `third_party/MyoPS-Net`, `third_party/U-MyoPS`, or old baseline defaults were modified.
- The existing coordinator files under `results/20260621_srr_goal/coordinator/` were preserved.
