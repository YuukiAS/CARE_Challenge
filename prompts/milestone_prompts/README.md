# SRR-v3 Milestone Prompts

Use this folder for the copy-paste prompts during the SRR-v3 milestone workflow.

- `EXECUTOR_PROMPTS.md`: prompts for the main Codex executor/controller session.
- `REVIEWER_PROMPTS.md`: prompts for the separate read-only Codex reviewer/auditor session.

Workflow:

1. Copy one executor prompt and run it in the main Codex session.
2. The executor writes the result directory, commits lightweight report files locally, and stops. It does not push.
3. You push the executor commit manually.
4. Copy the matching reviewer prompt and run it in a separate read-only Codex session.
5. The reviewer writes `review.md`, commits it locally, and stops. It does not push.
6. You push the reviewer commit manually.
7. Only then start the next milestone if the review has the audited-go decision.

Do not run multiple milestones in one Codex goal.
