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
if [[ "${UMYOPS_STAGE1_AUTO_LAYOUT:-1}" == "1" ]]; then
  bash "${CARE_ROOT}/scripts/U-MyoPS/prepare_stage1_layout.sh"
fi
cd "${REPO}/jrs"
FOLD="${FOLD:-0}"
# Upstream config defaults --phase to metric (eval only, no training). CARE benchmarks never passed --phase,
# so jobs exited almost immediately with nearly empty logs. Default to train; override with UMYOPS_STAGE1_PHASE
# or pass --phase ... in "$@" (last flag wins for typical argparse).
UMYOPS_STAGE1_PHASE="${UMYOPS_STAGE1_PHASE:-train}"
exec "${PY}" joint_registration_myocardium_segmentation.py \
  --fold "${FOLD}" \
  --phase "${UMYOPS_STAGE1_PHASE}" \
  --data_source "${UMYOPS_DATA_SOURCE:-ZS_unaligned}" \
  --net "${UMYOPS_NET:-tps}" \
  --weight "${UMYOPS_WEIGHT:-1.0}" \
  "$@"
