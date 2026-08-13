#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=ASEdiagB
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=08:00:00
#SBATCH --gres=gpu:nvidia_a100-pcie-40gb:1
#SBATCH --partition=a100-gpu
#SBATCH --qos=gpu_access

set -euo pipefail

RUNTIME_REPO="/users/a/e/aereinh/CARE/.worktrees/care-ase-faithful-formal-training-20260812"
DEVELOP_REPO="/users/a/e/aereinh/.tmp/codex-CARE/care-ase-develop-rules-20260813"
TASK_ROOT="${RUNTIME_REPO}/results/agent_flow_v3/care-ase-faithful-formal-training-20260812"
OUT_DIR="${TASK_ROOT}/stage_b_forgetting_diagnostic/gpu_readonly_${SLURM_JOB_ID:-local}"
LOG_DIR="${OUT_DIR}/logs"
mkdir -p "${LOG_DIR}"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
LOG_FILE="${LOG_DIR}/ASEdiagB_${SLURM_JOB_ID:-local}_${TS}.log"
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "started_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "host=$(hostname)"
echo "slurm_job_id=${SLURM_JOB_ID:-local}"
echo "runtime_repo=${RUNTIME_REPO}"
echo "develop_repo=${DEVELOP_REPO}"
echo "output_dir=${OUT_DIR}"
cd "${DEVELOP_REPO}"
git rev-parse HEAD

source /users/a/e/aereinh/CARE/env_nnunet.sh || true
export PYTHONPATH="${RUNTIME_REPO}:${RUNTIME_REPO}/src:${PYTHONPATH:-}"

/users/a/e/aereinh/CARE/envs/env_CARE/bin/python \
  scripts/evaluation/care_ase/run_stage_b_gpu_forgetting_diagnostic.py \
  --runtime-repo "${RUNTIME_REPO}" \
  --output-dir "${OUT_DIR}" \
  --folds 2 3 \
  --steps 2000 6000 \
  --inner-partial-limit 3 \
  --actual-partial-limit 3 \
  --complete-control-limit 1 \
  --evidence-case-limit-per-fold 1

echo "finished_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
