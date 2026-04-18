#!/usr/bin/env bash
# Collect trained benchmark weights into ${CARE_ROOT}/models/{nnUNet,CineMyoPS,MyoPS-Net,U-MyoPS}/...
# Aligns with code/run_unified_benchmark_{test,all}.sh job layout (FOLD / env_nnunet.sh).
#
# Usage (repo root or any cwd):
#   bash code/collect_benchmark_weights.sh
#   bash code/collect_benchmark_weights.sh --folds "0 1 2 3 4"
#   COLLECT_MODE=copy bash code/collect_benchmark_weights.sh   # copy instead of symlink
#   bash code/collect_benchmark_weights.sh --only nnUNet,CineMyoPS
#
# Env (optional): CARE_ROOT, CARE_ROOT_OVERRIDE, FOLD, FOLDS, COLLECT_MODE=symlink|copy,
#   CONFIG (nnUNet v2, default 3d_fullres), CARE_NNUNET_TRAINER,
#   CINE_NNUNET_TASK, UMYOPS_STAGE2_TASK, UMYOPS_STAGE2_TRAINER, UMYOPS_STAGE2_DIM,
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
CINE_NNUNET_TASK="${CINE_NNUNET_TASK:-Task025_Cine_Seg}"
UMYOPS_STAGE2_TASK="${UMYOPS_STAGE2_TASK:-Task901_CARE_UmyopsPathology}"
UMYOPS_STAGE2_TRAINER="${UMYOPS_STAGE2_TRAINER:-nnUNetTrainerPSNV8}"
UMYOPS_STAGE2_DIM="${UMYOPS_STAGE2_DIM:-2d}"
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

echo "=== CARE collect_benchmark_weights ==="
echo "CARE_ROOT=${CARE_ROOT} MODELS_ROOT=${MODELS_ROOT} COLLECT_MODE=${COLLECT_MODE}"
echo "FOLDS=${FOLDS} CONFIG=${CONFIG} CARE_NNUNET_TRAINER=${CARE_NNUNET_TRAINER}"

for FOLD in ${FOLDS}; do
  echo "--- fold ${FOLD} ---"

  if _want nnUNet; then
    echo "[nnUNet v2]"
    D501="${NNRES}/Dataset501_CAREMyoPS/${CARE_NNUNET_TRAINER}__nnUNetPlans__${CONFIG}/fold_${FOLD}"
    D502="${NNRES}/Dataset502_CARECineMyoPS/${CARE_NNUNET_TRAINER}__nnUNetPlans__${CONFIG}/fold_${FOLD}"
    DEST501="${MODELS_ROOT}/nnUNet/Dataset501_CAREMyoPS_${CONFIG}_fold${FOLD}"
    DEST502="${MODELS_ROOT}/nnUNet/Dataset502_CARECineMyoPS_${CONFIG}_fold${FOLD}"
    for f in checkpoint_final.pth checkpoint_best.pth; do
      _place "${D501}/${f}" "${DEST501}" "${f}"
      _place "${D502}/${f}" "${DEST502}" "${f}"
    done
  fi

  if _want CineMyoPS; then
    echo "[CineMyoPS / nnU-Net v1 Task025]"
    CINE="${NNRES}/nnUNet/2d/${CINE_NNUNET_TASK}/nnUNetTrainerV2__nnUNetPlansv2.1/fold_${FOLD}"
    DESTC="${MODELS_ROOT}/CineMyoPS/${CINE_NNUNET_TASK}_fold${FOLD}"
    for f in model_final_checkpoint.model model_best.model model_latest.model; do
      _place "${CINE}/${f}" "${DESTC}" "${f}"
    done
  fi

  if _want MyoPS-Net; then
    echo "[MyoPS-Net]"
    # Training cwd is third_party/MyoPS-Net; checkpoints/ is shared across folds if you re-run jobs.
    CKPT_DIR="${MYOPSNET_REPO}/checkpoints"
    DESTM="${MODELS_ROOT}/MyoPS-Net/fold_${FOLD}"
    if [[ -d "${CKPT_DIR}" ]]; then
      shopt -s nullglob
      _n_myops=0
      for p in "${CKPT_DIR}"/*.pth; do
        _place "${p}" "${DESTM}" "$(basename "${p}")"
        _n_myops=$((_n_myops + 1))
      done
      shopt -u nullglob
      if [[ "${_n_myops}" -eq 0 ]]; then
        echo "  (no .pth under ${CKPT_DIR}; MyoPS-Net saves only when val dice > threshold)" >&2
      fi
    else
      echo "  skip: no directory ${CKPT_DIR}" >&2
    fi
  fi

  if _want U-MyoPS; then
    echo "[U-MyoPS stage1]"
    MID="asn_myo_tps_${UMYOPS_NET}_${UMYOPS_DATA_SOURCE}_${UMYOPS_WEIGHT}_fold${FOLD}"
    S1CK="${UMYO_REPO}/outputs/${MID}/checkpoint"
    DEST1="${MODELS_ROOT}/U-MyoPS/stage1_${MID}"
    if [[ -d "${S1CK}" ]]; then
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
      echo "  skip: no ${S1CK}" >&2
    fi

    echo "[U-MyoPS stage2 / nnU-Net v1 pathology]"
    S2BASE="${UMYO_REPO}/outputs/nnunet/output/nnUNet/${UMYOPS_STAGE2_DIM}/${UMYOPS_STAGE2_TASK}/${UMYOPS_STAGE2_TRAINER}__nnUNetPlansv2.1/fold_${FOLD}"
    DEST2="${MODELS_ROOT}/U-MyoPS/stage2_${UMYOPS_STAGE2_TASK}_${UMYOPS_STAGE2_DIM}_fold${FOLD}"
    for f in model_final_checkpoint.model model_best.model model_latest.model; do
      _place "${S2BASE}/${f}" "${DEST2}" "${f}"
    done
  fi
done

echo "=== Done. Weights under ${MODELS_ROOT} ==="
ls -la "${MODELS_ROOT}" 2>/dev/null || true
