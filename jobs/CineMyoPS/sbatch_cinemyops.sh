#!/bin/bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=CineMyoPS_paper
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=2-00:00:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access
set -euo pipefail

if [[ "${1:-}" == "--help" ]]; then
  cat <<'EOF'
Usage: sbatch jobs/CineMyoPS/sbatch_cinemyops.sh

Environment:
  FOLD                  Fold index, default 0
  CINE_NUM_FRAMES       Sampled cine frames, default 4
  CINE_SKIP_SANITY      If 1, skip Task026 sanity_check_task026.py
  CINE_NNUNET_EPOCHS    Trainer epochs, default 500
  CARE_MAX_BATCH_SIZE   CARE trainer caps nnU-Net planned batch_size (default 2); increase only if GPU allows
EOF
  exit 0
fi

THIS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CARE_ROOT="${CARE_ROOT:-$(cd "${THIS_DIR}/../.." && pwd)}"
cd "${CARE_ROOT}"
source "${CARE_ROOT}/env_nnunet.sh"

CARE_CineMyoPS_ENV="${CARE_CineMyoPS_ENV:-${CARE_CINEMYOPS_ENV:-${CARE_ROOT}/env_CARE_nnUNet_v1}}"
export PATH="${CARE_CineMyoPS_ENV}/bin:${PATH}"
export CARE_CineMyoPS_ENV
export PYTHONUNBUFFERED=1

mkdir -p "${CARE_ROOT}/logs"
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/CineMyoPS_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

PY="${CARE_CineMyoPS_ENV}/bin/python"
TASK="${CINE_NNUNET_TASK:-Task026_Cine_4D}"
BENCHMARK_TASK_ROOT="${CARE_ROOT}/data/benchmarks/CineMyoPS/${TASK}"
RAW_TASK_ROOT="${nnUNet_raw}/${TASK}"
PREPROCESSED_TASK_ROOT="${nnUNet_preprocessed}/${TASK}"
PLANS_2D="${PREPROCESSED_TASK_ROOT}/nnUNetPlansv2.1_plans_2D.pkl"
PLANS_2D_LEGACY="${PREPROCESSED_TASK_ROOT}/nnUNetPlans_plans_2D.pkl"
SPLIT_JSON="${CARE_ROOT}/data/benchmarks/protocol/splits_CineMyoPS.json"
FOLD="${FOLD:-0}"

export CINE_NUM_FRAMES="${CINE_NUM_FRAMES:-4}"
export CINE_NNUNET_TASK="${TASK}"
export CINE_NNUNET_TRAINER="${CINE_NNUNET_TRAINER:-CARECineMyoPSTrainer}"
export CINE_NNUNET_DIM="${CINE_NNUNET_DIM:-2d}"

echo "paper sbatch repo root: $(readlink -f "${CARE_ROOT}")"
echo "paper sbatch benchmark task: $(readlink -f "${BENCHMARK_TASK_ROOT}")"
echo "paper sbatch raw task: $(readlink -f "${RAW_TASK_ROOT}")"
echo "paper sbatch preprocessed task: $(readlink -f "${PREPROCESSED_TASK_ROOT}")"
echo "paper sbatch split json: $(readlink -f "${SPLIT_JSON}")"
echo "paper sbatch log file: $(readlink -f "${LOG_FILE}")"

if [[ ! -f "${SPLIT_JSON}" ]]; then
  "${PY}" "${CARE_ROOT}/scripts/benchmark/generate_splits.py" \
    --task CineMyoPS \
    --input-root "${CARE_ROOT}/data/CARE_Challenge/CineMyoPS_train" \
    --output-dir "$(dirname "${SPLIT_JSON}")" \
    --n-splits 5 \
    --random-state 42
fi

"${PY}" "${CARE_ROOT}/code/CineMyoPS/prepare_task026_cine_4d.py" \
  --input "${CARE_ROOT}/data/CARE_Challenge/CineMyoPS_train" \
  --output "${BENCHMARK_TASK_ROOT}" \
  --nnunet-raw-output "${RAW_TASK_ROOT}" \
  --num-frames "${CINE_NUM_FRAMES}"

if [[ "${CINE_SKIP_SANITY:-0}" != "1" ]]; then
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

if [[ ! -f "${PREPROCESSED_TASK_ROOT}/splits_final.pkl" ]]; then
  "${PY}" "${CARE_ROOT}/scripts/benchmark/nnunet_v1_write_splits_final.py" \
    --protocol-json "${SPLIT_JSON}" \
    --task-dir "${RAW_TASK_ROOT}" \
    --preprocessed-task-dir "${PREPROCESSED_TASK_ROOT}"
fi

bash "${CARE_ROOT}/code/CineMyoPS/run_train.sh" "$@"
