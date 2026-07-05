# Review Request

review_target: `results/20260705_handoff_milestone_review_protocol_repair/`
review_type: `independent_read_only_protocol_audit`

## Requested Reviewer Action

Start a separate read-only Codex reviewer/auditor session to inspect this result
directory and the changed protocol/prompt files. The reviewer should write:

```text
results/20260705_handoff_milestone_review_protocol_repair/review.md
```

## Review Scope

Verify:

- `prompts/MILESTONE_REVIEW_PROTOCOL.md` defines the two-step milestone gate;
- `prompts/AGENT_RULES.md`, `prompts/CHATGPT_RULES.md`,
  `prompts/CONTROLLER_TASK_PROTOCOL.md`, `prompts/HANDOFF_GATE_POLICY.md`, and
  `prompts/GPT_HARD_GATE_PROMPT.md` enforce it;
- SRR-v3 milestone prompt files M0-M5 require executor stop after
  `completion_check.md` and `review_request.md`;
- executor/controller is forbidden to write `review.md`, approve itself, or
  start the next milestone;
- next milestone requires independent `review.md` with exact audited-go token;
- no SRR-v3 milestone was executed.

## Controlled Review Decision

Use one of:

- `MILESTONE_REVIEW_PROTOCOL_REPAIR_AUDITED_GO`
- `MILESTONE_REVIEW_PROTOCOL_REPAIR_NEEDS_REVISION`
- `MILESTONE_REVIEW_PROTOCOL_REPAIR_NEEDS_EVIDENCE`

The review must remain read-only except for writing `review.md`.
