# M10 Follow-up Independent Runtime Review

Task key: `20260714_srr_v3_m10_continuation_reconciliation`

Reviewer role: independent read-only CARE Codex reviewer.

Decision: `M10_FOLLOWUP_AUDITED_NEEDS_REVISION_RETURN_TO_CINE_FIDELITY_WAVE`

This corresponds to the controller-requested review state
`NEEDS_REVISION_RETURN_TO_CINE_FIDELITY_WAVE_REVIEW` and the F3 runtime token
`M10_FOLLOWUP_CINE_RUNTIME_NEEDS_REVISION_RETURN_TO_CINE_FIDELITY_WAVE`.

This is not audited-go. The follow-up packet has terminal accounting, but it
does not satisfy the F3 temporal runtime evidence gate and is not reviewable as
a completed M10 follow-up packet.

## Contract Sources Reviewed

- `AGENTS.md`
- `prompts/shared/REVIEWER_PROMPTS.md`, section `M10 follow-up reviewer: contract reconciliation, Wave 2 evidence completion, and Cine fidelity repair`
- `prompts/shared/EXECUTOR_PROMPTS.md`, section `M10 follow-up executor/controller: contract reconciliation, Wave 2 evidence completion, and Cine fidelity repair`
- `prompts/tasks/20260714_srr_v3_m10_continuation_reconciliation_executor_plan.yaml`
- `results/20260714_srr_v3_m10_continuation_reconciliation/`
- `results/20260714_srr_v3_m10_followup_wave2_reconciliation/`
- `results/20260714_srr_v3_m10_followup_cine_fidelity/`
- `results/20260714_srr_v3_m10_followup_cine_runtime/`

## Evidence Reviewed

- Controller packet: `completion_check.md`, `controller_report.md`,
  `result.md`, `review_request.md`, `finalizer_state.json`, `MANIFEST.md`
- F1 packet validator and result files
- F2 packet validator, freeze receipt, contract files, unit/self-test reports
- F3 packet: `result.md`, `validator_report.md`,
  `temporal_timeout_analysis.md`, `terminal_accounting.csv`,
  `temporal_training_budget_ledger.csv`, `finalizer_state.json`,
  `frozen_hash_validation.json`, and job wrapper
  `jobs/src/run_srr_v3_m10_followup_cine_temporal.sh`
- Live Slurm terminal accounting via `sacct` for follow-up F3 jobs.

## Findings

1. F1 and F2 are locally acceptable as inherited follow-up inputs, but they do
   not complete the milestone without F3.

   The controller packet records F1 as
   `M10_FOLLOWUP_WAVE2_RECONCILIATION_READY_FOR_CONTROLLER_MERGE` and F2 as
   `M10_FOLLOWUP_CINE_FIDELITY_READY_FOR_CONTROLLER_MERGE`, with validator
   pass reports and frozen hashes. I did not identify a blocker in those
   packet-level acceptance states.

2. F3 temporal runtime evidence is missing and undertrained.

   F3 terminal accounting records:

   | Job | Role | State | Review interpretation |
   | ---: | --- | --- | --- |
   | `58932590` | preflight | `COMPLETED 0:0` | preflight passed |
   | `58932609` | adapter | `COMPLETED 0:0` | terminal adapter evidence present |
   | `58932626` | random-init control | `COMPLETED 0:0` | terminal control evidence present |
   | `58932627` | registration | `COMPLETED 0:0` | terminal registration evidence present |
   | `58932628` | temporal attempt | `FAILED 1:0` | zero credit startup failure |
   | `58997393` | temporal retry | `TIMEOUT 0:0` | zero credit; no terminal temporal evidence |
   | `58997394` | retry finalizer | `COMPLETED 0:0` | terminal accounting preserved the gap |

   The temporal retry ran `08:00:20` but did not write `summary.json`,
   `training_log.csv`, `validation_events.csv`, `temporal_slot_usage.csv`, or
   `checkpoint_final.pt`. The only inspected temporal checkpoint reports
   `step=6000`, below the required `20000` optimizer steps. The packet
   therefore assigns zero temporal training credit.

3. The F3 job wrapper and frozen plan point to different temporal entrypoints.

   `jobs/src/run_srr_v3_m10_followup_cine_temporal.sh` calls
   `scripts/training/run_cine_temporal_model_m10.py`, while the F3 executor
   plan and frozen evidence bind
   `scripts/training/run_cine_temporal_m10_followup.py`. Correcting this is
   outside F3 write scope because F3 is limited to runtime submission,
   monitoring, and aggregation. This supports the controller's return-to-Cine-
   fidelity-wave state rather than another F3 hot patch.

4. Terminal accounting exists; the decision is not `NEEDS_MONITOR`.

   I independently checked Slurm accounting for jobs `58932590`, `58932609`,
   `58932626`, `58932627`, `58932628`, `58932629`, `58997393`, and
   `58997394`. They are terminal, with `58997393` in `TIMEOUT` and the finalizer
   completed. The blocker is missing/insufficient temporal evidence after
   completion, not pending queue state.

5. The controller correctly avoids route decisions.

   The controller report keeps `route_promotion_decision: NOT_REVIEWED`,
   `route_negative_decision: NOT_REVIEWED`, and
   `scientific_resolution_status: AWAITING_REVIEW`. No validation packaging,
   hosted metric claim, route promotion, scientific stop, push, or M11 start is
   authorized from this packet.

## Controlled Decision

`M10_FOLLOWUP_AUDITED_NEEDS_REVISION_RETURN_TO_CINE_FIDELITY_WAVE`

Rationale: F3 reached terminal accounting but lacks required temporal runtime
outputs and minimum training evidence, and the temporal job-wrapper/entrypoint
mismatch requires a Cine fidelity revision or planner-authorized follow-up.
This packet cannot receive audited-go or route-level scientific closure.
