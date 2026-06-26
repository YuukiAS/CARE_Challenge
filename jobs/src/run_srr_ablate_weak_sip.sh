#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=SRRWeakF0
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
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/SRRWeakF0_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "[SRRWeakF0] start $(date -Is)"
echo "[SRRWeakF0] host $(hostname)"
echo "[SRRWeakF0] log ${LOG_FILE}"

./envs/env_CARE/bin/python scripts/training/run_srr_myops_fold0.py \
  --variant retrieval_no_sip_or_weak_sip \
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
  --out-root results/20260625_srr_rescue_ablate \
  --retrieval-weight 0.2 \
  --retrieval-entropy-floor 0.35 \
  --retrieval-entropy-weight 0.02 \
  --retrieval-coverage-weight 0.02 \
  --retrieval-max-weight-penalty 0.01

echo "[SRRWeakF0] done $(date -Is)"
