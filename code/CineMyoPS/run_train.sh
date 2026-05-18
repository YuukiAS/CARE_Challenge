#!/usr/bin/env bash
# CineMyoPS paper repo: nnU-Net v1 training via Lascar_3_train.py (bundled nnunet package).
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CARE_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
REPO="${CARE_ROOT}/third_party/CineMyoPS/code"
export PYTHONPATH="${REPO}:${PYTHONPATH:-}"
cd "${REPO}"

# nnU-Net v1 + legacy batchgenerators; separate from env_CARE (nnUNet v2).
CARE_CineMyoPS_ENV="${CARE_CineMyoPS_ENV:-${CARE_CINEMYOPS_ENV:-${CARE_ROOT}/env_CARE_nnUNet_v1}}"
PY="${CARE_CineMyoPS_ENV}/bin/python"
NET="${CINE_NNUNET_DIM:-2d}"
TRAINER="${CINE_NNUNET_TRAINER:-CARECineMyoPSTrainer}"
TASK="${CINE_NNUNET_TASK:-Task026_Cine_4D}"
FOLD="${FOLD:-0}"
EPOCHS="${CINE_NNUNET_EPOCHS:-300}"
export CINE_NUM_FRAMES="${CINE_NUM_FRAMES:-4}"

exec "${PY}" Lascar_3_train.py "${NET}" "${TRAINER}" "${TASK}" "${FOLD}" --epochs "${EPOCHS}" "$@"
