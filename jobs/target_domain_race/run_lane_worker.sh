#!/usr/bin/env bash

#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=CareTDRace
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=12:00:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access

set -euo pipefail

CARE_ROOT="${CARE_ROOT:-/users/a/e/aereinh/CARE}"
LANE_ID="${LANE_ID:?LANE_ID is required}"
RUNTIME_ROOT="${RUNTIME_ROOT:-/users/a/e/aereinh/.tmp/codex-CARE/20260801_care_target_domain_pathology_specialist_race}"
RESULT_ROOT="${RESULT_ROOT:-${CARE_ROOT}/results/20260801_care_target_domain_pathology_specialist_race}"
COMMAND_FILE="${COMMAND_FILE:-${RUNTIME_ROOT}/commands/${LANE_ID}.sh}"
WAIT_SECONDS="${WAIT_SECONDS:-7200}"

mkdir -p "${RUNTIME_ROOT}/logs" "${RUNTIME_ROOT}/commands" "${RESULT_ROOT}/lane_worker_receipts"
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${RUNTIME_ROOT}/logs/${LANE_ID}_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "lane_id=${LANE_ID}"
echo "slurm_job_id=${SLURM_JOB_ID:-local}"
echo "host=$(hostname)"
echo "start_time=$(date -Is)"
echo "cuda_visible_devices=${CUDA_VISIBLE_DEVICES:-unset}"
echo "command_file=${COMMAND_FILE}"
cd "${CARE_ROOT}"
source "${CARE_ROOT}/.care-codex-env.sh"
source "${CARE_ROOT}/env_nnunet.sh"
export PATH=/users/a/e/aereinh/codex-runtime/bin:/users/a/e/aereinh/CARE/envs/env_CARE/bin:$PATH
echo "python=$(command -v python || true)"
./envs/env_CARE/bin/python - <<'PY'
import json, os, sys
payload = {
    "python": sys.executable,
    "version": sys.version,
    "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
}
try:
    import torch
    payload["torch"] = torch.__version__
    payload["cuda_available"] = torch.cuda.is_available()
    payload["cuda_device_count"] = torch.cuda.device_count()
except Exception as exc:
    payload["torch_import_error"] = repr(exc)
print(json.dumps(payload, sort_keys=True))
PY

deadline=$((SECONDS + WAIT_SECONDS))
while [[ ! -s "${COMMAND_FILE}" ]]; do
  if (( SECONDS >= deadline )); then
    echo "ERROR: command file did not appear before WAIT_SECONDS=${WAIT_SECONDS}"
    exit 42
  fi
  sleep 30
done

echo "executing_command_file=${COMMAND_FILE}"
bash "${COMMAND_FILE}"
status=$?
echo "end_time=$(date -Is)"
echo "exit_code=${status}"
exit "${status}"
