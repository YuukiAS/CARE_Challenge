# M8 Slurm Race Status

status: `M8_NEEDS_MONITOR_NO_REVIEW`

## First Race Attempt

The first AGENTS-compliant race replaced the initial single-partition a100-gpu job.

- cancelled pre-race job: `58080244`
- first htzhulab mirror array: `58080628`
- first a100-gpu mirror array: `58080627`
- first watcher job: `58080636`

Watcher evidence from `logs/SRRv3M8MyOPSRace_58080628_58080627.log` showed htzhulab tasks `0` and `1` started and a100 `58080627_[0-2]` was cancelled while pending.

The first htzhulab race failed quickly:

- `58080628_0`: `FAILED`, exit `1:0`, elapsed `00:01:39`
- `58080628_1`: `FAILED`, exit `1:0`, elapsed `00:01:38`
- `58080628_2`: `FAILED`, exit `1:0`, elapsed `00:00:52`

All three logs showed the same training-loop bug:

```text
KeyError: 'correction_opportunity_loss'
```

The fix was to route `m8_` variants through the same expanded SRR loss path as `m6_` and `m7_` variants in `scripts/training/run_srr_propref_myops_fold0.py`.

## Corrected Race Attempt

After removing stale failed runtime locks/partials under `results/20260707_srr_v3_m8_editor_grade_leaderboard_sprint/runtime/`, the corrected race was submitted:

- corrected htzhulab mirror array: `58081007`
- corrected a100-gpu mirror array: `58081025`
- corrected watcher job: `58081026`
- watcher log: `logs/SRRv3M8MyOPSRace_58081007_58081025.log`

Current `squeue -j 58081007,58081025,58081026` evidence:

- `58081007_0`: `RUNNING` on `htzhulab`, node `g1807htzh01`, elapsed at check `00:03:03`
- `58081007_1`: `RUNNING` on `htzhulab`, node `g1807htzh01`, elapsed at check `00:03:03`
- `58081007_[2]`: `PENDING (Resources)` on `htzhulab`
- `58081025`: absent from current `squeue` after cancellation
- `58081026`: absent from current `squeue` after watcher completion

Current `sacct -j 58081007,58081025,58081026` evidence:

- `58081007_0`: `RUNNING`, partition `htzhulab`, start `2026-07-07T00:18:35`
- `58081007_1`: `RUNNING`, partition `htzhulab`, start `2026-07-07T00:18:35`
- `58081007_[2]`: `PENDING`
- `58081025_[0-2]`: `CANCELLED by 397557`, partition `a100-gpu`, end `2026-07-07T00:19:10`
- `58081026`: `COMPLETED`, partition `spill`, elapsed `00:00:01`

Watcher log excerpt:

```text
2026-07-07T00:19:10.285172 watch_start htzhulab=58081007 a100=58081025
2026-07-07T00:19:10.346125 check=1 htzhulab=[('58081007_[2]', 'htzhulab', 'PENDING', '(Resources)'), ('58081007_1', 'htzhulab', 'RUNNING', 'g1807htzh01'), ('58081007_0', 'htzhulab', 'RUNNING', 'g1807htzh01')] a100=[('58081025_[0-2]', 'a100-gpu', 'PENDING', '(Priority)')]
2026-07-07T00:19:10.366487 cancel_a100 code=0 output=
```

## Lock Evidence

Runtime locks currently exist for:

- `m8_full_srr_context_arbitration_longrun`: claimed by job `58081023`, task `0`, partition `htzhulab`
- `m8_scar_precision_edema_safe_longrun`: claimed by job `58081024`, task `1`, partition `htzhulab`

The third variant has not started yet and remains pending monitor evidence.

## Task2 Supplemental Race

The initial array-level watcher cancelled the full a100 mirror after tasks `0` and `1` started on htzhulab. Because task `2` remained pending, a task-specific a100 mirror was submitted under the same per-variant atomic lock:

- htzhulab task-specific job id: `58081007_2`
- a100-gpu task2 mirror array: `58081494`
- task2 watcher job: `58081496`
- task2 watcher log: `logs/SRRv3M8MyOPSTask2Race_58081007_2_58081494.log`

Current `squeue -j 58081007,58081494,58081496` evidence:

- `58081007_0`: `RUNNING` on `htzhulab`, elapsed at check `00:20:08`
- `58081007_1`: `RUNNING` on `htzhulab`, elapsed at check `00:20:08`
- `58081007_[2]`: `PENDING (Resources)` on `htzhulab`
- `58081494_[2]`: `PENDING (Priority)` on `a100-gpu`
- `58081496`: `RUNNING` on `spill`

Current `sacct -j 58081007,58081494,58081496` evidence:

- `58081007_0`: `RUNNING`, partition `htzhulab`, start `2026-07-07T00:18:35`
- `58081007_1`: `RUNNING`, partition `htzhulab`, start `2026-07-07T00:18:35`
- `58081007_[2]`: `PENDING`
- `58081494_[2]`: `PENDING`, partition `a100-gpu`
- `58081496`: `RUNNING`, partition `spill`

Task2 watcher log excerpt:

```text
2026-07-07T00:35:16.673408 watch_start htzhulab=58081007_2 a100=58081494
2026-07-07T00:35:16.713044 check=1 htzhulab=[('58081007_2', 'htzhulab', 'PENDING', '(Resources)')] a100=[('58081494_[2]', 'a100-gpu', 'PENDING', '(Priority)')]
2026-07-07T00:37:16.754405 check=2 htzhulab=[('58081007_2', 'htzhulab', 'PENDING', '(Resources)')] a100=[('58081494_[2]', 'a100-gpu', 'PENDING', '(Priority)')]
```

## Latest Check After Aggregator Installation

`squeue -j 58081007,58081476,58081477,58081479,58081494,58081496` showed:

- `58081007_0`: `RUNNING` on `htzhulab`, node `g1807htzh01`, elapsed at check `00:50:03`
- `58081007_1`: `RUNNING` on `htzhulab`, node `g1807htzh01`, elapsed at check `00:50:03`
- `58081007_[2]`: `PENDING (Resources)` on `htzhulab`
- `58081494_[2]`: `PENDING (Priority)` on `a100-gpu`
- `58081496`: `RUNNING` watcher on `spill`

`sacct -j 58081007,58081476,58081477,58081479,58081494,58081496` showed:

- `58081007_0`: `RUNNING`, partition `htzhulab`, elapsed `00:50:05`, start `2026-07-07T00:18:35`
- `58081007_1`: `RUNNING`, partition `htzhulab`, elapsed `00:50:05`, start `2026-07-07T00:18:35`
- `58081007_[2]`: `PENDING`
- `58081494_[2]`: `PENDING`, partition `a100-gpu`
- `58081496`: `RUNNING`, partition `spill`

Task2 watcher latest excerpt:

```text
2026-07-07T00:55:18.471719 check=11 htzhulab=[('58081007_2', 'htzhulab', 'PENDING', '(Resources)')] a100=[('58081494_[2]', 'a100-gpu', 'PENDING', '(Priority)')]
2026-07-07T00:57:18.517628 check=12 htzhulab=[('58081007_2', 'htzhulab', 'PENDING', '(Resources)')] a100=[('58081494_[2]', 'a100-gpu', 'PENDING', '(Priority)')]
2026-07-07T00:59:18.559476 check=13 htzhulab=[('58081007_2', 'htzhulab', 'PENDING', '(Resources)')] a100=[('58081494_[2]', 'a100-gpu', 'PENDING', '(Priority)')]
2026-07-07T01:01:18.603520 check=14 htzhulab=[('58081007_2', 'htzhulab', 'PENDING', '(Resources)')] a100=[('58081494_[2]', 'a100-gpu', 'PENDING', '(Priority)')]
2026-07-07T01:03:18.648452 check=15 htzhulab=[('58081007_2', 'htzhulab', 'PENDING', '(Resources)')] a100=[('58081494_[2]', 'a100-gpu', 'PENDING', '(Priority)')]
2026-07-07T01:05:18.690857 check=16 htzhulab=[('58081007_2', 'htzhulab', 'PENDING', '(Resources)')] a100=[('58081494_[2]', 'a100-gpu', 'PENDING', '(Priority)')]
2026-07-07T01:07:18.734620 check=17 htzhulab=[('58081007_2', 'htzhulab', 'PENDING', '(Resources)')] a100=[('58081494_[2]', 'a100-gpu', 'PENDING', '(Priority)')]
```

Runtime artifact check showed that task0 and task1 have written validation checkpoints up to `checkpoint_validation_step_9000.pt` and `checkpoint_best.pt`, but no `checkpoint_final.pt`, `training_log.csv`, `validation_events.csv`, or `summary.json` has been written yet. This is consistent with `--enforce-min-train-loop-seconds`: the 9000-step validation checkpoints are intermediate evidence only and cannot be used as M8 completion.

`find results/20260707_srr_v3_m8_editor_grade_leaderboard_sprint/runtime -maxdepth 5 -type f \( -name 'summary.json' -o -name 'training_log.csv' -o -name 'validation_events.csv' -o -name 'checkpoint_final.pt' -o -name 'registration_same_subset_matrix.csv' \) -print | sort` returned no files, so the M8 post-job aggregator correctly kept the packet in monitor state.

## Post-Poll Partial Runtime Aggregation

After the 7200-second minimum train-loop threshold, MyoPS tasks `0` and `1` completed and wrote final runtime outputs.

Post-poll `sacct -j 58081007,58081476,58081477,58081479,58081494,58081496` evidence:

- `58081023` / array task `0`: `COMPLETED`, exit `0:0`, elapsed `02:02:09`, start `2026-07-07T00:18:35`, end `2026-07-07T02:20:44`
- `58081024` / array task `1`: `COMPLETED`, exit `0:0`, elapsed `02:02:00`, start `2026-07-07T00:18:35`, end `2026-07-07T02:20:35`
- `58081007` / array task `2`: `RUNNING`, partition `htzhulab`, start `2026-07-07T02:20:53`
- `58081494`: `CANCELLED by 397557`, a100 task2 mirror cancelled by the watcher after htzhulab task2 started
- `58081496`: `COMPLETED`, exit `0:0`, task2 watcher ended after cancelling the a100 mirror

Completed runtime artifacts now exist for:

- `runtime/variants/m8_full_srr_context_arbitration_longrun/summary.json`
- `runtime/variants/m8_full_srr_context_arbitration_longrun/training_log.csv`
- `runtime/variants/m8_full_srr_context_arbitration_longrun/validation_events.csv`
- `runtime/variants/m8_full_srr_context_arbitration_longrun/checkpoints/fold_0/propref_config/checkpoint_final.pt`
- `runtime/variants/m8_scar_precision_edema_safe_longrun/summary.json`
- `runtime/variants/m8_scar_precision_edema_safe_longrun/training_log.csv`
- `runtime/variants/m8_scar_precision_edema_safe_longrun/validation_events.csv`
- `runtime/variants/m8_scar_precision_edema_safe_longrun/checkpoints/fold_0/propref_config/checkpoint_final.pt`

The fail-closed aggregator was rerun after these files appeared:

```bash
python scripts/evaluation/aggregate_srr_v3_m8_leaderboard_sprint_packet.py --packet results/20260707_srr_v3_m8_editor_grade_leaderboard_sprint --contribution-device cpu
```

It exited `0` and kept the packet in `M8_NEEDS_MONITOR_NO_REVIEW` with blocker:

```text
missing_runtime_summary=m8_t2_centerC_edema_repair_longrun
```

The post-aggregation validator exited `0` with `error_count=0`, validating only the controlled non-ready monitor state.

## Completion Boundary

This is not M8 completion. Two MyoPS variants have completed and been partially aggregated, but task2 is still running, the full 28800-second MyoPS budget is not proven, Cine mature registration is not complete, and no normal review-ready packet exists.
