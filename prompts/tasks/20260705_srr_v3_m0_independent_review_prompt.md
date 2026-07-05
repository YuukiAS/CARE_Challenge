# M0 Independent Review Prompt

Use this prompt after the main Codex executor has completed M0 and pushed `results/20260705_srr_v3_m0_architecture_master_contract/`.

```text
You are a separate read-only reviewer/auditor session for M0. Do not fix code, do not generate missing artifacts, do not train, do not package validation, do not upload, and do not start M1.

Review only:
- `prompts/tasks/20260705_srr_v3_m0_architecture_master_contract.md`
- `prompts/MILESTONE_REVIEW_PROTOCOL.md`
- `prompts/HANDOFF_GATE_POLICY.md`
- `prompts/GPT_HARD_GATE_PROMPT.md`
- `results/20260705_handoff_hard_gate_repair/review.md`
- `results/20260705_srr_v25_evidence_supplement_audit/result.md`
- `results/20260705_srr_v3_m0_architecture_master_contract/`

Check that all M0 required outputs exist, `completion_check.md` declares `M0_READY_FOR_REVIEW`, the strict hard-gate checks are documented, the downstream milestone graph is machine-checkable, and no forbidden substitute was used. Do not repair missing files. If anything required is missing, mark the review as needs revision or needs evidence.

Write only:
`results/20260705_srr_v3_m0_architecture_master_contract/review.md`

The review decision must be exactly one of:
- `M0_AUDITED_GO`
- `M0_AUDITED_NEEDS_REVISION`
- `M0_AUDITED_NEEDS_EVIDENCE`

After writing the review, commit and push only the review file and any tiny review manifest if explicitly needed.
```
