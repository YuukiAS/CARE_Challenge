#!/usr/bin/env bash
# Refresh protocol + nnU-Net splits; submit all benchmark models for one fold (default 0).
#
# Models: nnU-Net v2 D501 + D502 (separate jobs), MyoPS-Net_D501, U-MyoPS-Stage1-D501 [+ Stage2 if UMYOPS_RUN_STAGE2=1], CineMyoPS_D502 (paper Task025).
#
# Prerequisites: nnUNetv2 plan_and_preprocess for 501/502; Task025 v1 preprocess runs here (unless CINE_SKIP_V1_PREPROCESS=1).
#
# Usage:
#   bash code/run_unified_benchmark_test.sh
# Env: FOLD (default 0), PREPARE (default 1), SKIP_CONVERT, CONFIG, CARE_ROOT_OVERRIDE
#       CARE_CONDA_ENV / CARE_CONDA_ENV_NNUNET_V1 — conda env prefixes for sbatch --export=ALL
#       CINE_SKIP_V1_PREPROCESS=1 — skip scripts/CineMyoPS/ensure_task025_v1_preprocessed.sh (CineMyoPS job must PREPARE raw itself)
#       CINE_FORCE_PREPROCESS=1 — redo nnU-Net v1 plan+preprocess for Task025
#       UMYOPS_RUN_STAGE2=1 — submit U-MyoPS-Stage2-D501 after Stage1 (afterok); default 0 in env_nnunet.sh
set -euo pipefail

_CARE_SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -n "${CARE_ROOT_OVERRIDE:-}" ]]; then
  CARE_ROOT="${CARE_ROOT_OVERRIDE}"
else
  CARE_ROOT="$(cd "${_CARE_SELF_DIR}/.." && pwd)"
fi
unset _CARE_SELF_DIR
if [[ ! -f "${CARE_ROOT}/env_nnunet.sh" ]]; then
  echo "error: CARE_ROOT=${CARE_ROOT} has no env_nnunet.sh." >&2
  echo "  Run from repo: .../code/$(basename "${BASH_SOURCE[0]}") or set CARE_ROOT_OVERRIDE=" >&2
  exit 1
fi
export CARE_ROOT
export FOLD="${FOLD:-0}"
export PREPARE="${PREPARE:-1}"

# shellcheck source=/dev/null
source "${CARE_ROOT}/env_nnunet.sh"

CARE_CONDA_ENV="${CARE_CONDA_ENV:-${CARE_ROOT}/env_CARE}"
CARE_CONDA_ENV_NNUNET_V1="${CARE_CONDA_ENV_NNUNET_V1:-${CARE_ROOT}/env_CARE_nnUNet_v1}"
# CineMyoPS (nnU-Net v1): passed through sbatch --export=ALL (see code/CineMyoPS/sbatch.sh).
export CARE_CineMyoPS_ENV="${CARE_CineMyoPS_ENV:-${CARE_CINEMYOPS_ENV:-${CARE_CONDA_ENV_NNUNET_V1}}}"

care_conda_activate() {
  local env_path="$1"
  command -v conda >/dev/null 2>&1 || return 0
  # shellcheck disable=SC2312
  eval "$(conda shell.bash hook)"
  conda activate "${env_path}"
}

export PATH="${CARE_ROOT}/env_CARE/bin:${PATH}"

echo "=== CARE unified benchmark — TEST (all models, FOLD=${FOLD}) ==="
bash "${CARE_ROOT}/code/run_unified_benchmark.sh" gen-protocol

echo "=== Write nnU-Net splits (requires preprocessed datasets) ==="
bash "${CARE_ROOT}/code/run_unified_benchmark.sh" write-splits-501 --backup
bash "${CARE_ROOT}/code/run_unified_benchmark.sh" write-splits-502 --backup

echo "=== Task025 (CineMyoPS paper): nnU-Net v1 raw + plan_and_preprocess ==="
bash "${CARE_ROOT}/scripts/CineMyoPS/ensure_task025_v1_preprocessed.sh"

echo "=== Submit Slurm jobs ==="
care_conda_activate "${CARE_CONDA_ENV}"
sbatch --export=ALL,CARE_ROOT,FOLD,SKIP_CONVERT,CONFIG \
  "${CARE_ROOT}/code/nnUNet/run_MyoPS.sh"
care_conda_activate "${CARE_CONDA_ENV}"
sbatch --export=ALL,CARE_ROOT,FOLD,SKIP_CONVERT,CONFIG \
  "${CARE_ROOT}/code/nnUNet/run_CineMyoPS.sh"

care_conda_activate "${CARE_CONDA_ENV}"
sbatch --export=ALL,CARE_ROOT,FOLD,PREPARE \
  "${CARE_ROOT}/code/MyoPS-Net/sbatch.sh"

# U-MyoPS: two Slurm jobs — U-MyoPS-Stage1-D501 + optional U-MyoPS-Stage2-D501 (afterok stage1 if UMYOPS_RUN_STAGE2=1).
care_conda_activate "${CARE_CONDA_ENV_NNUNET_V1}"
export CARE_CineMyoPS_ENV="${CARE_CineMyoPS_ENV:-${CARE_CONDA_ENV_NNUNET_V1}}"
_UMY_EXPORT="ALL,CARE_ROOT,FOLD,PREPARE,CARE_CineMyoPS_ENV,CARE_CINEMYOPS_ENV,UMYOPS_PYTHON,LEGACY_PYTHON"
UMYOPS_S1_JOB="$(sbatch --parsable --export="${_UMY_EXPORT}" "${CARE_ROOT}/code/U-MyoPS/sbatch_stage1.sh")"
echo "Submitted U-MyoPS Stage 1 job ${UMYOPS_S1_JOB}"
if [[ "${UMYOPS_RUN_STAGE2:-0}" == "1" ]]; then
  UMYOPS_S2_JOB="$(sbatch --parsable --dependency=afterok:"${UMYOPS_S1_JOB}" \
    --export=ALL,CARE_ROOT,FOLD,CARE_CineMyoPS_ENV,CARE_CINEMYOPS_ENV,UMYOPS_PYTHON,LEGACY_PYTHON,UMYOPS_STAGE2_TASK,UMYOPS_STAGE2_DIM,UMYOPS_STAGE2_TRAINER,UMYOPS_STAGE2_EPOCHS \
    "${CARE_ROOT}/code/U-MyoPS/sbatch_stage2.sh")"
  echo "Submitted U-MyoPS Stage 2 job ${UMYOPS_S2_JOB} (afterok:${UMYOPS_S1_JOB})"
else
  echo "U-MyoPS Stage 2 not submitted (set UMYOPS_RUN_STAGE2=1 to enable; requires v1 Task + prepro)."
fi

if [[ "${CINE_SKIP_V1_PREPROCESS:-0}" == "1" ]]; then
  _cin_prep="${PREPARE}"
else
  _cin_prep=0
fi
care_conda_activate "${CARE_CONDA_ENV_NNUNET_V1}"
sbatch --export=ALL,CARE_ROOT,FOLD,PREPARE="${_cin_prep}",CARE_CineMyoPS_ENV \
  "${CARE_ROOT}/code/CineMyoPS/sbatch.sh"

_UMY_EXTRA=""
_NJOBS=5
[[ "${UMYOPS_RUN_STAGE2:-0}" == "1" ]] && { _UMY_EXTRA=" + U-MyoPS-Stage2-D501"; _NJOBS=6; }
echo "Done. Submitted ${_NJOBS} jobs (nnUNet_D501, nnUNet_D502, MyoPS-Net_D501, U-MyoPS-Stage1-D501${_UMY_EXTRA}, CineMyoPS_D502)."
echo "Note: UMYOPS_RUN_STAGE2=${UMYOPS_RUN_STAGE2:-0} — if 1, Stage2 runs after Stage1 (Slurm afterok). Task: ${UMYOPS_STAGE2_TASK:-unset}."
echo "After training: bash \"${CARE_ROOT}/code/collect_benchmark_weights.sh\"  →  models/{nnUNet,CineMyoPS,MyoPS-Net,U-MyoPS}/"
