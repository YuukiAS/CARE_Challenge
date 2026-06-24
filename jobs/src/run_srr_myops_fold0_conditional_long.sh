#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=SRRCondLongF0
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=08:00:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access

set -euo pipefail

CARE_ROOT="${CARE_ROOT:-/overflow/htzhu/CARE}"
cd "${CARE_ROOT}"
mkdir -p logs
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/SRRCondLongF0_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "LOG_FILE=${LOG_FILE}"
echo "variant=conditional_dualhead_control"
./envs/env_CARE/bin/python scripts/training/run_srr_myops_fold0.py \
  --variant conditional_dualhead_control \
  --fold 0 \
  --device cuda \
  --base-channels 16 \
  --patch-shape 12,96,96 \
  --batch-size 2 \
  --max-runtime-seconds 21600 \
  --min-effective-seconds 14400 \
  --max-steps 1000000 \
  --log-every 1000 \
  --val-every 10000 \
  --out-root results/20260621_srr_fold0_long
