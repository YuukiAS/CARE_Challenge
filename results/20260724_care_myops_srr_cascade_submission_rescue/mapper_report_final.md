# SCR-R1 RC1 Mapper Final Report

review_token: `NOT_REVIEWED_NOT_REQUIRED`

## Decision

`PASS_MAPPER_FINAL`: CARE-SRR-Cascade SCR-R1 runtime closure is now implemented and terminally evaluated in the current main worktree. The scientific outcome is baseline fallback for both custom pathologies, not a custom package candidate.

## Runtime Evidence

- Formal W3 terminal accounting: `results/20260724_care_myops_srr_cascade_submission_rescue/runtime_closure_repair_rc1/formal_terminal_accounting_v2.json` -> `PASS_TERMINAL_TRAINING_READY_FOR_AGGREGATION`.
- W4 aggregation: `results/20260724_care_myops_srr_cascade_submission_rescue/runtime_closure_repair_rc1/w4_aggregation_status_v2.json` -> `PASS_READY_FOR_STRICT_VALIDATOR`.
- Strict validator: `results/20260724_care_myops_srr_cascade_submission_rescue/strict_validator_report_v2.json` -> `PASS`.
- Known-bad terminal report: `results/20260724_care_myops_srr_cascade_submission_rescue/real_known_bad_report_terminal_v2.json` -> `PASS` across 22 fixtures.
- W4 Slurm jobs: evaluator `60576153 COMPLETED 0:0`; afterany finalizer `60576158 COMPLETED 0:0`.

## Component Mapping

- Anchor runtime: `src/care_myocardium/srr_production/anchor_runtime.py`; all-220 OOF anchor cache and roundtrip evidence are recorded in `anchor_cache_manifest_v2.csv`, `anchor_cache_roundtrip_v2.csv`, and `anchor_cache_hashes_v2.json`.
- Source cache: `jobs/care_mm/precompute_care_srr_cascade_source_cache.sh` and `run_care_srr_cascade_rc2_preflight.py`; all-220/880-field parity is recorded in `source_cache_manifest_v2.csv`, `source_cache_parity_v2.csv`, and `source_cache_hashes_v2.json`.
- Model/loss: `src/care_myocardium/models/care_srr_cascade_rescue.py` and `src/care_myocardium/losses/care_srr_cascade_rescue_losses.py`; independent scar/edema trunks and bounded pathology-channel correction are covered by runtime RC1 tests and known-bad fixtures.
- Prototype bank: `src/care_myocardium/srr_production/case_prototypes.py`; W4 used `prototype_bank_source=fold0_train_only` with `prototype_bank_record_count=176` for both pathologies.
- Formal trainer: `src/care_myocardium/training/care_srr_cascade_trainer.py` and `scripts/training/run_care_srr_cascade_formal.py`; eight variant summaries reached optimizer step 6250 with five validation events.
- Evaluation/selection: `scripts/evaluation/evaluate_care_srr_cascade.py`, `scripts/evaluation/select_care_srr_cascade.py`, and `scripts/evaluation/aggregate_care_srr_cascade_w4.py`; six calibration candidates only, audit not used for selection, exact-HD gate enforced.

## Final Scientific State

- Scar: `FALLBACK_TO_NNUNET`, selected calibration evidence candidate `control_two_seed_probability_mean_derived_bounded_channel_correction`, audit gate failed on `exact_HD_delta_max`.
- Edema: `FALLBACK_TO_NNUNET`, selected calibration evidence candidate `control_seed20260724`, audit gate failed on `exact_HD_delta_max`.
- W5 package/Docker dry-run: skipped because both pathologies fell back to nnU-Net; no upload or push was performed.

## Wiki And Entrypoint Delta

`wiki/README.md`, `wiki/current_state.yaml`, `prompts/routes/handoffs/CURRENT.md`, and `configs/srr_production/entrypoints.yaml` must now state terminal runtime closure rather than repair-ready/formal-not-started. This report is paired with `architecture_delta_final.md`.
