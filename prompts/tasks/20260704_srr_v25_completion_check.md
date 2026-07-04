---
task_key: "20260704_srr_v25_completion_check"
project: "CARE_Challenge"
status: "READY_FOR_USER_REVIEW"
task_type: "execution"
risk_level: "medium"
allow_code_change: false
allow_shell_command: true
allow_network: false
allow_external_upload: false
review_required: false
mechanism_class: "read-only completion check"
---

# Task: Read-Only Completion Check

## Goal

After the implementation and experiment tasks finish, check whether the full SRR-v2.5 packet is complete or still partial.

## Required Checks

Check encoder/context, dictionary semantics, prototype bank, proposal quality, local refinement, training objectives, same-split metrics, hard subgroups, Cine registration, and ablations.

## Required Outputs

Write `results/20260704_srr_v25_completion_check/` with `review.md`, `claim_table.md`, `metric_review.md`, `ablation_review.md`, `decision.md`, and `MANIFEST.md`.
