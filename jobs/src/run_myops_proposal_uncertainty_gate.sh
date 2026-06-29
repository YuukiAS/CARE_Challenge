#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=PropUncF0
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
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/PropUncF0_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "LOG_FILE=${LOG_FILE}"
echo "variant=proposal_uncertainty_gate"
./envs/env_CARE/bin/python -u scripts/training/run_srr_myops_fold0.py \
  --variant proposal_uncertainty_gate \
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
  --out-root results/20260628_myops_proposal \
  --proposal-bce-weight 0.42 \
  --proposal-margin-weight 0.20 \
  --proposal-uncertainty-weight 0.08 \
  --proposal-margin 0.25 \
  --retrieval-entropy-floor 0.70 \
  --retrieval-entropy-weight 0.08 \
  --retrieval-coverage-weight 0.10 \
  --retrieval-max-weight-penalty 0.05
