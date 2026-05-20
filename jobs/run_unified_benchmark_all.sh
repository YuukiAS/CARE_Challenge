#!/usr/bin/env bash
# Unified benchmark entrypoint for all folds (default 0..4).
#
# Lifecycle:
#   1. prep    -> refresh protocol + inject splits + ensure Task025 preprocessed
#   2. submit  -> submit training jobs for all requested folds
#   3. collect -> collect trained weights into models/
#   4. eval    -> sbatch GPU unified eval -> logs/UnifiedEval_<jobid>.log (UNIFIED_EVAL_LOCAL=1 for local)
#   5. post    -> collect + eval
#   6. full    -> prep + submit   (default)
#
# Examples:
#   bash jobs/run_unified_benchmark_all.sh
#   bash jobs/run_unified_benchmark_all.sh submit --folds "0 1 2 3 4"
#   bash jobs/run_unified_benchmark_all.sh post
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

# U-MyoPS Slurm submit mode when BENCHMARK_MODEL_PLAN has U-MyoPS=run (ignored if U-MyoPS is skip/eval).
#   stage1 -> only Stage 1 (sbatch_stage1.sh)
#   stage2 -> only Stage 2 (sbatch_stage2.sh); no afterok (use when Stage 1 is already done)
#   both   -> Stage 1 then Stage 2 with Slurm afterok on Stage 1
# Alias: all -> same as both
UMYOPS_BENCHMARK_STAGES="${UMYOPS_BENCHMARK_STAGES:-stage1}"

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

CARE_CONDA_ENV="${CARE_CONDA_ENV:-${CARE_ROOT}/envs/env_CARE}"
CARE_CONDA_ENV_NNUNET_V1="${CARE_CONDA_ENV_NNUNET_V1:-${CARE_ROOT}/envs/env_CARE_nnUNet_v1}"
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
  export PATH="${CARE_ROOT}/envs/env_CARE/bin:${PATH}"
  echo "=== CARE unified benchmark — PREP (FOLDS=${FOLDS}) ==="
  bash "${CARE_ROOT}/jobs/benchmark_protocol_helpers.sh" gen-protocol
  bash "${CARE_ROOT}/jobs/benchmark_protocol_helpers.sh" write-splits-501 --backup
  bash "${CARE_ROOT}/jobs/benchmark_protocol_helpers.sh" write-splits-502 --backup
  bash "${CARE_ROOT}/code/CineMyoPS/ensure_task025_v1_preprocessed.sh"
  bash "${CARE_ROOT}/jobs/benchmark_protocol_helpers.sh" write-splits-task025 --backup
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
        "${CARE_ROOT}/jobs/nnUNet/run_MyoPS.sh"
      care_conda_activate "${CARE_CONDA_ENV}"
      sbatch --export=ALL,CARE_ROOT,FOLD,SKIP_CONVERT,CONFIG \
        "${CARE_ROOT}/jobs/nnUNet/run_CineMyoPS.sh"
    else
      echo "Skip submit: nnUNet (FOLD=${FOLD})"
    fi

    if want_submit MyoPS-Net; then
      export PREPARE=1
      care_conda_activate "${CARE_CONDA_ENV}"
      sbatch --export=ALL,CARE_ROOT,FOLD,PREPARE \
        "${CARE_ROOT}/jobs/MyoPS-Net/sbatch.sh"
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
      _UMY_EXPORT="ALL,CARE_ROOT,FOLD,PREPARE,CARE_CineMyoPS_ENV,CARE_CINEMYOPS_ENV,UMYOPS_PYTHON,LEGACY_PYTHON,UMYOPS_NET,UMYOPS_DATA_SOURCE,UMYOPS_WEIGHT"
      _UMY_S2_EXPORT="ALL,CARE_ROOT,FOLD,CARE_CineMyoPS_ENV,CARE_CINEMYOPS_ENV,UMYOPS_PYTHON,LEGACY_PYTHON,UMYOPS_STAGE2_TASK,UMYOPS_STAGE2_PER_FOLD_TASK,UMYOPS_STAGE2_AUTO_PREP,UMYOPS_STAGE2_PRIOR_TAG,UMYOPS_STAGE2_FORCE_CLEAN,UMYOPS_STAGE2_PREPROCESS_TF,UMYOPS_STAGE2_PREPROCESS_TL,UMYOPS_STAGE2_DIM,UMYOPS_STAGE2_TRAINER,UMYOPS_STAGE2_EPOCHS,UMYOPS_NET,UMYOPS_DATA_SOURCE,UMYOPS_WEIGHT"
      case "${UMYOPS_BENCHMARK_STAGES}" in
        stage1)
          UMYOPS_S1_JOB="$(sbatch --parsable --export="${_UMY_EXPORT}" "${CARE_ROOT}/jobs/U-MyoPS/sbatch_stage1.sh")"
          echo "Submitted U-MyoPS Stage 1 job ${UMYOPS_S1_JOB} (FOLD=${FOLD})"
          ;;
        stage2)
          UMYOPS_S2_JOB="$(sbatch --parsable --export="${_UMY_S2_EXPORT}" "${CARE_ROOT}/jobs/U-MyoPS/sbatch_stage2.sh")"
          echo "Submitted U-MyoPS Stage 2 job ${UMYOPS_S2_JOB} (FOLD=${FOLD})"
          ;;
        both|all)
          UMYOPS_S1_JOB="$(sbatch --parsable --export="${_UMY_EXPORT}" "${CARE_ROOT}/jobs/U-MyoPS/sbatch_stage1.sh")"
          echo "Submitted U-MyoPS Stage 1 job ${UMYOPS_S1_JOB} (FOLD=${FOLD})"
          UMYOPS_S2_JOB="$(sbatch --parsable --dependency=afterok:"${UMYOPS_S1_JOB}" \
            --export="${_UMY_S2_EXPORT}" "${CARE_ROOT}/jobs/U-MyoPS/sbatch_stage2.sh")"
          echo "Submitted U-MyoPS Stage 2 job ${UMYOPS_S2_JOB} (afterok:${UMYOPS_S1_JOB}, FOLD=${FOLD})"
          ;;
        *)
          echo "Invalid UMYOPS_BENCHMARK_STAGES=${UMYOPS_BENCHMARK_STAGES} (use stage1, stage2, or both)" >&2
          exit 1
          ;;
      esac
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
        "${CARE_ROOT}/jobs/CineMyoPS/sbatch.sh"
    else
      echo "Skip submit: CineMyoPS (FOLD=${FOLD})"
    fi
  done

  local nfolds _jpf _umy
  nfolds=$(echo "${FOLDS}" | wc -w)
  _jpf=0
  want_submit nnUNet && _jpf=$((_jpf + 2))
  want_submit MyoPS-Net && _jpf=$((_jpf + 1))
  _umy=0
  if want_submit U-MyoPS; then
    case "${UMYOPS_BENCHMARK_STAGES}" in
      both|all) _umy=2 ;;
      stage1|stage2) _umy=1 ;;
    esac
  fi
  _jpf=$((_jpf + _umy))
  want_submit CineMyoPS && _jpf=$((_jpf + 1))
  echo "Submitted ~$((nfolds * _jpf)) jobs (approx; U-MyoPS mode=${UMYOPS_BENCHMARK_STAGES})."
}

run_collect() {
  echo "=== CARE unified benchmark — COLLECT (FOLDS=${FOLDS}) ==="
  local targets
  targets="$(collect_targets_csv)"
  if [[ -z "${targets}" ]]; then
    echo "No models enabled for collect."
    return 0
  fi
  bash "${CARE_ROOT}/jobs/collect_benchmark_weights.sh" --folds "${FOLDS}" --only "${targets}"
}

run_eval() {
  echo "=== CARE unified benchmark — EVAL (FOLDS=${FOLDS}) ==="
  local eval_models
  eval_models="$(eval_targets_words)"
  if [[ -z "${eval_models}" ]]; then
    echo "No models enabled for eval."
    return 0
  fi
  if [[ "${UNIFIED_EVAL_LOCAL:-0}" == "1" ]]; then
    MODELS="${eval_models}" FOLDS="${FOLDS}" \
      bash "${CARE_ROOT}/scripts/evaluation/run_unified_eval_all.sh"
    return 0
  fi
  export MODELS="${eval_models}"
  export FOLDS
  local job_id
  if [[ "${UNIFIED_EVAL_WAIT:-0}" == "1" ]]; then
    job_id="$(sbatch --wait --parsable "${CARE_ROOT}/jobs/evaluation/sbatch_unified_eval.sh")"
    echo "Unified eval GPU job ${job_id} finished. Log: ${CARE_ROOT}/logs/UnifiedEval_${job_id}.log"
  else
    job_id="$(sbatch --parsable "${CARE_ROOT}/jobs/evaluation/sbatch_unified_eval.sh")"
    echo "Submitted unified eval GPU job ${job_id}; log ${CARE_ROOT}/logs/UnifiedEval_${job_id}.log"
  fi
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
    bash "${CARE_ROOT}/jobs/benchmark_protocol_helpers.sh" print-all
    ;;
  *)
    echo "unknown action: ${ACTION}" >&2
    exit 1
    ;;
esac
