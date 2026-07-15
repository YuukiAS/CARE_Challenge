# M10 Follow-up Cine F3 Validator

Status: `NEEDS_REVISION_RETURN_TO_CINE_FIDELITY_WAVE`

Error count: `1`

Blocking evidence issue:

- `temporal_summary_missing`: conditional temporal dictionary formal execution
  did not produce terminal `summary.json`, `training_log.csv`,
  `validation_events.csv`, `temporal_slot_usage.csv`, or
  `checkpoint_final.pt`.
- `temporal_entrypoint_scope_mismatch`: frozen F3 temporal job wrapper calls
  `scripts/training/run_cine_temporal_model_m10.py`, while the F3 plan and
  freeze receipt bind `scripts/training/run_cine_temporal_m10_followup.py`.
  Correcting the job/script behavior requires returning to the Cine fidelity
  wave rather than hot-patching F3.

Terminal accounting:

- Original temporal job `58932628`: `FAILED`, `1:0`, `00:00:07`,
  zero training credit.
- Replacement temporal job `58997393`: `TIMEOUT`, `0:0`, `08:00:20`,
  batch step `CANCELLED 0:15`, zero training credit.
- Replacement finalizer `58997394`: `COMPLETED`, `0:0`, `00:00:02`.

Checkpoint inspection:

- `checkpoint_best.pt` exists, but its metadata reports `step=6000`, below
  the required `20000` optimizer steps.

Validator decision:

`M10_FOLLOWUP_CINE_RUNTIME_NEEDS_REVISION_RETURN_TO_CINE_FIDELITY_WAVE`
