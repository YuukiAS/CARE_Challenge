# M10 Follow-up Controller Result

Task key: `20260714_srr_v3_m10_continuation_reconciliation`

Current state: `NEEDS_REVISION_RETURN_TO_CINE_FIDELITY_WAVE`

This controller has initialized the M10 follow-up packet under the new canonical follow-up contract. The old M10 controller packet is inherited evidence only. No runtime role has written `review.md`, pushed, packaged/uploaded validation, claimed hosted metrics, promoted a route, made a scientific stop decision, or started M11.

Wave order is fixed and serial:

| Wave | Executor | State |
|---|---|---|
| F1 | `m10_followup_wave2_reconciliation_executor` | `READY_FOR_CONTROLLER_MERGE_ACCEPTED` |
| F2 | `m10_followup_cine_fidelity_executor` | `READY_FOR_CONTROLLER_MERGE_ACCEPTED` |
| F3 | `m10_followup_cine_runtime_executor` | `NEEDS_REVISION_RETURN_TO_CINE_FIDELITY_WAVE` |

Wave F1 preflight job `58921369`, serial checkpoint replay/control jobs `58921373`-`58921379`, and afterany finalizer `58921380` completed `0:0` on `htzhulab`. Wave F1 produced completion token `M10_FOLLOWUP_WAVE2_RECONCILIATION_READY_FOR_CONTROLLER_MERGE` and validator status `PASS`.

Wave F2 produced completion token `M10_FOLLOWUP_CINE_FIDELITY_READY_FOR_CONTROLLER_MERGE`, validator status `PASS`, and freeze hash `6439a7da9710cf41566ce2ab8a931f837dc1fa7915003b9ecdfede1066741e68`.

Wave F3 frozen-runtime execution reached terminal accounting. Preflight,
adapter, random-init control, registration, and finalizers completed, but the
conditional temporal dictionary did not produce required terminal evidence.

Temporal job `58932628` failed at startup because the temporal runtime root did
not contain upstream summaries; it is recorded with zero credit. Replacement
temporal job `58997393` started on `htzhulab` and ran until Slurm `TIMEOUT` at
`08:00:20`, but it did not write `summary.json`, `training_log.csv`,
`validation_events.csv`, `temporal_slot_usage.csv`, or `checkpoint_final.pt`.
The only temporal checkpoint artifact reports `step=6000`, below the required
`20000` optimizer steps. The replacement finalizer `58997394` completed and the
F3 executor completion token is
`M10_FOLLOWUP_CINE_RUNTIME_NEEDS_REVISION_RETURN_TO_CINE_FIDELITY_WAVE`.

No further F3 hot-patch retry was submitted because F3 write scope is limited
to the runtime result directory and forbids modifying implementation, scripts,
configs, or jobs. Any implementation/job-wrapper fix must return to the
authorized Cine fidelity/revision path rather than being patched inside F3.
The frozen temporal job wrapper calls `run_cine_temporal_model_m10.py`, while
the F3 executor plan and freeze receipt bind
`run_cine_temporal_m10_followup.py`; correcting this entrypoint behavior is
therefore a Cine fidelity revision item.

This packet is not reviewable as a completed M10 runtime packet.

Mapper/finalizer status:

- Mapper final ran against the current F1/F2/F3 evidence and updated root
  `wiki/` plus `wiki/history/M10/` as `candidate_unreviewed`.
- `wiki/current_state.yaml` remains on M09.
- FINALIZER_B validators passed for executor plan, handoff policy,
  architecture wiki, generated diagrams, F1/F2 validators, F2 unit tests, JSON
  sanity, and `git diff --check`.
- AI Research Toolkit `smoke` failed because `d2` is unavailable in the current
  environment; this is recorded in `wiki/toolkit_healthcheck.json` and
  `mapper_report_final.md`.
