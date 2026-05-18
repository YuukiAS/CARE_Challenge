#!/usr/bin/env bash
# Stage 2: pathology nnUNet (legacy nnU-Net v1 API; vendored nnunet under jrs when PYTHONPATH is set).
# Python: LEGACY_PYTHON, else CARE_CineMyoPS_ENV / CARE_CINEMYOPS_ENV, else env_CARE_nnUNet_v1.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CARE_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
REPO="${CARE_ROOT}/third_party/U-MyoPS_myops"
_V1_ENV="${CARE_CineMyoPS_ENV:-${CARE_CINEMYOPS_ENV:-${CARE_ROOT}/env_CARE_nnUNet_v1}}"
PY="${LEGACY_PYTHON:-${_V1_ENV}/bin/python}"

if [[ -z "${PY}" ]] || [[ ! -x "${PY}" ]]; then
  echo "No usable Python for stage 2. Set LEGACY_PYTHON or CARE_CineMyoPS_ENV (nnU-Net v1 env). Example:" >&2
  echo "  export CARE_CineMyoPS_ENV=${CARE_ROOT}/env_CARE_nnUNet_v1" >&2
  exit 1
fi

REPO="$(cd "${REPO}" && pwd)"
# Vendored nnunet/paths.py defaults to relative ../outputs/... from jrs/; use repo-absolute dirs for Slurm/CARE.
export nnUNet_raw_data_base="${UMYOPS_NNUNET_RAW_BASE:-${REPO}/outputs/nnunet/raw}"
export nnUNet_preprocessed="${UMYOPS_NNUNET_PREPROCESSED:-${REPO}/outputs/nnunet/prepro}"
export RESULTS_FOLDER="${UMYOPS_NNUNET_RESULTS:-${REPO}/outputs/nnunet/output}"
export PYTHONUNBUFFERED=1

export PYTHONPATH="${REPO}/jrs:${REPO}:${PYTHONPATH:-}"
cd "${REPO}/jrs"
extra_args=()
if [[ -n "${UMYOPS_STAGE2_WHICH_SUBNET:-}" ]]; then
  extra_args+=( --whichsubnet "${UMYOPS_STAGE2_WHICH_SUBNET}" )
fi
if [[ "${UMYOPS_STAGE2_CONTINUE:-0}" == "1" ]]; then
  extra_args+=( --continue_training )
fi
if [[ -n "${UMYOPS_STAGE2_ADJUST_WEIGHTS:-}" ]]; then
  extra_args+=( --adjust_weights "${UMYOPS_STAGE2_ADJUST_WEIGHTS}" )
fi
if [[ -n "${UMYOPS_STAGE2_PRETRAINED_WEIGHTS:-}" ]]; then
  extra_args+=( -pretrained_weights "${UMYOPS_STAGE2_PRETRAINED_WEIGHTS}" )
fi
exec "${PY}" -u pathology_segmentation_train.py "$@" "${extra_args[@]}"
