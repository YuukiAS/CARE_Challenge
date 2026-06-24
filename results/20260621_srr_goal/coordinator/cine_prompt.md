You are a delegated Codex execution session for the CARE Cine secondary line.

Working directory: this session should run in an independent git worktree, not /overflow/htzhu/CARE, to avoid concurrent edits with the MyoPS mainline.

Primary entrypoint:

- prompts/tasks/20260621_cine_retrieval.md

Required first reads before task action:

- AGENTS.md
- prompts/AGENT_RULES.md
- prompts/tasks/20260621_cine_retrieval.md
- docs/notes/deep_research/Result3.pdf
- docs/notes/deep_research/Result4.pdf
- prompts/Baseline_report.md
- results/20260620_cinema_adapter_pilot/result.md
- results/20260620_cinema_adapter_pilot/MANIFEST.md
- results/20260620_cinema_adapter_pilot/review.md
- docs/plans/laneB_round03plus_controller_cinemyops_hosted_topology_motion_plan.md

Execute prompts/tasks/20260621_cine_retrieval.md literally through the handoff protocol, but do not block the MyoPS SRR mainline.

First establish the reference/geometry contract. Extract Result4 Cine/temporal retrieval relevant text to results/20260621_cine_retrieval/Result4_cine_excerpt.txt as required. Confirm reference frame semantics and inverse geometry safety before any training. If reference or geometry is unclear, stop cleanly with result.md, MANIFEST.md, reference_geometry_contract.md, and decision.md.

If training gates pass, use up to two independent single-GPU jobs for reference_frame_control and temporal_selective_retrieval, each <= 08:00:00 with 4-6 hours effective training budget after one-batch/tiny-overfit gates. Default to htzhulab unless queue evidence justifies fallback.

Hard constraints:

- no network, no external upload, no validation submission, no upload-ready package
- do not revive the old single-frame wrapper as the official Cine story
- do not compute Dice on non-reference frames as if their labels were frame-wise GT
- do not rewrite the full CineMyoPS motion-registration pipeline
- do not overwrite existing CineMA/nnU-Net/CineMyoPS predictions or caches

Write results/20260621_cine_retrieval/{result.md,MANIFEST.md,decision.md,reference_geometry_contract.md,metrics_summary.md} and the required CSV diagnostics when applicable. Also append a short status line to results/20260621_srr_goal/progress.md if safe to do so; otherwise keep all Cine status in the Cine result directory.
