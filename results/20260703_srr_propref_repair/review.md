# Review 20260703 SRR PropRef Repair

audit_decision: AUDITED_DIAGNOSTIC_PUBLISH
claim_audit_decision: SUPPORTED_WITH_CAVEATS
experiment_adequacy_decision: FAIL
route_promotion_decision: NOT_EVALUABLE
route_negative_decision: STOP_NOT_SUPPORTED
scientific_resolution_status: SCIENTIFIC_UNDERTRAINED
diagnostic_publication_decision: PUBLISH_REVIEWED_DIAGNOSTIC_PACKET
recommended_next_state: AUDITED_DIAGNOSTIC_PUBLISH
role: separate read-only auditor
audited_task: `prompts/tasks/20260703_srr_propref_repair.md`
audited_result: `results/20260703_srr_propref_repair/result.md`

## Audit Scope

I audited only `results/20260703_srr_propref_repair/` and the task-scoped code paths named by the user: `scripts/training/run_srr_propref_myops_fold0.py`, `jobs/src/run_srr_propref_myops_fold0.sh`, and `scripts/evaluation/aggregate_srr_propref_repair_20260703.py`. I did not edit code, repair artifacts, run training, package validation, upload, expand folds, commit, push, or use network access. I wrote only this `review.md`.

An extra untracked file, `scripts/evaluation/run_nnunet_oof_component_20260703.py`, is present in the worktree but is not referenced by this task packet and was not audited for this decision.

## Claim Ledger

| claim | status | audit finding |
| --- | --- | --- |
| `experiment_adequacy_decision: FAIL` | SUPPORTED | The task requires at least 1500 optimizer steps, 1800 train-loop seconds, overfit sanity, prediction sanity, loss decrease, and post-warmup validation (`prompts/tasks/20260703_srr_propref_repair.md:24-27`). The result reports 0 formal optimizer steps, 0.0 train-loop seconds, 0 validation events for the only touched variant, and evidence-not-found for the other two variants (`results/20260703_srr_propref_repair/result.md:20-24`; `experiment_adequacy_report.md:6-10`). |
| Formal adequate training completed | NOT SUPPORTED | The transcript records only syntax checks, an interrupted CPU smoke command with exit status 130, an interrupted forward/decode check with exit status 130, and no Slurm formal retry (`command_transcript.md:3-19`). This is not an adequate fold0 training/evaluation run. |
| One-batch overfit sanity | PARTIAL / SMOKE_ONLY | The one available overfit artifact shows a 2-step local run with positive loss decrease (`one_batch_overfit.md:3-7`; `variants/srr_propref_shared_dual_dict/one_batch_overfit.json:3-12`), but the command used `--overfit-steps 2` and `--min-overfit-loss-decrease -999` in an interrupted CPU smoke (`command_transcript.md:8-10`). It is useful diagnostic evidence, not a formal adequacy pass. |
| Prototype update sanity exists | PARTIAL / SMOKE_ONLY | The shared-dual-dict smoke generated gradient/update rows for prototype parameters, including nonzero scar dictionary updates and mixed edema-memory updates (`variants/srr_propref_shared_dual_dict/prototype_update_sanity.csv`). No formal-run `prototype_update_sanity_formal.csv` exists. |
| Prediction/decode sanity completed | NOT SUPPORTED | The top-level prediction sanity report says evidence not found and no raw-label validation export was generated (`prediction_sanity.md:3-7`). A partial smoke prediction NIfTI exists under the variant tree, but no summary/metric CSV ties it to completed formal evaluation. |
| Proposal PR sweep completed | NOT SUPPORTED | `proposal_pr_sweep.csv` contains only evidence-not-found placeholder rows for all three variants, so proposal recall/precision and lesion-wise recall were not measured for a formal run. |
| Same-split baseline reference present | PARTIAL | The metrics summary records nnU-Net same-split reference values for scar and edema (`metrics_summary.md:3-4`), but no SRR formal metric rows exist for comparison (`metrics_summary.md:6-8`). |
| `route_promotion_decision: NOT_EVALUABLE` | SUPPORTED | There are no completed SRR metrics, prediction sanity, proposal PR metrics, or label/export QC sufficient to compare against the same-split baseline. |
| `route_negative_decision: STOP_NOT_SUPPORTED` | SUPPORTED | Handoff and CARE gates forbid `STOP_NO_PROPREF_SIGNAL` without experiment adequacy and auditor support (`prompts/EXPERIMENT_ADEQUACY_GATE.md:56-73`; `prompts/CARE_OVERLAY_GATES.md:79-98`). Adequacy failed, so a route-negative stop is not supported. |
| `scientific_resolution_status: SCIENTIFIC_UNDERTRAINED` | SUPPORTED | The observed evidence is an interrupted smoke/partial run, not an adequate negative experiment. Under the state machine, short or weak runs should use `SCIENTIFIC_UNDERTRAINED` rather than scientific stop (`prompts/HANDOFF_STATE_MACHINE.md:69-76`). |
| No network/upload/fold expansion/validation packaging | SUPPORTED BY PACKET | The executor states none were performed (`result.md:14-17`; `failure_interpretation.md:7-9`), and the transcript records `network_used: false` and no formal retry launch (`command_transcript.md:15-19`). I did not independently run external checks. |

## Artifact Coverage

Required top-level report artifacts exist: `result.md`, `MANIFEST.md`, `experiment_adequacy_report.md`, `one_batch_overfit.md`, `checkpoint_policy.md`, `prediction_sanity.md`, `proposal_pr_sweep.csv`, `metrics_summary.md`, `subgroup_metrics.csv`, `component_hd_by_case.csv`, `roi_coverage.csv`, `label_export_qc.md`, `failure_interpretation.md`, and `command_transcript.md` (`MANIFEST.md:7-23`).

Most metric CSVs are placeholder evidence-not-found outputs, not completed formal metrics. The per-variant tree contains partial smoke binary artifacts: checkpoint files and one prediction NIfTI for `srr_propref_shared_dual_dict`. These are explicitly not approved for publication and should not be interpreted as formal checkpoints/predictions because the smoke command was interrupted and no completed `summary.json` or formal metric CSV exists.

The aggregate script correctly maps missing summaries to failed/undertrained decisions (`scripts/evaluation/aggregate_srr_propref_repair_20260703.py:58-77`, `112-139`), but it would overwrite `command_transcript.md` with only aggregate-command metadata if rerun (`scripts/evaluation/aggregate_srr_propref_repair_20260703.py:417-430`). The richer current transcript therefore should be preserved as reviewed report evidence; this caveat does not change the undertrained decision.

## Code Review Notes

The training runner implements the requested repair mechanisms at the code level:

- validation milestones after warmup/proposal/refinement/end plus periodic validation (`scripts/training/run_srr_propref_myops_fold0.py:86-95`);
- argmax and pathology-aware decode paths (`scripts/training/run_srr_propref_myops_fold0.py:255-319`);
- proposal threshold sweep with recall, precision, lesion-wise recall, components, and outside-myocardium FP ratio (`scripts/training/run_srr_propref_myops_fold0.py:329-377`);
- prediction sanity rows with compact labels, foreground/pathology rates, class volumes, and no-T2 edema voxels (`scripts/training/run_srr_propref_myops_fold0.py:411-447`);
- checkpoint-specific best/final prediction and metric exports (`scripts/training/run_srr_propref_myops_fold0.py:459-495`, `907-965`);
- optimizer/time/validation/loss summary fields (`scripts/training/run_srr_propref_myops_fold0.py:933-975`).

The Slurm entrypoint uses the `/users` CARE root, `htzhulab`, 7.5-hour budget, `gpu_access`, and the repair output root (`jobs/src/run_srr_propref_myops_fold0.sh:15-24`, `32-71`). It is consistent with the task's bounded retry design, but it was not launched as a formal retry in this executor turn (`command_transcript.md:19`).

## Gate Decisions

experiment_adequacy_decision: FAIL

route_promotion_decision: NOT_EVALUABLE

route_negative_decision: STOP_NOT_SUPPORTED

scientific_resolution_status: SCIENTIFIC_UNDERTRAINED

diagnostic_publication_decision: PUBLISH_REVIEWED_DIAGNOSTIC_PACKET

Diagnostic publication is supported only for the reviewed repair code and small reports needed by the GPT planner. This is diagnostic publication only; no route promotion.

## Audit Decision

The executor's core decisions are supported: the repair code is useful diagnostic work, but formal adequate fold0 training was not completed. The evidence supports `SCIENTIFIC_UNDERTRAINED`, not `STOP_NO_PROPREF_SIGNAL`, `SCIENTIFIC_STOP_SUPPORTED`, or route promotion.

## Blocked Actions

- validation packaging remains blocked
- validation upload remains blocked
- fold expansion remains blocked
- hosted metric claims remain blocked
- label/evaluator/fold split changes remain blocked
- next-stage training remains blocked unless a new explicit task authorizes it
- publishing checkpoints, predictions, NIfTI files, heavy logs, full result trees, upload packages, credentials, or environment dumps remains blocked
