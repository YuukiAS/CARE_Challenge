#!/bin/bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=R5DecodeAudit
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=02:00:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access
#
# Slurm entry: Result5 loss/decode calibration and pathology checkpoint audit.
# Reads completed proposal checkpoints only; writes task outputs under results/20260629_*.
set -euo pipefail

if [[ -z "${CARE_ROOT:-}" ]]; then
  if [[ -n "${SLURM_SUBMIT_DIR:-}" ]]; then
    CARE_ROOT="${SLURM_SUBMIT_DIR}"
  else
    SCRIPT_PATH="${BASH_SOURCE[0]:-$0}"
    THIS_DIR="$(cd "$(dirname "${SCRIPT_PATH}")" && pwd)"
    CARE_ROOT="$(cd "${THIS_DIR}/../.." && pwd)"
  fi
fi
cd "${CARE_ROOT}"

export PYTHONUNBUFFERED=1

mkdir -p "${CARE_ROOT}/logs"
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/R5DecodeAudit_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

VARIANTS="${VARIANTS:-proposal_pos_neg_basic}"

echo "===== Result5 decode/checkpoint audit ====="
echo "LOG_FILE=${LOG_FILE}"
echo "CARE_ROOT=${CARE_ROOT}"
echo "VARIANTS=${VARIANTS}"
echo "CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-}"

# shellcheck disable=SC2086
"${CARE_ROOT}/envs/env_CARE/bin/python" -u scripts/evaluation/audit_result5_decode_calibration.py \
  --variants ${VARIANTS} \
  --device cuda \
  --fast-metrics \
  --decode-dir results/20260629_loss_decode_calibration \
  --checkpoint-dir results/20260629_pathology_checkpoint_selection

echo "===== Result5 decode/checkpoint audit done ====="
