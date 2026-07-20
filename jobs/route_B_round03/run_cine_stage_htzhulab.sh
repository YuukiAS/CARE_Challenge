#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=RBCineLab
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=08:00:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access

set -euo pipefail
CARE_ROOT="/users/a/e/aereinh/CARE_worktrees/route_B"
MAIN_CARE_ROOT="/users/a/e/aereinh/CARE"
cd "${CARE_ROOT}"
mkdir -p logs/route_B_round03
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/route_B_round03/RouteBCineLab_${ROUTE_B_EXECUTOR:-Bx}_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1
source "${MAIN_CARE_ROOT}/.care-codex-env.sh"
source "${MAIN_CARE_ROOT}/env_nnunet.sh"
export PATH="/users/a/e/aereinh/codex-runtime/bin:${MAIN_CARE_ROOT}/envs/env_CARE/bin:${PATH}"
CARE_PYTHON="${MAIN_CARE_ROOT}/envs/env_CARE/bin/python"
: "${ROUTE_B_EXECUTOR:?missing ROUTE_B_EXECUTOR}"
: "${ROUTE_B_CINE_TASK:?missing ROUTE_B_CINE_TASK}"
: "${ROUTE_B_CONFIG:?missing ROUTE_B_CONFIG}"
: "${ROUTE_B_OUT:?missing ROUTE_B_OUT}"
"${CARE_PYTHON}" scripts/route_B_round03/preflight.py --executor "${ROUTE_B_EXECUTOR}" --partition "${SLURM_JOB_PARTITION:-htzhulab}" --config "${ROUTE_B_CONFIG}" --out "results/route_B/round03/executors/${ROUTE_B_EXECUTOR}/preflight_${SLURM_JOB_PARTITION:-htzhulab}.json"
case "${ROUTE_B_CINE_TASK}" in
  cinema_control)
    "${CARE_PYTHON}" scripts/training/route_B_round03/train_cinema_control.py --sources pretrained random --steps 8000 --config "${ROUTE_B_CONFIG}" --out "${ROUTE_B_OUT}"
    "${CARE_PYTHON}" scripts/validation/route_B_round03/validate_cinema_control.py --strict results/route_B/round03/executors/B7
    ;;
  registration)
    : "${ROUTE_B_SOURCE:?missing ROUTE_B_SOURCE}"
    "${CARE_PYTHON}" scripts/training/route_B_round03/train_registration.py --steps 25000 --source "${ROUTE_B_SOURCE}" --config "${ROUTE_B_CONFIG}" --out "${ROUTE_B_OUT}"
    "${CARE_PYTHON}" scripts/validation/route_B_round03/validate_registration.py --strict results/route_B/round03/executors/B8
    ;;
  temporal)
    : "${ROUTE_B_REGISTRATION:?missing ROUTE_B_REGISTRATION}"
    "${CARE_PYTHON}" scripts/training/route_B_round03/train_temporal.py --targets 4000 8000 12000 16000 20000 --registration "${ROUTE_B_REGISTRATION}" --config "${ROUTE_B_CONFIG}" --out "${ROUTE_B_OUT}"
    "${CARE_PYTHON}" scripts/validation/route_B_round03/validate_temporal.py --strict results/route_B/round03/executors/B9
    ;;
  *)
    echo "unknown ROUTE_B_CINE_TASK=${ROUTE_B_CINE_TASK}" >&2
    exit 2
    ;;
esac
