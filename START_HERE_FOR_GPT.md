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

## SRR/MyoPS/Cine Route Bootstrap

Before writing any SRR/MyoPS/Cine milestone, Codex goal, handoff, or route decision, copy or download and read the local repository route diagrams:

- `images/SRR-v2.png`
- `images/SRR-v2.5.png`
- `images/SRR-v3.png`
- any later SRR/MyoPS route diagrams present under `images/`

Follow `prompts/THREAD_BOOTSTRAP_ROUTE_IMAGE_PROTOCOL.md` exactly. After reading the diagrams, first state the route objective in your own words.

The recovered route objective must preserve this meaning: SRR-MyoPS is availability-aware selective retrieval plus a semantic representation retrieval bank, anatomy-guided lesion proposal, pathology-specific soft-ROI refinement, and explicit losses/objectives. nnU-Net or another strong segmentation model may be used only as anchor, context, evidence, or safety source. Do not downgrade SRR into optional post-processing or a generic fallback around nnU-Net.

If the diagrams cannot be located, copied/downloaded, opened, or interpreted, block before generating any milestone. Report `BLOCKED_ROUTE_DIAGRAMS_UNAVAILABLE`, list the failed paths, and ask the user to provide the missing readable diagrams or repository access.
