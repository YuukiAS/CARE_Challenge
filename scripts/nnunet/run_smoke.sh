#!/usr/bin/env bash
# Local smoke test: convert at most MAX_CASES per dataset, then plan_and_preprocess.
# Does NOT run training. Safe on CPU-only nodes.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CARE_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
# shellcheck source=/dev/null
source "${CARE_ROOT}/env_nnunet.sh"

export PATH="${CARE_ROOT}/env_CARE/bin:${PATH}"
PYTHON="${CARE_ROOT}/env_CARE/bin/python"
MAX_CASES="${MAX_CASES:-3}"

echo "=== CARE nnU-Net smoke (max ${MAX_CASES} cases per dataset) ==="

echo "--- MyoPS -> Dataset501_CAREMyoPS ---"
"${PYTHON}" "${SCRIPT_DIR}/convert_myops_to_nnunet.py" \
  --input "${CARE_ROOT}/data/CARE_Challenge/MyoPS_train" \
  --output "${nnUNet_raw}/Dataset501_CAREMyoPS" \
  --max-cases "${MAX_CASES}"

echo "--- CineMyoPS -> Dataset502_CARECineMyoPS ---"
"${PYTHON}" "${SCRIPT_DIR}/convert_cine_to_nnunet.py" \
  --input "${CARE_ROOT}/data/CARE_Challenge/CineMyoPS_train" \
  --output "${nnUNet_raw}/Dataset502_CARECineMyoPS" \
  --max-cases "${MAX_CASES}"

NPFP="${NPFP:-2}"
echo "--- nnUNetv2_plan_and_preprocess Dataset501 ---"
nnUNetv2_plan_and_preprocess -d 501 --verify_dataset_integrity -npfp "${NPFP}"

echo "--- nnUNetv2_plan_and_preprocess Dataset502 ---"
nnUNetv2_plan_and_preprocess -d 502 --verify_dataset_integrity -npfp "${NPFP}"

echo "=== Smoke OK ==="
