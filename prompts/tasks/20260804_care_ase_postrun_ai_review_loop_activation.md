---
task_key: 20260804_care_ase_postrun_ai_review_loop_activation
task_kind: maintenance
task_type: activate_repository_mediated_chatgpt_codex_review_loop
status: DRAFT_WAIT_CURRENT_ASE_RUN_TERMINAL
risk_level: high
route_change: false
scientific_decision_scope: none
execution_mode: controller_supervised
requires_execution_controller: true
controller_is_coordinator: true
executor_slots: 1
executor_count: 1
parallel_execution_allowed: false
mapper_required: false
architecture_impact: none
wiki_update_required: true
diagram_update_required: false
slurm_runtime_continuity_required: true
continuity_backend: tmux_watcher
planning_review_required: false
review_required: false
allow_git_commit: true
auto_git_commit: true
allow_git_push: true
auto_git_push: true
formal_training_authorized: false
outer_access_authorized: false
validation_upload_authorized: false
docker_upload_authorized: false
---

# CARE-ASE current-run terminal 后启用 AI review loop

## Boundary

Do not execute this task while the current CARE-ASE fold1/fold4 run is active. Do not alter its checkout, source hash, permit, checkpoints, jobs, fair-comparison outputs or controller continuity.

This task starts only after the current run has terminal accounting and the user chooses the repair base commit.

## Objective

Create an isolated CARE-ASE faithful-implementation branch/worktree, attach one dedicated Codex repair thread, and activate the repository-mediated loop defined in:

```text
automation/ai_review_loop/README.md
automation/ai_review_loop/PROTOCOL.md
automation/ai_review_loop/chatgpt_hourly_task_prompt.md
scripts/automation/ai_review_loop.py
```

The loop repeatedly performs:

```text
Codex implementation
-> notifier trigger
-> hourly independent ChatGPT review
-> GitHub REVISE/PASS artifacts
-> exact Codex thread resume
-> repair
```

until ChatGPT writes PASS for the current implementation SHA or a hard stop is reached. PASS returns to the user. It does not authorize training.

## Activation steps

1. Confirm current training is terminal and capture its final source/checkpoints/results without rewriting history.
2. Read latest origin/main and machine truth. Mark stale CURRENT/wiki evidence explicitly.
3. Select the user-approved base commit.
4. Create only:

```text
branch: ai-review/care-ase-faithful
worktree: /users/a/e/aereinh/CARE_ai_review/care-ase-faithful
CODEX_HOME: /users/a/e/aereinh/.codex-homes/CARE_AI_LOOP_care-ase-faithful
local state: /users/a/e/aereinh/.ai-review-loop/care-ase-faithful
```

5. Start one dedicated Codex goal/thread in that worktree. Record the exact thread id locally; do not commit it.
6. Configure the frozen CARE-ASE contract and critical path list.
7. Run the AI review-loop unit tests and validator.
8. Publish review round 1, commit/push the request artifacts, emit the notifier-compatible brief, and run the existing notifier.
9. Start the watcher in a dedicated tmux window. It must use exact thread id, flock, 60-second polling and branch/worktree checks.
10. Do not start training after PASS. Write a concise terminal packet and return to the user for the next decision.

## Hard gates

- No review of moving/unbound HEAD.
- No old PASS applied to a new critical fingerprint.
- No implementation edits by ChatGPT Reviewer.
- No contract weakening by Codex.
- No review-artifact commit treated as implementation change.
- No response to generic repository commits.
- No `codex --last` or tmux keystroke injection.
- No same checkout for active training and repair.
- No more than 12 rounds.
- Same unresolved blocker for three rounds stops as `STOPPED_STUCK`.
- No training, outer, upload or deployment before user authorization.
