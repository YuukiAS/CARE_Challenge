# SRR-v3 First Milestone Start Prompt

Use this prompt to start the next Codex session.

```text
Execute `prompts/tasks/20260705_srr_v3_m0_architecture_master_contract.md` only. Do not start later milestones. Before executing the scientific task, enforce the hard-gate policy: exact task graph, strict validator, completion-check-before-final-audit, minimum effective training, and current-bad-packet regression. If any hard gate fails, stop with NEEDS_REVISION or NEEDS_EVIDENCE; do not continue to final audit.

This is a planning/contract milestone, not training. Read the handoff hard-gate repair review, SRR-v2.5 evidence supplement audit, HANDOFF_GATE_POLICY, and GPT_HARD_GATE_PROMPT. Produce the exact result directory `results/20260705_srr_v3_m0_architecture_master_contract/` with the required outputs. No model edits, no full-fold training, no validation packaging, no upload, no route promotion, no fold expansion. Stop after writing `completion_check.md` and `review_request.md`.
```
