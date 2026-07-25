#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=SRRW4EvalC
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=04:00:00
#SBATCH --partition=general

set -euo pipefail

export CARE_W4_DEVICE=cpu
export CARE_W4_ATTEMPT_ID="${CARE_W4_ATTEMPT_ID:-w4_eval_cpu_fallback_${SLURM_JOB_ID:-local}}"

bash /users/a/e/aereinh/CARE/jobs/care_mm/evaluate_care_srr_cascade_w4.sh
