# Independent Reviewer Prompt

You are the separate read-only reviewer for
`results/20260711_agent_flow_generic_protocol_repair/`.

Do not modify code, do not generate missing evidence, do not run training, do
not submit Slurm jobs, do not push, and do not execute or design any scientific
milestone.

Reject if any of the following are true:

- active policy/templates/skills/generic validators still use concrete
  milestone numbers to decide control flow, review token, history prerequisite,
  planning review requirement, or packet schema;
- `python scripts/validation/validate_handoff_policy.py --policy --warnings-as-errors`
  fails;
- candidate readiness and policy health are not separated;
- planning critic review can be bypassed with arbitrary token or stale prompt
  hash;
- direct executor and controller-supervised schemas are not both available;
- `wiki/current_state.yaml` is not the current review source;
- history predecessor delta is not dynamic;
- controller packet schema is not the single machine source for required files;
- Slurm monitor packet completion guards were weakened.

If supported, write `review.md` with a controlled reviewer decision. Do not
write route promotion, scientific stop, upload, push, or next milestone
authorization.
