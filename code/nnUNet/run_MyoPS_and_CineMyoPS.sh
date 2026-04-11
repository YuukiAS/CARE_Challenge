#!/bin/bash
# CARE nnU-Net v2 — both datasets in one Slurm job (MyoPS 501 then CineMyoPS 502).
# For one dataset only: nnUNet/run_MyoPS.sh or nnUNet/run_CineMyoPS.sh
#
# Submit:  sbatch "${CARE_ROOT}/code/nnUNet/run_MyoPS_and_CineMyoPS.sh"
#
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --job-name=CARE_nnUNet_MyoPS_and_CineMyoPS
#SBATCH --output=/overflow/htzhu/CARE/logs/slurm_%x_%j.out
#SBATCH --mem=64G
#SBATCH --time=144:00:00
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

care_nnunet_init_logging "$CARE_ROOT" "MyoPS_CineMyoPS"
care_nnunet_print_header "CARE nnU-Net — MyoPS + CineMyoPS (both)"
care_nnunet_env_python
care_nnunet_check_gpu_torch

care_nnunet_run_subtask "myops" "501" "Dataset501_CAREMyoPS"
care_nnunet_run_subtask "cinemyops" "502" "Dataset502_CARECineMyoPS"

echo "===== Finished CARE nnU-Net (both datasets) ====="
echo "End time: $(date -Iseconds)"
echo "nnUNet_results: $nnUNet_results"
