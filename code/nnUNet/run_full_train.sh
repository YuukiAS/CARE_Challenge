#!/usr/bin/env bash
# Full nnU-Net v2 pipeline: convert (optional) → plan_and_preprocess → train (501 / 502).
# Usage: from repo root, after CUDA torch + pip install -r requirements-nnunet.txt:
#   source env_nnunet.sh
#   bash code/nnUNet/run_full_train.sh
#
# Env:
#   CONFIG, FOLD, TRAIN_MYOPS, TRAIN_CINE, SKIP_CONVERT — see SERVER.md
#   CARE_NNUNET_TRAINER — default nnUNetTrainer_500epochs (set in env_nnunet.sh)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CARE_ROOT="${CARE_ROOT:-$(cd "${SCRIPT_DIR}/../.." && pwd)}"
# shellcheck source=/dev/null
source "${CARE_ROOT}/env_nnunet.sh"

PYTHON="${CARE_ROOT}/envs/env_CARE/bin/python"
CONFIG="${CONFIG:-3d_fullres}"
FOLD="${FOLD:-0}"
TRAIN_MYOPS="${TRAIN_MYOPS:-1}"
TRAIN_CINE="${TRAIN_CINE:-1}"
SKIP_CONVERT="${SKIP_CONVERT:-0}"
MYOPS_CONVERT_INPUT="${MYOPS_CONVERT_INPUT:-}"
CINE_CONVERT_INPUT="${CINE_CONVERT_INPUT:-}"

if [[ "${SKIP_CONVERT}" != "1" ]]; then
  echo "===== Convert → nnUNet_raw ====="
  MYOPS_EXTRA=()
  [[ -n "${MYOPS_CONVERT_INPUT}" ]] && MYOPS_EXTRA+=(--input "${MYOPS_CONVERT_INPUT}")
  "${PYTHON}" "${CARE_ROOT}/code/nnUNet/convert_myops_to_nnunet.py" \
    "${MYOPS_EXTRA[@]}" --output "${nnUNet_raw}/Dataset501_CAREMyoPS"
  CINE_EXTRA=()
  [[ -n "${CINE_CONVERT_INPUT}" ]] && CINE_EXTRA+=(--input "${CINE_CONVERT_INPUT}")
  "${PYTHON}" "${CARE_ROOT}/code/nnUNet/convert_cine_to_nnunet.py" \
    "${CINE_EXTRA[@]}" --output "${nnUNet_raw}/Dataset502_CARECineMyoPS"
else
  echo "SKIP_CONVERT=1: skipping conversion."
fi

if [[ "${TRAIN_MYOPS}" == "1" ]]; then
  echo "===== Plan & train: Dataset 501 (${CONFIG}, fold ${FOLD}, -tr ${CARE_NNUNET_TRAINER}) ====="
  nnUNetv2_plan_and_preprocess -d 501 --verify_dataset_integrity
  nnUNetv2_train 501 "${CONFIG}" "${FOLD}" --npz -tr "${CARE_NNUNET_TRAINER}"
else
  echo "TRAIN_MYOPS=0: skip 501."
fi

if [[ "${TRAIN_CINE}" == "1" ]]; then
  echo "===== Plan & train: Dataset 502 (${CONFIG}, fold ${FOLD}, -tr ${CARE_NNUNET_TRAINER}) ====="
  nnUNetv2_plan_and_preprocess -d 502 --verify_dataset_integrity
  nnUNetv2_train 502 "${CONFIG}" "${FOLD}" --npz -tr "${CARE_NNUNET_TRAINER}"
else
  echo "TRAIN_CINE=0: skip 502."
fi

echo "===== Done ====="
