# Handoff Repair Review Start Prompt

把下面这段交给另一个 Codex session，用来审阅 handoff milestone review protocol repair 的结果。

```text
只执行只读审阅，不继续实现。审阅对象是 `results/20260705_handoff_milestone_review_protocol_repair/`。

请读取：
- `prompts/tasks/20260705_review_gate_repair_start_prompt.md`
- `results/20260705_handoff_milestone_review_protocol_repair/`
- `prompts/MILESTONE_REVIEW_PROTOCOL.md`
- `prompts/AGENT_RULES.md`
- `prompts/CHATGPT_RULES.md`
- `prompts/CONTROLLER_TASK_PROTOCOL.md`
- `prompts/HANDOFF_GATE_POLICY.md`
- `prompts/GPT_HARD_GATE_PROMPT.md`
- `prompts/tasks/20260705_srr_v3_milestone_codex_goal_prompts.md`
- `prompts/tasks/20260705_srr_v3_first_milestone_start_prompt.md`

检查 durable handoff 文件是否已经一致执行两步 milestone gate：executor 只写 result、completion_check.md、review_request.md 后停止；独立 reviewer 写 review.md；只有 review.md 里有 audited-go 才能进入下一 milestone。

检查修复结果目录是否包含 result.md、doc_change_summary.md、milestone_flow_contract.md、completion_check.md、review_request.md、MANIFEST.md，并检查 completion_check.md 是否表示 ready for review。

只写一个文件：
`results/20260705_handoff_milestone_review_protocol_repair/review.md`

review decision 必须是以下之一：
- `HANDOFF_MILESTONE_REVIEW_REPAIR_AUDITED_GO`
- `HANDOFF_MILESTONE_REVIEW_REPAIR_NEEDS_REVISION`
- `HANDOFF_MILESTONE_REVIEW_REPAIR_NEEDS_EVIDENCE`

完成后 commit/push。
```
