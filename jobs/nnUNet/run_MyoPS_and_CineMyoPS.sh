#!/bin/bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=nnUNet_D501_D502
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=2-00:00:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access
#
# Full nnU-Net v2 CARE baseline: Dataset 501 then 502 (same fold).
set -euo pipefail

THIS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CARE_ROOT="${CARE_ROOT:-$(cd "${THIS_DIR}/../.." && pwd)}"
cd "${CARE_ROOT}"
export PATH="${CARE_ROOT}/env_CARE/bin:${PATH}"
# shellcheck source=/dev/null
source "${CARE_ROOT}/env_nnunet.sh"

mkdir -p logs
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/nnUNet_D501_D502_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "LOG_FILE=${LOG_FILE}"
echo "===== CARE nnU-Net — MyoPS + CineMyoPS (501 + 502) ====="
echo "Timestamp: $(date -Iseconds 2>/dev/null || date)"
echo "Host: $(hostname 2>/dev/null || true) JobID: ${SLURM_JOB_ID:-local}"
echo "CARE_ROOT=${CARE_ROOT} CONFIG=${CONFIG:-3d_fullres} FOLD=${FOLD:-0} SKIP_CONVERT=${SKIP_CONVERT:-0}"

export TRAIN_MYOPS=1
export TRAIN_CINE=1
export CONFIG="${CONFIG:-3d_fullres}"
export FOLD="${FOLD:-0}"
export SKIP_CONVERT="${SKIP_CONVERT:-0}"

bash "${CARE_ROOT}/code/nnUNet/run_full_train.sh"
echo "===== Finished 501 + 502 ====="
