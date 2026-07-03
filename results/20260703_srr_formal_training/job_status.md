# Job Status: 20260703 SRR Formal Training

last_checked: 2026-07-03 13:15:50 EDT initial monitor; completed state verified by executor after user handoff
executor_task: `prompts/tasks/20260703_srr_formal_training.md`
output_root: `results/20260703_srr_formal_training/`

## Slurm Completion

submit_command: `sbatch --array=0-2 jobs/src/run_srr_propref_formal_myops_fold0.sh`
array_job_id: `57655472`
partition: `htzhulab`
qos: `gpu_access`
time_limit: `07:30:00`
gpu_request: `gres/gpu:1`

| array_task | sacct_job_id | child_job_id | variant | final_state | exit_code | slurm_elapsed | train_loop_seconds | log |
| --- | --- | --- | --- | --- | --- | ---: | ---: | --- |
| `0` | `57655472_0` | `57655473` | `srr_propref_shared_dual_dict` | `COMPLETED` | `0:0` | `00:08:30` | 138.168 | `logs/SRRPropRefFormalF0_0_57655473_20260703_131157.log` |
| `1` | `57655472_1` | `57655474` | `srr_propref_scar_precision` | `COMPLETED` | `0:0` | `00:07:47` | 138.574 | `logs/SRRPropRefFormalF0_1_57655474_20260703_131157.log` |
| `2` | `57655472_2` | `57655472` | `srr_propref_no_proto_cascade` | `COMPLETED` | `0:0` | `00:06:21` | 151.525 | `logs/SRRPropRefFormalF0_2_57655472_20260703_131718.log` |

## Config Guards

- wrapper: `jobs/src/run_srr_propref_formal_myops_fold0.sh`
- `MAX_STEPS < 1800` is refused.
- `VAL_EVERY > 300` is refused.
- all variant configs record `max_steps=1800`, `val_every=300`, `min_effective_optimizer_steps=1500`, and `min_effective_train_loop_seconds=1800`.

## Log Note

The three formal Slurm log files are present but zero bytes. Completed summaries, per-variant CSVs, checkpoints, predictions, and this command transcript are the replacement provenance evidence; Slurm stdout/stderr alone is not used for adequacy.
