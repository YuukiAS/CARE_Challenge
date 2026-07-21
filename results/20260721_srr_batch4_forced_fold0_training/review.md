# Batch4 Independent Review

task_key: `20260721_srr_batch4_forced_fold0_training`

review_timestamp_utc: `2026-07-21T01:48:53Z`
review_mode: `independent_readonly`
review_required: `true`

## Review Decision

review_decision: `PASS`
review_token: `BATCH4_TRAINING_PACKET_AUDITED_GO`

The Batch4 terminal packet passes the requested operational and evidence review. This is a local Batch4 packet audit only. It does not authorize validation packaging, validation upload, hosted metric claims, fold expansion, route promotion, M11, or a final scientific conclusion.

## Protocol Gate

- The Batch4 task frontmatter explicitly sets `review_required: true`, `review_mode: independent_thread`, and `reviewer: separate_readonly`; therefore a reviewer report is required under the updated Agent-Flow v2 protocol.
- The controller packet was already locally committed before this review.
- The reviewer did not run training, submit Slurm jobs, modify model code, package validation outputs, upload, or make route/scientific decisions.

## Operational Evidence Checked

- Valid formal training job: `59682067`, Slurm state `COMPLETED 0:0`, elapsed `00:33:26`.
- Training budget evidence: `actual_optimizer_steps=1800`, `optimizer_steps=1800`, `max_steps=1800`, `train_loop_seconds=1800.0000680589583`.
- Selected checkpoint: `step_1800`.
- Selected checkpoint SHA256: `bc325754202d5cf0aa59aa8fab0306b38c2665640339afa3f8d06a13c70009f6`.
- Strict validator rerun: `./envs/env_CARE/bin/python scripts/evaluation/validate_srr_batch4_packet.py` returned `BATCH4_STRICT_VALIDATION_PASS`.
- Executor plan validator rerun: `./envs/env_CARE/bin/python scripts/ops/validate_executor_plan.py prompts/tasks/20260721_srr_batch4_forced_fold0_training_executor_plan.yaml` returned `executor plan validation passed`.

## Zero-Credit Failure Accounting

- `59678596` remains zero formal credit because it completed with `actual_optimizer_steps=7182`, exceeding the 1800-step budget.
- `59680114` remains failed/zero selected-control credit from the invalid checkpoint lineage.
- `59686817` remains failed/zero control job credit; its inference artifacts were evaluated only after local evaluator contract repair and do not count as a successful Slurm control job.

## Metric Evidence

Local fold0 validation/evaluation files include Dice, HD, HD95, component, remote false-positive, subgroup, and casewise metrics:

- `validation_checkpoint_metrics.csv`
- `casewise_metrics.csv`
- `subgroup_metrics.csv`
- `component_remote_fp.csv`
- `help_harm.csv`

Selected `step_1800` all-case rows from `validation_checkpoint_metrics.csv`:

| variant | class | cases | Dice mean | HD mean | HD95 mean | components mean | remote FP mean | empty pred rate |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| argmax | edema `4` | 44 | 0.780042 | 10.774309 | 7.277857 | 3.295455 | 0.045455 | 0.636364 |
| argmax | scar `5` | 44 | 0.561511 | 25.926020 | 13.942591 | 4.659091 | 0.363636 | 0.022727 |
| pathology_aware | edema `4` | 44 | 0.780093 | 10.774309 | 7.299954 | 3.250000 | 0.045455 | 0.636364 |
| pathology_aware | scar `5` | 44 | 0.562570 | 29.602104 | 16.428850 | 4.636364 | 0.500000 | 0.022727 |

Selected same-checkpoint identity-vs-SRR rows from `subgroup_metrics.csv`:

| pathology | subgroup | case rows | anchor Dice | SRR Dice | mean changed voxels | anchor remote FP mm3 | SRR remote FP mm3 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| edema | all | 44 | 0.3944358977 | 0.3951155483 | 2.931818 | 86.191351 | 86.191351 |
| edema | t2_present | 16 | 0.3944358977 | 0.3951155483 | 8.062500 | 237.026215 | 237.026215 |
| edema | no_t2 | 28 | NA | NA | 0.000000 | 0.000000 | 0.000000 |
| scar | all | 44 | 0.5601692281 | 0.5615107217 | 22.204545 | 620.361970 | 605.628867 |
| scar | t2_present | 16 | 0.6933346102 | 0.6932200411 | 7.250000 | 1.102448 | 1.102448 |
| scar | no_t2 | 28 | 0.4840747241 | 0.4862482535 | 30.750000 | 974.224554 | 951.072535 |

These are local fold0 diagnostic metrics only. They are not hosted validation metrics and are not evidence of route promotion or challenge performance.

## Summary Gap Review

- Runtime summary top-level `source_commit=None` is not accepted by assertion; the strict validator covers it from the selected checkpoint payload as `0466260e3f4eb6c50b05a7f5a8b66652b873fe46`.
- Runtime summary top-level `full_volume_eval_steps=None` is not accepted by assertion; the strict validator reconstructs coverage from runtime files for steps `600`, `1200`, and `1800`, each covering 44 cases.

## Residual Boundaries

- The packet supports a Batch4 local diagnostic review decision only.
- The local metrics show small SRR-vs-anchor deltas and mixed scar HD behavior; this should be treated as planner evidence, not as a final scientific decision.
- Validation packaging/upload, hosted metric claim, route promotion, fold expansion, M11, and production readiness remain unauthorized.
