# Doc Change Summary

## Durable Protocol Files

- `prompts/MILESTONE_REVIEW_PROTOCOL.md`: upgraded from a descriptive protocol into the formal two-step milestone gate contract, including required executor files, reviewer-only `review.md`, prerequisite review tokens, and forbidden shortcuts.
- `prompts/AGENT_RULES.md`: added `task_type: milestone` rules and same-session controller boundary.
- `prompts/CHATGPT_RULES.md`: added GPT planning requirements for one milestone at a time, executor/reviewer separation, and exact audited-go continuation.
- `prompts/CONTROLLER_TASK_PROTOCOL.md`: clarified that milestone chains are stricter than ordinary controller tasks and that controller reports cannot replace `completion_check.md`, `review_request.md`, or independent `review.md`.
- `prompts/HANDOFF_GATE_POLICY.md`: added milestone executor/review separation and machine-checkable milestone continuation gates.
- `prompts/GPT_HARD_GATE_PROMPT.md`: added required executor and reviewer wording for milestone prompts.
- `AGENTS.md`: mirrored the milestone executor/reviewer boundary in repo-level agent rules.

## SRR-v3 Prompt Files

Updated SRR-v3 milestone prompts M0-M5 so each one states:

- executor/controller runs one milestone only;
- writes required outputs, `completion_check.md`, `review_request.md`, and `MANIFEST.md`;
- does not write `review.md`;
- does not mark `*_AUDITED_GO`;
- does not approve itself;
- does not start the next milestone;
- next milestone requires a separate read-only reviewer `review.md` with exact audited-go token.

Also updated:

- `prompts/tasks/20260705_srr_v3_milestone_codex_goal_prompts.md`
- `prompts/tasks/20260705_srr_v3_milestone_plan_index.md`
- `prompts/tasks/20260705_srr_v3_architecture_alignment_note.md`

## Scope Boundary

This repair does not execute SRR-v3 M0, does not train models, does not package validation, does not upload, and does not promote any route.
