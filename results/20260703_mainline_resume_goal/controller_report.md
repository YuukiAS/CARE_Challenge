# Controller Report: 20260703 Mainline Resume Goal

controller_task_id: 20260703_mainline_resume_goal
controller_task: `prompts/tasks/20260703_mainline_resume_goal.md`
controller_role: Codex execution controller
final_controller_state: AUDITED_DIAGNOSTIC_PUBLISH

diagnostic publication only; no route promotion

## Executive Summary

The authorized controller workflow has completed operationally. MyoPS remained
primary: SRR-ProposeRefine formal fold0 training was launched first as Slurm
array `57655472` on `htzhulab` using
`jobs/src/run_srr_propref_formal_myops_fold0.sh` with `MAX_STEPS=1800` and
`VAL_EVERY=300`. All three array tasks completed with exit code `0:0`.

The MyoPS packet was aggregated and independently audited. It is publishable as
a reviewed diagnostic packet, but the formal adequacy gate fails because all
variants trained for only about 138-152 train-loop seconds, below the explicit
`min_train_loop_seconds=1800` requirement. Therefore MyoPS is
`SCIENTIFIC_UNDERTRAINED`, not promotable, and not eligible for
`STOP_NO_PROPREF_SIGNAL`.

Cine was run only after MyoPS Slurm completion and audit. The Cine packet was
CPU-only diagnostic work with non-reference frame evidence. It was independently
audited as a local temporal proxy diagnostic packet with no hosted metric, no
validation packaging/upload, no fold expansion, and no route promotion.

## Subtasks

| role | task | session/evidence | result | review | decision |
| --- | --- | --- | --- | --- | --- |
| executor | `prompts/tasks/20260703_srr_formal_training.md` | Slurm array `57655472`; executor `019f28f4-9fec-7da3-9d7e-02230d4df19b`; aggregation executor `019f2905-4675-79f1-89f0-b75701ea5a4e` | `results/20260703_srr_formal_training/result.md` | `results/20260703_srr_formal_training/review.md` | `SCIENTIFIC_UNDERTRAINED`, diagnostic only |
| executor | `prompts/tasks/20260703_cine_temporal_resume.md` | executor `019f290f-cdeb-7a82-a258-b709ded31677`; CPU diagnostic command in result packet | `results/20260703_cine_temporal_resume/result.md` | `results/20260703_cine_temporal_resume/review.md` | `TEMPORAL_PROXY_SIGNAL_DIAGNOSTIC`, diagnostic only |
| auditor | Cine review | auditor `019f2916-404a-7e73-a690-04039c4f0cb8`; duplicate late auditor `019f2919-48ae-7ae0-b070-760ffa11a36c` was closed before writing | `results/20260703_cine_temporal_resume/result.md` | `results/20260703_cine_temporal_resume/review.md` | `AUDITED_DIAGNOSTIC_PUBLISH` |

## MyoPS Evidence

Verified Slurm accounting:

```text
57655472_0  COMPLETED  0:0  00:08:30
57655472_1  COMPLETED  0:0  00:07:47
57655472_2  COMPLETED  0:0  00:06:21
```

Executor/auditor evidence:

- all three variants reached `optimizer_steps=1800`;
- all three variants wrote `summary.json`, `training_log.csv`, checkpoints,
  checkpoint-specific predictions, prediction sanity, proposal PR sweeps,
  component/HD metrics, ROI coverage, and subgroup metrics;
- one-batch overfit sanity passed for all variants;
- same-split nnU-Net references were recorded: scar Dice `0.5602`, edema Dice
  `0.3944`;
- SRR metrics remained far below those references;
- adequacy still fails because `train_loop_seconds` is only `138.168`,
  `138.574`, and `151.525` against the required `1800`.

MyoPS audit decision:

- `audit_decision: AUDITED_DIAGNOSTIC_PUBLISH`
- `experiment_adequacy_decision: FAIL`
- `route_promotion_decision: NOT_EVALUABLE`
- `route_negative_decision: STOP_NOT_SUPPORTED`
- `scientific_resolution_status: SCIENTIFIC_UNDERTRAINED`
- `diagnostic_publication_decision: PUBLISH_REVIEWED_DIAGNOSTIC_PACKET`

## Cine Evidence

Cine executor command:

```bash
envs/env_CARE/bin/python scripts/evaluation/cine_motion_hardmode_20260703.py --output-dir results/20260703_cine_temporal_resume --task-key 20260703_cine_temporal_resume --controller-task-key 20260703_mainline_resume_goal
```

Executor/auditor evidence:

- `59` safe cases and `5` mismatch cases were reproduced;
- frame0/reference-only was used as a reference control, not as completion;
- non-reference frames entered both the optical-flow/feature-warp route and the
  descriptor temporal aggregation route;
- local reference-control myocardium/LV Dice: `0.5626` / `0.7709`;
- optical-flow/feature-warp myocardium/LV Dice delta: `+0.0406` / `+0.0454`;
- descriptor route deltas were near zero: `-0.0002` / `-0.0001`;
- hosted `myocardium_cinemyops`, validation packaging/upload, raw-label export
  QC, and learned pathology head evidence were not present and were not
  authorized.

Cine audit decision:

- `audit_decision: AUDITED_DIAGNOSTIC_PUBLISH`
- `route_decision_recommendation: TEMPORAL_PROXY_SIGNAL_DIAGNOSTIC`
- `experiment_adequacy_decision: PARTIAL`
- `route_promotion_decision: NO_PROMOTION`
- `route_negative_decision: STOP_NOT_SUPPORTED`
- `scientific_resolution_status: SCIENTIFIC_UNRESOLVED`
- `diagnostic_publication_decision: PUBLISH_REVIEWED_DIAGNOSTIC_PACKET`

The Cine script fallback enum was aligned after audit from the unexecuted
`STOP_NO_TEMPORAL_PROXY_GAIN` branch to the task-allowed
`STOP_CINE_NO_TEMPORAL_SIGNAL`; the executed positive diagnostic output is
unchanged. `python -m py_compile` passed after this change.

## Git Publication Scope

The controller task authorizes diagnostic commit and push, but the actual push
attempt was rejected by the execution environment's external-disclosure safety
review because the packet contains data-derived research artifacts and reports.
The local commit is prepared for human review. Diagnostic publication remains
for GPT planner review only. It excludes checkpoints, predictions, NIfTI
outputs, upload packages, full result trees, credentials, heavy logs, and
command transcripts with environment dumps.

Planned publication scope:

- controller report, execution plan, and manifest;
- reviewed MyoPS result/review and small decision packets;
- MyoPS aggregate metric CSV/Markdown needed to diagnose adequacy and variant
  behavior;
- each SRR variant's `summary.json` and `training_log.csv`;
- reviewed Cine result/review and small diagnostic metric files;
- `jobs/src/run_srr_propref_formal_myops_fold0.sh`;
- `scripts/evaluation/cine_motion_hardmode_20260703.py`.

## Blocked Actions

- validation upload
- validation packaging or upload-ready package generation
- fold expansion
- hosted metric claims
- label/evaluator/fold split changes
- old SRR-v2 tuning routes
- learned anchor-refine training
- route promotion
- route-negative scientific stop
- next-stage training without a new GPT-authored task

## Required Ending

controller_run_status: COMPLETE
operational_completion_status: COMPLETE
experiment_adequacy_decision: PARTIAL
route_promotion_decision: NO_PROMOTION
route_negative_decision: STOP_NOT_SUPPORTED
scientific_resolution_status: SCIENTIFIC_UNRESOLVED
diagnostic_publication_decision: PUBLISH_REVIEWED_DIAGNOSTIC_PACKET
git_commit_decision: COMMIT_DIAGNOSTIC_ONLY
git_push_decision: SKIP_PUSH
published_files:
  - results/20260703_mainline_resume_goal/controller_report.md
  - results/20260703_mainline_resume_goal/execution_plan.md
  - results/20260703_mainline_resume_goal/MANIFEST.md
  - results/20260703_srr_formal_training/result.md
  - results/20260703_srr_formal_training/review.md
  - results/20260703_srr_formal_training/MANIFEST.md
  - results/20260703_srr_formal_training/job_status.md
  - results/20260703_srr_formal_training/experiment_adequacy_report.md
  - results/20260703_srr_formal_training/one_batch_overfit.md
  - results/20260703_srr_formal_training/checkpoint_policy.md
  - results/20260703_srr_formal_training/prediction_sanity.md
  - results/20260703_srr_formal_training/metrics_summary.md
  - results/20260703_srr_formal_training/subgroup_metrics.csv
  - results/20260703_srr_formal_training/component_hd_by_case.csv
  - results/20260703_srr_formal_training/roi_coverage.csv
  - results/20260703_srr_formal_training/proposal_pr_sweep.csv
  - results/20260703_srr_formal_training/label_export_qc.md
  - results/20260703_srr_formal_training/failure_interpretation.md
  - results/20260703_srr_formal_training/variants/srr_propref_shared_dual_dict/summary.json
  - results/20260703_srr_formal_training/variants/srr_propref_shared_dual_dict/training_log.csv
  - results/20260703_srr_formal_training/variants/srr_propref_scar_precision/summary.json
  - results/20260703_srr_formal_training/variants/srr_propref_scar_precision/training_log.csv
  - results/20260703_srr_formal_training/variants/srr_propref_no_proto_cascade/summary.json
  - results/20260703_srr_formal_training/variants/srr_propref_no_proto_cascade/training_log.csv
  - results/20260703_cine_temporal_resume/result.md
  - results/20260703_cine_temporal_resume/review.md
  - results/20260703_cine_temporal_resume/MANIFEST.md
  - results/20260703_cine_temporal_resume/safe_cases_used.csv
  - results/20260703_cine_temporal_resume/mismatch_cases_heldout.csv
  - results/20260703_cine_temporal_resume/reference_frame_contract.md
  - results/20260703_cine_temporal_resume/motion_or_warp_metrics.csv
  - results/20260703_cine_temporal_resume/temporal_metrics_summary.md
  - results/20260703_cine_temporal_resume/case_metrics.csv
  - results/20260703_cine_temporal_resume/summary_metrics.csv
  - results/20260703_cine_temporal_resume/center_summary_metrics.csv
  - results/20260703_cine_temporal_resume/warp_sanity.csv
  - results/20260703_cine_temporal_resume/motion_or_warp_summary.csv
  - results/20260703_cine_temporal_resume/resource_audit.md
  - results/20260703_cine_temporal_resume/anatomy_prior_adapter_audit.md
  - results/20260703_cine_temporal_resume/label_export_qc.md
  - results/20260703_cine_temporal_resume/failure_interpretation.md
  - jobs/src/run_srr_propref_formal_myops_fold0.sh
  - scripts/evaluation/cine_motion_hardmode_20260703.py
blocked_actions:
  - validation upload/fold expansion/next-stage training remain blocked
next_required_action: return reviewed diagnostic packet to GPT strategic planner; do not promote or expand without a new GPT-authored task
reason_if_not_published: local diagnostic commit is prepared, but remote push was blocked by external-disclosure safety review
reason_if_no_route_promotion: MyoPS adequacy failed on train-loop seconds; Cine remains local proxy only without hosted evidence
