#!/bin/bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=U-MyoPS-Stage2-A100
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=08:00:00
#SBATCH --gres=gpu:1
#SBATCH --partition=a100-gpu
#
# U-MyoPS stage 2 on school GPU fallback partitions. The main entrypoint handles
# logging/training; pass partition/QOS overrides to sbatch when needed.
set -euo pipefail

if [[ -n "${SLURM_SUBMIT_DIR:-}" ]]; then
  CARE_ROOT="$(cd "${SLURM_SUBMIT_DIR}" && pwd)"
else
  THIS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  CARE_ROOT="${CARE_ROOT:-$(cd "${THIS_DIR}/../.." && pwd)}"
fi
export CARE_ROOT
cd "${CARE_ROOT}"

exec bash "${CARE_ROOT}/jobs/U-MyoPS/sbatch_stage2.sh"
