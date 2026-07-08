# SRR-v3 Milestone Prompts

Use this folder for the copy-paste prompts during the SRR-v3 milestone workflow.

- `EXECUTOR_PROMPTS.md`: prompts for the main Codex executor/controller session.
- `REVIEWER_PROMPTS.md`: prompts for the separate read-only Codex reviewer/auditor session.
- `M<id>_<short_slug>.md`: temporary GPT-authored staging file for a future
  milestone that has not yet been split into the canonical executor/reviewer
  files.

Workflow:

1. Copy one executor prompt and run it in the main Codex session.
2. The executor writes the result directory, commits lightweight report files locally, and stops. It does not push.
3. You push the executor commit manually.
4. Copy the matching reviewer prompt and run it in a separate read-only Codex session.
5. The reviewer writes `review.md`, commits it locally, and stops. It does not push.
6. You push the reviewer commit manually.
7. Only then start the next milestone if the review has the audited-go decision.

Do not run multiple milestones in one Codex goal.

Future milestone authoring:

1. GPT must not directly edit the large canonical files when drafting a new
   milestone. Instead, it must write one staging file here, named
   `M<id>_<short_slug>.md`, for example `M9_myops_fold_expansion_planning.md`.
2. The staging file must contain both `## Executor Prompt` and
   `## Reviewer Prompt` sections.
3. A later Codex maintenance step will split/merge those sections into
   `EXECUTOR_PROMPTS.md` and `REVIEWER_PROMPTS.md`.
4. After the split/merge is verified, delete the temporary staging file.
