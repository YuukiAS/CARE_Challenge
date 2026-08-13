#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=ASEF2R6
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=5-00:00:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access

set -euo pipefail

MAIN_ROOT="/users/a/e/aereinh/CARE"
CARE_ROOT="${MAIN_ROOT}/.worktrees/care-ase-faithful-formal-training-20260812"
TASK_KEY="care-ase-faithful-formal-training-20260812"
RESULT_ROOT="${CARE_ROOT}/results/agent_flow_v3/${TASK_KEY}"
RUNTIME_DIR="${RESULT_ROOT}/runtime/fold_2"
TMP_ROOT="/users/a/e/aereinh/.tmp/codex-CARE/${TASK_KEY}"
EXPECTED_HEAD="fdd45b5ee1c1abea352c318c66951910e565262f"
LOG_DIR="${CARE_ROOT}/logs"

mkdir -p "${LOG_DIR}" "${TMP_ROOT}/matplotlib"
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${LOG_DIR}/ASEF2R6_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

cd "${CARE_ROOT}"
source "${MAIN_ROOT}/.care-codex-env.sh"
source "${MAIN_ROOT}/env_nnunet.sh"
export PATH="${MAIN_ROOT}/envs/env_CARE/bin:${PATH}"
export PYTHONPATH="${CARE_ROOT}:${PYTHONPATH:-}"
export MPLCONFIGDIR="${TMP_ROOT}/matplotlib"
export CUBLAS_WORKSPACE_CONFIG=":4096:8"

status_json() {
  "${MAIN_ROOT}/envs/env_CARE/bin/python" - "$@" <<'PY'
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

path = Path(sys.argv[1])
payload = json.loads(sys.argv[2])
payload["updated_utc"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
}

rename_stale_lock() {
  local start="$1"
  local end="$2"
  local lock_dir="${RUNTIME_DIR}/lock_$(printf '%05d' "${start}")_$(printf '%05d' "${end}")"
  if [[ ! -d "${lock_dir}" ]]; then
    return 0
  fi
  local owner="${lock_dir}/owner.json"
  local pid=""
  if [[ -f "${owner}" ]]; then
    pid="$("${MAIN_ROOT}/envs/env_CARE/bin/python" - "${owner}" <<'PY'
import json
import sys
from pathlib import Path
payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(payload.get("pid", ""))
PY
)"
  fi
  if [[ -n "${pid}" ]] && ps -p "${pid}" >/dev/null 2>&1; then
    echo "active lock owner still alive for fold2 ${start}-${end}: pid=${pid}" >&2
    exit 67
  fi
  mv "${lock_dir}" "${RUNTIME_DIR}/stale_lock_$(printf '%05d' "${start}")_$(printf '%05d' "${end}")_before_retry_${SLURM_JOB_ID:-local}_$(date +%Y%m%d_%H%M%S)"
}

verify_checkpoint() {
  local step="$1"
  local ckpt="${RUNTIME_DIR}/$(printf 'checkpoint_step%05d.pt' "${step}")"
  if [[ ! -f "${ckpt}" || ! -f "${ckpt}.verified.json" ]]; then
    echo "missing verified fold2 step${step} checkpoint: ${ckpt}" >&2
    exit 70
  fi
  export CHECKPOINT="${ckpt}"
  "${MAIN_ROOT}/envs/env_CARE/bin/python" - <<'PY'
import json
import os
from pathlib import Path

ckpt = Path(os.environ["CHECKPOINT"])
verified = json.loads(Path(str(ckpt) + ".verified.json").read_text(encoding="utf-8"))
reload_receipt = json.loads(ckpt.with_name(ckpt.name.replace(".pt", "_full_reload_receipt.json")).read_text(encoding="utf-8"))
if verified.get("status") != "PASS" or reload_receipt.get("status") != "PASS":
    raise SystemExit(f"checkpoint verified/full-reload status is not PASS: {ckpt}")
if verified.get("global_step") != 6000 and ckpt.name == "checkpoint_step06000.pt":
    raise SystemExit("step06000 checkpoint global step mismatch")
PY
}

run_chunk() {
  local start="$1"
  local end="$2"
  local resume="${RUNTIME_DIR}/$(printf 'checkpoint_step%05d.pt' "${start}")"
  rename_stale_lock "${start}" "${end}"
  status_json "${RESULT_ROOT}/fold2_step06000_retry_status.json" "{\"status\":\"RUNNING\",\"slurm_job_id\":\"${SLURM_JOB_ID:-local}\",\"phase\":\"train_fold_2_${start}_${end}\",\"resume_checkpoint\":\"${resume}\",\"outer_accessed\":false}"
  "${MAIN_ROOT}/envs/env_CARE/bin/python" \
    scripts/training/care_ase/run_care_ase_r2_chunk.py \
    --fold 2 \
    --start-step "${start}" \
    --end-step "${end}" \
    --patch-size 20,256,256 \
    --output-dir "${RUNTIME_DIR}" \
    --seed 20260803 \
    --training-permit "${RESULT_ROOT}/training_permit_fold2.json" \
    --formal-runtime-input-bundle "${RESULT_ROOT}/formal_runtime_input_bundle_fold2.json" \
    --resume-checkpoint "${resume}"
}

run_inner_monitor() {
  local step="$1"
  local ckpt="${RUNTIME_DIR}/$(printf 'checkpoint_step%05d.pt' "${step}")"
  local out="${RESULT_ROOT}/inner_checkpoint_monitor/fold_2/$(printf 'step%05d' "${step}")"
  if [[ -f "${out}/monitor_packet.json" && -f "${out}/casewise_metrics.csv" ]]; then
    echo "fold2 step${step} formal inner eval already exists: ${out}"
    return 0
  fi
  status_json "${RESULT_ROOT}/fold2_step06000_retry_status.json" "{\"status\":\"RUNNING\",\"slurm_job_id\":\"${SLURM_JOB_ID:-local}\",\"phase\":\"inner_monitor_fold_2_step_${step}\",\"outer_accessed\":false}"
  "${MAIN_ROOT}/envs/env_CARE/bin/python" \
    scripts/evaluation/care_ase/monitor_care_ase_r2_inner_trend.py \
    --fold 2 \
    --checkpoint-step "${step}" \
    --checkpoint "${ckpt}" \
    --split-case-lists "${RESULT_ROOT}/split_case_lists.csv" \
    --output-dir "${out}"
}

echo "JOB_START_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "LOG_FILE=${LOG_FILE}"
hostname
nvidia-smi || true

HEAD_SHA="$(git rev-parse HEAD)"
if [[ "${HEAD_SHA}" != "${EXPECTED_HEAD}" ]]; then
  echo "unexpected training HEAD: ${HEAD_SHA} expected ${EXPECTED_HEAD}" >&2
  exit 65
fi

verify_checkpoint 6000
status_json "${RESULT_ROOT}/fold2_step06000_retry_status.json" "{\"status\":\"RUNNING\",\"slurm_job_id\":\"${SLURM_JOB_ID:-local}\",\"phase\":\"start_from_verified_step06000\",\"head\":\"${HEAD_SHA}\",\"outer_accessed\":false}"

for start in 6000 8000 10000 12000; do
  end=$((start + 2000))
  run_chunk "${start}" "${end}"
  run_inner_monitor "${end}"
done

"${MAIN_ROOT}/envs/env_CARE/bin/python" \
  scripts/evaluation/care_ase/select_care_ase_r2_inner_checkpoint.py \
  --packet "${RESULT_ROOT}/inner_checkpoint_monitor/fold_2/step04000/monitor_packet.json" \
  --packet "${RESULT_ROOT}/inner_checkpoint_monitor/fold_2/step06000/monitor_packet.json" \
  --packet "${RESULT_ROOT}/inner_checkpoint_monitor/fold_2/step08000/monitor_packet.json" \
  --packet "${RESULT_ROOT}/inner_checkpoint_monitor/fold_2/step10000/monitor_packet.json" \
  --packet "${RESULT_ROOT}/inner_checkpoint_monitor/fold_2/step12000/monitor_packet.json" \
  --packet "${RESULT_ROOT}/inner_checkpoint_monitor/fold_2/step14000/monitor_packet.json" \
  --output "${RESULT_ROOT}/inner_checkpoint_selection_fold2.json"

status_json "${RESULT_ROOT}/fold2_step06000_retry_status.json" "{\"status\":\"COMPLETE\",\"slurm_job_id\":\"${SLURM_JOB_ID:-local}\",\"phase\":\"fold2_14000_complete_inner_monitors_complete\",\"head\":\"${HEAD_SHA}\",\"outer_accessed\":false}"
echo "JOB_END_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
