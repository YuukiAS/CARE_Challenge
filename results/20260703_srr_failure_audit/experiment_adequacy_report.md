# Experiment Adequacy Report

task: `prompts/tasks/20260703_srr_failure_audit.md`
audited_packet: `results/20260703_myops_srr_propose_refine/`

## Decision

experiment_adequacy_decision: FAIL
scientific_resolution_status: SCIENTIFIC_UNDERTRAINED

The prior PropRef packet is not an adequate formal training experiment for a route-negative conclusion. It has real artifacts and fold0 metrics, but the training evidence fails the CARE adequacy gate: the runs used `max_steps=120`, exported `checkpoint_best` from `best_step=1`, did not record post-warmup validation, logged only three non-validation training rows after the initial row, and reported train-loop wall time of only `6.02`, `6.05`, and `29.66` seconds.

## Evidence Table

| variant | max_steps | logged steps | best_step | train_loop_seconds | validation evidence | loss trend | adequacy finding |
| --- | ---: | --- | ---: | ---: | --- | --- | --- |
| `srr_propref_shared_dual_dict` | 120 | `1, 50, 100` plus blank step-1 validation row | 1 | 6.05 | step 1 only; `val_every=300` exceeds `max_steps` | `2.713 -> 4.196` | FAIL |
| `srr_propref_scar_precision` | 120 | `1, 50, 100` plus blank step-1 validation row | 1 | 6.02 | step 1 only; `val_every=300` exceeds `max_steps` | `2.968 -> 4.280` | FAIL |
| `srr_propref_no_proto_cascade` | 120 | `1, 50, 100` plus blank step-1 validation row | 1 | 29.66 | step 1 only; `val_every=300` exceeds `max_steps` | `2.586 -> 3.797` | FAIL |

## Gate Findings

- `actual_steps`: evidence not found as an explicit `summary.json` key. It can be inferred that the loop intended `range(1, max_steps + 1)`, but the artifact does not record a completed-step counter.
- `optimizer_steps`: evidence not found as an explicit artifact field.
- `validation_events`: evidence not found as an explicit artifact field; the only logged validation row is at step 1.
- `loss_decrease`: not supported. Logged loss increases from first to last logged training row in all three variants.
- `train_loop_seconds`: present but far below a minimum effective formal training budget.
- `one-batch or one-case overfit sanity`: evidence not found.
- `same-split baseline`: present in `metrics_summary.md`, but inadequate training prevents route-negative use.
- `prediction sanity`: present as metrics/QC, but dominated by near-zero Dice and heavy component/remote-FP burden.
- `proposal/refinement sanity`: partial. Proposal metrics exist, but only at a fixed threshold and without PR/threshold-sweep evidence.
- `logs/provenance`: partial. Slurm accounting and configs exist, but configured tee logs are zero bytes.

## Evidence Index

- `prompts/tasks/20260703_srr_failure_audit.md:68-74` defines the adequacy audit questions.
- `prompts/EXPERIMENT_ADEQUACY_GATE.md:33-50` requires train-loop seconds, steps, validation events, loss decrease, prediction sanity, proposal sanity, provenance, and same-split baseline.
- `prompts/CARE_OVERLAY_GATES.md:74-98` rejects very short runs and requires explicit training, prediction, proposal, log, and same-split evidence before route-negative conclusions.
- `results/20260703_myops_srr_propose_refine/result.md:21-25` reports Slurm elapsed and `train_loop_seconds`.
- `results/20260703_myops_srr_propose_refine/training_schedule.md:22-26` states the formal runs used `max_steps=120`, logs every 50 steps, validates every 300 steps, and lack logged low-LR rows.
- `results/20260703_myops_srr_propose_refine/variants/*/summary.json` records `best_step: 1`, `max_steps: 120`, and `elapsed_seconds`, but not explicit `actual_steps`, `optimizer_steps`, or `validation_events`.
- `results/20260703_myops_srr_propose_refine/variants/*/training_log.csv` records rows at step 1, step 50, and step 100 plus a step-1 validation row.
- `scripts/training/run_srr_propref_myops_fold0.py:519-537` validates at step 1 or every `val_every` and saves `checkpoint_best` when validation improves.
- `scripts/training/run_srr_propref_myops_fold0.py:592-593` sets `log_every=50` and `val_every=300` defaults.
