#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=LCScarF0
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=07:30:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access

set -euo pipefail

CARE_ROOT="${CARE_ROOT:-/overflow/htzhu/CARE}"
cd "${CARE_ROOT}"
mkdir -p logs
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/LCScarF0_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "LOG_FILE=${LOG_FILE}"
echo "variant=scar_lge_fallback_boost"
./envs/env_CARE/bin/python scripts/training/run_srr_myops_fold0.py \
  --variant scar_lge_fallback_boost \
  --fold 0 \
  --device cuda \
  --base-channels 16 \
  --patch-shape 12,96,96 \
  --batch-size 2 \
  --max-runtime-seconds 23400 \
  --min-effective-seconds 21600 \
  --max-steps 1000000 \
  --log-every 500 \
  --val-every 5000 \
  --out-root results/20260626_lesion_compact \
  --scar-weight 1.70 \
  --edema-weight 1.20 \
  --oversample-foreground 0.90 \
  --complete-oversample 0.45 \
  --scar-router-temperature 1.25 \
  --retrieval-entropy-floor 0.70 \
  --retrieval-entropy-weight 0.08 \
  --retrieval-coverage-weight 0.12 \
  --retrieval-max-weight-penalty 0.05
