# Batch4 Completion Check

task_key: `20260721_srr_batch4_forced_fold0_training`

status: `REVIEWED_PACKET_AUDITED_GO`

review_token_requested: `BATCH4_TRAINING_PACKET_AUDITED_GO`
review_token_received: `BATCH4_TRAINING_PACKET_AUDITED_GO`

## Terminal Evidence

- Valid formal training job: `59682067`, `COMPLETED 0:0`, elapsed `00:33:26`, node `g1807htzh01`.
- Budget proof: `actual_optimizer_steps=1800`, `optimizer_steps=1800`, `max_steps=1800`, `train_loop_seconds=1800.0000680589583`, `post_optimizer_wait_seconds=1195.3847569739446`.
- Stop reason: `max_steps_min_train_loop_seconds_satisfied_without_extra_optimizer_steps`.
- Data contract: `176` train cases, `44` validation/evaluation cases, model `m10_d3_hierarchical_memory_propref`, encoder `full_4scale`, base channels `32`.
- Full-volume evaluation coverage: steps `600`, `1200`, and `1800`; validator confirmed each runtime component file covers `44` cases.
- Selected checkpoint: `step_1800`, SHA256 `bc325754202d5cf0aa59aa8fab0306b38c2665640339afa3f8d06a13c70009f6`.
- Same-weight controls: identity, anchor-bounded SRR correction, and no-anchor all use the same selected checkpoint hash and each wrote `44` predictions.

## Explicit Failure Accounting

- `59678596` is invalid and zero formal credit despite Slurm `COMPLETED 0:0`, because `actual_optimizer_steps=7182` exceeded `max_steps=1800`.
- `59680114` is failed/zero control credit from the invalid checkpoint lineage.
- `59686817` is failed/zero control job credit. Its inference outputs were validly aggregated only after the evaluator config contract was repaired and rerun locally.

## Missing Summary Field Coverage

- Runtime summary top-level `source_commit` is `None`; validator covers it from selected checkpoint payload `source_commit=0466260e3f4eb6c50b05a7f5a8b66652b873fe46`.
- Runtime summary top-level `full_volume_eval_steps` is `None`; validator covers it from runtime files for `step_600`, `step_1200`, and `step_1800`, each with `44` cases.

## Validator

- Command: `./envs/env_CARE/bin/python scripts/evaluation/validate_srr_batch4_packet.py`
- Result: `BATCH4_STRICT_VALIDATION_PASS`

## Boundaries

No `review.md` was written by the controller. The required independent read-only reviewer report was added after the controller packet because the task explicitly set `review_required: true`. No training, Slurm submission, validation packaging, validation upload, hosted metric claim, Cine expansion, route promotion, or scientific final decision was performed during review.
