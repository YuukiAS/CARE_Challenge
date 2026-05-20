#!/usr/bin/env bash
# Export CineMyoPS fold predictions on CARE protocol val cases via nnU-Net v1 inference.
set -euo pipefail

CARE_ROOT="${CARE_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
source "${CARE_ROOT}/env_nnunet.sh"

# CARE: quiet timestamped inference logs by default; set CINE_NNUNET_INFERENCE_VERBOSE=1 for legacy per-case prints.
export CINE_NNUNET_INFERENCE_VERBOSE="${CINE_NNUNET_INFERENCE_VERBOSE:-0}"

FOLD="${FOLD:-0}"
TASK="${CINE_NNUNET_TASK:-Task026_Cine_4D}"
TRAINER="${CINE_NNUNET_TRAINER:-CARECineMyoPSTrainer}"
NET="${CINE_NNUNET_DIM:-2d}"
CHK="${CINE_PRED_CHECKPOINT:-model_final_checkpoint}"
OUTPUT_MODEL="${CINE_OUTPUT_MODEL:-CineMyoPS}"
SPLIT_JSON="${CINE_PROTOCOL_SPLIT_JSON:-${CARE_ROOT}/data/benchmarks/protocol/splits_CineMyoPS.json}"
RAW_IMAGES="${nnUNet_raw}/${TASK}/imagesTr"
TMP_ROOT="${CARE_ROOT}/results/predictions/_tmp/${OUTPUT_MODEL}/fold_${FOLD}"
TMP_INPUT="${TMP_ROOT}/imagesTs"
TMP_OUTPUT="${TMP_ROOT}/pred_prefixed"
FINAL_OUTPUT="${CARE_ROOT}/results/predictions/${OUTPUT_MODEL}/fold_${FOLD}"
PY="${CARE_ROOT}/envs/env_CARE_nnUNet_v1/bin/python"
MODEL_DIR="${nnUNet_results}/nnUNet/${NET}/${TASK}/${TRAINER}__nnUNetPlansv2.1/fold_${FOLD}"
CKPT_PATH="${MODEL_DIR}/${CHK}.model"

mkdir -p "${TMP_INPUT}" "${TMP_OUTPUT}" "${FINAL_OUTPUT}"
echo "export split json: $(readlink -f "${SPLIT_JSON}")"
echo "export raw images: $(readlink -f "${RAW_IMAGES}")"
echo "export output model: ${OUTPUT_MODEL}"
echo "export tmp input: $(readlink -f "${TMP_INPUT}")"
echo "export tmp output: $(readlink -f "${TMP_OUTPUT}")"
echo "export final output: $(readlink -f "${FINAL_OUTPUT}")"
echo "export checkpoint: ${CKPT_PATH}"
echo "export BN recalibration: CINE_BN_RECALIBRATE=${CINE_BN_RECALIBRATE:-0} CINE_BN_RECALIB_BATCHES=${CINE_BN_RECALIB_BATCHES:-32}"
echo "export combine mode: CINE_COMBINE_MODE=${CINE_COMBINE_MODE:-current}"

if [[ ! -f "${CKPT_PATH}" ]]; then
  echo "missing checkpoint: ${CKPT_PATH}" >&2
  echo "available checkpoints under ${MODEL_DIR}:" >&2
  find "${MODEL_DIR}" -maxdepth 1 -type f -name '*.model' -printf '%TY-%Tm-%Td %TH:%TM %p\n' 2>/dev/null | sort >&2 || true
  exit 1
fi

if [[ "${CHK}" == "model_best" && -f "${MODEL_DIR}/model_final_checkpoint.model" && "${MODEL_DIR}/model_best.model" -ot "${MODEL_DIR}/model_final_checkpoint.model" ]]; then
  echo "warning: model_best.model is older than model_final_checkpoint.model; export may not represent the latest training round." >&2
fi
stat -c 'export checkpoint mtime=%y size=%s path=%n' "${CKPT_PATH}"

rm -f "${TMP_INPUT}"/*.nii.gz
rm -f "${TMP_OUTPUT}"/*.nii.gz

shopt -s nullglob

while IFS= read -r cid; do
  matches=( "${RAW_IMAGES}/${cid}"_*.nii.gz "${RAW_IMAGES}"/*_"${cid}"_*.nii.gz )
  [[ "${#matches[@]}" -gt 0 ]] || { echo "missing raw input channels for ${cid} under ${RAW_IMAGES}" >&2; exit 1; }
  for input_path in "${matches[@]}"; do
    ln -sfn "$(readlink -f "${input_path}")" "${TMP_INPUT}/$(basename "${input_path}")"
  done
done < <("${PY}" - "${SPLIT_JSON}" "${FOLD}" <<'PY'
import json, sys
from pathlib import Path
folds = json.loads(Path(sys.argv[1]).read_text())["folds"]
for cid in folds[int(sys.argv[2])]["val"]:
    print(cid)
PY
)

bash "${CARE_ROOT}/code/CineMyoPS/run_test.sh" \
  -i "${TMP_INPUT}" \
  -o "${TMP_OUTPUT}" \
  -t "${TASK}" \
  -tr "${TRAINER}" \
  -m "${NET}" \
  -f "${FOLD}" \
  --chk "${CHK}" \
  --overwrite_existing

# nnU-Net writes predictions using the Task026 training identifier (e.g. center_alpha_Case1005.nii.gz),
# while splits_CineMyoPS.json lists protocol ids (Case1005). Prefer exact CaseXXXX.nii.gz when present,
# otherwise accept exactly one *_<CaseXXXX>.nii.gz match (do not use a single array slot: the first
# element would be the non-existent CaseXXXX path and would always fail under nullglob+prefixed outputs).
while IFS= read -r cid; do
  pred=""
  if [[ -f "${TMP_OUTPUT}/${cid}.nii.gz" ]]; then
    pred="${TMP_OUTPUT}/${cid}.nii.gz"
  else
    matches=( "${TMP_OUTPUT}"/*_"${cid}".nii.gz )
    if [[ "${#matches[@]}" -eq 1 && -f "${matches[0]}" ]]; then
      pred="${matches[0]}"
    elif [[ "${#matches[@]}" -eq 0 ]]; then
      echo "missing inference output for ${cid} (expected ${TMP_OUTPUT}/${cid}.nii.gz or ${TMP_OUTPUT}/*_${cid}.nii.gz)" >&2
      exit 1
    else
      echo "ambiguous inference output for ${cid}: ${matches[*]}" >&2
      exit 1
    fi
  fi
  ln -sfn "$(readlink -f "${pred}")" "${FINAL_OUTPUT}/${cid}.nii.gz"
done < <("${PY}" - "${SPLIT_JSON}" "${FOLD}" <<'PY'
import json, sys
from pathlib import Path
folds = json.loads(Path(sys.argv[1]).read_text())["folds"]
for cid in folds[int(sys.argv[2])]["val"]:
    print(cid)
PY
)

shopt -u nullglob
