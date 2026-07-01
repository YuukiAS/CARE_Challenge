#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=CascadeTeacherInfer
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=08:00:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access

set -euo pipefail

export CARE_ROOT="${CARE_ROOT:-/users/a/e/aereinh/CARE}"
export CODEX_HOME="${CODEX_HOME:-/users/a/e/aereinh/.codex-home-care}"
export CODEX_HOME_BASE="${CODEX_HOME_BASE:-/users/a/e/aereinh/.codex-homes}"
export CODEX_REPO_ROOT="${CODEX_REPO_ROOT:-${CARE_ROOT}}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-/users/a/e/aereinh/.cache/codex-care}"
export TMPDIR="${TMPDIR:-/users/a/e/aereinh/.tmp/codex-care}"
export PATH="/users/a/e/aereinh/codex-runtime/bin:${CARE_ROOT}/envs/env_CARE/bin:${PATH}"

cd "${CARE_ROOT}"
source "${CARE_ROOT}/env_nnunet.sh"

mkdir -p logs
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/CascadeTeacherInfer_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

TASK_ROOT="${CARE_ROOT}/results/20260629_cascade_teacher_route"
CACHE_ROOT="${TASK_ROOT}/teacher_cache"
INPUT_DIR="${CACHE_ROOT}/nnunet_train_input_fold0"
PRED_DIR="${CACHE_ROOT}/nnunet_train_predictions/fold_0/checkpoint_best"
SPLIT_JSON="${CARE_ROOT}/data/benchmarks/protocol/splits_MyoPS.json"
RAW_IMAGES="${CARE_ROOT}/data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS/imagesTr"
export TASK_ROOT CACHE_ROOT INPUT_DIR PRED_DIR SPLIT_JSON RAW_IMAGES

echo "CARE_ROOT=${CARE_ROOT}"
echo "LOG_FILE=${LOG_FILE}"
echo "INPUT_DIR=${INPUT_DIR}"
echo "PRED_DIR=${PRED_DIR}"
echo "nnUNet_raw=${nnUNet_raw}"
echo "nnUNet_preprocessed=${nnUNet_preprocessed}"
echo "nnUNet_results=${nnUNet_results}"

mkdir -p "${INPUT_DIR}" "${PRED_DIR}"

"${CARE_ROOT}/envs/env_CARE/bin/python" - <<'PY'
import json
import os
from pathlib import Path

care_root = Path(os.environ["CARE_ROOT"])
split_json = Path(os.environ["SPLIT_JSON"])
raw_images = Path(os.environ["RAW_IMAGES"])
input_dir = Path(os.environ["INPUT_DIR"])
split = json.loads(split_json.read_text(encoding="utf-8"))["folds"][0]
missing = []
for case_id in split["train"]:
    for channel in range(3):
        src = raw_images / f"{case_id}_{channel:04d}.nii.gz"
        dst = input_dir / src.name
        if not src.is_file():
            missing.append(str(src))
            continue
        if dst.exists() or dst.is_symlink():
            continue
        os.symlink(src, dst)
if missing:
    raise FileNotFoundError("\n".join(missing[:20]))
print({"train_cases": len(split["train"]), "input_files": len(list(input_dir.glob("*.nii.gz")))})
PY

PREDICT_ARGS=(
  -i "${INPUT_DIR}"
  -o "${PRED_DIR}"
  -d 501
  -c 3d_fullres
  -f 0
  -tr "${CARE_NNUNET_TRAINER:-nnUNetTrainer_500epochs}"
  -chk checkpoint_best.pth
  --save_probabilities
)

if [[ "${NNUNET_DISABLE_TTA:-0}" == "1" ]]; then
  PREDICT_ARGS+=(--disable_tta)
fi

echo "Running nnUNetv2_predict ${PREDICT_ARGS[*]}"
nnUNetv2_predict "${PREDICT_ARGS[@]}"

"${CARE_ROOT}/envs/env_CARE/bin/python" scripts/evaluation/preflight_cascade_teacher_cache.py \
  --out-dir "${CACHE_ROOT}" \
  --fold 0

echo "Cascade teacher train inference complete."
