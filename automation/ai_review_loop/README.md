# Repository-mediated AI review loop

## Practical decision

This directory defines a reusable, no-OpenAI-API review-and-repair loop for CARE and future repositories such as CardiacNexus and EAT.

The loop does **not** change or stop the currently running CARE-ASE training. The first CARE-ASE activation must wait until the current fold1/fold4 run is terminal. Until then, this system remains infrastructure only.

The intended flow is:

```text
Codex implementation/repair commit
-> tracked REQUEST.json bound to exact implementation SHA
-> existing controller notifier sends AI_REVIEW_READY_V1
-> personal Gmail Sent copy is visible to ChatGPT
-> hourly ChatGPT scheduled task reads Gmail + GitHub
-> ChatGPT reviews the exact SHA and pushes PASS/REVISE artifacts
-> server watcher sees CURRENT.json
-> on REVISE, codex exec resume <exact thread id> receives repair prompt
-> Codex repairs, tests, commits, publishes the next request
-> repeat
-> on PASS, stop at AWAIT_HUMAN_DECISION
```

The user remains responsible for blueprint design, scientific choices, promotion decisions, merge approval, training authorization, and final acceptance.

## Why GitHub Actions is present but not the orchestrator

GitHub Actions is used only for deterministic validation of protocol files, state bindings, and tests. It does not call ChatGPT, Codex, Gmail, or a private server. This avoids API charges, secrets in CI, and self-hosted-runner risk.

The first operational version uses:

- existing CARE notifier for the trigger email;
- ChatGPT Scheduled Tasks, once per hour;
- the GitHub app for exact-SHA reading and review-artifact writes;
- a local server watcher that polls `origin/<branch>` every 60 seconds;
- `codex exec resume <thread-id>` to wake the exact repair thread.

A self-hosted GitHub Actions runner is optional later. It is not required for v1 because the server watcher already supplies near-immediate Codex wake-up after ChatGPT pushes a decision.

## Gmail trigger feasibility

The connected personal Gmail can search messages in `in:sent`. Existing CARE notifier messages sent from the personal Gmail account to the school mailbox are visible there. The school mailbox itself does not need to be connected to ChatGPT.

The stable keyword is:

```text
AI_REVIEW_READY_V1
```

The email is only a wake-up hint. The repository `REQUEST.json` is the machine truth. ChatGPT must never trust a long email body as the review contract.

## Isolation model

Do not repair the same checkout that is running training.

For a live review task:

```text
implementation branch: ai-review/<task_id>
repair worktree: /users/a/e/aereinh/CARE_ai_review/<task_id>
Codex home: /users/a/e/aereinh/.codex-homes/CARE_AI_LOOP_<task_id>
local watcher state: /users/a/e/aereinh/.ai-review-loop/<task_id>/
```

The active training checkout remains frozen. ChatGPT reviews the implementation branch by exact commit SHA. Passing review does not merge it and does not authorize training.

## Files

- `PROTOCOL.md`: state machine, keyword, anti-loop and security rules.
- `chatgpt_hourly_task_prompt.md`: exact prompt for the hourly ChatGPT task.
- `schemas.json`: machine fields and allowed states.
- `task_template.json`: reusable task configuration template.
- `scripts/automation/ai_review_loop.py`: publish, notify-brief, validate and watch commands.
- `.github/workflows/ai-review-loop-ci.yml`: deterministic CI only.
- `prompts/tasks/20260804_care_ase_postrun_ai_review_loop_activation.md`: CARE-ASE activation handoff after the current run is terminal.

## Minimal activation sequence

After the current CARE-ASE run is terminal:

```bash
# 1. Create an isolated branch and worktree.
git fetch origin main --prune
git branch ai-review/care-ase-faithful <chosen-base-sha>
git worktree add /users/a/e/aereinh/CARE_ai_review/care-ase-faithful \
  ai-review/care-ase-faithful

# 2. Start one dedicated Codex automation session and record its exact thread id
#    in a local, untracked file.
mkdir -p /users/a/e/aereinh/.ai-review-loop/care-ase-faithful
printf '%s\n' '<thread-id>' \
  > /users/a/e/aereinh/.ai-review-loop/care-ase-faithful/codex_thread_id

# 3. Codex commits implementation source, then publishes the review request.
python scripts/automation/ai_review_loop.py publish-request \
  --repo-root . \
  --task-id care-ase-faithful \
  --repository YuukiAS/CARE_Challenge \
  --branch ai-review/care-ase-faithful \
  --contract-path prompts/tasks/<frozen-contract>.md \
  --implementation-sha "$(git rev-parse HEAD)" \
  --critical-path 'src/care_myocardium/**/*.py' \
  --critical-path 'scripts/**/*.py' \
  --critical-path 'jobs/**/*.sh' \
  --critical-path 'tests/care_ase/**/*.py' \
  --context-path AGENTS.md \
  --context-path START_HERE_FOR_GPT.md \
  --context-path GPT_PLANNER_CARE_PROTOCOL.md \
  --context-path prompts/routes/handoffs/CURRENT.md \
  --context-path wiki/README.md \
  --enabled

# 4. Commit and push request artifacts, then write the existing notifier brief.
python scripts/automation/ai_review_loop.py emit-notification-brief \
  --repo-root . --task-id care-ase-faithful

# 5. Existing controller goal finalizer commits/pushes and runs the existing
#    controller notifier. No second SMTP service is created.
```

The watcher is then started in a dedicated tmux window using the command documented in `PROTOCOL.md`.
