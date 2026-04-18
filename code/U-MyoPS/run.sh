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

"${PY}" "${CARE_ROOT}/scripts/U-MyoPS/prepare_u_myops_from_care.py" "$@"
bash "${CARE_ROOT}/scripts/U-MyoPS/run_stage1.sh" "$@"
echo "===== U-MyoPS stage 1 done ====="

if [[ "${UMYOPS_RUN_STAGE2:-0}" != "1" ]]; then
  echo "===== U-MyoPS: stage 2 skipped (set UMYOPS_RUN_STAGE2=1 to enable) ====="
  exit 0
fi

bash "${CARE_ROOT}/scripts/U-MyoPS/run_stage2.sh" \
  "${UMYOPS_STAGE2_DIM:-2d}" \
  "${UMYOPS_STAGE2_TRAINER:-nnUNetTrainerPSNV8}" \
  "${UMYOPS_STAGE2_TASK}" \
  "${FOLD:-0}" \
  --epochs "${UMYOPS_STAGE2_EPOCHS:-100}"
echo "===== U-MyoPS stage 2 done ====="
