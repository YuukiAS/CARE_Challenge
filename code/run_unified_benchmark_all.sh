#!/usr/bin/env bash
# Unified benchmark entrypoint for all folds (default 0..4).
#
# Lifecycle:
#   1. prep    -> refresh protocol + inject splits + ensure Task025 preprocessed
#   2. submit  -> submit training jobs for all requested folds
#   3. collect -> collect trained weights into models/
#   4. eval    -> run unified offline evaluation on all requested folds
#   5. post    -> collect + eval
#   6. full    -> prep + submit   (default)
#
# Examples:
#   bash code/run_unified_benchmark_all.sh
#   bash code/run_unified_benchmark_all.sh submit --folds "0 1 2 3 4"
#   bash code/run_unified_benchmark_all.sh post
set -euo pipefail

export CARE_ROOT="/overflow/htzhu/CARE"

ACTION="full"
if [[ $# -gt 0 ]]; then
  case "$1" in
    prep|submit|collect|eval|post|full|print)
      ACTION="$1"
      shift
      ;;
  esac
fi

# Single source of truth for model participation in this script.
# Modes:
#   run  -> submit training, then later collect/eval
#   eval -> do not submit; only collect/eval existing results
#   skip -> ignore completely
BENCHMARK_MODEL_PLAN=(
  "nnUNet=run"
  "MyoPS-Net=run"
  "U-MyoPS=run"
  "CineMyoPS=run"
)

FOLDS="${FOLDS:-0 1 2 3 4}"
PREPARE_SHARE="${PREPARE_SHARE:-1}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --folds)
      FOLDS="${2:?}"
      shift 2
      ;;
    --prepare-share)
      PREPARE_SHARE="${2:?}"
      shift 2
      ;;
    -h|--help)
      sed -n '1,30p' "$0"
      exit 0
      ;;
    *)
      echo "unknown arg: $1" >&2
      exit 1
      ;;
  esac
done

# shellcheck source=/dev/null
source "${CARE_ROOT}/env_nnunet.sh"

CARE_CONDA_ENV="${CARE_CONDA_ENV:-${CARE_ROOT}/env_CARE}"
CARE_CONDA_ENV_NNUNET_V1="${CARE_CONDA_ENV_NNUNET_V1:-${CARE_ROOT}/env_CARE_nnUNet_v1}"
export CARE_CineMyoPS_ENV="${CARE_CineMyoPS_ENV:-${CARE_CINEMYOPS_ENV:-${CARE_CONDA_ENV_NNUNET_V1}}}"

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

plan_mode() {
  local model="$1" item key value
  for item in "${BENCHMARK_MODEL_PLAN[@]}"; do
    key="${item%%=*}"
    value="${item#*=}"
    if [[ "${key}" == "${model}" ]]; then
      echo "${value}"
      return 0
    fi
  done
  echo "skip"
}

want_submit() {
  [[ "$(plan_mode "$1")" == "run" ]]
}

want_post() {
  case "$(plan_mode "$1")" in
    run|eval) return 0 ;;
    *) return 1 ;;
  esac
}

collect_targets_csv() {
  local out=()
  want_post nnUNet && out+=(nnUNet)
  want_post CineMyoPS && out+=(CineMyoPS)
  want_post MyoPS-Net && out+=(MyoPS-Net)
  want_post U-MyoPS && out+=(U-MyoPS)
  local IFS=,
  echo "${out[*]}"
}

eval_targets_words() {
  local out=()
  if want_post nnUNet; then
    out+=(nnUNet501 nnUNet502)
  fi
  want_post MyoPS-Net && out+=(MyoPS-Net)
  want_post U-MyoPS && out+=(U-MyoPS)
  want_post CineMyoPS && out+=(CineMyoPS)
  echo "${out[*]}"
}

run_prep() {
  export PATH="${CARE_ROOT}/env_CARE/bin:${PATH}"
  echo "=== CARE unified benchmark — PREP (FOLDS=${FOLDS}) ==="
  bash "${CARE_ROOT}/code/run_unified_benchmark.sh" gen-protocol
  bash "${CARE_ROOT}/code/run_unified_benchmark.sh" write-splits-501 --backup
  bash "${CARE_ROOT}/code/run_unified_benchmark.sh" write-splits-502 --backup
  bash "${CARE_ROOT}/scripts/CineMyoPS/ensure_task025_v1_preprocessed.sh"
  bash "${CARE_ROOT}/code/run_unified_benchmark.sh" write-splits-task025 --backup
}

run_submit() {
  echo "=== CARE unified benchmark — SUBMIT (FOLDS=${FOLDS}) ==="
  local first_fold
  first_fold="$(echo "${FOLDS}" | awk '{print $1}')"

  for FOLD in ${FOLDS}; do
    export FOLD
    echo "--- FOLD=${FOLD} ---"

    if want_submit nnUNet; then
      care_conda_activate "${CARE_CONDA_ENV}"
      sbatch --export=ALL,CARE_ROOT,FOLD,SKIP_CONVERT,CONFIG \
        "${CARE_ROOT}/code/nnUNet/run_MyoPS.sh"
      care_conda_activate "${CARE_CONDA_ENV}"
      sbatch --export=ALL,CARE_ROOT,FOLD,SKIP_CONVERT,CONFIG \
        "${CARE_ROOT}/code/nnUNet/run_CineMyoPS.sh"
    else
      echo "Skip submit: nnUNet (FOLD=${FOLD})"
    fi

    if want_submit MyoPS-Net; then
      export PREPARE=1
      care_conda_activate "${CARE_CONDA_ENV}"
      sbatch --export=ALL,CARE_ROOT,FOLD,PREPARE \
        "${CARE_ROOT}/code/MyoPS-Net/sbatch.sh"
    else
      echo "Skip submit: MyoPS-Net (FOLD=${FOLD})"
    fi

    if want_submit U-MyoPS; then
      if [[ "${PREPARE_SHARE}" == "1" ]] && [[ "${FOLD}" != "${first_fold}" ]]; then
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
    else
      echo "Skip submit: U-MyoPS (FOLD=${FOLD})"
    fi

    if want_submit CineMyoPS; then
      if [[ "${PREPARE_SHARE}" == "1" ]] && [[ "${FOLD}" != "${first_fold}" ]]; then
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
    else
      echo "Skip submit: CineMyoPS (FOLD=${FOLD})"
    fi
  done

  local nfolds jpf
  nfolds=$(echo "${FOLDS}" | wc -w)
  jpf=5
  [[ "${UMYOPS_RUN_STAGE2:-0}" == "1" ]] && jpf=6
  echo "Submitted $((nfolds * jpf)) jobs."
}

run_collect() {
  echo "=== CARE unified benchmark — COLLECT (FOLDS=${FOLDS}) ==="
  local targets
  targets="$(collect_targets_csv)"
  if [[ -z "${targets}" ]]; then
    echo "No models enabled for collect."
    return 0
  fi
  bash "${CARE_ROOT}/code/collect_benchmark_weights.sh" --folds "${FOLDS}" --only "${targets}"
}

run_eval() {
  echo "=== CARE unified benchmark — EVAL (FOLDS=${FOLDS}) ==="
  local eval_models
  eval_models="$(eval_targets_words)"
  if [[ -z "${eval_models}" ]]; then
    echo "No models enabled for eval."
    return 0
  fi
  MODELS="${eval_models}" FOLDS="${FOLDS}" \
    bash "${CARE_ROOT}/scripts/evaluation/run_unified_eval_all.sh"
}

case "${ACTION}" in
  prep)
    run_prep
    ;;
  submit)
    run_submit
    ;;
  collect)
    run_collect
    ;;
  eval)
    run_eval
    ;;
  post)
    run_collect
    run_eval
    ;;
  full)
    run_prep
    run_submit
    ;;
  print)
    bash "${CARE_ROOT}/code/run_unified_benchmark.sh" print-all
    ;;
  *)
    echo "unknown action: ${ACTION}" >&2
    exit 1
    ;;
esac
