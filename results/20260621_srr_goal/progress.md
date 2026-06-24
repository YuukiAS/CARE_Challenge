# Progress 20260621 SRR Goal

Updated: 2026-06-22

## Current Phase

- Phase 1 main SRR spec: completed with `GO_FOLD0`.
- Phase 2 fold0: completed with `REVISE_ROUTING`.
- Cine retrieval: executed in independent worktree `/overflow/htzhu/mingcheng_new/temp/care_worktrees/20260621_cine_retrieval`; stopped before training with `REVISE_GEOMETRY`.
- Validation submission/upload: not run.

## Spec Task

- task: `prompts/tasks/20260621_srr_spec.md`
- result: `results/20260621_srr_spec/result.md`
- manifest: `results/20260621_srr_spec/MANIFEST.md`
- gate: `GO_FOLD0`

## Commands

- `pdftotext docs/notes/deep_research/Result4.pdf results/20260621_srr_spec/Result4.txt`
- `./envs/env_CARE/bin/python -m unittest discover -s src/care_myocardium/tests -p 'test_srr_*.py'`
- `./envs/env_CARE/bin/python scripts/training/run_srr_myops.py --smoke --output-json results/20260621_srr_spec/one_batch_smoke.json`
- `./envs/env_CARE/bin/python scripts/training/run_srr_myops_fold0.py ... --skip-export` preflight passed for both fold0 variants.
- `./envs/env_CARE/bin/python -m py_compile scripts/evaluation/report_srr_fold0.py`

## Slurm Jobs

- `55720659`: `conditional_dualhead_control`, script `jobs/src/run_srr_myops_fold0_conditional.sh`, `htzhulab`, `06:00:00`.
- `55720658`: `srr_minimal`, script `jobs/src/run_srr_myops_fold0_srr.sh`, `htzhulab`, `06:00:00`.
- `55723114`: corrected `conditional_dualhead_control` formal runtime-guarded rerun, `htzhulab`, `06:00:00`, `max_runtime_seconds=16200`, `max_steps=500000`.
- `55723115`: corrected `srr_minimal` formal runtime-guarded rerun, `htzhulab`, `06:00:00`, `max_runtime_seconds=16200`, `max_steps=500000`.

Verified current state:

- Initial jobs `55720659` and `55720658` completed successfully but stopped by `max_steps` in 12-19 minutes; they are retained as wiring evidence, not final fold0 budget evidence.
- `sacct -j 55720659,55720658 --format=JobID,JobName,State,ExitCode,Elapsed,AllocTRES%50 -P` showed both jobs `RUNNING` on `2026-06-21` after submission.
- `squeue -j 55720659,55720658 -o '%.18i %.24j %.2t %.10M %.20R'` showed both jobs running on `g1807htzh01`.
- Runtime logs:
  - `logs/SRRCondF0_55720659_20260621_191600.log`
  - `logs/SRRMinF0_55720658_20260621_191600.log`

## Fold0 Report Artifacts Prepared

- `results/20260621_srr_fold0/setup.md`
- `scripts/evaluation/report_srr_fold0.py`
- `results/20260621_srr_fold0/result.md`
- `results/20260621_srr_fold0/MANIFEST.md`
- `results/20260621_srr_fold0/decision.md`: `REVISE_ROUTING`
- `results/20260621_srr_fold0/metrics_summary.md`
- `results/20260621_srr_fold0/subgroup_metrics.csv`
- `results/20260621_srr_fold0/component_hd_by_case.csv`
- `results/20260621_srr_fold0/retrieval_usage.csv`
- `results/20260621_srr_fold0/retrieval_usage.md`

## Cine Secondary Line

- worktree: `/overflow/htzhu/mingcheng_new/temp/care_worktrees/20260621_cine_retrieval`
- result: `/overflow/htzhu/mingcheng_new/temp/care_worktrees/20260621_cine_retrieval/results/20260621_cine_retrieval/result.md`
- decision: `/overflow/htzhu/mingcheng_new/temp/care_worktrees/20260621_cine_retrieval/results/20260621_cine_retrieval/decision.md`
- status: `REVISE_GEOMETRY`
- training jobs: none submitted
- reason: frame0 ED/reference evidence is plausible, but strict frame0-label metadata matched only `59/64` cases and geometry-aware crop/inverse mapping is not proven.

## Latest Poll

- `2026-06-21 19:57` local poll: corrected jobs `55723114` and `55723115` were both `RUNNING` on `g1807htzh01` at ~18 minutes elapsed.
- `2026-06-21 20:09` local poll: corrected jobs `55723114` and `55723115` were both `RUNNING` on `g1807htzh01` at ~30 minutes elapsed; `conditional_dualhead_control` checkpoint refreshed at `20:02`, final summaries still stale.
- `2026-06-21 20:39` local poll: corrected jobs `55723114` and `55723115` were both `RUNNING` on `g1807htzh01` at ~60 minutes elapsed; checkpoints refreshed during the corrected runs, final summaries still stale.
- `2026-06-21 21:39` local poll: corrected jobs `55723114` and `55723115` were both `RUNNING` on `g1807htzh01` at ~2 hours elapsed; `srr_minimal` checkpoint refreshed at `21:18`, final summaries still stale.
- `2026-06-21 22:40` local poll: corrected jobs `55723114` and `55723115` were both `RUNNING` on `g1807htzh01` at ~3 hours elapsed; final summaries still stale.
- `2026-06-21 20:33` local poll: corrected jobs `55723114` and `55723115` were both `RUNNING` on `g1807htzh01` at ~53 minutes elapsed. Node-level `ps` confirmed both Python commands include `--max-steps 500000` and `--max-runtime-seconds 16200`, so they are not the prior 20k-step short path.
- `2026-06-22 00:10` local poll: corrected jobs completed cleanly. `55723114` completed in `04:06:08` with stop reason `max_steps`; `55723115` completed in `04:31:04` with stop reason `max_runtime_seconds`.

## Runtime Guard Follow-up

- `scripts/training/run_srr_myops_fold0.py` now defaults `--max-steps` to `1000000`, supports `--out-root`, and records `budget_status` plus runtime guard settings in `summary.json`.
- Added unsubmitted backup long-run wrappers:
  - `jobs/src/run_srr_myops_fold0_conditional_long.sh`
  - `jobs/src/run_srr_myops_fold0_srr_long.sh`
- No duplicate long jobs were submitted because corrected jobs `55723114` and `55723115` already provided the formal fold0 evidence with `--max-steps 500000`.
- These backup long-run wrappers remain unsubmitted; fold0 decision uses the corrected completed jobs above.

## Gate Decision

Goal-level MyoPS status: `MYOPS_REVISE_SRR`.

Reason: fold0 decision is `REVISE_ROUTING`, not `GO_ABLATION`, so ablation and fold expansion were not started.

- `2026-06-22 00:15` monitor: jobs `55723114,55723115` finished; report_srr_fold0.py status `OK`. See `/overflow/htzhu/CARE/results/20260621_srr_goal/coordinator/monitor_fold0_jobs.log`.
