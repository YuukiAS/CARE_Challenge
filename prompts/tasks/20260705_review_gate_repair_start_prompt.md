# Milestone Review Gate Repair Prompt

```text
Before running SRR-v3 M0, update the CARE handoff documents to require a two-step milestone gate.

Executor step: one session runs exactly one milestone, writes required outputs in results/<task_key>/, writes completion_check.md and review_request.md, then stops.

Reviewer step: a different read-only session inspects that result directory and writes review.md. The next milestone may start only when review.md contains the audited-go state.

Update durable files: prompts/MILESTONE_REVIEW_PROTOCOL.md, prompts/AGENT_RULES.md, prompts/CHATGPT_RULES.md, prompts/CONTROLLER_TASK_PROTOCOL.md, prompts/HANDOFF_GATE_POLICY.md, prompts/GPT_HARD_GATE_PROMPT.md, and the SRR-v3 milestone prompt files.

Write the repair report under results/20260705_handoff_milestone_review_protocol_repair/ with result.md, doc_change_summary.md, milestone_flow_contract.md, completion_check.md, review_request.md, and MANIFEST.md. Do not run SRR-v3 M0 from this repair task.
```
