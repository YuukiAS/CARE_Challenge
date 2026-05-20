#!/usr/bin/env bash
# Shared steps: Task026 prepare (optional), plan/splits, train, optional export + unified eval.
# Expects: env_nnunet-compatible environment; CARE_ROOT set or derivable from this script location.
set -euo pipefail

if [[ -z "${CARE_ROOT:-}" ]]; then
  _HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  CARE_ROOT="$(cd "${_HERE}/../.." && pwd)"
fi
export CARE_ROOT
# shellcheck source=/dev/null
source "${CARE_ROOT}/env_nnunet.sh"

CARE_CineMyoPS_ENV="${CARE_CineMyoPS_ENV:-${CARE_CINEMYOPS_ENV:-${CARE_ROOT}/envs/env_CARE_nnUNet_v1}}"
export CARE_CineMyoPS_ENV
export PATH="${CARE_CineMyoPS_ENV}/bin:${PATH}"
PY="${CARE_CineMyoPS_ENV}/bin/python"
TASK="${CINE_NNUNET_TASK:-Task026_Cine_4D}"
BENCHMARK_TASK_ROOT="${CARE_ROOT}/data/benchmarks/CineMyoPS/${TASK}"
RAW_TASK_ROOT="${nnUNet_raw}/${TASK}"
PREPROCESSED_TASK_ROOT="${nnUNet_preprocessed}/${TASK}"
PLANS_2D="${PREPROCESSED_TASK_ROOT}/nnUNetPlansv2.1_plans_2D.pkl"
PLANS_2D_LEGACY="${PREPROCESSED_TASK_ROOT}/nnUNetPlans_plans_2D.pkl"
SPLIT_JSON="${CARE_ROOT}/data/benchmarks/protocol/splits_CineMyoPS.json"
FOLD="${FOLD:-0}"
export FOLD

export CINE_NUM_FRAMES="${CINE_NUM_FRAMES:-4}"
export CINE_NNUNET_TASK="${TASK}"
export CINE_NNUNET_TRAINER="${CINE_NNUNET_TRAINER:-CARECineMyoPSTrainer}"
export CINE_NNUNET_DIM="${CINE_NNUNET_DIM:-2d}"
export CINE_OUTPUT_MODEL="${CINE_OUTPUT_MODEL:-CineMyoPS}"

echo "run_task026_paper_steps: CARE_ROOT=$(readlink -f "${CARE_ROOT}")"
echo "run_task026_paper_steps: TASK=${TASK} FOLD=${FOLD} TRAINER=${CINE_NNUNET_TRAINER} OUTPUT_MODEL=${CINE_OUTPUT_MODEL} CINE_NUM_FRAMES=${CINE_NUM_FRAMES}"

if [[ ! -f "${SPLIT_JSON}" ]]; then
  "${PY}" "${CARE_ROOT}/scripts/benchmark/generate_splits.py" \
    --task CineMyoPS \
    --input-root "${CARE_ROOT}/data/CARE_Challenge/CineMyoPS_train" \
    --output-dir "$(dirname "${SPLIT_JSON}")" \
    --n-splits 5 \
    --random-state 42
fi

if [[ "${CINE_SKIP_PREPARE:-0}" != "1" ]]; then
  "${PY}" "${CARE_ROOT}/code/CineMyoPS/prepare_task026_cine_4d.py" \
    --input "${CARE_ROOT}/data/CARE_Challenge/CineMyoPS_train" \
    --output "${BENCHMARK_TASK_ROOT}" \
    --nnunet-raw-output "${RAW_TASK_ROOT}" \
    --num-frames "${CINE_NUM_FRAMES}"
else
  echo "CINE_SKIP_PREPARE=1: skipping prepare_task026_cine_4d.py"
fi

if [[ "${CINE_SKIP_PREPARE:-0}" != "1" && "${CINE_SKIP_SANITY:-0}" != "1" ]]; then
  "${PY}" "${CARE_ROOT}/code/CineMyoPS/sanity_check_task026.py" \
    --task-root "${BENCHMARK_TASK_ROOT}"
fi

if [[ ! -f "${PLANS_2D}" && -f "${PLANS_2D_LEGACY}" ]]; then
  ln -sfn "nnUNetPlans_plans_2D.pkl" "${PLANS_2D}"
fi

if [[ ! -f "${PLANS_2D}" ]]; then
  export PYTHONPATH="${CARE_ROOT}/third_party/CineMyoPS/code:${PYTHONPATH:-}"
  "${PY}" "${CARE_ROOT}/third_party/CineMyoPS/code/nnunet/experiment_planning/old/old_plan_and_preprocess_task.py" \
    -t "${TASK}" \
    -pl "${CINE_NNUNET_PL:-8}" \
    -pf "${CINE_NNUNET_PF:-8}" \
    -s 1
  if [[ -f "${PLANS_2D_LEGACY}" && ! -f "${PLANS_2D}" ]]; then
    ln -sfn "nnUNetPlans_plans_2D.pkl" "${PLANS_2D}"
  fi
fi

_SPLITS="${PREPROCESSED_TASK_ROOT}/splits_final.pkl"
if [[ ! -f "${_SPLITS}" ]]; then
  "${PY}" "${CARE_ROOT}/scripts/benchmark/nnunet_v1_write_splits_final.py" \
    --protocol-json "${SPLIT_JSON}" \
    --task-dir "${RAW_TASK_ROOT}" \
    --preprocessed-task-dir "${PREPROCESSED_TASK_ROOT}"
elif [[ "${CINE_FORCE_WRITE_SPLITS:-0}" == "1" ]]; then
  echo "CINE_FORCE_WRITE_SPLITS=1: rewriting ${_SPLITS} (backup existing)"
  "${PY}" "${CARE_ROOT}/scripts/benchmark/nnunet_v1_write_splits_final.py" \
    --protocol-json "${SPLIT_JSON}" \
    --task-dir "${RAW_TASK_ROOT}" \
    --preprocessed-task-dir "${PREPROCESSED_TASK_ROOT}" \
    --backup-existing
fi

export CINE_NNUNET_EPOCHS="${CINE_NNUNET_EPOCHS:-300}"
export CINE_PROTOCOL_SPLIT_JSON="${CINE_PROTOCOL_SPLIT_JSON:-${SPLIT_JSON}}"
echo "run_task026_paper_steps: starting training (epochs=${CINE_NNUNET_EPOCHS}, fold=${FOLD})"
bash "${CARE_ROOT}/code/CineMyoPS/run_train.sh" "$@"
echo "run_task026_paper_steps: training finished"

if [[ "${CINE_RUN_EXPORT_EVAL:-0}" == "1" ]]; then
  echo "===== export protocol val (fold ${FOLD}) ====="
  bash "${CARE_ROOT}/code/CineMyoPS/export_protocol_val_predictions.sh"
  echo "===== unified eval (Dataset502 GT, foreground 1,2,3; report class_1 = myocardium) ====="
  PY_EVAL="${CARE_EVAL_PYTHON:-${CARE_ROOT}/envs/env_CARE/bin/python}"
  EVAL_JSON="${CARE_ROOT}/results/metrics/unified/${CINE_OUTPUT_MODEL}/fold_${FOLD}/evaluation_summary.json"
  "${PY_EVAL}" "${CARE_ROOT}/scripts/evaluation/evaluate_predictions.py" \
    --pred-dir "${CARE_ROOT}/results/predictions/${CINE_OUTPUT_MODEL}/fold_${FOLD}" \
    --gt-dir "${nnUNet_raw}/Dataset502_CARECineMyoPS/labelsTr" \
    --fold-json "${SPLIT_JSON}" \
    --fold "${FOLD}" \
    --foreground-classes "1,2,3" \
    --output-dir "${CARE_ROOT}/results/metrics/unified/${CINE_OUTPUT_MODEL}/fold_${FOLD}"
  "${PY_EVAL}" "${CARE_ROOT}/scripts/evaluation/aggregate_folds.py" \
    --inputs "${EVAL_JSON}" \
    --output-json "${CARE_ROOT}/results/metrics/unified/${CINE_OUTPUT_MODEL}/aggregate.json" \
    --output-md "${CARE_ROOT}/results/metrics/unified/${CINE_OUTPUT_MODEL}/aggregate.md"
  echo "===== eval artifacts: ${EVAL_JSON} ====="
fi
