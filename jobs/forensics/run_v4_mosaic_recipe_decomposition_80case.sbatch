#!/bin/bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=V4Mosaic80
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

mkdir -p logs
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/V4Mosaic80_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "job_id=${SLURM_JOB_ID:-local}"
echo "host=$(hostname)"
echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "care_root=${CARE_ROOT}"
echo "python=$("${CARE_ROOT}/envs/env_CARE/bin/python" -c 'import sys; print(sys.executable)')"

export MPLCONFIGDIR=/tmp/care_mpl_${SLURM_JOB_ID:-local}
export PYTHONUNBUFFERED=1

"${CARE_ROOT}/envs/env_CARE/bin/python" \
  scripts/forensics/care_failure_forensics/run_mosaic_recipe_decomposition_v2.py \
  --root "${CARE_ROOT}" \
  --run-id "v4_mosaic_80case_${SLURM_JOB_ID:-local}" \
  --cases-from-file "${CARE_ROOT}/results/20260730_care_failure_forensics_deep_research_packet/v4_mosaic_t2_present_cases.txt" \
  --clean-oof-limit 220 \
  --require-cuda

"${CARE_ROOT}/envs/env_CARE/bin/python" \
  scripts/forensics/care_failure_forensics/build_v4_design_readiness_packet.py \
  --root "${CARE_ROOT}"

echo "end_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
