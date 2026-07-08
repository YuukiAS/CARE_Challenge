#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=M9SRRDict
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
source "${CARE_ROOT}/.care-codex-env.sh"
source "${CARE_ROOT}/env_nnunet.sh"
export PATH=/users/a/e/aereinh/codex-runtime/bin:${CARE_ROOT}/envs/env_CARE/bin:${PATH}
mkdir -p logs
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/M9SRRDict_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

OUT_ROOT="${M9_RUNTIME_ROOT:-${CARE_ROOT}/results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/runtime}"
for VARIANT in \
  m9_srr_main_true_br2_pattern_sip \
  m9_srr_main_lesion_proposal_memory \
  m9_srr_main_t2_edema_recall_focus
do
  "${CARE_ROOT}/envs/env_CARE/bin/python" scripts/training/run_srr_propref_myops_fold0.py \
    --variant "${VARIANT}" \
    --out-root "${OUT_ROOT}" \
    --max-steps 6000 \
    --max-runtime-seconds 27000 \
    --val-every 300 \
    --loss-weight loss_scar_refiner_small_roi=1.0 \
    --loss-weight loss_edema_refiner_large_roi_t2_present=1.0
done
"${CARE_ROOT}/envs/env_CARE/bin/python" scripts/evaluation/aggregate_srr_v3_m9_dictionary_fidelity_packet.py
