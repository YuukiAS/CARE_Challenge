# M8 Cine Slurm Status

status: `M8_NEEDS_MONITOR_NO_REVIEW`

## Submission

Mandatory M8 Cine mature registration was submitted to the default CARE lab partition with:

```bash
sbatch jobs/src/run_srr_v3_m8_cine_registration_mature_htzhulab.sh
```

Submitted job id: `58081208`.

The job script runs:

```bash
python scripts/evaluation/run_srr_v3_m7_cine_registration_repair.py \
  --max-cases 12 \
  --pairs-per-case 3 \
  --demons-iterations 40 \
  --antspy-iterations 25
```

and copies the mature-registration outputs into the M8 result filenames when successful.

## Current Scheduler Evidence

`squeue -j 58081007,58081025,58081026,58081208` showed:

- `58081208`: `PENDING`, partition `htzhulab`, reason `(Priority)`
- `58081007_0`: `RUNNING`, partition `htzhulab`
- `58081007_1`: `RUNNING`, partition `htzhulab`
- `58081007_[2]`: `PENDING`, partition `htzhulab`, reason `(Resources)`

`sacct -j 58081007,58081025,58081026,58081208` showed `58081208|SRRv3M8CineReg|htzhulab|PENDING`.

## Completion Boundary

This is not Cine evidence completion. Mature registration has been submitted but has not completed, and no M8 Cine registration matrix or temporal dictionary aggregation has been produced from the submitted job.
