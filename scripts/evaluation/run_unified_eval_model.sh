#!/usr/bin/env bash
# Run unified offline evaluation for one benchmark model across one or more folds.
set -euo pipefail

CARE_ROOT="${CARE_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
source "${CARE_ROOT}/env_nnunet.sh"
PY="${CARE_EVAL_PYTHON:-${CARE_ROOT}/env_CARE/bin/python}"

MODEL="${1:-}"
[[ -n "${MODEL}" ]] || {
  echo "usage: bash scripts/evaluation/run_unified_eval_model.sh <nnUNet501|nnUNet502|MyoPS-Net|CineMyoPS|U-MyoPS> [--folds \"0 1 2 3 4\"] [--foreground-classes \"...\"] [--hd95]" >&2
  exit 1
}
shift || true

FOLDS="0 1 2 3 4"
FG_CLASSES=""
HD95=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --folds)
      FOLDS="${2:?}"
      shift 2
      ;;
    --foreground-classes)
      FG_CLASSES="${2:?}"
      shift 2
      ;;
    --hd95)
      HD95=1
      shift
      ;;
    *)
      echo "unknown arg: $1" >&2
      exit 1
      ;;
  esac
done

PRED_ROOT="${CARE_ROOT}/results/predictions"
METRICS_ROOT="${CARE_ROOT}/results/metrics/unified"
mkdir -p "${PRED_ROOT}/${MODEL}" "${METRICS_ROOT}/${MODEL}"

case_list() {
  "${PY}" - "$1" "$2" <<'PY'
import json, sys
from pathlib import Path
folds = json.loads(Path(sys.argv[1]).read_text())["folds"]
fold = int(sys.argv[2])
for cid in folds[fold]["val"]:
    print(cid)
PY
}

abs_path() {
  readlink -f "$1"
}

resolve_umyo_stage2_task() {
  local fold="$1"
  local base="${UMYOPS_STAGE2_TASK:-Task901_CARE_UmyopsPathology}"
  if [[ "${UMYOPS_STAGE2_PER_FOLD_TASK:-1}" == "1" ]]; then
    printf '%s_fold%s\n' "${base}" "${fold}"
  else
    printf '%s\n' "${base}"
  fi
}

link_exact_cases() {
  local src_dir="$1" dest_dir="$2" split_json="$3" fold="$4"
  mkdir -p "${dest_dir}"
  while IFS= read -r cid; do
    local src_file="${src_dir}/${cid}.nii.gz"
    [[ -f "${src_file}" ]] || { echo "missing prediction ${src_file}" >&2; return 1; }
    ln -sfn "$(abs_path "${src_file}")" "${dest_dir}/${cid}.nii.gz"
  done < <(case_list "${split_json}" "${fold}")
}

link_suffix_cases() {
  local src_dir="$1" dest_dir="$2" split_json="$3" fold="$4"
  mkdir -p "${dest_dir}"
  while IFS= read -r cid; do
    local matches=( "${src_dir}"/*_"${cid}".nii.gz )
    [[ -f "${matches[0]:-}" ]] || { echo "missing prediction suffix match for ${cid} in ${src_dir}" >&2; return 1; }
    [[ "${#matches[@]}" -eq 1 ]] || { echo "ambiguous prediction suffix match for ${cid} in ${src_dir}" >&2; return 1; }
    ln -sfn "$(abs_path "${matches[0]}")" "${dest_dir}/${cid}.nii.gz"
  done < <(case_list "${split_json}" "${fold}")
}

run_myops_export_if_needed() {
  local fold="$1" pred_dir="$2"
  if compgen -G "${pred_dir}/*.nii.gz" >/dev/null; then
    return 0
  fi
  local data_root="${CARE_ROOT}/data/benchmarks/MyoPS-Net/fold_${fold}"
  echo "Export MyoPS-Net fold ${fold} validation predictions -> ${pred_dir}"
  "${PY}" "${CARE_ROOT}/scripts/MyoPS-Net/export_val_predictions.py" \
    --data-root "${data_root}" \
    --output-dir "${pred_dir}"
}

run_umyops_export_if_needed() {
  local fold="$1" pred_dir="$2"
  if compgen -G "${pred_dir}/*.nii.gz" >/dev/null; then
    return 0
  fi
  echo "Export U-MyoPS fold ${fold} validation predictions -> ${pred_dir}"
  local cmd=(
    "${PY}" "${CARE_ROOT}/scripts/U-MyoPS/export_stage2_val_predictions.py"
    --fold "${fold}"
    --base-task-name "${UMYOPS_STAGE2_TASK}"
    --trainer "${UMYOPS_STAGE2_TRAINER:-nnUNetTrainerPSNV8}"
    --dim "${UMYOPS_STAGE2_DIM:-2d}"
    --output-dir "${pred_dir}"
  )
  if [[ "${UMYOPS_STAGE2_PER_FOLD_TASK:-1}" == "1" ]]; then
    cmd+=( --per-fold-task )
  fi
  "${cmd[@]}"
}

SUMMARY_INPUTS=()
for FOLD in ${FOLDS}; do
  PRED_DIR="${PRED_ROOT}/${MODEL}/fold_${FOLD}"
  OUT_DIR="${METRICS_ROOT}/${MODEL}/fold_${FOLD}"
  case "${MODEL}" in
    nnUNet501)
      SPLIT_JSON="${CARE_ROOT}/data/benchmarks/protocol/splits_MyoPS.json"
      GT_DIR="${nnUNet_raw}/Dataset501_CAREMyoPS/labelsTr"
      SRC_DIR="${nnUNet_results}/Dataset501_CAREMyoPS/${CARE_NNUNET_TRAINER}__nnUNetPlans__${CONFIG:-3d_fullres}/fold_${FOLD}/validation"
      FG="${FG_CLASSES:-4,5}"
      link_exact_cases "${SRC_DIR}" "${PRED_DIR}" "${SPLIT_JSON}" "${FOLD}"
      ;;
    nnUNet502)
      SPLIT_JSON="${CARE_ROOT}/data/benchmarks/protocol/splits_CineMyoPS.json"
      GT_DIR="${nnUNet_raw}/Dataset502_CARECineMyoPS/labelsTr"
      SRC_DIR="${nnUNet_results}/Dataset502_CARECineMyoPS/${CARE_NNUNET_TRAINER}__nnUNetPlans__${CONFIG:-3d_fullres}/fold_${FOLD}/validation"
      FG="${FG_CLASSES:-1,2,3}"
      link_exact_cases "${SRC_DIR}" "${PRED_DIR}" "${SPLIT_JSON}" "${FOLD}"
      ;;
    MyoPS-Net)
      SPLIT_JSON="${CARE_ROOT}/data/benchmarks/protocol/splits_MyoPS.json"
      GT_DIR="${nnUNet_raw}/Dataset501_CAREMyoPS/labelsTr"
      FG="${FG_CLASSES:-4,5}"
      mkdir -p "${PRED_DIR}"
      run_myops_export_if_needed "${FOLD}" "${PRED_DIR}"
      ;;
    CineMyoPS)
      SPLIT_JSON="${CARE_ROOT}/data/benchmarks/protocol/splits_CineMyoPS.json"
      GT_DIR="${nnUNet_raw}/Dataset502_CARECineMyoPS/labelsTr"
      FG="${FG_CLASSES:-1,2,3}"
      if ! compgen -G "${PRED_DIR}/*.nii.gz" >/dev/null; then
        FOLD="${FOLD}" bash "${CARE_ROOT}/scripts/CineMyoPS/export_protocol_val_predictions.sh"
      fi
      ;;
    U-MyoPS)
      SPLIT_JSON="${CARE_ROOT}/data/benchmarks/protocol/splits_MyoPS.json"
      GT_DIR="${nnUNet_raw}/Dataset501_CAREMyoPS/labelsTr"
      FG="${FG_CLASSES:-4,5}"
      mkdir -p "${PRED_DIR}"
      run_umyops_export_if_needed "${FOLD}" "${PRED_DIR}"
      ;;
    *)
      echo "unsupported model: ${MODEL}" >&2
      exit 1
      ;;
  esac

  cmd=( "${PY}" "${CARE_ROOT}/scripts/evaluation/evaluate_predictions.py"
    --pred-dir "${PRED_DIR}"
    --gt-dir "${GT_DIR}"
    --fold-json "${SPLIT_JSON}"
    --fold "${FOLD}"
    --foreground-classes "${FG}"
    --output-dir "${OUT_DIR}"
  )
  [[ "${HD95}" == "1" ]] && cmd+=( --hd95 )
  "${cmd[@]}"
  SUMMARY_INPUTS+=( "${OUT_DIR}/evaluation_summary.json" )
done

"${PY}" "${CARE_ROOT}/scripts/evaluation/aggregate_folds.py" \
  --inputs "${SUMMARY_INPUTS[@]}" \
  --output-json "${METRICS_ROOT}/${MODEL}/aggregate.json" \
  --output-md "${METRICS_ROOT}/${MODEL}/aggregate.md"
