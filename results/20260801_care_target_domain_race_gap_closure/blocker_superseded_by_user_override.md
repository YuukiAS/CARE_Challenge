用户已明确否决将 W0 existing-interactive allocation 缺失作为终局阻塞。随后 controller 已直接验证 `61220581 / htzhulab / g1807htzh01` 是可用的 RUNNING GPU allocation，且 `srun --jobid=61220581 --overlap ... torch.cuda` 返回 `NVIDIA H100 NVL`。此前 `OPERATIONALLY_BLOCKED_EXISTING_INTERACTIVE_LOST` 只能保留为一次过早 fail-closed packet 的历史记录，不再代表当前 controller 的最终状态。

# Blocker Superseded

- superseded_commit: `ecfe69cbbc0fb126d6b2645691d40f5f016c95a7`
- superseded_decision: `OPERATIONALLY_BLOCKED_EXISTING_INTERACTIVE_LOST`
- superseded_at: `2026-08-01`
- superseding_user_instruction: `有病? 又阻塞???`
- verified_interactive_job_id: `61220581`
- verified_partition: `htzhulab`
- verified_node: `g1807htzh01`
- verified_gpu: `NVIDIA H100 NVL`
- current_controller_action: continue same-scope implementation, preflight, Slurm queue submission, and interactive takeover scheduling

## Corrected Interpretation

The previous packet correctly audited old M0 as `HIGH_LR_SHORT_FINETUNE_NEGATIVE`, but it stopped too early on the resource gate. The current controller must not treat the missing interactive allocation as a final scientific or operational endpoint because job `61220581` is present, RUNNING, on `htzhulab`, and CUDA-usable.

## Active Continuation

Continue toward the same task:

- keep old M0 downgraded;
- implement/prepare M0R, M1, M2, and M3 lanes;
- use htzhulab queue jobs where possible;
- run M3 first on existing interactive job `61220581`;
- submit M0R/M1/M2 htzhulab queue jobs after lane preflight, using isolated outputs;
- if interactive finishes one lane while another lane is still pending, cancel one pending mirror/job and run that lane serially in the interactive allocation;
- do not submit a100-gpu or volta-gpu;
- do not access official validation, upload validation/Docker, or claim hosted metrics.
