#!/usr/bin/env bash
# Full pipeline on GPU server: convert all cases, preprocess, train (and optional predict).
# Usage:
#   source env_nnunet.sh   # or conda activate env_CARE (auto-sources via activate.d)
#   bash scripts/nnunet/run_full_train.sh
# Optional env:
#   CONFIG=3d_fullres   (default)
#   FOLD=0              (default)
#   TRAIN_MYOPS=1 TRAIN_CINE=1  (defaults both on)
#   SKIP_CONVERT=1      skip conversion if nnUNet_raw already synced
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CARE_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
# shellcheck source=/dev/null
source "${CARE_ROOT}/env_nnunet.sh"

export PATH="${CARE_ROOT}/env_CARE/bin:${PATH}"
PYTHON="${CARE_ROOT}/env_CARE/bin/python"

CONFIG="${CONFIG:-3d_fullres}"
FOLD="${FOLD:-0}"
TRAIN_MYOPS="${TRAIN_MYOPS:-1}"
TRAIN_CINE="${TRAIN_CINE:-1}"
SKIP_CONVERT="${SKIP_CONVERT:-0}"
NPFP="${NPFP:-8}"

MYOPS_OUT="${nnUNet_raw}/Dataset501_CAREMyoPS"
CINE_OUT="${nnUNet_raw}/Dataset502_CARECineMyoPS"

if [[ "${SKIP_CONVERT}" != "1" ]]; then
  echo "=== Full conversion: MyoPS ==="
  "${PYTHON}" "${SCRIPT_DIR}/convert_myops_to_nnunet.py" \
    --input "${CARE_ROOT}/data/CARE_Challenge/MyoPS_train" \
    --output "${MYOPS_OUT}"

  echo "=== Full conversion: CineMyoPS ==="
  "${PYTHON}" "${SCRIPT_DIR}/convert_cine_to_nnunet.py" \
    --input "${CARE_ROOT}/data/CARE_Challenge/CineMyoPS_train" \
    --output "${CINE_OUT}"
else
  echo "=== SKIP_CONVERT=1: using existing ${nnUNet_raw} ==="
fi

if [[ "${TRAIN_MYOPS}" == "1" ]]; then
  echo "=== Preprocess Dataset501 ==="
  nnUNetv2_plan_and_preprocess -d 501 --verify_dataset_integrity -npfp "${NPFP}"
  echo "=== Train Dataset501 ${CONFIG} fold ${FOLD} ==="
  nnUNetv2_train "501" "${CONFIG}" "${FOLD}" --npz
fi

if [[ "${TRAIN_CINE}" == "1" ]]; then
  echo "=== Preprocess Dataset502 ==="
  nnUNetv2_plan_and_preprocess -d 502 --verify_dataset_integrity -npfp "${NPFP}"
  echo "=== Train Dataset502 ${CONFIG} fold ${FOLD} ==="
  nnUNetv2_train "502" "${CONFIG}" "${FOLD}" --npz
fi

echo "=== Training commands submitted / completed. Check nnUNet_results ==="
