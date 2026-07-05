---
task_key: "20260705_srr_v3_m3_myops_min_effective_pilot_training"
project: "CARE_Challenge"
status: "READY_FOR_USER_REVIEW"
task_type: "milestone"
milestone_id: "M3"
risk_level: "high"
allow_code_change: true
allow_shell_command: true
allow_network: false
allow_external_upload: false
review_required: true
mechanism_class: "MyoPS minimum-effective pilot training / not full fold"
expected_result_dir: "results/20260705_srr_v3_m3_myops_min_effective_pilot_training/"
prerequisite_review: "results/20260705_srr_v3_m2_myops_bounded_runtime_repair/review.md:M2_AUDITED_GO"
minimum_effective_training:
  min_optimizer_steps: 1200
  min_train_loop_seconds: 1800
  min_eval_cases: 12
  require_one_batch_overfit: true
  require_prediction_sanity: true
  require_loss_decrease: true
  require_same_split_baseline: true
  require_cache_isolation: true
required_outputs:
  - "result.md"
  - "pilot_training_config.md"
  - "training_curves.csv"
  - "validation_events.csv"
  - "prediction_sanity.csv"
  - "gate_residual_stats.csv"
  - "prototype_bank_summary.json"
  - "same_split_help_harm.csv"
  - "hard_subgroup_metrics.csv"
  - "adequacy_check.md"
  - "completion_check.md"
  - "review_request.md"
  - "MANIFEST.md"
forbidden_substitutes:
  - "6-step smoke as pilot"
  - "full fold training"
  - "eval-only over old checkpoints"
  - "missing gate/residual stats"
  - "missing same-split nnU-Net comparison"
  - "route promotion"
---

# Milestone M3: MyoPS Minimum-Effective Pilot Training

## Goal

Run the first scientifically interpretable MyoPS SRR-v3 pilot after M0-M2 pass. This is not full-fold training and not a challenge candidate. It is a minimum-effective pilot designed to answer whether SRR can learn non-trivial, bounded corrections over nnU-Net on a controlled subset.

## Prerequisite Gate

Before starting, verify that `results/20260705_srr_v3_m2_myops_bounded_runtime_repair/review.md` exists and contains `M2_AUDITED_GO`. If not, stop with `M3_BLOCKED_BY_M2`.

## Pilot Scope

Use a controlled fold0 training/eval subset, not full folds. The subset must include:

- scar-positive cases;
- T2-present edema-positive cases;
- CenterC hard cases if available;
- no-T2 cases for safety sanity;
- at least one case where nnU-Net is known to be imperfect from prior help/harm or overlay diagnostics.

The result must include cache/provenance isolation. Do not reuse 6-step bounded smoke checkpoints as pilot evidence.

## Minimum Effective Training

The milestone must satisfy the frontmatter `minimum_effective_training` fields. If resource limits prevent this, stop with `M3_NEEDS_EVIDENCE_RESOURCE_BLOCKED` and do not call the run a pilot.

## Required Evidence

Report:

- training loss curve and validation events;
- one-batch overfit before pilot;
- prediction sanity including no-T2 edema voxels;
- same-split nnU-Net help/harm by case and class;
- gate open-rate, residual magnitude, and decode label-delta counts;
- prototype bank counts with T2-present edema coverage;
- hard subgroup metrics for scar, T2-present edema, CenterC, component count, HD95, and remote FP.

## Required Outputs

Write all required outputs under `results/20260705_srr_v3_m3_myops_min_effective_pilot_training/`.

`completion_check.md` must contain one of:

- `M3_READY_FOR_REVIEW`
- `M3_NEEDS_REVISION`
- `M3_NEEDS_EVIDENCE`
- `M3_RESOURCE_BLOCKED`

A separate read-only reviewer should later write `review.md` with one of:

- `M3_AUDITED_GO`
- `M3_AUDITED_NEEDS_REVISION`
- `M3_AUDITED_NEEDS_EVIDENCE`

## Completion Gate

Do not mark ready if the run is under the minimum effective budget, if loss does not decrease without explanation, if gate/residual stats are missing, if prototype bank lacks T2-present edema coverage, or if same-split nnU-Net help/harm is absent.
