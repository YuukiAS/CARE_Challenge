#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --job-name=T2EdemaPilot
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=32G
#SBATCH --time=02:00:00
#SBATCH --partition=general

set -euo pipefail

CARE_ROOT="${CARE_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
cd "${CARE_ROOT}"

mkdir -p "${CARE_ROOT}/logs"
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/T2EdemaPilot_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "LOG_FILE=${LOG_FILE}"
echo "CARE_ROOT=${CARE_ROOT}"
echo "HOST=$(hostname)"
echo "START=$(date -Is)"

"${CARE_ROOT}/envs/env_CARE/bin/python" "${CARE_ROOT}/scripts/experiments/t2_present_edema_pilot.py" "$@"

echo "END=$(date -Is)"
