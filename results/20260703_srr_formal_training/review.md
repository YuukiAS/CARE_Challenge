# Review 20260703 SRR Formal Training

audit_decision: `AUDITED_DIAGNOSTIC_PUBLISH`
claim_audit_decision: `SUPPORTED_WITH_CAVEATS`
self_assessed_status: `EXECUTED_UNAUDITED`
experiment_adequacy_decision: `FAIL`
route_promotion_decision: `NOT_EVALUABLE`
route_negative_decision: `STOP_NOT_SUPPORTED`
scientific_resolution_status: `SCIENTIFIC_UNDERTRAINED`
diagnostic_publication_decision: `PUBLISH_REVIEWED_DIAGNOSTIC_PACKET`
recommended_next_state: `AUDITED_DIAGNOSTIC_PUBLISH`
role: separate read-only auditor
audited_task: `prompts/tasks/20260703_srr_formal_training.md`
audited_result: `results/20260703_srr_formal_training/result.md`

## Audit Scope

I audited only the `20260703_srr_formal_training` task output package after formal Slurm array job `57655472` was recorded as completed. I did not edit code, repair artifacts, rerun training, rerun Slurm, query live `sacct`, package validation, upload, expand folds, change labels/evaluators/splits, commit, push, or use network access. I wrote only this `review.md`.

Recorded Slurm completion is supported by the executor packet, not by a fresh scheduler query: `job_status.md` records all three array tasks as `COMPLETED` with exit code `0:0`, and `command_transcript.md` records `sacct -j 57655472` exit `0` with child states `COMPLETED 0:0`. The three Slurm stdout/stderr log files are present but zero bytes, so the usable provenance is the named transcript plus per-variant JSON/CSV artifacts.

## Claim Ledger

| claim | audit status | finding |
| --- | --- | --- |
| `self_assessed_status: EXECUTED_UNAUDITED` | SUPPORTED | The executor wrote the required result package and correctly stopped before audit. No prior `review.md` existed when this audit began. |
| Slurm job `57655472` completed | SUPPORTED_FROM_RECORDED_EVIDENCE | `job_status.md` and `command_transcript.md` record all three variants as `COMPLETED:0:0`. I did not rerun `sacct`. |
| All variants reached 1800 optimizer steps | SUPPORTED | Each `summary.json` records `optimizer_steps=1800`, `actual_optimizer_steps=1800`, `max_steps=1800`, `stop_reason=max_steps`, and `best_step=1800`. |
| Best/final checkpoint policy completed | SUPPORTED | `checkpoint_policy.md` and per-variant summaries show `checkpoint_best.pt` and `checkpoint_final.pt`; best and final both correspond to step 1800 for all variants. |
| One-batch overfit sanity passed | SUPPORTED | `one_batch_overfit.md` reports 40-step overfit loss decreases for all variants: 1.3965, 1.2853, and 1.1212. |
| Post-warmup validation occurred | SUPPORTED | Each variant has 9 validation events through step 1800; final validation at step 1800 is `eligible_for_best=True`. |
| Prediction sanity exists and is non-empty | SUPPORTED_WITH_SCOPE_CAVEAT | `prediction_sanity.md` reports 44 cases per checkpoint/decode mode, nonzero foreground/pathology rates, and `empty_prediction_rate=0.0`. These are compact-label local predictions only. |
| Label/export QC passed | SUPPORTED_WITH_SCOPE_CAVEAT | `label_export_qc.md` supports compact-label local QC only: observed compact labels are valid, but raw-label export and validation package generation were not authorized and were not performed. |
| Same-split nnU-Net references exist | SUPPORTED | The referenced nnU-Net fold0 summary contains scar class-5 Dice `0.5602` and edema class-4 Dice `0.3944`; the unified fold0 class-4 all-case sanity Dice is `0.7798`. |
| SRR metrics are poor vs nnU-Net | SUPPORTED_DIAGNOSTIC_ONLY | Best local scar Dice is at most `0.1665` argmax / `0.1524` pathology-aware for shared-dual-dict and lower for other variants. Best edema GT-positive Dice is at most `0.0868`. Component/HD and proposal metrics show high FP burden. |
| `experiment_adequacy_decision: FAIL` | SUPPORTED | The task explicitly requires `min_train_loop_seconds=1800`. The completed summaries record only 138.168, 138.574, and 151.525 seconds. Meeting 1800 optimizer steps and `best_step=1800` does not satisfy the separate time gate. |
| `route_promotion_decision: NOT_EVALUABLE` | SUPPORTED | Metrics are far below the same-split nnU-Net references and, more importantly, the formal adequacy gate fails. This cannot support route promotion, fold expansion, validation packaging/upload, or hosted metric claims. |
| `route_negative_decision: STOP_NOT_SUPPORTED` | SUPPORTED | The handoff and CARE gates forbid `STOP_NO_PROPREF_SIGNAL` unless experiment adequacy passes and the auditor supports the route-negative conclusion. Adequacy fails on the explicit time gate. |
| `scientific_resolution_status: SCIENTIFIC_UNDERTRAINED` | SUPPORTED | The run is not smoke-only because checkpoints, predictions, validation events, and metrics exist, but it is under the task's formal training budget. This is an undertrained diagnostic result, not a scientific stop. |

## Evidence Coverage

Required top-level artifacts are present: `result.md`, `MANIFEST.md`, `job_status.md`, `experiment_adequacy_report.md`, `one_batch_overfit.md`, `checkpoint_policy.md`, `prediction_sanity.md`, `proposal_pr_sweep.csv`, `metrics_summary.md`, `subgroup_metrics.csv`, `component_hd_by_case.csv`, `roi_coverage.csv`, `label_export_qc.md`, `failure_interpretation.md`, and `command_transcript.md`.

Per-variant evidence is present for all three variants: `summary.json`, `training_log.csv`, `validation_events.csv`, checkpoint-specific prediction sanity, proposal PR sweeps, subgroup metrics, component/HD-by-case metrics, ROI coverage, and config files. Aggregate row counts are consistent with the executor summary: 5280 proposal PR rows, 216 subgroup rows, 1056 component/HD rows, and 1056 ROI coverage rows.

The main caveat is provenance logging: the Slurm log files are zero bytes. The task gate allows transcript substitution only when the report names it; this package does name `command_transcript.md` and per-variant summaries as replacement evidence. That is adequate for auditing completion state and artifacts, but it does not repair the failed training-duration gate.

## Gate Decisions

experiment_adequacy_decision: `FAIL`

Reason: all variants satisfy optimizer-step, validation-event, loss-decrease, one-batch-overfit, checkpoint, prediction, PR-sweep, and compact-label local QC evidence, but all fail the explicit `min_train_loop_seconds=1800` requirement by a wide margin.

route_promotion_decision: `NOT_EVALUABLE`

Reason: adequacy failure blocks route promotion. The available diagnostic metrics are also substantially below nnU-Net fold0 references.

route_negative_decision: `STOP_NOT_SUPPORTED`

Reason: `STOP_NO_PROPREF_SIGNAL` is blocked because the route-negative gate requires adequacy PASS. The poor metrics may motivate a revision or strategic decision, but they cannot scientifically stop the PropRef route under this task's rules.

scientific_resolution_status: `SCIENTIFIC_UNDERTRAINED`

Reason: the run has real GPU artifacts and is not just a CPU smoke test, but the formal evidence budget is unmet.

diagnostic_publication_decision: `PUBLISH_REVIEWED_DIAGNOSTIC_PACKET`

Reason: a minimal reviewed diagnostic packet is useful for GPT planner/controller review. This is diagnostic publication only; no route promotion.

## Diagnostic Publication Scope

Supported for diagnostic publication, if a controller task with git authority chooses to publish: `result.md`, this `review.md`, `MANIFEST.md`, `job_status.md`, `experiment_adequacy_report.md`, `one_batch_overfit.md`, `checkpoint_policy.md`, `prediction_sanity.md`, `metrics_summary.md`, `label_export_qc.md`, and `failure_interpretation.md`. Compact aggregate CSVs may be published only if the controller judges them necessary and within the diagnostic scope.

Do not publish checkpoints, prediction directories, NIfTI outputs, full per-variant result trees, heavy logs, upload packages, hosted validation packages, credentials, `.env`-style files, or the full local evidence tree. This audit does not authorize commit or push because the audited execution task has `allow_git_commit: false` and `allow_git_push: false`.

## Audit Decision

The executor's controlled decisions are supported:

- `self_assessed_status: EXECUTED_UNAUDITED`
- `experiment_adequacy_decision: FAIL`
- `route_promotion_decision: NOT_EVALUABLE`
- `route_negative_decision: STOP_NOT_SUPPORTED`
- `scientific_resolution_status: SCIENTIFIC_UNDERTRAINED`

The key judgment is that 1800 optimizer steps and `best_step=1800` do not override the separate task requirement of at least 1800 train-loop seconds. The observed 138-152 second train loops correctly fail adequacy and block `STOP_NO_PROPREF_SIGNAL`.

## Blocked Actions

- route promotion remains blocked
- `STOP_NO_PROPREF_SIGNAL` / `SCIENTIFIC_STOP_SUPPORTED` remains blocked
- validation packaging remains blocked
- validation upload and external upload remain blocked
- fold expansion remains blocked
- hosted metric claims remain blocked
- label/evaluator/fold split changes remain blocked
- next-stage training remains blocked unless a new GPT-authored task explicitly authorizes it
- publishing checkpoints, predictions, NIfTI outputs, heavy logs, full result trees, upload packages, credentials, or environment dumps remains blocked

## Controller Recommendation

For this MyoPS SRR PropRef route, the controller should treat the task as operationally audited but scientifically undertrained: `AUDITED_DIAGNOSTIC_PUBLISH`, no route promotion, no route-negative stop, and no automatic continuation.

The next decision belongs to the user-supervised GPT strategic planner. A bounded follow-up could either revise the adequacy policy with an explicit rationale for step-based adequacy despite very short loop time, or authorize a true time-budgeted formal training run. If the broader CARE plan needs Cine work, handle Cine in a separate GPT-authored task; this MyoPS SRR audit does not authorize Cine fold expansion, validation packaging, one-zip submission work, or next-stage Cine training.
