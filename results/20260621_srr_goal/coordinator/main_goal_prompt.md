You are a delegated Codex execution session for CARE.

Working directory: /overflow/htzhu/CARE.

Primary entrypoint:

- prompts/tasks/20260621_srr_goal.md

Required first reads before task action:

- AGENTS.md
- prompts/AGENT_RULES.md
- prompts/CHATGPT_RULES.md
- prompts/tasks/20260621_srr_goal.md
- prompts/tasks/20260621_srr_spec.md
- docs/notes/deep_research/Result3.pdf
- docs/notes/deep_research/Result4.pdf
- docs/notes/20260620_r2_deep_research_assessment.md
- TODO.md
- docs/plans/care_myocardium_plan_registry_rules.md
- docs/plans/laneA_round03plus_controller_myops_modality_aware_src_plan.md

Execute the main MyoPS SRR path literally through the handoff protocol.

Start with prompts/tasks/20260621_srr_spec.md. Extract Result4 to results/20260621_srr_spec/Result4.txt as the task requires. Build the Result4 SRR architecture contract and minimal first-party skeleton/tests. Write results/20260621_srr_spec/{result.md,MANIFEST.md,architecture_contract.md,architecture_contract.yaml,test_summary.md}. Only continue to prompts/tasks/20260621_srr_fold0.md if the spec result explicitly reaches GO_FOLD0.

Do not run the Cine retrieval task in this session; a separate worktree/session owns that lower-priority line. You may coordinate through files under results/20260621_srr_goal/.

Keep all single Slurm jobs <= 08:00:00. If fold0 is reached, use up to two independent single-GPU jobs for conditional_dualhead_control and srr_minimal, with 4-6 hours effective training budget rather than a tiny smoke. Default to htzhulab unless queue evidence justifies fallback. Do not submit validation packages or upload anything.

Hard constraints:

- no network, no external upload, no external data or new weights
- no validation submission or upload-ready package
- do not patch third_party/MyoPS-Net, third_party/U-MyoPS, or old baseline defaults
- do not treat no-T2 cases as edema hard negatives
- do not skip Result4 architecture contract or fold0/ablation/expand gates
- keep output/cache/checkpoint/prediction paths task-scoped, variant-scoped, fold-scoped, and checkpoint/config-scoped

Keep progress current in results/20260621_srr_goal/progress.md and write/update the goal MANIFEST as needed. Include job IDs, commands, logs, stop reasons, and gate decisions.
