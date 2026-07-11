# Reviewer Prompt For M10 Blocked Prerequisite Packet

This is a separate read-only reviewer session for `results/20260711_srr_v3_m10_complete_mechanism_repair/`.

Review only whether the controller correctly stopped with `M10_BLOCKED_PREREQUISITE` before executor wave 1. Do not fix code, generate missing artifacts, train, resume jobs, package/upload validation, push, start M11, or review scientific M10 completion.

Check:

- the controller used `prompts/shared/EXECUTOR_PROMPTS.md` section `M10 executor/controller: SRR-v3 complete mechanism repair`;
- the controller strictly used `prompts/tasks/20260711_srr_v3_m10_complete_mechanism_repair_executor_plan.yaml`;
- the executor plan validator passed;
- the planner draft commit was not an ancestor of current HEAD;
- `prompts/shared/M10_srr_v3_complete_mechanism_repair.md` was missing even though the planning review declares it as `reviewed_prompt_path`;
- no executor wave, Slurm job, training, validation packaging/upload, push, or controller-written `review.md` occurred.

Write only `review.md` if the user explicitly starts the independent review.
