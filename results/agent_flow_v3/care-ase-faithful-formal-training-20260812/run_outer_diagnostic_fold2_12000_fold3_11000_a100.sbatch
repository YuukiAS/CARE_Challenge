#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=ASEOUTR12
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=06:00:00
#SBATCH --gres=gpu:nvidia_a100-pcie-40gb:1
#SBATCH --partition=a100-gpu
#SBATCH --qos=gpu_access

set -euo pipefail

MAIN_ROOT="/users/a/e/aereinh/CARE"
WORKTREE="${MAIN_ROOT}/.worktrees/care-ase-faithful-formal-training-20260812"
RESULT_ROOT="${WORKTREE}/results/agent_flow_v3/care-ase-faithful-formal-training-20260812"
OUTER_ROOT="${RESULT_ROOT}/outer_diagnostic_user_authorized"
LOCK_DIR="${OUTER_ROOT}/outer_diagnostic_step12000_11000_20260815.lock"
STATUS_JSON="${OUTER_ROOT}/outer_diagnostic_step12000_11000_job_status.json"
LOG_DIR="${WORKTREE}/logs"

mkdir -p "${LOG_DIR}" "${OUTER_ROOT}"
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${LOG_DIR}/ASEOUTR12_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

cd "${WORKTREE}"
source "${MAIN_ROOT}/.care-codex-env.sh"
source "${MAIN_ROOT}/env_nnunet.sh"
export PATH="${MAIN_ROOT}/envs/env_CARE/bin:${PATH}"
export PYTHONPATH="${WORKTREE}:${PYTHONPATH:-}"
export CARE_DATA_REPO_ROOT="${MAIN_ROOT}"

echo "JOB_START_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "LOG_FILE=${LOG_FILE}"
hostname
nvidia-smi || true

if ! mkdir "${LOCK_DIR}" 2>/dev/null; then
  echo "outer diagnostic lock already exists: ${LOCK_DIR}"
  exit 0
fi
trap 'rmdir "${LOCK_DIR}" 2>/dev/null || true' EXIT

FOLD2_CKPT="${RESULT_ROOT}/runtime/fold_2/checkpoint_step12000.pt"
FOLD3_CKPT="${RESULT_ROOT}/runtime/fold_3_parallel/checkpoint_step11000.pt"
for ckpt in "${FOLD2_CKPT}" "${FOLD3_CKPT}"; do
  if [[ ! -f "${ckpt}" || ! -f "${ckpt}.verified.json" ]]; then
    echo "missing verified checkpoint: ${ckpt}" >&2
    exit 70
  fi
done

"${MAIN_ROOT}/envs/env_CARE/bin/python" \
  scripts/evaluation/care_ase/run_current_user_authorized_outer_diagnostic.py \
  --fold-step 2:12000 \
  --fold-step 3:11000 \
  --diagnostic-output-suffix step12000_11000_20260815 \
  --output-name outer_diagnostic_step12000_11000_combined_summary.json \
  --force

"${MAIN_ROOT}/envs/env_CARE/bin/python" - <<'PY'
import json
import os
from pathlib import Path

root = Path("/users/a/e/aereinh/CARE/.worktrees/care-ase-faithful-formal-training-20260812")
result_root = root / "results/agent_flow_v3/care-ase-faithful-formal-training-20260812"
summary = result_root / "outer_diagnostic_user_authorized/outer_diagnostic_step12000_11000_combined_summary.json"
packet = json.loads(summary.read_text())
status = {
    "status": "COMPLETED_PASS",
    "authorized_by_user": True,
    "authorized_utc": "2026-08-15T00:00:00Z_USER_CHAT_REQUEST",
    "comparison_contract": packet.get("comparison_contract"),
    "fold_steps_requested": packet.get("fold_steps"),
    "output": str(summary.relative_to(root)),
    "result_summary": {
        "case_count_total": packet.get("case_count_total"),
        "scar_care_mean": packet["scar"]["care_mean"],
        "scar_nnunet_mean": packet["scar"]["nnunet_mean"],
        "scar_delta_care_minus_nnunet": packet["scar"]["delta_care_minus_nnunet"],
        "pure_edema_care_mean": packet["pure_edema"]["care_mean"],
        "pure_edema_nnunet_mean": packet["pure_edema"]["nnunet_mean"],
        "pure_edema_delta_care_minus_nnunet": packet["pure_edema"]["delta_care_minus_nnunet"],
    },
    "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
    "training_interference": "none_eval_only_read_only_checkpoint_inputs_isolated_outer_output",
    "updated_utc": __import__("datetime").datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
}
status_path = result_root / "outer_diagnostic_user_authorized/outer_diagnostic_step12000_11000_job_status.json"
status_path.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n")
print(json.dumps(status, indent=2, sort_keys=True))
PY

echo "JOB_END_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
