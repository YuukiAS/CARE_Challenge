#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=M10CineMA
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=08:00:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access
set -euo pipefail

CARE_ROOT="${CARE_ROOT:-/users/a/e/aereinh/CARE}"
cd "${CARE_ROOT}"
source "${CARE_ROOT}/.care-codex-env.sh"
source "${CARE_ROOT}/env_nnunet.sh"
export PATH=/users/a/e/aereinh/codex-runtime/bin:${CARE_ROOT}/envs/env_CARE/bin:${PATH}
mkdir -p logs
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/M10CineMA_${SLURM_JOB_ID:-local}_${TS}.log}"
export LOG_FILE
exec > >(tee -a "${LOG_FILE}") 2>&1

RUNTIME_ROOT="${M10_RUNTIME_ROOT:-results/20260711_srr_v3_m10_complete_mechanism_repair/runtime/m10_cine_temporal_executor}"
"${CARE_ROOT}/envs/env_CARE/bin/python" scripts/training/run_cinema_adapter_m10.py --out-root "${RUNTIME_ROOT}"
"${CARE_ROOT}/envs/env_CARE/bin/python" scripts/evaluation/aggregate_cine_m10_packet.py --phase cinema_adapter --runtime-root "${RUNTIME_ROOT}" --job-id "${SLURM_JOB_ID:-}" --job-state "${SLURM_JOB_STATE:-RUNNING}" --job-exit-code "${SLURM_JOB_EXIT_CODE:-}" --job-log "${LOG_FILE}" --partition "${SLURM_JOB_PARTITION:-htzhulab}"
