# M10 Controller Packet Manifest

Task key: `20260711_srr_v3_m10_complete_mechanism_repair`

Packet state: `NEEDS_MONITOR`

## Files

| Path | Purpose |
| --- | --- |
| `result.md` | Controller result and blocker summary. |
| `controller_context.json` | Machine-readable bootstrap context and read receipts. |
| `controller_ledger.csv` | Append-only controller phase ledger. |
| `controller_bootstrap_snapshot.md` | Human-readable hard-gate snapshot. |
| `controller_resume_bootstrap.md` | Historical resumed bootstrap after prerequisite repair. |
| `implementation_snapshot.md` | Confirms no implementation occurred. |
| `finalizer_state.json` | Deterministic terminal accounting for the blocked prerequisite packet. |
| `validator_report.md` | Validation command report. |
| `controller_report.md` | Controller decision report. |
| `completion_check.md` | Completion state and gate table. |
| `review_request.md` | Request for later separate read-only review of the blocked packet. |
| `prerequisite_repair.md` | Later integration-layer repair note for the prerequisite blocker; not runtime completion evidence. |
| `subagents/m10_shared_architecture_executor_prompt.md` | Wave 1 executor handoff prompt. |
| `subagents/m10_myops_training_executor_prompt.md` | Wave 2 executor handoff prompt. |
| `wave1_launch_receipt.json` | Controller receipt for serial wave 1 worker launch. |
| `wave1_merge_receipt.md` | Controller verification and merge/freeze decision for wave 1. |
| `wave2_launch_receipt.json` | Controller receipt for serial wave 2 worker launch. |
| `wave2_monitor_receipt.md` | Controller receipt for wave 2 monitor state and terminal failure update. |
| `wave2_terminal_failure_receipt.md` | Terminal Slurm accounting, log failure cause, dependency repair, and fail-closed aggregation receipt. |
| `wave2_startup_failed_jobs.csv` | Permanent zero-credit accounting for original startup-failed Wave 2 jobs. |
| `wave2_env_preflight.sh` | Slurm compute-node environment preflight wrapper for the authorized replacement attempt. |
| `wave2_replacement_preflight_receipt.md` | Replacement authorization, hashes, preflight command, and preflight/submission receipt. |
| `wave2_replacement_job_ledger.csv` | Replacement job ledger with old/new job IDs, preflight evidence, hashes, dependencies, partition, runtime root, and log path. |
| `wave2_partition_race_submission.json` | Three-partition formal race submission receipt and job graph. |
| `wave2_partition_race_watcher_state.json` | Watcher evidence selecting `volta-gpu` and cancelling pending mirrors. |
| `wave2_partition_race_finalizer_submission.json` | New afterany finalizer receipt for the race graph. |
| `wave2_partition_race_job_ledger.csv` | Per-partition race ledger with superseded jobs, preflight IDs, dependencies, runtime roots, and credit policy. |
| `wave2_partition_race_watcher.py` | Result-scope watcher used to cancel pending loser mirrors after a D0 winner starts. |
| `finalize_wave2_partition_race.py` | Result-scope aggregation helper that will aggregate only the winning partition runtime root. |
| `wave2_partition_race_retry2_submission.json` | Htz/A100 retry race receipt after V100 hardware incompatibility. |
| `wave2_partition_race_retry2_finalizer_submission.json` | New afterany finalizer receipt for the htz/A100 retry graph. |
| `wave2_partition_race_retry2_job_ledger.csv` | Htz/A100 retry ledger with preflight IDs, dependencies, runtime roots, and credit policy. |
| `wave2_partition_race_retry3_submission.json` | User-authorized htz/a100/volta retry receipt retaining active htz/a100 jobs and adding a preflight-gated volta mirror. |
| `wave2_partition_race_retry3_finalizer_submission.json` | New afterany finalizer receipt for the retry3 graph. |
| `wave2_partition_race_retry3_job_ledger.csv` | Retry3 ledger with htz/a100 pending jobs, volta failed preflight, cancelled volta afterok chain, runtime roots, and credit policy. |
| `wave2_partition_race_retry3_watcher_state.json` | Local active retry3 watcher state path; it may continue changing while watcher `58701289` runs and is not completion evidence. |
| `wave2_partition_race_retry3_volta_failure.md` | Human-readable zero-credit volta preflight failure receipt. |
| `wave2_partition_race_retry3_monitor_20260712T125305Z.md` | First formal two-hour pending-only monitor checkpoint for retry3; not completion evidence. |
| `wave2_partition_race_retry3_finalization.json` | Retry3 terminal aggregation replay result; fail-closed `NEEDS_EVIDENCE` after htz D0 `58701196` failed. |
| `wave2_partition_race_retry4_submission.json` | Repaired-code retry4 formal submission receipt after htz preflight `58706079` completed `0:0`. |
| `wave2_partition_race_retry4_finalizer_submission.json` | Retry4 afterany finalizer receipt for job `58706300`. |
| `wave2_partition_race_retry4_job_ledger.csv` | Retry4 ledger recording old/new job IDs, repair reason, preflight command/exit code, hashes, dependencies, runtime root, and log paths. |
| `wave2_partition_race_retry4_monitor_20260712T141110Z.md` | Current retry4 monitor checkpoint showing D0 running and downstream/finalizer dependency-pending; not completion evidence. |
| `wave2_partition_race_retry4_finalization.json` | Local retry4 finalization replay; fail-closed `NEEDS_EVIDENCE` because D1 failed and no full chain completed. |
| `wave2_partition_race_retry4_terminal_d1_failure.md` | Retry4 terminal accounting: D0 completed, D1 logging failed, downstream cancelled, finalizer failed, and wrapper repair recorded. |
| `wave2_partition_race_retry5_submission.json` | D1-through-alignment replacement submission receipt after repaired-code preflight `58714000` and retained D0 verification. |
| `wave2_partition_race_retry5_finalizer_submission.json` | Retry5 afterany finalizer receipt for job `58714029`. |
| `wave2_partition_race_retry5_job_ledger.csv` | Retry5 ledger recording old/new job IDs, repair reason, preflight command/exit code, hashes, dependencies, runtime root, and log paths. |
| `wave2_partition_race_retry5_monitor_20260712T163737Z.md` | Current retry5 monitor checkpoint showing D1 running and downstream/finalizer dependency-pending; not completion evidence. |
| `wave2_partition_race_retry5_finalization.json` | Retry5 terminal aggregation replay; fail-closed `NEEDS_EVIDENCE` because D1 reached `OUT_OF_MEMORY(0:125)` and no full chain completed. |
| `wave2_partition_race_retry5_terminal_oom.md` | Retry5 terminal accounting receipt: D1 OOM at 64G, downstream cancelled, zero effective D1-through-alignment credit. |
| `wave2_partition_race_retry6_submission.json` | Retry6 D1-through-alignment replacement submission receipt after 96G preflight and retained D0 verification. |
| `wave2_partition_race_retry6_finalizer_submission.json` | Retry6 afterany finalizer receipt for job `58714640`. |
| `wave2_partition_race_retry6_job_ledger.csv` | Retry6 ledger recording old/new job IDs, OOM resource retry reason, preflight command/exit code, hashes, dependencies, runtime root, log paths, and `mem=96G`. |
| `wave2_partition_race_retry6_monitor_20260712T164736Z.md` | Current retry6 monitor checkpoint showing D1 running at 96G and downstream/finalizer dependency-pending; not completion evidence. |
| `wave2_partition_race_retry6_finalization.json` | Retry6 terminal aggregation replay; fail-closed `NEEDS_EVIDENCE` because D1 reached `OUT_OF_MEMORY(0:125)` and no full chain completed. |
| `wave2_partition_race_retry6_terminal_oom.md` | Retry6 terminal accounting receipt: D1 OOM at 96G, downstream cancelled, finalizer argv failure, zero effective D1-through-alignment credit. |
| `wave2_partition_race_retry7_submission.json` | Retry7 D1-through-alignment replacement submission receipt after 128G preflight and retained D0 verification. |
| `wave2_partition_race_retry7_finalizer_submission.json` | Retry7 afterany finalizer receipt for job `58719841` with corrected aggregation-command string. |
| `wave2_partition_race_retry7_job_ledger.csv` | Retry7 ledger recording old/new job IDs, OOM resource retry reason, preflight command/exit code, hashes, dependencies, runtime root, log paths, and `mem=128G`. |
| `wave2_partition_race_retry7_monitor_20260712T171037Z.md` | Current retry7 monitor checkpoint showing D1 running at 128G and downstream/finalizer dependency-pending; not completion evidence. |
| `wave2_partition_race_retry7_finalization.json` | Retry7 terminal aggregation replay; fail-closed `NEEDS_EVIDENCE` because D1 reached `OUT_OF_MEMORY(0:125)` and no full chain completed. |
| `wave2_partition_race_retry7_terminal_oom.md` | Retry7 terminal accounting receipt: D1 OOM at 128G, downstream cancelled, zero effective D1-through-alignment credit. |
| `wave2_partition_race_retry8_submission.json` | Retry8 D1-through-alignment replacement submission receipt after 160G `gpu_access_patron` preflight and retained D0 verification. |
| `wave2_partition_race_retry8_finalizer_submission.json` | Retry8 afterany finalizer receipt for job `58720464`. |
| `wave2_partition_race_retry8_job_ledger.csv` | Retry8 ledger recording old/new job IDs, OOM resource retry reason, preflight command/exit code, hashes, dependencies, runtime root, log paths, `qos=gpu_access_patron`, and `mem=160G`. |
| `wave2_partition_race_retry8_monitor_20260712T174444Z.md` | Current retry8 monitor checkpoint showing D1 running at 160G and downstream/finalizer dependency-pending; not completion evidence. |
| `wave2_partition_race_retry8_finalization.json` | Retry8 terminal aggregation replay; fail-closed `NEEDS_EVIDENCE` because D1 reached `OUT_OF_MEMORY(0:125)` and no full chain completed. |
| `wave2_partition_race_retry8_terminal_oom.md` | Retry8 terminal accounting receipt: D1 OOM at 160G `gpu_access_patron`, downstream cancelled, zero effective D1-through-alignment credit. |
| `wave2_partition_race_retry9_submission.json` | Retry9 D1-through-alignment replacement submission receipt after 1200G `gpu_access_patron` preflight and retained D0 verification. |
| `wave2_partition_race_retry9_finalizer_submission.json` | Retry9 afterany finalizer receipt for job `58733769`. |
| `wave2_partition_race_retry9_job_ledger.csv` | Retry9 ledger recording old/new job IDs, OOM resource retry reason, preflight command/exit code, hashes, dependencies, runtime root, log paths, `qos=gpu_access_patron`, and `mem=1200G`. |
| `wave2_partition_race_retry9_monitor_20260712T182952Z.md` | Current retry9 monitor checkpoint showing D1 running at 1200G and downstream/finalizer dependency-pending; not completion evidence. |
| `wave2_partition_race_retry9_monitor_20260712T191138Z.md` | Retry9 progress monitor showing D1 crossed prior OOM windows and wrote validation checkpoints 1666 and 3332; not completion evidence. |
| `wave2_partition_race_retry9_monitor_20260712T194643Z.md` | Retry9 running monitor showing D1 still running at 01:18:54 with validation checkpoints through step 6664; not completion evidence. |
| `wave2_partition_race_retry9_monitor_20260712T201919Z.md` | Retry9 running monitor showing D1 still running at 01:51:31 with validation checkpoints through step 8330; not completion evidence. |
| `wave2_partition_race_retry9_monitor_20260712T210229Z.md` | Retry9 D1 monitor showing the run crossed the 9000-second D1 minimum train-loop floor and wrote validation checkpoints through step 11662; not completion evidence. |
| `wave2_partition_race_retry9_monitor_20260712T220154Z.md` | Retry9 D1 monitor showing final checkpoint and training logs exist while Slurm still reports D1 running; not completion evidence. |
| `wave2_partition_race_retry10_submission_monitor.md` | Retry9 undertrained terminal accounting, same-scope runtime-cap repair, retry10 preflight/submission monitor; not completion evidence. |
| `wave2_partition_race_retry10_submission.json` | Retry10 submission receipt with D0 retained and D1-through-alignment replacement job IDs. |
| `wave2_partition_race_retry10_job_ledger.csv` | Retry10 ledger recording old/new job IDs, undertraining retry reason, preflight, hashes, dependencies, runtime root, and log paths. |
| `wave2_partition_race_retry10_finalizer_submission.json` | Retry10 afterany finalizer receipt for job `58743452`. |
| `wave2_partition_race_retry10_monitor_20260712T234010Z.md` | Retry10 D1 first-checkpoint monitor showing D1 running with validation checkpoints 1666 and 3332; not completion evidence. |
| `wave2_partition_race_retry10_monitor_20260713T002802Z.md` | Retry10 D1 monitor showing D1 running with validation checkpoints through step 6664; not completion evidence. |
| `wave2_partition_race_retry10_monitor_20260713T013659Z.md` | Retry10 D1 monitor showing D1 crossed the 9000-second D1 minimum-time floor and wrote checkpoints through step 11662; not completion evidence. |
| `wave2_partition_race_retry10_monitor_20260713T015839Z.md` | Retry10 D1 monitor showing D1 running with validation checkpoints through step 13328; not completion evidence. |
| `wave2_partition_race_retry10_monitor_20260713T023314Z.md` | Retry10 D1 monitor showing D1 running with validation checkpoints through step 15000; not completion evidence. |
| `wave2_partition_race_retry10_monitor_20260713T030523Z.md` | Retry10 D1 monitor showing D1 running with validation checkpoints through step 16660; not completion evidence. |
| `wave2_partition_race_retry10_monitor_20260713T034453Z.md` | Retry10 D1 monitor showing D1 running with validation checkpoints through step 18326; not completion evidence. |
| `wave2_partition_race_retry10_terminal_oom.md` | Retry10 terminal accounting packet: D1 `58743282` reached `OUT_OF_MEMORY(0:125)` after `06:09:20`, D2-through-alignment did not run, and controller state is `NEEDS_EVIDENCE`; finalizer classifies further retry as requiring revision first. |
| `wave2_partition_race_retry11_submission.json` | Retry11 htzhulab replacement submission receipt after gate-usage evidence logging repair and compute preflight `58775059`. |
| `wave2_partition_race_retry11_watcher_state.json` | Retry11 routing decision: htzhulab was the only partition with preflight exit `0` before formal submission; a100 was cancelled pending and volta failed V100 CUDA kernel probe. |
| `wave2_partition_race_retry11_job_ledger.csv` | Retry11 ledger recording old/new job IDs, repair reason, preflight command/exit code, hashes, dependencies, runtime root, and log paths. |
| `wave2_partition_race_retry11_finalizer_submission.json` | Retry11 afterany finalizer receipt for job `58775071`. |
| `wave2_partition_race_retry11_monitor_20260713T060230Z.md` | Retry11 monitor packet showing D1 `58775065` running and downstream stages dependency-pending; not completion evidence. |
| `wave2_partition_race_retry11_monitor_20260713T061121Z.md` | Retry11 first-checkpoint monitor showing D1 `58775065` running, checkpoint `1666`, one-batch overfit pass, and low early RSS; not completion evidence. |
| `wave2_partition_race_retry11_monitor_20260713T062448Z.md` | Retry11 Step3332 monitor showing D1 `58775065` running with checkpoints through `3332` and low RSS; not completion evidence. |
| `finalizer_state.json` | Retry10 finalizer terminal accounting with `final_state=RUNTIME_FAILURE`, `failure_class=OUT_OF_MEMORY_NEEDS_REVISION`, `suggested_next_state=NEEDS_REVISION`, and `retryable=false`. |
| `care_milestone_finalizer_58743452.log` | Retry10 finalizer log for Slurm job `58743452`. |
| `executors/m10_myops_training_executor/` | Wave 2 executor monitor packet; not completion evidence. |
| `subagents/reviewer_prompt.md` | Reviewer handoff prompt for this blocked packet only. |
| `mapper_report_draft.md` | Mapper draft non-run receipt. |
| `architecture_delta_draft.md` | Draft architecture delta after wave 1 merge. |
| `mapper_report_final.md` | Mapper final non-run receipt. |
| `architecture_delta_final.md` | Confirms no M10 architecture delta was applied. |
| `executor_waves/README.md` | Executor wave non-launch receipt. |

## Exclusions

`review.md` is intentionally absent. Wave 2 terminal failure files are not successful completion evidence. No checkpoints, predictions, NIfTI outputs, upload zips, raw data, large logs, secrets, environment dumps, or runtime result trees are included.
