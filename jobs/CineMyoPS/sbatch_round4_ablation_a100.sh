#!/bin/bash
# Round4 CineMyoPS export-only combine-mode ablations on fallback A100 partition. No training.
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=CineMyoPS_r4_modes
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=04:00:00
#SBATCH --gres=gpu:1
#SBATCH --partition=a100-gpu
#SBATCH --qos=gpu_access
set -euo pipefail

THIS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "${THIS_DIR}/sbatch_round4_ablation.sh" "$@"
