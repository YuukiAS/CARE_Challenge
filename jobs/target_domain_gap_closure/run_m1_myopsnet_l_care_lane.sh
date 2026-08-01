#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=12
#SBATCH --job-name=M1MyoPSLane
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=96G
#SBATCH --time=12:00:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access

set -euo pipefail

CARE_ROOT="${CARE_ROOT:-/users/a/e/aereinh/CARE}"
LANE="M1_MYOPSNET_L_CARE"
LOCK_DIR="${LOCK_DIR:-/users/a/e/aereinh/.locks/care_td_gap_closure_20260801}"
RESULT_ROOT="${RESULT_ROOT:-${CARE_ROOT}/results/20260801_care_target_domain_race_gap_closure}"
mkdir -p "${LOCK_DIR}" "${RESULT_ROOT}/race_claims" "${CARE_ROOT}/logs"

exec 8>"${LOCK_DIR}/${LANE}.claim"
if ! flock -n 8; then
  TS="$(date -Is)"
  cat > "${RESULT_ROOT}/race_claims/${LANE}_${SLURM_JOB_ID:-local}_race_lost.json" <<EOF
{
  "created_at": "${TS}",
  "lane_id": "${LANE}",
  "slurm_job_id": "${SLURM_JOB_ID:-local}",
  "status": "RACE_LOST_ZERO_CREDIT"
}
EOF
  echo "RACE_LOST_ZERO_CREDIT lane=${LANE}"
  exit 0
fi

cd "${CARE_ROOT}"
source "${CARE_ROOT}/.care-codex-env.sh"
source "${CARE_ROOT}/env_nnunet.sh"
export PATH="/users/a/e/aereinh/codex-runtime/bin:${CARE_ROOT}/envs/env_CARE/bin:${PATH}"

EPOCHS="${EPOCHS:-60}"
STEPS_PER_EPOCH="${STEPS_PER_EPOCH:-100}"
DIM="${DIM:-128}"
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/M1MyoPSLane_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "[M1MyoPSLane] job=${SLURM_JOB_ID:-local} host=$(hostname) start=$(date -Is)"
for FOLD in 2 3; do
  echo "[M1MyoPSLane] fold=${FOLD} start=$(date -Is)"
  "${CARE_ROOT}/envs/env_CARE/bin/python" scripts/training/target_domain_gap_closure/run_m1_myopsnet_l_care.py \
    --fold "${FOLD}" \
    --epochs "${EPOCHS}" \
    --steps-per-epoch "${STEPS_PER_EPOCH}" \
    --dim "${DIM}"
  echo "[M1MyoPSLane] fold=${FOLD} end=$(date -Is)"
done
echo "[M1MyoPSLane] job=${SLURM_JOB_ID:-local} end=$(date -Is)"
