#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=B6Formal300
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=04:00:00
#SBATCH --gres=gpu:nvidia_a100-pcie-40gb:1
#SBATCH --partition=a100-gpu
#SBATCH --qos=gpu_access

set -euo pipefail
CARE_ROOT="${CARE_ROOT:-/users/a/e/aereinh/CARE}"
cd "${CARE_ROOT}"
mkdir -p logs/srr_batch6
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/srr_batch6/B6Formal300A100_${SLURM_JOB_ID:-local}_${TS}.log}"
export LOG_FILE BATCH6_STAGE=300 PARTITION_LABEL=a100-gpu
exec > >(tee -a "${LOG_FILE}") 2>&1
bash jobs/srr_production/run_myops_batch6_formal_common.sh
