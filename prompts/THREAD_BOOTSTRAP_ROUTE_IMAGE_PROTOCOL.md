# Thread Bootstrap Route Image Protocol

This protocol is mandatory for every new GPT/ChatGPT planning thread before it writes or revises CARE MyoPS/Cine milestones, Codex goals, handoffs, or route decisions.

## Purpose

The SRR route is defined by the repository diagrams, not by a loose natural-language memory of previous chats. Future GPT threads must first recover the diagram intent, then write milestones. This prevents the planner from mistaking SRR-v3 for a plain nnU-Net fallback, a generic post-processing block, or an abstract two-branch competition.

## Repository read first

Before writing any SRR/MyoPS/Cine milestone, Codex goal, handoff, or route judgment, the planner must read the current repository entrypoints, starting with `START_HERE_FOR_GPT.md`, then `GPT_PLANNER_CARE_PROTOCOL.md`, `AGENTS.md`, `README.md`, `prompts/CHATGPT_RULES.md`, and `prompts/GPT_HARD_GATE_PROMPT.md`.

## Required Project background visual reading

After reading the repository, the planner must visually read every SRR design diagram at version `v2` or later from the current ChatGPT Project background files / project materials. This includes, when present, diagrams named or described as:

- `v2`
- `v2.5`
- `v3`
- later versions such as `v3.1`, `v4`, or successor SRR/MyoPS architecture diagrams

At minimum, the planner must visually read the Project background diagrams corresponding to the canonical repository references `images/SRR-v2.png`, `images/SRR-v2.5.png`, and `images/SRR-v3.png`.

The repository `images/` paths remain canonical filenames and version references. They are not the required GPT visual-reading entrypoint, because GitHub connector access to `.png` files may expose only blob, SHA, or base64 metadata instead of a stable multimodal visual input.

Do not require GPT to open repository PNG files through the GitHub connector, and do not treat GitHub connector binary metadata as visual reading. If the Project background is missing a diagram, the user may either add the corresponding image to the ChatGPT Project background materials or upload it into the current conversation.

A link, filename listing, GitHub blob SHA, base64 metadata, old chat screenshot reference, or prior natural-language summary is not enough unless the image content is actually read through the current thread's visual channel.

## Required route statement before planning

Before writing any new milestone, task prompt, or route judgment, the planner must explicitly state the recovered route objective in its own words. At minimum it must cover:

1. availability-aware modality-specific input handling with no zero-filling semantics;
2. semantic representation retrieval bank with shared, modality-private, optional interaction dictionaries, and real train/OOF prototypes;
3. anatomy-guided scar/edema lesion proposal using union/LV/RV anatomy, uncertainty, distance maps, and segmentation-context evidence;
4. pathology-specific soft-ROI refinement for scar and edema;
5. explicit training objectives for proposal, refinement, negative-space/hard-negative control, anatomy prior/ROI, dictionary/prototype regularization, and no-T2-safe edema supervision;
6. nnU-Net or another strong segmenter may provide anchor/context/evidence, but SRR must not be reduced to an optional post-processing add-on or a purely abstract competitor.

## Blocking rule

If the planner cannot access or visually interpret the `v2` and later diagrams from ChatGPT Project background materials or images uploaded into the current conversation, it must stop before writing milestones or Codex goals. The response must explicitly report `BLOCKED_PROJECT_ROUTE_DIAGRAMS_UNAVAILABLE`, the missing versions, the canonical repository references for those versions, and the exact user action needed: add the diagrams to the ChatGPT Project background materials or upload them into the current conversation.

Do not silently continue from memory, prior summaries, or a partial text description when the diagrams are unavailable.

## Evidence to record in new milestones

Any new SRR MyoPS milestone after M4 must include either:

- route-bootstrap fields such as:

```yaml
diagram_source: "ChatGPT Project background materials"
diagram_versions_read: ["SRR-v2", "SRR-v2.5", "SRR-v3"]
canonical_repo_paths: ["images/SRR-v2.png", "images/SRR-v2.5.png", "images/SRR-v3.png"]
visual_read_status: "READ_FROM_PROJECT_BACKGROUND"
```

- an equivalent result artifact proving the same Project-background visual-read status and version coverage; or
- a result artifact such as `srr_v3_fidelity_contract.md` / `architecture_component_trace.csv` that maps the diagram modules to code paths, runtime evidence, and unresolved gaps.

A reviewer must treat missing `diagram_versions_read`, missing `visual_read_status`, reliance only on repository filenames/GitHub blob metadata/base64 metadata/old summaries, or claimed visual image reading from GitHub connector without actual visual input as a route-definition blocker for new SRR/MyoPS planning tasks.
