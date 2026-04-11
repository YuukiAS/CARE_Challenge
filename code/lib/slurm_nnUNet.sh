#!/usr/bin/env bash
# Shared helpers for CARE nnU-Net v2 Slurm jobs and paper-baseline sbatch wrappers.
# shellcheck shell=bash
# Usage: source "${CARE_ROOT}/code/lib/slurm_nnUNet.sh"

set -euo pipefail

care_nnunet_init_logging() {
  local care_root="${1:?}"
  mkdir -p "$care_root/logs"
  local run_ts
  run_ts="$(date +%Y%m%d_%H%M%S)"
  local log_file="$care_root/logs/${2:-run}_${SLURM_JOB_ID:-local}_${run_ts}.log"
  exec > >(tee -a "$log_file") 2>&1
  echo "LOG_FILE=$log_file"
}

care_nnunet_print_header() {
  local title="${1:?}"
  echo "===== $title ====="
  echo "Timestamp: $(date -Iseconds)"
  echo "Host: $(hostname)"
  echo "JobID: ${SLURM_JOB_ID:-N/A}"
  echo "GPU visible: ${CUDA_VISIBLE_DEVICES:-N/A}"
  echo "CARE_ROOT: ${CARE_ROOT:?}"
  echo "ENV_PATH: ${ENV_PATH:?}"
  echo "CONFIG=${CONFIG:-3d_fullres} FOLD=${FOLD:-0} NPFP=${NPFP:-8}"
  echo "RUN_TEST=${RUN_TEST:-1} SKIP_CONVERT=${SKIP_CONVERT:-0}"
}

care_nnunet_env_python() {
  # shellcheck source=/dev/null
  source "${CARE_ROOT}/env_nnunet.sh"
  export PATH="${ENV_PATH}/bin:${PATH}"
  PYTHON="${ENV_PATH}/bin/python"
  export PYTHON
}

care_nnunet_check_gpu_torch() {
  if command -v nvidia-smi >/dev/null 2>&1; then
    echo "===== nvidia-smi ====="
    nvidia-smi || true
  fi
  echo "===== Python / Torch ====="
  "$PYTHON" - << 'PY'
import sys
print("python:", sys.version)
try:
    import torch
    print("torch:", torch.__version__, "cuda_available:", torch.cuda.is_available())
    if torch.cuda.is_available():
        print("gpu_count:", torch.cuda.device_count())
except Exception as e:
    print("torch_check_failed:", e)
PY
}

# Run one CARE subtask: MyoPS (501) or CineMyoPS (502)
# Args: subtask_key dataset_id dataset_folder_name
# subtask_key: myops | cinemyops
care_nnunet_run_subtask() {
  local subtask_key="${1:?}"
  local dataset_id="${2:?}"
  local dataset_folder="${3:?}"
  local name_display
  case "$subtask_key" in
    myops) name_display="MyoPS" ;;
    cinemyops) name_display="CineMyoPS" ;;
    *) echo "Unknown subtask_key=$subtask_key"; return 1 ;;
  esac

  echo "----- Subtask: $name_display (nnU-Net dataset $dataset_id) -----"

  if [[ "${SKIP_CONVERT:-0}" != "1" ]]; then
    echo "===== Convert: $name_display -> $dataset_folder ====="
    if [[ "$subtask_key" == "myops" ]]; then
      "$PYTHON" "$CARE_ROOT/scripts/nnunet/convert_myops_to_nnunet.py" \
        --input "$CARE_ROOT/data/CARE_Challenge/MyoPS_train" \
        --output "$nnUNet_raw/$dataset_folder"
    else
      "$PYTHON" "$CARE_ROOT/scripts/nnunet/convert_cine_to_nnunet.py" \
        --input "$CARE_ROOT/data/CARE_Challenge/CineMyoPS_train" \
        --output "$nnUNet_raw/$dataset_folder"
    fi
  else
    echo "SKIP_CONVERT=1: skip conversion, expect $nnUNet_raw/$dataset_folder"
  fi

  echo "===== Plan & preprocess: $name_display ====="
  nnUNetv2_plan_and_preprocess -d "$dataset_id" --verify_dataset_integrity -npfp "${NPFP:-8}"

  echo "===== Train: $name_display (${CONFIG:-3d_fullres}, fold ${FOLD:-0}) ====="
  nnUNetv2_train "$dataset_id" "${CONFIG:-3d_fullres}" "${FOLD:-0}" --npz

  if [[ "${RUN_TEST:-1}" == "1" ]]; then
    echo "===== Validation (--val): $name_display ====="
    nnUNetv2_train "$dataset_id" "${CONFIG:-3d_fullres}" "${FOLD:-0}" --val
  fi

  echo "===== Done: $name_display ====="
}
