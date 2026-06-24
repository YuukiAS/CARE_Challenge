#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=SRRMyoPSF0
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=06:00:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access

set -euo pipefail

CARE_ROOT="${CARE_ROOT:-/overflow/htzhu/CARE}"
cd "${CARE_ROOT}"
mkdir -p logs
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/SRRMyoPSF0_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "LOG_FILE=${LOG_FILE}"
echo "This fold0 job is gated by prompts/tasks/20260621_srr_fold0.md."
echo "The spec task only validates the SRR interface; do not submit this script before GO_FOLD0."

./envs/env_CARE/bin/python scripts/training/run_srr_myops.py --smoke \
  --output-json results/20260621_srr_spec/job_interface_smoke.json
