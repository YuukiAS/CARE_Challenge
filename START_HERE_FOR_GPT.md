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

Before writing any SRR/MyoPS/Cine milestone, Codex goal, handoff, or route decision, read the SRR route diagrams from the current ChatGPT Project background files / project materials. Use these canonical repository filenames and versions as identifiers:

- `images/SRR-v2.png`
- `images/SRR-v2.5.png`
- `images/SRR-v3.png`
- any later SRR/MyoPS route diagrams present under `images/`

The repository image paths remain the canonical filenames and version references, but they are not the required GPT visual-reading entrypoint. Do not rely on GitHub connector PNG blobs, SHA/base64 metadata, filenames, old chat summaries, memory, or text recaps as a substitute for visual reading through ChatGPT Project background materials or images uploaded into the current conversation.

Follow `prompts/THREAD_BOOTSTRAP_ROUTE_IMAGE_PROTOCOL.md` exactly. After reading the diagrams, first state the route objective in your own words.

The recovered route objective must preserve this meaning: SRR-MyoPS is availability-aware selective retrieval plus a semantic representation retrieval bank, anatomy-guided lesion proposal, pathology-specific soft-ROI refinement, and explicit losses/objectives. nnU-Net or another strong segmentation model may be used only as anchor, context, evidence, or safety source. Do not downgrade SRR into optional post-processing or a generic fallback around nnU-Net.

If the diagrams cannot be accessed or visually interpreted from ChatGPT Project background materials, block before generating any milestone. Report `BLOCKED_PROJECT_ROUTE_DIAGRAMS_UNAVAILABLE`, list the missing versions, and ask the user to add the diagrams to the ChatGPT Project background materials or upload them into the current conversation.
