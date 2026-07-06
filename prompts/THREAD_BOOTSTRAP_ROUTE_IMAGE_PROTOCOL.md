# Thread Bootstrap Route Image Protocol

This protocol is mandatory for every new GPT/ChatGPT planning thread before it writes or revises CARE MyoPS/Cine milestones, Codex goals, handoffs, or route decisions.

## Purpose

The SRR route is defined by the repository diagrams, not by a loose natural-language memory of previous chats. Future GPT threads must first recover the diagram intent, then write milestones. This prevents the planner from mistaking SRR-v3 for a plain nnU-Net fallback, a generic post-processing block, or an abstract two-branch competition.

## Required local image acquisition

After reading the repository, the planner must locate the repository `images/` directory and download or copy every SRR design diagram at version `v2` or later to local working storage. This includes, when present, diagrams named or described as:

- `v2`
- `v2.5`
- `v3`
- later versions such as `v3.1`, `v4`, or successor SRR/MyoPS architecture diagrams

The local-copy step is required even if the user pasted a screenshot in the current chat, because the repo copy is the auditable source for route planning.

A local Codex/GPT environment should use an explicit image staging directory, for example:

```bash
mkdir -p /tmp/care_srr_route_images
git ls-files 'images/*' | grep -Ei 'v2|v2\.5|v3|srr|myops' > /tmp/care_srr_route_images/source_files.txt
while IFS= read -r p; do cp "$p" /tmp/care_srr_route_images/; done < /tmp/care_srr_route_images/source_files.txt
find /tmp/care_srr_route_images -maxdepth 1 -type f -print | sort
```

When operating through a GitHub connector rather than a checked-out workspace, the planner must fetch the raw image files or otherwise make local copies before planning. A link, filename listing, or prior chat screenshot alone is not enough unless the image contents are actually read in the current thread.

## Required route statement before planning

Before writing any new milestone, task prompt, or route judgment, the planner must explicitly state the recovered route objective in its own words. At minimum it must cover:

1. availability-aware modality-specific input handling with no zero-filling semantics;
2. semantic representation retrieval bank with shared, modality-private, optional interaction dictionaries, and real train/OOF prototypes;
3. anatomy-guided scar/edema lesion proposal using union/LV/RV anatomy, uncertainty, distance maps, and segmentation-context evidence;
4. pathology-specific soft-ROI refinement for scar and edema;
5. explicit training objectives for proposal, refinement, negative-space/hard-negative control, anatomy prior/ROI, dictionary/prototype regularization, and no-T2-safe edema supervision;
6. nnU-Net or another strong segmenter may provide anchor/context/evidence, but SRR must not be reduced to an optional post-processing add-on or a purely abstract competitor.

## Blocking rule

If the planner cannot locate the `images/` directory, cannot copy/download the diagrams, cannot read the diagrams, or cannot determine the content of `v2` and later diagrams, it must stop before writing milestones or Codex goals. The response must explicitly report a blocked state, the missing/failed image paths, and the exact user action needed, such as uploading the diagrams, fixing repository access, or confirming an alternate source.

Do not silently continue from memory, prior summaries, or a partial text description when the diagrams are unavailable.

## Evidence to record in new milestones

Any new SRR MyoPS milestone after M4 must include either:

- a `diagram_source` or equivalent field listing the local copied diagram paths and versions used; or
- a result artifact such as `srr_v3_fidelity_contract.md` / `architecture_component_trace.csv` that maps the diagram modules to code paths, runtime evidence, and unresolved gaps.

A reviewer must treat missing diagram-source evidence as a route-definition blocker for new SRR/Myops planning tasks.
