#!/bin/bash
# U-MyoPS round5 export-only checkpoint comparison for Task912 LGE-only/no-prior.
# Submit from repo root:
#   sbatch jobs/U-MyoPS/sbatch_round5_export_compare.sh
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=U-MyoPS-r5-export
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=32G
#SBATCH --time=02:00:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access
set -euo pipefail

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

mkdir -p logs
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/U-MyoPS_r5_export_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "===== U-MyoPS round5 Task912 final/best export comparison ====="
echo "host=$(hostname) SLURM_JOB_ID=${SLURM_JOB_ID:-na}"
echo "LOG_FILE=${LOG_FILE}"

for chk in model_final_checkpoint model_best; do
  tag="round5_lge_only_no_prior_${chk}"
  echo ""
  echo "===== export ${chk} tag=${tag} ====="
  UMYOPS_EXPORT_TASK=Task912_CARE_UmyopsLGEOnlyNoPrior \
  UMYOPS_EXPORT_TRAINER=nnUNetTrainerPSNV8ScarCE2 \
  UMYOPS_EXPORT_CHECKPOINT="${chk}" \
  UMYOPS_EXPORT_TAG="${tag}" \
  UMYOPS_STAGE2_WHICH_SUBNET=scar \
  UMYOPS_EXPORT_FORCE_FALLBACK=1 \
  CARE_ROOT="${CARE_ROOT}" \
  bash "${CARE_ROOT}/jobs/U-MyoPS/sbatch_export_eval_fold0.sh"
done

echo "===== U-MyoPS round5 export comparison done ====="
