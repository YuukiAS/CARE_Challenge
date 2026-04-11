#!/bin/bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=CARE_CineMyoPS-paper
#SBATCH --output=/overflow/htzhu/CARE/logs/slurm_%x_%j.out
#SBATCH --mem=64G
#SBATCH --time=120:00:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access
mkdir -p /overflow/htzhu/CARE/logs
export CARE_ROOT="${CARE_ROOT:-/overflow/htzhu/CARE}"
# shellcheck source=/dev/null
source "$CARE_ROOT/code/lib/slurm_nnUNet.sh"
care_nnunet_init_logging "$CARE_ROOT" "CineMyoPS-paper"
care_nnunet_print_header "CARE CineMyoPS (upstream repo)"
care_nnunet_env_python
care_nnunet_check_gpu_torch
bash "$CARE_ROOT/code/CineMyoPS/run.sh" || true
