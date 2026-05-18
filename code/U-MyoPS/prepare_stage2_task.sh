#!/usr/bin/env bash
# Build a fold-specific U-MyoPS Stage2 raw task and run nnU-Net v1 plan_and_preprocess.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CARE_ROOT="${CARE_ROOT:-$(cd "${SCRIPT_DIR}/../.." && pwd)}"
# shellcheck source=/dev/null
source "${CARE_ROOT}/env_nnunet.sh"

_V1_ENV="${CARE_CineMyoPS_ENV:-${CARE_CINEMYOPS_ENV:-${CARE_ROOT}/env_CARE_nnUNet_v1}}"
PY="${LEGACY_PYTHON:-${_V1_ENV}/bin/python}"
REPO="${CARE_ROOT}/third_party/U-MyoPS_myops"
FOLD="${FOLD:-0}"

resolve_stage2_task_name() {
  local base="${UMYOPS_STAGE2_TASK:-Task901_CARE_UmyopsPathology}"
  if [[ "${UMYOPS_STAGE2_PER_FOLD_TASK:-1}" == "1" ]]; then
    printf '%s_fold%s\n' "${base}" "${FOLD}"
  else
    printf '%s\n' "${base}"
  fi
}

TASK_NAME="${UMYOPS_STAGE2_TASK_NAME:-$(resolve_stage2_task_name)}"
TASK_ID="$(echo "${TASK_NAME}" | sed -E 's/^Task([0-9]+).*/\1/')"
[[ -n "${TASK_ID}" ]] || {
  echo "error: unable to parse task id from ${TASK_NAME}" >&2
  exit 1
}

export nnUNet_raw_data_base="${UMYOPS_NNUNET_RAW_BASE:-${REPO}/outputs/nnunet/raw}"
export nnUNet_preprocessed="${UMYOPS_NNUNET_PREPROCESSED:-${REPO}/outputs/nnunet/prepro}"
export RESULTS_FOLDER="${UMYOPS_NNUNET_RESULTS:-${REPO}/outputs/nnunet/output}"
export PYTHONPATH="${REPO}/jrs:${REPO}:${PYTHONPATH:-}"
VERIFY_DATASET="${UMYOPS_STAGE2_VERIFY_DATASET:-1}"

RAW_TASK_DIR="${nnUNet_raw_data_base}/nnUNet_raw_data/${TASK_NAME}"
PREPRO_TASK_DIR="${nnUNet_preprocessed}/${TASK_NAME}"

echo "===== U-MyoPS Stage2 prep ====="
echo "PY=${PY}"
echo "FOLD=${FOLD}"
echo "TASK_NAME=${TASK_NAME}"
echo "RAW_TASK_DIR=${RAW_TASK_DIR}"
echo "PREPRO_TASK_DIR=${PREPRO_TASK_DIR}"
echo "VERIFY_DATASET=${VERIFY_DATASET}"
echo "SKIP_BUILD=${UMYOPS_STAGE2_SKIP_BUILD:-0}"
echo "SKIP_PREPROCESS=${UMYOPS_STAGE2_SKIP_PREPROCESS:-0}"

UMYOPS_STAGE2_TASK="${UMYOPS_STAGE2_TASK:-Task901_CARE_UmyopsPathology}"
export UMYOPS_STAGE2_TASK
if [[ "${UMYOPS_STAGE2_SKIP_BUILD:-0}" != "1" ]]; then
  build_cmd=(
    "${PY}" "${CARE_ROOT}/code/U-MyoPS/build_stage2_task_from_stage1.py"
    --fold "${FOLD}"
    --base-task-name "${UMYOPS_STAGE2_TASK}"
    --task-root-base "${nnUNet_raw_data_base}/nnUNet_raw_data"
    --stage1-net "${UMYOPS_NET:-tps}"
    --stage1-data-source "${UMYOPS_DATA_SOURCE:-ZS_unaligned}"
    --stage1-weight "${UMYOPS_WEIGHT:-1.0}"
    --prior-tag "${UMYOPS_STAGE2_PRIOR_TAG:-img_de_branch_lab}"
    --input-variant "${UMYOPS_STAGE2_INPUT_VARIANT:-existing_full}"
  )
  if [[ -n "${UMYOPS_STAGE2_PRIOR_DILATION_RADIUS_XY:-}" ]]; then
    build_cmd+=( --prior-dilation-radius-xy "${UMYOPS_STAGE2_PRIOR_DILATION_RADIUS_XY}" )
  fi
  if [[ "${UMYOPS_STAGE2_PER_FOLD_TASK:-1}" == "1" ]]; then
    build_cmd+=( --per-fold-task )
  fi
  if [[ "${UMYOPS_STAGE2_FORCE_CLEAN:-1}" == "1" ]]; then
    build_cmd+=( --force-clean )
  fi
  "${build_cmd[@]}"
else
  echo "Skipping raw task build; using existing RAW_TASK_DIR=${RAW_TASK_DIR}"
fi

cd "${REPO}/jrs"
preprocess_cmd=(
  "${PY}" -m nnunet.experiment_planning.nnUNet_plan_and_preprocess
  -t "${TASK_ID}"
  -tf "${UMYOPS_STAGE2_PREPROCESS_TF:-8}"
  -tl "${UMYOPS_STAGE2_PREPROCESS_TL:-8}"
)
if [[ "${UMYOPS_STAGE2_DIM:-2d}" == "2d" ]]; then
  preprocess_cmd+=( -pl3d None -pl2d ExperimentPlanner2D_v21 )
else
  preprocess_cmd+=( -pl3d ExperimentPlanner3D_v21 -pl2d None )
fi
if [[ "${VERIFY_DATASET}" == "1" ]]; then
  preprocess_cmd+=( --verify_dataset_integrity )
fi
if [[ "${UMYOPS_STAGE2_SKIP_PREPROCESS:-0}" != "1" ]]; then
  "${preprocess_cmd[@]}"
else
  echo "Skipping preprocessing; using existing PREPRO_TASK_DIR=${PREPRO_TASK_DIR}"
fi

if [[ -n "${UMYOPS_STAGE2_BATCH_SIZE:-}" ]]; then
  if [[ "${UMYOPS_STAGE2_DIM:-2d}" == "2d" ]]; then
    _PLANS_FILE="${PREPRO_TASK_DIR}/nnUNetPlansv2.1_plans_2D.pkl"
  else
    _PLANS_FILE="${PREPRO_TASK_DIR}/nnUNetPlansv2.1_plans_3D.pkl"
  fi
  "${PY}" "${CARE_ROOT}/code/U-MyoPS/clamp_stage2_plans_batch_size.py" \
    --plans "${_PLANS_FILE}" \
    --batch-size "${UMYOPS_STAGE2_BATCH_SIZE}"
fi

"${PY}" "${CARE_ROOT}/scripts/benchmark/nnunet_v1_write_splits_final.py" \
  --protocol-json "${CARE_ROOT}/data/benchmarks/protocol/splits_MyoPS.json" \
  --task-dir "${RAW_TASK_DIR}" \
  --preprocessed-task-dir "${PREPRO_TASK_DIR}" \
  --backup-existing

echo "===== U-MyoPS Stage2 prep done ====="
