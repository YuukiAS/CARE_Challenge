#!/usr/bin/env bash
# Run MyoPS-Net, U-MyoPS, and/or CineMyoPS (paper repos). See scripts/MyoPS-Net, scripts/U-MyoPS, scripts/CineMyoPS.
# Env:
#   MODEL=all|MyoPS-Net|U-MyoPS|CineMyoPS (legacy: myops_net|u_myops|cinemyops)
#   PREPARE_ONLY=0|1
#   STAGE=1|2  (U-MyoPS only)
set -euo pipefail
CARE_ROOT="${CARE_ROOT:-/overflow/htzhu/CARE}"
MODEL="${MODEL:-all}"
PREPARE_ONLY="${PREPARE_ONLY:-0}"
STAGE="${STAGE:-1}"

run_prepare_MyoPS_Net() {
  "${CARE_ROOT}/env_CARE/bin/python" "${CARE_ROOT}/scripts/MyoPS-Net/prepare_myops_net_layout.py" "$@"
}

run_MyoPS_Net_train() {
  bash "${CARE_ROOT}/scripts/MyoPS-Net/run_train.sh" "$@"
}

run_prepare_U_MyoPS() {
  _v1="${CARE_CineMyoPS_ENV:-${CARE_CINEMYOPS_ENV:-${CARE_ROOT}/env_CARE_nnUNet_v1}}"
  "${_v1}/bin/python" "${CARE_ROOT}/scripts/U-MyoPS/prepare_u_myops_from_care.py" "$@"
}

run_u_stage1() {
  bash "${CARE_ROOT}/scripts/U-MyoPS/run_stage1.sh" "$@"
}

run_u_stage2() {
  bash "${CARE_ROOT}/scripts/U-MyoPS/run_stage2.sh" "$@"
}

run_prepare_CineMyoPS() {
  "${CARE_ROOT}/env_CARE/bin/python" "${CARE_ROOT}/scripts/CineMyoPS/prepare_task025_from_care.py" "$@"
}

run_CineMyoPS_train() {
  bash "${CARE_ROOT}/scripts/CineMyoPS/run_train.sh" "$@"
}

do_MyoPS_Net() {
  run_prepare_MyoPS_Net
  if [[ "${PREPARE_ONLY}" == "1" ]]; then
    echo "PREPARE_ONLY=1: skip MyoPS-Net training."
    return 0
  fi
  run_MyoPS_Net_train
}

do_U_MyoPS() {
  run_prepare_U_MyoPS
  if [[ "${PREPARE_ONLY}" == "1" ]]; then
    echo "PREPARE_ONLY=1: skip U-MyoPS stages."
    return 0
  fi
  if [[ "${STAGE}" == "2" ]]; then
    run_u_stage2 "$@"
  else
    run_u_stage1 "$@"
  fi
}

do_CineMyoPS() {
  run_prepare_CineMyoPS
  if [[ "${PREPARE_ONLY}" == "1" ]]; then
    echo "PREPARE_ONLY=1: skip CineMyoPS training."
    return 0
  fi
  run_CineMyoPS_train "$@"
}

# shellcheck source=/dev/null
source "${CARE_ROOT}/env_nnunet.sh"
export PATH="${CARE_ROOT}/env_CARE/bin:${PATH}"

case "${MODEL}" in
  all)
    do_MyoPS_Net
    do_U_MyoPS "$@"
    do_CineMyoPS "$@"
    ;;
  MyoPS-Net|myops_net) do_MyoPS_Net ;;
  U-MyoPS|u_myops) do_U_MyoPS "$@" ;;
  CineMyoPS|cinemyops) do_CineMyoPS "$@" ;;
  *)
    echo "Unknown MODEL=${MODEL} (use all|MyoPS-Net|U-MyoPS|CineMyoPS)" >&2
    exit 1
    ;;
esac

echo "===== PaperBaselines/run_all.sh done (MODEL=${MODEL}) ====="
