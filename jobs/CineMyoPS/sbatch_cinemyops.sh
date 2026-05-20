#!/bin/bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=CineMyoPS_paper
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=08:00:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access
set -euo pipefail

if [[ "${1:-}" == "--help" ]]; then
  cat <<'EOF'
Usage: sbatch jobs/CineMyoPS/sbatch_cinemyops.sh

Environment:
  FOLD                  Fold index, default 0
  CINE_NUM_FRAMES       Sampled cine frames, default 4
  CINE_SKIP_SANITY      If 1, skip Task026 sanity_check_task026.py
  CINE_NNUNET_EPOCHS    Trainer epochs (also read by CARECineMyoPSTrainer env), default 300
  CINE_SKIP_PREPARE     If 1, skip prepare_task026 + sanity (reuse existing raw/preprocessed)
  CINE_FORCE_WRITE_SPLITS  If 1, rewrite splits_final.pkl with --backup-existing when present
  CINE_RUN_EXPORT_EVAL  If 1, after training run export + unified eval (fold FOLD)
  CARE_MAX_BATCH_SIZE   CARE trainer caps nnU-Net planned batch_size (default 2); increase only if GPU allows
EOF
  exit 0
fi

if [[ -z "${CARE_ROOT:-}" ]]; then
  if [[ -n "${SLURM_SUBMIT_DIR:-}" && -f "${SLURM_SUBMIT_DIR}/env_nnunet.sh" ]]; then
    CARE_ROOT="$(cd "${SLURM_SUBMIT_DIR}" && pwd)"
  else
    THIS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    CARE_ROOT="$(cd "${THIS_DIR}/../.." && pwd)"
  fi
fi
export CARE_ROOT
cd "${CARE_ROOT}"
# shellcheck source=/dev/null
source "${CARE_ROOT}/env_nnunet.sh"

CARE_CineMyoPS_ENV="${CARE_CineMyoPS_ENV:-${CARE_CINEMYOPS_ENV:-${CARE_ROOT}/envs/env_CARE_nnUNet_v1}}"
export PATH="${CARE_CineMyoPS_ENV}/bin:${PATH}"
export CARE_CineMyoPS_ENV
export PYTHONUNBUFFERED=1

mkdir -p "${CARE_ROOT}/logs"
TS="$(date +%Y%m%d_%H%M%S)"
_SHORT="${SLURM_JOB_NAME:-CineMyoPS_paper}"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/${_SHORT}_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "paper sbatch log file: $(readlink -f "${LOG_FILE}")"
bash "${CARE_ROOT}/jobs/CineMyoPS/run_task026_paper_steps.sh" "$@"
