# Independent Reviewer Prompt

You are the separate read-only reviewer for `20260711_agent_flow_v2_pre_m10_final_repair`.

Read this packet and the changed repository files. Do not edit files, do not train, do not submit Slurm jobs, do not generate missing evidence, do not package validation, do not upload, and do not push.

Reject the packet if any of the following are true:

- controller wrote `review.md` or made a scientific route decision;
- M10 was designed or executed;
- model code, historical M8/M9 result packets, checkpoints, NIfTI, predictions, uploads, raw data, or secrets were modified;
- watcher stops on finalizer exit code 0 while state is still `NEEDS_MONITOR` or `AWAITING_SACCT_RETRY_EXHAUSTED`;
- accounting retry exhaustion requires manual user discovery instead of recording retryable continuation metadata;
- executor wave validator misses nested path overlap, duplicate branch/worktree/result/runtime/log/lock/Slurm namespace, duplicate merge order, dependency cycles, code-writing executor without write scope, or MyoPS/Cine same-wave isolation proof;
- merge helper allows executor self-merge or continues after merge conflict;
- history migration coverage depends on deleted root TODO files rather than archived originals;
- M8 `1.5 Proposal` is not in `wiki/history/M08/components/proposal.md`;
- `todo-m10.md` casing is wrong;
- history comparison is generic placeholder text;
- current/history diagrams contain `历史组件关系`, `component_delta`, `component delta`, or `COMPONENT_DELTA`;
- M10/system-level GPT planning can pass without listing required history files read;
- post-review reconciliation makes scientific judgments instead of copying controlled review fields.

If the packet passes, write `review.md` in this result directory with a conservative audited token. Do not push.
