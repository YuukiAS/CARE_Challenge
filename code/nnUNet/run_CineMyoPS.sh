#!/bin/bash
# CARE nnU-Net v2 — CineMyoPS challenge only (dataset ID 502, cine frame).
#
# Submit:  sbatch "${CARE_ROOT}/code/nnUNet/run_CineMyoPS.sh"
#
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --job-name=CARE_nnUNet_CineMyoPS
#SBATCH --output=/overflow/htzhu/CARE/logs/slurm_%x_%j.out
#SBATCH --mem=64G
#SBATCH --time=72:00:00
#SBATCH --partition=htzhulab
#SBATCH --gres=gpu:1
#SBATCH --qos=gpu_access

mkdir -p /overflow/htzhu/CARE/logs

CARE_ROOT="${CARE_ROOT:-/overflow/htzhu/CARE}"
ENV_PATH="${ENV_PATH:-$CARE_ROOT/env_CARE}"
CONFIG="${CONFIG:-3d_fullres}"
FOLD="${FOLD:-0}"
NPFP="${NPFP:-8}"
RUN_TEST="${RUN_TEST:-1}"
SKIP_CONVERT="${SKIP_CONVERT:-0}"

# shellcheck source=/dev/null
source "$CARE_ROOT/code/lib/slurm_nnUNet.sh"

care_nnunet_init_logging "$CARE_ROOT" "CineMyoPS"
care_nnunet_print_header "CARE nnU-Net — CineMyoPS only"
care_nnunet_env_python
care_nnunet_check_gpu_torch

care_nnunet_run_subtask "cinemyops" "502" "Dataset502_CARECineMyoPS"

echo "===== Finished CARE nnU-Net (CineMyoPS) ====="
echo "End time: $(date -Iseconds)"
echo "nnUNet_results: $nnUNet_results"
