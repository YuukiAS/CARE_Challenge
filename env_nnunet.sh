#!/usr/bin/env bash
# nnU-Net environment for CARE benchmarks. Source from job scripts or conda activate.d, e.g.:
#   source /overflow/htzhu/CARE/env_nnunet.sh
#
# When conda activates env_CARE, care_nnunet_env.sh sets CARE_ROOT then sources this file.
# If CARE_ROOT is unset, it defaults to the directory containing this script (repo root).

if [[ -z "${CARE_ROOT:-}" ]]; then
  _CARE_ENV_THIS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  export CARE_ROOT="${_CARE_ENV_THIS}"
  unset _CARE_ENV_THIS
fi

export nnUNet_raw="${nnUNet_raw:-${CARE_ROOT}/data/nnUNet/nnUNet_raw}"
export nnUNet_preprocessed="${nnUNet_preprocessed:-${CARE_ROOT}/data/nnUNet/nnUNet_preprocessed}"
export nnUNet_results="${nnUNet_results:-${CARE_ROOT}/data/nnUNet/nnUNet_results}"

# nnU-Net v2 training length: use upstream trainer variant (poly LR matches this horizon).
# Train / predict with: -tr "${CARE_NNUNET_TRAINER}"
# For 1000 epochs: export CARE_NNUNET_TRAINER=nnUNetTrainer
export CARE_NNUNET_TRAINER="${CARE_NNUNET_TRAINER:-nnUNetTrainer_500epochs}"

# U-MyoPS stage 2 (nnU-Net v1): task folder under nnUNet_raw (nnUNet_raw_data). Override if you use another Task ID.
export UMYOPS_STAGE2_TASK="${UMYOPS_STAGE2_TASK:-Task901_CARE_UmyopsPathology}"
# Build a fold-specific Stage2 task by default because the Stage1 prior channel is fold-dependent.
export UMYOPS_STAGE2_PER_FOLD_TASK="${UMYOPS_STAGE2_PER_FOLD_TASK:-1}"
# If 1, stage2 sbatch can auto-build the fold-specific raw task and run plan_and_preprocess before training.
export UMYOPS_STAGE2_AUTO_PREP="${UMYOPS_STAGE2_AUTO_PREP:-0}"
# Default off until raw Task + v1 plan_and_preprocess exist. If 1: local run.sh also runs stage 2; run_unified_benchmark_{test,all}.sh submits a second Slurm job (afterok stage 1).
export UMYOPS_RUN_STAGE2="${UMYOPS_RUN_STAGE2:-0}"
# If 1, Stage1 wrappers auto-link CARE staging into the legacy jrs data layout before training.
export UMYOPS_STAGE1_AUTO_LAYOUT="${UMYOPS_STAGE1_AUTO_LAYOUT:-1}"
