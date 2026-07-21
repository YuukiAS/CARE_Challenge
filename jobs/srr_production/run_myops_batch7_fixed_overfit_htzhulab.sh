#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=B7Fixed
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=04:00:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access

set -euo pipefail
CARE_ROOT="${CARE_ROOT:-/users/a/e/aereinh/CARE}"
cd "${CARE_ROOT}"
mkdir -p logs/srr_batch7
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/srr_batch7/B7Fixed_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1
source "${CARE_ROOT}/.care-codex-env.sh"
export PATH=/users/a/e/aereinh/CARE/envs/env_CARE/bin:$PATH
export PARTITION_LABEL=htzhulab
/users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/training/run_srr_batch7_fixed_overfit.py --device cuda
