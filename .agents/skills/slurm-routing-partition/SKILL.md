---
name: slurm-routing-partition
description: Must be used before submitting any CARE Slurm job or writing a GPT/Codex plan that will submit Slurm jobs; covers GPU partition routing, sbatch/srun/squeue/sacct decisions, pending-job monitoring, monitor-packet completion rules, routing races, and scheduler block decisions for milestone or goal tasks.
---

# CARE Slurm Routing and Partition Policy

Use this skill before every CARE Slurm job submission and before writing any GPT/Codex milestone, goal, or handoff that will submit Slurm jobs. It applies whenever a CARE task involves Slurm, GPU jobs, `sbatch`, `srun`, `squeue`, `sacct`, partition choice, pending monitor packets, scheduler blockers, or milestone/goal completion from job outputs.

## Partition Order

Default CARE model work to `htzhulab`.

Fallback order:

1. `htzhulab` — default/preferred for CARE jobs.
2. `a100-gpu` — school A100 fallback when `htzhulab` is expected to wait too long.
3. `volta-gpu` — V100 fallback after `a100-gpu`.

Known school GPU resources:

- `a100-gpu`: `gpu:nvidia_a100-pcie-40gb`, default QOS `gpu_access`.
- `volta-gpu`: `gpu:tesla_v100-sxm2-16gb`, default QOS `gpu_access`.

Other visible partitions such as `l40-gpu`, `gpu`, and `webportal_gpu` are not default CARE fallback routes. Use them only when the user explicitly asks or the job requirements clearly fit them better.

Before switching away from `htzhulab`, inspect queue state:

```bash
squeue -p htzhulab
sinfo -o '%P|%a|%l|%D|%t|%G'
```

Do not switch partitions for short waits or routine pending jobs. Switch only when `htzhulab` is full and the expected wait is long relative to the planned job budget.

## Pending and Goal Block Rule

Do not report a scheduler block just because jobs are pending.

For goal tasks, if every submitted routing partition remains pending and no job has started, monitor checks must be spaced 2 hours apart. Only after 12 consecutive 2-hour checks where every submitted routing partition is still pending with no progress may the goal be marked blocked for scheduler saturation. This is a 24-hour pending evidence threshold.

For milestone/handoff packets, a pending, submitted-only, running, or awaiting-accounting state is a monitor state, not completion. Use the milestone's allowed monitor state, such as `NEEDS_MONITOR`, and do not request normal review.

## Monitor Packet Is Not Completion

A Slurm submission, monitor job, watcher, pending queue state, or submitted-only packet is not a completion packet.

If `completion_check.md`, `result.md`, `commands_run.md`, or a training adequacy table contains `NEEDS_MONITOR`, `PENDING_MONITOR`, `JOB_SUBMITTED`, `PENDING_PRIORITY`, `RUNNING`, `AWAITING_SACCT`, or an equivalent state, the packet is not reviewable as complete.

After a Slurm job completes, rerun the relevant aggregator or evidence collector and commit the tracked lightweight result files produced from runtime outputs before requesting review.

`commands_run.md` showing only `sbatch submitted`, `squeue pending`, `PENDING Priority`, or pending `sacct` is not completion evidence.

Completion evidence from jobs must record:

- job id;
- state;
- exit code;
- runtime;
- log path;
- runtime output path;
- aggregation command;
- aggregation exit code;
- tracked evidence files updated from runtime output.

If the job completed but runtime output is missing or aggregation fails, completion state must be `NEEDS_EVIDENCE`, not ready.

## Routing Race

When both `htzhulab` and `a100-gpu` are plausibly long-wait and either may start first, a routing race to both partitions is allowed.

Rules:

- Use isolated output directories or an atomic per-run/per-variant lock.
- As soon as one partition starts running, cancel the other partition's still-pending mirror job.
- Record job IDs, partition states, cancellation command, and watcher/log path.
- Do not include `volta-gpu` in the race unless `htzhulab` and `a100-gpu` are unusable or the user explicitly approves it.

## Preflight and Replacement Submission

Every formal CARE training chain must run a compute-environment preflight before
the first GPU job. A login-node import check is not enough. The preflight should
use the same Python, environment activation, config, output roots, log roots,
lock roots, and entrypoint contract as the formal job.

Minimum preflight checks:

- Python executable and version.
- Critical imports needed by the training entrypoint.
- Optimizer construction smoke check.
- CUDA visibility when a GPU job is required.
- Config parse and semantic contract print, such as `--print-contract`.
- Output, log, and lock parent directory writability.
- Code/config/split fingerprints for later retry comparison.

Default dependency semantics:

- A training stage that requires upstream success uses `afterok`.
- Independent training stages use no dependency, or an explicitly plan-declared
  dependency with `independent_of_upstream_success: true` and a reason.
- Accounting/finalizer jobs over all attempts use `afterany`.

Bounded same-scope retry is allowed for operational defects without a new
planner decision when command semantics, code/config/split fingerprints, task
graph, executor id, and write scope are unchanged. Recommended defaults:

```yaml
max_startup_retries: 2
max_preemption_retries: 2
max_unknown_retries: 0
```

Before retry, verify the command/config/code/split fingerprints. Any semantic
change is not a retry and must go through the appropriate revision/planning
gate. Old failed jobs remain in the ledger permanently and failed startup
attempts receive zero optimizer-step and train-loop credit. Replacement receipts
must record old and new job IDs, retry reason, attempt number, and fingerprint
comparison. A single failed job is runtime evidence, not a goal block.

## Slurm Headers

Default CARE/lab jobs:

```bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=<ShortJobName>
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=<limit>
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access
```

A100 fallback:

```bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=<ShortJobName>
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=<limit>
#SBATCH --gres=gpu:nvidia_a100-pcie-40gb:1
#SBATCH --partition=a100-gpu
#SBATCH --qos=gpu_access
```

V100 fallback:

```bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=<ShortJobName>
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=<limit>
#SBATCH --gres=gpu:tesla_v100-sxm2-16gb:1
#SBATCH --partition=volta-gpu
#SBATCH --qos=gpu_access
```

School GPU partitions may reject jobs that inherit an incompatible default QOS. Keep `--qos=gpu_access` unless the user explicitly asks for another QOS or a known reason requires it.

## Logging

Inside Slurm scripts, create a timestamped log and tee stdout/stderr:

```bash
mkdir -p logs
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/<ShortJobName>_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1
```

Use filenames like `logs/CineMyoPS_44291121_20260418_111101.log`. Avoid Slurm `%x_%j.out` files unless diagnosing scheduler startup failures.

## Job Size

Default single CARE training/evaluation job walltime is 8 hours or less unless the task explicitly authorizes a longer run. Prefer budgeted jobs, max-runtime guards, max-epoch caps, validation-based early stopping, and explicit best-checkpoint selection.
