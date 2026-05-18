#!/bin/bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=CineMyoPS_D502
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=08:00:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access
#
# CineMyoPS paper repo: Task025 nnU-Net v1 via third_party/CineMyoPS/code/Lascar_3_train.py.
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
# shellcheck source=/dev/null
source "${CARE_ROOT}/env_nnunet.sh"

CARE_CineMyoPS_ENV="${CARE_CineMyoPS_ENV:-${CARE_CINEMYOPS_ENV:-${CARE_ROOT}/env_CARE_nnUNet_v1}}"
export PATH="${CARE_CineMyoPS_ENV}/bin:${PATH}"
export CARE_CineMyoPS_ENV
# Python block-buffers stdout when piped to tee; epoch/loss lines use print() and appear late without this.
export PYTHONUNBUFFERED=1

mkdir -p logs
TS="$(date +%Y%m%d_%H%M%S)"
_SHORT="${SLURM_JOB_NAME:-CineMyoPS_D502}"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/${_SHORT}_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

PY="${CARE_CineMyoPS_ENV}/bin/python"

CINE_NNUNET_TASK="${CINE_NNUNET_TASK:-Task025_Cine_Seg}"
export CINE_NNUNET_TASK

echo "===== CineMyoPS (paper): prepare + train ====="
echo "CARE_CineMyoPS_ENV=${CARE_CineMyoPS_ENV}"
echo "CINE_NNUNET_TASK=${CINE_NNUNET_TASK} nnUNet_raw=${nnUNet_raw:-} nnUNet_preprocessed=${nnUNet_preprocessed:-}"

if [[ "${PREPARE:-1}" == "1" ]]; then
  "${PY}" "${CARE_ROOT}/code/CineMyoPS/prepare_task025_from_care.py" \
    --output "${nnUNet_raw}/${CINE_NNUNET_TASK}" "$@"
fi

# Raw export alone is not enough: Lascar_3_train needs nnUNetPlansv2.1_plans_2D.pkl under nnUNet_preprocessed.
PLANS_2D="${nnUNet_preprocessed}/${CINE_NNUNET_TASK}/nnUNetPlansv2.1_plans_2D.pkl"
PLANS_2D_LEGACY="${nnUNet_preprocessed}/${CINE_NNUNET_TASK}/nnUNetPlans_plans_2D.pkl"
if [[ ! -f "${PLANS_2D}" && -f "${PLANS_2D_LEGACY}" ]]; then
  ln -sf "nnUNetPlans_plans_2D.pkl" "${PLANS_2D}"
  echo "Linked ${PLANS_2D} -> nnUNetPlans_plans_2D.pkl (skip redundant plan+preprocess)"
fi
if [[ ! -f "${PLANS_2D}" ]]; then
  echo "Missing ${PLANS_2D} — running nnU-Net v1 plan_and_preprocess (set CINE_SKIP_PLAN_PREPROCESS=1 to abort instead)."
  if [[ "${CINE_SKIP_PLAN_PREPROCESS:-0}" == "1" ]]; then
    echo "error: CINE_SKIP_PLAN_PREPROCESS=1 but plans missing." >&2
    exit 1
  fi
  export PYTHONPATH="${CARE_ROOT}/third_party/CineMyoPS/code:${PYTHONPATH:-}"
  PP="${CARE_ROOT}/third_party/CineMyoPS/code/nnunet/experiment_planning/old/old_plan_and_preprocess_task.py"
  "${PY}" "${PP}" -t "${CINE_NNUNET_TASK}" -pl "${CINE_NNUNET_PL:-8}" -pf "${CINE_NNUNET_PF:-8}"
  _ppdir="${nnUNet_preprocessed}/${CINE_NNUNET_TASK}"
  if [[ -f "${_ppdir}/nnUNetPlans_plans_2D.pkl" && ! -f "${PLANS_2D}" ]]; then
    ln -sf "nnUNetPlans_plans_2D.pkl" "${PLANS_2D}"
    echo "Linked ${PLANS_2D} -> nnUNetPlans_plans_2D.pkl (v1 old planner filename vs default_plans_identifier)"
  fi
fi

export CINE_NNUNET_EPOCHS="${CINE_NNUNET_EPOCHS:-300}"
bash "${CARE_ROOT}/code/CineMyoPS/run_train.sh" "$@"
echo "===== CineMyoPS paper train done ====="
