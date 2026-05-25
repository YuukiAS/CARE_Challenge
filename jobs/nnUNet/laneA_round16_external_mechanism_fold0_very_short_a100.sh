#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=R16ExtA100
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=04:00:00
#SBATCH --gres=gpu:nvidia_a100-pcie-40gb:1
#SBATCH --partition=a100-gpu
#SBATCH --qos=gpu_access

set -euo pipefail

CARE_ROOT="${CARE_ROOT:-/overflow/htzhu/CARE}"
export ROUND16_ALLOW_UNREGISTERED="${ROUND16_ALLOW_UNREGISTERED:-1}"
exec "${CARE_ROOT}/jobs/nnUNet/laneA_round16_external_mechanism_fold0_very_short.sh"
