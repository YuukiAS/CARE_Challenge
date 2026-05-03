#!/usr/bin/env bash
# Export CineMyoPS fold predictions on CARE protocol val cases via nnU-Net v1 inference.
set -euo pipefail

CARE_ROOT="${CARE_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
source "${CARE_ROOT}/env_nnunet.sh"

# CARE: quiet timestamped inference logs by default; set CINE_NNUNET_INFERENCE_VERBOSE=1 for legacy per-case prints.
export CINE_NNUNET_INFERENCE_VERBOSE="${CINE_NNUNET_INFERENCE_VERBOSE:-0}"

FOLD="${FOLD:-0}"
TASK="${CINE_NNUNET_TASK:-Task025_Cine_Seg}"
TRAINER="${CINE_NNUNET_TRAINER:-nnUNetTrainerV2}"
NET="${CINE_NNUNET_DIM:-2d}"
CHK="${CINE_PRED_CHECKPOINT:-model_best}"
SPLIT_JSON="${CARE_ROOT}/data/benchmarks/protocol/splits_CineMyoPS.json"
RAW_IMAGES="${nnUNet_raw}/${TASK}/imagesTr"
TMP_ROOT="${CARE_ROOT}/results/predictions/_tmp/CineMyoPS/fold_${FOLD}"
TMP_INPUT="${TMP_ROOT}/imagesTs"
TMP_OUTPUT="${TMP_ROOT}/pred_prefixed"
FINAL_OUTPUT="${CARE_ROOT}/results/predictions/CineMyoPS/fold_${FOLD}"
PY="${CARE_ROOT}/env_CARE/bin/python"

mkdir -p "${TMP_INPUT}" "${TMP_OUTPUT}" "${FINAL_OUTPUT}"

while IFS= read -r cid; do
  match=( "${RAW_IMAGES}"/*_"${cid}"_0000.nii.gz )
  [[ -f "${match[0]:-}" ]] || { echo "missing Task025 input for ${cid}" >&2; exit 1; }
  [[ "${#match[@]}" -eq 1 ]] || { echo "ambiguous Task025 input for ${cid}" >&2; exit 1; }
  ln -sfn "$(readlink -f "${match[0]}")" "${TMP_INPUT}/$(basename "${match[0]}")"
done < <("${PY}" - "${SPLIT_JSON}" "${FOLD}" <<'PY'
import json, sys
from pathlib import Path
folds = json.loads(Path(sys.argv[1]).read_text())["folds"]
for cid in folds[int(sys.argv[2])]["val"]:
    print(cid)
PY
)

bash "${CARE_ROOT}/scripts/CineMyoPS/run_test.sh" \
  -i "${TMP_INPUT}" \
  -o "${TMP_OUTPUT}" \
  -t "${TASK}" \
  -tr "${TRAINER}" \
  -m "${NET}" \
  -f "${FOLD}" \
  --chk "${CHK}" \
  --overwrite_existing

while IFS= read -r cid; do
  match=( "${TMP_OUTPUT}"/*_"${cid}".nii.gz )
  [[ -f "${match[0]:-}" ]] || { echo "missing inference output for ${cid}" >&2; exit 1; }
  [[ "${#match[@]}" -eq 1 ]] || { echo "ambiguous inference output for ${cid}" >&2; exit 1; }
  ln -sfn "$(readlink -f "${match[0]}")" "${FINAL_OUTPUT}/${cid}.nii.gz"
done < <("${PY}" - "${SPLIT_JSON}" "${FOLD}" <<'PY'
import json, sys
from pathlib import Path
folds = json.loads(Path(sys.argv[1]).read_text())["folds"]
for cid in folds[int(sys.argv[2])]["val"]:
    print(cid)
PY
)
