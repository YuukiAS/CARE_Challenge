# Completion Check

当前 goal 没有完成最终评价/aggregation/validator，但已经不是“训练没跑”或“四个模型都失败”。截至当前 live Slurm/accounting 复查：M3 fold2/fold3 已在 `61220581 / htzhulab / g1807htzh01` interactive allocation 完成；M0R fold2 job `61565286` 完成；M0R fold3 原 pending job `61565287` 被取消后已在 interactive allocation 完成；M1 替换后的 lane-level job `61576324` 已完成 fold2+fold3。M2 仍是外部 Google Drive 权重资产门，不能用假 job 代替。

- controller_verification_decision: `ACTIVE_CONTINUATION`
- scientific_decision: `CONTROLLER_ACTIVE_CONTINUATION`
- previous_decision_superseded: `OPERATIONALLY_BLOCKED_EXISTING_INTERACTIVE_LOST`
- usable_existing_interactive_allocation: `true`
- existing_interactive_job_id: `61220581`
- old_M0_classification: `HIGH_LR_SHORT_FINETUNE_NEGATIVE`
- formal_lane_training_started: `true`
- formal_lane_training_status: `M0R_M1_M3_FOLD2_FOLD3_COMPLETE_M2_ASSET_GATED`
- queue_jobs_submitted_by_this_goal: `true`
- interactive_steps_started_by_this_goal: `true`
- active_interactive_lane: `none_currently_known`
- active_interactive_launcher_pid: `none_currently_known`
- submitted_queue_jobs: `61565286,61565287,61565288,61565289,61576324`
- cancelled_for_replacement: `61565288,61565289`
- active_m1_lane_job: `none_completed_61576324`
- completed_training_jobs: `61565286,61576324`
- completed_interactive_training_steps: `M3_fold2,M3_fold3,M0R_fold3`
- interactive_takeover_monitor_pid: `4185840_exited_M1_QUEUE_RUNNING_NO_TAKEOVER`
- interactive_takeover_monitor_state: `results/20260801_care_target_domain_race_gap_closure/interactive_takeover_monitor_state.json`
- m2_status: `ASSET_CHECK_REQUIRED_NO_FAKE_JOB`
- remaining_required_work: `checkpoint_reload_hash_audit,inner_full_volume_selection,outer_replay,aggregation,atlas,mapper,strict_final_validator,final_commit_push,notification`
- validator_required_before_final_completion: `scripts/validation/validate_target_domain_race_gap_closure.py --phase final`
