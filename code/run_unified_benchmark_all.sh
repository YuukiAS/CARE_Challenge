#!/usr/bin/env bash
# Refresh protocol + nnU-Net splits; submit all benchmark models for each fold (default 0–4).
#
# Per fold: nnU-Net v2 D501 + D502 (two jobs), MyoPS-Net_D501, U-MyoPS-Stage1-D501 [+ Stage2 if UMYOPS_RUN_STAGE2=1], CineMyoPS_D502
# (prepare only on the first fold in FOLDS to avoid redundant IO; set PREPARE_SHARE=0 to always PREPARE=1).
#
# Prerequisites: nnUNet v2 plan_and_preprocess for 501/502; Task025 v1 preprocess runs once below (unless CINE_SKIP_V1_PREPROCESS=1).
#
# Usage:
#   bash code/run_unified_benchmark_all.sh
# Env: SKIP_CONVERT, CONFIG, FOLDS (space-separated, default "0 1 2 3 4"), PREPARE_SHARE (default 1)
#       CARE_ROOT_OVERRIDE — optional alternate repo root (must contain env_nnunet.sh); ignores inherited CARE_ROOT
#       CARE_CONDA_ENV / CARE_CONDA_ENV_NNUNET_V1 — conda env prefixes (defaults under CARE_ROOT)
#       CINE_SKIP_V1_PREPROCESS, CINE_FORCE_PREPROCESS — see scripts/CineMyoPS/ensure_task025_v1_preprocessed.sh
#       UMYOPS_RUN_STAGE2=1 — also submit U-MyoPS-Stage2-D501 after Stage1 (Slurm afterok); default 0 in env_nnunet.sh
set -euo pipefail

_CARE_SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -n "${CARE_ROOT_OVERRIDE:-}" ]]; then
  CARE_ROOT="${CARE_ROOT_OVERRIDE}"
else
  CARE_ROOT="$(cd "${_CARE_SELF_DIR}/.." && pwd)"
fi
unset _CARE_SELF_DIR
if [[ ! -f "${CARE_ROOT}/env_nnunet.sh" ]]; then
  echo "error: CARE_ROOT=${CARE_ROOT} has no env_nnunet.sh (expected .../code/$(basename "${BASH_SOURCE[0]}") inside the repo)." >&2
  echo "  Or set CARE_ROOT_OVERRIDE=/path/to/CARE" >&2
  exit 1
fi
export CARE_ROOT

# shellcheck source=/dev/null
source "${CARE_ROOT}/env_nnunet.sh"

CARE_CONDA_ENV="${CARE_CONDA_ENV:-${CARE_ROOT}/env_CARE}"
CARE_CONDA_ENV_NNUNET_V1="${CARE_CONDA_ENV_NNUNET_V1:-${CARE_ROOT}/env_CARE_nnUNet_v1}"
export CARE_CineMyoPS_ENV="${CARE_CineMyoPS_ENV:-${CARE_CINEMYOPS_ENV:-${CARE_CONDA_ENV_NNUNET_V1}}}"

# Match submit-shell env to the job before sbatch --export=ALL (optional if conda is on PATH).
_care_conda_hook_done=0
care_conda_activate() {
  local env_path="$1"
  command -v conda >/dev/null 2>&1 || return 0
  if [[ "${_care_conda_hook_done}" -eq 0 ]]; then
    # shellcheck disable=SC2312
    eval "$(conda shell.bash hook)"
    _care_conda_hook_done=1
  fi
  conda activate "${env_path}"
}

FOLDS="${FOLDS:-0 1 2 3 4}"
PREPARE_SHARE="${PREPARE_SHARE:-1}"
FIRST_FOLD="$(echo "${FOLDS}" | awk '{print $1}')"

echo "=== Refresh protocol + nnU-Net splits (shared across folds) ==="
bash "${CARE_ROOT}/code/run_unified_benchmark.sh" gen-protocol
bash "${CARE_ROOT}/code/run_unified_benchmark.sh" write-splits-501 --backup
bash "${CARE_ROOT}/code/run_unified_benchmark.sh" write-splits-502 --backup

echo "=== Task025 (CineMyoPS paper): nnU-Net v1 raw + plan_and_preprocess (once per run) ==="
bash "${CARE_ROOT}/scripts/CineMyoPS/ensure_task025_v1_preprocessed.sh"

echo "=== Submit all models for each fold (FOLDS=${FOLDS}) ==="
for FOLD in ${FOLDS}; do
  export FOLD
  echo "--- FOLD=${FOLD} ---"
  care_conda_activate "${CARE_CONDA_ENV}"
  sbatch --export=ALL,CARE_ROOT,FOLD,SKIP_CONVERT,CONFIG \
    "${CARE_ROOT}/code/nnUNet/run_MyoPS.sh"
  care_conda_activate "${CARE_CONDA_ENV}"
  sbatch --export=ALL,CARE_ROOT,FOLD,SKIP_CONVERT,CONFIG \
    "${CARE_ROOT}/code/nnUNet/run_CineMyoPS.sh"

  export PREPARE=1
  care_conda_activate "${CARE_CONDA_ENV}"
  sbatch --export=ALL,CARE_ROOT,FOLD,PREPARE \
    "${CARE_ROOT}/code/MyoPS-Net/sbatch.sh"

  if [[ "${PREPARE_SHARE}" == "1" ]] && [[ "${FOLD}" != "${FIRST_FOLD}" ]]; then
    export PREPARE=0
  else
    export PREPARE=1
  fi
  care_conda_activate "${CARE_CONDA_ENV_NNUNET_V1}"
  export CARE_CineMyoPS_ENV="${CARE_CineMyoPS_ENV:-${CARE_CONDA_ENV_NNUNET_V1}}"
  _UMY_EXPORT="ALL,CARE_ROOT,FOLD,PREPARE,CARE_CineMyoPS_ENV,CARE_CINEMYOPS_ENV,UMYOPS_PYTHON,LEGACY_PYTHON"
  UMYOPS_S1_JOB="$(sbatch --parsable --export="${_UMY_EXPORT}" "${CARE_ROOT}/code/U-MyoPS/sbatch_stage1.sh")"
  echo "Submitted U-MyoPS Stage 1 job ${UMYOPS_S1_JOB} (FOLD=${FOLD})"
  if [[ "${UMYOPS_RUN_STAGE2:-0}" == "1" ]]; then
    UMYOPS_S2_JOB="$(sbatch --parsable --dependency=afterok:"${UMYOPS_S1_JOB}" \
      --export=ALL,CARE_ROOT,FOLD,CARE_CineMyoPS_ENV,CARE_CINEMYOPS_ENV,UMYOPS_PYTHON,LEGACY_PYTHON,UMYOPS_STAGE2_TASK,UMYOPS_STAGE2_DIM,UMYOPS_STAGE2_TRAINER,UMYOPS_STAGE2_EPOCHS \
      "${CARE_ROOT}/code/U-MyoPS/sbatch_stage2.sh")"
    echo "Submitted U-MyoPS Stage 2 job ${UMYOPS_S2_JOB} (afterok:${UMYOPS_S1_JOB}, FOLD=${FOLD})"
  fi

  if [[ "${PREPARE_SHARE}" == "1" ]] && [[ "${FOLD}" != "${FIRST_FOLD}" ]]; then
    export PREPARE=0
  else
    export PREPARE=1
  fi
  if [[ "${CINE_SKIP_V1_PREPROCESS:-0}" == "1" ]]; then
    _cin_prep="${PREPARE}"
  else
    _cin_prep=0
  fi
  care_conda_activate "${CARE_CONDA_ENV_NNUNET_V1}"
  sbatch --export=ALL,CARE_ROOT,FOLD,PREPARE="${_cin_prep}",CARE_CineMyoPS_ENV \
    "${CARE_ROOT}/code/CineMyoPS/sbatch.sh"
done

nfolds=$(echo "${FOLDS}" | wc -w)
_JPF=5
[[ "${UMYOPS_RUN_STAGE2:-0}" == "1" ]] && _JPF=6
echo "Submitted $((nfolds * _JPF)) jobs (${nfolds} folds × ${_JPF} Slurm scripts: nnUNet_D501, nnUNet_D502, MyoPS-Net_D501, U-MyoPS-Stage1-D501[, Stage2 if UMYOPS_RUN_STAGE2=1], CineMyoPS_D502)."
echo "Collect weights (all folds): bash \"${CARE_ROOT}/code/collect_benchmark_weights.sh\" --folds \"${FOLDS}\""
