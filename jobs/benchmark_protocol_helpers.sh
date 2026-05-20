#!/usr/bin/env bash
# CARE benchmark protocol/split helpers (low-level): JSON protocol generation + nnU-Net split injection.
# Invoked by run_unified_benchmark_{test,all}.sh during prep; safe to run manually for debugging.
set -euo pipefail

CARE_ROOT="${CARE_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
source "${CARE_ROOT}/env_nnunet.sh"

PY="${CARE_PYTHON:-${CARE_ROOT}/envs/env_CARE/bin/python}"
PROTO_DIR="${CARE_ROOT}/data/benchmarks/protocol"
MYOPS_INPUT="${MYOPS_PROTOCOL_INPUT:-${CARE_ROOT}/data/CARE_Challenge/MyoPS_train}"
CINE_INPUT="${CINE_PROTOCOL_INPUT:-${CARE_ROOT}/data/CARE_Challenge/CineMyoPS_train}"

cmd="${1:-}"
[[ -n "${cmd}" ]] || {
  echo "usage: bash jobs/benchmark_protocol_helpers.sh <gen-protocol|write-splits-501|write-splits-502|write-splits-task025|write-splits-umyo-stage2|print-all> [args...]" >&2
  exit 1
}
shift || true

translated_args=()
for arg in "$@"; do
  if [[ "${arg}" == "--backup" ]]; then
    translated_args+=("--backup-existing")
  else
    translated_args+=("${arg}")
  fi
done

resolve_umyo_stage2_task() {
  local fold="${1:-${FOLD:-0}}"
  local base="${UMYOPS_STAGE2_TASK:-Task901_CARE_UmyopsPathology}"
  if [[ "${UMYOPS_STAGE2_PER_FOLD_TASK:-1}" == "1" ]]; then
    printf '%s_fold%s\n' "${base}" "${fold}"
  else
    printf '%s\n' "${base}"
  fi
}

case "${cmd}" in
  gen-protocol)
    "${PY}" "${CARE_ROOT}/scripts/benchmark/generate_splits.py" \
      --task MyoPS \
      --input-root "${MYOPS_INPUT}" \
      --output-dir "${PROTO_DIR}" \
      "${translated_args[@]}"
    "${PY}" "${CARE_ROOT}/scripts/benchmark/generate_splits.py" \
      --task CineMyoPS \
      --input-root "${CINE_INPUT}" \
      --output-dir "${PROTO_DIR}" \
      "${translated_args[@]}"
    ;;
  write-splits-501)
    "${PY}" "${CARE_ROOT}/scripts/benchmark/nnunet_write_splits_final.py" \
      --protocol-json "${PROTO_DIR}/splits_MyoPS.json" \
      --dataset-name Dataset501_CAREMyoPS \
      "${translated_args[@]}"
    ;;
  write-splits-502)
    "${PY}" "${CARE_ROOT}/scripts/benchmark/nnunet_write_splits_final.py" \
      --protocol-json "${PROTO_DIR}/splits_CineMyoPS.json" \
      --dataset-name Dataset502_CARECineMyoPS \
      "${translated_args[@]}"
    ;;
  write-splits-task025)
    "${PY}" "${CARE_ROOT}/scripts/benchmark/nnunet_v1_write_splits_final.py" \
      --protocol-json "${PROTO_DIR}/splits_CineMyoPS.json" \
      --task-dir "${nnUNet_raw}/Task025_Cine_Seg" \
      --preprocessed-task-dir "${nnUNet_preprocessed}/Task025_Cine_Seg" \
      "${translated_args[@]}"
    ;;
  write-splits-umyo-stage2)
    UMYOPS_STAGE2_TASK_NAME="$(resolve_umyo_stage2_task "${FOLD:-0}")"
    "${PY}" "${CARE_ROOT}/scripts/benchmark/nnunet_v1_write_splits_final.py" \
      --protocol-json "${PROTO_DIR}/splits_MyoPS.json" \
      --task-dir "${CARE_ROOT}/third_party/U-MyoPS_myops/outputs/nnunet/raw/nnUNet_raw_data/${UMYOPS_STAGE2_TASK_NAME}" \
      --preprocessed-task-dir "${CARE_ROOT}/third_party/U-MyoPS_myops/outputs/nnunet/prepro/${UMYOPS_STAGE2_TASK_NAME}" \
      "${translated_args[@]}"
    ;;
  print-all)
    echo "CARE_ROOT=${CARE_ROOT}"
    echo "Protocol JSON:"
    ls -1 "${PROTO_DIR}"/cases_*.json "${PROTO_DIR}"/splits_*.json
    echo
    echo "nnUNet splits:"
    ls -1 "${nnUNet_preprocessed}/Dataset501_CAREMyoPS/splits_final.json" \
          "${nnUNet_preprocessed}/Dataset502_CARECineMyoPS/splits_final.json" 2>/dev/null || true
    echo
    echo "Task025 split:"
    ls -1 "${nnUNet_preprocessed}/Task025_Cine_Seg/splits_final.pkl" 2>/dev/null || true
    echo
    echo "U-MyoPS Stage2 split (current fold task):"
    UMYOPS_STAGE2_TASK_NAME="$(resolve_umyo_stage2_task "${FOLD:-0}")"
    ls -1 "${CARE_ROOT}/third_party/U-MyoPS_myops/outputs/nnunet/prepro/${UMYOPS_STAGE2_TASK_NAME}/splits_final.pkl" 2>/dev/null || true
    ;;
  *)
    echo "unknown command: ${cmd}" >&2
    exit 1
    ;;
esac
