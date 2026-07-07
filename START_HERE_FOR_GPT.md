# Start Here For GPT

This is the root entrypoint for any new GPT/ChatGPT planning thread reading this repository. Read this file before writing CARE milestones, Codex goals, handoffs, route judgments, or review instructions.

## Required Reading Order

1. `START_HERE_FOR_GPT.md`
2. `AGENTS.md`
3. `README.md`
4. `prompts/CHATGPT_RULES.md`
5. `prompts/GPT_HARD_GATE_PROMPT.md`
6. `prompts/THREAD_BOOTSTRAP_ROUTE_IMAGE_PROTOCOL.md`

Do not rely only on old chat summaries, memory, or natural-language recaps when planning SRR/MyoPS/Cine routes.

## MONITOR_PACKET_IS_NOT_COMPLETION

Any GPT/ChatGPT milestone, handoff, or review instruction must enforce this rule: a monitor packet, pending Slurm job packet, watcher packet, or submitted-only job packet is not completion.

If `completion_check.md` includes `NEEDS_MONITOR`, `PENDING_MONITOR`, `JOB_SUBMITTED`, `PENDING_PRIORITY`, `RUNNING`, `AWAITING_SACCT`, or equivalent pending/monitor language, GPT must not ask a reviewer to grant audited-go. The correct reviewer decision is `NEEDS_EVIDENCE` or `NEEDS_MONITOR`.

After a Slurm job completes, the executor must rerun the relevant aggregator/evidence collector and commit tracked lightweight evidence containing job id, state, exit code, runtime, log path, runtime output path, aggregation command, and updated tracked evidence files. `commands_run.md` with only `sbatch submitted`, `squeue pending`, `PENDING Priority`, or pending `sacct` is not completion evidence.

This applies to M7 follow-up2/follow-up3 and all future milestones.

## SRR/MyoPS/Cine Route Bootstrap

Before writing any SRR/MyoPS/Cine milestone, Codex goal, handoff, or route decision, read the SRR route diagrams from the current ChatGPT Project background files / project materials. Use these canonical repository filenames and versions as identifiers:

- `images/SRR-v2.png`
- `images/SRR-v2.5.png`
- `images/SRR-v3.png`
- any later SRR/MyoPS route diagrams present under `images/`

The repository image paths remain the canonical filenames and version references, but they are not the required GPT visual-reading entrypoint. Do not rely on GitHub connector PNG blobs, SHA/base64 metadata, filenames, old chat summaries, memory, or text recaps as a substitute for visual reading through ChatGPT Project background materials or images uploaded into the current conversation.

Follow `prompts/THREAD_BOOTSTRAP_ROUTE_IMAGE_PROTOCOL.md` exactly. After reading the diagrams, first state the route objective in your own words.

The recovered route objective must preserve this meaning: SRR-MyoPS is availability-aware selective retrieval plus a semantic representation retrieval bank, anatomy-guided lesion proposal, pathology-specific soft-ROI refinement, and explicit losses/objectives. nnU-Net or another strong segmentation model may be used only as anchor, context, evidence, or safety source. Do not downgrade SRR into optional post-processing or a generic fallback around nnU-Net.

If the diagrams cannot be accessed or visually interpreted from ChatGPT Project background materials, block before generating any milestone. Report `BLOCKED_PROJECT_ROUTE_DIAGRAMS_UNAVAILABLE`, list the missing versions, and ask the user to add the diagrams to the ChatGPT Project background materials or upload them into the current conversation.
