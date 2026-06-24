# Artifact Manifest 20260621 SRR Goal

task: `prompts/tasks/20260621_srr_goal.md`
result: `results/20260621_srr_goal/result.md`
review: `results/20260621_srr_goal/review.md`

## Goal Tracking Artifacts

- `results/20260621_srr_goal/progress.md`: current phase, commands, job IDs, gate decisions.
- `results/20260621_srr_goal/result.md`: goal-level execution report.
- `results/20260621_srr_goal/final_status.md`: final goal status, jobs, metrics, diagnostics, and next-task recommendation.
- `results/20260621_srr_goal/MANIFEST.md`: this manifest.
- `results/20260621_srr_goal/coordinator/`: pre-existing coordinator scripts/prompts/logs preserved by this session.

## Subtask Artifacts

- `results/20260621_srr_spec/result.md`: spec execution report, final status `GO_FOLD0`.
- `results/20260621_srr_spec/MANIFEST.md`: spec artifact index.
- `results/20260621_srr_spec/architecture_contract.md`: SRR-MyoPS-Lite contract.
- `results/20260621_srr_spec/architecture_contract.yaml`: machine-readable contract.
- `results/20260621_srr_spec/test_summary.md`: spec verification evidence.
- `results/20260621_srr_fold0/variants/conditional_dualhead_control/`: preflight artifacts, short wiring job `55720659`, and corrected runtime-guarded Slurm job `55723114`.
- `results/20260621_srr_fold0/variants/srr_minimal/`: preflight artifacts, short wiring job `55720658`, and corrected runtime-guarded Slurm job `55723115`.
- `results/20260621_srr_fold0/result.md`: fold0 execution report, final status `REVISE_ROUTING`.
- `results/20260621_srr_fold0/MANIFEST.md`: fold0 artifact index.
- `results/20260621_srr_fold0/decision.md`: fold0 decision `REVISE_ROUTING`.
- `results/20260621_srr_fold0/metrics_summary.md`: combined fold0 metrics and decision reasons.
- `results/20260621_srr_fold0/subgroup_metrics.csv`: combined subgroup Dice/HD/HD95 metrics.
- `results/20260621_srr_fold0/component_hd_by_case.csv`: combined component/HD case diagnostics.
- `results/20260621_srr_fold0/retrieval_usage.csv`: combined SRR usage rows.
- `results/20260621_srr_fold0/retrieval_usage.md`: per-expert retrieval usage summary.
- `scripts/training/run_srr_myops_fold0.py`: patched runtime guard defaults and summary fields to prevent accidental 20k-step under-budget completion.
- `results/20260621_srr_goal/coordinator/monitor_fold0_jobs.sh`: tmux monitor for jobs `55723114,55723115`; runs `report_srr_fold0.py` after completion.
- `results/20260621_srr_goal/coordinator/monitor_fold0_jobs.log`: live monitor log for the corrected fold0 jobs.
- `jobs/src/run_srr_myops_fold0_conditional_long.sh`: unsubmitted backup long-run entrypoint writing to `results/20260621_srr_fold0_long/`.
- `jobs/src/run_srr_myops_fold0_srr_long.sh`: unsubmitted backup long-run entrypoint writing to `results/20260621_srr_fold0_long/`.
- `/overflow/htzhu/mingcheng_new/temp/care_worktrees/20260621_cine_retrieval/results/20260621_cine_retrieval/result.md`: Cine secondary-line result in independent worktree, decision `REVISE_GEOMETRY`.
- `/overflow/htzhu/mingcheng_new/temp/care_worktrees/20260621_cine_retrieval/results/20260621_cine_retrieval/MANIFEST.md`: Cine secondary-line artifact index.

## Final Gate

- goal status: `MYOPS_REVISE_SRR`
- spec gate: `GO_FOLD0`
- fold0 gate: `REVISE_ROUTING`
- Cine secondary line: `REVISE_GEOMETRY`
- not executed: ablation, fold expansion, validation submission, upload package, external upload.
