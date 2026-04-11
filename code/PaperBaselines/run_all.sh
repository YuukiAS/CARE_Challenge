#!/usr/bin/env bash
# Run MyoPS-Net, U-MyoPS, and/or CineMyoPS (paper repos). See scripts/<model>/ for details.
# Env:
#   MODEL=all|myops_net|u_myops|cinemyops (default: all)
#   PREPARE_ONLY=0|1
#   STAGE=1|2  (U-MyoPS only)
set -euo pipefail
CARE_ROOT="${CARE_ROOT:-/overflow/htzhu/CARE}"
MODEL="${MODEL:-all}"
PREPARE_ONLY="${PREPARE_ONLY:-0}"
STAGE="${STAGE:-1}"

run_prepare_myops_net() {
  "${CARE_ROOT}/env_CARE/bin/python" "${CARE_ROOT}/scripts/myops_net/prepare_myops_net_layout.py" "$@"
}

run_myops_net_train() {
  bash "${CARE_ROOT}/scripts/myops_net/run_train.sh" "$@"
}

run_prepare_u_myops() {
  "${CARE_ROOT}/env_CARE/bin/python" "${CARE_ROOT}/scripts/u_myops/prepare_u_myops_from_care.py" "$@"
}

run_u_stage1() {
  bash "${CARE_ROOT}/scripts/u_myops/run_stage1.sh" "$@"
}

run_u_stage2() {
  bash "${CARE_ROOT}/scripts/u_myops/run_stage2.sh" "$@"
}

run_prepare_cinemyops() {
  "${CARE_ROOT}/env_CARE/bin/python" "${CARE_ROOT}/scripts/cinemyops/prepare_task025_from_care.py" "$@"
}

run_cinemyops_train() {
  bash "${CARE_ROOT}/scripts/cinemyops/run_train.sh" "$@"
}

do_myops_net() {
  run_prepare_myops_net
  if [[ "${PREPARE_ONLY}" == "1" ]]; then
    echo "PREPARE_ONLY=1: skip MyoPS-Net training."
    return 0
  fi
  run_myops_net_train
}

do_u_myops() {
  run_prepare_u_myops
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

do_cinemyops() {
  run_prepare_cinemyops
  if [[ "${PREPARE_ONLY}" == "1" ]]; then
    echo "PREPARE_ONLY=1: skip CineMyoPS training."
    return 0
  fi
  run_cinemyops_train "$@"
}

# shellcheck source=/dev/null
source "${CARE_ROOT}/env_nnunet.sh"
export PATH="${CARE_ROOT}/env_CARE/bin:${PATH}"

case "${MODEL}" in
  all)
    do_myops_net
    do_u_myops "$@"
    do_cinemyops "$@"
    ;;
  myops_net) do_myops_net ;;
  u_myops) do_u_myops "$@" ;;
  cinemyops) do_cinemyops "$@" ;;
  *)
    echo "Unknown MODEL=${MODEL} (use all|myops_net|u_myops|cinemyops)" >&2
    exit 1
    ;;
esac

echo "===== PaperBaselines/run_all.sh done (MODEL=${MODEL}) ====="
