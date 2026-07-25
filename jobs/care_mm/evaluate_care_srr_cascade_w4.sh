#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=SRRW4Eval
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=02:00:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access

set -euo pipefail

CARE_ROOT="${CARE_ROOT:-/users/a/e/aereinh/CARE}"
cd "${CARE_ROOT}"

mkdir -p logs/care_myops_srr_cascade_submission_rescue/w4_v2
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/care_myops_srr_cascade_submission_rescue/w4_v2/SRRW4Eval_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

RESULT_ROOT="${CARE_ROOT}/results/20260724_care_myops_srr_cascade_submission_rescue"
RC1_ROOT="${RESULT_ROOT}/runtime_closure_repair_rc1"
LOCK_ROOT="${RESULT_ROOT}/runtime/w4_eval_v2"
LOCK_DIR="${LOCK_ROOT}/w4_eval.lock"
ATTEMPT_ID="${CARE_W4_ATTEMPT_ID:-w4_eval_${SLURM_JOB_ID:-local}}"
PARTITION_NAME="${SLURM_JOB_PARTITION:-unknown}"
mkdir -p "${LOCK_ROOT}"
if ! mkdir "${LOCK_DIR}" 2>/dev/null; then
  OWNER_FILE="${LOCK_DIR}/owner.json"
  LOST_RECEIPT="${RC1_ROOT}/w4_eval_race_lock_lost_${ATTEMPT_ID}_${SLURM_JOB_ID:-local}.json"
  "${CARE_ROOT}/envs/env_CARE/bin/python" - <<PY
import json
from pathlib import Path

owner_path = Path("${OWNER_FILE}")
owner = json.loads(owner_path.read_text()) if owner_path.exists() else {"decision": "LOCK_OWNER_UNKNOWN"}
receipt = {
    "decision": "RACE_LOCK_LOST",
    "attempt_id": "${ATTEMPT_ID}",
    "slurm_job_id": "${SLURM_JOB_ID:-local}",
    "partition": "${PARTITION_NAME}",
    "owner": owner,
    "formal_training_credit": 0,
}
path = Path("${LOST_RECEIPT}")
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
print(json.dumps(receipt, indent=2, sort_keys=True))
PY
  exit 0
fi

"${CARE_ROOT}/envs/env_CARE/bin/python" - <<PY
import json
from pathlib import Path

receipt = {
    "decision": "LOCK_HELD",
    "attempt_id": "${ATTEMPT_ID}",
    "slurm_job_id": "${SLURM_JOB_ID:-local}",
    "partition": "${PARTITION_NAME}",
    "log_file": "${LOG_FILE}",
}
path = Path("${LOCK_DIR}") / "owner.json"
path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
print(json.dumps(receipt, indent=2, sort_keys=True))
PY

source "${CARE_ROOT}/.care-codex-env.sh"
source "${CARE_ROOT}/env_nnunet.sh"
export PATH="${CARE_ROOT}/envs/env_CARE/bin:${PATH}"

python scripts/evaluation/evaluate_care_srr_cascade.py \
  --w4-batch \
  --pathologies scar,edema \
  --device "${CARE_W4_DEVICE:-cuda}"

python scripts/evaluation/aggregate_care_srr_cascade_w4.py
