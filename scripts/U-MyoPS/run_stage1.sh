#!/usr/bin/env bash
# U-MyoPS stage 1: joint registration + myocardium segmentation (legacy jrs stack).
# Python: UMYOPS_PYTHON, else CARE_CineMyoPS_ENV / legacy CARE_CINEMYOPS_ENV, else env_CARE_nnUNet_v1 (same stack as CineMyoPS v1).
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CARE_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
REPO="${CARE_ROOT}/third_party/U-MyoPS_myops"
_V1_ENV="${CARE_CineMyoPS_ENV:-${CARE_CINEMYOPS_ENV:-${CARE_ROOT}/env_CARE_nnUNet_v1}}"
PY="${UMYOPS_PYTHON:-${_V1_ENV}/bin/python}"
export PYTHONPATH="${REPO}/jrs:${REPO}:${PYTHONPATH:-}"
cd "${REPO}/jrs"
FOLD="${FOLD:-0}"
exec "${PY}" joint_registration_myocardium_segmentation.py --fold "${FOLD}" "$@"
