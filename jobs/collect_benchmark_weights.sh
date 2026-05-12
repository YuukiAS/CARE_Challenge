#!/usr/bin/env bash
# Collect trained benchmark weights into canonical fold-wise directories under ${CARE_ROOT}/models/:
#   nnUNet501/fold_k, nnUNet502/fold_k, MyoPS-Net/fold_k, CineMyoPS/fold_k, U-MyoPS/fold_k/{stage1,stage2}
# Aligns with jobs/run_unified_benchmark_{test,all}.sh job layout (FOLD / env_nnunet.sh). Prep uses benchmark_protocol_helpers.sh.
#
# Usage (repo root or any cwd):
#   bash jobs/collect_benchmark_weights.sh
#   bash jobs/collect_benchmark_weights.sh --folds "0 1 2 3 4"
#   COLLECT_MODE=copy bash jobs/collect_benchmark_weights.sh   # copy instead of symlink
#   bash jobs/collect_benchmark_weights.sh --only nnUNet,CineMyoPS
#
# Env (optional): CARE_ROOT, CARE_ROOT_OVERRIDE, FOLD, FOLDS, COLLECT_MODE=symlink|copy,
#   CONFIG (nnUNet v2, default 3d_fullres), CARE_NNUNET_TRAINER,
#   CINE_NNUNET_TASK (default Task026_Cine_4D), CINE_NNUNET_TRAINER (default CARECineMyoPSTrainer),
#   CINE_NNUNET_DIM (default 2d),
#   UMYOPS_STAGE2_TASK, UMYOPS_STAGE2_TRAINER, UMYOPS_STAGE2_DIM,
#   UMYOPS_STAGE2_PER_FOLD_TASK=0|1,
#   UMYOPS_WEIGHT (stage1 model_id weight segment, default 1.0), UMYOPS_NET/TPS (default tps),
#   UMYOPS_DATA_SOURCE (default ZS_unaligned)
set -euo pipefail

_CARE_SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -n "${CARE_ROOT_OVERRIDE:-}" ]]; then
  CARE_ROOT="${CARE_ROOT_OVERRIDE}"
else
  CARE_ROOT="$(cd "${_CARE_SELF_DIR}/.." && pwd)"
fi
unset _CARE_SELF_DIR

if [[ ! -f "${CARE_ROOT}/env_nnunet.sh" ]]; then
  echo "error: CARE_ROOT=${CARE_ROOT} missing env_nnunet.sh" >&2
  exit 1
fi
# shellcheck source=/dev/null
source "${CARE_ROOT}/env_nnunet.sh"

ONLY=""
FOLDS_CLI=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --folds)
      FOLDS_CLI="${2:?}"
      shift 2
      ;;
    --only)
      ONLY="${2:?}"
      shift 2
      ;;
    -h|--help)
      sed -n '1,25p' "$0"
      exit 0
      ;;
    *)
      echo "unknown arg: $1" >&2
      exit 1
      ;;
  esac
done

FOLDS="${FOLDS_CLI:-${FOLDS:-${FOLD:-0}}}"
COLLECT_MODE="${COLLECT_MODE:-symlink}"
CONFIG="${CONFIG:-3d_fullres}"
CARE_NNUNET_TRAINER="${CARE_NNUNET_TRAINER:-nnUNetTrainer_500epochs}"
# CARE paper-replication path: Task026_Cine_4D + CARECineMyoPSTrainer (4D cine, scar-only Lb3 head).
# Override CINE_NNUNET_TASK / CINE_NNUNET_TRAINER for the legacy Task025 single-frame nnUNetTrainerV2 baseline.
CINE_NNUNET_TASK="${CINE_NNUNET_TASK:-Task026_Cine_4D}"
CINE_NNUNET_TRAINER="${CINE_NNUNET_TRAINER:-CARECineMyoPSTrainer}"
CINE_NNUNET_DIM="${CINE_NNUNET_DIM:-2d}"
UMYOPS_STAGE2_TASK="${UMYOPS_STAGE2_TASK:-Task901_CARE_UmyopsPathology}"
UMYOPS_STAGE2_TRAINER="${UMYOPS_STAGE2_TRAINER:-nnUNetTrainerPSNV8}"
UMYOPS_STAGE2_DIM="${UMYOPS_STAGE2_DIM:-2d}"
UMYOPS_STAGE2_PER_FOLD_TASK="${UMYOPS_STAGE2_PER_FOLD_TASK:-1}"
UMYOPS_WEIGHT="${UMYOPS_WEIGHT:-1.0}"
UMYOPS_NET="${UMYOPS_NET:-tps}"
UMYOPS_DATA_SOURCE="${UMYOPS_DATA_SOURCE:-ZS_unaligned}"

MODELS_ROOT="${MODELS_ROOT:-${CARE_ROOT}/models}"
NNRES="${nnUNet_results:?nnUNet_results not set}"
UMYO_REPO="${CARE_ROOT}/third_party/U-MyoPS_myops"
MYOPSNET_REPO="${CARE_ROOT}/third_party/MyoPS-Net"

_want() {
  local name="$1"
  [[ -z "${ONLY}" ]] && return 0
  echo ",${ONLY}," | grep -q ",${name},"
}

_want_any() {
  local name
  for name in "$@"; do
    if _want "${name}"; then
      return 0
    fi
  done
  return 1
}

_abs() {
  readlink -f "$1"
}

_place() {
  local src="$1" dest_dir="$2" dest_name="${3:-$(basename "$src")}"
  [[ -e "${src}" ]] || { echo "  skip (missing): ${src}" >&2; return 0; }
  mkdir -p "${dest_dir}"
  local dest="${dest_dir}/${dest_name}"
  if [[ "${COLLECT_MODE}" == "copy" ]]; then
    cp -a "${src}" "${dest}"
    echo "  copy -> ${dest}"
  else
    ln -sfn "$(_abs "${src}")" "${dest}"
    echo "  symlink -> ${dest}"
  fi
}

_resolve_umyo_stage2_task() {
  local fold="$1"
  if [[ "${UMYOPS_STAGE2_PER_FOLD_TASK}" == "1" ]]; then
    printf '%s_fold%s\n' "${UMYOPS_STAGE2_TASK}" "${fold}"
  else
    printf '%s\n' "${UMYOPS_STAGE2_TASK}"
  fi
}

_find_umyo_stage1_dir() {
  local fold="$1"
  local exact="${UMYO_REPO}/outputs/asn_myo_tps_${UMYOPS_NET}_${UMYOPS_DATA_SOURCE}_${UMYOPS_WEIGHT}_fold${fold}"
  if [[ -d "${exact}/checkpoint" ]]; then
    printf '%s\n' "${exact}"
    return 0
  fi

  local best=""
  local best_score=-1
  local cand score
  shopt -s nullglob
  for cand in "${UMYO_REPO}"/outputs/*_fold"${fold}"; do
    [[ -d "${cand}" ]] || continue
    [[ -d "${cand}/checkpoint" || -d "${cand}/gen_res" ]] || continue
    score=0
    [[ "$(basename "${cand}")" == asn_myo_tps_"${UMYOPS_NET}"_"${UMYOPS_DATA_SOURCE}"_"${UMYOPS_WEIGHT}"_fold"${fold}" ]] && score=$((score + 100))
    [[ "$(basename "${cand}")" == *"${UMYOPS_NET}"* ]] && score=$((score + 10))
    [[ "$(basename "${cand}")" == *"${UMYOPS_DATA_SOURCE}"* ]] && score=$((score + 10))
    [[ "$(basename "${cand}")" == *"${UMYOPS_WEIGHT}"* ]] && score=$((score + 10))
    if [[ "${score}" -gt "${best_score}" ]]; then
      best="${cand}"
      best_score="${score}"
    fi
  done
  shopt -u nullglob
  [[ -n "${best}" ]] && printf '%s\n' "${best}"
}

echo "=== CARE collect_benchmark_weights ==="
echo "CARE_ROOT=${CARE_ROOT} MODELS_ROOT=${MODELS_ROOT} COLLECT_MODE=${COLLECT_MODE}"
echo "FOLDS=${FOLDS} CONFIG=${CONFIG} CARE_NNUNET_TRAINER=${CARE_NNUNET_TRAINER}"

for FOLD in ${FOLDS}; do
  echo "--- fold ${FOLD} ---"

  if _want_any nnUNet nnUNet501 nnUNet502; then
    echo "[nnUNet v2]"
    D501="${NNRES}/Dataset501_CAREMyoPS/${CARE_NNUNET_TRAINER}__nnUNetPlans__${CONFIG}/fold_${FOLD}"
    D502="${NNRES}/Dataset502_CARECineMyoPS/${CARE_NNUNET_TRAINER}__nnUNetPlans__${CONFIG}/fold_${FOLD}"
    if _want_any nnUNet nnUNet501; then
      DEST501="${MODELS_ROOT}/nnUNet501/fold_${FOLD}"
      for f in checkpoint_final.pth checkpoint_best.pth; do
        _place "${D501}/${f}" "${DEST501}" "${f}"
      done
      _place "${D501}/validation/summary.json" "${DEST501}" "validation_summary.json"
    fi
    if _want_any nnUNet nnUNet502; then
      DEST502="${MODELS_ROOT}/nnUNet502/fold_${FOLD}"
      for f in checkpoint_final.pth checkpoint_best.pth; do
        _place "${D502}/${f}" "${DEST502}" "${f}"
      done
      _place "${D502}/validation/summary.json" "${DEST502}" "validation_summary.json"
    fi
  fi

  if _want CineMyoPS; then
    echo "[CineMyoPS / nnU-Net v1 ${CINE_NNUNET_TASK} ${CINE_NNUNET_TRAINER}]"
    CINE="${NNRES}/nnUNet/${CINE_NNUNET_DIM}/${CINE_NNUNET_TASK}/${CINE_NNUNET_TRAINER}__nnUNetPlansv2.1/fold_${FOLD}"
    DESTC="${MODELS_ROOT}/CineMyoPS/fold_${FOLD}"
    # Drop stale symlinks/files first so a missing source under a renamed task/trainer is not silently kept.
    mkdir -p "${DESTC}"
    rm -f "${DESTC}"/*.model "${DESTC}"/*.model.pkl "${DESTC}"/validation_summary.json
    for f in model_final_checkpoint.model model_best.model model_latest.model; do
      _place "${CINE}/${f}" "${DESTC}" "${f}"
      # nnU-Net v1 stores plans+config alongside .model as .model.pkl; inference needs both.
      _place "${CINE}/${f}.pkl" "${DESTC}" "${f}.pkl"
    done
    _place "${CINE}/validation_raw/summary.json" "${DESTC}" "validation_summary.json"
  fi

  if _want MyoPS-Net; then
    echo "[MyoPS-Net]"
    CKPT_DIR="${CARE_ROOT}/results/checkpoints/MyoPS-Net/fold_${FOLD}/checkpoints"
    LEGACY_CKPT_DIR="${MYOPSNET_REPO}/checkpoints"
    DESTM="${MODELS_ROOT}/MyoPS-Net/fold_${FOLD}"
    if [[ ! -d "${CKPT_DIR}" ]] && [[ -d "${LEGACY_CKPT_DIR}" ]]; then
      CKPT_DIR="${LEGACY_CKPT_DIR}"
    fi
    if [[ -d "${CKPT_DIR}" ]]; then
      mkdir -p "${DESTM}"
      rm -f "${DESTM}"/*.pth
      if [[ -f "${CKPT_DIR}/best.pth" ]]; then
        _place "${CKPT_DIR}/best.pth" "${DESTM}" "best.pth"
        _place "${CKPT_DIR}/best_metrics.txt" "${DESTM}" "best_metrics.txt"
      else
        echo "  (no best.pth under ${CKPT_DIR}; MyoPS-Net has not saved a best checkpoint yet)" >&2
      fi
    else
      echo "  skip: no directory ${CKPT_DIR}" >&2
    fi
  fi

  if _want U-MyoPS; then
    echo "[U-MyoPS stage1]"
    S1DIR="$(_find_umyo_stage1_dir "${FOLD}" || true)"
    S1CK="${S1DIR:+${S1DIR}/checkpoint}"
    DEST1="${MODELS_ROOT}/U-MyoPS/fold_${FOLD}/stage1"
    if [[ -n "${S1CK}" && -d "${S1CK}" ]]; then
      shopt -s nullglob
      for p in "${S1CK}"/epoch_*.pth; do
        _place "${p}" "${DEST1}" "$(basename "${p}")"
      done
      shopt -u nullglob
      _latest_s1="$(ls -1t "${S1CK}"/epoch_*.pth 2>/dev/null | head -1 || true)"
      if [[ -n "${_latest_s1}" ]]; then
        _place "${_latest_s1}" "${DEST1}" "latest.pth"
      fi
    else
      echo "  skip: no stage1 checkpoint dir found for fold ${FOLD} under ${UMYO_REPO}/outputs" >&2
    fi

    echo "[U-MyoPS stage2 / nnU-Net v1 pathology]"
    UMYOPS_STAGE2_TASK_NAME="$(_resolve_umyo_stage2_task "${FOLD}")"
    S2BASE="${UMYO_REPO}/outputs/nnunet/output/nnUNet/${UMYOPS_STAGE2_DIM}/${UMYOPS_STAGE2_TASK_NAME}/${UMYOPS_STAGE2_TRAINER}__nnUNetPlansv2.1/fold_${FOLD}"
    DEST2="${MODELS_ROOT}/U-MyoPS/fold_${FOLD}/stage2"
    for f in model_final_checkpoint.model model_best.model model_latest.model; do
      _place "${S2BASE}/${f}" "${DEST2}" "${f}"
    done
    _place "${S2BASE}/validation_raw/summary.json" "${DEST2}" "validation_summary.json"
  fi
done

echo "=== Done. Weights under ${MODELS_ROOT} ==="
ls -la "${MODELS_ROOT}" 2>/dev/null || true
