#!/usr/bin/env bash
# Smoke test: convert a few cases, plan_and_preprocess for 501 and 502 (no long training).
# Usage: MAX_CASES=3 NPFP=2 bash code/nnUNet/run_smoke.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CARE_ROOT="${CARE_ROOT:-$(cd "${SCRIPT_DIR}/../.." && pwd)}"
# shellcheck source=/dev/null
source "${CARE_ROOT}/env_nnunet.sh"

PYTHON="${CARE_ROOT}/env_CARE/bin/python"
MAX_CASES="${MAX_CASES:-3}"
NPFP="${NPFP:-2}"

echo "===== Smoke: convert (max ${MAX_CASES} cases each) ====="
"${PYTHON}" "${CARE_ROOT}/code/nnUNet/convert_myops_to_nnunet.py" \
  --output "${nnUNet_raw}/Dataset501_CAREMyoPS" --max-cases "${MAX_CASES}"
"${PYTHON}" "${CARE_ROOT}/code/nnUNet/convert_cine_to_nnunet.py" \
  --output "${nnUNet_raw}/Dataset502_CARECineMyoPS" --max-cases "${MAX_CASES}"

echo "===== Smoke: plan_and_preprocess (npfp=${NPFP}) ====="
nnUNetv2_plan_and_preprocess -d 501 --verify_dataset_integrity -npfp "${NPFP}"
nnUNetv2_plan_and_preprocess -d 502 --verify_dataset_integrity -npfp "${NPFP}"

echo "===== Smoke done (no nnUNetv2_train). For training use code/nnUNet/run_full_train.sh ====="
