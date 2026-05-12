#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "--help" ]]; then
  cat <<'EOF'
Usage: bash code/CineMyoPS/smoke_test.sh

Runs a 2-case Task026 smoke test end-to-end with the nnU-Net v1 CineMyoPS paper replication path.
EOF
  exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CARE_ROOT="${CARE_ROOT:-$(cd "${SCRIPT_DIR}/../.." && pwd)}"
source "${CARE_ROOT}/env_nnunet.sh"

CARE_CineMyoPS_ENV="${CARE_CineMyoPS_ENV:-${CARE_CINEMYOPS_ENV:-${CARE_ROOT}/env_CARE_nnUNet_v1}}"
PY="${CARE_CineMyoPS_ENV}/bin/python"
TASK="Task026_Cine_4D_smoke"
BENCHMARK_TASK_ROOT="${CARE_ROOT}/data/benchmarks/CineMyoPS/${TASK}"
RAW_TASK_ROOT="${nnUNet_raw}/${TASK}"
PREPROCESSED_TASK_ROOT="${nnUNet_preprocessed}/${TASK}"
PLANS_2D="${PREPROCESSED_TASK_ROOT}/nnUNetPlansv2.1_plans_2D.pkl"
PLANS_2D_LEGACY="${PREPROCESSED_TASK_ROOT}/nnUNetPlans_plans_2D.pkl"
SMOKE_PROTOCOL_JSON="${CARE_ROOT}/data/benchmarks/protocol/splits_CineMyoPS_smoke.json"
MODEL_DIR="${nnUNet_results}/nnUNet/2d/${TASK}/CARECineMyoPSTrainer__nnUNetPlansv2.1/fold_0"

export PYTHONPATH="${CARE_ROOT}/third_party/CineMyoPS/code:${PYTHONPATH:-}"
export CINE_NUM_FRAMES="${CINE_NUM_FRAMES:-4}"
export CINE_NNUNET_TASK="${TASK}"
export CINE_NNUNET_TRAINER="CARECineMyoPSTrainer"
export CINE_NNUNET_DIM="2d"
export CINE_PROTOCOL_SPLIT_JSON="${SMOKE_PROTOCOL_JSON}"

HAS_CUDA="$("${PY}" -c 'import torch; print(int(torch.cuda.is_available()))')"
if [[ "${CINE_SMOKE_INTERNAL:-0}" != "1" && "${HAS_CUDA}" != "1" ]]; then
  echo "smoke: no local CUDA device detected; relaunching via srun on one GPU"
  exec srun \
    --partition=htzhulab \
    --qos=gpu_access \
    --gres=gpu:1 \
    --cpus-per-task=8 \
    --mem=64G \
    --time=00:20:00 \
    env \
      CARE_ROOT="${CARE_ROOT}" \
      CINE_SMOKE_INTERNAL=1 \
      CINE_NUM_FRAMES="${CINE_NUM_FRAMES}" \
      bash "${CARE_ROOT}/code/CineMyoPS/smoke_test.sh"
fi
if [[ "${CINE_SMOKE_INTERNAL:-0}" == "1" && "${HAS_CUDA}" != "1" ]]; then
  echo "smoke: expected a CUDA device inside the srun allocation, but torch.cuda.is_available() is still false" >&2
  exit 1
fi

echo "smoke repo root: $(readlink -f "${CARE_ROOT}")"
echo "smoke benchmark task: $(readlink -f "${BENCHMARK_TASK_ROOT}")"
echo "smoke raw task: $(readlink -f "${RAW_TASK_ROOT}")"
echo "smoke preprocessed task: $(readlink -f "${PREPROCESSED_TASK_ROOT}")"
echo "smoke protocol json: $(readlink -f "${SMOKE_PROTOCOL_JSON}")"
echo "smoke model dir: $(readlink -f "$(dirname "${MODEL_DIR}")")"

"${PY}" "${CARE_ROOT}/code/CineMyoPS/prepare_task026_cine_4d.py" \
  --input "${CARE_ROOT}/data/CARE_Challenge/CineMyoPS_train" \
  --output "${BENCHMARK_TASK_ROOT}" \
  --nnunet-raw-output "${RAW_TASK_ROOT}" \
  --num-frames "${CINE_NUM_FRAMES}" \
  --max-cases 2

"${PY}" "${CARE_ROOT}/code/CineMyoPS/sanity_check_task026.py" \
  --task-root "${BENCHMARK_TASK_ROOT}" \
  --sample-cases 2 \
  --seed 42

"${PY}" "${CARE_ROOT}/third_party/CineMyoPS/code/nnunet/experiment_planning/old/old_plan_and_preprocess_task.py" \
  -t "${TASK}" \
  -pl 2 \
  -pf 2 \
  -s 1

if [[ ! -f "${PLANS_2D}" && -f "${PLANS_2D_LEGACY}" ]]; then
  ln -sfn "nnUNetPlans_plans_2D.pkl" "${PLANS_2D}"
fi

"${PY}" - "${RAW_TASK_ROOT}" "${PREPROCESSED_TASK_ROOT}" "${SMOKE_PROTOCOL_JSON}" <<'PY'
import json
import pickle
import sys
from pathlib import Path

raw_task = Path(sys.argv[1])
preprocessed_task = Path(sys.argv[2])
protocol_json = Path(sys.argv[3])
case_ids = sorted(path.name.replace(".nii.gz", "") for path in (raw_task / "labelsTr").glob("*.nii.gz"))
if len(case_ids) != 2:
    raise RuntimeError(f"Smoke task expects exactly 2 cases, found {len(case_ids)}: {case_ids}")
folds = [{"train": [case_ids[0]], "val": [case_ids[1]]}]
protocol_json.parent.mkdir(parents=True, exist_ok=True)
protocol_json.write_text(json.dumps({"protocol": "CARE-smoke", "folds": folds}, indent=2) + "\n", encoding="utf-8")
preprocessed_task.mkdir(parents=True, exist_ok=True)
with (preprocessed_task / "splits_final.pkl").open("wb") as handle:
    pickle.dump(folds, handle)
print(f"smoke wrote protocol json: {protocol_json.resolve()}")
print(f"smoke wrote splits_final.pkl: {(preprocessed_task / 'splits_final.pkl').resolve()}")
PY

"${PY}" "${CARE_ROOT}/third_party/CineMyoPS/code/Lascar_3_train.py" \
  2d CARECineMyoPSTrainer "${TASK}" 0 \
  --epochs 2 \
  --disable_postprocessing_on_folds

bash "${CARE_ROOT}/code/CineMyoPS/export_protocol_val_predictions.sh"

TRAIN_LOG="$(find "${MODEL_DIR}" -maxdepth 1 -name 'training_log_*.txt' | sort | tail -n 1)"
[[ -n "${TRAIN_LOG}" ]] || { echo "missing smoke training log under ${MODEL_DIR}" >&2; exit 1; }
echo "smoke training log: $(readlink -f "${TRAIN_LOG}")"
grep 'pathology_seg loss=' "${TRAIN_LOG}" >/tmp/cinemyops_smoke_pathology_loss.txt
grep -Eiq 'nan|inf' /tmp/cinemyops_smoke_pathology_loss.txt && {
  echo "pathology_seg loss contains nan/inf" >&2
  exit 1
}
tail -n 5 /tmp/cinemyops_smoke_pathology_loss.txt
echo "Smoke test PASSED"
