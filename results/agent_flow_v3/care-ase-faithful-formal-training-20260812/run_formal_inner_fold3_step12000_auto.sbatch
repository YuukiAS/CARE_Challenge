#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=ASEI3K12
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=08:00:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access

set -euo pipefail

MAIN_ROOT="/users/a/e/aereinh/CARE"
WORKTREE="${MAIN_ROOT}/.worktrees/care-ase-faithful-formal-training-20260812"
RESULT_ROOT="${WORKTREE}/results/agent_flow_v3/care-ase-faithful-formal-training-20260812"
RUNTIME_DIR="${RESULT_ROOT}/runtime/fold_3_parallel"
CHECKPOINT="${RUNTIME_DIR}/checkpoint_step12000.pt"
OUTPUT_DIR="${RESULT_ROOT}/inner_checkpoint_monitor/fold_3/step12000"
LOCK_DIR="${RUNTIME_DIR}/formal_inner_step12000_eval.lock"
LOG_DIR="${WORKTREE}/logs"

mkdir -p "${LOG_DIR}"
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${LOG_DIR}/ASEI3K12_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

cd "${WORKTREE}"
source "${MAIN_ROOT}/.care-codex-env.sh"
source "${MAIN_ROOT}/env_nnunet.sh"
export PATH="${MAIN_ROOT}/envs/env_CARE/bin:${PATH}"
export PYTHONPATH="${WORKTREE}:${PYTHONPATH:-}"
export MPLCONFIGDIR="/users/a/e/aereinh/.tmp/codex-CARE/care-ase-faithful-formal-training-20260812/matplotlib"
mkdir -p "${MPLCONFIGDIR}"

echo "JOB_START_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "LOG_FILE=${LOG_FILE}"
hostname
nvidia-smi || true

if [[ "$(git rev-parse HEAD)" != "fdd45b5ee1c1abea352c318c66951910e565262f" ]]; then
  echo "unexpected training worktree HEAD" >&2
  exit 65
fi

if [[ ! -f "${CHECKPOINT}" || ! -f "${CHECKPOINT}.verified.json" ]]; then
  echo "missing verified fold3 step12000 checkpoint: ${CHECKPOINT}" >&2
  exit 70
fi

export CHECKPOINT
"${MAIN_ROOT}/envs/env_CARE/bin/python" - <<'PY'
import json
import os
from pathlib import Path
ckpt = Path(os.environ["CHECKPOINT"])
verified = json.loads(Path(str(ckpt) + ".verified.json").read_text())
reload_receipt = json.loads(ckpt.with_name(ckpt.name.replace(".pt", "_full_reload_receipt.json")).read_text())
if verified.get("status") != "PASS" or reload_receipt.get("status") != "PASS":
    raise SystemExit("checkpoint verified/full-reload status is not PASS")
PY

if [[ -f "${OUTPUT_DIR}/monitor_packet.json" && -f "${OUTPUT_DIR}/casewise_metrics.csv" ]]; then
  echo "fold3 step12000 formal inner eval already exists: ${OUTPUT_DIR}"
  exit 0
fi

if ! mkdir "${LOCK_DIR}" 2>/dev/null; then
  echo "another fold3 step12000 formal inner eval job owns lock: ${LOCK_DIR}"
  exit 0
fi
trap 'rmdir "${LOCK_DIR}" 2>/dev/null || true' EXIT

"${MAIN_ROOT}/envs/env_CARE/bin/python" \
  scripts/evaluation/care_ase/monitor_care_ase_r2_inner_trend.py \
  --fold 3 \
  --checkpoint-step 12000 \
  --checkpoint "${CHECKPOINT}" \
  --split-case-lists "${RESULT_ROOT}/split_case_lists.csv" \
  --output-dir "${OUTPUT_DIR}"

echo "JOB_END_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
