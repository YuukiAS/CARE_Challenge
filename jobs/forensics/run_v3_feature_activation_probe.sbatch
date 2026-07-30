#!/bin/bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=V3FeatProbe
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

mkdir -p logs
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/V3FeatProbe_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "job_id=${SLURM_JOB_ID:-local}"
echo "host=$(hostname)"
echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "care_root=${CARE_ROOT}"
echo "python=$("${CARE_ROOT}/envs/env_CARE/bin/python" -c 'import sys; print(sys.executable)')"

export MPLCONFIGDIR=/tmp/care_mpl_${SLURM_JOB_ID:-local}
export PYTHONUNBUFFERED=1

"${CARE_ROOT}/envs/env_CARE/bin/python" \
  scripts/forensics/care_failure_forensics/run_v3_feature_activation_probe.py \
  --root "${CARE_ROOT}" \
  --device cuda \
  --train-cases 16 \
  --eval-cases 16

echo "end_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
