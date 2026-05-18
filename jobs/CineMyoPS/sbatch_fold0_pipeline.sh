#!/bin/bash
# Fold-0 end-to-end: Task026 train (budget epochs) + export protocol val preds + unified eval vs Dataset502.
# Default 300 epochs is intended to stay within the 8h iterative-improvement budget.
# Submit from repo root: cd /path/to/CARE && sbatch jobs/CineMyoPS/sbatch_fold0_pipeline.sh
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=CineMyoPS_e2e
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=08:00:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access
set -euo pipefail

if [[ -z "${CARE_ROOT:-}" ]]; then
  if [[ -n "${SLURM_SUBMIT_DIR:-}" && -f "${SLURM_SUBMIT_DIR}/env_nnunet.sh" ]]; then
    CARE_ROOT="$(cd "${SLURM_SUBMIT_DIR}" && pwd)"
  else
    THIS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    CARE_ROOT="$(cd "${THIS_DIR}/../.." && pwd)"
  fi
fi
export CARE_ROOT
cd "${CARE_ROOT}"
# shellcheck source=/dev/null
source "${CARE_ROOT}/env_nnunet.sh"

CARE_CineMyoPS_ENV="${CARE_CineMyoPS_ENV:-${CARE_CINEMYOPS_ENV:-${CARE_ROOT}/env_CARE_nnUNet_v1}}"
export PATH="${CARE_CineMyoPS_ENV}/bin:${PATH}"
export CARE_CineMyoPS_ENV
export PYTHONUNBUFFERED=1

export FOLD="${FOLD:-0}"
export CINE_NNUNET_TASK="${CINE_NNUNET_TASK:-Task026_Cine_4D}"
export CINE_NNUNET_TRAINER="${CINE_NNUNET_TRAINER:-CARECineMyoPSTrainer}"
export CINE_OUTPUT_MODEL="${CINE_OUTPUT_MODEL:-CineMyoPS}"
export CINE_NNUNET_EPOCHS="${CINE_NNUNET_EPOCHS:-300}"
export CINE_PRED_CHECKPOINT="${CINE_PRED_CHECKPOINT:-model_final_checkpoint}"
export CINE_SKIP_PREPARE="${CINE_SKIP_PREPARE:-1}"
export CINE_RUN_EXPORT_EVAL=1

mkdir -p "${CARE_ROOT}/logs" "${CARE_ROOT}/results/experiments"
TS="$(date +%Y%m%d_%H%M%S)"
_SHORT="${SLURM_JOB_NAME:-CineMyoPS_e2e}"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/${_SHORT}_${SLURM_JOB_ID:-local}_${TS}.log}"
ITER_LOG="${CARE_ROOT}/results/experiments/CineMyoPS_iteration_log.md"
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "===== CineMyoPS fold0 pipeline (train+export+eval) ====="
echo "host=$(hostname) SLURM_JOB_ID=${SLURM_JOB_ID:-na}"
echo "CARE_ROOT=$(readlink -f "${CARE_ROOT}")"
echo "LOG_FILE=$(readlink -f "${LOG_FILE}")"
echo "FOLD=${FOLD} TASK=${CINE_NNUNET_TASK} TRAINER=${CINE_NNUNET_TRAINER} OUTPUT_MODEL=${CINE_OUTPUT_MODEL} CINE_NNUNET_EPOCHS=${CINE_NNUNET_EPOCHS} CINE_SKIP_PREPARE=${CINE_SKIP_PREPARE} CINE_NUM_FRAMES=${CINE_NUM_FRAMES:-4} CINE_PRED_CHECKPOINT=${CINE_PRED_CHECKPOINT} CINE_BN_RECALIBRATE=${CINE_BN_RECALIBRATE:-0} CINE_BN_RECALIB_BATCHES=${CINE_BN_RECALIB_BATCHES:-32}"
echo "frame policy: Task026 ED at t=0 + linspace sample (see prepare_task026_cine_4d.py / task026_utils.sample_frame_indices)"

_START_TS="$(date +%s)"
bash "${CARE_ROOT}/jobs/CineMyoPS/run_task026_paper_steps.sh"
_END_TS="$(date +%s)"
_ELAPSED=$((_END_TS - _START_TS))

PY_EVAL="${CARE_EVAL_PYTHON:-${CARE_ROOT}/env_CARE/bin/python}"
export CARE_ROOT FOLD
_MYODICE="$("${PY_EVAL}" - <<'PY'
import json
import os
from pathlib import Path

root = Path(os.environ["CARE_ROOT"])
fold = int(os.environ.get("FOLD", "0"))
output_model = os.environ.get("CINE_OUTPUT_MODEL", "CineMyoPS")
p = root / "results/metrics/unified" / output_model / f"fold_{fold}" / "evaluation_summary.json"
if not p.is_file():
    print("n/a")
else:
    d = json.loads(p.read_text())
    md = d.get("mean_dice") or {}
    v = md.get("class_1")
    print(f"{float(v):.6f}" if v is not None else "n/a")
PY
)" || _MYODICE="n/a"

{
  echo ""
  echo "## Iteration $(date -Iseconds 2>/dev/null || date)"
  echo "- **job_id**: ${SLURM_JOB_ID:-local}"
  echo "- **log**: \`${LOG_FILE}\`"
  echo "- **frame_policy**: Task026 ED-first + ${CINE_NUM_FRAMES:-4} sampled frames (Cine 4D raw channels)"
  echo "- **config**: FOLD=${FOLD} CINE_NNUNET_EPOCHS=${CINE_NNUNET_EPOCHS} CINE_SKIP_PREPARE=${CINE_SKIP_PREPARE} CINE_PRED_CHECKPOINT=${CINE_PRED_CHECKPOINT} task=${CINE_NNUNET_TASK} trainer=${CINE_NNUNET_TRAINER} output_model=${CINE_OUTPUT_MODEL} CINE_BN_RECALIBRATE=${CINE_BN_RECALIBRATE:-0} CINE_BN_RECALIB_BATCHES=${CINE_BN_RECALIB_BATCHES:-32}"
  echo "- **planned_wall**: 8h sbatch limit"
  echo "- **actual_train_pipeline_s**: ${_ELAPSED}"
  echo "- **unified_eval mean Dice class_1 (myocardium)**: ${_MYODICE} (nnU-Net v2 Dataset502 ref mean myocardium ≈ 0.6808 over folds; compare same metric on protocol val)"
  echo "- **note**: Leaderboard \`myocardium_cinemyops\` is a hosted composite; offline protocol metric tracked here is **class_1** vs Dataset502 labels on val split."
} >> "${ITER_LOG}"

echo "===== pipeline done; appended ${ITER_LOG} ====="
