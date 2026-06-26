#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=SRRSoftF0
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
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/SRRSoftF0_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "LOG_FILE=${LOG_FILE}"
echo "variant=srr_soft_entropy"
./envs/env_CARE/bin/python scripts/training/run_srr_myops_fold0.py \
  --variant srr_soft_entropy \
  --fold 0 \
  --device cuda \
  --base-channels 16 \
  --patch-shape 12,96,96 \
  --batch-size 2 \
  --max-runtime-seconds 23400 \
  --min-effective-seconds 18000 \
  --max-steps 750000 \
  --log-every 500 \
  --val-every 5000 \
  --out-root results/20260625_srr_recovery \
  --retrieval-entropy-floor 0.9 \
  --retrieval-entropy-weight 0.12 \
  --retrieval-coverage-weight 0.08 \
  --retrieval-max-weight-penalty 0.06
