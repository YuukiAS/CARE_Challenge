#!/usr/bin/env bash
# Local driver: prepare → stage 1; stage 2 off by default (env_nnunet.sh UMYOPS_RUN_STAGE2=0). Set UMYOPS_RUN_STAGE2=1 to run pathology nnU-Net. Task: UMYOPS_STAGE2_TASK.
set -euo pipefail
CARE_ROOT="${CARE_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export CARE_ROOT
# shellcheck source=/dev/null
source "${CARE_ROOT}/env_nnunet.sh"
CARE_CineMyoPS_ENV="${CARE_CineMyoPS_ENV:-${CARE_CINEMYOPS_ENV:-${CARE_ROOT}/env_CARE_nnUNet_v1}}"
export CARE_CineMyoPS_ENV
export PATH="${CARE_CineMyoPS_ENV}/bin:${PATH}"
export LEGACY_PYTHON="${LEGACY_PYTHON:-${CARE_CineMyoPS_ENV}/bin/python}"
PY="${UMYOPS_PYTHON:-${CARE_CineMyoPS_ENV}/bin/python}"

resolve_stage2_task_name() {
  local base="${UMYOPS_STAGE2_TASK:-Task901_CARE_UmyopsPathology}"
  if [[ "${UMYOPS_STAGE2_PER_FOLD_TASK:-1}" == "1" ]]; then
    printf '%s_fold%s\n' "${base}" "${FOLD:-0}"
  else
    printf '%s\n' "${base}"
  fi
}

"${PY}" "${CARE_ROOT}/scripts/U-MyoPS/prepare_u_myops_from_care.py" "$@"
bash "${CARE_ROOT}/scripts/U-MyoPS/run_stage1.sh" "$@"
echo "===== U-MyoPS stage 1 done ====="

if [[ "${UMYOPS_RUN_STAGE2:-0}" != "1" ]]; then
  echo "===== U-MyoPS: stage 2 skipped (set UMYOPS_RUN_STAGE2=1 to enable) ====="
  exit 0
fi

UMYOPS_STAGE2_TASK_NAME="${UMYOPS_STAGE2_TASK_NAME:-$(resolve_stage2_task_name)}"
export UMYOPS_STAGE2_TASK_NAME
if [[ "${UMYOPS_STAGE2_AUTO_PREP:-0}" == "1" ]]; then
  bash "${CARE_ROOT}/scripts/U-MyoPS/prepare_stage2_task.sh"
fi

bash "${CARE_ROOT}/scripts/U-MyoPS/run_stage2.sh" \
  "${UMYOPS_STAGE2_DIM:-2d}" \
  "${UMYOPS_STAGE2_TRAINER:-nnUNetTrainerPSNV8}" \
  "${UMYOPS_STAGE2_TASK_NAME}" \
  "${FOLD:-0}" \
  --epochs "${UMYOPS_STAGE2_EPOCHS:-100}"
echo "===== U-MyoPS stage 2 done ====="
